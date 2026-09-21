import argparse
import glob
import os
import re
import numpy as np
import matplotlib.pyplot as plt
import tqdm

# Channel columns are named ch<N>_1x in current logs and j3_ch<N>_1x in older ones.
channelPattern = re.compile(r"^(?:j3_)?ch(\d+)_1x$")

def myround(x, base=5):
	return base * round(x/base)

def centerOfMass(X):
	x = X[:, 0]
	y = X[:, 1]
	
	g = (x[:-1]*y[1:] - x[1:]*y[:-1])
	A = 0.5 * g.sum()
	cx = ((x[:-1] + x[1:])*g).sum()
	cy = ((y[:-1] + y[1:])*g).sum()
	
	return 1./(6*A)*np.array([cx, cy])

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

parser = argparse.ArgumentParser(description="Grid FOV scan channel data by stage position and contour it.")
parser.add_argument("inFile", nargs='?', default=None, help="log CSV to process (default: newest *log.csv here)")
parser.add_argument("--start-log", type=int, default=10, dest="startLog", help="rows to skip at the start of the log")
parser.add_argument("--delta-step", type=float, default=0.01, dest="deltaStep", help="stage position bin size")
parser.add_argument("--xcent", type=float, default=0.5162, help="stage x centre")
parser.add_argument("--ycent", type=float, default=0.5286, help="stage y centre")
parser.add_argument("--channels", default=None, help="channels to process, e.g. 1,2,7 or 1-5,10 (default: all)")
parser.add_argument("--frac", type=float, default=0.05, help="mask grid cells below this fraction of each channel's own peak")
parser.add_argument("--outdir", default="plots", help="directory to write the plots into (created if needed)")
parser.add_argument("--no-show", action="store_true", dest="noShow", help="save the plots without opening windows")

args = parser.parse_args()

inFile = args.inFile

if inFile is None:
	inFile = sorted(glob.glob("*log.csv"))[-1]

startLog = args.startLog
deltaStep = args.deltaStep
xCent = args.xcent
yCent = args.ycent

if args.noShow:
	plt.switch_backend('Agg')

names = readHeader(inFile)

if 'sx' not in names or 'sy' not in names:
	raise SystemExit(f"{inFile}: header has no sx/sy columns")

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
print(f"startLog: {startLog}")
print(f"deltaStep: {deltaStep}")
print(f"cent: {xCent}, {yCent}")
print(f"channels: {channelNumbers}")

# Only the columns we actually use are read; the time column is not numeric.
usecols = [names.index('sx'), names.index('sy')] + [column for _, column, _ in channelCols]

data = np.loadtxt(inFile, skiprows=1+startLog, delimiter=',', usecols=usecols, ndmin=2)

sx = data[:, 0] - xCent
sy = data[:, 1] - yCent

channels = data[:, 2:].T

roundedSx = np.vectorize(myround)(sx, base=deltaStep)
roundedSy = np.vectorize(myround)(sy, base=deltaStep)

uniqueSx = np.unique(roundedSx)
uniqueSy = np.unique(roundedSy)

print(roundedSx)
print(uniqueSx)
print(uniqueSy)
print(len(uniqueSx))
print(len(uniqueSy))

if len(uniqueSx) < 2 or len(uniqueSy) < 2:
	raise SystemExit(f"{inFile}: stage positions collapse to a {len(uniqueSx)}x{len(uniqueSy)} grid at "
	                 f"--delta-step {deltaStep}; this log may not be a scan, or the step is too coarse")

# Every rounded position is by construction a member of the unique array, so
# searchsorted gives the exact bin index for the whole log at once.
indexX = np.searchsorted(uniqueSx, roundedSx)
indexY = np.searchsorted(uniqueSy, roundedSy)

flatIndex = indexX * len(uniqueSy) + indexY
cells = len(uniqueSx) * len(uniqueSy)

dataGrid = np.zeros((len(uniqueSx), len(uniqueSy), len(channels)))

numGrid = np.bincount(flatIndex, minlength=cells).reshape(len(uniqueSx), len(uniqueSy))

for j in tqdm.tqdm(range(len(channels))):
	sums = np.bincount(flatIndex, weights=abs(channels[j]), minlength=cells)
	
	dataGrid[:, :, j] = sums.reshape(len(uniqueSx), len(uniqueSy))

with np.errstate(invalid='ignore', divide='ignore'):
	dataGrid = dataGrid / numGrid[:, :, None]

dataGrid[numGrid == 0, :] = np.nan

# Channel magnitudes differ by orders of magnitude, so the floor is a fraction
# of each channel's own peak rather than one absolute level for all of them.
for j in range(len(channels)):
	peak = np.nanmax(dataGrid[:, :, j])
	
	if np.isfinite(peak):
		plane = dataGrid[:, :, j]
		plane[plane <= args.frac*peak] = np.nan

uniqueSx += xCent
uniqueSy += yCent

stem = os.path.splitext(os.path.basename(inFile))[0]

if args.outdir:
	os.makedirs(args.outdir, exist_ok=True)

ncols = min(4, len(channels))
nrows = int(np.ceil(len(channels)/ncols))

X, Y = np.meshgrid(uniqueSy, uniqueSx)

avgX = 0
avgY = 0
numCom = 0

contourFig, contourAxes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3.5*nrows), squeeze=False)

for j in range(len(channels)):
	ax = contourAxes[j // ncols][j % ncols]
	ax.set_title(f"Channel {channelNumbers[j]}")
	
	if np.all(np.isnan(dataGrid[:, :, j])):
		print(f"Channel {channelNumbers[j]}: no data above the mask, skipping")
		ax.set_axis_off()
		continue
	
	cont = ax.contourf(Y, X, dataGrid[:, :, j], 11)
	
	contourFig.colorbar(cont, ax=ax)
	
	if cont.allsegs[-1]:
		com = centerOfMass(cont.allsegs[-1][0])
		print(f"Channel {channelNumbers[j]}: {com}")
		
		avgX += com[0]
		avgY += com[1]
		numCom += 1
		
		ax.plot(com[0], com[1], marker='o')
	else:
		print(f"Channel {channelNumbers[j]}: no closed peak contour, no centre")

for j in range(len(channels), nrows*ncols):
	contourAxes[j // ncols][j % ncols].set_axis_off()

contourFig.tight_layout()

contourPath = os.path.join(args.outdir, f"{stem}_fov_contours.png")
contourFig.savefig(contourPath, dpi=150)
print(f"Wrote {contourPath}")

if numCom:
	avgX /= numCom
	avgY /= numCom
	
	print(f"Averaged center: {avgX} {avgY}")
else:
	print("Averaged center: no channel produced a centre")

mapFig, mapAxes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3.5*nrows), squeeze=False)

for j in range(len(channels)):
	ax = mapAxes[j // ncols][j % ncols]
	ax.set_title(f"Channel {channelNumbers[j]}")
	
	im = ax.imshow(dataGrid[:, :, j])
	
	mapFig.colorbar(im, ax=ax)

for j in range(len(channels), nrows*ncols):
	mapAxes[j // ncols][j % ncols].set_axis_off()

mapFig.tight_layout()

mapPath = os.path.join(args.outdir, f"{stem}_fov_maps.png")
mapFig.savefig(mapPath, dpi=150)
print(f"Wrote {mapPath}")

if not args.noShow:
	plt.show()
