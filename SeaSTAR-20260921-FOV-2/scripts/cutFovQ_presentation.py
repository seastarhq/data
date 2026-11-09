#!/usr/bin/env python3
# the same FOV cross-sections as cutFov_presentation.py, but drawn against the
# measured motor angles q1 and q2 rather than the commanded stage position.
#
# the cells are still assigned on the commanded position (tx, ty), which is
# exact and gives an unambiguous grid; only the position each cell is plotted
# at changes, to the mean of the motor angle over that cell's settled samples.
# each drawn cut carries its own angles, since a neighbouring row or column was
# scanned at a different time and so at a different pointing.
#
# the two angles are not interchangeable: in the 2026-09-21 scans q1 carries
# the y sweep (~70 deg per stage unit) while q2 barely moves along a row, so an
# x cut against q2 is tracking drift rather than a profile.  only one cut is
# drawn, the y cut against q1 by default; --cut x and --angle pick the other
# combinations, and the script prints the span of the axis so a degenerate one
# is obvious.

import argparse
import glob
import os
import re
import sys

import matplotlib
import matplotlib.pyplot as plt

from matplotlib.ticker import MultipleLocator
import numpy as np

# Channel columns are named ch<N>_1x in current logs and j3_ch<N>_1x in older ones.
channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_1x$")

# channel -> centre wavelength in nm of its bandpass filter, from the hardware
# configuration (hardware/configuration-sept-2026.md):
channelWavelengths = {
	1: 380,
	2: 440,
	3: 500,
	4: 550,
	5: 675,
	6: 340,
	7: 870,
	8: 940,
	9: 940,
	10: 1020,
}

# ch8 and ch9 are the two 940 nm channels, which sit in the water vapour band;
# they and ch4 (550 nm) are left out of these plots:
excludedChannels = (4, 8, 9)

# commanded positions are rounded to this many decimals before being treated as
# the same grid point, to absorb float noise in the log:
gridDecimals = 4

# samples further than this from the commanded position are still in transit
# between grid points and are left out of the cell average:
defaultSettleTolerance = 0.002

# the centroid that picks the centre row and column ignores cells below this
# fraction of the channel's peak, so the background does not pull it about:
centroidFloor = 0.05

# the background is taken as this quantile of the grid, which is far below the
# spot as long as the scan range is a few times the spot:
backgroundQuantile = 0.25

# an axis whose cells span less than this many degrees carries no scan: it is
# drawn anyway, with a warning, since the point of the plot is to show what the
# angle did:
degenerateSpan = 1.0

# one colour per channel, cycling if more than ten are drawn:
channelColours = plt.get_cmap('tab10').colors

def readHeader(inFile):
	with open(inFile) as f:
		return [name.strip() for name in f.readline().split(',')]

def findChannels(names):
	"""Return [(number, columnIndex, name), ...] for every channel column, in channel order."""
	channels = []

	for i, name in enumerate(names):
		match = channelPattern.match(name)
		if match:
			channels.append((int(match.group(1)), i, name))

	return sorted(channels)

def channelLabel(number):
	"""The channel's label on the plots: its wavelength, or its number if that is unknown."""
	if number in channelWavelengths:
		return f"{channelWavelengths[number]} nm"

	return f"ch{number}"

def parseChannelList(spec):
	"""Parse a channel selection such as "1,2,7" or "1-5,10" into a list of numbers."""
	wanted = []

	for part in spec.split(','):
		part = part.strip()

		if not part:
			continue

		if '-' in part[1:]:
			lo, hi = part.split('-', 1)
			wanted.extend(range(int(lo), int(hi)+1))
		else:
			wanted.append(int(part))

	return wanted

def centroid(grid, X, Y):
	"""The weighted first moment of the cells clearly above background, or None."""
	peak = np.nanmax(grid)
	weights = np.where(np.isfinite(grid), np.clip(grid - centroidFloor*peak, 0, None), 0)

	if weights.sum() <= 0:
		return None

	return (weights*X).sum()/weights.sum(), (weights*Y).sum()/weights.sum()

def signalSpan(profiles, backgrounds, floor, length, margin=0):
	"""The [lo, hi] cell range over which any profile is more than floor above its background, widened by margin cells."""
	above = np.zeros(length, dtype=bool)

	for profile, background in zip(profiles, backgrounds):
		above |= np.nan_to_num(profile) > background + floor

	if not above.any():
		return 0, length - 1

	hits = np.flatnonzero(above)

	return max(0, hits[0] - margin), min(length - 1, hits[-1] + margin)

