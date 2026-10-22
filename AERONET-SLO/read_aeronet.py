#!/usr/bin/env python3
"""Read NASA_Ames_905_raw_and_aod.csv and write a pickled numpy structured array.

The pickle is a dict {"data": structured_array, "metadata": {...}} where metadata
carries the V0 zero-calibration tables (2024 and 2025) plus filter/source info.
"""

import argparse
import csv
import glob
import os
import pickle
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


# Order matches the CSV's V*/AOD columns and is also the bit order in aod_missing_flags.
WAVELENGTH_ORDER = [1020, 1640, 870, 675, 440, 500, "1020_InGaAs", 935, 380, 340]

AOD_FIELDS = [
    "AOD_1020", "AOD_1640", "AOD_870", "AOD_675", "AOD_440",
    "AOD_500", "AOD_1020_InGaAs", "AOD_380", "AOD_340",
]

# CSV header for AOD InGaAs uses parentheses; map to a numpy-safe field name.
AOD_CSV_TO_FIELD = {
    "AOD_1020": "AOD_1020",
    "AOD_1640": "AOD_1640",
    "AOD_870": "AOD_870",
    "AOD_675": "AOD_675",
    "AOD_440": "AOD_440",
    "AOD_500": "AOD_500",
    "AOD_1020(InGaAs)": "AOD_1020_InGaAs",
    "AOD_380": "AOD_380",
    "AOD_340": "AOD_340",
}

V_BANDS = ["1020", "1640", "870", "675", "440", "500", "1020(InGaAs)", "935", "380", "340"]
V_FIELDS = [f"V{i}_{b.replace('(InGaAs)', '_InGaAs')}" for i in (1, 2, 3) for b in V_BANDS]
V_CSV_HEADERS = [f"V{i}_{b}" for i in (1, 2, 3) for b in V_BANDS]

EXPECTED_HEADER = (
    ["Date", "Time", "JDay", "Type"]
    + V_CSV_HEADERS
    + ["Temperature", "offset(sec)", "Level", "Zenith", "AirMass"]
    + ["AOD_1020", "AOD_1640", "AOD_870", "AOD_675", "AOD_440", "AOD_500", "AOD_1020(InGaAs)"]
    + ["Water_Vapor", "AOD_380", "AOD_340", "Alpha"]
)


def build_dtype():
    fields = [
        ("datetime", "datetime64[ms]"),
        ("jday", "f8"),
        ("obs_type", "U4"),
    ]
    fields += [(f, "f8") for f in V_FIELDS]
    fields += [
        ("temperature", "f8"),
        ("offset_sec", "f8"),
        ("level", "U6"),
        ("zenith", "f8"),
        ("airmass", "f8"),
    ]
    fields += [(f, "f8") for f in AOD_FIELDS]
    fields += [
        ("water_vapor", "f8"),
        ("alpha", "f8"),
        ("aod_missing_flags", "i4"),
    ]
    return np.dtype(fields)


def _to_float(s):
    s = s.strip()
    if s == "":
        return np.nan
    return float(s)


