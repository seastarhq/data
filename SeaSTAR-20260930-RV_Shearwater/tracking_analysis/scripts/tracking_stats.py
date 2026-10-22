#!/usr/bin/env python3

# per-second statistics of each radiometer channel from the L0.5 data, evaluated against the
# three tracking error levels (TRACKING_EUCLIDIAN_MAX1/2/3, read from the L05 metadata).
#
# for each run this writes:
#   STATS_DIR/SeaSTAR_<run>_tracking_stats.csv    one row per second: min/max/range/mean/std/median
#                                                 of every channel, plus tracking class and flags
#   STATS_DIR/SeaSTAR_<run>_tracking_summary.csv  per channel and tracking level: number of seconds
#                                                 and samples that pass, and the medians of the stats
#   PLOTS_DIR/SeaSTAR_<run>_tracking.png          max tracking error per second, with the levels
#   PLOTS_DIR/SeaSTAR_<run>_ch_mean.png           per-second mean and min-max envelope of each channel
#   PLOTS_DIR/SeaSTAR_<run>_ch_relstd.png         per-second std/mean of each channel
#   PLOTS_DIR/SeaSTAR_<run>_ch_relstd_onecolour.png
#                                                 the same, with every second in one colour
# and, when more than one run is given, a summary of all of them pooled:
#   STATS_DIR/SeaSTAR_allruns_tracking_summary.csv
# with --start and/or --end (local time, HH:MM) it only makes the plots, limited to that part of the
# day, and names them after the window, e.g. SeaSTAR_<run>_1335-end_ch_mean.png. the stats are still
# worked out from the whole run, so the screening at the edges of the window sees the seconds outside it
#
# the tracking error levels are recomputed here rather than taken from the L05 flags, so that the
# screening can look forward in time as well as back. as in L0-to-L04, the screening window for each
# second starts TRACKING_PRE_MARGIN before it; it also runs on TRACKING_POST_MARGIN after it ends.
# a second passes a level when the max euclidian distance over its screening window is not above it
# (so passing level 1 means passing all three) and the camera gave good data (no NO_CAMERA_DATA or
# brightness flags, which are still taken from L05). the stats always use only the samples in the second.
# with TRACKING_POST_MARGIN=0 and the L0.5 ANALYSIS_MARGIN this reproduces the L05 tracking flags,
# which is checked for every run.
# seconds where every radiometer sample is exactly 0 (the radiometers weren't logging, e.g. while the
# robot was parked) are their own class and are left out of every level, including 'all'.
# cloud, robot and housekeeping flags don't exclude anything - they are shown on the plots

import sys, os
import argparse
import warnings
import numpy as np
import pandas as pd
import pytz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from seastar_error_flags import *

PICKLE_DIR = os.environ['PICKLE_DIR']
PLOTS_DIR = os.environ['PLOTS_DIR']
STATS_DIR = os.environ['STATS_DIR']
SEASTAR_TIMEZONE = os.environ['SEASTAR_TIMEZONE']
seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE)
TRACKING_PRE_MARGIN = float(os.environ['TRACKING_PRE_MARGIN'])
TRACKING_POST_MARGIN = float(os.environ['TRACKING_POST_MARGIN'])

CHANNELS = range(1, 11)
STATS = ['min', 'max', 'range', 'mean', 'std', 'median']

CAMERA_BAD = NO_CAMERA_DATA | CAMERA_BRIGHTNESS_HIGH | CAMERA_BRIGHTNESS_LOW

# tracking classes, from best to worst. each second is in exactly one class
CLASS_L1, CLASS_L2, CLASS_L3, CLASS_FAIL, CLASS_CAMERA, CLASS_NO_RADIOMETER = range(6)
CLASS_COLOURS = {CLASS_L1: '#2a78d6', CLASS_L2: '#f4a3a2', CLASS_L3: '#e34948',
                 CLASS_FAIL: '#8f1d1c', CLASS_CAMERA: '#8a8984', CLASS_NO_RADIOMETER: '#c3c2b7'}

