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

# plot_aod.py and plot_angstrom.py on one figure, from one or more L10 files (L06-to-L10_sun.py): the AOD at one
# wavelength above the Angstrom exponent, against the same local time axis. the AOD panel has the timesteps that
# pass the screening in colour and the screened ones faintly behind them; the exponent panel has only those that
# pass. --screen picks which aod_flags screen the data (default tracking only). the y axes cover the values that
# pass unless --aod-ymax, --angstrom-ymin or --angstrom-ymax set them, and anything beyond a limit is cut off.
# --microtops overlays a Microtops L1.5 groups file (one row per group of shots, in UTC) on both panels: its AOD at
# the same wavelength and its 440-870 exponent, its times converted to SEASTAR_TIMEZONE. --title adds a title with
# the date, V0 mode and screening; by default there is none.
# writes aod_<nm>nm_angstrom_<date>_<flags>.png and .pdf to PLOTS_DIR, with the date of the first file, no <flags>
# when every flag screens it, and _v0origin after the date for L10 files processed with V0_MODE=origin

SCREEN_FLAGS = {'cloud': AOD_CLOUD, 'tracking': AOD_TRACKING, 'temp_low': AOD_CHANNEL_TEMP_LOW,
                'pressure': AOD_PRESSURE_FILLED, 'position': AOD_POSITION_FILLED, 'signal_low': AOD_SIGNAL_LOW}

UNFLAGGED_COLOUR = "#2a78d6"
FLAGGED_COLOUR = "#b8b7b0"
MICROTOPS_COLOUR = "#e8833a"
MICROTOPS_ANGSTROM = 'Angstrem 440-870'

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+', help='L10 files, found in L10_DATA_DIR')
parser.add_argument('--nm', type=int, default=500, help='the AOD wavelength to plot (default 500)')
parser.add_argument('--screen', nargs='+', choices=SCREEN_FLAGS, default=['tracking'],
                    help='the aod_flags that screen the data (default tracking only)')
parser.add_argument('--aod-ymax', type=float, help='the top of the AOD axis (default: from the AODs that pass)')
parser.add_argument('--angstrom-ymin', type=float, help='the bottom of the exponent axis (default: from the exponents that pass)')
parser.add_argument('--angstrom-ymax', type=float, help='the top of the exponent axis (default: from the exponents that pass)')
parser.add_argument('--xmin', help='the start of the x axis, HH:MM local time on the date of the first file (default: from the data)')
parser.add_argument('--microtops', help='a Microtops computed_aod_L15_groups file to overlay (times in UTC)')
parser.add_argument('--title', action='store_true', help='give the plot a title (default: none)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of PLOTS_DIR/aod_<nm>nm_angstrom_<date>_<flags>.png')
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
angstrom = L10_data['angstrom']
screen_mask = 0
for name in args.screen:
    screen_mask |= SCREEN_FLAGS[name]
passed = (L10_data['aod_flags'] & screen_mask) == 0
aod_good = passed & np.isfinite(aod)
aod_flagged = ~passed & np.isfinite(aod)
angstrom_good = passed & np.isfinite(angstrom)
date = str(L10_data['datetime'].min())[:10]
v0_mode = metadata.get('V0_MODE', 'intercept')

def read_microtops(path, fields, timezone):
    # a few header lines, then a tab-separated table whose header line starts with Date; dates like SEP/30/2026
    with open(path) as f:
        skip = next(i for i, line in enumerate(f) if line.startswith('Date'))
    table = pd.read_csv(path, sep='\t', skiprows=skip)
    table.columns = table.columns.str.strip()
    for name in fields:
        if name not in table.columns:
            sys.exit(f"no {name} in {path}")
    utc = pd.to_datetime(table['Date'].str.title() + ' ' + table['Time'], format='%b/%d/%Y %H:%M:%S')
    local = utc.dt.tz_localize('UTC').dt.tz_convert(timezone).dt.tz_localize(None)
    return local.to_numpy(), [table[name].to_numpy() for name in fields]

