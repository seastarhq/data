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
import matplotlib.patheffects as patheffects
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import box

# maps of a PACE OCI L2 UAA aerosol granule, zoomed on the track of a SeaSTAR deployment: one panel for each AOD
# wavelength in --nm, on one shared colour scale, and one of the cloud fraction. each shows the track from --track-start
# on, and where the ship was when OCI scanned it.
#
# the AOD is screened by Quality_flag_Aerosol_Optical_Depth >= --min-qa (default 2). the granule labels this flag
# 'Land=0 Ocean,0,1,2,3': every land retrieval is 0, so any --min-qa above 0 leaves ocean only. a panel with nothing
# left says so. the cloud fraction is not screened.
#
# the default --nm are the PACE wavelengths closest to the SeaSTAR L1.0 AOD channels, which aren't all the same:
#   SeaSTAR  340  380  440  500  675  870  1020
#   PACE     354  388  480  480  670  870  (1240 is the closest, too far to compare)
# 550 is included too: SeaSTAR has that filter, and it is PACE's reference wavelength.
#
# writes pace_map_<granule time>_qa<min-qa>.png and .pdf to ../plots

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRACK_DIR = os.path.join(HERE, '..', '..', 'SeaSTAR-20260930-RV_Shearwater', 'pickle')

LAND_COLOUR = "#e8e6df"
COAST_COLOUR = "#8a8981"
GRID_COLOUR = "#e1e0d9"
TRACK_COLOUR = "#1a1a19"
TEXT_COLOUR = "#1a1a19"
MUTED_COLOUR = "#52514e"
# one hue each, light to dark, with the lightest still clear of the white sea (AOD as in plot_track_aod.py)
AOD_COLOURS = LinearSegmentedColormap.from_list('aod', ["#86b6ef", "#2a78d6", "#0d366b"])
CLOUD_COLOURS = LinearSegmentedColormap.from_list('cloud', ["#c9b8ec", "#7d5bc9", "#35206f"])
PANEL_COLUMNS = 4

parser = argparse.ArgumentParser()
parser.add_argument('granule', help='the PACE OCI L2 AER_UAA .nc file')
parser.add_argument('--nm', type=float, nargs='+', default=[354, 388, 480, 550, 670, 870],
                    help='the AOD wavelengths to plot, from those in the granule (default 354 388 480 550 670 870)')
parser.add_argument('--min-qa', type=int, choices=[0, 1, 2, 3], default=2,
                    help='the lowest Quality_flag_Aerosol_Optical_Depth to plot (default 2; 0 keeps every retrieval)')
parser.add_argument('--aod-range', nargs=2, type=float, metavar=('MIN', 'MAX'), default=[0, 0.3],
                    help='the AOD colour scale (default 0 0.3)')
parser.add_argument('--track-dir', default=DEFAULT_TRACK_DIR,
                    help='the directory of SeaSTAR_*.L10 files (default: the RV Shearwater pickle directory)')
parser.add_argument('--track-start', default='20:30',
                    help='the start of the track, HH:MM UTC on the day of the granule (default 20:30)')
parser.add_argument('--max-offset', type=float, default=2.0,
                    help='leave out positions further than this many degrees from the median (default 2)')
parser.add_argument('--margin', type=float, default=0.5, help='degrees of map around the track (default 0.5)')
parser.add_argument('-o', '--outputfile', help='the plot to write, instead of ../plots/pace_map_<time>_qa<min-qa>.png')
args = parser.parse_args()

# the granule: its variables are in groups, and its wavelengths are at the root
wavelengths = xr.open_dataset(args.granule)['Wavelength_Used_all'].values
geolocation = xr.open_dataset(args.granule, group='geolocation_data')
geophysical = xr.open_dataset(args.granule, group='geophysical_data')
scan_times = pd.to_datetime(xr.open_dataset(args.granule, group='scan_line_attributes')['scantime'].values)
grid_lat, grid_lon = geolocation['latitude'].values, geolocation['longitude'].values
aod = geophysical['Aerosol_Optical_Depth'].values
# stored as an int scaled by 0.001, so 3 comes back as 3.0000002
quality = np.round(geophysical['Quality_flag_Aerosol_Optical_Depth'].values)
cloud_fraction = geophysical['Aerosol_Cld_Fraction_Land_Ocean'].values