parser = argparse.ArgumentParser()
parser.add_argument('runs', nargs='+', help='runs named <date>_<time>, e.g. 2026-09-30_09-32-14')
parser.add_argument('--pre-margin', type=float, help='seconds of tracking screening before each second')
parser.add_argument('--post-margin', type=float, help='seconds of tracking screening after each second')
parser.add_argument('--start', help='only plot from this local time, HH:MM')
parser.add_argument('--end', help='only plot up to this local time, HH:MM')
args = parser.parse_args()
window = args.start is not None or args.end is not None

# get the margins from command line arguments or default to values set in environment variables
pre_margin = args.pre_margin if args.pre_margin is not None else TRACKING_PRE_MARGIN
post_margin = args.post_margin if args.post_margin is not None else TRACKING_POST_MARGIN
sys.stderr.write(f"tracking screening margins: {pre_margin} s before, {post_margin} s after each second\n")

os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(STATS_DIR, exist_ok=True)


def per_second_stats(L05_array):
    # every second of the L05 array holds up to 60 samples, NaN padded, so the stats are nan-aware.
    # a second with no samples gives NaN stats, which numpy warns about
    stats = {}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        for ch in CHANNELS:
            v = L05_array[f'ch{ch}_1x']
            stats[f'ch{ch}_min'] = np.nanmin(v, axis=1)
            stats[f'ch{ch}_max'] = np.nanmax(v, axis=1)
            stats[f'ch{ch}_range'] = stats[f'ch{ch}_max'] - stats[f'ch{ch}_min']
            stats[f'ch{ch}_mean'] = np.nanmean(v, axis=1)
            stats[f'ch{ch}_std'] = np.nanstd(v, axis=1, ddof=1)
            stats[f'ch{ch}_median'] = np.nanmedian(v, axis=1)
        max_eucl = np.nanmax(L05_array['euclidian_dist'], axis=1)
    return stats, max_eucl