def axisLimits(cuts, lo, hi):
	"""The [min, max] of the angles actually drawn, with a little air either side."""
	values = np.concatenate([positions[lo:hi+1] for positions, _ in cuts.values()])
	values = values[np.isfinite(values)]

	if not len(values):
		return None

	pad = 0.02*(values.max() - values.min()) or 0.01

	return values.min() - pad, values.max() + pad

parser = argparse.ArgumentParser(description="Draw the FOV cross-sections against the measured motor angles q1 and q2.")
parser.add_argument("inFile", nargs='?', default=None, help="log CSV to process (default: newest *log.csv here)")
parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of the log")
parser.add_argument("--xcent", type=float, default=None, help="stage x to cut through (default: the centroid of the scan)")
parser.add_argument("--ycent", type=float, default=None, help="stage y to cut through (default: the centroid of the scan)")
parser.add_argument("--channels", default=None, help="channels to draw, e.g. 1,2,7 or 1-5,10 (default: all)")
parser.add_argument("--angle", default="q1", help="the motor angle to draw the cut against (default: q1)")
parser.add_argument("--cut", default="y", choices=("x", "y"), help="which cut to draw: y, the column at fixed x that q1 sweeps, or x, the row at fixed y (default: y)")
parser.add_argument("--width", type=float, default=6.0, help="width of both figures in inches (default: 6)")
parser.add_argument("--angle-range", type=float, nargs=2, default=None, dest="angleRange", metavar=("LO", "HI"), help="angle limits of the x axis in degrees, e.g. --angle-range 44 50 (default: the angles the drawn cells cover)")
parser.add_argument("--minor-tick", type=float, default=0.5, dest="minorTick", help="spacing in degrees of the unlabelled minor ticks on the angle axis (default: 0.5); 0 leaves them off")
parser.add_argument("--neighbours", type=int, default=2, help="rows/columns either side of the centre cut to draw faintly behind it")
parser.add_argument("--floor", type=float, default=0.01, help="fraction of peak above the background below which a cell is not signal, for trimming the plotted range")
parser.add_argument("--margin", type=int, default=4, help="scan steps of background to keep either side of the signal, so the plotted range is not cut off at the foot of the profile")
parser.add_argument("--keep-park", action="store_true", dest="keepPark", help="keep the stationary run at each end of the log; by default they are dropped, since the long park at the centre swamps that cell's angles")
parser.add_argument("--settle", type=float, default=defaultSettleTolerance, help=f"how far a sample may sit from the commanded position and still count as settled (default: {defaultSettleTolerance})")
parser.add_argument("--outdir", default="plots", help="directory to write the plot into (created if needed)")
parser.add_argument("--no-show", action="store_true", dest="noShow", help="save the plot without opening a window")

args = parser.parse_args()

inFile = args.inFile

if inFile is None:
	inFile = sorted(glob.glob("*log.csv"))[-1]

if args.noShow:
	plt.switch_backend('Agg')

names = readHeader(inFile)

for column in ('sx', 'sy', 'tx', 'ty', args.angle):
	if column not in names:
		raise SystemExit(f"{inFile}: header has no {column} column")

channelCols = findChannels(names)

if not channelCols:
	raise SystemExit(f"{inFile}: header has no ch<N>_1x columns")

channelCols = [entry for entry in channelCols if entry[0] not in excludedChannels]

if not channelCols:
	raise SystemExit(f"{inFile}: header has no channel columns outside {excludedChannels}")

if args.channels is not None:
	wanted = parseChannelList(args.channels)
	available = [number for number, _, _ in channelCols]
	missing = [number for number in wanted if number not in available]

	if missing:
		raise SystemExit(f"{inFile}: no such channel(s): {missing}, file has {available}")

	channelCols = [entry for entry in channelCols if entry[0] in wanted]

# the plots run from short wavelength to long rather than in channel order; a
# channel with no wavelength in the table above falls to the end, in channel
# order:
channelCols.sort(key=lambda entry: (channelWavelengths.get(entry[0], float('inf')), entry[0]))

channelNumbers = [number for number, _, _ in channelCols]
channelLabels = [channelLabel(number) for number in channelNumbers]

print(f"Processing {inFile}")
print(f"startLog: {args.startLog}")
print("channels: " + ", ".join(f"ch{number} ({label})" for number, label in zip(channelNumbers, channelLabels)))
print(f"drawing the {args.cut} cut against {args.angle}")

usecols = [names.index(column) for column in ('sx', 'sy', 'tx', 'ty', args.angle)] + [column for _, column, _ in channelCols]

data = np.loadtxt(inFile, skiprows=1+args.startLog, delimiter=',', usecols=usecols, ndmin=2)

sx, sy, tx, ty = data[:, :4].T

tx = np.round(tx, gridDecimals)
ty = np.round(ty, gridDecimals)

