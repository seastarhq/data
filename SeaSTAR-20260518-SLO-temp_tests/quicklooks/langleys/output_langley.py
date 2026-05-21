#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import argparse
import pytz
import tqdm
import pandas as pd
import matplotlib.pyplot as plt

# custom seastar modules
import seastar_datautils
from seastar_error_flags import *
from seastar_analysis_utils import *

# where to find things including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR L06_DATA_DIR
from seastar_filepaths import *

## analysis parameters:
# including 
# SEASTAR_TIMEZONE AVG_INTERVAL ANALYSIS_MARGIN BRIGHTNESS_MIN BRIGHTNESS_MAX TRACKING_EUCLIDIAN_MAX
# HOT_BLOCK1_MIN HOT_BLOCK1_MAX HOT_BLOCK2_MIN HOT_BLOCK2_MAX COLD_BLOCK_MIN COLD_BLOCK_MAX
# IMU_TEMP_MIN IMU_TEMP_MAX IMU_PRESS_MIN IMU_PRESS_MAX
# TRIPLETVAR_TOLERANCE_PERCENT
from seastar_analysis_params import *

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-o', '--outputfile')
args = parser.parse_args()

# findFile needs a list passed to it, so we make one with `cwd` added 
L06_data_dir = [L06_DATA_DIR, './']
L06_npyfile = seastar_datautils.findFile(args.file, L06_data_dir)
# this is if our filename does not conform to convention
try:
    L06_file_date = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[1]
    L06_file_time = os.path.splitext(os.path.basename(L06_npyfile))[0].split("_")[2]
except: 
    pass

#print(f"\n\n{L05_file_date} {L05_file_time}\n\n")

L06_data = np.load(L06_npyfile, allow_pickle=True)
metadata = L06_data['metadata'][()]
L06_data = L06_data['array_data']

#print(L05_data.shape)

#L10_data = seastar_datautils.create_L10_sun_2darray(len(L05_data))
if args.outputfile is None:
    outfile = "./recoveryfile.txt"
else:
    outfile = QUICKLOOKS_DIR + '/' + 'langleys/' + args.outputfile

logfile_path = os.path.splitext(outfile)[0] + '_errors.log'


def safe_log_neg(value, channel_name, timestep, mydatetime, logfile):
    """Compute log(-value); on failure, log the error and return NaN."""
    try:
        return math.log(-1.0 * value)
    except (ValueError, TypeError) as e:
        logfile.write(
            f"timestep={timestep} datetime={mydatetime} channel={channel_name} "
            f"value={value} error={e}\n"
        )
        return float('nan')


rows = []

with open(outfile, "w") as textfile, open(logfile_path, "w") as errlog:

    for timestep in tqdm.tqdm(range(len(L06_data))):

        mydatetime = L06_data[timestep]['datetime']
        mysun_ephem_az = L06_data[timestep]['sun_ephem_az']
        mysun_ephem_elev = L06_data[timestep]['sun_ephem_elev']
        myimu_press = L06_data[timestep]['imu_press']
        mylat = L06_data[timestep]['imu_lat']
        mylon = L06_data[timestep]['imu_lon']
        logch1_1x = safe_log_neg(L06_data[timestep]['ch1_1x'] - CH1_DARK, 'ch1_1x', timestep, mydatetime, errlog)
        logch2_1x = safe_log_neg(L06_data[timestep]['ch2_1x'] - CH2_DARK, 'ch2_1x', timestep, mydatetime, errlog)
        logch3_1x = safe_log_neg(L06_data[timestep]['ch3_1x'] - CH3_DARK, 'ch3_1x', timestep, mydatetime, errlog)
        logch4_1x = safe_log_neg(L06_data[timestep]['ch4_1x'] - CH4_DARK, 'ch4_1x', timestep, mydatetime, errlog)
        logch5_1x = safe_log_neg(L06_data[timestep]['ch5_1x'] - CH5_DARK, 'ch5_1x', timestep, mydatetime, errlog)
        myhot_block_temp =  L06_data[timestep]['hot_block1_temp']
        mydTdt_smooth = L06_data[timestep]['dTdt_smooth']
        myd2Tdt2_smooth = L06_data[timestep]['d2Tdt2_smooth']
        myeuclidian_dist = L06_data[timestep]['euclidian_dist']
        mytracking_flags = L06_data[timestep]['tracking_flags']
        myrobot_flags = L06_data[timestep]['robot_flags']
        myhousekeeping_flags =L06_data[timestep]['housekeeping_flags']
        myradiometer_1x_flags = L06_data[timestep]['radiometer_1x_flags']

        airmass = airmass_star(mysun_ephem_elev, myimu_press)
        dataline = f"{airmass} {logch1_1x} {logch2_1x} {logch3_1x} {logch4_1x} {logch5_1x} {myhot_block_temp}\n"
        textfile.write(dataline)

        rows.append({
            'datetime': mydatetime,
            'airmass': airmass,
            'logch1_1x': logch1_1x,
            'logch2_1x': logch2_1x,
            'logch3_1x': logch3_1x,
            'logch4_1x': logch4_1x,
            'logch5_1x': logch5_1x,
            'hot_block_temp': myhot_block_temp,
            'dTdt_smooth': mydTdt_smooth,
            'd2Tdt2_smooth': myd2Tdt2_smooth,
        })

