#!/usr/bin/env python3

import sys, os
import numpy as np
import argparse
import pytz
from datetime import datetime

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *
from seastar_atmosphere import *

# where to find things including
# ROOT_DIR SCRIPTS_DIR L06_DATA_DIR L10_DATA_DIR
from seastar_filepaths import *

## analysis parameters:
# including
# IMU_PRESS_MIN IMU_PRESS_MAX AOD_PRESSURE_FALLBACK_HPA AOD_TRACKING_LEVEL OZONE_COLUMN_DU NO2_COLUMN_DU
# V0_MODE V0_CHANNELS V0 V0_A V0_TEMP_CORR V0_TREF OZONE_XSEC NO2_XSEC
from seastar_analysis_params import *

# aerosol optical depth from an L06 file, for every timestep and every channel with a V0 (calibration.sh).
# the dark-subtracted voltage is temperature corrected the way its V0 was transferred from AERONET,
#     |V|corr = |ch<n>_1x_darksub_quad| / (1 + A*dT + B*dT^2),   dT = ch<n>_temp - V0_TREF
# and, with the intercept-line calibration |V| = a + b*V_aeronet (so only |V| - a follows the sun),
#     ln((V0 - a) / (d^2 * (|V|corr - a))) = m_R*tau_R + m_a*AOD + m_O3*tau_O3 + m_NO2*tau_NO2
# or, with V0_MODE=origin, the line through the origin |V| = b*V_aeronet, its V0 and a = 0.
# with d the earth-sun distance in AU, tau_R from the IMU pressure, and an airmass for each constituent.
# the solar position is computed from the time and the GPS position, which is interpolated across dropouts.
# the Angstrom exponent is fitted over ANGSTROM_WAVELENGTHS. aod_flags (seastar_error_flags.py) marks the
# timesteps to distrust; nothing is dropped. the L06 fields are carried over, and the L10 is written beside it

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-o', '--outputfile')
parser.add_argument('--v0-mode', choices=V0_MODES, help='the V0 calibration to use, instead of V0_MODE')
args = parser.parse_args()

if args.v0_mode is not None:
    V0_MODE = args.v0_mode
if V0_MODE not in V0_MODES:
    sys.exit(f"V0_MODE must be one of {', '.join(V0_MODES)}, not {V0_MODE!r}")
V0, V0_A = V0[V0_MODE], V0_A[V0_MODE]

# findFile needs a list passed to it, so we make one with length 1
L06_data_dir = [L06_DATA_DIR,]
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

if args.outputfile is None:
    L10_npyfile = os.path.join(L10_DATA_DIR, os.path.splitext(os.path.basename(L06_npyfile))[0] + '.L10')
else:
    L10_npyfile = os.path.join(L10_DATA_DIR, args.outputfile)

wavelengths = {ch: int(metadata['CHANNEL_NM'][ch - 1]) for ch in V0_CHANNELS}

new_fields = [('lat', 'f8'), ('lon', 'f8'), ('pressure_hpa', 'f8'), ('sun_elev', 'f8'), ('sun_zenith', 'f8'),
              ('earth_sun_distance_au', 'f8'), ('airmass_rayleigh', 'f8'), ('airmass_aerosol', 'f8'),
              ('airmass_ozone', 'f8'), ('airmass_no2', 'f8')]
for ch in V0_CHANNELS:
    nm = wavelengths[ch]
    new_fields += [(f'ch{ch}_1x_darksub_quad_v0tc', 'f8'), (f'tau_rayleigh_{nm}nm', 'f8'),
                   (f'tau_ozone_{nm}nm', 'f8'), (f'tau_no2_{nm}nm', 'f8'), (f'aod_{nm}nm', 'f8')]
new_fields += [('angstrom', 'f8'), ('aod_flags', 'i4')]
L10_data = np.zeros(len(L06_data), dtype=L06_data.dtype.descr + new_fields)
for name in L06_data.dtype.names:
    L10_data[name] = L06_data[name]

# GPS dropouts read (0, 0): fill them by interpolating in time from the good positions
good_position = (L06_data['imu_lat'] != 0) & (L06_data['imu_lon'] != 0)
if not good_position.any():
    sys.exit(f"no GPS positions in {L06_npyfile}")
seconds = (L06_data['datetime'] - L06_data['datetime'][0]).astype('f8') / 1000.0
L10_data['lat'] = np.interp(seconds, seconds[good_position], L06_data['imu_lat'][good_position])
L10_data['lon'] = np.interp(seconds, seconds[good_position], L06_data['imu_lon'][good_position])

# the IMU records pascals
pressure = L06_data['imu_press'] / 100.0
good_pressure = (pressure >= IMU_PRESS_MIN) & (pressure <= IMU_PRESS_MAX)
L10_data['pressure_hpa'] = np.where(good_pressure, pressure, AOD_PRESSURE_FALLBACK_HPA)

elev, distance = solar_position(L06_data['datetime'], L10_data['lat'], L10_data['lon'])
zenith = 90.0 - elev
L10_data['sun_elev'], L10_data['sun_zenith'], L10_data['earth_sun_distance_au'] = elev, zenith, distance
m_rayleigh = L10_data['airmass_rayleigh'] = airmass_rayleigh(zenith)
m_aerosol = L10_data['airmass_aerosol'] = airmass_aerosol(zenith)
m_ozone = L10_data['airmass_ozone'] = airmass_layer(zenith, AIRMASS_OZONE_HEIGHT_KM)
m_no2 = L10_data['airmass_no2'] = airmass_layer(zenith, AIRMASS_NO2_HEIGHT_KM)