# the log opens and closes with the stage parked at one commanded position
# while the tracker runs; left in, those thousands of samples swamp that cell's
# mean angle, which is exactly what this plot reads off.  only the stationary
# run at each end is dropped, so the raster's own visit to that cell survives:
if not args.keepPark:
	moved = np.flatnonzero((tx != tx[0]) | (ty != ty[0]))
	start = moved[0] if len(moved) else 0

	moved = np.flatnonzero((tx != tx[-1]) | (ty != ty[-1]))
	end = moved[-1] + 1 if len(moved) else len(tx)

	dropped = start + (len(tx) - end)

	if dropped:
		print(f"dropped {start} parked rows at the start and {len(tx) - end} at the end")

	data, sx, sy, tx, ty = data[start:end], sx[start:end], sy[start:end], tx[start:end], ty[start:end]

angle = data[:, 4]

# the channels are negative-going, and it is the magnitude we want:
channels = abs(data[:, 5:]).T

uniqueTx = np.unique(tx)
uniqueTy = np.unique(ty)

if len(uniqueTx) < 3 or len(uniqueTy) < 3:
	raise SystemExit(f"{inFile}: commanded positions make a {len(uniqueTx)}x{len(uniqueTy)} grid; this log may not be a scan")

print(f"grid: {len(uniqueTx)} x {len(uniqueTy)}")

settled = np.hypot(sx - tx, sy - ty) < args.settle

indexX = np.searchsorted(uniqueTx, tx[settled])
indexY = np.searchsorted(uniqueTy, ty[settled])

flatIndex = indexX * len(uniqueTy) + indexY
cells = len(uniqueTx) * len(uniqueTy)

numGrid = np.bincount(flatIndex, minlength=cells).reshape(len(uniqueTx), len(uniqueTy))

def cellMeans(values):
	"""The mean of values over the settled samples in each cell, NaN where a cell is empty."""
	sums = np.bincount(flatIndex, weights=values[settled], minlength=cells)

	with np.errstate(invalid='ignore', divide='ignore'):
		grid = sums.reshape(len(uniqueTx), len(uniqueTy)) / numGrid

	grid[numGrid == 0] = np.nan

	return grid

dataGrid = np.array([cellMeans(channel) for channel in channels])
angleGrid = cellMeans(angle)

# each channel normalised to its own peak, so they overlay:
peaks = np.nanmax(dataGrid, axis=(1, 2))

if not np.all(np.isfinite(peaks) & (peaks > 0)):
	dead = [channelLabels[j] for j in range(len(channels)) if not (np.isfinite(peaks[j]) and peaks[j] > 0)]
	raise SystemExit(f"{inFile}: no signal in channel(s) {dead}")

normGrid = dataGrid / peaks[:, None, None]

backgrounds = np.nanquantile(normGrid, backgroundQuantile, axis=(1, 2))

print("background / peak: " + ", ".join(f"{channelLabels[j]} {backgrounds[j]:.3f}" for j in range(len(channels))))

X, Y = np.meshgrid(uniqueTx, uniqueTy, indexing='ij')

# the cut goes through the centre given, or else the mean centroid of the channels:
if args.xcent is not None and args.ycent is not None:
	cutX, cutY = args.xcent, args.ycent
	source = "given"
else:
	centroids = [centroid(dataGrid[j], X, Y) for j in range(len(channels))]
	centroids = [c for c in centroids if c is not None]

	if not centroids:
		raise SystemExit(f"{inFile}: no channel has a centroid")

	cutX = np.mean([c[0] for c in centroids])
	cutY = np.mean([c[1] for c in centroids])
	source = "centroid"

centreI = int(np.argmin(abs(uniqueTx - cutX)))
centreJ = int(np.argmin(abs(uniqueTy - cutY)))

print(f"centre: {cutX:.4f} {cutY:.4f} ({source})")
print(f"x cut along ty = {uniqueTy[centreJ]:.4f}, y cut along tx = {uniqueTx[centreI]:.4f}")

# each cut is (the angle at each of its cells, the normalised signal at each of
# its cells).  a neighbouring row or column was scanned at a different time, so
# it gets its own angles rather than the centre cut's:
offsets = range(-args.neighbours, args.neighbours + 1)

if args.cut == "y":
	# the column at fixed tx: signal against ty, which is the sweep q1 carries
	cuts = {k: (angleGrid[centreI + k, :], normGrid[:, centreI + k, :])
	        for k in offsets if 0 <= centreI + k < len(uniqueTx)}
	length = len(uniqueTy)
