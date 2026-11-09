#!/usr/bin/env python3

import os
import numpy as np
import argparse
import pandas as pd
import pytz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
from matplotlib.colors import LinearSegmentedColormap
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import box

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *

# where to find things including
# L10_DATA_DIR PLOTS_DIR
from seastar_filepaths import *

## analysis parameters:
# including
# SEASTAR_TIMEZONE ANGSTROM_WAVELENGTHS
from seastar_analysis_params import *

# zoomed-in maps of part of the GPS track, from one or more L10 files (L06-to-L10_sun.py) together, side by side: one
# coloured by the AOD at --nm, one by the Angstrom exponent. each shows the whole track between --start and --end
# (local time) in grey, and over it the timesteps that pass the screening, in colour. --screen picks which aod_flags
# screen the data (default tracking only). the colour scales cover the middle 98% of the values plotted, unless
# --aod-range or --angstrom-range set them. positions are chosen as in plot_track.py: the GPS's own imu_lat and imu_lon,
# without dropouts or anything more than --max-offset degrees from the median. --title adds a title; by default there
# is none.
# writes track_aod_<nm>nm_angstrom_<date>_<flags>.png and .pdf to PLOTS_DIR, with the date of the first timestep, no
# <flags> when every flag screens it, and _v0origin after the date for L10 files processed with V0_MODE=origin

SCREEN_FLAGS = {'cloud': AOD_CLOUD, 'tracking': AOD_TRACKING, 'temp_low': AOD_CHANNEL_TEMP_LOW,
                'pressure': AOD_PRESSURE_FILLED, 'position': AOD_POSITION_FILLED, 'signal_low': AOD_SIGNAL_LOW}

LAND_COLOUR = "#e8e6df"
COAST_COLOUR = "#8a8981"
GRID_COLOUR = "#e1e0d9"
TRACK_COLOUR = "#c9c8c1"
TEXT_COLOUR = "#1a1a19"
# one hue each, light to dark, with the lightest still clear of the white sea
AOD_COLOURS = LinearSegmentedColormap.from_list('aod', ["#86b6ef", "#2a78d6", "#0d366b"])
ANGSTROM_COLOURS = LinearSegmentedColormap.from_list('angstrom', ["#f5b08f", "#eb6834", "#7a2a0c"])
# where the deployment finished
END_NAME = "Santa Barbara"
# an hour's label needs a position this close to it
LABEL_WINDOW = pd.Timedelta(minutes=2)

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+', help='L10 files, found in L10_DATA_DIR')
parser.add_argument('--nm', type=int, default=500, help='the AOD wavelength to plot (default 500)')
parser.add_argument('--start', default='13:30', help='the start of the track, HH:MM local time (default 13:30)')
parser.add_argument('--end', help='the end of the track, HH:MM local time (default: the end of the data)')
parser.add_argument('--screen', nargs='+', choices=SCREEN_FLAGS, default=['tracking'],
                    help='the aod_flags that screen the data (default tracking only)')
parser.add_argument('--aod-range', nargs=2, type=float, metavar=('MIN', 'MAX'), help='the AOD colour scale')
parser.add_argument('--angstrom-range', nargs=2, type=float, metavar=('MIN', 'MAX'), help='the exponent colour scale')
parser.add_argument('--max-offset', type=float, default=2.0,
                    help='leave out positions further than this many degrees from the median (default 2)')
parser.add_argument('--margin', type=float, default=0.03, help='degrees of map around the track (default 0.03)')
parser.add_argument('--title', action='store_true', help='give the plot a title (default: none)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of PLOTS_DIR/track_aod_<nm>nm_angstrom_<date>_<flags>.png')
args = parser.parse_args()

L10_data_dir = [L10_DATA_DIR,]
arrays = []
for name in args.files:
    L10_npz = np.load(seastar_datautils.findFile(name, L10_data_dir), allow_pickle=True)
    arrays.append(L10_npz['array_data'])
    metadata = L10_npz['metadata'][()]
L10_data = np.concatenate(arrays)
L10_data = L10_data[np.argsort(L10_data['datetime'], kind='stable')]
v0_mode = metadata.get('V0_MODE', 'intercept')

timezone = pytz.timezone(SEASTAR_TIMEZONE)
# pandas can't always find time zones by name, so timezone is a pytz object
all_times = pd.to_datetime(L10_data['datetime']).tz_localize('UTC').tz_convert(timezone).tz_localize(None)
date = str(all_times[0])[:10]
lat, lon = L10_data['imu_lat'], L10_data['imu_lon']
fixed = (lat != 0) & (lon != 0)
near = (np.abs(lat - np.median(lat[fixed])) <= args.max_offset) & (np.abs(lon - np.median(lon[fixed])) <= args.max_offset)
keep = fixed & near & (all_times >= pd.Timestamp(f'{date} {args.start}'))
if args.end is not None:
    keep &= all_times <= pd.Timestamp(f'{date} {args.end}')
