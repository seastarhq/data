#!/usr/bin/env python3
"""Plot time-matched AERONET and SeaSTAR temperature-corrected voltages.

Reads a matched pickle written by match_aeronet_seastar.py and writes, to --outdir:
  - matched_<site>_<date>_timeseries.png for each day of SeaSTAR data: for each
    SeaSTAR channel and the AERONET wavelength it is matched to, the SeaSTAR
    windowed mean and the AERONET dropout-screened triplet mean against time.
    The two are in different units (V and counts), so each is shown relative
    to its own median over the day, on one axis.
  - matched_<site>_scatter.png: AERONET triplet mean against SeaSTAR mean for
    each channel, one colour per day.
SeaSTAR channel voltages are negative, so their magnitudes are plotted.
Only matches with at least one usable SeaSTAR sample and a finite AERONET
triplet mean are drawn.
"""

import argparse
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from match_aeronet_seastar import AERONET_WAVELENGTH_LOOKUP, triplet_field

SEASTAR_COLOUR = "#2a78d6"
AERONET_COLOUR = "#eb6834"
# one colour per day on the scatter plots, in a fixed order. three days validate as a set; more
# days than colours would have to be split into separate plots
DAY_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a"]


def matched_pairs(channel_wavelengths):
    """(ch_num, wl, v_stem) for every SeaSTAR channel and AERONET wavelength it is matched to."""
    pairs = []
    for ch, wl in sorted(channel_wavelengths.items()):
        for v_stem, _aod in AERONET_WAVELENGTH_LOOKUP.get(wl, []):
            pairs.append((ch, wl, v_stem))
    return pairs


def pair_label(ch, wl, v_stem):
    return f"ch{ch} ({wl} nm) vs AERONET {v_stem.replace('V*_', '')}"


def pair_values(data, ch, wl, v_stem):
    """|SeaSTAR| mean, AERONET triplet mean, and which rows have both."""
    seastar = np.abs(data[f"seastar_ch{ch}_{wl}nm_mean"])
    aeronet = data[triplet_field(v_stem, "mean")]
    ok = (data[f"seastar_ch{ch}_{wl}nm_n_used"] > 0) & np.isfinite(seastar) & np.isfinite(aeronet)
    return seastar, aeronet, ok


def source_day(source):
    """The date in a SeaSTAR L06 file name, e.g. SeaSTAR_2026-09-25_12-00-54.L06 -> 2026-09-25."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", source)
    return m.group(1) if m else ""


def style_panel(ax):
    ax.grid(True, color="#e1e0d9", linewidth=0.5)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def panel_grid(n):
    """Two columns of panels, filled down the left column first."""
    rows = (n + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(16, 2.6 * rows + 1.5), squeeze=False)
    order = [axes[r, c] for c in range(2) for r in range(rows)]
    for ax in order[n:]:
        ax.set_visible(False)
    return fig, order[:n]


def plot_timeseries(data, pairs, site, day, timezone, outdir):
    # pandas can't always find time zones by name, so timezone is a pytz object
    times = pd.to_datetime(data["aeronet_datetime"]).tz_localize("UTC").tz_convert(timezone).tz_localize(None)
    fig, axes = panel_grid(len(pairs))
    for ax, (ch, wl, v_stem) in zip(axes, pairs):
        seastar, aeronet, ok = pair_values(data, ch, wl, v_stem)
        if ok.any():
            ax.plot(times[ok], seastar[ok] / np.median(seastar[ok]), "o-", color=SEASTAR_COLOUR,
                    markersize=4, linewidth=1, label="SeaSTAR (|V| / median)")
            ax.plot(times[ok], aeronet[ok] / np.median(aeronet[ok]), "s-", color=AERONET_COLOUR,
                    markersize=4, linewidth=1, label="AERONET triplet mean (counts / median)")
        else:
            ax.text(0.5, 0.5, "no matches", transform=ax.transAxes, ha="center", va="center", color="#52514e")
        ax.set_title(pair_label(ch, wl, v_stem), loc="left", fontsize=9)
        ax.set_ylabel("relative to median")
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        style_panel(ax)
    for ax in axes:
        if ax.get_legend_handles_labels()[0]:
            fig.legend(*ax.get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.965),
                       ncol=2, frameon=False, fontsize=9)
            break
    for ax in axes[-2:]:
        ax.set_xlabel(f"time ({timezone.zone})")
    fig.suptitle(f"AERONET {site} and SeaSTAR, time matched, {day}", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = Path(outdir) / f"matched_{site}_{day}_timeseries.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"  plot: {path}")


def plot_scatter(data, pairs, site, days, outdir):
    fig, axes = panel_grid(len(pairs))
    for ax, (ch, wl, v_stem) in zip(axes, pairs):
        seastar, aeronet, ok = pair_values(data, ch, wl, v_stem)
        for day, colour in zip(days, DAY_COLOURS):
            sel = ok & (data["day"] == day)
            if sel.any():
                ax.scatter(aeronet[sel], seastar[sel], s=16, color=colour, label=day,
                           edgecolors="white", linewidths=0.5)
        ax.set_title(pair_label(ch, wl, v_stem), loc="left", fontsize=9)
        ax.set_xlabel("AERONET triplet mean (counts)")
        ax.set_ylabel("SeaSTAR |V|")
        style_panel(ax)
    for ax in axes:
        if ax.get_legend_handles_labels()[0]:
            fig.legend(*ax.get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.965),
                       ncol=len(days), frameon=False, fontsize=9)
            break
    fig.suptitle(f"AERONET {site} against SeaSTAR, time matched", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = Path(outdir) / f"matched_{site}_scatter.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"  plot: {path}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("matched", help="matched pickle written by match_aeronet_seastar.py")
    p.add_argument("--outdir", required=True, help="directory for the plots")
    p.add_argument("--timezone", default="UTC", help="time zone for the time axes (default: UTC)")
    args = p.parse_args()

    with open(args.matched, "rb") as fh:
        matched = pickle.load(fh)
    data, metadata = matched["data"], matched["metadata"]
    site = metadata.get("aeronet_site") or Path(args.matched).stem.replace("matched_", "")
    pairs = matched_pairs(metadata["channel_wavelengths"])
    timezone = pytz.timezone(args.timezone)

    # the day of each match is the day of the SeaSTAR run it was matched to; matches with no
    # SeaSTAR data at all have no day and aren't plotted
    days_of_rows = np.array([source_day(s) for s in data["seastar_source"]])
    data = pd.DataFrame({name: data[name] for name in data.dtype.names}).assign(day=days_of_rows)
    data = data[data["day"] != ""].reset_index(drop=True)
    days = sorted(data["day"].unique())
    if not days:
        sys.exit(f"{args.matched}: no AERONET observations matched any SeaSTAR data")
    if len(days) > len(DAY_COLOURS):
        print(f"warning: {len(days)} days, but only {len(DAY_COLOURS)} colours for the scatter plot; "
              f"plotting the first {len(DAY_COLOURS)}", file=sys.stderr)

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    for day in days:
        day_data = data[data["day"] == day].reset_index(drop=True)
        plot_timeseries(day_data.to_records(index=False), pairs, site, day, timezone, args.outdir)
    plot_scatter(data.to_records(index=False), pairs, site, days[:len(DAY_COLOURS)], args.outdir)


if __name__ == "__main__":
    main()
