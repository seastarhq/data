#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz
import datetime

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
#print(metadata)
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

        tvar_ch1 = calc_tvar(ch1_triplet)
        tvar_ch2 = calc_tvar(ch2_triplet)
        tvar_ch3 = calc_tvar(ch3_triplet)
        tvar_ch4 = calc_tvar(ch4_triplet)
        tvar_ch5 = calc_tvar(ch5_triplet)

        L06_data[timestep]['tvar_ch1'] = tvar_ch1
        L06_data[timestep]['tvar_ch2'] = tvar_ch2
        L06_data[timestep]['tvar_ch3'] = tvar_ch3
        L06_data[timestep]['tvar_ch4'] = tvar_ch4
        L06_data[timestep]['tvar_ch5'] = tvar_ch5

        if tvar_ch1 > TRIPLET_TOLERANCE*100.0:
            L06_data[timestep]['cloud_flags'] = 2
        if tvar_ch2 > TRIPLET_TOLERANCE*100.0:
            L06_data[timestep]['cloud_flags'] = 2
        if tvar_ch3 > TRIPLET_TOLERANCE*100.0:
            L06_data[timestep]['cloud_flags'] = 2
        if tvar_ch4 > TRIPLET_TOLERANCE*100.0:
            L06_data[timestep]['cloud_flags'] = 2
        if tvar_ch5 > TRIPLET_TOLERANCE*100.0:
            L06_data[timestep]['cloud_flags'] = 2

now = datetime.now(pytz.utc).isoformat()
triplet_metadata = {'TRIPLETVAR_TOLERANCE_PERCENT': TRIPLET_TOLERANCE, 'TRIPLETVAR_TIME': TRIPLET_TIME, 'LAST_PROCESSING_TIME': now}
metadata.update(triplet_metadata)
#print(metadata)
#print(L06_npyfile)


try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)

