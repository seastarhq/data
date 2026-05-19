import numpy as np
import matplotlib.pyplot as plt
import sys
import glob as glob
import tqdm

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

inFile = sorted(glob.glob("*log.csv"))[-1]

if (len(sys.argv) > 1):
	if (str(sys.argv[1]) != "1"):
		inFile = str(sys.argv[1])
		
		
startLog = 10
deltaStep = 0.01
xCent = 0.5162
yCent = 0.5286

if (len(sys.argv) > 2):
	startLog = int(sys.argv[2])
	
if (len(sys.argv) > 3):
	deltaStep = float(sys.argv[3])	
	
if (len(sys.argv) > 4):
	xCent = float(sys.argv[4])	

if (len(sys.argv) > 5):
	yCent = float(sys.argv[5])	

print(f"Processing {inFile}")
print(f"startLog: {startLog}")
print(f"deltaStep: {deltaStep}")
print(f"cent: {xCent}, {yCent}")

times, q1s, q2s, q3s, sunAzs, sunAlts, qws, qxs, qys, qzs, sxs, sys, sbs, txs, tys, rxs, rys, rzs, axs, ays, azs, cqws, cqxs, cqys, cqzs, imuTs, imuPs, imuLats, imuLons, hMins, hMaxs, hScales, j3_ch1_1xs, j3_ch2_1xs, j3_ch3_1xs, j3_ch4_1xs, j3_ch5_1xs = np.loadtxt(inFile, unpack=True, skiprows=1, delimiter=',', dtype=str)



j3_ch1_1x = np.array(j3_ch1_1xs[startLog:], dtype=float)
j3_ch2_1x = np.array(j3_ch2_1xs[startLog:], dtype=float)
j3_ch3_1x = np.array(j3_ch3_1xs[startLog:], dtype=float)
j3_ch4_1x = np.array(j3_ch4_1xs[startLog:], dtype=float)
j3_ch5_1x = np.array(j3_ch5_1xs[startLog:], dtype=float)

channels = np.array([j3_ch1_1x, j3_ch2_1x, j3_ch3_1x, j3_ch4_1x, j3_ch5_1x])

sx = np.array(sxs[startLog:], dtype=float) - xCent
sy = np.array(sys[startLog:], dtype=float) - yCent


roundedSx = np.vectorize(myround)(sx, base=deltaStep)
roundedSy = np.vectorize(myround)(sy, base=deltaStep)

uniqueSx = np.unique(roundedSx)
uniqueSy = np.unique(roundedSy)

print(roundedSx)
print(np.unique(roundedSx))
print(np.unique(roundedSy))
print(len(np.unique(roundedSx)))
print(len(np.unique(roundedSy)))


dataGrid = np.zeros((len(np.unique(roundedSx)), len(np.unique(roundedSy)), 5))
numGrid = np.zeros((len(np.unique(roundedSx)), len(np.unique(roundedSy)), 5))


for j in range(len(channels)):
	for i in tqdm.tqdm(range(len(channels[j]))):
		currentX = myround(sx[i], base=deltaStep)
		currentY = myround(sy[i], base=deltaStep)
		
		indexX = np.argmin(abs(currentX - uniqueSx))
		indexY = np.argmin(abs(currentY - uniqueSy))
		
		#print(currentX, currentY)
		#print(indexX, indexY)
		
		dataGrid[indexX, indexY, j] += abs(channels[j, i])
		
		numGrid[indexX, indexY, j] += 1
	

dataGrid = dataGrid / numGrid

dataGrid[dataGrid <= 0.025] = np.nan

uniqueSx += xCent
uniqueSy += yCent

avgX = 0
avgY = 0

for j in range(len(channels)):
	plt.figure()
	
	X, Y = np.meshgrid(uniqueSy, uniqueSx)
	
	cont = plt.contourf(Y, X, dataGrid[:, :, j], 11)
	
	com = centerOfMass(cont.allsegs[-1][0])
	print(com)
	
	avgX += com[0]
	avgY += com[1]
	
	plt.plot(com[0], com[1], marker='o')
	
	plt.colorbar()
	plt.show()
	
avgX /= len(channels)
avgY /= len(channels)
	
print(f"Averaged center: {avgX} {avgY}")	


for j in range(len(channels)):
	plt.figure()
	plt.title(f"Channel {j+1}")
	plt.imshow(dataGrid[:, :, j])
	plt.show()

