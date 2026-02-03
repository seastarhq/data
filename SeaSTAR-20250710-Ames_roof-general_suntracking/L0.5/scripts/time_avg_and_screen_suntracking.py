#!/usr/bin/env python3

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

# where to find things:
# including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR PICKLE_DIR
from seastar_filepaths import *

# analysis parameters:
# including 
# SEASTAR_TIMEZONE AVG_INTERVAL ANALYSIS_MARGIN BRIGHTNESS_MIN BRIGHTNESS_MAX TRACKING_EUCLIDIAN_MAX
# HOT_BLOCK1_MIN HOT_BLOCK1_MAX HOT_BLOCK2_MIN HOT_BLOCK2_MAX COLD_BLOCK_MIN COLD_BLOCK_MAX
# IMU_TEMP_MIN IMU_TEMP_MAX IMU_PRESS_MIN IMU_PRESS_MAX
from seastar_analysis_params import *

seastar_timezone = pytz.timezone(SEASTAR_TIMEZONE) # we only get this from the parameters file, not cli 

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-i', '--interval', type=float)
parser.add_argument('-m', '--margin', type=float)
parser.add_argument('--trackerror', type=float)
parser.add_argument('-brightmin', type=float)
parser.add_argument('-brightmax', type=float)
args = parser.parse_args()

# get analysis parameters from command line arguments
# or default to values set in environment variables
if args.interval  is not None:
    avg_interval = timedelta(seconds = args.interval)
else:
    avg_interval = timedelta(seconds = AVG_INTERVAL)
if args.margin is not None:
    analysis_margin = timedelta(seconds = args.margin)
else:
    analysis_margin = timedelta(seconds = ANALYSIS_MARGIN)
if args.trackerror is not None:
    TRACKING_EUCLIDIAN_MAX = args.trackerror
if args.brightmin is not None:
    BRIGHTNESS_MIN = args.brightmin
if args.brightmax is not None:
    BRIGHTNESS_MAX = args.brightmax

# findFile needs a list passed to it, so we make one of length 1: 
raw_data_dirs = [RAW_DATA_DIR,]
seastar_logfile = seastar_datautils.findFile(args.file,raw_data_dirs)

logfile_date = os.path.basename(seastar_logfile).split("_")

sys.stderr.write(f"seastar logfile date: {logfile_date[0]}\n")
sys.stderr.write(f"averaging interval: {avg_interval}\n")
sys.stderr.write(f"analysis margin: {analysis_margin}\n")

# we use pandas: # the things we are interested in are # columns: 
# 0=timestamp, 
# 1=m0_encoder 2=m1_encoder 3=m2_encoder 
# 4=sun_ephem_az 5=sun_ephem_elev
# 6=quaternion_w 7=quaternion_x 8=quaternion_y 9=quaterion_z
# 10=camera_sun_x 11=camera_sun_y 12=camera_brightness 13=camera_target_x 14=camera_target_y
# 15=angular_vx, 16=angular_vy, 17=angular_vz, 18=linear_ax, 19=linear_ay, 20=linear_az,
# we omit for now: correction quaternion components: 21 22 23 24 
# 25=imu_temp, 26=imu_press, 27=imu_lat, 28=imu_lon 
# we omit for now: 29=hyperbolic_min 30=hyper_max 31=hyper_scale
# 32=ch1, 33=ch2, 34=ch3, 35=ch4, 36=ch5
# 37=t3

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
sys.stderr.write(f"Number of variables in the Pandas datastructure: {len(df.columns)}\n")

sys.stderr.write(f"calculating tracking errors\n")
df['euclidian_dist'] = df.apply(eucl_dist,axis=1)

sys.stderr.write(f"updated number of variables in the Pandas datastructure: {len(df.columns)}\n")

starttime = df['datetime'][0] # starttime is only used for the stderr output in the line below!
sys.stderr.write(f"seastar logfile start time: {starttime}\n")
time_final = df['datetime'][len(df)-1].round('s')
sys.stderr.write(f"seastar logfile end time: {time_final}\n")

L05_filename = PICKLE_DIR + '/' + 'SeaSTAR-L05_' + logfile_date[0] + "_" + logfile_date[1]

# we do three passes through the data. These will screen:
# 1. Bad suntracking, based on euclidian distance
# 2. Temperatures out of bounds
# 3. Dropouts of radiometer voltages
# we might do more in future:
# 4. Other things we have not yet thought of...

