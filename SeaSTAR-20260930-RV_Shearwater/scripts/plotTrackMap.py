#!/usr/bin/env python3
# where the ship went over the day, from the instrument's own GPS, drawn on
# the coastline.

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

import quicklook as ql

trackColour = ql.panelColours[0]

# the smallest area drawn around the track, in degrees, so a day spent tied up
# in port is not drawn at the scale of the dock:
minSpan = 0.1

def mapExtent(lat, lon):
	"""Lon/lat limits around the track, with a margin and at least minSpan wide."""
	extent = []

	for values in (lon, lat):
		low, high = values.min(), values.max()
		centre, span = (low + high) / 2, max(high - low, minSpan) * 1.2
		extent += [centre - span/2, centre + span/2]

	return extent

def plotTrackMap(frame, title):
	"""The track as one line on the coast, with where it started and finished."""
	track = ql.breakGaps(frame[['imuLat', 'imuLon']])
	fixes = frame[['imuLat', 'imuLon']].dropna()

	fig = plt.figure(figsize=(10, 9))
	fig.patch.set_facecolor('white')
	ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

	ax.set_extent(mapExtent(fixes['imuLat'], fixes['imuLon']), crs=ccrs.PlateCarree())
	ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor="#efeee9")
	ax.add_feature(cfeature.OCEAN.with_scale('10m'), facecolor="#f7fafd")
	ax.add_feature(cfeature.COASTLINE.with_scale('10m'), edgecolor=ql.textSecondary,
	               linewidth=0.6)

	ax.plot(track['imuLon'], track['imuLat'], color=trackColour, linewidth=1.2,
	        transform=ccrs.PlateCarree(), rasterized=True)

	# the ends are marked by shape and named, not coloured, so the track stays
	# one colour throughout.  the map is drawn in PlateCarree, so its data
	# coordinates are lon/lat:
	for marker, label, n, offset in (("o", "start", 0, (8, -14)), ("s", "end", -1, (8, 6))):
		time, row = fixes.index[n], fixes.iloc[n]

		ax.plot(row['imuLon'], row['imuLat'], marker=marker, markersize=7,
		        markerfacecolor='white', markeredgecolor=trackColour,
		        markeredgewidth=1.5, transform=ccrs.PlateCarree(), zorder=5)
		ax.annotate(f"{label} {time:%H:%M}", (row['imuLon'], row['imuLat']),
		            xytext=offset, textcoords='offset points', fontsize=9,
		            color=ql.textPrimary)

	gridlines = ax.gridlines(draw_labels=True, color=ql.gridColour, linewidth=0.5)
	gridlines.top_labels = gridlines.right_labels = False
	gridlines.xlabel_style = gridlines.ylabel_style = dict(size=8, color=ql.textSecondary)

	ax.set_title(title, fontsize=12, color=ql.textPrimary, loc='left')
	fig.tight_layout()

	return fig

def main():
	parser = ql.commonArguments("The ship track over a day of logs, on the coastline.")
	args = parser.parse_args()

	frame = ql.loadDay(args)
	stem = ql.outputStem(frame, args.start, args.end)

	if frame['imuLat'].isna().all():
		raise SystemExit("no GPS fixes in these logs")

	fig = plotTrackMap(frame, f"{stem}: ship track")
	ql.savePlots(fig, args.outdir, f"{stem}_track_map")

	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
