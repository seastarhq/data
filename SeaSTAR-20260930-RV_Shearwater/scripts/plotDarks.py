#!/usr/bin/env python3
# the dark level of each channel through the day, from the dark sequences: in
# each one the channels are darkened in turn, ch10 first and ch1 last, a few
# seconds apart and each for 15-25 s, while the instrument goes on sun tracking.

import argparse
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import quicklook as ql

channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_\d+x$")

# a channel counts as steady while its standard deviation over this window
# stays under flatStd.  a dark is steady to ~1e-4 (ch8 to ~3e-3, it is the
# noisy one); so are thick cloud and a spell of steady sun, which is why the
# order of the sequence, not the steadiness alone, picks the darks out:
flatWindow = "2s"
flatStd = 0.005

# a steady stretch shorter than this is not a dark:
minDark = pd.Timedelta(seconds=8)

# trimmed off each end of a dark before it is averaged:
edgeTrim = pd.Timedelta(seconds=1)

# the next channel down goes dark within this long of the one before it:
maxStep = pd.Timedelta(seconds=40)

def channelColumns(frame):
	"""The channel columns, highest channel first: the order they go dark in."""
	channels = [name for name in frame.columns if channelPattern.match(name)]

	return sorted(channels, key=lambda name: -int(channelPattern.match(name).group(1)))

def steadyRuns(series):
	"""[(start, end), ...] of every stretch where the channel holds steady."""
	flat = series.rolling(flatWindow).std() < flatStd
	runs = (flat != flat.shift()).cumsum()

	return [(group.index[0], group.index[-1])
	        for _, group in series[flat].groupby(runs[flat])
	        if group.index[-1] - group.index[0] >= minDark]

def findSequence(frame, columns):
	"""{column: (start, end)} of each channel's dark in one sequence.

	Every steady stretch of the first channel to go dark is tried as the start
	of the sequence, and each channel after it takes the first of its own
	steady stretches to start after the one before it.  The chain that reaches
	the most channels is the sequence: thick cloud and steady sun hold every
	channel steady at once, and do not climb down the channels in turn.
	"""
	candidates = {column: steadyRuns(frame[column]) for column in columns}
	best = {}

	for anchor in candidates[columns[0]]:
		chain = {columns[0]: anchor}
		previous = anchor[0]

		for column in columns[1:]:
			following = [run for run in candidates[column]
			             if previous < run[0] <= previous + maxStep]

			if not following:
				break

			chain[column] = following[0]
			previous = following[0][0]

		if len(chain) > len(best):
			best = chain

	return best

def darkLevels(frame, windows, columns, temperatures):
	"""A row per sequence: when it was, each channel's dark and its spread."""
	rows = []

	for start, end in windows:
		window = ql.timeWindow(frame, start, end)
		sequence = findSequence(window, columns)

		if len(sequence) < len(columns):
			missing = [column for column in columns if column not in sequence]
			print(f"{start}-{end}: no dark found for {', '.join(missing)}")

		if not sequence:
			continue

		first = min(run[0] for run in sequence.values())
		last = max(run[1] for run in sequence.values())
		row = {"start": first, "end": last, "time": first + (last - first) / 2}

		for column, (darkStart, darkEnd) in sequence.items():
			# the first and last second can still catch the channel on its
			# way down or up, which would swamp the spread of the dark:
			dark = window.loc[darkStart + edgeTrim:darkEnd - edgeTrim, column]
			row[column] = dark.median()
			row[f"{column}_std"] = dark.std()
			row[f"{column}_seconds"] = (darkEnd - darkStart).total_seconds()

		# the temperatures over the whole sequence, which is over in ~90 s:
		for column in temperatures:
			row[column] = window.loc[first:last, column].mean()

		rows.append(row)

	return pd.DataFrame(rows).set_index("time")

def plotDarks(levels, columns, temperatures, title):
	"""A panel per channel of its dark level at each sequence, and the temperatures.

	The channels go two to a row, and the temperatures are drawn under each
	column, on the same time axis as it, so a dark can be read straight down
	against the temperature it was taken at.
	"""
	columns = sorted(columns, key=lambda name: int(channelPattern.match(name).group(1)))
	rows = (len(columns) + 1) // 2
	
	fig, axes = plt.subplots(rows + 1, 2, sharex=True, squeeze=False,
	                         figsize=(14, 1.7*(rows + 1) + 1.4))
	fig.patch.set_facecolor('white')
	
	# down the first column and then the second, so the channels read in order:
	order = axes[:rows].T.flatten()
	
	for n, (ax, column) in enumerate(zip(order, columns)):
		colour = ql.panelColours[n % len(ql.panelColours)]
		
		if column in levels.columns:
			ax.errorbar(levels.index, levels[column], yerr=levels[f"{column}_std"],
			            color=colour, marker='o', markersize=4, linewidth=0.8,
			            capsize=2)
		
		ql.stylePanel(ax, f"{column} dark", colour)
	
	for ax in order[len(columns):]:
		ax.set_visible(False)
	
	for ax in axes[rows]:
		for m, column in enumerate(temperatures):
			ax.plot(levels.index, levels[column], marker='o', markersize=3, linewidth=0.8,
			        color=ql.panelColours[m % len(ql.panelColours)], label=column)
		
		ax.legend(loc='lower right', fontsize=8, frameon=False, ncols=len(temperatures))
		ql.stylePanel(ax, "temperature (°C)", ql.gridColour)
		ql.formatTimeAxis(ax, levels)
	
	fig.suptitle(title, fontsize=12, color=ql.textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.96))
	
	return fig

