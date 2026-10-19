#!/usr/bin/env python3
# what the quicklook scripts share: reading a day of SeaSTAR logs into one
# frame on a common time axis, the instrument states, and the plot styling.

import argparse
import os

import matplotlib
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

scriptDir = os.path.dirname(os.path.abspath(__file__))
rootDir = os.path.dirname(scriptDir)

# one colour per panel within a figure, from a colourblind-safe categorical
# palette (blue, orange, green, yellow, magenta):
panelColours = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

textPrimary = "#0b0b0b"
textSecondary = "#52514e"
gridColour = "#d9d8d4"

# a single spike (a startup transient, a power cycle) otherwise flattens a whole
# panel, so by default we scale to this quantile range and say how many points
# fall outside it:
ylimQuantile = 0.001

# a column with no more distinct values than this, all of them whole numbers, is
# a state or a gain setting rather than a measurement, and is drawn as steps:
discreteLevels = 10

# samples come every 20 ms; a jump longer than this is the instrument off (or
# between logs), and the line is broken there rather than drawn across it:
gapSeconds = 1.0

# columns that read exactly zero until the part of the instrument that reports
# them is up (the radiometer board, the IMU, the tracking settings), and that
# cannot really be zero once it is: there a zero is made NaN, not plotted:
zeroMeansMissing = ["t3", "t4", "t5", "t6", "boardTemp", "imuT", "imuP",
                    "tx", "ty", "m1Gain", "m2Gain", "imuBlend",
                    "hMin", "hMax", "hScale"]

# the state the instrument is in while it closes the loop on the sun, from
# ../setup/states:
sunTracking = 2

def readLog(inFile, startLog):
	"""Read one log into a frame indexed by time, with the columns unpadded."""
	frame = pd.read_csv(inFile, skipinitialspace=True)
	frame.columns = [name.strip() for name in frame.columns]

	if 'time' not in frame.columns:
		raise SystemExit(f"{inFile}: header has no time column")

	frame['time'] = pd.to_datetime(frame['time'])

	# the first rows are logged while the instrument is still starting up and
	# every column reads zero, which flattens the panels underneath them:
	frame = frame.iloc[startLog:]

	return frame.set_index('time')

def readLogs(inFiles, startLog=10):
	"""Every log of the day as one frame, in time order, all numeric.

	Placeholder zeros the instrument logs before it has a value are made NaN,
	so that they are neither drawn nor counted in the panel scaling: rows that
	are zero throughout, the columns in zeroMeansMissing, and a position (or sun position, which is worked out
	from it) of exactly 0, 0 before the GPS has a fix.
	"""
	frames = [readLog(inFile, startLog) for inFile in inFiles]
	frame = pd.concat(frames).sort_index()
	frame = frame.apply(pd.to_numeric, errors='coerce')

	frame = frame.loc[~(frame.fillna(0) == 0).all(axis=1)]

	for column in zeroMeansMissing:
		if column in frame.columns:
			frame.loc[frame[column] == 0, column] = np.nan
	
	for pair in (["imuLat", "imuLon"], ["sunAz", "sunAlt"]):
		if set(pair) <= set(frame.columns):
			noFix = (frame[pair] == 0).all(axis=1)
			frame.loc[noFix, pair] = np.nan

	return frame

def breakGaps(frame):
	"""The frame with a row of NaN in every gap, so a line is not drawn across it."""
	gaps = frame.index.to_series().diff() > pd.Timedelta(seconds=gapSeconds)

	if not gaps.any():
		return frame

	before = frame.index[np.flatnonzero(gaps.to_numpy()) - 1]
	blanks = pd.DataFrame(np.nan, index=before + pd.Timedelta(milliseconds=1),
	                      columns=frame.columns)

	return pd.concat([frame, blanks]).sort_index()

def readStates(path=None):
	"""{number: name} for the instrument states, from ../setup/states."""
	if path is None:
		path = os.path.join(rootDir, "setup", "states")

	states = {}

	if not os.path.exists(path):
		return states

	with open(path) as stateFile:
		for line in stateFile:
			number, _, name = line.strip().partition(" ")

			if number.isdigit():
				states[int(number)] = name.strip()

	return states

