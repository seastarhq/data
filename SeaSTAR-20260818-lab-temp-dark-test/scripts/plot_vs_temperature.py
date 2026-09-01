#!/usr/bin/env python3
# plot the J3 channels against the block temperatures, one panel per channel and
# temperature, with a straight line fitted to each so the temperature dependence
# can be read off as a slope.

import argparse
import datetime
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# the time series script holds the palette and the shared plumbing:
from plot_timeseries import (CHANNEL_COLOURS, GAIN_COLUMNS, GRID_COLOUR,
                             TEXT_PRIMARY, TEXT_SECONDARY, YLIM_QUANTILE,
                             find_pickle)

TEMPERATURES = ["Temp3", "Temp4"]

# Temp3 is the one the fits are tabulated against: it is the block sensor the
# channels track best, so its slope is the number the calibration wants. the
# Temp4 panels stay in the figure as a sanity check but are not written out.
FIT_TEMPERATURE = "Temp3"
FIT_FILE = "fit_coefficients.txt"

# what the rows of a run with no --tag are called in the table:
WHOLE_RUN = "full"


def clean(df, keepdisturbed, keeplampoff):
    """Drop the samples the notes say are no good for a temperature fit.

    Lamp-off samples are a different measurement, not a cooler version of the
    same one, so they go by default; so does anything flagged as disturbed.
    """
    if not keeplampoff and "lamp_on" in df.columns:
        lampoff = ~df["lamp_on"]
        if lampoff.any():
            sys.stderr.write(f"leaving out {int(lampoff.sum())} lamp-off samples "
                             "(-l keeps them)\n")
        df = df[~lampoff]

    if not keepdisturbed and "disturbance" in df.columns:
        disturbed = df["disturbance"] != ""
        if disturbed.any():
            sys.stderr.write(f"leaving out {int(disturbed.sum())} disturbed "
                             "samples (-d keeps them)\n")
        df = df[~disturbed]

    return df


def robust_limits(series):
    """Axis limits that ignore the odd spike, as in the time series plots."""
    low, high = series.quantile([YLIM_QUANTILE, 1 - YLIM_QUANTILE])
    if not (low < high):
        return None
    margin = 0.05 * (high - low)
    return low - margin, high + margin


def fit(temperature, signal):
    """Least squares straight line, as (slope, intercept, r squared, n).

    None when there is nothing to fit: fewer than two usable samples, or every
    sample at the same temperature.
    """
    good = temperature.notna() & signal.notna()
    if good.sum() < 2 or temperature[good].nunique() < 2:
        return None

    slope, intercept = np.polyfit(temperature[good], signal[good], 1)
    correlation = np.corrcoef(temperature[good], signal[good])[0, 1]
    return slope, intercept, correlation ** 2, int(good.sum())


def fit_line(ax, temperature, signal):
    """Draw the fit on a panel, and hand back its coefficients."""
    fitted = fit(temperature, signal)
    if fitted is None:
        return None
    slope, intercept, rsquared, _ = fitted

    good = temperature.notna() & signal.notna()
    x = np.array([temperature[good].min(), temperature[good].max()])
    ax.plot(x, slope * x + intercept, color=TEXT_PRIMARY, linewidth=1.2,
            linestyle="--", zorder=3)

    ax.text(0.985, 0.06, f"{slope * 1e6:+.1f} µV/°C   r² = {rsquared:.2f}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            color=TEXT_PRIMARY,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75,
                      boxstyle="round,pad=0.2"))

    return fitted


def style_panel(ax):
    ax.grid(True, color=GRID_COLOUR, linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8, colors=TEXT_SECONDARY)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID_COLOUR)


