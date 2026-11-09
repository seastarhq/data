#!/usr/bin/env python3

import argparse
import glob
import os
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# the SeaSTAR AOD at --nm against time, from the PACE OCI overpass to the end of the ship data, with the AOD of the
# PACE cell the ship is in at each moment overlaid as a line across the time it spends in that cell. the PACE AOD is a
# snapshot from the overpass, so the further right, the older it is compared with the ship's measurement.
#
# the ship's cell is the one with the nearest centre, which is the cell containing it as long as the grid is locally
# regular. cells without an AOD at --min-qa or above are shaded. the granule's quality flag is 0 for every land cell,
# and most of the cells along a coastal track are flagged land, so the default --min-qa is 0: a higher one can leave
# nothing to overlay.
#
# PACE has no AOD at most SeaSTAR wavelengths, so it's interpolated to --nm between the two either side, linearly in
# log(AOD) against log(wavelength), which is the Angstrom power law between them. --pace-nm uses one of PACE's own
# wavelengths instead, for a SeaSTAR channel close to it: with --nm 675 --pace-nm 670, the interpolation would need
# the AOD at 870, which land cells don't have.
#
# only the timesteps that pass --screen are plotted.
#
# writes ship_vs_pace_<nm>nm_<granule time>_qa<min-qa>_<flags>.png and .pdf to ../plots, with _pace<pace-nm> after
# <nm>nm if that's set

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRACK_DIR = os.path.join(HERE, '..', '..', 'SeaSTAR-20260930-RV_Shearwater', 'pickle')

# the AOD_* bits of seastar_error_flags.py
SCREEN_FLAGS = {'cloud': 1, 'tracking': 2, 'temp_low': 4, 'pressure': 8, 'position': 16, 'signal_low': 32}

SHIP_COLOUR = "#2a78d6"
PACE_COLOUR = "#e8833a"
NO_CELL_COLOUR = "#f1f0ea"
DIVIDER_COLOUR = "#c9c8c1"
GRID_COLOUR = "#e1e0d9"
TEXT_COLOUR = "#1a1a19"
MUTED_COLOUR = "#52514e"

parser = argparse.ArgumentParser()
parser.add_argument('granule', help='the PACE OCI L2 AER_UAA .nc file')
parser.add_argument('--nm', type=int, default=500, help='the SeaSTAR AOD wavelength to plot (default 500)')
parser.add_argument('--pace-nm', type=int, help="one of PACE's wavelengths to plot (default: interpolated to --nm)")
parser.add_argument('--screen', nargs='+', choices=SCREEN_FLAGS, default=['tracking'],
                    help='the aod_flags that screen the ship data (default tracking only)')
parser.add_argument('--min-qa', type=int, choices=[0, 1, 2, 3], default=0,
                    help='the lowest Quality_flag_Aerosol_Optical_Depth to overlay (default 0)')
parser.add_argument('--ymax', type=float, help='the top of the y axis (default: from the AODs that pass)')
parser.add_argument('--track-dir', default=DEFAULT_TRACK_DIR,
                    help='the directory of SeaSTAR_*.L10 files (default: the RV Shearwater pickle directory)')
parser.add_argument('--max-offset', type=float, default=2.0,
                    help='leave out positions further than this many degrees from the median (default 2)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of the name above in ../plots')
args = parser.parse_args()

# the ship, from the first position of the day
names = [name for name in sorted(glob.glob(os.path.join(args.track_dir, 'SeaSTAR_*.L10'))) if '_v0' not in name]
if not names:
    raise SystemExit(f"no L10 files in {args.track_dir}")
L10_data = np.concatenate([np.load(name, allow_pickle=True)['array_data'] for name in names])
L10_data = L10_data[np.argsort(L10_data['datetime'], kind='stable')]
field = f'aod_{args.nm}nm'
if field not in L10_data.dtype.names:
    raise SystemExit(f"no {field} in the L10 files")
lat, lon = L10_data['imu_lat'], L10_data['imu_lon']
fixed = (lat != 0) & (lon != 0)
near = (np.abs(lat - np.median(lat[fixed])) <= args.max_offset) & (np.abs(lon - np.median(lon[fixed])) <= args.max_offset)
L10_data = L10_data[fixed & near]
times = pd.to_datetime(L10_data['datetime'])
lat, lon = L10_data['imu_lat'], L10_data['imu_lon']

