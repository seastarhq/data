#!/usr/bin/env python3

# finds the caps-on dark periods of each channel in an L05 file, for the DARK_PERIODS_CH<n> parameters
# used by dark_subtraction.py. the darks were taken by capping one channel at a time (see raw/notes_*.txt),
# and the caps overlap, so a channel is dark when its voltage has dropped to near zero and stays flat (a lost
# sun or a cloud flickers), while at least one other channel is still lit (when everything drops together
# it's a cloud or tracking loss, not a cap).
# only the windows around the noted dark sequences are searched. the first and last second of each period are
# trimmed off, since the cap is moving then.
# prints DARK_PERIODS_CH<n> lines to paste into L0.6/setup/parameters.sh, and plots the periods for checking.

import sys, os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CHANNELS = range(1, 11)

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--windows', nargs='+', required=True,
                    help='UTC times of the noted dark sequences, e.g. 2026-09-30T18:01:00; each is searched +/- --margin')
parser.add_argument('--margin', type=float, default=300, help='seconds either side of each window time (default 300)')
parser.add_argument('--dark-fraction', type=float, default=0.1,
                    help="a channel is dark below this fraction of its lit level in the window (default 0.1)")
parser.add_argument('--lit-fraction', type=float, default=0.5,
                    help='the other channels count as lit above this fraction of their lit level (default 0.5)')
parser.add_argument('--flat', type=float, default=1.0,
                    help='a dark channel varies by less than this standard deviation over --flat-time, in mV (default 1)')
parser.add_argument('--flat-time', type=int, default=5, help='seconds the flatness is measured over (default 5, centred)')
parser.add_argument('--min-length', type=int, default=4, help='shortest dark run kept, in seconds, before trimming (default 4)')
parser.add_argument('-o', '--outputfile', default='../plots/dark_periods.png')
args = parser.parse_args()

L05_data = np.load(args.file, allow_pickle=True)
L05_array = L05_data['array_data']
times = L05_array['datetime'][:, 0].astype('datetime64[ms]')
voltage = {ch: np.nanmean(L05_array[f'ch{ch}_1x'], axis=1) for ch in CHANNELS}

periods = {ch: [] for ch in CHANNELS}
fig, axes = plt.subplots(len(args.windows), 1, figsize=(14, 3 * len(args.windows)), layout='constrained', squeeze=False)
for window, ax in zip(args.windows, axes[:, 0]):
    centre = np.datetime64(window, 'ms')
    margin = np.timedelta64(int(args.margin * 1000), 'ms')
    sel = np.flatnonzero((times >= centre - margin) & (times <= centre + margin))
    # each channel's lit level in the window: a high percentile of its magnitude
    lit_level = {ch: np.nanpercentile(np.abs(voltage[ch][sel]), 95) for ch in CHANNELS}
    lit = {ch: np.abs(voltage[ch][sel]) > args.lit_fraction * lit_level[ch] for ch in CHANNELS}
    for ch in CHANNELS:
        others_lit = np.any([lit[other] for other in CHANNELS if other != ch], axis=0)
        # centred rolling standard deviation (a window running off the end of the search window isn't flat)
        windows = np.lib.stride_tricks.sliding_window_view(voltage[ch][sel], args.flat_time)
        flatness = np.full(len(sel), np.inf)
        flatness[args.flat_time // 2: args.flat_time // 2 + len(windows)] = np.std(windows, axis=1)
        dark = (np.abs(voltage[ch][sel]) < args.dark_fraction * lit_level[ch]) & (flatness < args.flat / 1000.0) & others_lit
        # runs of consecutive dark timesteps
        edges = np.flatnonzero(np.diff(np.concatenate(([0], dark.astype(int), [0]))))
        for start, end in zip(edges[::2], edges[1::2]):  # end is one past the last dark timestep
            if end - start >= args.min_length:
                periods[ch].append((times[sel[start + 1]], times[sel[end - 2]]))
        line, = ax.plot(times[sel], voltage[ch][sel], linewidth=0.8, label=f'ch{ch}')
        for start, end in periods[ch]:
            if centre - margin <= start <= centre + margin:
                ax.axvspan(start, end, color=line.get_color(), alpha=0.2)
    ax.set_title(f'{window} UTC ± {args.margin:g} s', fontsize=10)
    ax.set_ylabel('1x voltage (V)')
    ax.grid(color='0.9', linewidth=0.5)
axes[0, 0].legend(ncol=10, fontsize=8, loc='lower left', frameon=False)
fig.suptitle(f'Dark periods found in {os.path.basename(args.file)} (shaded)')

os.makedirs(os.path.dirname(args.outputfile) or '.', exist_ok=True)
fig.savefig(args.outputfile, dpi=100)
sys.stderr.write(f"wrote {args.outputfile}\n")

for ch in CHANNELS:
    durations = [int((end - start) / np.timedelta64(1, 's')) + 1 for start, end in periods[ch]]
    sys.stderr.write(f"ch{ch}: {len(periods[ch])} periods, {sum(durations)} s, "
                     f"dark mean {np.mean([np.nanmean(voltage[ch][(times >= s) & (times <= e)]) for s, e in periods[ch]]) * 1000:.2f} mV\n"
                     if periods[ch] else f"ch{ch}: no periods found\n")
    print(f'DARK_PERIODS_CH{ch}="' + ' '.join(f'{start}/{end}' for start, end in periods[ch]) + '"')
