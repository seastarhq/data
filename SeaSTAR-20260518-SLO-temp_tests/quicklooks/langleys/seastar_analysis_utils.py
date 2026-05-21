#!/usr/bin/env python3

from datetime import datetime,timedelta
import os
import math
import numpy as np
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

def airmass_star(solarelevation, pressure): # from Star's Jupyter notes. is this Kasten & Young?
    theta = np.deg2rad(90.0 - solarelevation)
    airmass = (1 / (np.cos(theta) + (0.50572 * (96.07995 - np.rad2deg(theta))**(-1.6364))))
    pressurecorrection = (pressure / 101325.0)  
    return airmass * pressurecorrection

def optical_airmass(sza):   # taken from Balmes et al (HSR1 paper), citing Kasten & Young
                            # same formula is given by Porter 2001
    return 1.0 / ( math.cos(sza) + 0.50572 * (96.07995 - sza)**-1.6364 )

def ozone_airmass(sza):
    """From Porter et al 2001"""
    oa = optical_airmass(sza)
    return oa - 0.011*oa + 0.027*oa**2 - 0.0161*oa**3

def tau_rayleigh_ichoku(height, wavelength):   # from ichoku 2002
    """ height in meters, wavelength in nanometers"""
    wavelength = wavelength/1000.0 # convert to microns to match ichoku 2002
    R2 = 1e-8 * ((8342.13 + 2406030 / (130-wavelength**-2)) + (15997 / (38.9 - wavelength**-2)))
    R4 = 28773.6 * (R2 * (2.0 + R2) * wavelength**-2)**2
    return R4*math.exp(-height/29.3/273)

def tau_rayleigh_hansen(pressure, wavelength): # from Balmes et al, citing Hansen & Travis 1974
    """ pressure in mbar, wavelegnth in nanometers"""
    wavelength = wavelength / 1000.0   # convert to microns to match Balmes
    return (pressure/1013.25) * 0.008579 * wavelength**-4 * ( 1.0 + 0.0133*wavelength**-2 + 0.00013*wavelength**-4)
    