# we need to use a numpy array to hold each timestep's data - thus need to figure out how many timesteps there
# going to be. (Sadly, it looks like Pandas and Xarray will not be suitable for this.)
# this will be a  3-d array, where each timestep contains the raw data (with times) in a 2-d array:
#
#labels: time, var1, var2 , var3... var-n, flags
#
#        time1, 0.1 , 0.2 , 0.3 ... 0.4, 0
#        time2, 0.1 , 0.2 , 0.3 ... 0.4, 0
#        time3, 0.1 , 0.2 , 0.3 ... 0.4, 0
#        time4, 0.1 , 0.2 , 0.3 ... 0.4, 0
#        ...
#        timen, 0.1 , 0.2 , 0.3 ... 0.4, 0
#        NaT  , Nan , Nan , Nan ... Nan, 0
#        NaT  , Nan , Nan , Nan ... Nan, 0
#
# Nan padding is to make sure we have space for all the raw data in each timestep
# taking care not to repeat data, i.e. time1 should not be the same as time-n from the 
# previous timestep
# 
# This will be the L0.5 data - basically raw data but tidied up and screened and flagged for bad tracking or housekeeping 
# from each timestep, we can calcaluate 1-s averages & stats - e.g. for radiometer data and products
# or alternatively, we still have the raw data e.g. quaternions and encoders for robot data and products    

time0 = df['datetime'][0].round('s')
time0 = time0.to_pydatetime()

sys.stderr.write(f"time 0: {time0}\n")
sys.stderr.write(f"time final: {time_final}\n")

timesteps = (time_final - time0) / avg_interval
sys.stderr.write(f"These should always be equal float and integer: {timesteps} {int(timesteps)} timesteps\n")
timesteps = int(timesteps)

# this function creates a 3-d array [timesteps][maxdatapoints=60][dtype_dict] of NaT/NaN/0 to put all the data in
sys.stderr.write("creating the 3-d L05 array...")
L05_3d_array = seastar_datautils.create_L05_3darray(timesteps)
sys.stderr.write("\n")

for timestep in range(timesteps):

    sys.stderr.write(f"timestep: {timestep}\n")

# this function creates a 2-d array of NaT/NaN/0 for each timestep from the df dataframe
# which then get put into the appropriate timestep of the L05array
    sys.stderr.write("creating the 2-d L05 array...\n")
    L05_2d_line = seastar_datautils.create_L05_2darray()
    sys.stderr.write(f"{L05_2d_line[0][2]}\n")

# we calculate statistics for each avg_interval, from these we can see 
# bad suntracking - max euclidian distance bigger than theshold
# temperatures - mean/stddev of temps
# dropouts  - min/max vs mean

# we start with the first avg_interval to create the first layer of the 3-d array, then go into a loop

    time1 = time0 + avg_interval
    sys.stderr.write(f"time 1: {time1}\n\n")

    screeninterval = df.loc[df['datetime'] < time1] # screeninterval is a pandas dataframe extended backwards in time compared to avginterval, which we use to screen bad suntracking
    screeninterval = screeninterval.loc[(time0 - analysis_margin) < screeninterval['datetime']]
    avginterval = df.loc[df['datetime'] < time1]  # avginterval is a pandas dataframe
    avginterval = avginterval.loc[time0 < avginterval['datetime']]

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
                0)   # 0 is what we set the initial flags to, 
        
        
#then set them once we've filled up the L05array

# flag locations in the L05 arrays:
# are described in seastar_error_flags.py: (that is the canonical location)
# L05_2d_line['flags'][0] is tracking flags
# L05_2d_line['flags'][1] is robot flags
# L05_2d_line['flags'][2] is housekeeping flags
#                   [3] is 1x radiometer flags
#                   [4] is 100x radiometer flags
#                   [5] is 10kx radiometer flags

    sys.stderr.write("camera stats and flagging...")
    trackingparams = {"trackingmax": TRACKING_EUCLIDIAN_MAX, "brightmin": BRIGHTNESS_MIN, "brightmax": BRIGHTNESS_MAX}
    L05_2d_line['flags'][0] = calculate_tracking_flags(screeninterval,avginterval,trackingparams) # trackingflags
    sys.stderr.write("\n")

    sys.stderr.write("robot stats and flagging...")
# robot flags doesn't need parameters for now
    L05_2d_line['flags'][1] = calculate_robot_flags(avginterval)
    sys.stderr.write("\n")

    sys.stderr.write("housekeeping stats and flagging...")
# for now we only worry about the hot block temp
    housekeepingparams = {"hotblock1min": HOT_BLOCK1_MIN, "hotblock1max": HOT_BLOCK1_MAX}
    L05_2d_line['flags'][2] = calculate_housekeeping_flags(avginterval,housekeepingparams)


    L05_3d_array[timestep] = L05_2d_line

    time0 = time1

