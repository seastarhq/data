#!/usr/bin/env python3


import sys, os
import numpy as np
import math
import argparse
import pytz
from scipy.signal import *


# custom seastar modules
import seastar_datautils

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--window', type=int)
args = parser.parse_args()

temp_slope_data = np.load(args.file, allow_pickle=True)
temp_slope_data = temp_slope_data['array_data']


time_subarray = np.array((temp_slope_data['datetime']))
tempslope_subarray = np.array((temp_slope_data['temp0'],temp_slope_data['temp1'],temp_slope_data['temp2'],temp_slope_data['slope'])).transpose()


slope_array = tempslope_subarray[:,3]
#avg_kernel = np.array((0.33333333, 0.33333333, 0.33333333, 0.0, 0.0))
avg_kernel = np.ones(args.window)/args.window

slope_array = convolve(slope_array, avg_kernel, mode='same')

output_dtype_dict = {"datetime": "datetime64[ms]", "slope": "f8"}
output_dtype = np.dtype(list(zip(output_dtype_dict.keys(),output_dtype_dict.values())))
output_array = np.zeros(len(time_subarray), dtype=output_dtype)

for index in range(len(output_array)):

        output_array[index]["datetime"] = time_subarray[index]
        output_array[index]["slope"] = slope_array[index]


with open(f"tempslope_smooth-{args.window}.npy", 'bw') as outputfile:
    np.savez(outputfile, array_data=output_array)



