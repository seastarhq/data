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
# DARK_TREF DARK_LIN_COEFFS DARK_QUAD_COEFFS DARK_PERIODS DARK_SEGMENT_BREAKS
from seastar_analysis_params import *

# models the dark voltage of each channel from its (interpolated) temperature, with the straight-line and
# quadratic fits to the 20261014 caps-on run (fit_dark_vs_temp.py there), and subtracts each from ch<n>_1x:
#     ch<n>_dark_lin         c0 + c1*dT
#     ch<n>_dark_quad        c0 + c1*dT + c2*dT^2        with dT = ch<n>_temp - DARK_TREF_CH<n>
#     ch<n>_1x_darksub_lin   ch<n>_1x - ch<n>_dark_lin
#     ch<n>_1x_darksub_quad  ch<n>_1x - ch<n>_dark_quad
# ch<n>_1x itself is left raw. a channel temperature of exactly 0 is the sensors' startup zeros, not a reading,
# so the dark fields are NaN there.
# if the run has caps-on darks (DARK_PERIODS for all channels, DARK_PERIODS_CH<n> for one), the curves are
# anchored to them: the run is split into segments at DARK_SEGMENT_BREAKS, and in each segment both curves
# are shifted by the mean of (measured - modelled) over that channel's dark timesteps in the segment.
# a segment with no darks for a channel uses its curves unshifted.

parser = argparse.ArgumentParser()
parser.add_argument('file')
args = parser.parse_args()

CHANNELS = range(1, 11)  # ch1-5 are block 1, ch6-10 are block 2
MODELS = {'lin': DARK_LIN_COEFFS, 'quad': DARK_QUAD_COEFFS}

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

times = L06_data['datetime'].astype('datetime64[ms]')
breaks = np.sort(np.array(DARK_SEGMENT_BREAKS, dtype='datetime64[ms]'))
segment = np.searchsorted(breaks, times, side='right')  # 0 before the first break, 1 after it, ...

dark_metadata = {'DARK_SEGMENT_BREAKS': [str(t) for t in breaks]}
for ch in CHANNELS:
    in_dark = np.zeros(len(L06_data), dtype=bool)
    for start, end in DARK_PERIODS[ch]:
        in_dark |= (times >= start) & (times <= end)
    dark_metadata[f'DARK_PERIODS_CH{ch}'] = [f'{start}/{end}' for start, end in DARK_PERIODS[ch]]
    dark_metadata[f'DARK_ANCHORED_CH{ch}'] = bool(in_dark.any())
    dark_metadata[f'DARK_TREF_CH{ch}'] = DARK_TREF[ch]
    temp = np.where(L06_data[f'ch{ch}_temp'] == 0.0, np.nan, L06_data[f'ch{ch}_temp'])
    dT = temp - DARK_TREF[ch]
    for name, coeffs in MODELS.items():
        dark = np.polynomial.polynomial.polyval(dT, coeffs[ch])
        offsets = []
        for seg in range(len(breaks) + 1):
            anchor = in_dark & (segment == seg)
            residual = L06_data[f'ch{ch}_1x'][anchor] - dark[anchor]
            offset = np.nanmean(residual) if np.isfinite(residual).any() else 0.0
            dark[segment == seg] += offset
            offsets.append(float(offset))
        L06_data[f'ch{ch}_dark_{name}'] = dark
        L06_data[f'ch{ch}_1x_darksub_{name}'] = L06_data[f'ch{ch}_1x'] - dark
        dark_metadata.update({f'DARK_{name.upper()}_C{i}_CH{ch}': c for i, c in enumerate(coeffs[ch])})
        dark_metadata[f'DARK_{name.upper()}_ANCHOR_OFFSETS_CH{ch}'] = offsets  # volts, one per segment

dark_metadata['LAST_PROCESSING_TIME'] = datetime.now(pytz.utc).isoformat()
metadata.update(dark_metadata)

try:
    with open(L06_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L06', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