def overlay_microtops(ax, mt_times, values, label):
    ax.plot(mt_times, values, 'D', color=MICROTOPS_COLOUR, markersize=8, markeredgecolor='white', markeredgewidth=1.5,
            label=f'{label} ({len(values)})', zorder=3)

def finish_panel(ax):
    ax.grid(True, color='#e1e0d9', linewidth=0.5)
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    legend = ax.legend(loc='upper left', frameon=False, fontsize=9)
    # the data dots are too small to read in the legend, so every legend marker is drawn at one size
    for handle in legend.legend_handles:
        handle.set_markersize(7)

fig, (ax_aod, ax_ang) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

ax_aod.plot(times[aod_flagged], aod[aod_flagged], '.', color=FLAGGED_COLOUR, markersize=1.5,
            label=f'screened ({aod_flagged.sum()})')
ax_aod.plot(times[aod_good], aod[aod_good], '.', color=UNFLAGGED_COLOUR, markersize=2.5,
            label=f'passed ({aod_good.sum()})')
if aod_good.any():
    lo, hi = np.percentile(aod[aod_good], [0.5, 99.5])
    pad = 0.15 * (hi - lo) + 0.01
    ax_aod.set_ylim(max(lo - pad, 0.0) if lo >= 0 else lo - pad, hi + pad)
    if args.aod_ymax is not None:
        ax_aod.set_ylim(min(ax_aod.get_ylim()[0], 0.0), args.aod_ymax)
ax_aod.set_ylabel(f'AOD {args.nm} nm')

ax_ang.plot(times[angstrom_good], angstrom[angstrom_good], '.', color=UNFLAGGED_COLOUR, markersize=2.5,
            label=f'passed ({angstrom_good.sum()})')
if angstrom_good.any():
    lo, hi = np.percentile(angstrom[angstrom_good], [0.5, 99.5])
    pad = 0.15 * (hi - lo) + 0.05
    ax_ang.set_ylim(lo - pad, hi + pad)
if args.angstrom_ymin is not None:
    ax_ang.set_ylim(bottom=args.angstrom_ymin)
    print(f"  {(angstrom[angstrom_good] < args.angstrom_ymin).sum()} of {angstrom_good.sum()} exponents that pass "
          f"are below {args.angstrom_ymin:g}, off the plot")
if args.angstrom_ymax is not None:
    ax_ang.set_ylim(top=args.angstrom_ymax)
ax_ang.set_ylabel(f"Ångström exponent ({', '.join(f'{nm:g}' for nm in ANGSTROM_WAVELENGTHS)} nm)")

if args.microtops is not None:
    mt_times, (mt_aod, mt_angstrom) = read_microtops(args.microtops, [f'AOD {args.nm}', MICROTOPS_ANGSTROM], timezone)
    overlay_microtops(ax_aod, mt_times, mt_aod, 'Microtops L1.5 groups')
    overlay_microtops(ax_ang, mt_times, mt_angstrom, 'Microtops L1.5 groups, 440-870')

if args.xmin is not None:
    ax_ang.set_xlim(left=pd.Timestamp(f'{date} {args.xmin}'))
locator = mdates.AutoDateLocator()
ax_ang.xaxis.set_major_locator(locator)
ax_ang.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
ax_ang.set_xlabel(f'time ({SEASTAR_TIMEZONE})')
finish_panel(ax_aod)
finish_panel(ax_ang)
all_flags = set(args.screen) == set(SCREEN_FLAGS)
screened_by = 'all aod_flags' if all_flags else ', '.join(args.screen) + ' flags only'
if args.title:
    ax_aod.set_title(f'SeaSTAR L1.0 AOD at {args.nm} nm and Ångström exponent, {date} ({os.path.basename(ROOT_DIR)}), '
                     f'{v0_mode} V0, screened by {screened_by}', loc='left', fontsize=10)
fig.tight_layout()

if args.outputfile is None:
    suffix = ('' if v0_mode == 'intercept' else f'_v0{v0_mode}') + ('' if all_flags else '_' + '_'.join(sorted(args.screen)))
    plot_path = os.path.join(PLOTS_DIR, f'aod_{args.nm}nm_angstrom_{date}{suffix}.png')
else:
    plot_path = args.outputfile
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=120)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
