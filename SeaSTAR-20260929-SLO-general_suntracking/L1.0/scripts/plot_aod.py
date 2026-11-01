#!/usr/bin/env python3

import sys, os
import numpy as np
import argparse
import pandas as pd
import pytz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *

# where to find things including
# ROOT_DIR L10_DATA_DIR PLOTS_DIR
from seastar_filepaths import *

## analysis parameters:
# including
# SEASTAR_TIMEZONE
from seastar_analysis_params import *

# plots the AOD at one wavelength against local time, from one or more L10 files (L06-to-L10_sun.py) on one
# figure: the timesteps that pass the screening in colour, and the screened ones faintly behind them for context.
# --screen picks which aod_flags screen the data (default all of them). the y axis covers the AODs that pass,
# so screened ones far outside them (mostly cloud) are cut off, unless --ymax sets the top. a channel's AOD is
# undefined where |V| <= a (the sun is dimmed below the calibration's intercept, by thick cloud): those timesteps
# that pass the screening are marked along the top of the plot, rather than left out (--hide-undefined leaves
# them out). --microtops overlays a Microtops L1.5 groups file (one row per group of shots, in UTC), the AOD at the
# same wavelength, its times converted to SEASTAR_TIMEZONE.
# writes aod_<nm>nm_<date>.png to PLOTS_DIR, with the date of the first file, or aod_<nm>nm_<date>_<flags>.png
# when only some flags screen it, and _v0origin after the date for L10 files processed with V0_MODE=origin

SCREEN_FLAGS = {'cloud': AOD_CLOUD, 'tracking': AOD_TRACKING, 'temp_low': AOD_CHANNEL_TEMP_LOW,
                'pressure': AOD_PRESSURE_FILLED, 'position': AOD_POSITION_FILLED, 'signal_low': AOD_SIGNAL_LOW}

UNFLAGGED_COLOUR = "#2a78d6"
FLAGGED_COLOUR = "#b8b7b0"
UNDEFINED_COLOUR = "#c2185b"
MICROTOPS_COLOUR = "#e8833a"

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+', help='L10 files, found in L10_DATA_DIR')
parser.add_argument('--nm', type=int, default=500, help='the wavelength to plot (default 500)')
parser.add_argument('--screen', nargs='+', choices=SCREEN_FLAGS, default=list(SCREEN_FLAGS),
                    help='the aod_flags that screen the data (default all of them)')
parser.add_argument('--ymax', type=float, help='the top of the y axis (default: from the AODs that pass)')
parser.add_argument('--xmin', help='the start of the x axis, HH:MM local time on the date of the first file (default: from the data)')
parser.add_argument('--hide-undefined', action='store_true',
                    help="don't mark the timesteps where |V| <= a and the AOD is undefined")
parser.add_argument('--microtops', help='a Microtops computed_aod_L15_groups file to overlay (times in UTC)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of PLOTS_DIR/aod_<nm>nm_<date>.png')
args = parser.parse_args()

L10_data_dir = [L10_DATA_DIR,]
arrays = []
for name in args.files:
    L10_npyfile = seastar_datautils.findFile(name, L10_data_dir)
    L10_npz = np.load(L10_npyfile, allow_pickle=True)
    arrays.append(L10_npz['array_data'])
    metadata = L10_npz['metadata'][()]
L10_data = np.concatenate(arrays)
field = f'aod_{args.nm}nm'
if field not in L10_data.dtype.names:
    sys.exit(f"no {field} in {', '.join(args.files)}")

timezone = pytz.timezone(SEASTAR_TIMEZONE)
# pandas can't always find time zones by name, so timezone is a pytz object
times = pd.to_datetime(L10_data['datetime']).tz_localize('UTC').tz_convert(timezone).tz_localize(None)
aod = L10_data[field]
# the channel at this wavelength, and its temperature-corrected voltage, to find where |V| <= a
ch = next(ch for ch, nm in metadata['AOD_WAVELENGTHS_NM'].items() if nm == args.nm)
volts = L10_data[f'ch{ch}_1x_darksub_quad_v0tc']
screen_mask = 0
for name in args.screen:
    screen_mask |= SCREEN_FLAGS[name]
