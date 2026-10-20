#!/usr/bin/env python3

# plots the dark diode voltage against temperature for each channel, from an L05 file.
# the caps were on for the whole run, so every voltage is a dark.
# each point is a one-second L05 timestep: the mean voltage against the mean interpolated
# channel temperature. timesteps flagged HEATER_ON (heater on, plus a margin) are drawn in a
# muted color behind the usable data, and left out of the fit.
# --block1-shift delays the block 1 temperatures, and --block1-tau applies a first-order thermal lag
# to them instead, to test whether the diodes lag the sensors (see scan_block1_shift.py).
# --tmin zooms in on temperatures above a value: the line is fit to the zoomed points only, and
# the fit over the full temperature range is drawn dashed for comparison.

import sys, os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'L0.5', 'scripts'))
from seastar_error_flags import HEATER_ON

USER_FLAGS = 7  # index of the user-set flags in L05line['flags']
HEATER_COLOR = '#e3c4b3'  # muted warm tone, so it doesn't read as part of the blue time scale
CHANNELS = range(1, 11)

# from hardware/configuration-sept-2026.md
WAVELENGTHS = {1: '380/2 nm', 2: '440/10 nm', 3: '500/10 nm', 4: '550/10 nm', 5: '675/10 nm',
               6: '340/2 nm', 7: '870/10 nm', 8: '940/10 nm', 9: '940/5 nm', 10: '1020/10 nm'}

parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', default='../pickle/SeaSTAR_2026-10-14_08-49-33.L05')
parser.add_argument('-o', '--outputfile', default='plots/dark_vs_temp.png')
parser.add_argument('--exclude-heater', action='store_true',
                    help="don't plot the timesteps flagged HEATER_ON")
lag = parser.add_mutually_exclusive_group()
lag.add_argument('--block1-shift', type=float, default=0.0,
                 help='seconds to delay the block 1 (ch1-5) temperatures by: each voltage is plotted against '
                      'the temperature this many seconds earlier (default 0)')
lag.add_argument('--block1-tau', type=float, default=0.0,
                 help='time constant in seconds of a first-order lag applied to the block 1 (ch1-5) '
                      'temperatures: the diode relaxes towards the sensor temperature (default 0, no lag)')
parser.add_argument('--tmin', type=float,
                    help='only plot and fit temperatures at or above this, in °C')
parser.add_argument('--channels', type=int, nargs='+', default=list(CHANNELS),
                    help='channels to plot (default all)')
args = parser.parse_args()

def shifted(values, seconds, logged, shift):
    # values at (seconds - shift), interpolated between the logged timesteps
    return np.interp(seconds - shift, seconds[logged], values[logged])

def lagged(values, seconds, logged, tau):
    # first-order lag: the diode temperature relaxes towards the sensor temperature with time constant tau,
    # starting from the first logged sensor temperature (assumes the block starts in equilibrium)
    out = np.full_like(values, np.nan)
    index = np.flatnonzero(logged)
    diode = values[index[0]]
    previous = seconds[index[0]]
    for i in index:
        diode += (1.0 - np.exp(-(seconds[i] - previous) / tau)) * (values[i] - diode)
        out[i] = diode
        previous = seconds[i]
    return out

L05_data = np.load(args.file, allow_pickle=True)
L05_array = L05_data['array_data']
metadata = L05_data['metadata'][()]

usable = (L05_array['flags'][:, USER_FLAGS] & HEATER_ON) == 0
# the first timesteps after startup log zeros for every sensor
# (unused datapoints in each timestep are NaN, so nanmean ignores them)
time = L05_array['datetime'][:, 0]
seconds = (time - time[0]) / np.timedelta64(1, 's')

rows = (len(args.channels) + 4) // 5
columns = min(len(args.channels), 5)
fig, axes = plt.subplots(rows, columns, figsize=(4 * columns, 4 * rows), layout='constrained', squeeze=False)
for ax in axes.flat[len(args.channels):]:
    ax.set_visible(False)

