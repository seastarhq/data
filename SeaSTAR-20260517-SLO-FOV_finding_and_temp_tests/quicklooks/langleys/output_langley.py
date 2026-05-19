#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz
import tqdm
import pandas as pd

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

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-o', '--outputfile')
args = parser.parse_args()

# findFile needs a list passed to it, so we make one with `cwd` added 
L06_data_dir = [L06_DATA_DIR, './']
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)
# this is if our filename does not conform to convention
try:
    L06_file_date = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[1]
    L06_file_time = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[2]
except: 
    pass

#print(f"\n\n{L05_file_date} {L05_file_time}\n\n")

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

#print(L05_data.shape)

#L10_data = seastar_datautils.create_L10_sun_2darray(len(L05_data))
if args.outputfile is None:
    outfile = "./recoveryfile.txt"
else:
    outfile = QUICKLOOKS_DIR + '/' + 'langleys/' + args.outputfile




with open(outfile, "w") as textfile:

    for timestep in tqdm.tqdm(range(len(L06_data))):

        mydatetime = L06_data[timestep]['datetime']
        #motor_0_enc = np.nan # not important?
    #motor_1_enc = np.nan # not important?
    #motor_2_enc = np.nan
    #quaternion_w = np.nan
    #quaternion_x = np.nan
    #quaternion_y = np.nan
    #quaternion_z = np.nan
        mysun_ephem_az = L06_data[timestep]['sun_ephem_az']
        mysun_ephem_elev = L06_data[timestep]['sun_ephem_elev']
    #L06_data[timestep]['camera_sun_x'] = np.nanmean(L05_data[timestep][:]['camera_sun_x'])
    #L06_data[timestep]['camera_sun_y'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    #L06_data[timestep]['camera_sun_brightness'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    #L06_data[timestep]['camera_target_x'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    #L06_data[timestep]['camera_target_y'] = np.nanmean(L05_data[timestep][:]['sun_ephem_elev'])
    #angular_vx = np.nan
    #angular_vy = np.nan
    #angular_vz = np.nan
    #linear_ax = np.nan
    #linear_ay = np.nan
    #linear_az = np.nan
    #L06_data[timestep]['imu_temp'] = np.nanmean(L05_data[timestep][:]['imu_temp'])
        myimu_press = L06_data[timestep]['imu_press'] 
        mylat = L06_data[timestep]['imu_lat']
        mylon = L06_data[timestep]['imu_lon']
        logch1_1x = math.log(-1.0 * (L06_data[timestep]['ch1_1x'] - 0.009))
        logch2_1x = math.log(-1.0 * (L06_data[timestep]['ch2_1x'] - 0.009))
        logch3_1x = math.log(-1.0 * (L06_data[timestep]['ch3_1x'] - 0.009))
        logch4_1x = math.log(-1.0 * (L06_data[timestep]['ch4_1x'] - 0.009))
        logch5_1x = math.log(-1.0 * (L06_data[timestep]['ch5_1x'] - 0.009))
        myhot_block_temp =  L06_data[timestep]['hot_block1_temp']
        myeuclidian_dist = L06_data[timestep]['euclidian_dist'] 
        mytracking_flags = L06_data[timestep]['tracking_flags'] 
        myrobot_flags = L06_data[timestep]['robot_flags']
        myhousekeeping_flags =L06_data[timestep]['housekeeping_flags'] 
        myradiometer_1x_flags = L06_data[timestep]['radiometer_1x_flags'] 
    #L06_data[timestep]['radiometer_100x_flags'] = L05_data[timestep][4]['flags']
    #L06_data[timestep]['radiometer_10kx_flags'] = L05_data[timestep][5]['flags']
    #L06_data[timestep]['cloud_flags'] = 0


        airmass = airmass_star(mysun_ephem_elev, myimu_press)
        dataline = f"{airmass} {logch1_1x} {logch2_1x} {logch3_1x} {logch4_1x} {logch5_1x} {myhot_block_temp}\n"
        textfile.write(dataline)
    



#try:
#    with open(L06_npyfile, 'bw') as arrayfile:
#        np.savez(arrayfile, array_data=L06_data, metadata = metadata)
#except FileNotFoundError:
#    with open('recoveryfilename.L06', 'bw') as arrayfile:
#        np.savez(arrayfile, array_data=L06_data, metadata = metadata)





    




