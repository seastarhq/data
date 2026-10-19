#!/usr/bin/env python3
# this contains the same code as time_avg_and_screen_suntracking, for importing into ipython

from datetime import datetime,timedelta
import sys, os
import numpy as np
import pandas as pd
import math
import pytz
import argparse

# custom modules:
import seastar_datautils
from seastar_error_flags import *
from seastar_analysis_utils import *

from seastar_filepaths import *
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

avg_interval = timedelta(seconds = AVG_INTERVAL)
analysis_margin = timedelta(seconds = ANALYSIS_MARGIN)
tracking_max = TRACKING_EUCLIDIAN_MAX
brightmin = BRIGHTNESS_MIN
brightmax = BRIGHTNESS_MAX

raw_data_dirs = [RAW_DATA_DIR,]
seastar_logfile = seastar_datautils.findFile("2025-07-10_09-23-46_preprocessed.csv",raw_data_dirs)

logfile_date = os.path.basename(seastar_logfile).split("_")

df = pd.read_csv(seastar_logfile,skiprows=0,usecols=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,26,27,28,32,33,34,35,36,37])
df['datetime'] = pd.to_datetime(df['time'], format='%Y-%m-%d %H:%M:%S.%f') 
df['datetime'] = df['datetime'].dt.tz_localize(seastar_timezone)
df.drop('time',axis=1,inplace=True)
# rename the motor & quaternion
df.rename(columns={" q1": "motor_0_enc", " q2": "motor_1_enc", " q3": "motor_2_enc", " qw": "quaternion_w", " qx": "quaternion_x", " qy": "quaternion_y", " qz": "quaternion_z"},inplace=True)
# rename the suntracking 
df.rename(columns={" sunAz": "sun_ephem_az", " sunAlt": "sun_ephem_elev", " sx": "camera_sun_x", " sy": "camera_sun_y", " sb": "camera_sun_brightness", " tx": "camera_target_x", " ty": "camera_target_y"},inplace=True)
# rename the imu variables
df.rename(columns={" rx": "angular_vx", " ry": "angular_vy", " rz": "angular_vz", " ax": "linear_ax", " ay": "linear_ay", " az": "linear_az", " imuT": "imu_temp", " imuP": "imu_press", " imuLat": "imu_lat", " imuLon": "imu_lon"},inplace=True)
# rename the radiometer variables
df.rename(columns={" j3_ch1_1x": "ch1_1x", " j3_ch2_1x": "ch2_1x", " j3_ch3_1x": "ch3_1x", " j3_ch4_1x": "ch4_1x", " j3_ch5_1x": "ch5_1x"},inplace=True)
df.rename(columns={" t3": "hot_block1_temp"},inplace=True)

df['euclidian_dist'] = df.apply(eucl_dist,axis=1)

starttime = df['datetime'][0] # starttime is only used for stderr output!
time_final = df['datetime'][len(df)-1].round('s')

L05_filename = PICKLE_DIR + '/' + 'SeaSTAR-L05-' + logfile_date[0] + "_" + logfile_date[1] + '.pkl'

time0 = df['datetime'][0].round('s')
time0 = time0.to_pydatetime()

timesteps = (time_final - time0) / avg_interval
timesteps = int(timesteps)

L05_3d_array = seastar_datautils.create_L05_3darray(timesteps)

for timestep in range(timesteps):

    L05_2d_line = seastar_datautils.create_L05_2darray()

    time1 = time0 + avg_interval

    screeninterval = df.loc[df['datetime'] < time1]
    screeninterval = screeninterval.loc[(time0 - analysis_margin) < screeninterval['datetime']]
    avginterval = df.loc[df['datetime'] < time1]
    avginterval = avginterval.loc[time0 < avginterval['datetime']]

    sys.stderr.write(f"timestep is {timestep}\n")

    for i in range(len(avginterval)):

        L05_2d_line[i] = (avginterval.iloc[i]['datetime'].to_numpy(),
                avginterval.iloc[i]['motor_0_enc'],
                avginterval.iloc[i]['motor_1_enc'],
                avginterval.iloc[i]['motor_2_enc'],
                avginterval.iloc[i]['quaternion_w'],
                avginterval.iloc[i]['quaternion_x'],
                avginterval.iloc[i]['quaternion_y'],
                avginterval.iloc[i]['quaternion_z'],
                avginterval.iloc[i]['sun_ephem_az'],
                avginterval.iloc[i]['sun_ephem_elev'],
                avginterval.iloc[i]['camera_sun_x'],
                avginterval.iloc[i]['camera_sun_y'],
                avginterval.iloc[i]['camera_sun_brightness'],
                avginterval.iloc[i]['camera_target_x'],
                avginterval.iloc[i]['camera_target_y'],
                avginterval.iloc[i]['angular_vx'],
                avginterval.iloc[i]['angular_vy'],
                avginterval.iloc[i]['angular_vz'],
                avginterval.iloc[i]['linear_ax'],
                avginterval.iloc[i]['linear_ay'],
                avginterval.iloc[i]['linear_az'],
                avginterval.iloc[i]['imu_temp'],
                avginterval.iloc[i]['imu_press'],
                avginterval.iloc[i]['imu_lat'],
                avginterval.iloc[i]['imu_lon'],
                avginterval.iloc[i]['ch1_1x'],
                avginterval.iloc[i]['ch2_1x'],
                avginterval.iloc[i]['ch3_1x'],
                avginterval.iloc[i]['ch4_1x'],
                avginterval.iloc[i]['ch5_1x'],
                avginterval.iloc[i]['hot_block1_temp'],
                avginterval.iloc[i]['euclidian_dist'],
                0)   # 0 is what we set the initial flags to, then set them once we've filled up the L05array
       # sys.stderr.write(f"i = {i}") 

    L05_3d_array[timestep] = L05_2d_line

    time0 = time1
    


