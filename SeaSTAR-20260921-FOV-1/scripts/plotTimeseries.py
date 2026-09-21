#!/usr/bin/env python3
# quicklook time series of every column in a SeaSTAR log: one panel per
# variable, sharing a time axis, gathered into a figure per subsystem.

import argparse
import glob
import os
import re
import sys

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# columns are gathered into a figure per subsystem, in this order.  the spec is
# either a list of names or a pattern.  anything the log carries that none of
# these claim is still plotted, in an "other" figure at the end: a quicklook
# that silently drops a column is worse than a busy one.
groups = [
	("channels", "radiometer channels", re.compile(r"^(?:j3_)?ch\d+_\d+x$")),
	("temperatures", "temperatures", ["t3", "t4", "t5", "t6", "boardTemp", "imuT"]),
	("stage", "stage and target position", ["sx", "sy", "sb", "tx", "ty"]),
	("pointing", "sun position and encoders", ["sunAz", "sunAlt", "q1", "q2", "q3"]),
	("attitude", "attitude quaternion", ["qw", "qx", "qy", "qz"]),
	("command", "commanded quaternion", ["cqw", "cqx", "cqy", "cqz"]),
	("motion", "rates and accelerations", ["rx", "ry", "rz", "ax", "ay", "az"]),
	("imu", "imu", ["imuP", "imuLat", "imuLon", "imuBlend"]),
	("housekeeping", "housekeeping", ["hMin", "hMax", "hScale", "m1Gain", "m2Gain", "state"]),
]

# one colour per panel within a figure, from a colourblind-safe categorical
# palette (blue, orange, green, yellow, magenta):
panelColours = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

textPrimary = "#0b0b0b"
textSecondary = "#52514e"
gridColour = "#d9d8d4"

# a stack taller than this is unreadable, so a long group is split over several
# figures rather than squeezed into one:
maxPanels = 6

# a single spike (a startup transient, a power cycle) otherwise flattens a whole
# panel, so by default we scale to this quantile range and say how many points
# fall outside it:
ylimQuantile = 0.001

# a column with no more distinct values than this, all of them whole numbers, is
# a state or a gain setting rather than a measurement, and is drawn as steps:
discreteLevels = 10

def readLog(inFile):
	"""Read the log into a frame indexed by time, with the columns unpadded."""
	frame = pd.read_csv(inFile, skipinitialspace=True)
	frame.columns = [name.strip() for name in frame.columns]
	
	if 'time' not in frame.columns:
		raise SystemExit(f"{inFile}: header has no time column")
	
	frame['time'] = pd.to_datetime(frame['time'])
	
	return frame.set_index('time').sort_index()

def matchGroup(spec, names):
	"""The columns a group claims, in the order the group asks for them."""
	if isinstance(spec, re.Pattern):
		return [name for name in names if spec.match(name)]
	
	return [name for name in spec if name in names]

def assignGroups(names):
	"""Split the columns into [(slug, title, [column, ...]), ...].

	Every column lands in exactly one group; whatever is left over at the end
	is grouped as "other" so that nothing goes unplotted.
	"""
	assigned = []
	claimed = set()
	
	for slug, title, spec in groups:
		columns = [name for name in matchGroup(spec, names) if name not in claimed]
		
		if columns:
			assigned.append((slug, title, columns))
			claimed.update(columns)
	
	leftover = [name for name in names if name not in claimed]
	
	if leftover:
		assigned.append(("other", "other columns", leftover))
	
	return assigned

def chunkGroup(slug, title, columns):
	"""Split one group into figures of at most maxPanels panels."""
	chunks = [columns[i:i+maxPanels] for i in range(0, len(columns), maxPanels)]
	
	if len(chunks) == 1:
		return [(slug, title, chunks[0])]
	
	return [(f"{slug}{n+1}", f"{title} ({n+1} of {len(chunks)})", chunk)
	        for n, chunk in enumerate(chunks)]

def setYlim(ax, series):
	"""Scale the panel to the bulk of the data, flagging anything off-scale."""
	low, high = series.quantile([ylimQuantile, 1-ylimQuantile])
	
	if not low < high:
		return
	
	margin = 0.05 * (high - low)
	ax.set_ylim(low - margin, high + margin)
	
	offscale = int(((series < low - margin) | (series > high + margin)).sum())
	
	if offscale:
		ax.text(0.995, 0.94, f"{offscale} points off-scale", transform=ax.transAxes,
		        va='top', ha='right', fontsize=8, color=textSecondary)

def isDiscrete(series):
	"""Whether a column is a state or a setting rather than a measurement."""
	values = series.dropna()
	
	if values.empty or values.nunique() > discreteLevels:
		return False
	
	return bool(np.all(values == values.round()))

