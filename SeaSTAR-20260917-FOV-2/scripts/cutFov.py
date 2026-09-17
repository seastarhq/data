#!/usr/bin/env python3
# cross-sections of the FOV scan along x and y at the native scan step: the
# scan column and row through the centre, with their neighbours faint behind
# them, every channel normalised to its own peak and overlaid.
#
# like fitFov.py this grids on the commanded stage position (tx, ty), so the
# profiles are sampled exactly at the scan steps.  the plotted range is trimmed
# to where the signal is, since the scan range is several times the spot.

import argparse
import glob
import os
import re
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Channel columns are named ch<N>_1x in current logs and j3_ch<N>_1x in older ones.
channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_1x$")

# commanded positions are rounded to this many decimals before being treated as
# the same grid point, to absorb float noise in the log:
gridDecimals = 4

# samples further than this from the commanded position are still in transit
# between grid points and are left out of the cell average:
settleTolerance = 0.002

# the centroid that picks the centre row and column ignores cells below this
# fraction of the channel's peak, so the background does not pull it about:
centroidFloor = 0.05

# the background is taken as this quantile of the grid, which is far below the
# spot as long as the scan range is a few times the spot:
backgroundQuantile = 0.25

# one colour per channel, cycling if the log carries more than ten:
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

def signalSpan(positions, profiles, backgrounds, floor):
	"""The [lo, hi] index range over which any profile is more than floor above its background."""
	above = np.zeros(len(positions), dtype=bool)

	for profile, background in zip(profiles, backgrounds):
		above |= np.nan_to_num(profile) > background + floor

	if not above.any():
		return 0, len(positions) - 1

	hits = np.flatnonzero(above)

	return hits[0], hits[-1]

parser = argparse.ArgumentParser(description="Draw x and y cross-sections of an FOV scan through its centre at the native scan step.")
parser.add_argument("inFile", nargs='?', default=None, help="log CSV to process (default: newest *log.csv here)")
parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of the log")
parser.add_argument("--xcent", type=float, default=None, help="stage x to cut through (default: the centroid of the scan)")
parser.add_argument("--ycent", type=float, default=None, help="stage y to cut through (default: the centroid of the scan)")
parser.add_argument("--channels", default=None, help="channels to draw, e.g. 1,2,7 or 1-5,10 (default: all)")
parser.add_argument("--neighbours", type=int, default=2, help="rows/columns either side of the centre cut to draw faintly behind it")
parser.add_argument("--floor", type=float, default=0.01, help="fraction of peak above the background below which a cell is not signal, for trimming the plotted range")
parser.add_argument("--outdir", default="plots", help="directory to write the plot into (created if needed)")
parser.add_argument("--no-show", action="store_true", dest="noShow", help="save the plot without opening a window")

args = parser.parse_args()

inFile = args.inFile

if inFile is None:
	inFile = sorted(glob.glob("*log.csv"))[-1]

if args.noShow:
	plt.switch_backend('Agg')

names = readHeader(inFile)

for column in ('sx', 'sy', 'tx', 'ty'):
	if column not in names:
		raise SystemExit(f"{inFile}: header has no {column} column")

channelCols = findChannels(names)

if not channelCols:
	raise SystemExit(f"{inFile}: header has no ch<N>_1x columns")

if args.channels is not None:
	wanted = parseChannelList(args.channels)
	available = [number for number, _, _ in channelCols]
	missing = [number for number in wanted if number not in available]

	if missing:
		raise SystemExit(f"{inFile}: no such channel(s): {missing}, file has {available}")

	channelCols = [entry for entry in channelCols if entry[0] in wanted]

channelNumbers = [number for number, _, _ in channelCols]

print(f"Processing {inFile}")
print(f"startLog: {args.startLog}")
print(f"channels: {channelNumbers}")

# Only the columns we actually use are read; the time column is not numeric.
usecols = [names.index(column) for column in ('sx', 'sy', 'tx', 'ty')] + [column for _, column, _ in channelCols]

data = np.loadtxt(inFile, skiprows=1+args.startLog, delimiter=',', usecols=usecols, ndmin=2)

sx, sy, tx, ty = data[:, :4].T

# the channels are negative-going, and it is the magnitude we want:
channels = abs(data[:, 4:]).T

tx = np.round(tx, gridDecimals)
ty = np.round(ty, gridDecimals)

uniqueTx = np.unique(tx)
uniqueTy = np.unique(ty)

if len(uniqueTx) < 3 or len(uniqueTy) < 3:
	raise SystemExit(f"{inFile}: commanded positions make a {len(uniqueTx)}x{len(uniqueTy)} grid; this log may not be a scan")

print(f"grid: {len(uniqueTx)} x {len(uniqueTy)}")

settled = np.hypot(sx - tx, sy - ty) < settleTolerance

