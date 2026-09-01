#!/usr/bin/env python3
# read the pickled 1-second averages and make quicklook time series plots of the
# block temperatures and of the J3 radiometer channels at each gain setting.

import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

TEMP_COLUMNS = ["Temp1", "Temp2", "Temp3", "Temp4"]
GAIN_COLUMNS = {"0": ["J3_CH1_0", "J3_CH2_0", "J3_CH3_0", "J3_CH4_0", "J3_CH5_0"],
                "2": ["J3_CH1_2", "J3_CH2_2", "J3_CH3_2", "J3_CH4_2", "J3_CH5_2"]}

# the temperatures we show underneath each channel figure, so that channel drift
# can be read against the heating and cooling of the instrument:
CONTEXT_TEMPS = ["Temp3", "Temp4"]

# one colour per channel, used consistently in every figure, from a
# colourblind-safe categorical palette (blue, orange, aqua, yellow, magenta):
CHANNEL_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

# the flags from the notes are drawn as background bands, so they stay behind
# the data: a warm wash while the heater was on, a grey one over anything that
# upset the measurement, a cool one while the lamp was off. each band is hatched
# differently as well as coloured differently, so they are still told apart in
# greyscale or in print:
BAND_STYLES = {
        "heater on": dict(facecolor="#f6c9a8", alpha=0.55, linewidth=0),
        "disturbance (see labels above)": dict(facecolor="#d9d8d4", alpha=0.7,
                                               edgecolor="white", hatch="///",
                                               linewidth=0),
        "lamp off": dict(facecolor="#aec4dd", alpha=0.6,
                         edgecolor="white", hatch="..",
                         linewidth=0),
        }

TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID_COLOUR = "#d9d8d4"
CONTEXT_BACKGROUND = "#f7f6f4"

# a single spike (a dark, a power cycle) otherwise flattens a whole panel, so by
# default we scale to this quantile range and say how many points fall outside:
YLIM_QUANTILE = 0.001


def event_spans(series):
    """Group a flag column into (start, end, label) runs.

    Takes a boolean column, or the disturbance column, where a run is labelled
    with every disturbance named in it.
    """
    flagged = series.astype(bool) if series.dtype == bool else (series != "")
    if not flagged.any():
        return []

    # a run ends where the flag turns off, so number the runs and group by that:
    runs = (flagged != flagged.shift()).cumsum()[flagged]
    sample = series.index.to_series().diff().median()

    spans = []
    for _, run in series[flagged].groupby(runs):
        if series.dtype == bool:
            label = ""
        else:
            names = {name for value in run for name in value.split(",")}
            label = " + ".join(sorted(names))
        spans.append((run.index[0], run.index[-1] + sample, label))

    return spans


def event_bands(df):
    """Work out the bands to draw, from whichever flags this pickle carries."""
    bands = []
    if "heater_on" in df.columns:
        bands.append(("heater on", event_spans(df["heater_on"])))
    if "lamp_on" in df.columns:
        bands.append(("lamp off", event_spans(~df["lamp_on"])))
    if "disturbance" in df.columns:
        bands.append(("disturbance (see labels above)",
                      event_spans(df["disturbance"])))
    return [(label, spans) for label, spans in bands if spans]


def shade_events(ax, bands):
    """Draw the bands behind one panel."""
    for label, spans in bands:
        for start, end, _ in spans:
            ax.axvspan(start, end, zorder=0, **BAND_STYLES[label])


def label_disturbances(ax, disturbances):
    """Name each disturbance in the margin above the top panel.

    Two disturbances close together would write over each other, so labels that
    would collide go on a second row.
    """
    left, right = ax.get_xlim()
    previous = None

    for start, end, label in disturbances:
        middle = start + (end - start) / 2
        # where this label sits across the panel, 0 to 1:
        position = (mdates.date2num(middle) - left) / (right - left)
        crowded = previous is not None and position - previous < 0.06
        row = 1.13 if crowded else 1.04
        previous = position

        ax.text(middle, row, label, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=7, color=TEXT_SECONDARY)


def event_legend(fig, bands):
    """A key for the bands: identity is never colour alone."""
    handles = [Patch(label=label, **BAND_STYLES[label]) for label, _ in bands]
    if handles:
        fig.legend(handles=handles, loc="upper right", frameon=False, fontsize=8,
                   labelcolor=TEXT_SECONDARY, ncol=len(handles),
                   bbox_to_anchor=(0.995, 1.0))


def find_pickle(pickle_dir):
    """Return the most recent pickle file in pickle_dir."""
    pickles = sorted(glob.glob(os.path.join(pickle_dir, "*.pkl")),
                     key=os.path.getmtime)
    if not pickles:
        sys.stderr.write(f"no pickle files found in {pickle_dir}\n")
        sys.exit(1)
    return pickles[-1]


def set_ylim(ax, series):
    """Scale the panel to the bulk of the data, flagging anything off-scale."""
    low, high = series.quantile([YLIM_QUANTILE, 1 - YLIM_QUANTILE])
    if not (low < high):
        return

    margin = 0.05 * (high - low)
    ax.set_ylim(low - margin, high + margin)

    offscale = int(((series < low - margin) | (series > high + margin)).sum())
    if offscale:
        ax.text(0.995, 0.94, f"{offscale} points off-scale",
                transform=ax.transAxes, va="top", ha="right", fontsize=8,
                color=TEXT_SECONDARY)