def timeWindow(frame, start, end):
	"""The rows between start and end, given as times on the day of the data."""
	day = frame.index[0].date()

	if start is not None:
		frame = frame.loc[frame.index >= pd.Timestamp(f"{day} {start}")]

	if end is not None:
		frame = frame.loc[frame.index <= pd.Timestamp(f"{day} {end}")]

	if frame.empty:
		raise SystemExit("no rows left to plot in that time window")

	return frame

def outputStem(frame, start, end):
	"""2026-09-30, or 2026-09-30_1329-1429 for a window of the day."""
	stem = f"{frame.index[0]:%Y-%m-%d}"

	if start is not None or end is not None:
		stem += f"_{frame.index[0]:%H%M}-{frame.index[-1]:%H%M}"

	return stem

def commonArguments(description):
	"""The arguments every quicklook script takes."""
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument("inFiles", nargs='+', help="log CSVs of the day, in any order")
	parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of each log")
	parser.add_argument("--start", default=None, help="only plot from this time, e.g. 13:29")
	parser.add_argument("--end", default=None, help="only plot up to this time, e.g. 14:29")
	parser.add_argument("--outdir", default=os.path.join(rootDir, "plots"), help="directory to write the plots into (created if needed)")
	parser.add_argument("--show", action='store_true', help="open the figures as well as saving them")

	return parser

def loadDay(args):
	"""The logs named on the command line, cut to the window asked for."""
	if not args.show:
		matplotlib.use('Agg')

	frame = readLogs(args.inFiles, args.startLog)
	frame = timeWindow(frame, args.start, args.end)

	print(f"rows: {len(frame)} from {frame.index[0]} to {frame.index[-1]}")

	os.makedirs(args.outdir, exist_ok=True)

	return frame

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

def noteFlat(ax, series):
	"""Say so on a panel whose column never changes, and return whether it did."""
	if series.nunique(dropna=True) > 1:
		return False

	value = series.dropna()
	note = f"constant at {value.iloc[0]:g}" if len(value) else "no data"

	ax.text(0.5, 0.5, note, transform=ax.transAxes, va='center',
	        ha='center', fontsize=9, color=textSecondary)

	return True

def formatTimeAxis(ax, frame):
	"""Clock times along the bottom panel, with the day under them."""
	ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
	# ticks closer than a minute apart, on a zoom of a few minutes, would all
	# read the same to the minute:
	span = frame.index[-1] - frame.index[0]
	clock = "%H:%M:%S" if span < pd.Timedelta(minutes=15) else "%H:%M"
	ax.xaxis.set_major_formatter(mdates.DateFormatter(clock))
	ax.set_xlabel(f"log time on {frame.index[0].date()}", color=textSecondary,
	              fontsize=9)

def savePlots(fig, outdir, name):
	"""The figure as a PNG and a PDF.

	The data lines are drawn rasterized (see plotLine), so the PDF keeps its
	axes and text as vectors without carrying a million points per panel.
	"""
	for extension in ("png", "pdf"):
		outPath = os.path.join(outdir, f"{name}.{extension}")
		fig.savefig(outPath, dpi=150)
		print(f"Wrote {outPath}")

def plotLine(ax, series, colour, dots=False, **kwargs):
	"""A column against time, as steps if it is a setting.

	With dots, each sample is a point and nothing joins them: a signal that
	flicks between two levels faster than the plot can resolve then shows as
	the two levels, not as a solid band filled in by the lines between them.
	"""
	if dots:
		ax.plot(series.index, series, linestyle='none', marker='.', markersize=0.6,
		        markeredgewidth=0, color=colour, rasterized=True, **kwargs)
		return
	
	if isDiscrete(series):
		kwargs.setdefault('drawstyle', 'steps-post')

	kwargs.setdefault('linewidth', 0.8)
	
	ax.plot(series.index, series, color=colour, rasterized=True, **kwargs)