def plot_against_temperature(df, gain, outdir, datestamp, fullrange, tag=""):
    """Draw the panels, and hand back the file written and the Temp3 fits."""
    channels = [c for c in GAIN_COLUMNS[gain] if c in df.columns]
    temperatures = [t for t in TEMPERATURES if t in df.columns]
    fits = {}

    fig, axes = plt.subplots(len(channels), len(temperatures),
                             sharex="col", sharey="row", squeeze=False,
                             figsize=(4.4 * len(temperatures),
                                      1.9 * len(channels) + 1.2))
    fig.patch.set_facecolor("white")

    for row, (channel, colour) in enumerate(zip(channels, CHANNEL_COLOURS)):
        for column, temperature in enumerate(temperatures):
            ax = axes[row][column]
            ax.scatter(df[temperature], df[channel], s=2, alpha=0.15,
                       color=colour, linewidths=0, rasterized=True)
            fitted = fit_line(ax, df[temperature], df[channel])
            if temperature == FIT_TEMPERATURE and fitted is not None:
                fits[channel] = fitted
            style_panel(ax)

            if not fullrange:
                limits = robust_limits(df[channel])
                if limits:
                    ax.set_ylim(*limits)

            if column == 0:
                ax.set_ylabel(channel, fontsize=9, color=TEXT_PRIMARY)
            if row == 0:
                ax.set_title(temperature, fontsize=10, color=TEXT_PRIMARY)
            if row == len(channels) - 1:
                ax.set_xlabel(f"{temperature} (°C)", fontsize=9,
                              color=TEXT_SECONDARY)

    subtitle = f"{df.index[0]:%H:%M} to {df.index[-1]:%H:%M}" if tag else ""
    fig.suptitle(f"SeaSTAR J3 channels, gain {gain}, against block temperature, "
                 f"{datestamp}" + (f", {subtitle}" if subtitle else ""),
                 fontsize=12, color=TEXT_PRIMARY, x=0.01, ha="left")
    fig.supylabel("signal (V)", fontsize=9, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0.01, 0, 1, 0.97))

    outfile = os.path.join(
            outdir, f"channels_gain{gain}_vs_temperature_{datestamp}{tag}.png")
    fig.savefig(outfile, dpi=150)
    plt.close(fig)
    return outfile, fits


# the columns of the coefficients table: the heading, how the heading is laid
# out, and how the value underneath it is written. this run was fitted twice,
# over the whole run and over the cooling leg alone, so which samples a row
# came from is part of the row.
FIT_COLUMNS = [("channel", "<10", "<10s"), ("gain", ">4", ">4s"),
               ("subset", ">8", ">8s"), ("start", ">8", ">8s"),
               ("end", ">8", ">8s"),
               ("slope (V/degC)", ">15", ">+15.6e"),
               ("slope (uV/degC)", ">15", ">+15.3f"),
               ("intercept (V)", ">15", ">+15.6f"),
               ("r2", ">9", ">9.6f"), ("nsamples", ">8", ">8d")]


def fit_row(channel, gain, subset, span, fitted):
    slope, intercept, rsquared, n = fitted
    values = [channel, gain, subset, span[0], span[1],
              slope, slope * 1e6, intercept, rsquared, n]
    return "  ".join(f"{value:{spec}}"
                     for (_, _, spec), value in zip(FIT_COLUMNS, values))


def sort_key(row):
    """Whole-run rows first, then the subsets, by gain and channel."""
    subset, gain, channel = row[0], row[1], row[2]
    return (subset != WHOLE_RUN, subset, gain, channel)


