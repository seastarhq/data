#!/usr/bin/env python3
"""Plot time series from an AERONET *_tempcorr.npz written by read_aeronet_tempcorr.py.

Four figures, saved as <npz_stem>_<name>.png:

    voltages   V1/V2/V3 for each channel, one panel per channel
    geometry   temperature, solar zenith angle and airmass
    aod        AOD for each channel, one panel per channel
    wv_alpha   water vapor and Angstrom exponent

The voltages in the npz are already temperature-corrected to 25 C. Lines are
broken across gaps longer than --gap-hours so nights are not drawn as data.
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import numpy as np

from read_aeronet import AOD_FIELDS, V_BANDS
from read_aeronet_tempcorr import field_band


# V1/V2/V3 are the triplet's three readings; marker shape repeats the colour so
# they can be told apart without it.
TRIPLET_STYLE = {
    1: {"color": "#2a78d6", "marker": "o"},
    2: {"color": "#eb6834", "marker": "s"},
    3: {"color": "#1baf7a", "marker": "^"},
}
SINGLE_COLOR = "#2a78d6"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"


def band_label(band):
    if band.endswith("(InGaAs)"):
        return f"{band.removesuffix('(InGaAs)')} nm InGaAs"
    return f"{band} nm"


def aod_label(field):
    band = field.removeprefix("AOD_")
    if band.endswith("_InGaAs"):
        return f"{band.removesuffix('_InGaAs')} nm InGaAs"
    return f"{band} nm"


def break_gaps(t, y, gap):
    """Insert NaNs where consecutive times are more than gap apart."""
    idx = np.flatnonzero(np.diff(t) > gap) + 1
    if idx.size == 0:
        return t, y
    return np.insert(t, idx, t[idx - 1] + gap / 2), np.insert(y, idx, np.nan)


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_SECONDARY, labelsize=8)
    ax.yaxis.label.set_color(INK_SECONDARY)
    ax.title.set_color(INK)


def plot_series(ax, t, y, gap, color=SINGLE_COLOR, marker="o", label=None):
    tt, yy = break_gaps(t, y, gap)
    ax.plot(tt, yy, color=color, linewidth=1.0, alpha=0.6)
    ax.plot(t, y, linestyle="none", marker=marker, markersize=3.5,
            color=color, markeredgecolor=SURFACE, markeredgewidth=0.5, label=label)


def new_figure(plt, nrows, ncols, title, subtitle):
    fig, axes = plt.subplots(nrows, ncols, sharex=True, squeeze=False,
                             figsize=(6.5 * ncols, 2.0 * nrows + 1.0),
                             layout="constrained")
    fig.patch.set_facecolor(SURFACE)
    fig.suptitle(f"{title}\n{subtitle}", color=INK, fontsize=11)
    for ax in axes.flat:
        style_axes(ax)
    locator = mdates.AutoDateLocator()
    for ax in axes[-1]:
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_xlabel("UTC", color=INK_SECONDARY, fontsize=8)
    return fig, axes


def plot_voltages(plt, d, gap, title, subtitle):
    ncols = 2
    nrows = -(-len(V_BANDS) // ncols)
    fig, axes = new_figure(plt, nrows, ncols, f"{title}: voltages, temperature-corrected to 25 °C", subtitle)
    for ax, band in zip(axes.flat, V_BANDS):
        for i, style in TRIPLET_STYLE.items():
            plot_series(ax, d["datetime"], d[f"V{i}_{field_band(band)}"], gap, label=f"V{i}", **style)
        ax.set_title(band_label(band), fontsize=9, loc="left")
        ax.set_ylabel("counts", fontsize=8)
    for ax in axes.flat[len(V_BANDS):]:
        ax.set_visible(False)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper right", ncols=3, frameon=False,
               fontsize=9, labelcolor=INK_SECONDARY)
    return fig


def plot_single_panels(plt, d, gap, title, subtitle, panels, ncols=1):
    """panels: list of (field, panel title, y label)."""
    nrows = -(-len(panels) // ncols)
    fig, axes = new_figure(plt, nrows, ncols, title, subtitle)
    for ax, (field, panel_title, ylabel) in zip(axes.flat, panels):
        plot_series(ax, d["datetime"], d[field], gap)
        ax.set_title(panel_title, fontsize=9, loc="left")
        ax.set_ylabel(ylabel, fontsize=8)
    for ax in axes.flat[len(panels):]:
        ax.set_visible(False)
    return fig


def main():
    script_dir = Path(__file__).resolve().parent
    matches = sorted((script_dir / "202609").glob("*_tempcorr.npz"))
    default_input = matches[0] if matches else None

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("npz", nargs="?", default=default_input,
                   help="npz from read_aeronet_tempcorr.py (default: %(default)s)")
    p.add_argument("--outdir", default=None,
                   help="Where to write the PNGs (default: plots/ next to the npz)")
    p.add_argument("--gap-hours", type=float, default=1.0,
                   help="Break lines across gaps longer than this (default: %(default)s)")
    p.add_argument("--show", action="store_true", help="Open the figures as well as saving them")
    args = p.parse_args()

    if args.npz is None:
        p.error("no 202609/*_tempcorr.npz found; pass the npz path")
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    npz = Path(args.npz)
    z = np.load(npz, allow_pickle=True)
    d, metadata = z["array_data"], z["metadata"][()]
    if d.size == 0:
        sys.exit(f"{npz} has no rows")

    outdir = Path(args.outdir) if args.outdir else npz.parent / "plots"
    outdir.mkdir(parents=True, exist_ok=True)
    gap = np.timedelta64(int(args.gap_hours * 3600 * 1000), "ms")

    title = f"AERONET {metadata['SITE']} #{metadata['INSTRUMENT']}"
    subtitle = (f"type={metadata['FILTER_TYPE']}, level={','.join(metadata['FILTER_LEVEL'])}, "
                f"{d.size} obs, {npz.name}")

    figures = {
        "voltages": plot_voltages(plt, d, gap, title, subtitle),
        "geometry": plot_single_panels(plt, d, gap, f"{title}: temperature and geometry", subtitle, [
            ("temperature", "Temperature", "°C"),
            ("zenith", "Solar zenith angle", "degrees"),
            ("airmass", "Airmass", ""),
        ]),
        "aod": plot_single_panels(plt, d, gap, f"{title}: aerosol optical depth", subtitle,
                                  [(f, aod_label(f), "AOD") for f in AOD_FIELDS], ncols=2),
        "wv_alpha": plot_single_panels(plt, d, gap, f"{title}: water vapor and Angstrom exponent", subtitle, [
            ("water_vapor", "Water vapor", "cm"),
            ("alpha", "Angstrom exponent (alpha)", ""),
        ]),
    }

    for name, fig in figures.items():
        out = outdir / f"{npz.stem}_{name}.png"
        fig.savefig(out, dpi=150, facecolor=SURFACE)
        print(out)

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