else:
	cuts = {k: (angleGrid[:, centreJ + k], normGrid[:, :, centreJ + k])
	        for k in offsets if 0 <= centreJ + k < len(uniqueTy)}
	length = len(uniqueTx)

lo, hi = signalSpan([profiles[j] for _, profiles in cuts.values() for j in range(len(channels))],
                    [backgrounds[j] for _ in cuts for j in range(len(channels))],
                    args.floor, length, args.margin)

# the axis spans the angles the drawn cells cover, unless a range is asked
# for; the cells themselves are not re-trimmed, so a narrower range simply
# crops the view:
limits = tuple(args.angleRange) if args.angleRange else axisLimits(cuts, lo, hi)

# what the angle actually did over the drawn cells, so an axis that carries no
# scan is obvious rather than quietly plotted:
centreAngles = cuts[0][0][lo:hi+1]
finite = centreAngles[np.isfinite(centreAngles)]
steps = np.diff(finite)
monotonic = np.all(steps > 0) or np.all(steps < 0)

print(f"{args.cut} cut: {args.angle} {finite.min():.3f} to {finite.max():.3f} deg "
      f"({finite.max() - finite.min():.3f} deg over {hi - lo + 1} cells, "
      f"{'monotonic' if monotonic else 'NOT monotonic'})")

if finite.max() - finite.min() < degenerateSpan:
	print(f"  warning: {args.angle} spans under {degenerateSpan} deg along this cut, so it carries "
	      f"little of the scan; the profile is being drawn against pointing drift")

stem = os.path.splitext(os.path.basename(inFile))[0]

if args.outdir:
	os.makedirs(args.outdir, exist_ok=True)

def saveFigure(fig, path):
	"""Write the figure as a png for looking at and a pdf for the slides, side by side."""
	fig.savefig(path, dpi=150)
	print(f"Wrote {path}")

	pdfPath = os.path.splitext(path)[0] + ".pdf"
	fig.savefig(pdfPath)
	print(f"Wrote {pdfPath}")

fig, ax = plt.subplots(figsize=(args.width, 5.5))

def drawCuts(ax, cuts, lo, hi, angle, limits, which=None, label=None):
	if which is None:
		which = range(len(channels))

	for k, (positions, profiles) in sorted(cuts.items(), key=lambda item: -abs(item[0])):
		centre = (k == 0)

		for j in which:
			colour = channelColours[j % len(channelColours)]

			if centre:
				ax.plot(positions[lo:hi+1], profiles[j][lo:hi+1], color=colour, linewidth=1.8,
				        marker='o', markersize=4, label=channelLabels[j])
			else:
				ax.plot(positions[lo:hi+1], profiles[j][lo:hi+1], color=colour, linewidth=0.8, alpha=0.25)

	if limits:
		ax.set_xlim(*limits)

		# half-degree ticks between the labelled whole degrees.  an axis too
		# narrow to hold a couple of them keeps the automatic ticks, which is
		# what the degenerate q2 cut needs:
		if args.minorTick > 0 and limits[1] - limits[0] >= 2*args.minorTick:
			ax.xaxis.set_major_locator(MultipleLocator(1.0))
			ax.xaxis.set_minor_locator(MultipleLocator(args.minorTick))
			ax.grid(True, which='minor', axis='x', alpha=0.25, linewidth=0.5)
			ax.tick_params(axis='x', which='minor', length=3)

	ax.set_ylim(0, 1.05)
	ax.set_xlabel(f"{angle} (degrees)")
	ax.set_ylabel("signal / peak")
	ax.grid(True, alpha=0.3)

	# the plots carry no titles, so a panel of one channel says which it is here:
	if label:
		ax.text(0.02, 0.92, label, transform=ax.transAxes, ha='left', va='top', fontsize=10)

drawCuts(ax, cuts, lo, hi, args.angle, limits)

ax.legend(loc='upper right', fontsize=8, ncol=2)

fig.tight_layout()

saveFigure(fig, os.path.join(args.outdir, f"{stem}_fov_cuts_q_presentation.png"))

# the same cut with each channel on its own panel, in one column down the page:
rows = len(channels)

fig, axes = plt.subplots(rows, 1, figsize=(args.width, 2.4*rows), sharex=True, squeeze=False)

for j in range(len(channels)):
	panel = axes[j, 0]

	drawCuts(panel, cuts, lo, hi, args.angle, limits, which=[j], label=channelLabels[j])

	# sharex already hides the tick labels above the bottom row, so only the
	# axis labels have to go:
	if j < rows - 1:
		panel.set_xlabel("")

fig.tight_layout()

saveFigure(fig, os.path.join(args.outdir, f"{stem}_fov_cuts_channels_q_presentation.png"))

if not args.noShow:
	plt.show()
