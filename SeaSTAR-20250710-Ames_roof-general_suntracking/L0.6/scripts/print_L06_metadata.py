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

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)
L06_file_date = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[1]
L06_file_time = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[2]

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
print(metadata)


