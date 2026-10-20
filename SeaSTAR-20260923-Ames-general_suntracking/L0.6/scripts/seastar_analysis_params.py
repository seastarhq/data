#!/usr/bin/env python3

import os

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


TEMP_CORR_BASELINE = float(os.environ['TEMP_CORR_BASELINE'])
TEMP_CORR_SCALEFACTORS = {ch: float(os.environ[f'TEMP_CORR_SCALEFACTOR_CH{ch}']) for ch in range(1, 11)}