good = ((L10_data['aod_flags'] & screen_mask) == 0) & np.isfinite(aod)
flagged = ~good & np.isfinite(aod)
undefined = ((L10_data['aod_flags'] & screen_mask & ~AOD_SIGNAL_LOW) == 0) & np.isfinite(volts) & (volts <= metadata['V0_A'][ch])
date = str(L10_data['datetime'].min())[:10]
v0_mode = metadata.get('V0_MODE', 'intercept')

def read_microtops(path, nm, timezone):
    # a few header lines, then a tab-separated table whose header line starts with Date; dates like SEP/30/2026
    with open(path) as f:
        skip = next(i for i, line in enumerate(f) if line.startswith('Date'))
    table = pd.read_csv(path, sep='\t', skiprows=skip)
    table.columns = table.columns.str.strip()
    if f'AOD {nm}' not in table.columns:
        sys.exit(f"no AOD {nm} in {path}")
    utc = pd.to_datetime(table['Date'].str.title() + ' ' + table['Time'], format='%b/%d/%Y %H:%M:%S')
    local = utc.dt.tz_localize('UTC').dt.tz_convert(timezone).dt.tz_localize(None)
    return local.to_numpy(), table[f'AOD {nm}'].to_numpy()

fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(times[flagged], aod[flagged], '.', color=FLAGGED_COLOUR, markersize=1.5,
        label=f'screened ({flagged.sum()})')
ax.plot(times[good], aod[good], '.', color=UNFLAGGED_COLOUR, markersize=2.5,
        label=f'passed ({good.sum()})')
if good.any():
    lo, hi = np.percentile(aod[good], [0.5, 99.5])
    pad = 0.15 * (hi - lo) + 0.01
    ax.set_ylim(max(lo - pad, 0.0) if lo >= 0 else lo - pad, hi + pad)
    if args.ymax is not None:
        ax.set_ylim(min(ax.get_ylim()[0], 0.0), args.ymax)
else:
    ax.text(0.5, 0.5, 'no timesteps pass the screening', transform=ax.transAxes, ha='center', va='center', color='#52514e')
if args.microtops is not None:
    mt_times, mt_aod = read_microtops(args.microtops, args.nm, timezone)
    ax.plot(mt_times, mt_aod, 'D', color=MICROTOPS_COLOUR, markersize=8, markeredgecolor='white', markeredgewidth=1.5,
            label=f'Microtops L1.5 groups ({len(mt_aod)})', zorder=3)
if undefined.any() and not args.hide_undefined:
    ax.plot(times[undefined], np.full(undefined.sum(), ax.get_ylim()[1]), '|', color=UNDEFINED_COLOUR, markersize=8,
            clip_on=False, label=f'|V| \u2264 a, AOD undefined ({undefined.sum()})')
if args.xmin is not None:
    ax.set_xlim(left=pd.Timestamp(f'{date} {args.xmin}'))
locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
ax.set_xlabel(f'time ({SEASTAR_TIMEZONE})')
ax.set_ylabel(f'AOD {args.nm} nm')
ax.grid(True, color='#e1e0d9', linewidth=0.5)
ax.set_axisbelow(True)
for side in ('top', 'right'):
    ax.spines[side].set_visible(False)
legend = ax.legend(loc='upper left', frameon=False, fontsize=9)
# the data dots are too small to read in the legend, so every legend marker is drawn at one size
for handle in legend.legend_handles:
    handle.set_markersize(7)
all_flags = set(args.screen) == set(SCREEN_FLAGS)
screened_by = 'all aod_flags' if all_flags else ', '.join(args.screen) + ' flags only'
ax.set_title(f'SeaSTAR L1.0 AOD at {args.nm} nm, {date} ({os.path.basename(ROOT_DIR)}), {v0_mode} V0, screened by {screened_by}',
             loc='left', fontsize=10)
fig.tight_layout()

if args.outputfile is None:
    suffix = ('' if v0_mode == 'intercept' else f'_v0{v0_mode}') + ('' if all_flags else '_' + '_'.join(sorted(args.screen)))
    plot_path = os.path.join(PLOTS_DIR, f'aod_{args.nm}nm_{date}{suffix}.png')
else:
    plot_path = args.outputfile
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=120)
plt.close(fig)
print(f"  plot: {plot_path}")
