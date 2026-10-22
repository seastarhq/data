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

##### Level 0.5 data structures
# make an array of NaN's that we will update with the raw data timestep-by-timestep
# wouldn't it be nice to use a 3-d pandas structure? lucky - numpy supports heterogeneous data types.
# The magic number 60 is a guess at the max number data points there are going to be per second. E.g.if SeaSTAR is logging at 50Hz
# then we should have plenty of space in the array

L05_dtype_dict = { "datetime": 'datetime64[ms]',   # the [ms] is important for conversions from pandas to numpy 
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
                  "ch6_1x": 'f8',
                  "ch7_1x": 'f8',
                  "ch8_1x": 'f8',
                  "ch9_1x": 'f8',
                  "ch10_1x": 'f8',
                  "hot_block1_temp": 'f8',
                  "ch1_temp": 'f8',
                  "ch2_temp": 'f8',
                  "ch3_temp": 'f8',
                  "ch4_temp": 'f8',
                  "ch5_temp": 'f8',
                  "ch6_temp": 'f8',
                  "ch7_temp": 'f8',
                  "ch8_temp": 'f8',
                  "ch9_temp": 'f8',
                  "ch10_temp": 'f8',
                  "euclidian_dist": 'f8',
                  "flags": 'i4'}
L05_dtype = np.dtype(list(zip(L05_dtype_dict.keys(),L05_dtype_dict.values())))

def fill_L05_blanks(L05array):
# sets every field of an L05_dtype array (of any shape) to NaN, NaT, or 0 for the flags
    for key in L05_dtype_dict.keys():
        if key == 'datetime':
            L05array[key] = np.datetime64('NaT')
        elif key == 'flags':
            L05array[key] = 0
        else:
            L05array[key] = np.nan

def create_L05_3darray(timesteps,maxdatapoints=60):
# we add the last column for the flags - there will be one set of flags for each timestep, so one more column should be plenty
    L05array = np.empty( (timesteps, maxdatapoints),dtype=L05_dtype)   

# fill up the array with nans, or 0's for the flags
# we can't do this automatically using np.full in the line above, since the datatype contains floats
# and integers, so we fill one field at a time across the whole array:
    fill_L05_blanks(L05array)

    return L05array
    
def create_L05_2darray(maxdatapoints=60):
#maxdatapoints needs to be the same as the 3-d L05array
    L05line = np.empty((maxdatapoints),dtype=L05_dtype)
     
    fill_L05_blanks(L05line)

    return L05line

