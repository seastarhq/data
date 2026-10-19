#!/usr/bin/env python3
# the radiometer channels while the instrument was sun tracking: the signal
# the day is for, without the stretches spent homing or looking for the sun.

import re

import matplotlib.pyplot as plt

import quicklook as ql

channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_\d+x$")

def channelColumns(frame):
	"""The channel columns, in channel order rather than log order."""
	channels = [name for name in frame.columns if channelPattern.match(name)]
	
	return sorted(channels, key=lambda name: int(channelPattern.match(name).group(1)))

def plotChannels(frame, columns, title, fullRange):
	"""A panel per channel in two columns, all sharing the time axis."""
	rows = (len(columns) + 1) // 2

	fig, axes = plt.subplots(rows, 2, sharex=True, squeeze=False,
	                         figsize=(14, 1.7*rows + 1.4))
	fig.patch.set_facecolor('white')

	# down the first column and then the second, so the channels read in order:
	order = axes.T.flatten()

	for n, (ax, column) in enumerate(zip(order, columns)):
		series = frame[column]
		colour = ql.panelColours[n % len(ql.panelColours)]

		# while tracking the channels flick between the sun and nearly
		# nothing as the spot moves on and off the field of view:
		ql.plotLine(ax, series, colour, dots=True)
		ql.stylePanel(ax, column, colour)

		if not ql.noteFlat(ax, series) and not fullRange:
			ql.setYlim(ax, series)

	for ax in order[len(columns):]:
		ax.set_visible(False)

	for ax in axes[-1]:
		ql.formatTimeAxis(ax, frame)

	fig.suptitle(title, fontsize=12, color=ql.textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.96))

	return fig

def main():
	parser = ql.commonArguments("The radiometer channels while sun tracking, over a day of logs.")
	parser.add_argument("--full-range", action='store_true', dest="fullRange", help="scale each panel to all its data, spikes included")
	args = parser.parse_args()

	frame = ql.loadDay(args)
	stem = ql.outputStem(frame, args.start, args.end)
	columns = channelColumns(frame)

	if not columns:
		raise SystemExit("no channel columns in these logs")

	tracking = frame['state'] == ql.sunTracking
	print(f"sun tracking for {tracking.mean():.0%} of the rows")

	# off the sun the channels are just noise, so they are blanked there and
	# the line breaks rather than joining one stretch of tracking to the next:
	frame = ql.breakGaps(frame[columns].where(tracking, axis=0))

	fig = plotChannels(frame, columns, f"{stem}: radiometer channels while sun tracking",
	                   args.fullRange)
	ql.savePlots(fig, args.outdir, f"{stem}_channels_tracking")

	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
