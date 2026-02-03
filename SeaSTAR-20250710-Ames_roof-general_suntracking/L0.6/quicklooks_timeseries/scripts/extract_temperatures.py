#!/usr/bin/env python3

import sys, os
import numpy as np
import argparse
from datetime import *
import pytz

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
#from seastar_analysis_params import *


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

    timestamp = L06_data[timestep]['datetime'].astype(datetime)
    imu_temp = L06_data[timestep]['imu_temp']
    hot_block1_temp = L06_data[timestep]['hot_block1_temp']
    housekeeping_flags = L06_data[timestep]['housekeeping_flags']


    sys.stdout.write(f"{timestamp.isoformat()} {imu_temp} {hot_block1_temp} {housekeeping_flags}\n")