missing = [nm for nm in args.nm if nm not in wavelengths]
if missing:
    raise SystemExit(f"no AOD at {missing} nm: the granule has {wavelengths.tolist()}")

# the track, with positions chosen as in plot_track.py: no dropouts, nothing far from the median
names = [name for name in sorted(glob.glob(os.path.join(args.track_dir, 'SeaSTAR_*.L10'))) if '_v0' not in name]
if not names:
    raise SystemExit(f"no L10 files in {args.track_dir}")
L10_data = np.concatenate([np.load(name, allow_pickle=True)['array_data'] for name in names])
L10_data = L10_data[np.argsort(L10_data['datetime'], kind='stable')]
times = pd.to_datetime(L10_data['datetime'])
lat, lon = L10_data['imu_lat'], L10_data['imu_lon']
fixed = (lat != 0) & (lon != 0)
near = (np.abs(lat - np.median(lat[fixed])) <= args.max_offset) & (np.abs(lon - np.median(lon[fixed])) <= args.max_offset)
start = pd.Timestamp(f'{scan_times[0].date()} {args.track_start}')
keep = fixed & near & (times >= start)
if not keep.any():
    raise SystemExit(f"no positions after {start}")
lat, lon, times = lat[keep], lon[keep], times[keep]


def distance_km(cell_lat, cell_lon, point_lat, point_lon):
    return 111.2 * np.hypot(cell_lat - point_lat, (cell_lon - point_lon) * np.cos(np.radians(point_lat)))


def ship_at(time):
    return np.abs(times - time).argmin()


