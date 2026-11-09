#!/usr/bin/env python3
"""Check a campaign's L1.0 AOD calculation by running it on AERONET's own voltages and V0s.

For each sun observation in a temperature-corrected AERONET npz (read_aeronet_tempcorr.py), the AOD at
each AERONET wavelength that a SeaSTAR channel shares is calculated the way L06-to-L10_sun.py does it,
with the campaign's seastar_atmosphere.py (from --l10-scripts) and its gas settings, and compared with
the AOD AERONET reports:

    ln(V0 / (d^2 * V)) = m_R*tau_R + m_a*AOD + m_O3*tau_O3 + m_NO2*tau_NO2

V is the dropout-screened mean of the V1/V2/V3 triplet (as match_aeronet_seastar.py makes it), V0 is from
the calibration file the npz records, d is the earth-sun distance, and the airmasses are from AERONET's
solar zenith. AERONET's voltages are proportional to the sun, so there is no intercept. tau_R is scaled
by --pressure, the site's surface pressure in hPa (AERONET uses the day's NCEP pressure, which isn't in
the export: a 1% error in it moves the AOD by about 0.007 at 340 nm and 0.002 at 440 nm).

The gas settings and the channel wavelengths are read from the environment, so the campaign's
L1.0/setup/parameters.sh and channel_wavelengths.sh are sourced first (the Makefile's `closure` target
does this):
    OZONE_COLUMN_DU NO2_COLUMN_DU AIRMASS_OZONE_HEIGHT_KM AIRMASS_NO2_HEIGHT_KM
    OZONE_XSEC_CH<n> NO2_XSEC_CH<n> CH<n>_NM
Only the gas and Rayleigh terms and the airmasses are tested: the SeaSTAR calibration and temperature
correction are not. The differences left are those terms' errors, plus the difference between the
ozone and NO2 columns assumed here and the ones AERONET used, plus the pressure.

Output: -o, a table of mine - AERONET for each wavelength (median, interquartile range, and the slope
against aerosol airmass, which an airmass-independent offset in the gas terms would not show), and
--plot, the differences against airmass.
"""

import argparse
import importlib
import os
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from match_aeronet_seastar import load_aeronet, triplet_mean
from plot_matched import style_panel
from transfer_v0 import read_v0

AERONET_NM = (340, 380, 440, 500, 675, 870, 1020)  # the Si wavelengths; 935 is water vapour, 1640 has no SeaSTAR channel