def parse_csv(path, type_filter, level_filter):
    """Yield (date_range_str, header, list_of_row_tuples_for_dtype)."""
    with open(path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        line1 = next(reader)  # Instrument: 905
        line2 = next(reader)  # Site: NASA_Ames
        line3 = next(reader)  # date range
        header = next(reader)

        if header != EXPECTED_HEADER:
            extra = set(header) - set(EXPECTED_HEADER)
            missing = set(EXPECTED_HEADER) - set(header)
            raise ValueError(
                f"CSV header does not match expected layout.\n"
                f"  unexpected columns: {sorted(extra)}\n"
                f"  missing columns:    {sorted(missing)}\n"
                f"  got header:         {header}"
            )

        col = {name: i for i, name in enumerate(header)}
        rows = []
        for raw in reader:
            if not raw or all(c.strip() == "" for c in raw):
                continue
            if len(raw) < len(EXPECTED_HEADER):
                raw = raw + [""] * (len(EXPECTED_HEADER) - len(raw))
            obs_type = raw[col["Type"]].strip()
            level = raw[col["Level"]].strip()
            if type_filter is not None and obs_type not in type_filter:
                continue
            if level not in level_filter:
                continue

            dt = datetime.strptime(
                f"{raw[col['Date']].strip()} {raw[col['Time']].strip()}",
                "%b/%d/%Y %H:%M:%S",
            )
            dt64 = np.datetime64(dt, "ms")

            flags = 0
            aod_values = []
            for bit, csv_name in enumerate([
                "AOD_1020", "AOD_1640", "AOD_870", "AOD_675", "AOD_440",
                "AOD_500", "AOD_1020(InGaAs)", "AOD_380", "AOD_340",
            ]):
                v = raw[col[csv_name]].strip()
                if v == "":
                    flags |= (1 << bit)
                    aod_values.append(np.nan)
                else:
                    aod_values.append(float(v))

            row = (
                dt64,
                _to_float(raw[col["JDay"]]),
                obs_type,
                *[_to_float(raw[col[h]]) for h in V_CSV_HEADERS],
                _to_float(raw[col["Temperature"]]),
                _to_float(raw[col["offset(sec)"]]),
                level,
                _to_float(raw[col["Zenith"]]),
                _to_float(raw[col["AirMass"]]),
                *aod_values,
                _to_float(raw[col["Water_Vapor"]]),
                _to_float(raw[col["Alpha"]]),
                flags,
            )
            rows.append(row)

        return line3.strip() if isinstance(line3, str) else "\t".join(line3).strip(), header, rows


def parse_v0_file(path):
    """Parse a V_zero-calibration text file. Returns dict with V0 tables and raw_text."""
    with open(path) as fh:
        text = fh.read()

    lines = text.splitlines()
    table_start = None
    for i, line in enumerate(lines):
        if line.startswith("Wave") and "V0(new)" in line:
            table_start = i + 1
            break
    if table_start is None:
        raise ValueError(f"Could not find 'Wave | V0(new)' table header in {path}")

    rows = []
    for line in lines[table_start:]:
        if line.strip() == "":
            if rows:
                break
            continue
        if "|" not in line:
            break
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            break
        rows.append(parts)
        if len(rows) == 10:
            break

    if len(rows) != 10:
        raise ValueError(
            f"Expected 10 calibration rows in {path}, got {len(rows)}"
        )

    pct = lambda s: float(s.rstrip("%").strip())
    v0_new, v0_prec, diff_pct, diff_per_year_pct = {}, {}, {}, {}
    for key, parts in zip(WAVELENGTH_ORDER, rows):
        v0_new[key] = float(parts[1])
        v0_prec[key] = float(parts[2])
        diff_pct[key] = pct(parts[3])
        diff_per_year_pct[key] = pct(parts[4])

    return {
        "v0_new": v0_new,
        "v0_prec": v0_prec,
        "diff_pct": diff_pct,
        "diff_per_year_pct": diff_per_year_pct,
        "raw_text": text,
    }


def discover_calibrations(input_csv, override_2024, override_2025):
    base_dir = Path(input_csv).parent
    cals = {}
    for year, override in ((2024, override_2024), (2025, override_2025)):
        if override:
            path = override
        else:
            matches = sorted(glob.glob(str(base_dir / f"AERONET-905-V_zero-calibration-{year}.txt")))
            if not matches:
                raise FileNotFoundError(
                    f"No calibration file for {year} found in {base_dir} "
                    f"(pass --cal-{year} to override)"
                )
            path = matches[0]
        cals[year] = parse_v0_file(path)
        cals[year]["source_path"] = os.path.abspath(path)
    return cals


def main():
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "NASA_Ames_905_raw_and_aod.csv"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv", nargs="?", default=str(default_input),
                   help="AERONET CSV (default: %(default)s)")
    p.add_argument("-o", "--output", default=None,
                   help="Output pickle path (default: <input_stem>.pkl next to input)")
    p.add_argument("--type", choices=["sun", "moon", "both"], default="sun",
                   help="Filter by observation type (default: sun)")
    p.add_argument("--level", action="append", default=None,
                   help="Level to keep; repeatable. Default: L1.5V")
    p.add_argument("--cal-2024", default=None, help="Override path to 2024 calibration file")
    p.add_argument("--cal-2025", default=None, help="Override path to 2025 calibration file")
    args = p.parse_args()

    levels = set(args.level) if args.level else {"L1.5V"}
    type_filter = None if args.type == "both" else {args.type}

    output_path = args.output or str(Path(args.input_csv).with_suffix(".pkl"))

    date_range, _header, rows = parse_csv(args.input_csv, type_filter, levels)
    arr = np.array(rows, dtype=build_dtype())

    cals = discover_calibrations(args.input_csv, args.cal_2024, args.cal_2025)

    metadata = {
        "source_csv": os.path.abspath(args.input_csv),
        "source_csv_date_range": date_range,
        "instrument": "905",
        "site": "NASA_Ames",
        "datetime_tz": "UTC",
        "filters_applied": {
            "type": args.type,
            "level": sorted(levels),
        },
        "aod_flag_bits": {bit: AOD_FIELDS[bit] for bit in range(len(AOD_FIELDS))},
        "wavelength_order": WAVELENGTH_ORDER,
        "calibration": cals,
        "n_rows": int(arr.shape[0]),
    }

    with open(output_path, "wb") as fh:
        pickle.dump({"data": arr, "metadata": metadata}, fh, protocol=pickle.HIGHEST_PROTOCOL)

    type_breakdown = dict(zip(*np.unique(arr["obs_type"], return_counts=True))) if arr.size else {}
    level_breakdown = dict(zip(*np.unique(arr["level"], return_counts=True))) if arr.size else {}
    print(f"input:        {args.input_csv}")
    print(f"output:       {output_path}")
    print(f"filters:      type={args.type}, level={sorted(levels)}")
    print(f"rows kept:    {arr.shape[0]}")
    print(f"  by type:    { {str(k): int(v) for k, v in type_breakdown.items()} }")
    print(f"  by level:   { {str(k): int(v) for k, v in level_breakdown.items()} }")
    print(f"calibrations: {sorted(cals.keys())}")


if __name__ == "__main__":
    main()
