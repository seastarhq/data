#!/usr/bin/env python3

import os
import numpy as np

SEASTAR_TIMEZONE = os.environ['SEASTAR_TIMEZONE']

IMU_PRESS_MIN = float(os.environ['IMU_PRESS_MIN'])  # in hPa
IMU_PRESS_MAX = float(os.environ['IMU_PRESS_MAX'])
AOD_PRESSURE_FALLBACK_HPA = float(os.environ['AOD_PRESSURE_FALLBACK_HPA'])

AOD_TRACKING_LEVEL = int(os.environ['AOD_TRACKING_LEVEL'])  # tracking error level that counts as bad tracking

OZONE_COLUMN_DU = float(os.environ['OZONE_COLUMN_DU'])
NO2_COLUMN_DU = float(os.environ['NO2_COLUMN_DU'])
AIRMASS_OZONE_HEIGHT_KM = float(os.environ['AIRMASS_OZONE_HEIGHT_KM'])
AIRMASS_NO2_HEIGHT_KM = float(os.environ['AIRMASS_NO2_HEIGHT_KM'])
ANGSTROM_WAVELENGTHS = [float(nm) for nm in os.environ['ANGSTROM_WAVELENGTHS'].split()]

# the V0 calibration (calibration.sh, written by calibration_vs_ref/scripts/write_v0_params.py), for the channels
# that have one: |V|corr = |V| / (1 + A*dT + B*dT^2), dT = T - V0_TREF, and tau*airmass = ln((V0 - a) / (|V|corr - a)).
# V0_MODE picks the calibration: intercept (the intercept line's V0 and a) or origin (the line through the origin's
# V0, with a = 0). V0[mode][ch] and V0_A[mode][ch]
V0_MODE = os.environ['V0_MODE']
V0_MODES = ('intercept', 'origin')
V0_TREF = float(os.environ['V0_TREF'])
V0_CHANNELS = [int(ch) for ch in os.environ['V0_CHANNELS'].split()]
V0 = {'intercept': {ch: float(os.environ[f'V0_INTERCEPT_CH{ch}']) for ch in V0_CHANNELS},
      'origin': {ch: float(os.environ[f'V0_ORIGIN_CH{ch}']) for ch in V0_CHANNELS}}
V0_A = {'intercept': {ch: float(os.environ[f'V0_INTERCEPT_A_CH{ch}']) for ch in V0_CHANNELS},
        'origin': {ch: 0.0 for ch in V0_CHANNELS}}
V0_TEMP_CORR = {ch: (float(os.environ[f'V0_TEMP_CORR_A_CH{ch}']), float(os.environ[f'V0_TEMP_CORR_B_CH{ch}']))
                for ch in V0_CHANNELS}

# absorption cross-sections, cm^2/molecule, for the channels with a V0
OZONE_XSEC = {ch: float(os.environ[f'OZONE_XSEC_CH{ch}']) for ch in V0_CHANNELS}
NO2_XSEC = {ch: float(os.environ[f'NO2_XSEC_CH{ch}']) for ch in V0_CHANNELS}
