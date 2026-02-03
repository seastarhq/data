#!/usr/bin/env python3

import sys,os
import numpy as np

class Error(Exception): pass

def _find(pathname, dirnames, matchFunc=os.path.isfile):
    """looks for files in a list of directories"""
    for dirname in dirnames:
        candidate = os.path.join(dirname, pathname)
        #sys.stderr.write(candidate)
        print(candidate)
        if matchFunc(candidate):
            return candidate
    raise Error("Can't find file %s" % candidate)

def findFile(pathname,dirnames):
    return _find(pathname,dirnames)

#def findDir(path):
#    return _find(path, matchFunc=os.path.isdir)


# make an array of NaN's that we will update with the raw data timestep-by-timestep
# wouldn't it be nice to use a 3-d pandas structure? lucky - numpy supports heterogeneous data types.
# The magic number 60 is a guess at the max number data points there are going to be per second. E.g.if SeaSTAR is logging at 50Hz
# then we should have plenty of space in the array

dtype_dict = { "datetime": 'datetime64[ms]',   # the [ms] is important for conversions from pandas to numpy 
               "motor_0_enc": 'f8',
                 "motor_1_enc": 'f8',
                  "motor_2_enc": 'f8',
                  "quaternion_w": 'f8',
                  "quaternion_x": 'f8',
                  "quaternion_y": 'f8',
                  "quaternion_z": 'f8',
                  "sun_ephem_az": 'f8',
                  "sun_ephem_elev": 'f8',
                  "camera_sun_x": 'f8',
                  "camera_sun_y": 'f8',
                  "camera_sun_brightness": 'f8',
                  "camera_target_x": 'f8',
                  "camera_target_y": 'f8',
                  "angular_vx": 'f8',
                  "angular_vy": 'f8',
                  "angular_vz": 'f8',
                  "linear_ax": 'f8',
                  "linear_ay": 'f8',
                  "linear_az": 'f8',
                  "imu_temp": 'f8',
                  "imu_press": 'f8',
                  "imu_lat": 'f8',
                  "imu_lon": 'f8',
                  "ch1_1x": 'f8',
                  "ch2_1x": 'f8',
                  "ch3_1x": 'f8',
                  "ch4_1x": 'f8',
                  "ch5_1x": 'f8',
                  "hot_block1_temp": 'f8',
                  "euclidian_dist": 'f8',
                  "flags": 'i4'}
L04_dtype = np.dtype(list(zip(dtype_dict.keys(),dtype_dict.values())))

def create_L04_3darray(timesteps,maxdatapoints=60):
# we add the last column for the flags - there will be one set of flags for each timestep, so one more column should be plenty
    L04array = np.empty( (timesteps, maxdatapoints),dtype=L04_dtype)   

# fill up the array with nans, or 0's for the flags
# we can't do this automatically using np.full in the line above, since the datatype contains floats
# and integers:
    for i in range(timesteps):
        for j in range(maxdatapoints):
            for key in dtype_dict.keys():
                if key != "flags" and key != 'datetime':
                    L04array[i][j][key] = np.nan
                elif key == 'datetime':
                    L04array[i][j][key] = np.datetime64('NaT')
                elif key == 'flags':
                    L04array[i][j][key] = 0

    return L04array
    
def create_L04_2darray(maxdatapoints=60):
#maxdatapoints needs to be the same as the 3-d L04array
    L04line = np.empty((maxdatapoints),dtype=L04_dtype)
     
    for j in range(maxdatapoints):
        for key in dtype_dict.keys():
            if key != "flags" and key != 'datetime':
                L04line[j][key] = np.nan
            elif key == 'datetime':
                L04line[j][key] = np.datetime64('NaT')
            elif key == 'flags':
                L04line[j][key] = 0

    return L04line







