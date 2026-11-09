#!/usr/bin/env python3
"""Plot the SeaSTAR L1.0 AOD against the AERONET AOD for every day and site together.

The all-days companion to plot_aod_vs_aeronet.py's aod_<site>_<date>_scatter.png, matched the same way: the
SeaSTAR AOD averaged over the unflagged timesteps within --window-seconds of each AERONET observation. Each
--site names one AERONET site's temperature-corrected npz and the .L10 files of the campaigns made beside it.
Writes:
  - aod_all_days<tag>_scatter.png and .pdf, to --outdir: a panel for each wavelength, with a colour and marker
    for each day, the 1:1 line, and the median difference and rms of all the days pooled
  - --table, the pooled statistics of each wavelength (aod_<site>.txt has them day by day)

These are the days the SeaSTAR V0s were transferred from AERONET on, so as with plot_aod_vs_aeronet.py, agreement
here checks the chain rather than the calibration: it is not an independent validation.
"""

import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from match_aeronet_seastar import load_aeronet
from plot_aod_vs_aeronet import load_l10, match, panels
from plot_matched import source_day, style_panel

# one colour and marker per day, in a fixed order. the five colours pass the palette validator as neighbours but
# not as all pairs, and a scatter plot mixes them all, so the marker has to tell the days apart as well
DAY_STYLES = [("#2a78d6", "o"), ("#eb6834", "s"), ("#1baf7a", "^"), ("#eda100", "D"), ("#e87ba4", "v")]


def matched_day(l10, aeronet, wavelengths, half_width):
    """For each wavelength, the day's AERONET AODs and the SeaSTAR means matched to them."""
    good = l10["aod_flags"] == 0
    s_times = l10["datetime"][good].astype("datetime64[ms]")
    a_times = aeronet["datetime"].astype("datetime64[ms]")
    in_day = (a_times >= l10["datetime"].min() - half_width) & (a_times <= l10["datetime"].max() + half_width)
    aeronet, a_times = aeronet[in_day], a_times[in_day]

    matched = {}
    for nm in wavelengths:
        a_aod = aeronet[f"AOD_{nm}"]
        means, counts = match(s_times, l10[f"aod_{nm}nm"][good], a_times, half_width)
        ok = np.isfinite(a_aod) & (a_aod > 0) & (counts > 0)
        matched[nm] = (a_aod[ok], means[ok])
    return matched


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", nargs="+", action="append", required=True, metavar=("AERONET_NPZ", "L10"),
                   help="an AERONET npz from read_aeronet_tempcorr.py and its .L10 files; repeat for each site")
    p.add_argument("--window-seconds", type=float, default=15, help="half-width of the matching window (default 15)")
    p.add_argument("--outdir", required=True, help="directory for the plot")
    p.add_argument("--tag", default="", help="added to the plot's name, e.g. _v0origin")
    p.add_argument("--table", required=True, help="the table of pooled statistics to write")
    args = p.parse_args()

    half_width = np.timedelta64(int(args.window_seconds * 1000), "ms")
    days, modes = [], set()  # days: (site, day, what was matched on it)
    for npz, *l10_paths in args.site:
        if not l10_paths:
            raise SystemExit(f"--site {npz}: no .L10 files")
        aeronet = load_aeronet(npz)
        site = aeronet["metadata"].get("SITE", Path(npz).stem)
        data = aeronet["data"][aeronet["data"]["obs_type"] == "sun"]
        by_day = {}
        for path in l10_paths:
            by_day.setdefault(source_day(Path(path).name), []).append(path)
        for day in sorted(by_day):
            l10, wavelengths, v0_mode = load_l10(sorted(by_day[day]))
            modes.add(v0_mode)
            days.append((site, day, matched_day(l10, data, wavelengths, half_width)))
    if len(modes) > 1:
        raise SystemExit(f"the .L10 files were processed with different V0 modes: {', '.join(sorted(modes))}")
    if len(days) > len(DAY_STYLES):
        raise SystemExit(f"{len(days)} days, but only {len(DAY_STYLES)} day styles: add to DAY_STYLES")
    v0_mode = modes.pop()

    wavelengths = sorted({nm for _site, _day, matched in days for nm in matched})
    table = [f"# all days: SeaSTAR L1.0 AOD (unflagged, mean within ±{args.window_seconds:g} s) against AERONET AOD "
             f"(plot_aod_scatter_all.py)",
             *[f"# {site} {day}" for site, day, _matched in days],
             "# these are the V0 transfer days, so this checks the processing chain, not the calibration",
             f"# {'V0 mode':9s} {'nm':>5s} {'n':>4s} {'AERONET':>8s} {'SeaSTAR':>8s} {'med diff':>9s} {'rms diff':>8s}"]
    fig, axes = panels(len(wavelengths))
    for ax, nm in zip(axes, wavelengths):
        pairs = [matched.get(nm, (np.empty(0), np.empty(0))) for _site, _day, matched in days]
        a_all = np.concatenate([a for a, _s in pairs])
        s_all = np.concatenate([s for _a, s in pairs])
        if len(a_all):
            lo, hi = min(a_all.min(), s_all.min()), max(a_all.max(), s_all.max())
            pad = 0.1 * (hi - lo) + 0.005
            ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.6", linewidth=1, linestyle="--")
            for (a_aod, s_aod), (colour, marker) in zip(pairs, DAY_STYLES):
                ax.scatter(a_aod, s_aod, s=18, color=colour, marker=marker, edgecolors="white", linewidths=0.5)
            ax.set_xlim(lo - pad, hi + pad)
            ax.set_ylim(lo - pad, hi + pad)
            diff = s_all - a_all
            rms = np.sqrt(np.mean(diff ** 2))
            ax.text(0.97, 0.04, f"n {len(diff)}\nmedian diff {np.median(diff):+.4f}\nrms diff {rms:.4f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5)
            table.append(f"  {v0_mode:9s} {nm:5d} {len(diff):4d} {np.median(a_all):8.4f} {np.median(s_all):8.4f}"
                         f" {np.median(diff):+9.4f} {rms:8.4f}")
        else:
            ax.text(0.5, 0.5, "no matches", transform=ax.transAxes, ha="center", va="center", color="#52514e")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{nm} nm", loc="left", fontsize=9)
        ax.set_xlabel("AERONET AOD", fontsize=8)
        ax.set_ylabel("SeaSTAR L1.0 AOD", fontsize=8)
        ax.tick_params(labelsize=7.5)
        style_panel(ax)

    handles = [Line2D([], [], linestyle="none", marker=marker, color=colour, markeredgecolor="white",
                      markeredgewidth=0.5, markersize=6, label=f"{site} {day}")
               for (site, day, _matched), (colour, marker) in zip(days, DAY_STYLES)]
    handles.append(Line2D([], [], color="0.6", linewidth=1, linestyle="--", label="1:1"))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=len(handles), frameon=False,
               fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    path = Path(args.outdir) / f"aod_all_days{args.tag}_scatter.png"
    fig.savefig(path, dpi=120)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
    print(f"  plot: {path}")

    path = Path(args.table)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(table) + "\n")
    print("\n".join(table))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
