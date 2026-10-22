#!/usr/bin/env python3

import sys, os
import numpy as np
import argparse
import pytz
from datetime import datetime

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *
from seastar_analysis_utils import *

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

## analysis parameters:
# including
# CHANNEL_TEMP_MIN
from seastar_analysis_params import *

# sets the CHANNEL_TEMP_LOW housekeeping flag on every timestep where any channel's (interpolated)
# temperature is below CHANNEL_TEMP_MIN. a channel with no temperature (NaN) doesn't set it; the
# startup zeros do, since they're below any sensible minimum.
# the flag is cleared first, so rerunning is safe.

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--channel_temp_min', type=float,
                    help='flag timesteps with any channel temperature below this, in degrees C')
args = parser.parse_args()

CHANNELS = range(1, 11)  # ch1-5 are block 1, ch6-10 are block 2

if args.channel_temp_min is not None:
    CHANNEL_TEMP_MIN = args.channel_temp_min

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

too_cold = np.zeros(len(L06_data), dtype=bool)
for ch in CHANNELS:
    too_cold |= L06_data[f'ch{ch}_temp'] < CHANNEL_TEMP_MIN  # NaN compares False
L06_data['housekeeping_flags'] &= ~CHANNEL_TEMP_LOW
L06_data['housekeeping_flags'][too_cold] |= CHANNEL_TEMP_LOW

metadata.update({'CHANNEL_TEMP_MIN': CHANNEL_TEMP_MIN, 'LAST_PROCESSING_TIME': datetime.now(pytz.utc).isoformat()})

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