def gas_settings():
    """{nm: (ozone xsec, NO2 xsec)} for each SeaSTAR channel with cross-sections, and the columns and layer heights."""
    xsec = {}
    for ch in range(1, 11):
        if f"OZONE_XSEC_CH{ch}" in os.environ and os.environ.get(f"CH{ch}_NM"):
            xsec[int(float(os.environ[f"CH{ch}_NM"]))] = (float(os.environ[f"OZONE_XSEC_CH{ch}"]),
                                                          float(os.environ[f"NO2_XSEC_CH{ch}"]))
    if not xsec:
        sys.exit("no OZONE_XSEC_CH<n> and CH<n>_NM in the environment: source the campaign's L1.0/setup/parameters.sh "
                 "and channel_wavelengths.sh first")
    return xsec, {name: float(os.environ[name]) for name in
                  ("OZONE_COLUMN_DU", "NO2_COLUMN_DU", "AIRMASS_OZONE_HEIGHT_KM", "AIRMASS_NO2_HEIGHT_KM")}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("aeronet", help="temperature-corrected AERONET npz from read_aeronet_tempcorr.py")
    p.add_argument("--pressure", type=float, required=True, help="the site's surface pressure, hPa")
    p.add_argument("--l10-scripts", required=True, help="the campaign's L1.0/scripts, for seastar_atmosphere.py")
    p.add_argument("--dropout-fraction", type=float, default=0.8,
                   help="triplet members below this fraction of the triplet median are left out (default 0.8)")
    p.add_argument("-o", "--output", required=True, help="the table to write")
    p.add_argument("--plot", help="the plot of the differences against airmass to write")
    args = p.parse_args()

    sys.path.insert(0, str(Path(args.l10_scripts).resolve()))
    atm = importlib.import_module("seastar_atmosphere")
    xsec, gas = gas_settings()

    aeronet = load_aeronet(args.aeronet)
    data, metadata = aeronet["data"], aeronet["metadata"]
    site = metadata.get("SITE", Path(args.aeronet).stem)
    data = data[data["obs_type"] == "sun"]
    v0 = read_v0(metadata["TEMP_CORR_FILE"])

    zenith = data["zenith"]
    # the distance doesn't depend on the position, so any will do
    _elev, distance = atm.solar_position(data["datetime"], 0.0, 0.0)
    m_rayleigh = atm.airmass_rayleigh(zenith)
    m_aerosol = atm.airmass_aerosol(zenith)
    m_ozone = atm.airmass_layer(zenith, gas["AIRMASS_OZONE_HEIGHT_KM"])
    m_no2 = atm.airmass_layer(zenith, gas["AIRMASS_NO2_HEIGHT_KM"])

    wavelengths = [nm for nm in AERONET_NM if nm in xsec]
    table = [f"# {site}: the L1.0 AOD calculation ({Path(args.l10_scripts).resolve().parent.parent.name}) on AERONET's "
             f"voltages and V0s (aeronet_aod_closure.py)",
             f"# {args.aeronet}",
             f"# V0 from {metadata['TEMP_CORR_FILE']}",
             f"# pressure {args.pressure:g} hPa, ozone {gas['OZONE_COLUMN_DU']:g} DU, NO2 {gas['NO2_COLUMN_DU']:g} DU, "
             f"{len(data)} sun observations, {str(data['datetime'].min())[:16]} to {str(data['datetime'].max())[:16]} UTC",
             "# diff = mine - AERONET. slope is d(diff)/d(aerosol airmass); airmass "
             f"{m_aerosol.min():.2f}-{m_aerosol.max():.2f}",
             f"# {'nm':>5s} {'n':>5s} {'AERONET AOD':>11s} {'tau_R':>7s} {'tau_O3':>7s} {'tau_NO2':>7s}"
             f" {'median diff':>11s} {'iqr':>17s} {'slope':>8s}"]
    diffs = {}
    for nm in wavelengths:
        v_stem = f"V*_{nm}"
        volts = np.array([triplet_mean(row, v_stem, args.dropout_fraction)[0] for row in data])
        tau_r = atm.tau_rayleigh(nm, args.pressure)
        tau_o3 = atm.tau_gas(gas["OZONE_COLUMN_DU"], xsec[nm][0])
        tau_no2 = atm.tau_gas(gas["NO2_COLUMN_DU"], xsec[nm][1])
        with np.errstate(invalid="ignore", divide="ignore"):
            slant = np.log(v0[v_stem] / (distance ** 2 * volts))
        mine = (slant - m_rayleigh * tau_r - m_ozone * tau_o3 - m_no2 * tau_no2) / m_aerosol
        theirs = data[f"AOD_{nm}"]
        ok = np.isfinite(mine) & np.isfinite(theirs) & (theirs > 0)
        diff = mine[ok] - theirs[ok]
        diffs[nm] = (m_aerosol[ok], diff)
        slope = np.polyfit(m_aerosol[ok], diff, 1)[0] if ok.sum() > 2 else np.nan
        q1, q3 = np.percentile(diff, [25, 75]) if ok.any() else (np.nan, np.nan)
        table.append(f"  {nm:5d} {ok.sum():5d} {np.median(theirs[ok]):11.4f} {tau_r:7.4f} {tau_o3:7.4f} {tau_no2:7.4f}"
                     f" {np.median(diff):+11.4f} {q1:+8.4f}..{q3:+8.4f} {slope:+8.4f}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(table) + "\n")
    print("\n".join(table))
    print(f"wrote {args.output}")

    if args.plot:
        fig, axes = plt.subplots(2, (len(wavelengths) + 1) // 2, figsize=(3.6 * ((len(wavelengths) + 1) // 2), 6.4),
                                 squeeze=False, sharex=True)
        for ax in axes.flat[len(wavelengths):]:
            ax.set_visible(False)
        for ax, nm in zip(axes.flat, wavelengths):
            airmass, diff = diffs[nm]
            ax.axhline(0, color="0.6", linewidth=0.8)
            ax.scatter(airmass, diff, s=8, color="#2a78d6", edgecolors="none")
            ax.set_title(f"{nm} nm, median {np.median(diff):+.4f}", loc="left", fontsize=9)
            ax.set_xlabel("aerosol airmass", fontsize=8)
            ax.set_ylabel("AOD mine − AERONET", fontsize=8)
            ax.tick_params(labelsize=7.5)
            style_panel(ax)
        fig.suptitle(f"{site}: the L1.0 AOD calculation on AERONET's voltages, against AERONET's AOD "
                     f"({args.pressure:g} hPa, O3 {gas['OZONE_COLUMN_DU']:g} DU)")
        fig.tight_layout()
        Path(args.plot).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.plot, dpi=110)
        fig.savefig(Path(args.plot).with_suffix(".pdf"))
        plt.close(fig)
        print(f"  plot: {args.plot}")


if __name__ == "__main__":
    main()
