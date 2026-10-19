#!/usr/bin/env python3

from datetime import datetime,timedelta
import os
import math

def round_to_the_last_x_min(timestamp,x):
    rounded = timestamp - (timestamp - datetime.min) % timedelta(minutes=x)
    return rounded

def eucl_dist(row):
    return math.sqrt((row['camera_target_x'] - row['camera_sun_x'])**2 + (row['camera_target_y'] - row['camera_sun_y'])**2)

def interpolate_temps(row):
    block1_inboard=row['block1_temp_inboard']
    block1_outboard=row['block1_temp_outboard']
    block2_inboard=row['block2_temp_inboard']
    block2_outboard=row['block2_temp_outboard']

    ch1_temp = block1_inboard
    ch2_temp = block1_inboard + (2-1) * ((block1_outboard - block1_inboard) / (5-1))  # linear interpolation from ch1/inboard to ch5/outboard
    ch3_temp = block1_inboard + (3-1) * ((block1_outboard - block1_inboard) / (5-1))
    ch4_temp = block1_inboard + (4-1) * ((block1_outboard - block1_inboard) / (5-1))
    ch5_temp = block1_outboard 

    ch6_temp = block2_inboard
    ch7_temp = block2_inboard + (2-1) * ((block2_outboard - block2_inboard) / (5-1))  # linear interpolation from ch6/inboard to ch10/outboard
    ch8_temp = block2_inboard + (3-1) * ((block2_outboard - block2_inboard) / (5-1))
    ch9_temp = block2_inboard + (4-1) * ((block2_outboard - block2_inboard) / (5-1))
    ch10_temp = block2_outboard 

    return([ch1_temp, ch2_temp, ch3_temp, ch4_temp, ch5_temp, ch6_temp, ch7_temp, ch8_temp, ch9_temp, ch10_temp])
