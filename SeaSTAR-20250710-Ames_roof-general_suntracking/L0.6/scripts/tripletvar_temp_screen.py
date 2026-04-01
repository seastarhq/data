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
# TRIPLETVAR_TOLERANCE_PERCENT TEMP_TRIPLET_TIME
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--temp_triplet_time', type=float)
parser.add_argument('--tempslope_tol', type=float)  
args = parser.parse_args()

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
#if args.triplet_tol is not None:
#    TRIPLET_TOLERANCE = args.triplet_tol
if args.temp_triplet_time is not None:
    TEMP_TRIPLET_TIME = args.temp_triplet_time
if args.tempslope_tol is not None:
    TEMP_TRIPLET_TOLERANCE = args.tempslope_tol

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
print(metadata)
#print(type(metadata))
L06_data = L06_data['array_data']


# for testing, we set all the housekeeping flags back to zero
#L06_data[:]['housekeeping_flags'] = 0

#print(L05_data.shape)

last_timestep = len(L06_data)
for timestep in range(len(L06_data)):

    if timestep < TEMP_TRIPLET_TIME: # we have not advanced enough timesteps 
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1
        continue
    elif timestep + TEMP_TRIPLET_TIME >= last_timestep: # we are less than triplet_time from the end
        L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1 
        continue
    else:  # we can go forward and back by triplet_time
        triplet_forward_time = int(timestep + TEMP_TRIPLET_TIME)
        triplet_backward_time = int(timestep - TEMP_TRIPLET_TIME)
        #sys.stderr.write(f"{triplet_forward_time} {triplet_backward_time}\n")
        hotblock1_triplet = (L06_data[triplet_backward_time]['hot_block1_temp'], L06_data[timestep]['hot_block1_temp'], L06_data[triplet_forward_time]['hot_block1_temp'])

        # 4 scenarios: positive slope, negative slope, crest, valley
        if hotblock1_triplet[0] <= hotblock1_triplet[1] <= hotblock1_triplet[2]:  #positive slope, heater is on, data is invalid
        #    sys.stderr.write("positive slope\n")
            temp_slope = (hotblock1_triplet[2] - hotblock1_triplet[0]) / TEMP_TRIPLET_TIME
            if temp_slope > TEMP_TRIPLET_TOLERANCE: 
                sys.stderr.write(f"{hotblock1_triplet[2]} {hotblock1_triplet[0]} {TEMP_TRIPLET_TIME} {temp_slope}\n")
                L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR1
        elif hotblock1_triplet[0] >= hotblock1_triplet[1] >= hotblock1_triplet[2]: # negative slope, heater is off, data is valid
        #    sys.stderr.write("negative slope\n")
            continue
        elif hotblock1_triplet[1] >= hotblock1_triplet[0] and hotblock1_triplet[1] >= hotblock1_triplet[2]: # valley, heater is turning on, data is invalid
            sys.stderr.write("valley\n")
            L06_data[timestep]['housekeeping_flags'] |= DTDT_ERROR2
        elif hotblock1_triplet[1] <= hotblock1_triplet[0] and hotblock1_triplet[1] <= hotblock1_triplet[2]: # crest, heater is turning off, data is valid
        #    sys.stderr.write("crest\n")
            continue

        
triplet_metadata = {'TEMP_TRIPLET_TIME': TEMP_TRIPLET_TIME, 'TEMP_TRIPLET_TOLERANCE': TEMP_TRIPLET_TOLERANCE}
metadata.update(triplet_metadata)

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)




    




