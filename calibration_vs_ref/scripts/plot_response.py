#!/usr/bin/env python3
"""Plot the SeaSTAR voltage against the AERONET voltage for every matched channel.

Reads a matched pickle written by match_aeronet_seastar.py and writes response_<site>.png to
--outdir: |V_SeaSTAR| (darksub_quad) against the AERONET triplet mean for each channel and the
AERONET wavelength it is matched to, with the points coloured by the SeaSTAR channel temperature.
The axes cover the data only. A straight-line fit is drawn, and its intercept is noted, so a response
that isn't proportional (an offset, or compression near the top of the 1x range) shows as a large
intercept. The slope and the rms (the scatter about that line, as a fraction of |V|) are noted too.

With --coeffs (a tempcorr_<site>.txt written by fit_tempcorr.py), it also writes
response_<site>_tempcorr_<method>_<order>.png for the linear and quadratic fits of each --method, with the
SeaSTAR voltages temperature corrected by that site's coefficients:
    Vcorr = V / (1 + A*dT + B*dT^2),   dT = T - TEMPCORR_TREF
Both ch10 panels use the ch10 coefficients, which were fitted against the Si 1020 detector.
"""

import argparse
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fit_tempcorr import pair_data, METHODS, ORDERS
from plot_matched import matched_pairs, pair_label, style_panel

DARK = "darksub_quad"


def read_coeffs(path, site, method, order):
    """TREF and {ch: (A, B)} for one method and order, from a tempcorr_<site>.txt."""
    values = dict(line.strip().split("=", 1) for line in open(path)
                  if "=" in line and not line.startswith("#"))
    stem = f"TEMPCORR_{re.sub(r'[^A-Z0-9]+', '_', site.upper())}_{method.upper()}_{DARK.upper()}_{ORDERS[order]}"
    coeffs = {}
    for key, value in values.items():
        m = re.fullmatch(rf"{stem}_([AB])_CH(\d+)", key)
        if m:
            A, B = coeffs.get(int(m.group(2)), (0.0, 0.0))
            coeffs[int(m.group(2))] = (float(value), B) if m.group(1) == "A" else (A, float(value))
    if not coeffs:
        sys.exit(f"no {stem}_* coefficients in {path}")
    return float(values["TEMPCORR_TREF"]), coeffs


def plot_response(data, pairs, site, outdir, correction=None):
    """correction: None, or (label, filename tag, TREF, {ch: (A, B)})."""
    # one temperature scale for every panel
    temps = np.concatenate([pair_data(data, *pair, DARK)[2][pair_data(data, *pair, DARK)[3]] for pair in pairs])
    vmin, vmax = np.min(temps), np.max(temps)

    columns = 4
    rows = (len(pairs) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(4.4 * columns, 3.8 * rows + 1.0), layout="constrained",
                             squeeze=False)
    for ax in axes.flat[len(pairs):]:
        ax.set_visible(False)
    for ax, (ch, wl, v_stem) in zip(axes.flat, pairs):
        seastar, aeronet, temp, ok = pair_data(data, ch, wl, v_stem, DARK)
        if not ok.any():
            ax.text(0.5, 0.5, "no matches", transform=ax.transAxes, ha="center", va="center", color="#52514e")
            continue
        seastar, aeronet, temp = seastar[ok], aeronet[ok], temp[ok]
        if correction is not None:
            _label, _tag, tref, coeffs = correction
            A, B = coeffs.get(ch, (0.0, 0.0))
            dT = temp - tref
            seastar = seastar / (1.0 + A * dT + B * dT ** 2)
        points = ax.scatter(aeronet, seastar, c=temp, cmap="viridis", vmin=vmin, vmax=vmax, s=14,
                            edgecolors="white", linewidths=0.4)
        x = np.linspace(aeronet.min(), aeronet.max(), 100)
        b, a = np.polyfit(aeronet, seastar, 1)
        rms = np.std(seastar / (a + b * aeronet) - 1.0)
        ax.plot(x, a + b * x, color="0.3", linewidth=1, linestyle="--", label="straight line")
        ax.text(0.97, 0.04, f"slope {b:.3e} V/count\n"
                            f"intercept {a:+.3f} V\n{a / np.mean(seastar) * 100:+.0f}% of mean |V|\n"
                            f"rms {rms * 100:.2f}%\n"
                            f"range: SeaSTAR {seastar.max() / seastar.min():.2f}x,\nAERONET {aeronet.max() / aeronet.min():.2f}x",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5)
        if correction is not None:
            ax.text(0.03, 0.96, f"A {A:+.2e}" + (f"\nB {B:+.1e}" if B else ""), transform=ax.transAxes,
                    ha="left", va="top", fontsize=7.5)
        ax.set_title(f"{pair_label(ch, wl, v_stem)}, n={ok.sum()}", loc="left", fontsize=9)
        ax.set_xlabel("V_AERONET triplet mean (counts)", fontsize=8)
        corrected = "" if correction is None else " temp-corrected"
        ax.set_ylabel(f"|V_SeaSTAR| {DARK}{corrected} (V)", fontsize=8)
        ax.tick_params(labelsize=7.5)
        style_panel(ax)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=1, frameon=False, fontsize=9)
    fig.colorbar(points, ax=axes, shrink=0.5, pad=0.01, label="SeaSTAR channel temperature (°C)")
    if correction is None:
        fig.suptitle(f"{site}: |V_SeaSTAR| against V_AERONET, time matched (no SeaSTAR temperature correction)")
        name = f"response_{site}.png"
    else:
        label, tag, tref, coeffs = correction
        formula = "V / (1 + A·dT + B·dT²)" if any(B for _A, B in coeffs.values()) else "V / (1 + A·dT)"
        fig.suptitle(f"{site}: temperature-corrected |V_SeaSTAR| against V_AERONET, time matched\n"
                     f"{formula}, dT = T − {tref:g} °C, {label}")
        name = f"response_{site}_tempcorr_{tag}.png"

    Path(outdir).mkdir(parents=True, exist_ok=True)
    path = Path(outdir) / name
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"  plot: {path}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("matched", help="matched pickle written by match_aeronet_seastar.py")
    p.add_argument("--outdir", required=True, help="directory for the plots")
    p.add_argument("--coeffs", help="tempcorr_<site>.txt from fit_tempcorr.py, to also plot corrected voltages")
    p.add_argument("--method", choices=METHODS, nargs="+", default=["residual"],
                   help="which fits' coefficients to correct with (default residual)")
    args = p.parse_args()

    with open(args.matched, "rb") as fh:
        matched = pickle.load(fh)
    data, metadata = matched["data"], matched["metadata"]
    site = metadata.get("aeronet_site") or Path(args.matched).stem.replace("matched_", "")
    pairs = matched_pairs(metadata["channel_wavelengths"])

    plot_response(data, pairs, site, args.outdir)
    if args.coeffs:
        for method in args.method:
            for order, name in ORDERS.items():
                tref, coeffs = read_coeffs(args.coeffs, site, method, order)
                label = f"{site} {method} fit, {name.lower()}, {DARK}"
                plot_response(data, pairs, site, args.outdir,
                              (label, f"{method}_{name.lower()}", tref, coeffs))


if __name__ == "__main__":
    main()
