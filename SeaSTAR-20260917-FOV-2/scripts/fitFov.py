#!/usr/bin/env python3
# grid the FOV scan on the commanded stage position and fit each channel with a
# 2D gaussian, to find the centre of the field of view.
#
# processFov.py bins the stage readback (sx, sy) at one fixed step, which
# aliases when the scan step differs from the bin and is smeared by the readback
# dithering.  the commanded positions (tx, ty) are exact, so gridding on them
# recovers the scan at its native resolution with no step to guess.  the spot is
# flat-topped rather than gaussian, so the widths are only a proxy, but the
# centre is robust.

import argparse
import glob
import os
import re
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

# Channel columns are named ch<N>_1x in current logs and j3_ch<N>_1x in older ones.
channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_1x$")

# commanded positions are rounded to this many decimals before being treated as
# the same grid point, to absorb float noise in the log:
gridDecimals = 4

# samples further than this from the commanded position are still in transit
# between grid points and are left out of the cell average:
settleTolerance = 0.002

# the weighted first moment that seeds the fit ignores cells below this fraction
# of the channel's peak, so the background does not pull it about:
seedFloor = 0.05

fwhmPerSigma = 2*np.sqrt(2*np.log(2))

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

def gaussian2d(xy, amplitude, x0, y0, sigmaX, sigmaY, theta, background):
	"""An elliptical gaussian on a background, rotated by theta about its centre."""
	x, y = xy

	cosT = np.cos(theta)
	sinT = np.sin(theta)

	xr = (x - x0)*cosT + (y - y0)*sinT
	yr = -(x - x0)*sinT + (y - y0)*cosT

	return amplitude*np.exp(-0.5*((xr/sigmaX)**2 + (yr/sigmaY)**2)) + background

def fitChannel(grid, X, Y):
	"""Fit one channel's grid; returns (x0, y0, fwhmX, fwhmY, thetaDeg, peak) or None."""
	finite = np.isfinite(grid)

	if finite.sum() < 7:
		return None

	peak = np.nanmax(grid)

	# seed from the weighted first moment of the cells clearly above background:
	weights = np.where(finite, np.clip(grid - seedFloor*peak, 0, None), 0)

	if weights.sum() <= 0:
		return None

	seedX = (weights*X).sum()/weights.sum()
	seedY = (weights*Y).sum()/weights.sum()

	stepX = np.median(np.diff(np.unique(X)))
	stepY = np.median(np.diff(np.unique(Y)))

	p0 = [peak, seedX, seedY, 2*stepX, 2*stepY, 0, 0]

	try:
		params, _ = curve_fit(gaussian2d, (X[finite], Y[finite]), grid[finite], p0=p0, maxfev=20000)
	except RuntimeError:
		return None

	amplitude, x0, y0, sigmaX, sigmaY, theta, background = params

	return x0, y0, fwhmPerSigma*abs(sigmaX), fwhmPerSigma*abs(sigmaY), np.degrees(theta) % 180, peak

parser = argparse.ArgumentParser(description="Grid an FOV scan on the commanded stage position and fit each channel's centre.")
parser.add_argument("inFile", nargs='?', default=None, help="log CSV to process (default: newest *log.csv here)")
parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of the log")
parser.add_argument("--xcent", type=float, default=None, help="stage x centre the scan was run about, drawn for reference")
parser.add_argument("--ycent", type=float, default=None, help="stage y centre the scan was run about, drawn for reference")
parser.add_argument("--channels", default=None, help="channels to process, e.g. 1,2,7 or 1-5,10 (default: all)")
parser.add_argument("--exclude", default=None, help="channels to leave out of the averaged centre, e.g. 8,9 (default: none)")
parser.add_argument("--window", type=float, default=None, help="half-width of the plotted window about the fitted centre (default: the whole scan)")
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
excluded = parseChannelList(args.exclude) if args.exclude else []

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

print(f"settled: {settled.sum()} of {len(settled)} samples")

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

X, Y = np.meshgrid(uniqueTx, uniqueTy, indexing='ij')

stem = os.path.splitext(os.path.basename(inFile))[0]

