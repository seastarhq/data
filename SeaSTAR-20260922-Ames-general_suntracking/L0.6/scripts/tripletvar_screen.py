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
parser.add_argument('--triplet_tol', type=float,
                    help='use this tolerance (percent) for every channel, instead of the per-channel ones')
parser.add_argument('--triplet_time', type=float)
parser.add_argument('--triplet_channels', type=int, nargs='+',
                    help='channels whose triplet variation sets the cloud flag')
parser.add_argument('--triplet_tracking_level', type=int, choices=(1, 2, 3),
                    help='tracking error level at which a timestep counts as badly tracked')
args = parser.parse_args()

CHANNELS = range(1, 11)  # ch1-5 are block 1, ch6-10 are block 2

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
if args.triplet_tol is not None:
    TRIPLET_TOLERANCES = {ch: args.triplet_tol for ch in CHANNELS}
if args.triplet_time is not None:
    TRIPLET_TIME = args.triplet_time
if args.triplet_channels is not None:
    TRIPLET_CHANNELS = args.triplet_channels
if args.triplet_tracking_level is not None:
    TRIPLET_TRACKING_LEVEL = args.triplet_tracking_level

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


# the triplet is only used when the tracking is good at all three of its timesteps: otherwise
# the variation could come from the pointing rather than the sky, and the screening can't be done
# (AUTO_CLOUD_FLAG_FAIL, with tvar left as nan). the tracking error bits are cumulative, so testing the
# chosen level's bit catches that level and every level above it
tracking_error_bit = {1: TRACKING_ERROR_1, 2: TRACKING_ERROR_2, 3: TRACKING_ERROR_3}[TRIPLET_TRACKING_LEVEL]
bad_tracking = NO_CAMERA_DATA | CAMERA_BRIGHTNESS_HIGH | CAMERA_BRIGHTNESS_LOW | tracking_error_bit
good_tracking = (L06_data['tracking_flags'] & bad_tracking) == 0

last_time = len(L06_data)
for timestep in range(len(L06_data)):

    if timestep < TRIPLET_TIME: # we have not advanced enough timesteps 
        L06_data[timestep]['cloud_flags'] = AUTO_CLOUD_FLAG_FAIL
        continue
    elif timestep + TRIPLET_TIME >= last_time: # we are less than triplet_time from the end
        L06_data[timestep]['cloud_flags'] = AUTO_CLOUD_FLAG_FAIL
        continue
    else:  # we can go forward and back by triplet_time
        triplet_forward_time = int(timestep + TRIPLET_TIME)
        triplet_backward_time = int(timestep - TRIPLET_TIME)
        print(f"{triplet_forward_time} {triplet_backward_time}\n")
        if not (good_tracking[triplet_backward_time] and good_tracking[timestep] and good_tracking[triplet_forward_time]):
            L06_data[timestep]['cloud_flags'] = AUTO_CLOUD_FLAG_FAIL
            continue
        for ch in CHANNELS:
            ch_triplet = (L06_data[triplet_backward_time][f'ch{ch}_1x'], L06_data[timestep][f'ch{ch}_1x'], L06_data[triplet_forward_time][f'ch{ch}_1x'])
            tvar = calc_tvar(ch_triplet)
            L06_data[timestep][f'tvar_ch{ch}'] = tvar
            if ch in TRIPLET_CHANNELS and tvar * 100.0 > TRIPLET_TOLERANCES[ch]:  # tvar is a fraction, the tolerance is in percent
                L06_data[timestep]['cloud_flags'] = TVAR_OOB

now = datetime.now(pytz.utc).isoformat()
triplet_metadata = {'TRIPLETVAR_TIME': TRIPLET_TIME, 'TRIPLETVAR_CHANNELS': TRIPLET_CHANNELS,
                    'TRIPLETVAR_TRACKING_LEVEL': TRIPLET_TRACKING_LEVEL, 'LAST_PROCESSING_TIME': now}
triplet_metadata.update({f'TRIPLETVAR_TOLERANCE_PERCENT_CH{ch}': TRIPLET_TOLERANCES[ch] for ch in CHANNELS})
metadata.update(triplet_metadata)
#print(metadata)
#print(L06_npyfile)


try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)

