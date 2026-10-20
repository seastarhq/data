#!/usr/bin/env python3

# tests whether delaying the block 1 temperatures straightens out the sawtooth in dark voltage
# vs temperature. for each shift, every block 1 channel's dark voltage is fit with a straight line
# against the temperature that many seconds earlier, and the RMS residual of that fit is recorded:
# the shift that gives the smallest residual is the best estimate of how far the diodes lag the sensors.
#
# for comparison it also tries a first-order thermal lag (the diode relaxing towards the sensor
# temperature with time constant tau) instead of a pure delay.
#
# the residuals are calculated two ways: from the usable (heater off) timesteps only, which is what
# the dark-vs-temperature fit uses, and from all the timesteps. a lag model that is right should
# also bring the heater-on timesteps onto the line.

import sys, os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'L0.5', 'scripts'))
from seastar_error_flags import HEATER_ON

USER_FLAGS = 7  # index of the user-set flags in L05line['flags']
BLOCK1_CHANNELS = range(1, 6)

parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', default='../pickle/SeaSTAR_2026-10-14_08-49-33.L05')
parser.add_argument('--max', type=float, default=900.0, help='largest shift / time constant to try, seconds (default 900)')
parser.add_argument('--step', type=float, default=5.0, help='seconds between the shifts tried (default 5)')
parser.add_argument('-o', '--outputfile', default='plots/block1_shift_scan.png')
args = parser.parse_args()

L05_array = np.load(args.file, allow_pickle=True)['array_data']
usable = (L05_array['flags'][:, USER_FLAGS] & HEATER_ON) == 0
time = L05_array['datetime'][:, 0]
seconds = (time - time[0]) / np.timedelta64(1, 's')

def delayed(temp, logged, shift):
    # temperature at (seconds - shift), interpolated between the logged timesteps
    return np.interp(seconds - shift, seconds[logged], temp[logged])

def lagged(temp, logged, tau):
    # first-order lag: the diode temperature relaxes towards the sensor temperature with time constant tau
    out = np.full_like(temp, np.nan)
    index = np.flatnonzero(logged)
    diode = temp[index[0]]
    previous = seconds[index[0]]
    for i in index:
        diode += (1.0 - np.exp(-(seconds[i] - previous) / tau)) * (temp[i] - diode)
        out[i] = diode
        previous = seconds[i]
    return out

def rms_residual(temp, voltage, select):
    slope, offset = np.polyfit(temp[select], voltage[select], 1)
    return np.sqrt(np.mean((voltage[select] - (slope * temp[select] + offset)) ** 2))

shifts = np.arange(0.0, args.max + args.step / 2, args.step)
taus = shifts[shifts > 0]
results = {}

for ch in BLOCK1_CHANNELS:
    voltage = np.nanmean(L05_array[f'ch{ch}_1x'], axis=1) * 1000.0  # mV
    temp = np.nanmean(L05_array[f'ch{ch}_temp'], axis=1)
    logged = temp > 0  # drops the startup zeros
    # skip the first --max seconds, so every shift is scored on the same timesteps
    scored = logged & (seconds >= seconds[logged][0] + args.max)

    delay_rms = np.array([[rms_residual(delayed(temp, logged, s), voltage, scored & usable),
                           rms_residual(delayed(temp, logged, s), voltage, scored)] for s in shifts]) * 1000.0  # uV
    lag_rms = np.array([[rms_residual(lagged(temp, logged, t), voltage, scored & usable),
                         rms_residual(lagged(temp, logged, t), voltage, scored)] for t in taus]) * 1000.0  # uV
    results[ch] = (delay_rms, lag_rms)

    best_shift = shifts[np.argmin(delay_rms[:, 0])]
    best_tau = taus[np.argmin(lag_rms[:, 0])]
    sys.stderr.write(f"ch{ch}: RMS residual (uV), heater-off / all timesteps\n"
                     f"   no shift:                 {delay_rms[0, 0]:6.1f} / {delay_rms[0, 1]:6.1f}\n"
                     f"   best delay {best_shift:5.0f} s:       {delay_rms[:, 0].min():6.1f} / "
                     f"{delay_rms[np.argmin(delay_rms[:, 0]), 1]:6.1f}\n"
                     f"   best lag tau {best_tau:5.0f} s:     {lag_rms[:, 0].min():6.1f} / "
                     f"{lag_rms[np.argmin(lag_rms[:, 0]), 1]:6.1f}\n")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained', sharey=True)
colors = plt.get_cmap('tab10').colors
for ch, color in zip(BLOCK1_CHANNELS, colors):
    delay_rms, lag_rms = results[ch]
    axes[0].plot(shifts, delay_rms[:, 0], color=color, linewidth=1.5, label=f'ch{ch}')
    axes[0].plot(shifts, delay_rms[:, 1], color=color, linewidth=1, linestyle=':')
    axes[1].plot(taus, lag_rms[:, 0], color=color, linewidth=1.5, label=f'ch{ch}')
    axes[1].plot(taus, lag_rms[:, 1], color=color, linewidth=1, linestyle=':')
axes[0].set_xlabel('block 1 temperature delay (s)')
axes[1].set_xlabel('block 1 first-order lag time constant (s)')
axes[0].set_ylabel('RMS residual of straight-line fit (µV)')
axes[0].set_title('pure time shift', fontsize=10)
axes[1].set_title('first-order thermal lag', fontsize=10)
for ax in axes:
    ax.grid(color='0.9', linewidth=0.5)
axes[0].legend(title='solid: heater off\ndotted: all timesteps', fontsize=8, title_fontsize=8, frameon=False)
fig.suptitle(f'Block 1 dark voltage vs temperature: fit residual against temperature lag, {os.path.basename(args.file)}')

os.makedirs(os.path.dirname(args.outputfile) or '.', exist_ok=True)
fig.savefig(args.outputfile, dpi=120)
sys.stderr.write(f"wrote {args.outputfile}\n")