if args.outdir:
	os.makedirs(args.outdir, exist_ok=True)

ncols = min(4, len(channels))
nrows = int(np.ceil((len(channels) + 1)/ncols))

fig, axes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3.5*nrows), squeeze=False)

fits = {}

print()
print(f"{'ch':>3} {'peak':>6} | {'x0':>7} {'y0':>7} {'fwhmX':>7} {'fwhmY':>7} {'theta':>6}")

for j in range(len(channels)):
	ax = axes[j // ncols][j % ncols]
	number = channelNumbers[j]
	grid = dataGrid[j]

	if np.all(np.isnan(grid)):
		print(f"{number:>3} no data, skipping")
		ax.set_title(f"Channel {number}: no data")
		ax.set_axis_off()
		continue

	peak = np.nanmax(grid)

	# x runs down the rows of the grid, so it is drawn on the vertical axis to
	# match the contour plots processFov.py draws:
	ax.pcolormesh(uniqueTy, uniqueTx, grid/peak, vmin=0, vmax=1, shading='nearest')
	ax.contour(uniqueTy, uniqueTx, grid/peak, levels=[0.5], colors='white', linewidths=1)

	if args.xcent is not None and args.ycent is not None:
		ax.plot(args.ycent, args.xcent, marker='x', color='white', linestyle='none')

	fit = fitChannel(grid, X, Y)

	if fit is None:
		print(f"{number:>3} {peak:6.3f} | fit failed")
		ax.set_title(f"Channel {number}: fit failed")
		continue

	x0, y0, fwhmX, fwhmY, theta, _ = fit
	fits[number] = fit

	print(f"{number:>3} {peak:6.3f} | {x0:7.4f} {y0:7.4f} {fwhmX:7.4f} {fwhmY:7.4f} {theta:6.1f}")

	ax.plot(y0, x0, marker='+', color='red', markersize=12, markeredgewidth=2, linestyle='none')
	ax.set_title(f"Channel {number}: peak {peak:.2f}, fwhm {fwhmX:.3f} x {fwhmY:.3f}", fontsize=10)
	ax.set_xlabel('ty')
	ax.set_ylabel('tx')

	if args.window is not None:
		ax.set_xlim(y0 - args.window, y0 + args.window)
		ax.set_ylim(x0 - args.window, x0 + args.window)

for j in range(len(channels), nrows*ncols):
	axes[j // ncols][j % ncols].set_axis_off()

print()

averaged = [fits[number] for number in fits if number not in excluded]

if averaged:
	avgX = np.mean([fit[0] for fit in averaged])
	avgY = np.mean([fit[1] for fit in averaged])
	spreadX = np.ptp([fit[0] for fit in averaged])
	spreadY = np.ptp([fit[1] for fit in averaged])

	left = [number for number in fits if number not in excluded]

	print(f"Fitted centre: {avgX:.4f} {avgY:.4f} (mean of channels {left}, spread {spreadX:.4f} x {spreadY:.4f})")

	if args.xcent is not None and args.ycent is not None:
		print(f"Scan centre:   {args.xcent:.4f} {args.ycent:.4f} (offset {avgX - args.xcent:+.4f} {avgY - args.ycent:+.4f})")

	legend = (f"red + : fitted centre\n"
	          f"white contour : half maximum\n"
	          f"white x : scan centre\n\n"
	          f"fitted centre = ({avgX:.4f}, {avgY:.4f})")
else:
	print("Fitted centre: no channel produced a fit")
	legend = "no channel produced a fit"

# the legend goes in the spare panel after the last channel:
legendAx = axes[len(channels) // ncols][len(channels) % ncols]
legendAx.text(0, 0.5, legend, fontsize=12, transform=legendAx.transAxes, verticalalignment='center')

fig.suptitle(f"{stem}: FOV on commanded stage position, {len(uniqueTx)} x {len(uniqueTy)} grid")
fig.tight_layout()

fitPath = os.path.join(args.outdir, f"{stem}_fov_fit.png")
fig.savefig(fitPath, dpi=150)
print(f"Wrote {fitPath}")

if not args.noShow:
	plt.show()
