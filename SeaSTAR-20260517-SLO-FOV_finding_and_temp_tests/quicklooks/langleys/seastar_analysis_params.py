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

TRIPLET_TOLERANCE = float(os.environ['TRIPLETVAR_TOLERANCE_PERCENT'])  # in percent...
TRIPLET_TIME = float(os.environ['TRIPLETVAR_TIME'])  # in timesteps + and - (timesteps are currently seconds)

TEMP_TRIPLET_TIME = float(os.environ['TEMP_TRIPLET_TIME'])
TEMP_SLOPE_TOLERANCE = float(os.environ['TEMP_SLOPE_TOLERANCE'])
WINDOWWIDTH = int(os.environ['WINDOWWIDTH'])
TEMP_D2TDT2_TOLERANCE = float(os.environ['TEMP_D2TDT2_TOLERANCE'])

TEMP_CORR_BASELINE = float(os.environ['TEMP_CORR_BASELINE'])
TEMP_CORR_SCALEFACTOR = float(os.environ['TEMP_CORR_SCALEFACTOR'])

CALIBRATION_SOURCE = os.environ['CALIBRATION_SOURCE']
CALIBRATION_DATE = os.environ['CALIBRATION_DATE']

CH1_NM = int(os.environ['CH1_NM'])
CH2_NM = int(os.environ['CH2_NM'])
CH3_NM = int(os.environ['CH3_NM'])
CH4_NM = int(os.environ['CH4_NM'])
CH5_NM = int(os.environ['CH5_NM'])

#VZERO_CH1 = float(os.environ['VZERO_CH1'])
#VZERO_CH2 = float(os.environ['VZERO_CH2'])
#VZERO_CH3 = float(os.environ['VZERO_CH3'])
#VZERO_CH4 = float(os.environ['VZERO_CH4'])
#VZERO_CH5 = float(os.environ['VZERO_CH5'])

