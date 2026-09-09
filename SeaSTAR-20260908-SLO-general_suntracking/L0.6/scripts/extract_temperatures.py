#!/usr/bin/env python3

import sys, os
import numpy as np
import argparse
from datetime import *
import pytz
import tqdm

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
# TRIPLETVAR_TOLERANCE_PERCENT TRIPLETVAR_TIME
from seastar_error_flags import * 

#hotblock_error = 0
#dtdt_error = 0


parser = argparse.ArgumentParser()
parser.add_argument('file')
args = parser.parse_args()

# findfile needs a list passed to it, so we make one with length 1
print(L06_DATA_DIR)

L06_datadir = [L06_DATA_DIR,]

L06_npyfile = seastar_datautils.findFile(args.file, L06_datadir)

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]  # this gives us the dictionary rather than the numpy array
L06_data = L06_data['array_data']

seastar_timezone = pytz.timezone(metadata['SEASTAR_TIMEZONE'])

for timestep in range(len(L06_data)):
    # these are the scenarios from the if-elif block
    scenario1 = 0  # we set the COLD_BLOCK_HOT flag 
    scenario2 = 0  # COLD_BLOCK_COLD 
    scenario3 = 0  # IMU_TEMP_OOB
    scenario4 = 0  # IMU_PRES_OOB
    scenario5 = 0

    timestamp = L06_data[timestep]['datetime'].astype(datetime)
    imu_temp = L06_data[timestep]['imu_temp']
    hot_block1_temp = L06_data[timestep]['hot_block1_temp']
    dTdt_raw = L06_data[timestep]['dTdt_raw']
    dTdt_smooth = L06_data[timestep]['dTdt_smooth']
    d2Tdt2 = L06_data[timestep]['d2Tdt2']
    d2Tdt2_smooth = L06_data[timestep]['d2Tdt2_smooth']

    housekeeping_flags = L06_data[timestep]['housekeeping_flags']
    if housekeeping_flags & COLD_BLOCK_HOT: 
        scenario1 = 1 
    elif housekeeping_flags & COLD_BLOCK_COLD: 
        scenario2 = 1
    elif housekeeping_flags & IMU_TEMP_OOB:
        scenario3 = 1
    elif housekeeping_flags & IMU_PRES_OOB:
        scenario4 = 1
    elif housekeeping_flags & WATER_TEMP_OOB:
        scenario5 = 1


    sys.stdout.write(f"{timestamp.isoformat()} {imu_temp} {hot_block1_temp} {dTdt_raw} {dTdt_smooth} {d2Tdt2} {d2Tdt2_smooth} {housekeeping_flags} {scenario1} {scenario2} {scenario3} {scenario4} {scenario5}\n")