# save the L05_3d_array as a pickle file:

sys.stderr.write(f"saving the L05 3d array as: {L05_filename}")

metadata = {'ROOT_DIR': ROOT_DIR,\
        'SCRIPTS_DIR': SCRIPTS_DIR,\
        'RAW_DATA_DIR': RAW_DATA_DIR,\
        'EXTRACTED_DATA_DIR': EXTRACTED_DATA_DIR,\
        'PICKLE_DIR': PICKLE_DIR,\
        'SEASTAR_TIMEZONE': seastar_timezone.zone,\
        'AVG_INTERVAL': avg_interval.seconds,\
        'ANALYSIS_MARGIN': analysis_margin.seconds,\
        'BRIGHTNESS_MIN': BRIGHTNESS_MIN,\
        'BRIGHTNESS_MAX': BRIGHTNESS_MAX,\
        'TRACKING_EUCLIDIAN_MAX': TRACKING_EUCLIDIAN_MAX,\
        'HOT_BLOCK1_MIN': HOT_BLOCK1_MIN,\
        'HOT_BLOCK1_MAX': HOT_BLOCK1_MAX,\
        'HOT_BLOCK2_MIN': HOT_BLOCK2_MIN,\
        'HOT_BLOCK2_MAX': HOT_BLOCK2_MAX,\
        'COLD_BLOCK_MIN': COLD_BLOCK_MIN,\
        'COLD_BLOCK_MAX': COLD_BLOCK_MAX,\
        'COLD_BLOCK_MAX': COLD_BLOCK_MAX,\
        'IMU_TEMP_MIN': IMU_TEMP_MIN,\
        'IMU_TEMP_MAX': IMU_TEMP_MAX,\
        'IMU_PRESS_MIN': IMU_PRESS_MIN,\
        'IMU_PRESS_MAX': IMU_PRESS_MAX } 

np.savez(L05_filename, array_data = L05_3d_array, metadata = metadata)



# here's some cruft that we keep here in case it's useful one day!
#time0 = time1
#time1 = time0 + avg_interval

#while (time1 <= time_final):
#
#    screeninterval = df.loc[df['datetime'] < time1]
#    screeninterval = screeninterval.loc[(time0 - analysis_margin) < screeninterval['datetime']]
#
#    avginterval = df.loc[df['datetime'] < time1]
#    avginterval = avginterval.loc[time0 < avginterval['datetime']]
#
#    screen = screeninterval['euclidian_dist'].describe()
#    L05line = avginterval.describe()
#
#    interval_midpoint = time0 + avg_interval/2
#    L05line['valid_time'] = interval_midpoint
#    trackingflags = 0
#    if screen['max'] > trackingmax:    # we only apply the "screen" time interval for tracking
#        trackingflags = trackingflags | TRACKING_ERROR_OOB
#    if L05line['camera_sun_brightness']['min'] == 0:   # the camera didnt' give data for the whole analysis interval
#        trackingflags = trackingflags | NO_CAMERA_DATA
#    if L05line['camera_sun_brightness']['mean'] < brightmin or L05line['camera_sun_brightness']['mean'] > brightmax:
#        trackingflags = trackingflags | CAMERA_BRIGHTNESS_OOB
#
#    L05line['trackingflags'] = trackingflags    
#    
#
#    interval_stats = interval.describe()
#    interval_midpoint = interval['datetime'].min() + avg_interval/2

    # append the data from this interval to the 3-d data array
    # 
#    time0 = time1
#    time1 = time0 + avg_interval

    
# old code that might still be useful for cut'n'paste:
# create some lists for the raw data, which will be made into a numpy array for each time step, then all the statistics collated together into an xarray  
#datetimes = []
#motor_0_enc = []
#motor_1_enc = []
#motor_2_enc = []
#quaternion_w = []
#quaternion_x = []
#quaternion_y = []
#quaternion_z = []
#sun_ephem_az = []
#sun_ephem_elev = []
#camera_sun_x = []
#camera_sun_y = []
#camera_sun_brightness = []
#angular_vx = []
#angular_vy = []
#angular_vz = []
#linear_ax = []
#linear_ay = []
#linear_az = []
#imu_temp = []
#imu_press = []
#imu_lat = []
#imu_lon = []
#ch1_1x = []
#ch2_1x = []
#ch3_1x = []
#ch4_1x = []
#ch5_1x = []
#hot_block1_temp = []
#euclidian_dist = []