def write_fits(path, gain, subset, span, fits, notes):
    """Write the coefficients table, keeping the rows this run did not make.

    One run of the script only fits one gain over one stretch of the data, so
    the rows already in the file for the other gains and the other stretches
    are read back and kept: that way a make of the lot leaves one table with
    every fit in it.
    """
    rows = []
    if os.path.exists(path):
        with open(path) as existing:
            for line in existing:
                fields = line.split()
                if len(fields) > 2 and not line.startswith("#"):
                    if (fields[1], fields[2]) != (gain, subset):
                        rows.append((fields[2], fields[1], fields[0],
                                     line.strip()))

    rows += [(subset, gain, channel,
              fit_row(channel, gain, subset, span, fitted))
             for channel, fitted in fits.items()]

    header = "  ".join(f"{name:{spec}}" for name, spec, _ in FIT_COLUMNS)

    with open(path, "w") as out:
        out.write("# straight-line least squares fits of the SeaSTAR J3 "
                  f"channels against {FIT_TEMPERATURE}\n")
        out.write(f"# signal = slope * {FIT_TEMPERATURE} + intercept, "
                  f"signal in volts, {FIT_TEMPERATURE} in degrees C\n")
        for note in notes:
            out.write(f"# {note}\n")
        out.write(f"# written by {os.path.basename(__file__)}, "
                  f"{datetime.datetime.now():%Y-%m-%d %H:%M}\n")
        out.write("#\n")
        out.write(f"# {header}\n")
        for row in sorted(rows, key=sort_key):
            out.write(f"  {row[-1]}\n")

    return path


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
    parser.add_argument("-c", "--fit-file",
                        default=os.path.join(root_dir, FIT_FILE),
                        help="file to write the fit coefficients to")
    parser.add_argument("-g", "--gain", default="2", choices=sorted(GAIN_COLUMNS),
                        help="which gain setting to plot (default 2)")
    parser.add_argument("-s", "--start", help="only plot from this time, eg 14:00")
    parser.add_argument("-e", "--end", help="only plot up to this time, eg 15:30")
    parser.add_argument("-d", "--keep-disturbed", action="store_true",
                        help="keep the samples the notes flagged as disturbed")
    parser.add_argument("-l", "--keep-lamp-off", action="store_true",
                        help="keep the samples taken with the lamp off")
    parser.add_argument("-f", "--full-range", action="store_true",
                        help="scale each panel to all its data, spikes included")
    parser.add_argument("-t", "--tag", default="",
                        help="added to the plot filename, to keep a fit over "
                             "part of the run separate from the whole-run one")
    args = parser.parse_args()

    picklefile = args.file if args.file else find_pickle(args.pickle_dir)
    sys.stderr.write(f"reading {picklefile}\n")
    df = pd.read_pickle(picklefile)

    day = str(df.index[0].date())
    if args.start is not None:
        df = df.loc[df.index >= pd.Timestamp(f"{day} {args.start}")]
    if args.end is not None:
        df = df.loc[df.index <= pd.Timestamp(f"{day} {args.end}")]

    datestamp = df.index[0].strftime("%Y_%m_%d")
    df = clean(df, args.keep_disturbed, args.keep_lamp_off)
    if df.empty:
        sys.stderr.write("no data left to plot\n")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    outfile, fits = plot_against_temperature(df, args.gain, args.outdir,
                                             datestamp, args.full_range,
                                             args.tag)

    # the tag names the stretch of the run in the table, so that the cooling
    # leg and the whole run can sit in the one file:
    subset = args.tag.strip("_") or WHOLE_RUN
    span = (f"{df.index[0]:%H:%M:%S}", f"{df.index[-1]:%H:%M:%S}")

    # what went into the fits, so the table can be read without the command
    # line that made it:
    left_out = [name for name, kept in
                [("lamp-off", args.keep_lamp_off),
                 ("disturbed", args.keep_disturbed)] if not kept]
    notes = [f"{os.path.basename(picklefile)}, {datestamp}",
             ("samples left out: " + ", ".join(left_out)) if left_out
             else "every sample kept"]
    if args.keep_lamp_off:
        notes.append("the lamp-off samples are kept: this is a dark test")
    fitfile = write_fits(args.fit_file, args.gain, subset, span, fits, notes)

    sys.stderr.write(f"{len(df)} samples, "
                     f"{df.index[0]:%H:%M:%S} to {df.index[-1]:%H:%M:%S}\n")
    sys.stderr.write(f"wrote {outfile}\n")
    sys.stderr.write(f"wrote {fitfile}\n")


if __name__ == "__main__":
    main()
