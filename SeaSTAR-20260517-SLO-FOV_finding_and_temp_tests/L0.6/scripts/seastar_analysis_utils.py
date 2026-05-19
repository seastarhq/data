#!/usr/bin/env python3

from datetime import datetime,timedelta
import os
import math
#from astropy.coordinates import get_sun
#from astropy.time import Time

def round_to_the_last_x_min(timestamp,x):
    rounded = timestamp - (timestamp - datetime.min) % timedelta(minutes=x)
    return rounded

def eucl_dist(row):
    return math.sqrt((row['camera_target_x'] - row['camera_sun_x'])**2 + (row['camera_target_y'] - row['camera_sun_y'])**2)

def calc_tvar(triplet):
    var01 = abs(triplet[1] - triplet[0]/triplet[1])
    var12 = abs(triplet[1] - triplet[2]/triplet[1])
    var02 = abs(triplet[0] - triplet[2]/triplet[0])
    return max(var01,var12,var02)


def getsundistance(time, approx=False):
    t = Time(time)
    sun = get_sun(t)
    return sun.distance.valuea

def getairmass(solarelevation, pressure):
    theta = np.deg2rad(90.0 - elevation)
    airmass = (1 / (np.cos(theta) + (0.50572 * (96.07995 - np.rad2deg(theta))**(-1.6364))))
    pressurecorrection = (pressure / 101325.0)  
    return airmass * pressurecorrection