# Every rounded position is by construction a member of the unique array, so
# searchsorted gives the exact bin index for the whole log at once.
indexX = np.searchsorted(uniqueTx, tx[settled])
indexY = np.searchsorted(uniqueTy, ty[settled])

flatIndex = indexX * len(uniqueTy) + indexY
cells = len(uniqueTx) * len(uniqueTy)

numGrid = np.bincount(flatIndex, minlength=cells).reshape(len(uniqueTx), len(uniqueTy))

dataGrid = np.zeros((len(channels), len(uniqueTx), len(uniqueTy)))

for j in range(len(channels)):
	sums = np.bincount(flatIndex, weights=channels[j][settled], minlength=cells)

	dataGrid[j] = sums.reshape(len(uniqueTx), len(uniqueTy))

with np.errstate(invalid='ignore', divide='ignore'):
	dataGrid = dataGrid / numGrid[None, :, :]

dataGrid[:, numGrid == 0] = np.nan

# each channel normalised to its own peak, so they overlay:
peaks = np.nanmax(dataGrid, axis=(1, 2))

if not np.all(np.isfinite(peaks) & (peaks > 0)):
	dead = [channelNumbers[j] for j in range(len(channels)) if not (np.isfinite(peaks[j]) and peaks[j] > 0)]
	raise SystemExit(f"{inFile}: no signal in channel(s) {dead}")

normGrid = dataGrid / peaks[:, None, None]

# the noise floor sits at a percent or so of peak, so the floor that trims the
# plotted range is measured up from it rather than from zero:
backgrounds = np.nanquantile(normGrid, backgroundQuantile, axis=(1, 2))

print("background / peak: " + ", ".join(f"ch{channelNumbers[j]} {backgrounds[j]:.3f}" for j in range(len(channels))))

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

# the x cut is a column of the grid (signal against tx at fixed ty), the y cut
# a row.  offsets are in scan steps from the centre cut:
offsets = range(-args.neighbours, args.neighbours + 1)

xCuts = {k: normGrid[:, :, centreJ + k] for k in offsets if 0 <= centreJ + k < len(uniqueTy)}
yCuts = {k: normGrid[:, centreI + k, :] for k in offsets if 0 <= centreI + k < len(uniqueTx)}

# trimmed to where any channel on any of the drawn cuts has signal:
xLo, xHi = signalSpan(uniqueTx, [cut[j] for cut in xCuts.values() for j in range(len(channels))],
                      [backgrounds[j] for cut in xCuts.values() for j in range(len(channels))], args.floor)
yLo, yHi = signalSpan(uniqueTy, [cut[j] for cut in yCuts.values() for j in range(len(channels))],
                      [backgrounds[j] for cut in yCuts.values() for j in range(len(channels))], args.floor)

print(f"x range: {uniqueTx[xLo]:.4f} to {uniqueTx[xHi]:.4f} ({xHi - xLo + 1} steps)")
print(f"y range: {uniqueTy[yLo]:.4f} to {uniqueTy[yHi]:.4f} ({yHi - yLo + 1} steps)")

stem = os.path.splitext(os.path.basename(inFile))[0]

if args.outdir:
	os.makedirs(args.outdir, exist_ok=True)

fig, (axX, axY) = plt.subplots(1, 2, figsize=(14, 5.5))

def drawCuts(ax, positions, cuts, lo, hi, along, at, atValue):
	for k, cut in sorted(cuts.items(), key=lambda item: -abs(item[0])):
		centre = (k == 0)

		for j in range(len(channels)):
			colour = channelColours[j % len(channelColours)]

			if centre:
				ax.plot(positions[lo:hi+1], cut[j][lo:hi+1], color=colour, linewidth=1.8,
				        marker='o', markersize=4, label=f"ch{channelNumbers[j]}")
			else:
				ax.plot(positions[lo:hi+1], cut[j][lo:hi+1], color=colour, linewidth=0.8, alpha=0.25)

	ax.set_xlim(positions[lo], positions[hi])
	ax.set_ylim(0, 1.05)
	ax.set_xlabel(along)
	ax.set_ylabel("signal / peak")
	ax.set_title(f"cut along {along} at {at} = {atValue:.4f}, neighbours ±{args.neighbours} faint")
	ax.grid(True, alpha=0.3)

drawCuts(axX, uniqueTx, xCuts, xLo, xHi, "tx", "ty", uniqueTy[centreJ])
drawCuts(axY, uniqueTy, yCuts, yLo, yHi, "ty", "tx", uniqueTx[centreI])

axY.legend(loc='upper right', fontsize=8, ncol=2)

fig.suptitle(f"{stem}: FOV cross-sections at the native scan step, each channel normalised to its peak")
fig.tight_layout()

cutsPath = os.path.join(args.outdir, f"{stem}_fov_cuts.png")
fig.savefig(cutsPath, dpi=150)
print(f"Wrote {cutsPath}")

if not args.noShow:
	plt.show()