# the granule
wavelengths = xr.open_dataset(args.granule)['Wavelength_Used_all'].values
geolocation = xr.open_dataset(args.granule, group='geolocation_data')
geophysical = xr.open_dataset(args.granule, group='geophysical_data')
scan_times = pd.to_datetime(xr.open_dataset(args.granule, group='scan_line_attributes')['scantime'].values)
grid_lat, grid_lon = geolocation['latitude'].values, geolocation['longitude'].values
aod = geophysical['Aerosol_Optical_Depth'].values
# stored as an int scaled by 0.001, so 3 comes back as 3.0000002
quality = np.round(geophysical['Quality_flag_Aerosol_Optical_Depth'].values)

pace_nm = args.nm if args.pace_nm is None else args.pace_nm
if args.pace_nm is not None and args.pace_nm not in wavelengths:
    raise SystemExit(f"no AOD at {args.pace_nm} nm: the granule has {wavelengths.tolist()}")
if not wavelengths[0] <= pace_nm <= wavelengths[-1]:
    raise SystemExit(f"{pace_nm} nm is outside the granule's {wavelengths[0]:g} to {wavelengths[-1]:g} nm")
upper = np.searchsorted(wavelengths, pace_nm)
lower = upper if wavelengths[upper] == pace_nm else upper - 1


def pace_aod(line, column):
    below, above = aod[line, column, lower], aod[line, column, upper]
    if lower == upper:
        return below
    if not (below > 0 and above > 0):
        return np.nan
    fraction = np.log(pace_nm / wavelengths[lower]) / np.log(wavelengths[upper] / wavelengths[lower])
    return np.exp(np.log(below) + fraction * (np.log(above) - np.log(below)))


def nearest_cell(cell_lines, cell_columns, point_lat, point_lon):
    distance = np.hypot(grid_lat[cell_lines, cell_columns] - point_lat,
                        (grid_lon[cell_lines, cell_columns] - point_lon) * np.cos(np.radians(point_lat)))
    return cell_lines[distance.argmin()], cell_columns[distance.argmin()]


# only the cells around the ship need searching
around = ((grid_lat >= lat.min() - 1) & (grid_lat <= lat.max() + 1) & (grid_lon >= lon.min() - 1) & (grid_lon <= lon.max() + 1))
if not around.any():
    raise SystemExit("the granule doesn't cover the track")
cell_lines, cell_columns = np.where(around)

