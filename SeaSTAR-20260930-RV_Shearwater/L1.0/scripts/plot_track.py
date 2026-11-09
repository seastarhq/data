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
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import box

# custom seastar modules
import seastar_datautils

# where to find things including
# L10_DATA_DIR PLOTS_DIR
from seastar_filepaths import *

## analysis parameters:
# including
# SEASTAR_TIMEZONE
from seastar_analysis_params import *

# plots the GPS track on a map, from every timestep of one or more L10 files (L06-to-L10_sun.py) together, with each
# hour of local time labelled beside it (hours with no position within LABEL_WINDOW have no label) and the first and
# last positions marked, and named START_NAME. it uses the GPS's own imu_lat and imu_lon, not the L10's
# lat and lon, which are interpolated across dropouts. dropouts read (0, 0), and the GPS can also give a wild
# position just after one or at the start of a run (e.g. 6.19, -21.54), so anything more than --max-offset degrees
# from the median position is left out too; how many of each is printed. the coastline is Natural Earth's, through
# cartopy, which downloads it on first use. --step thins the track to keep the PDF small. --title adds a title; by default there is none.
# writes track_<date>.png and .pdf to PLOTS_DIR, with the date of the first timestep

LAND_COLOUR = "#e8e6df"
COAST_COLOUR = "#8a8981"
GRID_COLOUR = "#e1e0d9"
END_COLOUR = "#1a1a19"
TRACK_COLOUR = "#2a78d6"
# where the deployment started and finished
START_NAME = "Santa Barbara"
# an hour's label needs a position this close to it
LABEL_WINDOW = pd.Timedelta(minutes=2)

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+', help='L10 files, found in L10_DATA_DIR')
parser.add_argument('--max-offset', type=float, default=2.0,
                    help='leave out positions further than this many degrees from the median (default 2)')
parser.add_argument('--step', type=float, default=10, help='seconds between the positions plotted (default 10)')
parser.add_argument('--margin', type=float, default=0.08, help='degrees of map around the track (default 0.08)')
parser.add_argument('--title', action='store_true', help='give the plot a title (default: none)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of PLOTS_DIR/track_<date>.png')
args = parser.parse_args()

L10_data_dir = [L10_DATA_DIR,]
L10_data = np.concatenate([np.load(seastar_datautils.findFile(name, L10_data_dir), allow_pickle=True)['array_data']
                           for name in args.files])
L10_data = L10_data[np.argsort(L10_data['datetime'], kind='stable')]
lat, lon = L10_data['imu_lat'], L10_data['imu_lon']
fixed = (lat != 0) & (lon != 0)
near = (np.abs(lat - np.median(lat[fixed])) <= args.max_offset) & (np.abs(lon - np.median(lon[fixed])) <= args.max_offset)
good = fixed & near
print(f"  {good.sum()} of {len(lat)} positions: left out {np.sum(~fixed)} dropouts and {np.sum(fixed & ~near)} more than "
      f"{args.max_offset:g} degrees from the median")
lat, lon = lat[good], lon[good]

timezone = pytz.timezone(SEASTAR_TIMEZONE)
# pandas can't always find time zones by name, so timezone is a pytz object
times = pd.to_datetime(L10_data['datetime'][good]).tz_localize('UTC').tz_convert(timezone).tz_localize(None)
date = str(L10_data['datetime'].min())[:10]

west, east = lon.min() - args.margin, lon.max() + args.margin
south, north = lat.min() - args.margin, lat.max() + args.margin
data_crs = ccrs.PlateCarree()
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(projection=ccrs.Mercator(central_longitude=(west + east) / 2))
ax.set_extent([west, east, south, north], crs=data_crs)
# clipped to just beyond the map: the PDF would otherwise hold the whole of each land polygon, a whole continent
region = box(west - 1, south - 1, east + 1, north + 1)
land = cfeature.NaturalEarthFeature('physical', 'land', '10m')
ax.add_geometries([polygon.intersection(region) for polygon in land.geometries() if polygon.intersects(region)],
                  crs=data_crs, facecolor=LAND_COLOUR, edgecolor=COAST_COLOUR, linewidth=0.6)
gridlines = ax.gridlines(crs=data_crs, draw_labels=True, color=GRID_COLOUR, linewidth=0.5)
gridlines.top_labels = gridlines.right_labels = False

# the first position of each --step seconds, to keep the PDF small; the labels and end markers use them all
seconds = (times - times[0]).total_seconds().to_numpy()
_, shown = np.unique((seconds // args.step).astype(int), return_index=True)
print(f"  plotting {len(shown)} of the {len(lat)} positions, one per {args.step:g} s")
ax.scatter(lon[shown], lat[shown], s=4, color=TRACK_COLOUR, edgecolors='none', transform=data_crs,
           label='RV Shearwater position')
ax.plot(lon[0], lat[0], 'o', color='white', markeredgecolor=END_COLOUR, markeredgewidth=1.5, markersize=8,
        transform=data_crs, label=f'first, {times[0]:%H:%M}')
ax.plot(lon[-1], lat[-1], 's', color=END_COLOUR, markeredgecolor='white', markeredgewidth=1, markersize=8,
        transform=data_crs, label=f'last, {times[-1]:%H:%M}')
ax.legend(loc='lower left', fontsize=9, frameon=True, framealpha=0.9, edgecolor='none')

# each hour's label sits to the right of the direction of travel, so it's clear of the track
for hour in pd.date_range(times[0].ceil('h'), times[-1].floor('h'), freq='h'):
    i = np.abs(times - hour).argmin()
    if abs(times[i] - hour) > LABEL_WINDOW:
        continue
    before = np.abs(times - (hour - LABEL_WINDOW)).argmin()
    after = np.abs(times - (hour + LABEL_WINDOW)).argmin()
    east = (lon[after] - lon[before]) * np.cos(np.radians(lat[i]))
    north = lat[after] - lat[before]
    length = np.hypot(east, north) or 1.0
    right = np.array([north, -east]) / length
    ax.plot(lon[i], lat[i], 'o', color='white', markeredgecolor=TRACK_COLOUR, markeredgewidth=1.2, markersize=5,
            transform=data_crs, zorder=4)
    ax.annotate(f'{hour:%H:%M}', xy=(lon[i], lat[i]), xycoords=data_crs._as_mpl_transform(ax),
                xytext=tuple(16 * right), textcoords='offset points', ha='left' if right[0] >= 0 else 'right',
                va='center', fontsize=9, color=END_COLOUR, zorder=5,
                path_effects=[patheffects.withStroke(linewidth=2.5, foreground='white')])
ax.annotate(START_NAME, xy=(lon[-1], lat[-1]), xycoords=data_crs._as_mpl_transform(ax), xytext=(0, 10),
            textcoords='offset points', ha='center', va='bottom', fontsize=10, fontweight='bold', color=END_COLOUR,
            zorder=5, path_effects=[patheffects.withStroke(linewidth=2.5, foreground='white')])
ax.text(0.99, 0.015, f'times are {SEASTAR_TIMEZONE}', transform=ax.transAxes, ha='right', va='bottom', fontsize=8,
        color='#52514e')
if args.title:
    ax.set_title(f'SeaSTAR GPS track, {date} ({os.path.basename(ROOT_DIR)})', loc='left', fontsize=10)
fig.tight_layout()

plot_path = args.outputfile if args.outputfile is not None else os.path.join(PLOTS_DIR, f'track_{date}.png')
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=120)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
