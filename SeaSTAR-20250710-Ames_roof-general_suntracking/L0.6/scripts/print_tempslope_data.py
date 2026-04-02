#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz

# custom seastar modules
import seastar_datautils

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

parser = argparse.ArgumentParser()
parser.add_argument('file')
args = parser.parse_args()


temp_slope_data = np.load(args.file, allow_pickle=True)
temp_slope_data = temp_slope_data['array_data']

for timestep in range(len(temp_slope_data)):
    sys.stdout.write(f"{temp_slope_data[timestep]['datetime']} {temp_slope_data[timestep]['temp0']} {temp_slope_data[timestep]['temp1']} {temp_slope_data[timestep]['temp2']} {temp_slope_data[timestep]['slope']}\n")

