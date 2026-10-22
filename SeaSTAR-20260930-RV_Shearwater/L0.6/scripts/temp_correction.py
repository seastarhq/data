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
# TEMP_CORR_ORDER TEMP_CORR_TREF TEMP_CORR_COEFFS
from seastar_analysis_params import *

# temperature corrects the dark-subtracted voltages (from dark_subtraction.py) with AERONET's form,
#     ch<n>_1x_darksub_<dark>_tc = ch<n>_1x_darksub_<dark> / (1 + A*dT)              TEMP_CORR_ORDER=lin
#     ch<n>_1x_darksub_<dark>_tc = ch<n>_1x_darksub_<dark> / (1 + A*dT + B*dT^2)     TEMP_CORR_ORDER=quad
# with dT = ch<n>_temp - TEMP_CORR_TREF, and A and B fitted against AERONET for each dark-subtracted voltage
# by calibration_vs_ref (fit_tempcorr.py, written into parameters.sh by write_tempcorr_params.py).
# the uncorrected fields are left as they are, so the AERONET matching can refit from them.
# a channel temperature of exactly 0 is the sensors' startup zeros, so the corrected fields are NaN there.

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--order', choices=('lin', 'quad'),
                    help='use the linear or quadratic coefficients, instead of TEMP_CORR_ORDER')
args = parser.parse_args()

CHANNELS = range(1, 11)  # ch1-5 are block 1, ch6-10 are block 2
DARKS = ('darksub_lin', 'darksub_quad')

if args.order is not None:
    TEMP_CORR_ORDER = args.order
if TEMP_CORR_ORDER not in ('lin', 'quad'):
    sys.exit(f"TEMP_CORR_ORDER must be lin or quad, not {TEMP_CORR_ORDER!r}")

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

temp_corr_metadata = {'TEMP_CORR_ORDER': TEMP_CORR_ORDER, 'TEMP_CORR_TREF': TEMP_CORR_TREF}
for ch in CHANNELS:
    temp = np.where(L06_data[f'ch{ch}_temp'] == 0.0, np.nan, L06_data[f'ch{ch}_temp'])
    dT = temp - TEMP_CORR_TREF
    for dark in DARKS:
        A, B = TEMP_CORR_COEFFS[dark][TEMP_CORR_ORDER][ch]
        L06_data[f'ch{ch}_1x_{dark}_tc'] = L06_data[f'ch{ch}_1x_{dark}'] / (1.0 + A * dT + B * dT ** 2)
        temp_corr_metadata[f'TEMP_CORR_{dark.upper()}_A_CH{ch}'] = A
        temp_corr_metadata[f'TEMP_CORR_{dark.upper()}_B_CH{ch}'] = B

temp_corr_metadata['LAST_PROCESSING_TIME'] = datetime.now(pytz.utc).isoformat()
metadata.update(temp_corr_metadata)

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