def screened_tracking_error(L05_array, interval, pre, post):
    # the max euclidian distance over each second's screening window, [start - pre, end + post).
    # L0-to-L04 starts the first second on a whole second and each holds the samples from its start
    # up to (not including) the next, so the window edges follow the same convention
    times = L05_array['datetime'].ravel()
    eucl = L05_array['euclidian_dist'].ravel()
    valid = ~np.isnat(times)
    times, eucl = times[valid], eucl[valid]
    step = np.timedelta64(int(round(interval * 1000)), 'ms')
    starts = times[0].astype('datetime64[s]').astype('datetime64[ms]') + step * np.arange(len(L05_array))
    # check the samples really do sit in the seconds we think they do, or the windows would be shifted
    in_second = np.repeat(np.arange(len(L05_array)), (~np.isnat(L05_array['datetime'])).sum(axis=1))
    if not np.array_equal((times - starts[0]) // step, in_second):
        sys.stderr.write("ERROR: the L05 samples aren't in whole-second timesteps, can't build the screening windows\n")
        sys.exit(1)
    lo = np.searchsorted(times, starts - np.timedelta64(int(round(pre * 1000)), 'ms'), side='left')
    hi = np.searchsorted(times, starts + step + np.timedelta64(int(round(post * 1000)), 'ms'), side='left')
    # an empty or all-NaN window gives NaN, which (as in calculate_tracking_flags) sets no tracking error bit
    screened = np.full(len(L05_array), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        for i in range(len(L05_array)):
            if hi[i] > lo[i]:
                screened[i] = np.nanmax(eucl[lo[i]:hi[i]])
    return screened


def tracking_error_bits(screened, levels):
    # the same cumulative bits as calculate_tracking_flags
    bits = np.zeros(len(screened), dtype=int)
    bits[screened > levels[0]] |= TRACKING_ERROR_1
    bits[screened > levels[1]] |= TRACKING_ERROR_2
    bits[screened > levels[2]] |= TRACKING_ERROR_3
    return bits


def tracking_class(tracking_flags, no_radiometer):
    tclass = np.full(len(tracking_flags), CLASS_FAIL)
    tclass[(tracking_flags & TRACKING_ERROR_3) == 0] = CLASS_L3
    tclass[(tracking_flags & TRACKING_ERROR_2) == 0] = CLASS_L2
    tclass[(tracking_flags & TRACKING_ERROR_1) == 0] = CLASS_L1
    tclass[(tracking_flags & CAMERA_BAD) != 0] = CLASS_CAMERA
    tclass[no_radiometer] = CLASS_NO_RADIOMETER
    return tclass


def load_run(run):
    L05 = np.load(f'{PICKLE_DIR}/SeaSTAR_{run}.L05', allow_pickle=True)
    metadata = L05['metadata'][()]
    L05_array = L05['array_data']
    L06_array = np.load(f'{PICKLE_DIR}/SeaSTAR_{run}.L06', allow_pickle=True)['array_data']

    # L06 is made one timestep per L05 timestep, so the two line up by index - check that they do
    L05_times = np.nanmin(L05_array['datetime'], axis=1)
    if len(L06_array) != len(L05_array) or not np.array_equal(L05_times, L06_array['datetime']):
        sys.stderr.write(f"ERROR: the L05 and L06 timesteps of {run} don't line up, remake the L06\n")
        sys.exit(1)

    levels = [metadata['TRACKING_EUCLIDIAN_MAX1'], metadata['TRACKING_EUCLIDIAN_MAX2'], metadata['TRACKING_EUCLIDIAN_MAX3']]
    L05_tracking_flags = L05_array['flags'][:, 0]
    tracking_error = TRACKING_ERROR_1 | TRACKING_ERROR_2 | TRACKING_ERROR_3

    # with no post margin we should get back exactly the L05 tracking error bits - if not, the pre
    # margin doesn't match the one L0-to-L04 used (its metadata can't tell us: it stores the margin
    # truncated to whole seconds). the first second is left out: L0-to-L04 screened it with raw rows
    # from before the first timestep, which aren't kept in the L05. in the same way, the post margin of
    # the last second can only see the samples that made it into the L05
    check = tracking_error_bits(screened_tracking_error(L05_array, metadata['AVG_INTERVAL'], pre_margin, 0.0), levels)
    differ = (check[1:] != (L05_tracking_flags[1:] & tracking_error)).sum()
    if differ:
        sys.stderr.write(f"WARNING: {run}: with a {pre_margin} s pre margin and no post margin, {differ} of "
                         f"{len(L05_array) - 1} seconds have different tracking levels from the L05 flags\n")

    screened = screened_tracking_error(L05_array, metadata['AVG_INTERVAL'], pre_margin, post_margin)
    tracking_flags = (L05_tracking_flags & ~tracking_error) | tracking_error_bits(screened, levels)

    stats, max_eucl = per_second_stats(L05_array)
    df = pd.DataFrame({'datetime_utc': L05_times,
                       'max_euclidian_dist': max_eucl,
                       'screened_max_euclidian_dist': screened,
                       'n_samples': (~np.isnan(L05_array['ch1_1x'])).sum(axis=1),
                       'L05_tracking_flags': L05_tracking_flags,
                       'tracking_flags': tracking_flags,
                       'robot_flags': L05_array['flags'][:, 1],
                       'housekeeping_flags': L05_array['flags'][:, 2],
                       'cloud_flags': L06_array['cloud_flags']})
    # nan_to_num makes the padding count as 0 too, so a second with no samples at all has no radiometer data
    no_radiometer = np.all([np.all(np.nan_to_num(L05_array[f'ch{ch}_1x']) == 0, axis=1) for ch in CHANNELS], axis=0)
    df['tracking_class'] = tracking_class(df['tracking_flags'].to_numpy(), no_radiometer)
    df['pass_level1'] = df['tracking_class'] <= CLASS_L1
    df['pass_level2'] = df['tracking_class'] <= CLASS_L2
    df['pass_level3'] = df['tracking_class'] <= CLASS_L3
    df = pd.concat([df, pd.DataFrame(stats)], axis=1)
    df.insert(1, 'datetime_local', df['datetime_utc'].dt.tz_localize('UTC').dt.tz_convert(seastar_timezone).dt.tz_localize(None))
    return df, levels


def summarise(df, levels):
    # for each tracking level, the seconds that pass it and the medians of their per-second stats.
    # rel_std and rel_range are std/mean and range/mean in percent
    selections = {'all': (df['tracking_class'] != CLASS_NO_RADIOMETER).to_numpy(),
                  f'level3 (<= {levels[2]})': df['pass_level3'].to_numpy(),
                  f'level2 (<= {levels[1]})': df['pass_level2'].to_numpy(),
                  f'level1 (<= {levels[0]})': df['pass_level1'].to_numpy()}
    rows = []
    for level, passing in selections.items():
        sel = df[passing]
        for ch in CHANNELS:
            rel_std = 100.0 * sel[f'ch{ch}_std'] / sel[f'ch{ch}_mean'].abs()
            rel_range = 100.0 * sel[f'ch{ch}_range'] / sel[f'ch{ch}_mean'].abs()
            rows.append({'tracking_level': level, 'pre_margin_s': pre_margin, 'post_margin_s': post_margin, 'channel': ch,
                         'n_seconds': len(sel), 'fraction_of_seconds': len(sel) / selections['all'].sum(),
                         'n_samples': int(sel['n_samples'].sum()),
                         'median_min': sel[f'ch{ch}_min'].median(),
                         'median_max': sel[f'ch{ch}_max'].median(),
                         'median_range': sel[f'ch{ch}_range'].median(),
                         'median_mean': sel[f'ch{ch}_mean'].median(),
                         'median_std': sel[f'ch{ch}_std'].median(),
                         'median_median': sel[f'ch{ch}_median'].median(),
                         'median_rel_std_pct': rel_std.median(),
                         'p95_rel_std_pct': rel_std.quantile(0.95),
                         'median_rel_range_pct': rel_range.median(),
                         'p95_rel_range_pct': rel_range.quantile(0.95)})
    return pd.DataFrame(rows)


def class_labels(levels):
    return {CLASS_L1: f'pass level 1 (<= {levels[0]})',
            CLASS_L2: f'level 1-2 ({levels[0]} - {levels[1]})',
            CLASS_L3: f'level 2-3 ({levels[1]} - {levels[2]})',
            CLASS_FAIL: f'fail level 3 (> {levels[2]})',
            CLASS_CAMERA: 'camera flagged',
            CLASS_NO_RADIOMETER: 'no radiometer data'}


def scatter_by_class(ax, t, y, tclass, levels, size=2, level1_on_top=False):
    # the best tracking is drawn first so that the worse classes, which are what we're looking for, sit on top.
    # level1_on_top raises the seconds that pass level 1 above the rest instead; it does this with zorder
    # rather than the drawing order, so the legend keeps the same order on every plot
    labels = class_labels(levels)
    for c in (CLASS_NO_RADIOMETER, CLASS_L1, CLASS_L2, CLASS_L3, CLASS_FAIL, CLASS_CAMERA):
        sel = tclass == c
        if sel.any():
            zorder = 3 if (level1_on_top and c == CLASS_L1) else 2
            ax.scatter(t[sel], y[sel], s=size, color=CLASS_COLOURS[c], label=labels[c], linewidths=0, rasterized=True, zorder=zorder)


def flag_strips(ax, df):
    # one row per flag type along the bottom of each figure, filled where the flag is set
    t = df['datetime_local']
    strips = [('tracking > level 1', ~df['pass_level1'], CLASS_COLOURS[CLASS_FAIL]),
              ('cloudy (TVAR)', (df['cloud_flags'] & TVAR_OOB) != 0, '#52514e'),
              ('cloud screen n/a', (df['cloud_flags'] & AUTO_CLOUD_FLAG_FAIL) != 0, '#c3c2b7'),
              ('encoder dropout', (df['robot_flags'] & ENCODER_DROPOUT) != 0, '#6250d6'),
              ('housekeeping', df['housekeeping_flags'] != 0, '#eda100')]
    for row, (name, mask, colour) in enumerate(strips):
        y0 = len(strips) - row - 1
        ax.fill_between(t, y0 + 0.1, y0 + 0.9, where=mask.to_numpy(), step='mid', color=colour, linewidth=0)
    ax.set_yticks([len(strips) - row - 0.5 for row in range(len(strips))], [s[0] for s in strips], fontsize=7)
    ax.set_ylim(0, len(strips))
    ax.tick_params(axis='y', length=0)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)


def finish_time_axis(ax):
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel(f'time ({SEASTAR_TIMEZONE})')


def style_panel(ax):
    ax.grid(True, color='#e1e0d9', linewidth=0.5)
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)


