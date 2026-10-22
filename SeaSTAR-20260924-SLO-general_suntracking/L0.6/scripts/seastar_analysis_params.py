#!/usr/bin/env python3

import os
import numpy as np

SEASTAR_TIMEZONE = os.environ['SEASTAR_TIMEZONE']
AVG_INTERVAL = float(os.environ['AVG_INTERVAL'])
ANALYSIS_MARGIN = float(os.environ['ANALYSIS_MARGIN'])

BRIGHTNESS_MIN = float(os.environ['BRIGHTNESS_MIN'])
BRIGHTNESS_MAX = float(os.environ['BRIGHTNESS_MAX'])
TRACKING_EUCLIDIAN_MAX = float(os.environ['TRACKING_EUCLIDIAN_MAX'])

HOT_BLOCK1_MIN = float(os.environ['HOT_BLOCK1_MIN'])
HOT_BLOCK1_MAX = float(os.environ['HOT_BLOCK1_MAX'])
HOT_BLOCK2_MIN = float(os.environ['HOT_BLOCK2_MIN'])
HOT_BLOCK2_MAX = float(os.environ['HOT_BLOCK2_MAX'])
COLD_BLOCK_MIN = float(os.environ['COLD_BLOCK_MIN'])
COLD_BLOCK_MAX = float(os.environ['COLD_BLOCK_MAX'])

IMU_TEMP_MIN = float(os.environ['IMU_TEMP_MIN'])
IMU_TEMP_MAX = float(os.environ['IMU_TEMP_MAX'])
IMU_PRESS_MIN = float(os.environ['IMU_PRESS_MIN'])
IMU_PRESS_MAX = float(os.environ['IMU_PRESS_MAX'])

TRIPLET_TOLERANCES = {ch: float(os.environ[f'TRIPLETVAR_TOLERANCE_PERCENT_CH{ch}']) for ch in range(1, 11)}  # in percent...
TRIPLET_TIME = float(os.environ['TRIPLETVAR_TIME'])  # in timesteps + and - (timesteps are currently seconds)
TRIPLET_CHANNELS = [int(ch) for ch in os.environ['TRIPLETVAR_CHANNELS'].split()]  # channels that set the cloud flag
TRIPLET_TRACKING_LEVEL = int(os.environ['TRIPLETVAR_TRACKING_LEVEL'])  # tracking error level that counts as bad tracking

CHANNEL_TEMP_MIN = float(os.environ['CHANNEL_TEMP_MIN'])  # in degrees C, below it sets CHANNEL_TEMP_LOW


# radiometer temperature correction, fitted against AERONET: Vcorr = V / (1 + A*dT (+ B*dT^2)), dT = T - TEMP_CORR_TREF.
# TEMP_CORR_ORDER is lin or quad. the coefficients are per dark-subtracted voltage, order and channel:
# TEMP_CORR_COEFFS[dark][order][ch] = (A, B), with B = 0 for lin
TEMP_CORR_ORDER = os.environ['TEMP_CORR_ORDER']
TEMP_CORR_TREF = float(os.environ['TEMP_CORR_TREF'])
TEMP_CORR_COEFFS = {dark: {'lin': {ch: (float(os.environ[f'TEMP_CORR_{dark.upper()}_LIN_A_CH{ch}']), 0.0)
                                   for ch in range(1, 11)},
                           'quad': {ch: (float(os.environ[f'TEMP_CORR_{dark.upper()}_QUAD_A_CH{ch}']),
                                         float(os.environ[f'TEMP_CORR_{dark.upper()}_QUAD_B_CH{ch}']))
                                    for ch in range(1, 11)}}
                    for dark in ('darksub_lin', 'darksub_quad')}

# dark voltage vs channel temperature, as polynomials in dT = T - DARK_TREF (volts)
DARK_TREF = {ch: float(os.environ[f'DARK_TREF_CH{ch}']) for ch in range(1, 11)}
DARK_LIN_COEFFS = {ch: [float(os.environ[f'DARK_LIN_C{i}_CH{ch}']) for i in range(2)] for ch in range(1, 11)}  # c0, c1
DARK_QUAD_COEFFS = {ch: [float(os.environ[f'DARK_QUAD_C{i}_CH{ch}']) for i in range(3)] for ch in range(1, 11)}  # c0, c1, c2
# caps-on periods used to anchor the dark offset, as UTC start/end pairs: DARK_PERIODS for every channel, plus
# DARK_PERIODS_CH<n> for each channel, and the UTC times that split the run into anchor segments. any can be empty
def parse_periods(text):
    return [tuple(np.datetime64(t, 'ms') for t in period.split('/')) for period in text.split()]
DARK_PERIODS = {ch: parse_periods(os.environ['DARK_PERIODS']) + parse_periods(os.environ[f'DARK_PERIODS_CH{ch}'])
                for ch in range(1, 11)}
DARK_SEGMENT_BREAKS = [np.datetime64(t, 'ms') for t in os.environ['DARK_SEGMENT_BREAKS'].split()]