for ch, ax in zip(args.channels, axes.flat):
    voltage = np.nanmean(L05_array[f'ch{ch}_1x'], axis=1) * 1000.0  # mV
    temp = np.nanmean(L05_array[f'ch{ch}_temp'], axis=1)
    logged = temp > 0  # drops the startup zeros

    shift = args.block1_shift if ch <= 5 else 0.0
    tau = args.block1_tau if ch <= 5 else 0.0
    if shift != 0.0:
        temp = shifted(temp, seconds, logged, shift)
        logged = logged & (seconds - shift >= seconds[logged][0])  # no temperature yet for the first timesteps
    elif tau != 0.0:
        temp = lagged(temp, seconds, logged, tau)

    keep = logged & usable
    full_slope, full_offset = np.polyfit(temp[keep], voltage[keep], 1)
    if args.tmin is not None:
        logged = logged & (temp >= args.tmin)
        keep = logged & usable
        if not keep.any():
            sys.stderr.write(f"ch{ch} ({WAVELENGTHS[ch]}): no heater-off points at or above {args.tmin:g} C\n")
            ax.set_visible(False)
            continue

    if not args.exclude_heater:
        heater = logged & ~usable
        ax.scatter(temp[heater], voltage[heater], s=2, color=HEATER_COLOR, linewidths=0)

    points = ax.scatter(temp[keep], voltage[keep], c=mdates.date2num(time[keep]), cmap='Blues',
                        vmin=mdates.date2num(time[logged].min()) - 0.03,  # so the earliest points aren't white
                        s=2, linewidths=0)

    slope, offset = np.polyfit(temp[keep], voltage[keep], 1)
    fit_temps = np.array([temp[keep].min(), temp[keep].max()])
    ax.plot(fit_temps, slope * fit_temps + offset, color='0.2', linewidth=1)
    if args.tmin is None:
        ax.text(0.03, 0.95, f'{slope * 1000.0:.2f} µV/°C', transform=ax.transAxes, va='top', fontsize=9)
    else:
        ax.plot(fit_temps, full_slope * fit_temps + full_offset, color='0.2', linewidth=1, linestyle='--')
        ax.text(0.03, 0.95, f'≥ {args.tmin:g} °C: {slope * 1000.0:.2f} µV/°C\n'
                            f'full range (dashed): {full_slope * 1000.0:.2f} µV/°C',
                transform=ax.transAxes, va='top', fontsize=9)
    sys.stderr.write(f"ch{ch} ({WAVELENGTHS[ch]}): {keep.sum()} points, slope {slope * 1000.0:.3f} uV/C, "
                     f"offset {offset:.4f} mV at 0 C, full-range slope {full_slope * 1000.0:.3f} uV/C\n")

    block = 1 if ch <= 5 else 2
    if shift != 0.0:
        shift_note = f', temp delayed {shift:g} s'
    elif tau != 0.0:
        shift_note = f', temp lagged τ={tau:g} s'
    else:
        shift_note = ''
    ax.set_title(f'ch{ch} - {WAVELENGTHS[ch]} (block {block}{shift_note})', fontsize=10)
    ax.grid(color='0.9', linewidth=0.5)
    ax.tick_params(labelsize=8)

for ax in axes[-1]:
    ax.set_xlabel('channel temperature (°C)')
for ax in axes[:, 0]:
    ax.set_ylabel('dark voltage (mV)')

if not args.exclude_heater:
    heater_marker = plt.Line2D([], [], linestyle='none', marker='o', markersize=5,
                               markerfacecolor=HEATER_COLOR, markeredgewidth=0)
    fig.legend([heater_marker], ['heater on (± margin), not in fit'], loc='upper right', fontsize=9, frameon=False)

colorbar = fig.colorbar(points, ax=axes, shrink=0.6, pad=0.01)
colorbar.ax.yaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
colorbar.set_label('time (UTC)')

swapped = [f'block {block}' for block in (1, 2) if metadata.get(f'SWAP_BLOCK{block}_TEMPS', False)]
swap_note = ', '.join(swapped) + ' temperature sensors swapped' if swapped else 'no temperature sensors swapped'
zoom_note = f', temperatures ≥ {args.tmin:g} °C' if args.tmin is not None else ''
fig.suptitle(f'Dark voltage vs temperature, {os.path.basename(args.file)} (1 s means, {swap_note}{zoom_note})')

os.makedirs(os.path.dirname(args.outputfile) or '.', exist_ok=True)
fig.savefig(args.outputfile, dpi=120)
sys.stderr.write(f"wrote {args.outputfile}\n")
