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
# SEASTAR_TIMEZONE ANGSTROM_WAVELENGTHS
from seastar_analysis_params import *

# plots the Angstrom exponent against local time, from one or more L10 files (L06-to-L10_sun.py) on one figure:
# only the timesteps that pass the screening. the exponent is the L10 'angstrom' field, fitted over
# ANGSTROM_WAVELENGTHS, and is undefined where any of those AODs is not positive, so those timesteps aren't plotted.
# --screen picks which aod_flags screen the data (default tracking only). the y axis covers the middle 99% of the
# exponents that pass, unless --ymin and --ymax set the limits. --microtops overlays
# a Microtops L1.5 groups file's 440-870 exponent (one row per group of shots, in UTC), its times converted to
# SEASTAR_TIMEZONE. --title adds a title with the date, V0 mode and screening; by default there is none.
# writes angstrom_<date>_<flags>.png and .pdf to PLOTS_DIR, with the date of the first file, or angstrom_<date>.png
# when every flag screens it, and _v0origin after the date for L10 files processed with V0_MODE=origin

SCREEN_FLAGS = {'cloud': AOD_CLOUD, 'tracking': AOD_TRACKING, 'temp_low': AOD_CHANNEL_TEMP_LOW,
                'pressure': AOD_PRESSURE_FILLED, 'position': AOD_POSITION_FILLED, 'signal_low': AOD_SIGNAL_LOW}

UNFLAGGED_COLOUR = "#2a78d6"
MICROTOPS_COLOUR = "#e8833a"
MICROTOPS_FIELD = 'Angstrem 440-870'

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+', help='L10 files, found in L10_DATA_DIR')
parser.add_argument('--screen', nargs='+', choices=SCREEN_FLAGS, default=['tracking'],
                    help='the aod_flags that screen the data (default tracking only)')
parser.add_argument('--ymin', type=float, help='the bottom of the y axis (default: from the exponents that pass)')
parser.add_argument('--ymax', type=float, help='the top of the y axis (default: from the exponents that pass)')
parser.add_argument('--xmin', help='the start of the x axis, HH:MM local time on the date of the first file (default: from the data)')
parser.add_argument('--microtops', help='a Microtops computed_aod_L15_groups file to overlay (times in UTC)')
parser.add_argument('--title', action='store_true', help='give the plot a title (default: none)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of PLOTS_DIR/angstrom_<date>_<flags>.png')
args = parser.parse_args()

L10_data_dir = [L10_DATA_DIR,]
arrays = []
for name in args.files:
    L10_npyfile = seastar_datautils.findFile(name, L10_data_dir)
    L10_npz = np.load(L10_npyfile, allow_pickle=True)
    arrays.append(L10_npz['array_data'])
    metadata = L10_npz['metadata'][()]
L10_data = np.concatenate(arrays)

timezone = pytz.timezone(SEASTAR_TIMEZONE)
# pandas can't always find time zones by name, so timezone is a pytz object
times = pd.to_datetime(L10_data['datetime']).tz_localize('UTC').tz_convert(timezone).tz_localize(None)
angstrom = L10_data['angstrom']
screen_mask = 0
for name in args.screen:
    screen_mask |= SCREEN_FLAGS[name]
good = ((L10_data['aod_flags'] & screen_mask) == 0) & np.isfinite(angstrom)
date = str(L10_data['datetime'].min())[:10]
v0_mode = metadata.get('V0_MODE', 'intercept')

def read_microtops(path, timezone):
    # a few header lines, then a tab-separated table whose header line starts with Date; dates like SEP/30/2026
    with open(path) as f:
        skip = next(i for i, line in enumerate(f) if line.startswith('Date'))
    table = pd.read_csv(path, sep='\t', skiprows=skip)
    table.columns = table.columns.str.strip()
    if MICROTOPS_FIELD not in table.columns:
        sys.exit(f"no {MICROTOPS_FIELD} in {path}")
    utc = pd.to_datetime(table['Date'].str.title() + ' ' + table['Time'], format='%b/%d/%Y %H:%M:%S')
    local = utc.dt.tz_localize('UTC').dt.tz_convert(timezone).dt.tz_localize(None)
    return local.to_numpy(), table[MICROTOPS_FIELD].to_numpy()

fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(times[good], angstrom[good], '.', color=UNFLAGGED_COLOUR, markersize=2.5,
        label=f'passed ({good.sum()})')
if good.any():
    lo, hi = np.percentile(angstrom[good], [0.5, 99.5])
    pad = 0.15 * (hi - lo) + 0.05
    ax.set_ylim(lo - pad, hi + pad)
else:
    ax.text(0.5, 0.5, 'no timesteps pass the screening', transform=ax.transAxes, ha='center', va='center', color='#52514e')
if args.ymin is not None:
    ax.set_ylim(bottom=args.ymin)
if args.ymax is not None:
    ax.set_ylim(top=args.ymax)
if args.microtops is not None:
    mt_times, mt_angstrom = read_microtops(args.microtops, timezone)
    ax.plot(mt_times, mt_angstrom, 'D', color=MICROTOPS_COLOUR, markersize=8, markeredgecolor='white', markeredgewidth=1.5,
            label=f'Microtops L1.5 groups, 440-870 ({len(mt_angstrom)})', zorder=3)
if args.xmin is not None:
    ax.set_xlim(left=pd.Timestamp(f'{date} {args.xmin}'))
locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
ax.set_xlabel(f'time ({SEASTAR_TIMEZONE})')
ax.set_ylabel(f"Ångström exponent ({', '.join(f'{nm:g}' for nm in ANGSTROM_WAVELENGTHS)} nm)")
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
if args.title:
    ax.set_title(f'SeaSTAR L1.0 Ångström exponent, {date} ({os.path.basename(ROOT_DIR)}), {v0_mode} V0, screened by {screened_by}',
                 loc='left', fontsize=10)
fig.tight_layout()

if args.outputfile is None:
    suffix = ('' if v0_mode == 'intercept' else f'_v0{v0_mode}') + ('' if all_flags else '_' + '_'.join(sorted(args.screen)))
    plot_path = os.path.join(PLOTS_DIR, f'angstrom_{date}{suffix}.png')
else:
    plot_path = args.outputfile
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=120)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