def fitTemperature(levels, column, temperature):
	"""Slope, intercept and r squared of a channel's dark against temperature."""
	x, y = levels[temperature], levels[column]
	slope, intercept = np.polyfit(x, y, 1)
	residual = y - (slope * x + intercept)
	rSquared = 1 - (residual**2).sum() / ((y - y.mean())**2).sum()
	
	return slope, intercept, rSquared

def plotVsTemperature(levels, columns, temperature, title):
	"""A panel per channel of its dark against temperature, with a straight line fitted.

	Each point is named by the time of its sequence, so the warming leg of the
	day can be told from the cooling one if the darks do not retrace it.
	"""
	columns = sorted(columns, key=lambda name: int(channelPattern.match(name).group(1)))
	rows = (len(columns) + 1) // 2
	
	fig, axes = plt.subplots(rows, 2, sharex=True, squeeze=False,
	                         figsize=(14, 2.2*rows + 1.4))
	fig.patch.set_facecolor('white')
	
	order = axes.T.flatten()
	fits = []
	span = np.linspace(levels[temperature].min(), levels[temperature].max(), 2)
	
	for n, (ax, column) in enumerate(zip(order, columns)):
		colour = ql.panelColours[n % len(ql.panelColours)]
		x, y = levels[temperature], levels[column]
		
		ax.errorbar(x, y, yerr=levels[f"{column}_std"], color=colour, marker='o',
		            markersize=4, linestyle='none', capsize=2)
		
		for time, xi, yi in zip(levels.index, x, y):
			ax.annotate(f"{time:%H:%M}", (xi, yi), xytext=(4, 4),
			            textcoords='offset points', fontsize=7, color=ql.textSecondary)
		
		slope, intercept, rSquared = fitTemperature(levels, column, temperature)
		fits.append((column, slope, intercept, rSquared))
		
		ax.plot(span, slope * span + intercept, color=colour, linewidth=0.8,
		        linestyle='--')
		# top right: with the darks falling as it warms, that corner is empty
		ax.text(0.995, 0.94, f"{slope:+.3g} /°C   r² {rSquared:.2f}",
		        transform=ax.transAxes, ha='right', va='top', fontsize=8,
		        color=ql.textSecondary)
		
		# scaled to the points, not their error bars: one sequence with a few
		# stray seconds in a dark otherwise flattens the rest of the panel
		low, high = y.min(), y.max()
		margin = 0.25 * (high - low) if high > low else abs(high) * 0.05
		ax.set_ylim(low - margin, high + margin)
		
		ql.stylePanel(ax, f"{column} dark", colour)
	
	for ax in order[len(columns):]:
		ax.set_visible(False)
	
	for ax in axes[-1]:
		ax.set_xlabel(f"{temperature} (°C), mean over the sequence",
		              color=ql.textSecondary, fontsize=9)
	
	fig.suptitle(title, fontsize=12, color=ql.textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.96))
	
	return fig, fits

def parseWindow(text):
	"""11:02:00-11:04:30, or with dots for the colons, as (start, end)."""
	start, end = text.replace(".", ":").split("-")

	return start, end

def main():
	parser = ql.commonArguments("The dark level of each channel over the day, from the dark sequences.")
	parser.add_argument("--windows", nargs='+', type=parseWindow, required=True, help="a time window around each dark sequence, e.g. 14:24:20-14:26:40")
	parser.add_argument("--table", default=None, help="also write the dark levels to this file")
	parser.add_argument("--temperature", default="t3", help="the temperature to plot the darks against (default t3)")
	parser.add_argument("--fit-file", default=None, dest="fitFile", help="also write the fitted slopes to this file")
	args = parser.parse_args()

	frame = ql.loadDay(args)
	stem = ql.outputStem(frame, args.start, args.end)
	columns = channelColumns(frame)
	temperatures = [name for name in ("t3", "t4", "t5", "t6") if name in frame.columns]

	levels = darkLevels(frame, args.windows, columns, temperatures)

	if levels.empty:
		raise SystemExit("no dark sequences found in those windows")

	table = levels[["start", "end"] + [c for c in columns[::-1] if c in levels]
	               + temperatures]

	with pd.option_context('display.width', 250, 'display.float_format', '{:.5f}'.format):
		print(table.to_string(index=False))

	if args.table:
		with open(args.table, "w") as tableFile:
			tableFile.write("# median dark level of each channel in each dark sequence,"
			                " and the mean temperatures over the sequence\n")
			table.to_csv(tableFile, index=False, float_format="%.6f")

		print(f"Wrote {args.table}")

	fig = plotDarks(levels, columns, temperatures, f"{stem}: dark level per channel")
	ql.savePlots(fig, args.outdir, f"{stem}_dark_levels")
	
	if not args.show:
		plt.close(fig)
	
	if len(levels) < 3:
		print("too few sequences to fit the darks against temperature")
	else:
		fig, fits = plotVsTemperature(levels, columns, args.temperature,
		                              f"{stem}: dark level against {args.temperature}")
		fits = pd.DataFrame(fits, columns=["channel", "slope_per_degC", "intercept", "r_squared"])
		
		print(fits.to_string(index=False))
		
		if args.fitFile:
			with open(args.fitFile, "w") as fitFile:
				fitFile.write(f"# straight line fitted to each channel's dark against"
				              f" {args.temperature}, over {len(levels)} dark sequences\n")
				fits.to_csv(fitFile, index=False, float_format="%.6g")
			
			print(f"Wrote {args.fitFile}")
		
		ql.savePlots(fig, args.outdir, f"{stem}_dark_vs_{args.temperature}")

	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
