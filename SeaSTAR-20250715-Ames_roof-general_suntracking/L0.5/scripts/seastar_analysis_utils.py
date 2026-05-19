#!/usr/bin/env python3

from datetime import datetime,timedelta
import os
import math

def round_to_the_last_x_min(timestamp,x):
    rounded = timestamp - (timestamp - datetime.min) % timedelta(minutes=x)
    return rounded

def eucl_dist(row):
    return math.sqrt((row['camera_target_x'] - row['camera_sun_x'])**2 + (row['camera_target_y'] - row['camera_sun_y'])**2)