signal_low = np.zeros(len(L06_data), dtype=bool)
for ch in V0_CHANNELS:
    nm = wavelengths[ch]
    # a channel temperature of exactly 0 is the sensors' startup zeros
    temp = np.where(L06_data[f'ch{ch}_temp'] == 0.0, np.nan, L06_data[f'ch{ch}_temp'])
    A, B = V0_TEMP_CORR[ch]
    dT = temp - V0_TREF
    volts = np.abs(L06_data[f'ch{ch}_1x_darksub_quad']) / (1.0 + A * dT + B * dT ** 2)
    L10_data[f'ch{ch}_1x_darksub_quad_v0tc'] = volts

    tau_r = L10_data[f'tau_rayleigh_{nm}nm'] = tau_rayleigh(nm, L10_data['pressure_hpa'])
    tau_o3 = L10_data[f'tau_ozone_{nm}nm'] = tau_gas(OZONE_COLUMN_DU, OZONE_XSEC[ch])
    tau_no2 = L10_data[f'tau_no2_{nm}nm'] = tau_gas(NO2_COLUMN_DU, NO2_XSEC[ch])

    signal = volts - V0_A[ch]
    low = ~(signal > 0)
    signal_low |= low & np.isfinite(volts)
    with np.errstate(invalid='ignore', divide='ignore'):
        slant = np.log((V0[ch] - V0_A[ch]) / (distance ** 2 * signal))
    L10_data[f'aod_{nm}nm'] = np.where(low, np.nan,
                                       (slant - m_rayleigh * tau_r - m_ozone * tau_o3 - m_no2 * tau_no2) / m_aerosol)

# Angstrom exponent: the slope of -ln(AOD) against ln(wavelength), over the channels with ANGSTROM_WAVELENGTHS
angstrom_nm = [nm for nm in sorted(wavelengths.values()) if nm in ANGSTROM_WAVELENGTHS]
L10_data['angstrom'] = np.nan
if len(angstrom_nm) >= 2:
    aods = np.stack([L10_data[f'aod_{nm}nm'] for nm in angstrom_nm], axis=1)
    usable = np.all(aods > 0, axis=1)
    x = np.log(angstrom_nm) - np.mean(np.log(angstrom_nm))
    with np.errstate(invalid='ignore', divide='ignore'):
        slope = np.log(aods) @ x / np.sum(x ** 2)
    L10_data['angstrom'] = np.where(usable, -slope, np.nan)

tracking_error_bit = {1: TRACKING_ERROR_1, 2: TRACKING_ERROR_2, 3: TRACKING_ERROR_3}[AOD_TRACKING_LEVEL]
bad_tracking = NO_CAMERA_DATA | CAMERA_BRIGHTNESS_HIGH | CAMERA_BRIGHTNESS_LOW | tracking_error_bit
flags = np.zeros(len(L06_data), dtype='i4')
flags |= np.where(L06_data['cloud_flags'] != 0, AOD_CLOUD, 0)
flags |= np.where((L06_data['tracking_flags'] & bad_tracking) != 0, AOD_TRACKING, 0)
flags |= np.where((L06_data['housekeeping_flags'] & CHANNEL_TEMP_LOW) != 0, AOD_CHANNEL_TEMP_LOW, 0)
flags |= np.where(~good_pressure, AOD_PRESSURE_FILLED, 0)
flags |= np.where(~good_position, AOD_POSITION_FILLED, 0)
flags |= np.where(signal_low, AOD_SIGNAL_LOW, 0)
L10_data['aod_flags'] = flags

now = datetime.now(pytz.utc).isoformat()
metadata.update({'L06-to-L10_PROCESSING_TIME': now, 'LAST_PROCESSING_TIME': now,
                 'AOD_WAVELENGTHS_NM': wavelengths, 'AOD_DARK': 'darksub_quad',
                 'V0_MODE': V0_MODE, 'V0_TREF': V0_TREF, 'V0': V0, 'V0_A': V0_A, 'V0_TEMP_CORR': V0_TEMP_CORR,
                 'OZONE_COLUMN_DU': OZONE_COLUMN_DU, 'NO2_COLUMN_DU': NO2_COLUMN_DU,
                 'OZONE_XSEC': OZONE_XSEC, 'NO2_XSEC': NO2_XSEC,
                 'AIRMASS_OZONE_HEIGHT_KM': AIRMASS_OZONE_HEIGHT_KM, 'AIRMASS_NO2_HEIGHT_KM': AIRMASS_NO2_HEIGHT_KM,
                 'IMU_PRESS_MIN': IMU_PRESS_MIN, 'IMU_PRESS_MAX': IMU_PRESS_MAX,
                 'AOD_PRESSURE_FALLBACK_HPA': AOD_PRESSURE_FALLBACK_HPA, 'AOD_TRACKING_LEVEL': AOD_TRACKING_LEVEL,
                 'ANGSTROM_WAVELENGTHS': angstrom_nm})

print(f"{os.path.basename(L10_npyfile)} ({V0_MODE} V0): {len(L10_data)} timesteps, {np.sum(flags == 0)} unflagged, "
      f"{np.sum(~good_position)} GPS dropouts filled, {np.sum(~good_pressure)} pressures filled")

try:
    with open(L10_npyfile, 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L10_data, metadata = metadata)
except FileNotFoundError:
    with open('recoveryfilename.L10', 'bw') as arrayfile:
        np.savez(arrayfile, array_data=L10_data, metadata = metadata)