def stylePanel(ax, label, colour):
	"""Recessive grid and axes, with the column named on the panel itself."""
	ax.grid(True, color=gridColour, linewidth=0.5, alpha=0.8)
	ax.set_axisbelow(True)
	ax.tick_params(labelsize=8, colors=textSecondary)
	
	for side in ('top', 'right'):
		ax.spines[side].set_visible(False)
	
	for side in ('left', 'bottom'):
		ax.spines[side].set_color(gridColour)
	
	# direct label on the panel: identity is never colour alone
	ax.text(0.005, 0.94, label, transform=ax.transAxes, va='top', ha='left',
	        fontsize=9, color=textPrimary,
	        bbox=dict(facecolor='white', edgecolor=colour, linewidth=1.0,
	                  boxstyle='round,pad=0.25', alpha=0.85))

def plotGroup(frame, title, columns, fullRange):
	"""One panel per column, all sharing the time axis.

	Separate panels rather than one set of axes: these columns share neither
	a scale nor a unit, and stacking them together would be misleading.
	"""
	fig, axes = plt.subplots(len(columns), 1, sharex=True, squeeze=False,
	                         figsize=(11, 1.6*len(columns) + 1.6))
	axes = axes[:, 0]
	fig.patch.set_facecolor('white')
	
	for n, (ax, column) in enumerate(zip(axes, columns)):
		series = frame[column]
		colour = panelColours[n % len(panelColours)]
		
		ax.plot(series.index, series, color=colour, linewidth=1.0,
		        drawstyle='steps-post' if isDiscrete(series) else 'default')
		
		stylePanel(ax, column, colour)
		
		# a dead channel is worth seeing at a glance, and its panel is
		# otherwise a flat line with an arbitrary y scale:
		if series.nunique(dropna=True) <= 1:
			value = series.dropna()
			note = f"constant at {value.iloc[0]:g}" if len(value) else "no data"
			
			ax.text(0.5, 0.5, note, transform=ax.transAxes, va='center',
			        ha='center', fontsize=9, color=textSecondary)
		elif not fullRange:
			setYlim(ax, series)
	
	axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
	axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
	axes[-1].set_xlabel(f"time on {frame.index[0].date()}", color=textSecondary,
	                    fontsize=9)
	
	fig.suptitle(title, fontsize=12, color=textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.96))
	
	return fig

def main():
	parser = argparse.ArgumentParser(description="Quicklook time series of every column in a scan log.")
	parser.add_argument("inFile", nargs='?', default=None, help="log CSV to plot (default: newest *log.csv here)")
	parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of the log")
	parser.add_argument("--start", default=None, help="only plot from this time, e.g. 11:05")
	parser.add_argument("--end", default=None, help="only plot up to this time, e.g. 11:14")
	parser.add_argument("--full-range", action='store_true', dest="fullRange", help="scale each panel to all its data, spikes included")
	parser.add_argument("--outdir", default="plots", help="directory to write the plots into (created if needed)")
	parser.add_argument("--show", action='store_true', help="open the figures as well as saving them")
	
	args = parser.parse_args()
	
	inFile = args.inFile
	
	if inFile is None:
		logs = sorted(glob.glob("*log.csv"))
		
		if not logs:
			raise SystemExit("no *log.csv here, and no file given")
		
		inFile = logs[-1]
	
	if not args.show:
		matplotlib.use('Agg')
	
	frame = readLog(inFile)
	
	# the first rows are logged while the instrument is still starting up and
	# every column reads zero, which flattens the panels underneath them:
	frame = frame.iloc[args.startLog:]
	
	# a start/end time without a date is taken to be on the day of the data:
	day = frame.index[0].date()
	
	if args.start is not None:
		frame = frame.loc[frame.index >= pd.Timestamp(f"{day} {args.start}")]
	
	if args.end is not None:
		frame = frame.loc[frame.index <= pd.Timestamp(f"{day} {args.end}")]
	
	if frame.empty:
		raise SystemExit(f"{inFile}: no rows left to plot")
	
	numeric = frame.apply(pd.to_numeric, errors='coerce')
	
	# anything that will not read as a number cannot be a panel, but it is
	# named rather than dropped in silence:
	unplottable = [name for name in numeric.columns if numeric[name].isna().all()]
	plottable = [name for name in numeric.columns if name not in unplottable]
	
	if not plottable:
		raise SystemExit(f"{inFile}: no numeric columns to plot")
	
	print(f"Processing {inFile}")
	print(f"rows: {len(frame)} from {frame.index[0]} to {frame.index[-1]}")
	print(f"columns: {len(plottable)} plotted")
	
	if unplottable:
		print(f"not numeric, not plotted: {unplottable}")
	
	stem = os.path.splitext(os.path.basename(inFile))[0]
	
	if args.outdir:
		os.makedirs(args.outdir, exist_ok=True)
	
	for slug, title, columns in assignGroups(plottable):
		for chunkSlug, chunkTitle, chunk in chunkGroup(slug, title, columns):
			fig = plotGroup(numeric, f"{stem}: {chunkTitle}", chunk, args.fullRange)
			
			outPath = os.path.join(args.outdir, f"{stem}_ts_{chunkSlug}.png")
			fig.savefig(outPath, dpi=150)
			
			print(f"Wrote {outPath} ({', '.join(chunk)})")
			
			if not args.show:
				plt.close(fig)
	
	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
