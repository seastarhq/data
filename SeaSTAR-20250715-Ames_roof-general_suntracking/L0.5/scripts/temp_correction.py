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

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--temp_corr_baseline', type=float)
parser.add_argument('--temp_corr_scalefactor', type=float)  
args = parser.parse_args()

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
#if args.triplet_tol is not None:
#    TRIPLET_TOLERANCE = args.triplet_tol
if args.temp_corr_baseline is not None:
    TEMP_CORR_BASELINE = args.temp_corr_baseline
if args.temp_corr_scalefactor is not None:
    TEMP_CORR_SCALEFACTOR = args.temp_corr_scalefactor

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

# do the correction for each timestep
for timestep in range(len(L06_data)):

    correction = TEMP_CORR_SCALEFACTOR * (L06_data[timestep]['hot_block1_temp'] - TEMP_CORR_BASELINE)
    ch2_1x_corr = L06_data[timestep]['ch2_1x'] - correction
    ch3_1x_corr = L06_data[timestep]['ch3_1x'] - correction
    ch4_1x_corr = L06_data[timestep]['ch4_1x'] - correction
    ch5_1x_corr = L06_data[timestep]['ch5_1x'] - correction

    # making it super clear by separating the assignment

    L06_data[timestep]['ch2_1x'] = ch2_1x_corr
    L06_data[timestep]['ch3_1x'] = ch3_1x_corr
    L06_data[timestep]['ch4_1x'] = ch4_1x_corr
    L06_data[timestep]['ch5_1x'] = ch5_1x_corr

        
temp_corr_metadata = {'TEMP_CORR_BASELINE': TEMP_CORR_BASELINE, 'TEMP_CORR_SCALEFACTOR': TEMP_CORR_SCALEFACTOR}
metadata.update(temp_corr_metadata)

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
