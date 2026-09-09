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
