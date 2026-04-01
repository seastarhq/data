#!/usr/bin/env python3

from datetime import datetime,timedelta
import sys, os
import numpy as np
import pandas as pd
import math
import pytz
import argparse
import tqdm

# custom modules:
import seastar_datautils
from seastar_error_flags import * 
from seastar_analysis_utils import *

# where to find things:
# including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR PICKLE_DIR
from seastar_filepaths import *

# analysis parameters:
# including 
# SEASTAR_TIMEZONE AVG_INTERVAL ANALYSIS_MARGIN BRIGHTNESS_MIN BRIGHTNESS_MAX TRACKING_EUCLIDIAN_MAX
# HOT_BLOCK1_MIN HOT_BLOCK1_MAX HOT_BLOCK2_MIN HOT_BLOCK2_MAX COLD_BLOCK_MIN COLD_BLOCK_MAX
# IMU_TEMP_MIN IMU_TEMP_MAX IMU_PRESS_MIN IMU_PRESS_MAX
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-o', '--outputfile')
args = parser.parse_args()

# findFile needs a list passed to it, so we make one of length 1: 
raw_data_dirs = [PICKLE_DIR,]
L04file = seastar_datautils.findFile(args.file,raw_data_dirs)

L04file_date = os.path.basename(L04file).split(".")[0].split('_')  # assuming a naming convention here...
try:
    sys.stderr.write(f"L04 file date: {L04file_date[1]}\n")
except:
    pass

if args.outputfile is None:
    L05_filename = PICKLE_DIR + '/' + 'SeaSTAR_' + L04file_date[0] + '_' + L04file_date[1] + '.L05'
else:
    L05_filename = PICKLE_DIR + '/' + args.outputfile

L04_data = np.load(L04file, allow_pickle=True)
metadata = L04_data['metadata'][()]
L04_array = L04_data['array_data']

# replace variables from the parameters.sh file with those from the metadata
# since these are the ones that were used from L0 to L04

SEASTAR_TIMEZONE = metadata['SEASTAR_TIMEZONE']
AVG_INTERVAL = metadata['AVG_INTERVAL']
ANALYSIS_MARGIN = metadata['ANALYSIS_MARGIN']
BRIGHTNESS_MIN = metadata['BRIGHTNESS_MIN']
BRIGHTNESS_MAX = metadata['BRIGHTNESS_MAX']
TRACKING_EUCLIDIAN_MAX = metadata['TRACKING_EUCLIDIAN_MAX']
HOT_BLOCK1_MIN = metadata['HOT_BLOCK1_MIN']
HOT_BLOCK1_MAX = metadata['HOT_BLOCK1_MAX']
HOT_BLOCK2_MIN = metadata['HOT_BLOCK2_MIN']
HOT_BLOCK2_MAX = metadata['HOT_BLOCK2_MAX']
COLD_BLOCK_MIN = metadata['COLD_BLOCK_MIN']
COLD_BLOCK_MAX = metadata['COLD_BLOCK_MAX']
IMU_TEMP_MIN = metadata['IMU_TEMP_MIN']
IMU_TEMP_MAX = metadata['IMU_TEMP_MAX']
IMU_PRESS_MIN = metadata['IMU_PRESS_MIN']
IMU_PRESS_MAX = metadata['IMU_PRESS_MAX']

housekeepingparams = {"hotblock1min": HOT_BLOCK1_MIN, "hotblock1max": HOT_BLOCK1_MAX}

for i in tqdm.tqdm(range(len(L04_array)), desc="Processing"):

    L04line = L04_array[i]
    L04_array[i]['flags'][1] = calculate_robot_flags(L04line)
    L04_array[i]['flags'][2] = calculate_housekeeping_flags(L04line,housekeepingparams)

proc_time = datetime.now(pytz.utc).isoformat()
metadata['L04-to-L05_PROCESSING_TIME'] = proc_time

try:
    with open(L05_filename, 'bw') as arrayfile:
        np.savez(arrayfile, array_data = L04_array, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L05', 'bw') as arrayfile:
        np.savez(arrayfile, array_data = L04_array, metadata = metadata)





