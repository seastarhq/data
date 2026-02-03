#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *
from seastar_analysis_utils import *

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

## analysis parameters:
# including 
# SEASTAR_TIMEZONE AVG_INTERVAL ANALYSIS_MARGIN BRIGHTNESS_MIN BRIGHTNESS_MAX TRACKING_EUCLIDIAN_MAX
# HOT_BLOCK1_MIN HOT_BLOCK1_MAX HOT_BLOCK2_MIN HOT_BLOCK2_MAX COLD_BLOCK_MIN COLD_BLOCK_MAX
# IMU_TEMP_MIN IMU_TEMP_MAX IMU_PRESS_MIN IMU_PRESS_MAX
# TRIPLETVAR_TOLERANCE_PERCENT
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--triplet_tol', type=float)
args = parser.parse_args()

# get analysis parameters from command line arguments, by overriding what's read in in the import above
# or default to values set in environment variables
if args.triplet_tol is not None:
    TRIPLET_TOLERANCE = args.trackerror

# findFile needs a list passed to it, so we make one with length 1
L05_data_dir = [L05_DATA_DIR,]
L05_npyfile = seastar_datautils.findFile(args.file, L05_data_dir)
L05_file_date = os.path.splitext(os.path.basename(L05_npyfile))[0].split("_")[1]
L05_file_time = os.path.splitext(os.path.basename(L05_npyfile))[0].split("_")[2]

#print(f"\n\n{L05_file_date} {L05_file_time}\n\n")

L05_data = np.load(L05_npyfile, allow_pickle=True)
metadata = L05_data['metadata']
L05_data = L05_data['array_data']

#print(L05_data.shape)

L06_data = seastar_datautils.create_L06_sun_2darray(len(L05_data))
L06_npyfile = L06_DATA_DIR + '/' + 'SeaSTAR-L06_' + L05_file_date + "_" + L05_file_time

for timestep in range(len(L05_data)):

    L06_data['datetime'] = min(L05_data[timestep][:]['datetime'])
    #motor_0_enc = np.nan # not important?
    #motor_1_enc = np.nan # not important?
    #motor_2_enc = np.nan
    #quaternion_w = np.nan
    #quaternion_x = np.nan
    #quaternion_y = np.nan
    #quaternion_z = np.nan
    L06_data['sun_ephem_az'] = np.nanmean(L05_data[timestep][:]['sun_ephem_az'])
    L06_data['sun_ephem_elev'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    L06_data['camera_sun_x'] = np.nanmean(L05_data[timestep][:]['camera_sun_x'])
    L06_data['camera_sun_y'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    L06_data['camera_sun_brightness'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    L06_data['camera_target_x'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    L06_data['camera_target_y'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    #angular_vx = np.nan
    #angular_vy = np.nan
    #angular_vz = np.nan
    #linear_ax = np.nan
    #linear_ay = np.nan
    #linear_az = np.nan
    L06_data['imu_temp'] = np.nanmean(L05_data[timestep][:]['imu_temp'])
    L06_data['imu_press'] = np.nanmean(L05_data[timestep][:]['imu_press'])
    L06_data['imu_lat'] = np.nanmean(L05_data[timestep][:]['imu_lat'])
    L06_data['imu_lon'] = np.nanmean(L05_data[timestep][:]['imu_lon'])
    L06_data['ch1_1x'] = np.nanmean(L05_data[timestep][:]['ch1_1x'])
    L06_data['ch2_1x'] = np.nanmean(L05_data[timestep][:]['ch2_1x'])
    L06_data['ch3_1x'] = np.nanmean(L05_data[timestep][:]['ch3_1x'])
    L06_data['ch4_1x'] = np.nanmean(L05_data[timestep][:]['ch4_1x'])
    L06_data['ch5_1x'] = np.nanmean(L05_data[timestep][:]['ch5_1x'])
    L06_data['hot_block1_temp'] = np.nanmean(L05_data[timestep][:]['hot_block1_temp'])
    L06_data['euclidian_dist'] = np.nanmax(L05_data[timestep][:]['euclidian_dist'])
    L06_data['tracking_flags'] = L05_data[timestep][0]['flags']
    L06_data['robot_flags'] = L05_data[timestep][1]['flags']
    L06_data['housekeeping_flags'] = L05_data[timestep][2]['flags']
    L06_data['radiometer_1x_flags'] = L05_data[timestep][3]['flags']
    L06_data['radiometer_100x_flags'] = L05_data[timestep][4]['flags']
    L06_data['radiometer_10kx_flags'] = L05_data[timestep][5]['flags']
    L06_data['cloud_flags'] = 0


np.savez(L06_npyfile, array_data=L06_data, metadata = metadata)





    