# the ship's position decides which scan line it's under and that line's time decides the position, but the ship moves
# so little in one granule that once round is enough
i = ship_at(scan_times[len(scan_times) // 2])
line, column = np.unravel_index(distance_km(grid_lat, grid_lon, lat[i], lon[i]).argmin(), grid_lat.shape)
overpass = scan_times[line]
i = ship_at(overpass)
if abs(times[i] - overpass) > pd.Timedelta(minutes=10):
    raise SystemExit(f"no position within 10 minutes of the overpass at {overpass}: the closest is {times[i]}")
distance = distance_km(grid_lat, grid_lon, lat[i], lon[i])
line, column = np.unravel_index(distance.argmin(), distance.shape)
print(f"  overpass {overpass:%Y-%m-%d %H:%M:%S} UTC, ship at {lat[i]:.3f}, {lon[i]:.3f}")
print(f"  closest cell {distance.min():.1f} km away, column {column} of {grid_lat.shape[1]}, "
      f"sensor zenith {geolocation['sensor_zenith_angle'].values[line, column]:.1f} degrees")

west, east = lon.min() - args.margin, lon.max() + args.margin
south, north = lat.min() - args.margin, lat.max() + args.margin
in_map = (grid_lat >= south) & (grid_lat <= north) & (grid_lon >= west) & (grid_lon <= east)
if not in_map.any():
    raise SystemExit("the granule doesn't cover the track")
# a block of cells just beyond the map, so that it's filled to the edges and the PDF holds no more than it shows
lines, columns = np.where(in_map)
block = (slice(max(lines.min() - 2, 0), lines.max() + 3), slice(max(columns.min() - 2, 0), columns.max() + 3))

data_crs = ccrs.PlateCarree()
projection = ccrs.Mercator(central_longitude=(west + east) / 2)
# clipped to just beyond the map: the PDF would otherwise hold the whole of each land polygon, a whole continent
region = box(west - 1, south - 1, east + 1, north + 1)
land = [polygon.intersection(region) for polygon in cfeature.NaturalEarthFeature('physical', 'land', '10m').geometries()
        if polygon.intersects(region)]
halo = [patheffects.withStroke(linewidth=2.5, foreground='white')]


def panel(ax, values, colours, limits, title, left_labels, bottom_labels):
    ax.set_extent([west, east, south, north], crs=data_crs)
    ax.add_geometries(land, crs=data_crs, facecolor=LAND_COLOUR, edgecolor='none', zorder=0)
    mesh = ax.pcolormesh(grid_lon[block], grid_lat[block], values[block], cmap=colours, vmin=limits[0], vmax=limits[1],
                         shading='nearest', transform=data_crs, zorder=1)
    ax.add_geometries(land, crs=data_crs, facecolor='none', edgecolor=COAST_COLOUR, linewidth=0.6, zorder=2)
    gridlines = ax.gridlines(crs=data_crs, draw_labels=True, color=GRID_COLOUR, linewidth=0.5, zorder=2)
    gridlines.top_labels = gridlines.right_labels = False
    gridlines.left_labels, gridlines.bottom_labels = left_labels, bottom_labels
    gridlines.xlocator = gridlines.ylocator = MultipleLocator(0.5)
    gridlines.xlabel_style = gridlines.ylabel_style = {'size': 8, 'color': MUTED_COLOUR}
    ax.plot(lon, lat, color=TRACK_COLOUR, linewidth=1, transform=data_crs, zorder=3)
    ax.plot(lon[i], lat[i], 'o', color='white', markeredgecolor=TEXT_COLOUR, markeredgewidth=1.2, markersize=7,
            transform=data_crs, zorder=4)
    ax.set_title(title, fontsize=10, color=TEXT_COLOUR)
    count = np.isfinite(values[in_map]).sum()
    if count == 0:
        ax.text(0.5, 0.12, f'no cells with QA ≥ {args.min_qa}', transform=ax.transAxes, ha='center', va='center',
                fontsize=10, color=TEXT_COLOUR, path_effects=halo, zorder=5)
    print(f"  {title}: {count} of {in_map.sum()} cells")
    return mesh


panels = len(args.nm) + 1
rows = -(-(panels + 1) // PANEL_COLUMNS)  # with a slot for the key
fig, axes = plt.subplots(rows, PANEL_COLUMNS, figsize=(3.1 * PANEL_COLUMNS, 3.3 * rows), layout='constrained',
                         subplot_kw={'projection': projection})
axes = axes.ravel()


def labels(n):
    return n % PANEL_COLUMNS == 0, n + PANEL_COLUMNS >= panels


aod_axes = axes[:len(args.nm)]
for n, (ax, nm) in enumerate(zip(aod_axes, args.nm)):
    values = aod[:, :, np.where(wavelengths == nm)[0][0]]
    values = np.where(quality >= args.min_qa, values, np.nan)
    aod_mesh = panel(ax, values, AOD_COLOURS, args.aod_range, f'AOD {nm:g} nm', *labels(n))
cloud_ax = axes[len(args.nm)]
cloud_mesh = panel(cloud_ax, cloud_fraction, CLOUD_COLOURS, (0, 1), 'Cloud fraction', *labels(len(args.nm)))
fig.colorbar(aod_mesh, ax=list(aod_axes), shrink=0.7, pad=0.01, extend='max', label='AOD')

for ax in axes[panels + 1:]:
    ax.set_visible(False)
# the slot after the panels holds the key, and the cloud fraction's colour bar so that it doesn't squeeze its panel
key_ax = axes[panels]
key_ax.set_axis_off()
fig.colorbar(cloud_mesh, cax=key_ax.inset_axes([0.1, 0.12, 0.8, 0.06]), orientation='horizontal', label='Cloud fraction')
key_ax.legend(handles=[Line2D([], [], color=TRACK_COLOUR, linewidth=1, label=f'Ship track from {args.track_start} UTC'),
                       Line2D([], [], marker='o', linestyle='none', color='white', markeredgecolor=TEXT_COLOUR,
                              markersize=7, label=f'Ship at overpass, {overpass:%H:%M} UTC'),
                       Patch(facecolor='white', edgecolor=COAST_COLOUR, label='Sea, no data'),
                       Patch(facecolor=LAND_COLOUR, edgecolor=COAST_COLOUR, label='Land, no data')],
              loc='upper center', frameon=False, fontsize=9, labelcolor=TEXT_COLOUR)
fig.suptitle(f'PACE OCI L2 aerosol, {overpass:%Y-%m-%d}, AOD with QA ≥ {args.min_qa}', fontsize=11, color=TEXT_COLOUR)

if args.outputfile is None:
    plot_path = os.path.join(HERE, '..', 'plots', f'pace_map_{scan_times[0]:%Y%m%dT%H%M%S}_qa{args.min_qa}.png')
else:
    plot_path = args.outputfile
plot_path = os.path.normpath(plot_path)
os.makedirs(os.path.dirname(os.path.abspath(plot_path)), exist_ok=True)
fig.savefig(plot_path, dpi=150)
fig.savefig(os.path.splitext(plot_path)[0] + '.pdf')
plt.close(fig)
print(f"  plot: {plot_path}")
