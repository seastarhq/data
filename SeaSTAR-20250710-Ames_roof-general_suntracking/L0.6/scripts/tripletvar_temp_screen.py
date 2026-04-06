#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz
from scipy.signal import *

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *
from seastar_analysis_utils import *

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

## analysis parameters:
# including 
# SEASTAR_TIMEZONE AVG_INTERVAL ANALYSIS_MARGIN BRIGHTNESS_MIN BRIGHTNESS_MAX TRACKING_EUCLIDIAN_MAX
# HOT_BLOCK1_MIN HOT_BLOCK1_MAX HOT_BLOCK2_MIN HOT_BLOCK2_MAX COLD_BLOCK_MIN COLD_BLOCK_MAX
# IMU_TEMP_MIN IMU_TEMP_MAX IMU_PRESS_MIN IMU_PRESS_MAX
# TRIPLETVAR_TOLERANCE_PERCENT TEMP_TRIPLET_TIME TEMP_SLOPE_TOLERANCE WINDOWWIDTH
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--temp_triplet_time', type=float)
parser.add_argument('--tempslope_tol', type=float)  
parser.add_argument('--windowwidth', type=int)
parser.add_argument('--d2T_tol', type=float)
args = parser.parse_args()

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
#if args.triplet_tol is not None:
#    TRIPLET_TOLERANCE = args.triplet_tol
if args.temp_triplet_time is not None:
    TEMP_TRIPLET_TIME = args.temp_triplet_time
if args.tempslope_tol is not None:
    TEMP_SLOPE_TOLERANCE = args.tempslope_tol
if args.windowwidth is not None:
    WINDOWWIDTH = args.windowwidth
if args.d2T_tol is not None:
    TEMP_D2TDT2_TOLERANCE = args.d2T_tol

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)
sys.stderr.write(L06_npyfile)
L06_file_date = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[1]
L06_file_time = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[2]
# for later re-saving:

#print(f"\n\n{L06_file_date} {L06_file_time}\n\n")

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

# for testing, we set all the housekeeping flags back to zero
#L06_data[:]['housekeeping_flags'] = 0

# fill in the values for raw temp slope
last_timestep = len(L06_data)
for timestep in range(len(L06_data)):

    if timestep < TEMP_TRIPLET_TIME: # we have not advanced enough timesteps
        #  don't do anythign to dTdt_raw - leave it as nan's
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1
    elif timestep + TEMP_TRIPLET_TIME >= last_timestep: # we are less than triplet_time from the end
        #  don't do anythign to dTdt_raw - leave it as nan's
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1 
    else:  # we can go forward and back by triplet_time
        triplet_forward_time = int(timestep + TEMP_TRIPLET_TIME)
        triplet_backward_time = int(timestep - TEMP_TRIPLET_TIME)
        #sys.stderr.write(f"{triplet_forward_time} {triplet_backward_time}\n")
        hotblock1_triplet = (L06_data[triplet_backward_time]['hot_block1_temp'], L06_data[timestep]['hot_block1_temp'], L06_data[triplet_forward_time]['hot_block1_temp'])
        temp_slope = (hotblock1_triplet[2] - hotblock1_triplet[0]) / 2.0 * TEMP_TRIPLET_TIME
        sys.stderr.write(f"dTdt: {temp_slope}\n")
        L06_data[timestep]['dTdt_raw'] = temp_slope
#    else:
        # this should never happen
#        sys.stderr.write("This is the part of the else block that should never happen!")
#        continue

# do a moving average of temp slope
# make a block function for the moving average
avg_kernel = np.ones(WINDOWWIDTH)/WINDOWWIDTH 
slope_array = convolve(L06_data['dTdt_raw'], avg_kernel, mode='same')

for timestep in range(len(L06_data)):
    L06_data[timestep]['dTdt_smooth'] = slope_array[timestep]


# calc the second derivative of temp slope

last_timestep = len(L06_data)
for timestep in range(len(L06_data)):

    if timestep < TEMP_TRIPLET_TIME: # we have not advanced enough timesteps
        #  don't do anythign to dTdt_raw - leave it as nan's
        continue
    elif timestep + TEMP_TRIPLET_TIME >= last_timestep: # we are less than triplet_time from the end
        #  don't do anythign to dTdt_raw - leave it as nan's
        continue
    else:  # we can go forward and back by triplet_time
        triplet_forward_time = int(timestep + TEMP_TRIPLET_TIME)
        triplet_backward_time = int(timestep - TEMP_TRIPLET_TIME)
        #sys.stderr.write(f"{triplet_forward_time} {triplet_backward_time}\n")
        dTdt_triplet = (L06_data[triplet_backward_time]['dTdt_smooth'], L06_data[timestep]['dTdt_smooth'], L06_data[triplet_forward_time]['dTdt_smooth'])
        d2Tdt2 = (dTdt_triplet[2] - dTdt_triplet[0]) / 2.0 * TEMP_TRIPLET_TIME
        #sys.stderr.write(f"d2Tdt2: {d2Tdt2}\n")
        L06_data[timestep]['d2Tdt2'] = d2Tdt2
#    else:
        # this should never happen
#        sys.stderr.write("This is the part of the else block that should never happen!")
#        continue

# do a moving average of the second derivative
avg_kernel = np.ones(WINDOWWIDTH)/WINDOWWIDTH  # we use the same window for the second derivative for now
slopeslope_array = convolve(L06_data['d2Tdt2'], avg_kernel, mode='same')

for timestep in range(len(L06_data)):
    L06_data[timestep]['d2Tdt2_smooth'] = slopeslope_array[timestep]


# set the flags:

# scenario 1: negative slope of temperature (good), negative second derivative (good) - data is good
# scenario 2: negative slope of temperature (good), positive second derivative (bad) - data is bad - heater is on
# scenario 3: small positive slope of temperature (bad), small second derivative - data is good - heating up without the heater   
# scenario 4: positive slope of temperature (bad), large second derivative - data is bad - heater is on

for timestep in range(len(L06_data)):

    if L06_data[timestep]['dTdt_smooth'] <= 0 and L06_data[timestep]['dTdt_smooth'] < 0:
        # data is good, leave the flag at 0
        pass
    elif L06_data[timestep]['dTdt_smooth'] <= 0 and L06_data[timestep]['d2Tdt2_smooth'] > TEMP_D2TDT2_TOLERANCE:
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1
    elif L06_data[timestep]['dTdt_smooth'] <= TEMP_SLOPE_TOLERANCE and abs(L06_data[timestep]['dTdt_smooth']) < TEMP_D2TDT2_TOLERANCE:
        # data is good
        pass
    elif L06_data[timestep]['dTdt_smooth'] >= 0 and abs(L06_data[timestep]['dTdt_smooth']) > TEMP_D2TDT2_TOLERANCE:
        # data is bad
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1
    else:
        pass
        
triplet_metadata = {'TEMP_TRIPLET_TIME': TEMP_TRIPLET_TIME, 'TEMP_SLOPE_TOLERANCE': TEMP_SLOPE_TOLERANCE, 'WINDOWWIDTH': WINDOWWIDTH, 'TEMP_D2TDT2_TOLERANCE': TEMP_D2TDT2_TOLERANCE }
metadata.update(triplet_metadata)

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