#### L0.6 data structures
L06_sun_dtype_dict = { "datetime": 'datetime64[ms]',   # the [ms] is important for conversions from pandas to numpy 
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
                  "ch6_1x": 'f8',
                  "ch7_1x": 'f8',
                  "ch8_1x": 'f8',
                  "ch9_1x": 'f8',
                  "ch10_1x": 'f8',
                  # modelled dark voltages (dark_subtraction.py) and ch<n>_1x with them subtracted
                  "ch1_dark_lin": 'f8',
                  "ch2_dark_lin": 'f8',
                  "ch3_dark_lin": 'f8',
                  "ch4_dark_lin": 'f8',
                  "ch5_dark_lin": 'f8',
                  "ch6_dark_lin": 'f8',
                  "ch7_dark_lin": 'f8',
                  "ch8_dark_lin": 'f8',
                  "ch9_dark_lin": 'f8',
                  "ch10_dark_lin": 'f8',
                  "ch1_dark_quad": 'f8',
                  "ch2_dark_quad": 'f8',
                  "ch3_dark_quad": 'f8',
                  "ch4_dark_quad": 'f8',
                  "ch5_dark_quad": 'f8',
                  "ch6_dark_quad": 'f8',
                  "ch7_dark_quad": 'f8',
                  "ch8_dark_quad": 'f8',
                  "ch9_dark_quad": 'f8',
                  "ch10_dark_quad": 'f8',
                  "ch1_1x_darksub_lin": 'f8',
                  "ch2_1x_darksub_lin": 'f8',
                  "ch3_1x_darksub_lin": 'f8',
                  "ch4_1x_darksub_lin": 'f8',
                  "ch5_1x_darksub_lin": 'f8',
                  "ch6_1x_darksub_lin": 'f8',
                  "ch7_1x_darksub_lin": 'f8',
                  "ch8_1x_darksub_lin": 'f8',
                  "ch9_1x_darksub_lin": 'f8',
                  "ch10_1x_darksub_lin": 'f8',
                  "ch1_1x_darksub_quad": 'f8',
                  "ch2_1x_darksub_quad": 'f8',
                  "ch3_1x_darksub_quad": 'f8',
                  "ch4_1x_darksub_quad": 'f8',
                  "ch5_1x_darksub_quad": 'f8',
                  "ch6_1x_darksub_quad": 'f8',
                  "ch7_1x_darksub_quad": 'f8',
                  "ch8_1x_darksub_quad": 'f8',
                  "ch9_1x_darksub_quad": 'f8',
                  "ch10_1x_darksub_quad": 'f8',
                  # the dark-subtracted voltages, temperature corrected (temp_correction.py)
                  "ch1_1x_darksub_lin_tc": 'f8',
                  "ch2_1x_darksub_lin_tc": 'f8',
                  "ch3_1x_darksub_lin_tc": 'f8',
                  "ch4_1x_darksub_lin_tc": 'f8',
                  "ch5_1x_darksub_lin_tc": 'f8',
                  "ch6_1x_darksub_lin_tc": 'f8',
                  "ch7_1x_darksub_lin_tc": 'f8',
                  "ch8_1x_darksub_lin_tc": 'f8',
                  "ch9_1x_darksub_lin_tc": 'f8',
                  "ch10_1x_darksub_lin_tc": 'f8',
                  "ch1_1x_darksub_quad_tc": 'f8',
                  "ch2_1x_darksub_quad_tc": 'f8',
                  "ch3_1x_darksub_quad_tc": 'f8',
                  "ch4_1x_darksub_quad_tc": 'f8',
                  "ch5_1x_darksub_quad_tc": 'f8',
                  "ch6_1x_darksub_quad_tc": 'f8',
                  "ch7_1x_darksub_quad_tc": 'f8',
                  "ch8_1x_darksub_quad_tc": 'f8',
                  "ch9_1x_darksub_quad_tc": 'f8',
                  "ch10_1x_darksub_quad_tc": 'f8',
                  "tvar_ch1": 'f8',
                  "tvar_ch2": 'f8',
                  "tvar_ch3": 'f8',
                  "tvar_ch4": 'f8',
                  "tvar_ch5": 'f8',
                  "tvar_ch6": 'f8',
                  "tvar_ch7": 'f8',
                  "tvar_ch8": 'f8',
                  "tvar_ch9": 'f8',
                  "tvar_ch10": 'f8',
                  "hot_block1_temp": 'f8',
                  "ch1_temp": 'f8',
                  "ch2_temp": 'f8',
                  "ch3_temp": 'f8',
                  "ch4_temp": 'f8',
                  "ch5_temp": 'f8',
                  "ch6_temp": 'f8',
                  "ch7_temp": 'f8',
                  "ch8_temp": 'f8',
                  "ch9_temp": 'f8',
                  "ch10_temp": 'f8',
                  "euclidian_dist": 'f8',
                  "tracking_flags": 'i4',
                  "robot_flags": 'i4',
                  "housekeeping_flags": 'i4',
                  "radiometer_1x_flags": 'i4',
                  "radiometer_100x_flags": 'i4',
                  "radiometer_10kx_flags": 'i4',
                  "cloud_flags": 'i4',
                  "user_flags": 'i4'}
                    
L06_sun_dtype = np.dtype(list(zip(L06_sun_dtype_dict.keys(),L06_sun_dtype_dict.values())))


