#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz

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
# TRIPLETVAR_TOLERANCE_PERCENT
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--triplet_tol', type=float)
parser.add_argument('--triplet_time', type=float)
args = parser.parse_args()

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
if args.triplet_tol is not None:
    TRIPLET_TOLERANCE = args.triplet_tol
if args.triplet_time is not None:
    TRIPLET_TIME = args.triplet_time

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)
L06_file_date = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[1]
L06_file_time = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[2]
# for later re-saving:

#print(f"\n\n{L06_file_date} {L06_file_time}\n\n")

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
print(metadata)
#print(type(metadata))
L06_data = L06_data['array_data']

#print(L05_data.shape)

last_time = len(L06_data)
for timestep in range(len(L06_data)):

    if timestep < TRIPLET_TIME: # we have not advanced enough timesteps 
        L06_data[timestep]['cloud_flags'] = 1
        continue
    elif timestep + TRIPLET_TIME >= last_time: # we are less than triplet_time from the end
        L06_data[timestep]['cloud_flags'] = 1
        continue
    else:  # we can go forward and back by triplet_time
        triplet_forward_time = int(timestep + TRIPLET_TIME)
        triplet_backward_time = int(timestep - TRIPLET_TIME)
        print(f"{triplet_forward_time} {triplet_backward_time}\n")
        ch1_triplet = (L06_data[triplet_backward_time]['ch1_1x'], L06_data[timestep]['ch1_1x'], L06_data[triplet_forward_time]['ch1_1x'])
        ch2_triplet = (L06_data[triplet_backward_time]['ch2_1x'], L06_data[timestep]['ch2_1x'], L06_data[triplet_forward_time]['ch2_1x'])
        ch3_triplet = (L06_data[triplet_backward_time]['ch3_1x'], L06_data[timestep]['ch3_1x'], L06_data[triplet_forward_time]['ch3_1x'])
        ch4_triplet = (L06_data[triplet_backward_time]['ch4_1x'], L06_data[timestep]['ch4_1x'], L06_data[triplet_forward_time]['ch4_1x'])
        ch5_triplet = (L06_data[triplet_backward_time]['ch5_1x'], L06_data[timestep]['ch5_1x'], L06_data[triplet_forward_time]['ch5_1x'])

        if abs(ch1_triplet[1] - ch1_triplet[0] / ch1_triplet[1]) > TRIPLET_TOLERANCE*100.0 or abs(ch1_triplet[1] - ch1_triplet[2] / ch1_triplet[1]) > TRIPLET_TOLERANCE*100.0:
            L06_data[timestamp]['cloud_flags'] = 2
        if abs(ch2_triplet[1] - ch2_triplet[0] / ch2_triplet[1]) > TRIPLET_TOLERANCE*100.0 or abs(ch2_triplet[1] - ch2_triplet[2] / ch2_triplet[1]) > TRIPLET_TOLERANCE*100.0:
            L06_data[timestamp]['cloud_flags'] = 2
        if abs(ch3_triplet[1] - ch3_triplet[0] / ch3_triplet[1]) > TRIPLET_TOLERANCE*100.0 or abs(ch3_triplet[1] - ch3_triplet[2] / ch3_triplet[1]) > TRIPLET_TOLERANCE*100.0:
            L06_data[timestamp]['cloud_flags'] = 2
        if abs(ch4_triplet[1] - ch4_triplet[0] / ch4_triplet[1]) > TRIPLET_TOLERANCE*100.0 or abs(ch4_triplet[1] - ch4_triplet[2] / ch4_triplet[1]) > TRIPLET_TOLERANCE*100.0:
            L06_data[timestamp]['cloud_flags'] = 2
        if abs(ch5_triplet[1] - ch5_triplet[0] / ch5_triplet[1]) > TRIPLET_TOLERANCE*100.0 or abs(ch5_triplet[1] - ch5_triplet[2] / ch5_triplet[1]) > TRIPLET_TOLERANCE*100.0:
            L06_data[timestamp]['cloud_flags'] = 2

triplet_metadata = {'TRIPLETVAR_TOLERANCE_PERCENT': TRIPLET_TOLERANCE, 'TRIPLETVAR_TIME': TRIPLET_TIME}
metadata.update(triplet_metadata)


np.savez(L06_npyfile, array_data=L06_data, metadata = metadata)





    