df = pd.DataFrame(rows)

channels = ['logch1_1x', 'logch2_1x', 'logch3_1x', 'logch4_1x', 'logch5_1x']
labels   = [f'Ch{i} ({nm} nm)' for i, nm in enumerate([CH1_NM, CH2_NM, CH3_NM, CH4_NM, CH5_NM], start=1)]

# Set to (min, max) to fix axis limits, or None to auto-scale
xlim = (1.0, 1.15)

# Per-channel y-limits — use None to auto-scale that channel
ylims = {
    'logch1_1x': (-0.18, -0.12),
    'logch2_1x': (0.41, 0.425), #(-2,0),
    'logch3_1x': (0.47, 0.480), #(-2,0),
    'logch4_1x': (0.44, 0.460), #(-2,0),
    'logch5_1x': (0.532, 0.54), #(0.4, 0.5), #(-2,0),
}

# y-limits for the hot block temperature subplot
temp_ylim =  (28,42.5)  # e.g. (20.0, 40.0)

# Dashed vertical lines at these airmass values (empty list = none)
vlines = [1.13, 1.12, 1.067, 1.0625, 1.049,  1.045, 1.038, 1.0355, 1.0315]

n_subplots = len(channels) + 1  # +1 for hot_block_temp
fig, axes = plt.subplots(n_subplots, 1, figsize=(8, 3 * n_subplots), sharex=True)

for ax, col, label in zip(axes, channels, labels):
    ax.scatter(df['airmass'], df[col], s=4, label=label)
    ax.set_ylabel(f'ln(V) — {label}')
    ax.legend(loc='upper right')
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylims.get(col) is not None:
        ax.set_ylim(ylims[col])
    for vx in vlines:
        ax.axvline(vx, color='gray', linestyle='--', linewidth=0.8)

ax_temp = axes[-1]
ax_temp.scatter(df['airmass'], df['hot_block_temp'], s=4, color='tab:red', label='Hot block temp')
ax_temp.set_ylabel('Temp (°C)')
ax_temp.set_xlabel('Airmass')
ax_temp.legend(loc='upper right')
if xlim is not None:
    ax_temp.set_xlim(xlim)
if temp_ylim is not None:
    ax_temp.set_ylim(temp_ylim)
for vx in vlines:
    ax_temp.axvline(vx, color='gray', linestyle='--', linewidth=0.8)

fig.suptitle('Langley Plot: Airmass vs ln(Voltage) by Channel')
plt.tight_layout()

plot_path = os.path.splitext(outfile)[0] + '_langley.png'
plt.savefig(plot_path, dpi=150)
print(f"Plot saved to {plot_path}")
    







    