def create_L06_sun_2darray(timesteps):

    L06array = np.empty(timesteps, dtype=L06_sun_dtype)

    for i in range(timesteps):
        for key in L06_sun_dtype_dict.keys():
            if key == 'datetime':
                L06array[i][key] = np.datetime64('NaT')
            elif key == 'tracking_flags':
                L06array[i][key] = 0
            elif key == 'robot_flags':
                L06array[i][key] = 0
            elif key == 'housekeeping_flags':
                L06array[i][key] = 0
            elif key == 'radiometer_1x_flags':
                L06array[i][key] = 0
            elif key == 'radiometer_100x_flags':
                L06array[i][key] = 0
            elif key == 'radiometer_10kx_flags':
                L06array[i][key] = 0
            elif key == 'cloud_flags':
                L06array[i][key] = 0
            elif key == 'user_flags':
                L06array[i][key] = 0
            else:
                L06array[i][key] = np.nan

    return L06array


#### L1.0 data structures
L10_sun_dtype_dict = { "datetime": 'datetime64[ms]',   # the [ms] is important for conversions from pandas to numpy 
              # "motor_0_enc": 'f8',
              #   "motor_1_enc": 'f8',
              #    "motor_2_enc": 'f8',
              #    "quaternion_w": 'f8',
              #    "quaternion_x": 'f8',
              #    "quaternion_y": 'f8',
              #    "quaternion_z": 'f8',
                  "sun_ephem_az": 'f8',
                  "sun_ephem_elev": 'f8',
                  "camera_sun_x": 'f8',
                  "camera_sun_y": 'f8',
                  "camera_sun_brightness": 'f8',
                  "camera_target_x": 'f8',
                  "camera_target_y": 'f8',
              #    "angular_vx": 'f8',
              #    "angular_vy": 'f8',
              #    "angular_vz": 'f8',
              #    "linear_ax": 'f8',
              #    "linear_ay": 'f8',
              #    "linear_az": 'f8',
                  "imu_temp": 'f8',
                  "imu_press": 'f8',
                  "imu_lat": 'f8',
                  "imu_lon": 'f8',
                  "380nm_aod": 'f8',
                  "440nm_aod": 'f8',
                  "500nm_aod": 'f8',
                  "550nm_aod": 'f8',
                  "675nm_aod": 'f8',
                  "hot_block1_temp": 'f8',
                  "euclidian_dist": 'f8',
                  "tracking_flags": 'i4',
                  "robot_flags": 'i4',
                  "housekeeping_flags": 'i4',
                  "radiometer_1x_flags": 'i4',
                  "radiometer_100x_flags": 'i4',
                  "radiometer_10kx_flags": 'i4',
                  "cloud_flags": 'i4',
                  "ozone_column_du": 'f8',
                  "no2_column_du": 'f8',
                  "optical_airmass": 'f8'}
                 # "dTdt_raw": 'f8',
                 # "dTdt_smooth": 'f8',
                 # "d2Tdt2": "f8",
                 # "d2Tdt2_smooth": "f8"}
                    
L10_sun_dtype = np.dtype(list(zip(L10_sun_dtype_dict.keys(),L10_sun_dtype_dict.values())))


def create_L10_sun_2darray(timesteps):

    L10array = np.empty(timesteps, dtype=L10_sun_dtype)

    for i in range(timesteps):
        for key in L10_sun_dtype_dict.keys():
            if key == 'datetime':
                L10array[i][key] = np.datetime64('NaT')
            elif key == 'tracking_flags':
                L10array[i][key] = 0
            elif key == 'robot_flags':
                L10array[i][key] = 0
            elif key == 'housekeeping_flags':
                L10array[i][key] = 0
            elif key == 'radiometer_1x_flags':
                L10array[i][key] = 0
            elif key == 'radiometer_100x_flags':
                L10array[i][key] = 0
            elif key == 'radiometer_10kx_flags':
                L10array[i][key] = 0
            elif key == 'cloud_flags':
                L10array[i][key] = 0
            else:
                L10array[i][key] = np.nan

    return L10array






