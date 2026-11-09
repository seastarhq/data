#!/usr/bin/env python3
"""Plot the SeaSTAR L1.0 AOD against the AERONET AOD, one day at a time.

Reads one AERONET site's temperature-corrected npz (read_aeronet_tempcorr.py) and the .L10 files of the
SeaSTAR campaigns made beside it (L06-to-L10_sun.py), and writes, to --outdir, for each day of SeaSTAR data
(the date in the L10 file names):
  - aod_<site>_<date>_timeseries.png: for each wavelength the two share, the SeaSTAR AOD of the timesteps
    with no aod_flags, and AERONET's AOD, against time
  - aod_<site>_<date>_scatter.png: for each wavelength, the SeaSTAR AOD averaged over the unflagged
    timesteps within --window-seconds of each AERONET observation, against AERONET's, with the 1:1 line,
    the median difference and its rms
and --table, the matched statistics of every day and wavelength. --tag is added to the plots' names
(e.g. _v0origin, for L10 files processed with V0_MODE=origin); the V0 mode is in their titles.

These are the days the SeaSTAR V0s were transferred from AERONET on (calibration_vs_ref/fits/v0_seastar.txt),
so agreement here checks the chain (temperature correction, intercept, gas and Rayleigh terms, airmasses)
rather than the calibration: it is not an independent validation.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from match_aeronet_seastar import load_aeronet
from plot_matched import source_day, style_panel, SEASTAR_COLOUR, AERONET_COLOUR

AERONET_NM = (340, 380, 440, 500, 675, 870, 1020)  # the Si wavelengths with an AOD


def load_l10(paths):
    """The L10 arrays of one day, joined, the wavelengths with an AOD, and the V0 mode they were processed with."""
    arrays, wavelengths, modes = [], set(), set()
    for path in paths:
        z = np.load(path, allow_pickle=True)
        arrays.append(z["array_data"])
        wavelengths |= set(z["metadata"][()]["AOD_WAVELENGTHS_NM"].values())
        modes.add(z["metadata"][()].get("V0_MODE", "intercept"))
    if len(modes) > 1:
        raise SystemExit(f"{', '.join(paths)} were processed with different V0 modes: {', '.join(sorted(modes))}")
    return np.concatenate(arrays), sorted(nm for nm in wavelengths if nm in AERONET_NM), modes.pop()


def local_times(times, timezone):
    # pandas can't always find time zones by name, so timezone is a pytz object
    return pd.to_datetime(times).tz_localize("UTC").tz_convert(timezone).tz_localize(None)


def match(seastar_times, seastar_aod, aeronet_times, half_width):
    """The mean of the finite SeaSTAR AODs within half_width of each AERONET time, and how many there were."""
    order = np.argsort(seastar_times)
    t, aod = seastar_times[order], seastar_aod[order]
    lo = np.searchsorted(t, aeronet_times - half_width, side="left")
    hi = np.searchsorted(t, aeronet_times + half_width, side="right")
    means, counts = np.full(len(aeronet_times), np.nan), np.zeros(len(aeronet_times), dtype=int)
    for i, (a, b) in enumerate(zip(lo, hi)):
        window = aod[a:b][np.isfinite(aod[a:b])]
        if len(window):
            means[i], counts[i] = window.mean(), len(window)
    return means, counts


def panels(n):
    columns = 4
    rows = (n + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(4.4 * columns, 3.6 * rows + 1.0), squeeze=False)
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    return fig, list(axes.flat[:n])


def plot_day(site, day, l10, aeronet, wavelengths, half_width, timezone, outdir, v0_mode, tag):
    """Write the day's two plots, and return its matched statistics as table lines."""
    good = l10["aod_flags"] == 0
    s_times = l10["datetime"][good].astype("datetime64[ms]")
    # the AERONET observations within the day's SeaSTAR data
    a_times = aeronet["datetime"].astype("datetime64[ms]")
    in_day = (a_times >= l10["datetime"].min() - half_width) & (a_times <= l10["datetime"].max() + half_width)
    aeronet = aeronet[in_day]
    a_times = a_times[in_day]

    stats, matched = [], {}
    fig, axes = panels(len(wavelengths))
    for ax, nm in zip(axes, wavelengths):
        s_aod, a_aod = l10[f"aod_{nm}nm"][good], aeronet[f"AOD_{nm}"]
        a_ok = np.isfinite(a_aod) & (a_aod > 0)
        ax.plot(local_times(s_times, timezone), s_aod, ".", color=SEASTAR_COLOUR, markersize=1.5, alpha=0.5,
                label="SeaSTAR L1.0, unflagged")
        ax.plot(local_times(a_times[a_ok], timezone), a_aod[a_ok], "s", color=AERONET_COLOUR, markersize=5,
                markeredgecolor="white", markeredgewidth=0.6, label="AERONET")
        values = np.concatenate([s_aod[np.isfinite(s_aod)], a_aod[a_ok]])
        if len(values):
            lo, hi = np.percentile(values, [0.5, 99.5])
            pad = 0.1 * (hi - lo) + 0.005
            ax.set_ylim(lo - pad, hi + pad)

        means, counts = match(s_times, s_aod, a_times, half_width)
        ok = a_ok & (counts > 0)
        matched[nm] = (a_aod[ok], means[ok])
        diff = means[ok] - a_aod[ok]
        if ok.any():
            stats.append(f"  {site:16s} {day} {v0_mode:9s} {nm:5d} {ok.sum():4d} {np.median(a_aod[ok]):8.4f} {np.median(means[ok]):8.4f}"
                         f" {np.median(diff):+9.4f} {np.sqrt(np.mean(diff ** 2)):8.4f}")
        ax.set_title(f"{nm} nm", loc="left", fontsize=9)
        ax.set_ylabel("AOD", fontsize=8)
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_xlabel(f"time ({timezone.zone})", fontsize=8)
        ax.tick_params(labelsize=7.5)
        style_panel(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    legend = fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2, frameon=False,
                        fontsize=9, markerscale=4)
    for handle in legend.legend_handles:
        handle.set_alpha(1)
    fig.suptitle(f"{site}, {day}: SeaSTAR L1.0 AOD ({v0_mode} V0) and AERONET AOD", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    path = Path(outdir) / f"aod_{site}{tag}_{day}_timeseries.png"
    fig.savefig(path, dpi=120)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
    print(f"  plot: {path}")

    fig, axes = panels(len(wavelengths))
    for ax, nm in zip(axes, wavelengths):
        a_aod, s_aod = matched[nm]
        if len(a_aod):
            lo, hi = min(a_aod.min(), s_aod.min()), max(a_aod.max(), s_aod.max())
            pad = 0.1 * (hi - lo) + 0.005
            ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.6", linewidth=1, linestyle="--",
                    label="1:1")
            ax.scatter(a_aod, s_aod, s=18, color=SEASTAR_COLOUR, edgecolors="white", linewidths=0.5,
                       label=f"SeaSTAR mean within ±{half_width.astype(int) / 1000:g} s")
            ax.set_xlim(lo - pad, hi + pad)
            ax.set_ylim(lo - pad, hi + pad)
            diff = s_aod - a_aod
            ax.text(0.97, 0.04, f"n {len(diff)}\nmedian diff {np.median(diff):+.4f}\nrms diff {np.sqrt(np.mean(diff ** 2)):.4f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5)
        else:
            ax.text(0.5, 0.5, "no matches", transform=ax.transAxes, ha="center", va="center", color="#52514e")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{nm} nm", loc="left", fontsize=9)
        ax.set_xlabel("AERONET AOD", fontsize=8)
        ax.set_ylabel("SeaSTAR L1.0 AOD", fontsize=8)
        ax.tick_params(labelsize=7.5)
        style_panel(ax)
    for ax in axes:
        if ax.get_legend_handles_labels()[0]:
            fig.legend(*ax.get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2,
                       frameon=False, fontsize=9)
            break
    fig.suptitle(f"{site}, {day}: SeaSTAR L1.0 AOD ({v0_mode} V0) against AERONET AOD, time matched", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    path = Path(outdir) / f"aod_{site}{tag}_{day}_scatter.png"
    fig.savefig(path, dpi=120)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
    print(f"  plot: {path}")
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aeronet", required=True, help="temperature-corrected AERONET npz from read_aeronet_tempcorr.py")
    p.add_argument("--seastar-l10", action="append", required=True, help="a SeaSTAR .L10 file; repeat for each")
    p.add_argument("--window-seconds", type=float, default=15, help="half-width of the matching window (default 15)")
    p.add_argument("--timezone", default="UTC", help="time zone for the time axes (default: UTC)")
    p.add_argument("--outdir", required=True, help="directory for the plots")
    p.add_argument("--tag", default="", help="added to the plots' names, e.g. _v0origin")
    p.add_argument("--table", required=True, help="the table of matched statistics to write")
    args = p.parse_args()

    aeronet = load_aeronet(args.aeronet)
    data, metadata = aeronet["data"], aeronet["metadata"]
    site = metadata.get("SITE", Path(args.aeronet).stem)
    data = data[data["obs_type"] == "sun"]
    timezone = pytz.timezone(args.timezone)
    half_width = np.timedelta64(int(args.window_seconds * 1000), "ms")

    by_day = {}
    for path in args.seastar_l10:
        by_day.setdefault(source_day(Path(path).name), []).append(path)

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    table = [f"# {site}: SeaSTAR L1.0 AOD (unflagged, mean within ±{args.window_seconds:g} s) against AERONET AOD "
             f"(plot_aod_vs_aeronet.py)",
             f"# {args.aeronet}",
             "# these are the V0 transfer days, so this checks the processing chain, not the calibration",
             f"# {'site':16s} {'day':10s} {'V0 mode':9s} {'nm':>5s} {'n':>4s} {'AERONET':>8s} {'SeaSTAR':>8s} {'med diff':>9s} {'rms diff':>8s}"]
    for day in sorted(by_day):
        l10, wavelengths, v0_mode = load_l10(sorted(by_day[day]))
        table += plot_day(site, day, l10, data, wavelengths, half_width, timezone, args.outdir, v0_mode, args.tag)
    path = Path(args.table)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(table) + "\n")
    print("\n".join(table))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
