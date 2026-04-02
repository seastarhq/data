#!/usr/bin/env python3


import sys, os
import numpy as np
import math
import argparse
import pytz
from numpy.lib.stride_tricks import sliding_window_view

# custom seastar modules
import seastar_datautils

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--window_shape', type=int)
args = parser.parse_args()


temp_slope_data = np.load(args.file, allow_pickle=True)
temp_slope_data = temp_slope_data['array_data']


time_subarray = np.array((temp_slope_data['datetime']))
tempslope_subarray = np.array((temp_slope_data['temp0'],temp_slope_data['temp1'],temp_slope_data['temp2'],temp_slope_data['slope'])).transpose()


slope_array = tempslope_subarray[:,3]

view = sliding_window_view(slope_array, window_shape=(args.window_shape))

moving_avg = view.mean(axis=-1)


# need to concatenate the arrays h



