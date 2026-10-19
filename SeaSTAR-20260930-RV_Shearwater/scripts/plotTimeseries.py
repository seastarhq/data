#!/usr/bin/env python3
# quicklook time series of every column in a day of SeaSTAR logs: one panel per
# variable, sharing a time axis, gathered into a figure per subsystem.

import re

import matplotlib.pyplot as plt

import quicklook as ql

# columns are gathered into a figure per subsystem, in this order.  the spec is
# either a list of names or a pattern.  anything the log carries that none of
# these claim is still plotted, in an "other" figure at the end: a quicklook
# that silently drops a column is worse than a busy one.
channelPattern = re.compile(r"^(?:j3_)?ch\d+_\d+x$")

groups = [
	("channels", "radiometer channels", channelPattern),
	("temperatures", "temperatures", ["t3", "t4", "t5", "t6", "boardTemp", "imuT"]),
	("stage", "stage and target position", ["sx", "sy", "sb", "tx", "ty"]),
	("pointing", "sun position and encoders", ["sunAz", "sunAlt", "q1", "q2", "q3"]),
	("attitude", "attitude quaternion", ["qw", "qx", "qy", "qz"]),
	("command", "commanded quaternion", ["cqw", "cqx", "cqy", "cqz"]),
	("motion", "rates and accelerations", ["rx", "ry", "rz", "ax", "ay", "az"]),
	("imu", "imu", ["imuP", "imuLat", "imuLon", "imuBlend"]),
	("housekeeping", "housekeeping", ["hMin", "hMax", "hScale", "m1Gain", "m2Gain", "state"]),
]

# a stack taller than this is unreadable, so a long group is split over several
# figures rather than squeezed into one:
maxPanels = 6

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
		colour = ql.panelColours[n % len(ql.panelColours)]

		ql.plotLine(ax, series, colour, dots=bool(channelPattern.match(column)))
		ql.stylePanel(ax, column, colour)

		# a dead channel is worth seeing at a glance, and its panel is
		# otherwise a flat line with an arbitrary y scale:
		if not ql.noteFlat(ax, series) and not fullRange:
			ql.setYlim(ax, series)

	ql.formatTimeAxis(axes[-1], frame)

	fig.suptitle(title, fontsize=12, color=ql.textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.96))

	return fig

def main():
	parser = ql.commonArguments("Quicklook time series of every column in a day of logs.")
	parser.add_argument("--full-range", action='store_true', dest="fullRange", help="scale each panel to all its data, spikes included")
	args = parser.parse_args()

	frame = ql.loadDay(args)

	# anything that will not read as a number cannot be a panel, but it is
	# named rather than dropped in silence:
	unplottable = [name for name in frame.columns if frame[name].isna().all()]
	plottable = [name for name in frame.columns if name not in unplottable]

	print(f"columns: {len(plottable)} plotted")

	if unplottable:
		print(f"not numeric, not plotted: {unplottable}")

	stem = ql.outputStem(frame, args.start, args.end)
	frame = ql.breakGaps(frame)

	for slug, title, columns in assignGroups(plottable):
		for chunkSlug, chunkTitle, chunk in chunkGroup(slug, title, columns):
			fig = plotGroup(frame, f"{stem}: {chunkTitle}", chunk, args.fullRange)
			ql.savePlots(fig, args.outdir, f"{stem}_ts_{chunkSlug}")

			if not args.show:
				plt.close(fig)

	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