# the ship's position decides which scan line it's under and that line's time decides the position, but the ship moves
# so little in one granule that once round is enough
i = np.abs(times - scan_times[len(scan_times) // 2]).argmin()
overpass = scan_times[nearest_cell(cell_lines, cell_columns, lat[i], lon[i])[0]]
i = np.abs(times - overpass).argmin()
if abs(times[i] - overpass) > pd.Timedelta(minutes=10):
    raise SystemExit(f"no position within 10 minutes of the overpass at {overpass}: the closest is {times[i]}")
overpass = scan_times[nearest_cell(cell_lines, cell_columns, lat[i], lon[i])[0]]

after = times >= overpass
L10_data, times, lat, lon = L10_data[after], times[after], lat[after], lon[after]
ship_aod = L10_data[field]
screen_mask = 0
for name in args.screen:
    screen_mask |= SCREEN_FLAGS[name]
good = ((L10_data['aod_flags'] & screen_mask) == 0) & np.isfinite(ship_aod)

# the runs of timesteps in one cell
cells = [nearest_cell(cell_lines, cell_columns, point_lat, point_lon) for point_lat, point_lon in zip(lat, lon)]
starts = [0] + [n for n in range(1, len(cells)) if cells[n] != cells[n - 1]]
ends = starts[1:] + [len(cells)]

fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(times[good], ship_aod[good], '.', color=SHIP_COLOUR, markersize=2.5, zorder=3)

print(f"  overpass {overpass:%Y-%m-%d %H:%M:%S} UTC; AOD at {args.nm} nm, ship median of the timesteps that pass")
overlaid = []
for start, end in zip(starts, ends):
    line, column = cells[start]
    # each run ends where the next begins, so that the shading and the lines have no gaps
    t0, t1 = times[start], times[min(end, len(times) - 1)]
    value = pace_aod(line, column) if quality[line, column] >= args.min_qa else np.nan
    ship_median = np.median(ship_aod[start:end][good[start:end]]) if good[start:end].any() else np.nan
    print(f"  {t0:%H:%M:%S}-{t1:%H:%M:%S} cell ({line}, {column}): ship {ship_median:.3f} ({good[start:end].sum()} of "
          f"{end - start}), PACE {value:.3f}, QA {quality[line, column]:.0f}, "
          f"{(t0 - overpass).total_seconds() / 60:.0f}-{(t1 - overpass).total_seconds() / 60:.0f} min after overpass")
    if start > 0:
        ax.axvline(t0, color=DIVIDER_COLOUR, linewidth=0.6, zorder=1)
    if np.isfinite(value):
        ax.plot([t0, t1], [value, value], color=PACE_COLOUR, linewidth=2.5, solid_capstyle='butt', zorder=4)
        overlaid.append((t0, t1, value, quality[line, column]))
    else:
        ax.axvspan(t0, t1, color=NO_CELL_COLOUR, linewidth=0, zorder=0)

if good.any():
    values = np.concatenate([ship_aod[good], [value for _, _, value, _ in overlaid]])
    lo, hi = np.percentile(ship_aod[good], [0.5, 99.5])
    lo, hi = min(lo, values.min()), max(hi, min(values.max(), hi))
    pad = 0.15 * (hi - lo) + 0.01
    ax.set_ylim(max(lo - pad, 0.0), hi + pad)
else:
    ax.text(0.5, 0.5, 'no timesteps pass the screening', transform=ax.transAxes, ha='center', va='center', color=MUTED_COLOUR)
if args.ymax is not None:
    ax.set_ylim(min(ax.get_ylim()[0], 0.0), args.ymax)
ax.set_xlim(times[0], times[-1])
for t0, t1, value, cell_quality in overlaid:
    ax.annotate(f'{value:.3f}, QA {cell_quality:.0f}', xy=(t0 + (t1 - t0) / 2, value), xytext=(0, -7),
                textcoords='offset points', ha='center', va='top', fontsize=9, color=TEXT_COLOUR, zorder=5)

locator = mdates.AutoDateLocator()
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax.set_xlabel(f'{overpass:%Y-%m-%d}, time (UTC), from the overpass at {overpass:%H:%M:%S}', color=MUTED_COLOUR)
ax.set_ylabel(f'AOD {args.nm} nm' if pace_nm == args.nm else f'AOD, SeaSTAR {args.nm} nm, PACE {pace_nm} nm')
ax.grid(True, axis='y', color=GRID_COLOUR, linewidth=0.5)
ax.set_axisbelow(True)
for side in ('top', 'right'):
    ax.spines[side].set_visible(False)
pace_label = (f'PACE cell the ship is in, at {wavelengths[lower]:g} nm' if lower == upper else
              f'PACE cell the ship is in, interpolated from {wavelengths[lower]:g} and {wavelengths[upper]:g} nm')
screened_by = ', '.join(args.screen)
ax.legend(handles=[Line2D([], [], marker='.', linestyle='none', color=SHIP_COLOUR, markersize=7,
                          label=f'SeaSTAR, passed {screened_by} ({good.sum()})'),
                   Line2D([], [], color=PACE_COLOUR, linewidth=2.5, label=pace_label),
                   Patch(facecolor=NO_CELL_COLOUR, edgecolor=DIVIDER_COLOUR, label=f'PACE cell with no AOD at QA ≥ {args.min_qa}')],
          loc='upper center', bbox_to_anchor=(0.5, -0.2), ncols=3, frameon=False, fontsize=9)
fig.tight_layout()

if args.outputfile is None:
    flags = '_'.join(sorted(args.screen))
    pace_tag = '' if args.pace_nm is None else f'_pace{args.pace_nm}'
    plot_path = os.path.join(HERE, '..', 'plots',
                             f'ship_vs_pace_{args.nm}nm{pace_tag}_{scan_times[0]:%Y%m%dT%H%M%S}_qa{args.min_qa}_{flags}.png')
else:
    plot_path = args.outputfile
plot_path = os.path.normpath(plot_path)
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=150)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
