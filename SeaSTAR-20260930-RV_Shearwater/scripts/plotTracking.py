#!/usr/bin/env python3
# how well the sun was tracked over the day: where the sun spot sat on the
# sensor against where it was meant to be, how far off that was while sun
# tracking, which state the instrument was in, and the tracking settings.

import matplotlib.pyplot as plt
import numpy as np

import quicklook as ql

def trackingError(frame):
	"""Distance of the spot from the target, only while sun tracking.

	In the other states the spot is wherever it happens to fall (or the
	target is not set yet), so a distance would mean nothing.
	"""
	error = np.hypot(frame['sx'] - frame['tx'], frame['sy'] - frame['ty'])

	return error.where(frame['state'] == ql.sunTracking)

def stateSummary(frame, states):
	"""Minutes spent in each state, from the time between samples."""
	step = frame.index.to_series().diff().dt.total_seconds()

	# a gap between logs is not time in whatever state came after it:
	step = step.where(step <= ql.gapSeconds, 0).fillna(0)
	minutes = step.groupby(frame['state']).sum() / 60

	return [(int(state), states.get(int(state), "unknown"), minutes[state])
	        for state in minutes.index if minutes[state] > 0]

def plotTracking(frame, title, states):
	"""Spot and target, tracking error, state and settings, sharing a time axis."""
	error = trackingError(frame)

	panels = [("spot x (sx) and target (tx)", [("sx", "sx"), ("tx", "tx")]),
	          ("spot y (sy) and target (ty)", [("sy", "sy"), ("ty", "ty")]),
	          ("tracking error |s - t| while sun tracking", None),
	          ("state", [("state", None)]),
	          ("motor gains", [("m1Gain", "m1Gain"), ("m2Gain", "m2Gain")]),
	          ("imuBlend", [("imuBlend", None)])]

	fig, axes = plt.subplots(len(panels), 1, sharex=True, figsize=(11, 13))
	fig.patch.set_facecolor('white')

	gapped = ql.breakGaps(frame.assign(error=error))

	for n, (ax, (label, columns)) in enumerate(zip(axes, panels)):
		colour = ql.panelColours[n % len(ql.panelColours)]

		if columns is None:
			ql.plotLine(ax, gapped['error'], colour)
			ql.setYlim(ax, error.dropna())
			ax.set_ylim(bottom=0)
		else:
			for m, (column, legend) in enumerate(columns):
				# the target is drawn over the spot, in black, as the
				# reference the spot is read against:
				lineColour = ql.textPrimary if column in ("tx", "ty") else \
				             ql.panelColours[(n + m) % len(ql.panelColours)]
				ql.plotLine(ax, gapped[column], lineColour, label=legend,
				            zorder=3 if column in ("tx", "ty") else 2)

			if len(columns) > 1:
				ax.legend(loc='lower right', fontsize=8, frameon=False, ncols=len(columns))

			if column not in ("state", "m1Gain", "m2Gain", "imuBlend"):
				ql.setYlim(ax, frame[[c for c, _ in columns]].stack())

		ql.stylePanel(ax, label, colour)

	# the state panel is read by name, not number:
	stateAx = axes[3]
	seen = sorted(int(s) for s in frame['state'].dropna().unique())
	stateAx.set_yticks(seen)
	stateAx.set_yticklabels([f"{s} {states.get(s, '')}" for s in seen])
	stateAx.set_ylim(min(seen) - 0.5, max(seen) + 0.5)

	ql.formatTimeAxis(axes[-1], frame)

	fig.suptitle(title, fontsize=12, color=ql.textPrimary, x=0.01, ha='left')
	fig.tight_layout(rect=(0.01, 0, 1, 0.97))

	return fig, error

def main():
	parser = ql.commonArguments("How well the sun was tracked over a day of logs.")
	parser.add_argument("--states", default=None, help="file naming the states (default ../setup/states)")
	args = parser.parse_args()

	frame = ql.loadDay(args)
	states = ql.readStates(args.states)
	stem = ql.outputStem(frame, args.start, args.end)

	fig, error = plotTracking(frame, f"{stem}: sun tracking", states)

	print("time in each state:")

	for state, name, minutes in stateSummary(frame, states):
		print(f"  {state} {name:<20s} {minutes:7.1f} min")

	error = error.dropna()

	if len(error):
		median, p95 = error.quantile([0.5, 0.95])
		print(f"tracking error while sun tracking: median {median:.4f}, 95% {p95:.4f}")

	ql.savePlots(fig, args.outdir, f"{stem}_tracking")

	if args.show:
		plt.show()

if __name__ == '__main__':
	main()
