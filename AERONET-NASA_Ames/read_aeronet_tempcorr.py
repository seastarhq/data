#!/usr/bin/env python3
"""Read an AERONET <site>_<instrument>_raw_and_aod.csv, temperature-correct the V
columns, and save in the same npz layout as SeaSTAR L0.6 files.

The output holds array_data (numpy structured array, datetime64[ms] UTC) and
metadata (dict), so it loads like an L06 file:

    z = np.load(path, allow_pickle=True)
    data, metadata = z["array_data"], z["metadata"][()]

The correction is applied in place to V1/V2/V3 for every band, using the
Temperature column and the A/B coefficients from calibrs_for_<instrument>.txt:

    Vcorr = Vmeas / (1 + (t - 25) * A + (t - 25)^2 * B)
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from read_aeronet import V_BANDS, build_dtype, parse_csv


T_REF = 25.0

# The calibrs file's wavelength labels are each instrument's measured centre
# wavelengths in microns (0.674 on 905, 0.676 on 608, ...), not the nominal band
# names in the CSV headers, so rows are matched to the nearest band within this
# tolerance. The "In" suffix marks the InGaAs 1020.
WAVELENGTH_TOL_NM = 10.0


def field_band(band):
    return band.replace("(InGaAs)", "_InGaAs")


def label_to_band(label, path):
    ingaas = label.endswith("In")
    nm = float(label.removesuffix("In")) * 1000.0
    candidates = [b for b in V_BANDS if b.endswith("(InGaAs)") == ingaas]
    band = min(candidates, key=lambda b: abs(float(b.removesuffix("(InGaAs)")) - nm))
    if abs(float(band.removesuffix("(InGaAs)")) - nm) > WAVELENGTH_TOL_NM:
        raise ValueError(f"Wavelength label {label!r} in {path} is not near any CSV band")
    return band


def read_instrument_site(path):
    """The first two lines of the AERONET CSV: 'Instrument: 905' and 'Site: NASA_Ames'."""
    with open(path) as fh:
        instrument = fh.readline().split(":", 1)[1].strip()
        site = fh.readline().split(":", 1)[1].strip()
    return instrument, site


def parse_calibrs_file(path):
    """Parse calibrs_for_<instrument>.txt. Returns {band: {"V0": , "A": , "B": }} and the raw text."""
    with open(path) as fh:
        text = fh.read()

    coeffs = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("Wave("):
            in_table = True
            continue
        if not in_table or line.strip() == "":
            continue
        # Sky_A/Sky_K are blank for some bands, so split on tabs and take V0 from
        # the front and A/B from the back.
        parts = [p.strip() for p in line.split("\t")]
        band = label_to_band(parts[0], path)
        if band in coeffs:
            raise ValueError(f"Two rows map to band {band} in {path}")
        coeffs[band] = {
            "V0": float(parts[1]),
            "A": float(parts[-2]),
            "B": float(parts[-1]),
        }

    missing = set(V_BANDS) - set(coeffs)
    if missing:
        raise ValueError(f"No temperature coefficients for bands {sorted(missing)} in {path}")
    return coeffs, text


def temperature_correct(arr, coeffs):
    """Apply the correction in place to every V1/V2/V3 field."""
    dt = arr["temperature"] - T_REF
    for band in V_BANDS:
        a, b = coeffs[band]["A"], coeffs[band]["B"]
        factor = 1.0 + dt * a + dt ** 2 * b
        for i in (1, 2, 3):
            f = f"V{i}_{field_band(band)}"
            arr[f] = arr[f] / factor


def main():
    script_dir = Path(__file__).resolve().parent
    # the site's export, whatever it is named (NASA_Ames_905_raw_and_aod.csv,
    # San_Luis_Obispo_608_raw_and_aod.xls, ...):
    matches = sorted((script_dir / "202609").glob("*_raw_and_aod.*"))
    default_input = matches[0] if matches else None

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input_csv", nargs="?", default=default_input,
                   help="AERONET CSV, tab-separated even when named .xls (default: %(default)s)")
    p.add_argument("-o", "--output", default=None,
                   help="Output path (default: <input_stem>_tempcorr.npz next to input)")
    p.add_argument("--calib", default=None,
                   help="Temperature coefficient file (default: calibrs_for_<instrument>.txt next to input)")
    p.add_argument("--type", choices=["sun", "moon", "both"], default="sun",
                   help="Filter by observation type (default: sun)")
    p.add_argument("--level", action="append", default=None,
                   help="Level to keep; repeatable. Default: L1.5V")
    args = p.parse_args()

    if args.input_csv is None:
        p.error("no *_raw_and_aod.* file in 202609/; pass input_csv")
    input_csv = Path(args.input_csv)
    instrument, site = read_instrument_site(input_csv)
    calib_path = Path(args.calib) if args.calib else input_csv.parent / f"calibrs_for_{instrument}.txt"
    output_path = Path(args.output) if args.output else input_csv.with_name(input_csv.stem + "_tempcorr.npz")
    levels = set(args.level) if args.level else {"L1.5V"}
    type_filter = None if args.type == "both" else {args.type}

    date_range, _header, rows = parse_csv(input_csv, type_filter, levels)
    arr = np.array(rows, dtype=build_dtype())

    n_no_temp = int(np.isnan(arr["temperature"]).sum())
    if n_no_temp:
        sys.stderr.write(f"warning: {n_no_temp} rows have no Temperature; their V values become NaN\n")

    coeffs, calib_text = parse_calibrs_file(calib_path)
    temperature_correct(arr, coeffs)

    metadata = {
        "SOURCE_CSV": os.path.abspath(input_csv),
        "SOURCE_CSV_DATE_RANGE": date_range,
        "INSTRUMENT": instrument,
        "SITE": site,
        "DATETIME_TZ": "UTC",
        "FILTER_TYPE": args.type,
        "FILTER_LEVEL": sorted(levels),
        "TEMP_CORR_FILE": os.path.abspath(calib_path),
        "TEMP_CORR_FORMULA": "Vcorr = Vmeas / (1 + (t - 25) * A + (t - 25)^2 * B)",
        "TEMP_CORR_BASELINE": T_REF,
        "TEMP_CORR_COEFFS": coeffs,
        "TEMP_CORR_FILE_TEXT": calib_text,
        "PROCESSING_TIME": datetime.now(timezone.utc).isoformat(),
        "N_ROWS": int(arr.shape[0]),
    }

    with open(output_path, "bw") as arrayfile:
        np.savez(arrayfile, array_data=arr, metadata=metadata)

    print(f"input:     {input_csv}")
    print(f"calib:     {calib_path}")
    print(f"output:    {output_path}")
    print(f"filters:   type={args.type}, level={sorted(levels)}")
    print(f"rows kept: {arr.shape[0]}")
    if arr.size:
        print(f"time span: {arr['datetime'][0]} -> {arr['datetime'][-1]} UTC")
        print(f"temp span: {np.nanmin(arr['temperature']):.1f} -> {np.nanmax(arr['temperature']):.1f} C")


if __name__ == "__main__":
    main()