def plot_tracking(df, levels, run, name):
    # run names the run in the titles, name is what the files are called after
    fig, (ax, axn, axf) = plt.subplots(3, 1, figsize=(12, 7), sharex=True, height_ratios=[4, 1.5, 1.5])
    t = df['datetime_local']
    tclass = df['tracking_class'].to_numpy()
    scatter_by_class(ax, t, df['screened_max_euclidian_dist'], tclass, levels, size=3)
    for n, level in enumerate(levels):
        ax.axhline(level, color='#52514e', linewidth=0.8, linestyle='--')
        ax.annotate(f'level {n+1}: {level}', (1.0, level), xycoords=('axes fraction', 'data'),
                    xytext=(4, 0), textcoords='offset points', fontsize=8, color='#52514e',
                    va=('top', 'bottom', 'center')[n])  # levels 1 and 2 are close together, so their labels go below and above their lines
    ax.set_yscale('log')
    ax.set_ylabel('max euclidian distance\nover screening window')
    fig.suptitle(f'SeaSTAR {run}: suntracking error per second, screened {pre_margin} s before and {post_margin} s after', y=0.99)
    fig.legend(*ax.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(0.5, 0.95), fontsize=8, markerscale=4, frameon=False, ncol=6)
    style_panel(ax)
    axn.plot(t, df['n_samples'], color='#2a78d6', linewidth=0.6)
    axn.set_ylabel('samples\nper second')
    style_panel(axn)
    flag_strips(axf, df)
    finish_time_axis(axf)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(f'{PLOTS_DIR}/SeaSTAR_{name}_tracking.png', dpi=150)
    plt.close(fig)


