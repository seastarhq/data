#!/usr/bin/env python3

# solar position, airmasses and the gas optical depths for the L1.0 aerosol optical depth

import numpy as np

DU = 2.687e16  # molecules/cm^2 in one Dobson unit
EARTH_RADIUS_KM = 6371.0


def solar_position(times, lat, lon):
    """Geometric solar elevation (degrees) and earth-sun distance (AU), from the NOAA solar calculator equations
    (Meeus). times are datetime64 UTC, lat and lon in degrees (east positive). Good to about 0.01 degrees."""
    jd = times.astype('datetime64[ms]').astype('f8') / 86400000.0 + 2440587.5
    jc = (jd - 2451545.0) / 36525.0
    mean_long = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    mean_anom = np.radians(357.52911 + jc * (35999.05029 - 0.0001537 * jc))
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    centre = (np.sin(mean_anom) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
              + np.sin(2 * mean_anom) * (0.019993 - 0.000101 * jc) + np.sin(3 * mean_anom) * 0.000289)
    true_anom = mean_anom + np.radians(centre)
    distance = 1.000001018 * (1 - ecc ** 2) / (1 + ecc * np.cos(true_anom))
    omega = np.radians(125.04 - 1934.136 * jc)
    app_long = np.radians(mean_long + centre - 0.00569 - 0.00478 * np.sin(omega))
    obliq = np.radians(23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
                       + 0.00256 * np.cos(omega))
    decl = np.arcsin(np.sin(obliq) * np.sin(app_long))
    y = np.tan(obliq / 2) ** 2
    L0 = np.radians(mean_long)
    eq_time = 4 * np.degrees(y * np.sin(2 * L0) - 2 * ecc * np.sin(mean_anom)
                             + 4 * ecc * y * np.sin(mean_anom) * np.cos(2 * L0)
                             - 0.5 * y ** 2 * np.sin(4 * L0) - 1.25 * ecc ** 2 * np.sin(2 * mean_anom))  # minutes
    minutes = (jd + 0.5) % 1 * 1440
    hour_angle = np.radians(((minutes + eq_time + 4 * lon) % 1440) / 4 - 180)
    cos_zen = (np.sin(np.radians(lat)) * np.sin(decl)
               + np.cos(np.radians(lat)) * np.cos(decl) * np.cos(hour_angle))
    return 90.0 - np.degrees(np.arccos(np.clip(cos_zen, -1, 1))), distance


def airmass_rayleigh(zenith):
    """Kasten & Young (1989). zenith in degrees."""
    return 1.0 / (np.cos(np.radians(zenith)) + 0.50572 * (96.07995 - zenith) ** -1.6364)


def airmass_aerosol(zenith):
    """Kasten (1966). zenith in degrees."""
    return 1.0 / (np.cos(np.radians(zenith)) + 0.15 * (93.885 - zenith) ** -1.253)


def airmass_layer(zenith, height_km):
    """Komhyr et al. (1989): the slant path through a thin absorbing layer at height_km, for an observer at sea level."""
    r = EARTH_RADIUS_KM + height_km
    return r / np.sqrt(r ** 2 - (EARTH_RADIUS_KM * np.sin(np.radians(zenith))) ** 2)


def tau_rayleigh(wavelength_nm, pressure_hpa):
    """Rayleigh optical depth, Bodhaine et al. (1999) eq. 30, scaled by the surface pressure."""
    lam = wavelength_nm / 1000.0
    tau = 0.0021520 * ((1.0455996 - 341.29061 * lam ** -2 - 0.90230850 * lam ** 2)
                       / (1 + 0.0027059889 * lam ** -2 - 85.968563 * lam ** 2))
    return tau * pressure_hpa / 1013.25


def tau_gas(column_du, xsec):
    """Absorption optical depth of a gas column (DU) with cross-section xsec (cm^2/molecule)."""
    return column_du * DU * xsec