if not keep.any():
    raise SystemExit(f"no positions after {args.start}")
L10_data, lat, lon, times = L10_data[keep], lat[keep], lon[keep], all_times[keep]

screen_mask = 0
for name in args.screen:
    screen_mask |= SCREEN_FLAGS[name]
passed = (L10_data['aod_flags'] & screen_mask) == 0

west, east = lon.min() - args.margin, lon.max() + args.margin
south, north = lat.min() - args.margin, lat.max() + args.margin
data_crs = ccrs.PlateCarree()
projection = ccrs.Mercator(central_longitude=(west + east) / 2)
# clipped to just beyond the map: the PDF would otherwise hold the whole of each land polygon, a whole continent
region = box(west - 1, south - 1, east + 1, north + 1)
land = [polygon.intersection(region) for polygon in cfeature.NaturalEarthFeature('physical', 'land', '10m').geometries()
        if polygon.intersects(region)]
halo = [patheffects.withStroke(linewidth=2.5, foreground='white')]

def panel(ax, values, colours, limits, colourbar_label, fig, left_labels):
    good = passed & np.isfinite(values)
    ax.set_extent([west, east, south, north], crs=data_crs)
    ax.add_geometries(land, crs=data_crs, facecolor=LAND_COLOUR, edgecolor=COAST_COLOUR, linewidth=0.6)
    gridlines = ax.gridlines(crs=data_crs, draw_labels=True, color=GRID_COLOUR, linewidth=0.5)
    gridlines.top_labels = gridlines.right_labels = False
    gridlines.left_labels = left_labels
    ax.scatter(lon, lat, s=3, color=TRACK_COLOUR, edgecolors='none', transform=data_crs)
    vmin, vmax = limits if limits is not None else np.percentile(values[good], [1, 99])
    points = ax.scatter(lon[good], lat[good], c=values[good], s=12, cmap=colours, vmin=vmin, vmax=vmax, edgecolors='none',
                        transform=data_crs, zorder=3)
    print(f"  {colourbar_label}: {good.sum()} of {len(values)} timesteps, colour scale {vmin:.3g} to {vmax:.3g}")
    for hour in pd.date_range(times[0].ceil('h'), times[-1].floor('h'), freq='h'):
        i = np.abs(times - hour).argmin()
        if abs(times[i] - hour) > LABEL_WINDOW:
            continue
        ax.plot(lon[i], lat[i], 'o', color='white', markeredgecolor=TEXT_COLOUR, markeredgewidth=1, markersize=5,
                transform=data_crs, zorder=4)
        ax.annotate(f'{hour:%H:%M}', xy=(lon[i], lat[i]), xycoords=data_crs._as_mpl_transform(ax), xytext=(10, 0),
                    textcoords='offset points', ha='left', va='center', fontsize=9, color=TEXT_COLOUR, zorder=5,
                    path_effects=halo)
    ax.annotate(END_NAME, xy=(lon[-1], lat[-1]), xycoords=data_crs._as_mpl_transform(ax), xytext=(0, 8),
                textcoords='offset points', ha='left', va='bottom', fontsize=10, fontweight='bold', color=TEXT_COLOUR,
                zorder=5, path_effects=halo)
    ax.text(0.98, 0.015, f'times are {SEASTAR_TIMEZONE}', transform=ax.transAxes, ha='right', va='bottom', fontsize=8,
            color='#52514e')
    fig.colorbar(points, ax=ax, shrink=0.8, pad=0.03, extend='both', label=colourbar_label)

fig, (ax_aod, ax_ang) = plt.subplots(1, 2, figsize=(10, 7.5), subplot_kw={'projection': projection})
panel(ax_aod, L10_data[f'aod_{args.nm}nm'], AOD_COLOURS, args.aod_range, f'AOD {args.nm} nm', fig, True)
panel(ax_ang, L10_data['angstrom'], ANGSTROM_COLOURS, args.angstrom_range,
      f"Ångström exponent ({', '.join(f'{nm:g}' for nm in ANGSTROM_WAVELENGTHS)} nm)", fig, False)
all_flags = set(args.screen) == set(SCREEN_FLAGS)
screened_by = 'all aod_flags' if all_flags else ', '.join(args.screen) + ' flags only'
if args.title:
    fig.suptitle(f'SeaSTAR L1.0 along the track, {date} from {args.start} ({os.path.basename(ROOT_DIR)}), {v0_mode} V0, '
                 f'screened by {screened_by}', fontsize=10)
fig.tight_layout()

if args.outputfile is None:
    suffix = ('' if v0_mode == 'intercept' else f'_v0{v0_mode}') + ('' if all_flags else '_' + '_'.join(sorted(args.screen)))
    plot_path = os.path.join(PLOTS_DIR, f'track_aod_{args.nm}nm_angstrom_{date}{suffix}.png')
else:
    plot_path = args.outputfile
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=120)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