def plot_channels(df, levels, run, name, channel_nm, kind):
    # kind 'mean': per-second mean with the min-max envelope behind it
    # kind 'relstd': per-second std/mean in percent, on a log axis
    # kind 'relstd_onecolour': the same, with every second in one colour rather than coloured by tracking level
    # two columns of five: ch1-5 (block 1) on the left, ch6-10 (block 2) on the right, each column with
    # its own flag strips and time axis at the bottom, so the times line up with the panels above them
    fig = plt.figure(figsize=(18, 13))
    grid = fig.add_gridspec(6, 2, height_ratios=[3] * 5 + [2])
    strips = [fig.add_subplot(grid[5, 0])]
    strips.append(fig.add_subplot(grid[5, 1], sharex=strips[0]))
    axes = [fig.add_subplot(grid[(ch - 1) % 5, (ch - 1) // 5], sharex=strips[0]) for ch in CHANNELS]
    t = df['datetime_local']
    tclass = df['tracking_class'].to_numpy()
    for ax, ch in zip(axes, CHANNELS):
        if kind == 'mean':
            ax.fill_between(t, df[f'ch{ch}_min'], df[f'ch{ch}_max'], step='mid', color='#c3c2b7', linewidth=0, label='min - max')
            scatter_by_class(ax, t, df[f'ch{ch}_mean'], tclass, levels, level1_on_top=True)
            ax.set_ylabel('V')
        else:
            relstd = 100.0 * df[f'ch{ch}_std'] / df[f'ch{ch}_mean'].abs()
            if kind == 'relstd_onecolour':
                ax.scatter(t, relstd, s=2, color=CLASS_COLOURS[CLASS_L1], linewidths=0, rasterized=True)
            else:
                scatter_by_class(ax, t, relstd, tclass, levels)
            ax.set_yscale('log')
            # a few seconds where the radiometer value is stuck have std/mean of ~1e-14 %, which would squash
            # everything else, so the limits come from the bulk of the data
            positive = relstd[relstd > 0]
            if len(positive):
                ax.set_ylim(positive.quantile(0.001) / 2, positive.quantile(0.999) * 2)
            ax.set_ylabel('std/mean (%)')
        ax.set_title(f'ch{ch} ({channel_nm[ch-1]:.0f} nm)', loc='left', fontsize=9)
        ax.tick_params(labelbottom=False)
        style_panel(ax)
    what = 'mean and min-max per second' if kind == 'mean' else 'relative std per second'
    if kind == 'relstd_onecolour':
        # one series, so no legend: the flag strips still show the tracking level
        fig.suptitle(f'SeaSTAR {run}: channel {what} '
                     f'(tracking screened {pre_margin} s before, {post_margin} s after)', y=0.995)
    else:
        fig.suptitle(f'SeaSTAR {run}: channel {what}, coloured by tracking level '
                     f'(screened {pre_margin} s before, {post_margin} s after)', y=0.995)
        fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(0.5, 0.975), fontsize=8, markerscale=4, frameon=False, ncol=7)
    for ax in strips:
        flag_strips(ax, df)
        finish_time_axis(ax)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(f'{PLOTS_DIR}/SeaSTAR_{name}_ch_{kind}.png', dpi=150)
    plt.close(fig)


all_seconds = []
for run in args.runs:
    sys.stderr.write(f"processing {run}\n")
    df, levels = load_run(run)
    channel_nm = np.load(f'{PICKLE_DIR}/SeaSTAR_{run}.L05', allow_pickle=True)['metadata'][()]['CHANNEL_NM']
    df.insert(0, 'run', run)
    if window:
        clock = df['datetime_local'].dt.strftime('%H:%M')
        in_window = np.ones(len(df), dtype=bool)
        if args.start is not None:
            in_window &= clock >= args.start
        if args.end is not None:
            in_window &= clock < args.end
        df = df[in_window].reset_index(drop=True)
        if df.empty:
            sys.stderr.write(f"WARNING: {run} has no data between {args.start} and {args.end}, no plots made\n")
            continue
        name = f"{run}_{(args.start or 'start').replace(':', '')}-{(args.end or 'end').replace(':', '')}"
        title = f"{run} {args.start or 'start'} to {args.end or 'end'}"
    else:
        df.to_csv(f'{STATS_DIR}/SeaSTAR_{run}_tracking_stats.csv', index=False)
        summary = summarise(df, levels)
        summary.to_csv(f'{STATS_DIR}/SeaSTAR_{run}_tracking_summary.csv', index=False)
        all_seconds.append((df, levels))
        name, title = run, run
    plot_tracking(df, levels, title, name)
    plot_channels(df, levels, title, name, channel_nm, 'mean')
    plot_channels(df, levels, title, name, channel_nm, 'relstd')
    plot_channels(df, levels, title, name, channel_nm, 'relstd_onecolour')

if len(all_seconds) > 1:
    # the pooled summary only makes sense if every run used the same tracking levels
    all_levels = {tuple(levels) for _, levels in all_seconds}
    if len(all_levels) > 1:
        sys.stderr.write(f"not writing the all-runs summary: the runs used different tracking levels {all_levels}\n")
    else:
        pooled = pd.concat([df for df, _ in all_seconds], ignore_index=True)
        summarise(pooled, all_seconds[0][1]).to_csv(f'{STATS_DIR}/SeaSTAR_allruns_tracking_summary.csv', index=False)