def style_panel(ax, label, colour):
    """Recessive grid and axes, with the series named on the panel itself."""
    ax.grid(True, color=GRID_COLOUR, linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8, colors=TEXT_SECONDARY)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID_COLOUR)
    # direct label on the panel: identity is never colour alone
    ax.text(0.005, 0.94, label, transform=ax.transAxes, va="top", ha="left",
            fontsize=9, color=TEXT_PRIMARY,
            bbox=dict(facecolor="white", edgecolor=colour, linewidth=1.0,
                      boxstyle="round,pad=0.25", alpha=0.85))


def format_time_axis(ax, df):
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel(f"time on {df.index[0].date()}", color=TEXT_SECONDARY,
                  fontsize=9)


def stacked_figure(df, columns, colours, title, ylabel,
                   contextpanels=0, fullrange=False):
    """One panel per column, all sharing the time axis.

    Separate panels rather than one set of axes: these columns do not share a
    scale, and a second y-axis on the same panel would be misleading. The last
    `contextpanels` panels are shaded, as background rather than signal.
    """
    fig, axes = plt.subplots(len(columns), 1, sharex=True,
                             figsize=(11, 1.6 * len(columns) + 1.6))
    fig.patch.set_facecolor("white")
    context_from = len(columns) - contextpanels

    # the state of the test, from the notes, if this pickle carries the flags:
    bands = event_bands(df)
    disturbances = dict(bands).get("disturbance (see labels above)", [])

    for panel, (ax, column, colour) in enumerate(zip(axes, columns, colours)):
        if panel >= context_from:
            ax.set_facecolor(CONTEXT_BACKGROUND)
        shade_events(ax, bands)
        ax.plot(df.index, df[column], color=colour, linewidth=1.0)
        style_panel(ax, column, colour)
        if not fullrange:
            set_ylim(ax, df[column])

    label_disturbances(axes[0], disturbances)
    event_legend(fig, bands)

    fig.suptitle(title, fontsize=12, color=TEXT_PRIMARY, x=0.01, ha="left")
    fig.supylabel(ylabel, fontsize=9, color=TEXT_SECONDARY)
    format_time_axis(axes[-1], df)
    fig.tight_layout(rect=(0.01, 0, 1, 0.945))
    return fig


def plot_temperatures(df, outdir, datestamp, fullrange):
    columns = [c for c in TEMP_COLUMNS if c in df.columns]
    fig = stacked_figure(df, columns, CHANNEL_COLOURS,
                         f"SeaSTAR temperatures, {datestamp}",
                         "temperature (raw sensor units)", fullrange=fullrange)
    outfile = os.path.join(outdir, f"temperatures_{datestamp}.png")
    fig.savefig(outfile, dpi=150)
    plt.close(fig)
    return outfile


def plot_channels(df, gain, outdir, datestamp, fullrange):
    columns = [c for c in GAIN_COLUMNS[gain] if c in df.columns]
    temps = [c for c in CONTEXT_TEMPS if c in df.columns]
    colours = CHANNEL_COLOURS[:len(columns)] + [TEXT_SECONDARY] * len(temps)

    fig = stacked_figure(df, columns + temps, colours,
                         f"SeaSTAR J3 channels, gain {gain}, {datestamp}",
                         "signal (V), with block temperatures below",
                         contextpanels=len(temps), fullrange=fullrange)

    outfile = os.path.join(outdir, f"channels_gain{gain}_{datestamp}.png")
    fig.savefig(outfile, dpi=150)
    plt.close(fig)
    return outfile


def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(scripts_dir)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?",
                        help="pickle file; default is the newest in ../pickle")
    parser.add_argument("-p", "--pickle-dir",
                        default=os.path.join(root_dir, "pickle"),
                        help="directory to look for the pickle file in")
    parser.add_argument("-o", "--outdir", default=os.path.join(root_dir, "plots"),
                        help="directory to write the plots to")
    parser.add_argument("-s", "--start", help="only plot from this time, eg 14:00")
    parser.add_argument("-e", "--end", help="only plot up to this time, eg 15:30")
    parser.add_argument("-f", "--full-range", action="store_true",
                        help="scale each panel to all its data, spikes included")
    args = parser.parse_args()

    picklefile = args.file if args.file else find_pickle(args.pickle_dir)
    sys.stderr.write(f"reading {picklefile}\n")
    df = pd.read_pickle(picklefile)

    # a start/end time without a date is taken to be on the day of the data:
    day = str(df.index[0].date())
    if args.start is not None:
        df = df.loc[df.index >= pd.Timestamp(f"{day} {args.start}")]
    if args.end is not None:
        df = df.loc[df.index <= pd.Timestamp(f"{day} {args.end}")]
    if df.empty:
        sys.stderr.write("no data in the requested time range\n")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    datestamp = df.index[0].strftime("%Y_%m_%d")

    outfiles = [plot_temperatures(df, args.outdir, datestamp, args.full_range)]
    for gain in sorted(GAIN_COLUMNS):
        outfiles.append(plot_channels(df, gain, args.outdir, datestamp,
                                      args.full_range))

    sys.stderr.write(f"plotted {df.index[0]} to {df.index[-1]}\n")
    for outfile in outfiles:
        sys.stderr.write(f"wrote {outfile}\n")


if __name__ == "__main__":
    main()
