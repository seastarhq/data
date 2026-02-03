#!/usr/bin/env python3

# flag locations in the L05 arrays:
# L05line['flags'][0] is tracking flags
# L05line['flags'][1] is robot flags
# L05line['flags'][2] is housekeeping flags
#                   [3] is 1x radiometer flags
#                   [4] is 100x radiometer flags
#                   [5] is 10kx radiometer flags

# OOB means Out Of Bounds

# tracking_error flags
NO_CAMERA_DATA = 1
TRACKING_ERROR_OOB = 2
CAMERA_BRIGHTNESS_HIGH = 4
CAMERA_BRIGHTNESS_LOW = 8

# robot_error flags
ENCODER_DROPOUT = 1
MOTOR_0_INOP = 2
MOTOR_1_INOP = 4
MOTOR_2_INOP = 8

# housekeeping_error flags
HOT_BLOCK_1_HOT = 1
HOT_BLOCK_1_COLD = 2
HOT_BLOCK_2_HOT = 4
HOT_BLOCK_2_COLD = 8
COLD_BLOCK_HOT = 16
COLD_BLOCK_COLD = 32
IMU_TEMP_OOB = 64
IMU_PRES_OOB = 128
WATER_TEMP_OOB = 256
COOLINGPLATE_TEMP_OOB = 512
POLARIZER_PLATE_TEMP_OOB = 1024
AD_TEMP_OOB = 2048
HAMB_TEMP_OOB  = 4096
HUMIDITY_HIGH = 8192

# radiometer_1x_error flags
CH1_1_ERROR = 1
CH2_1_ERROR = 2
CH3_1_ERROR = 4
CH4_1_ERROR = 8
CH5_1_ERROR = 16
CH6_1_ERROR = 32
CH7_1_ERROR = 64
CH8_1_ERROR = 128
CH9_1_ERROR = 256
CH10_1_ERROR = 512
CH11_1_ERROR = 1024
CH12_1_ERROR = 2048
CH13_1_ERROR = 4096
CH14_1_ERROR = 8192

# radiometer_100x_error flags
CH1_100_ERROR = 1
CH2_100_ERROR = 2
CH3_100_ERROR = 4
CH4_100_ERROR = 8
CH5_100_ERROR = 16
CH6_100_ERROR = 32
CH7_100_ERROR = 64
CH8_100_ERROR = 128
CH9_100_ERROR = 256
CH10_100_ERROR = 512
CH11_100_ERROR = 1024
CH12_100_ERROR = 2048
CH13_100_ERROR = 4096
CH14_100_ERROR = 8192

# radiometer_10kx_error flags
CH1_10k_ERROR = 1
CH2_10k_ERROR = 2
CH3_10k_ERROR = 4
CH4_10k_ERROR = 8
CH5_10k_ERROR = 16
CH6_10k_ERROR = 32
CH7_10k_ERROR = 64
CH8_10k_ERROR = 128
CH9_10k_ERROR = 256
CH10_10k_ERROR = 512
CH11_10k_ERROR = 1024
CH12_10k_ERROR = 2048
CH13_10k_ERROR = 4096
CH14_100_ERROR = 8192

def calculate_tracking_flags(screeninterval,avginterval,paramsdict): #
    # params is a dict with {trackingmax,brightmin,brightmax}:
    euclidian_dist_stats = screeninterval['euclidian_dist'].describe()
    camera_sun_brightness_stats = avginterval['camera_sun_brightness'].describe()
    trackingflags = 0 
    if euclidian_dist_stats['max'] > paramsdict['trackingmax']:    
        # we only apply the "screeninterval" time-interval for tracking
        trackingflags = trackingflags | TRACKING_ERROR_OOB
    if camera_sun_brightness_stats['min'] == 0:   
        # i.e. the camera didnt' give data for the whole analysis interval
        trackingflags = trackingflags | NO_CAMERA_DATA
    if camera_sun_brightness_stats['mean'] < paramsdict['brightmin'] or camera_sun_brightness_stats['mean'] > paramsdict['brightmax']:
        trackingflags = trackingflags | CAMERA_BRIGHTNESS_OOB
    return trackingflags

def calculate_robot_flags(avginterval):
    m0_stats = avginterval['motor_0_enc'].describe()
    m1_stats = avginterval['motor_1_enc'].describe()
    m2_stats = avginterval['motor_2_enc'].describe()
    robotflags = 0
    # this should catch any encoder dropouts:
    # if none of these are true, then the robot flags will stay at the
    # default value of zero
    if (m0_stats['mean'] - m0_stats['min']) > m0_stats['std']:
        robotflags = robotflags | ENCODER_DROPOUT
    if (m1_stats['mean'] - m1_stats['min']) > m1_stats['std']:
        robotflags = robotflags | ENCODER_DROPOUT
    if (m2_stats['mean'] - m2_stats['min']) > m2_stats['std']:
        robotflags = robotflags | ENCODER_DROPOUT
    return robotflags

def calculate_housekeeping_flags(avginterval,paramsdict):
    # paramsdict is a dict with hot block min and max (for now)
    # we need to handle more cases here, so we have to initialize:
    housekeepingflags = 0
    hotblock1stats = avginterval['hot_block1_temp'].describe()
    if hotblock1stats['mean'] > paramsdict['hotblock1max']:
       housekeepingflags = housekeepingflags | HOT_BLOCK_1_HOT  
    if hotblock1stats['mean'] < paramsdict['hotblock1min']:
       housekeepingflags = housekeepingflags | HOT_BLOCK_1_COLD
    return housekeepingflags






