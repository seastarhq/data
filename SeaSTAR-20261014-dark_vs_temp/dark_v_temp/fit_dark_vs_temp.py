#!/usr/bin/env python3

# fits the dark diode voltage against temperature for each channel, from an L05 file, with a straight
# line and a quadratic, for the L0.6 dark subtraction (dark_subtraction.py).
# the caps were on for the whole run, so every voltage is a dark.
# each point is a one-second L05 timestep: the mean voltage against the mean interpolated channel
# temperature (the raw sensor temperature, with no lag model, which is what L0.6 has in the field).
# timesteps flagged HEATER_ON are left out of the fit, as in plot_dark_vs_temp.py.
# the polynomials are in dT = T - tref, in volts, so they read the same way as the DARK_* parameters:
#     dark_lin  = c0 + c1*dT
#     dark_quad = c0 + c1*dT + c2*dT^2
# the coefficients are printed as lines to paste into an L0.6/setup/parameters.sh, and plotted.

import sys, os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'L0.5', 'scripts'))
from seastar_error_flags import HEATER_ON

USER_FLAGS = 7  # index of the user-set flags in L05line['flags']
CHANNELS = range(1, 11)

# from hardware/configuration-sept-2026.md
WAVELENGTHS = {1: '380/2 nm', 2: '440/10 nm', 3: '500/10 nm', 4: '550/10 nm', 5: '675/10 nm',
               6: '340/2 nm', 7: '870/10 nm', 8: '940/10 nm', 9: '940/5 nm', 10: '1020/10 nm'}

parser = argparse.ArgumentParser()
parser.add_argument('file', nargs='?', default='../pickle/SeaSTAR_2026-10-14_08-49-33.L05')
parser.add_argument('-o', '--outputfile', default='plots/dark_vs_temp_fits.png')
parser.add_argument('--tref', type=float, default=30.0,
                    help='reference temperature the polynomials are written about, in °C (default 30)')
args = parser.parse_args()

L05_data = np.load(args.file, allow_pickle=True)
L05_array = L05_data['array_data']

usable = (L05_array['flags'][:, USER_FLAGS] & HEATER_ON) == 0

fig, axes = plt.subplots(2, 5, figsize=(20, 8), layout='constrained', squeeze=False)

lines = [f'# dark voltage vs channel temperature, fitted by fit_dark_vs_temp.py from {os.path.basename(args.file)}',
         '# (20261014 caps-on run, heater-off timesteps, raw sensor temperatures), in volts with dT = T - DARK_TREF_CH<n>']
for ch, ax in zip(CHANNELS, axes.flat):
    voltage = np.nanmean(L05_array[f'ch{ch}_1x'], axis=1)
    temp = np.nanmean(L05_array[f'ch{ch}_temp'], axis=1)
    keep = (temp > 0) & usable & np.isfinite(voltage)  # temp > 0 drops the startup zeros

    dT = temp[keep] - args.tref
    lin = np.polyfit(dT, voltage[keep], 1)[::-1]   # c0, c1
    quad = np.polyfit(dT, voltage[keep], 2)[::-1]  # c0, c1, c2
    lin_rms = np.std(voltage[keep] - np.polynomial.polynomial.polyval(dT, lin))
    quad_rms = np.std(voltage[keep] - np.polynomial.polynomial.polyval(dT, quad))
    tmin, tmax = temp[keep].min(), temp[keep].max()

    lines.append(f'# ch{ch} ({WAVELENGTHS[ch]}): {keep.sum()} points, {tmin:.1f} to {tmax:.1f} C, '
                 f'rms {lin_rms * 1e6:.1f} uV (lin) {quad_rms * 1e6:.1f} uV (quad)')
    lines.append(f'DARK_TREF_CH{ch}={args.tref:g}')
    lines.append(f'DARK_LIN_C0_CH{ch}={lin[0]:.6e}')
    lines.append(f'DARK_LIN_C1_CH{ch}={lin[1]:.6e}')
    lines.append(f'DARK_QUAD_C0_CH{ch}={quad[0]:.6e}')
    lines.append(f'DARK_QUAD_C1_CH{ch}={quad[1]:.6e}')
    lines.append(f'DARK_QUAD_C2_CH{ch}={quad[2]:.6e}')

    ax.scatter(temp[keep], voltage[keep] * 1000.0, s=2, color='0.6', linewidths=0)
    # solid over the fitted temperatures, dashed out to the reference temperature where that's beyond them
    fit_temps = np.linspace(tmin, tmax, 100)
    wide_temps = np.linspace(min(tmin, args.tref), max(tmax, args.tref), 100)
    for coeffs, color, label in ((lin, 'tab:blue', 'linear'), (quad, 'tab:red', 'quadratic')):
        ax.plot(wide_temps, np.polynomial.polynomial.polyval(wide_temps - args.tref, coeffs) * 1000.0,
                color=color, linewidth=1, linestyle='--')
        ax.plot(fit_temps, np.polynomial.polynomial.polyval(fit_temps - args.tref, coeffs) * 1000.0,
                color=color, linewidth=1.5, label=label)
    ax.text(0.03, 0.95, f'lin rms {lin_rms * 1e6:.1f} µV\nquad rms {quad_rms * 1e6:.1f} µV',
            transform=ax.transAxes, va='top', fontsize=9)
    ax.set_title(f'ch{ch} - {WAVELENGTHS[ch]} (block {1 if ch <= 5 else 2})', fontsize=10)
    ax.grid(color='0.9', linewidth=0.5)
    ax.tick_params(labelsize=8)

for ax in axes[-1]:
    ax.set_xlabel('channel temperature (°C)')
for ax in axes[:, 0]:
    ax.set_ylabel('dark voltage (mV)')
axes.flat[0].legend(loc='lower left', fontsize=8, frameon=False)
fig.suptitle(f'Dark voltage fits, {os.path.basename(args.file)} (heater off, raw sensor temperatures, '
             f'dashed = extrapolated to {args.tref:g} °C)')

os.makedirs(os.path.dirname(args.outputfile) or '.', exist_ok=True)
fig.savefig(args.outputfile, dpi=120)
sys.stderr.write(f"wrote {args.outputfile}\n")

print('\n'.join(lines))
