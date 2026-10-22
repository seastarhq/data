# Dark voltage vs temperature, 2026-10-14

Analysis notes for run `2026-10-14_08-49-33`. The caps were on for the whole run, so every
radiometer voltage is a dark. The heater was cycled on and off nine times to step the hot blocks
through temperature (see `raw/notes_20261014.txt`). Hardware layout is in
`hardware/configuration-sept-2026.md`.

## Processing

### Heater-on flagging (L0.5)

`L0.5/scripts/L05-heater-flags.py` sets the `HEATER_ON` user flag (`flags[7]`, value 1, defined in
`seastar_error_flags.py`) on every L05 timestep within a heater-on period from the notes, plus a
margin either side. Usable data is the timesteps without the flag.

- The heater on/off times come from `raw/notes_<YYYYMMDD>.txt`. The line pattern tolerates the
  misspellings in the notes ("hetaer off", "hetare off"), and all nine periods were found.
- The notes are in local time (US/Pacific) and the L05 timestamps are naive UTC, so the note times are
  converted (08:52 local is 15:52 UTC).
- Margin: 45 s either side by default (`--margin`). A timestep is flagged if any of its datapoints fall
  in a period plus margin.
- Earlier heater flags are cleared before setting new ones, so rerunning is safe.
- The margin, the periods (UTC), and the notes filename are recorded in the L05 metadata.
- Result: 2760 of 16436 one-second timesteps flagged.

The Makefile runs it after `L04-to-L05.py`, and the L05 is rebuilt when the notes file changes.

Selecting usable data:

```python
usable = L05_array[(L05_array['flags'][:, 7] & HEATER_ON) == 0]
```

### Temperature sensor swap (L0.5)

`L0-to-L04.py` can reverse a block's inboard and outboard temperature sensors. This reverses the
interpolation across the channels, and `hot_block1_temp` (used by the housekeeping flags) follows the
swap.

- Set by `SWAP_BLOCK1_TEMPS` / `SWAP_BLOCK2_TEMPS` in `L0.5/setup/parameters.sh` (1 = swapped). Both
  are currently 0, which is the hardware-doc layout.
- Overridden per run with `--swap-block1-temps` / `--no-swap-block1-temps` (and the same for block 2).
- Recorded in the metadata as `SWAP_BLOCK1_TEMPS` / `SWAP_BLOCK2_TEMPS`. A `parameters.sh` without
  these lines is treated as not swapped.

The data in `pickle/` is processed with the hardware-doc layout (no swap).

## Plotting

All scripts run from `dark_v_temp/` with the data venv active
(`. /home/steve/nothing/seastar/seastarhq/data/.venv/bin/activate`; system Python lacks `pytz`).

`plot_dark_vs_temp.py [L05 file] [-o png]` plots dark voltage against temperature for all ten
channels: block 1 (ch1–5) on the top row, block 2 (ch6–10) on the bottom.

- Each point is one L05 timestep (1 s): the mean voltage (mV) against the mean interpolated channel
  temperature.
- The startup timesteps, which log zeros for every sensor, are dropped.
- Points are shaded by time of day. Heater-on timesteps are drawn in a muted tan behind the data
  (`--exclude-heater` hides them).
- A straight-line fit is drawn on heater-off points only, and its slope is printed in µV/°C.
- `--block1-shift <s>` or `--block1-tau <s>` applies a time correction to the block 1 temperatures
  (see below).
- `--tmin <°C>` plots and fits only temperatures at or above that value. The full-range fit is drawn
  dashed for comparison, and both slopes are printed on each panel.
- `--channels <n ...>` picks the channels to plot (default all ten).

`scan_block1_shift.py [--max s] [--step s]` scans block 1 time corrections and plots the fit residual
against each (`plots/block1_shift_scan.png`).

## Findings

### Block 2 (ch6, 7, 9, 10)

The dark voltage falls cleanly and almost linearly with temperature, by −34 to −37 µV/°C. The
heater-on points sit on the same line, and the RMS scatter around the fit is 31–36 µV.

| ch6 (340) | ch7 (870) | ch9 (940/5) | ch10 (1020) |
|---|---|---|---|
| −36.67 | −36.77 | −34.13 | −37.05 |

### Ch8 (940/10 nm) looks faulty

Ch8 reads −5 to −126 mV and jumps around, while every other channel stays below about 1.5 mV. Its
fitted slope (−3755 µV/°C) is meaningless. Check the wiring or A/D input for this channel.

### Block 1 (ch1–5): sawtooth

Against the sensor temperatures, block 1 falls overall (−27.5 to −31.5 µV/°C) but in a sawtooth:

- Within each step between heater cycles, the voltage rises with temperature.
- During each heater-on period, the sensors warm by 4–5 °C with almost no change in voltage. The
  voltage drops only after the heater goes off.
- The later, warmer steps go flat at about 0 mV.

This means the diodes are not at the temperature the sensors report.

#### Swapping the sensor ends doesn't help

With block 1 swapped, the slopes changed by less than 0.35 µV/°C and the sawtooth was unchanged.

| | ch1 | ch2 | ch3 | ch4 | ch5 |
|---|---|---|---|---|---|
| hardware-doc layout | −27.99 | −28.32 | −27.48 | −29.08 | −31.46 |
| block 1 swapped | −27.70 | −28.18 | −27.48 | −29.23 | −31.78 |

The swap can't fix the sawtooth, because block 1's two sensors almost always agree:

- The outboard − inboard difference has a median of 0 °C and stays between −0.19 and +0.69 °C for 98%
  of the run (1st to 99th percentile).
- The largest difference is 0.94 °C, while the heater is on.
- Swapping moves each channel's temperature by a fraction of that, but the sawtooth steps span 4–5 °C.
- Ch3 is in the middle of the block, so it gets the average of the two sensors either way and is
  unaffected.

Block 2's sensors agree within 0.25 °C. Block 2 only reaches about 24 °C against about 39 °C for
block 1, so the heater mainly warms block 1.

#### A pure time shift helps a little

Plotting each voltage against the sensor temperature from a fixed time earlier reduces the fit scatter
by about 30%:

- The scatter falls unevenly with no clear minimum, and the bumps line up with the heater cycles.
- At 2300 s the steps become near-vertical drops, and the data above about 25 °C turns into a flat
  cloud. The slope falls to about −19 µV/°C, which reflects the broken fit rather than the diodes.

#### A first-order thermal lag fixes it

Modelling the diodes as slowly warming or cooling towards the sensor temperature cuts the scatter by
about 75%. The best time constant is about 45 min.

RMS scatter (µV) of heater-off points around the straight-line fit. The first hour is left out so
every value is scored on the same timesteps.

| | ch1 | ch2 | ch3 | ch4 | ch5 |
|---|---|---|---|---|---|
| no correction | 93.5 | 90.6 | 93.2 | 93.8 | 94.4 |
| best time shift | 64.5 (3600 s) | 64.8 (2320 s) | 62.4 (3600 s) | 66.6 (2340 s) | 72.9 (2300 s) |
| best lag | 23.7 (τ 2820 s) | 23.6 (τ 2660 s) | 23.4 (τ 2900 s) | 24.6 (τ 2680 s) | 26.2 (τ 2340 s) |

- The scan ran from 0 to 3600 s in 20 s steps. "Best time shift" values of 3600 s are the end of the
  range, not a real minimum.
- The lag has a clear minimum, consistent across all five channels.
- The scatter over all points (heater on included) is just as low, 23–26 µV. A correct model should
  also bring the heater-on points onto the line, and this one does.
- Block 1's scatter (about 24 µV) is lower than block 2's without any correction (31–36 µV), so block 2
  may lag a little too.

With τ = 2700 s (`plots/dark_vs_temp_block1_tau2700.png`), the sawtooth collapses onto a single line.
The heater-on points sit on it, and block 1 reaches only about 29 °C instead of 39 °C.

| | ch1 | ch2 | ch3 | ch4 | ch5 |
|---|---|---|---|---|---|
| slope, τ = 2700 s (µV/°C) | −25.75 | −25.89 | −25.36 | −26.61 | −28.48 |

Block 1 is still shallower than block 2 (−34 to −37 µV/°C), so the blocks have different temperature
dependence.

## The lag model

The diode temperature relaxes towards the sensor temperature at a rate proportional to the
difference, as in Newton's law of cooling:

    dT_diode/dt = (T_sensor − T_diode) / τ

After a sudden step in the sensor temperature, the diode closes 63% of the gap in τ, 86% in 2τ, and
95% in 3τ. With τ = 2700 s, 95% is reached after about 2¼ hours.

`lagged()` in `plot_dark_vs_temp.py` and `scan_block1_shift.py` steps through the one-second L05
timesteps. Over each step it applies the exact solution of that equation, holding the sensor
temperature constant within the step:

    T_diode[i] = T_diode[i−1] + (1 − exp(−Δt/τ)) · (T_sensor[i] − T_diode[i−1])

- Δt is the actual time between consecutive logged timesteps, so gaps in the data are handled.
- T_diode starts at the first logged sensor temperature. This assumes the diodes and sensors start in
  equilibrium.
- T_sensor is the channel temperature already in the L05: the straight-line interpolation between
  block 1's inboard (t3) and outboard (t5) sensors, averaged over each timestep. The lag is applied to
  each channel separately.
- τ was chosen by fitting dark voltage against the lagged temperature for each trial τ and minimising
  the RMS scatter (`scan_block1_shift.py`).

Physically, the sensors respond quickly to the heater and the diodes are thermally slower. A single τ
means one heat path between the sensor and the diode.

### Where it doesn't fit

- **Start of the run:** the first points (about 1.5 °C) curl upward above the line. The equilibrium
  starting assumption apparently didn't hold right after startup. The scan left out the first hour, so
  this stretch wasn't tested.
- **End of the run:** the last points bunch at 27–29 °C, slightly below the line. One time constant
  may not capture everything, or τ may vary a little by channel (ch5's best was about 2340 s against
  2660–2900 s for the others). A two-time-constant model, or a τ for each channel, might do better.

### Above 27 °C the dark voltage flattens

Only block 1 gets above 27 °C. Plotted against the lagged temperature (τ = 2700 s) and zoomed to
27 °C and above (`plots/dark_vs_temp_block1_tau2700_above27C.png`), the dark voltage is essentially
flat:

| slope (µV/°C) | ch1 | ch2 | ch3 | ch4 | ch5 |
|---|---|---|---|---|---|
| ≥ 27 °C | −1.77 | +1.39 | +2.63 | +2.22 | −2.50 |
| full range | −25.75 | −25.89 | −25.36 | −26.61 | −28.48 |

At the full-range slope, the voltage should drop about 45–50 µV across this 1.8 °C span. That's
detectable even with about 25 µV of point-to-point noise, given about 3500 points per channel. So the
flattening is real in the data.

It shouldn't yet be read as the diodes' behaviour above 27 °C:

- **One stretch of time:** all the data above 27 °C comes from the last hour of the run, after the
  final heater period (about 19:15 to 20:23 UTC). Over that hour the block cools slowly from 28.8 °C to
  27 °C, so temperature and time change together. Any slow drift over that hour can't be separated
  from a real temperature effect.
- **A vertical streak at 28.8 °C:** at the peak of the lagged temperature (around 19:15 UTC), the
  voltage spans about 0.1 mV while the modelled temperature barely changes. The voltage is still
  changing after the model says the diode has stopped warming. This is the end-of-run misfit noted
  under "Where it doesn't fit", and it points to the single-τ model being incomplete rather than a
  genuine flattening.
- **The same plateau without the lag:** against the uncorrected sensor temperatures, the last steps
  also go flat at about 0 mV.
- **No heater-on points:** none fall in this region.

Testing whether the voltage really levels off would need a run that holds the block at several
temperatures above 27 °C for long enough to settle, preferably reached by both heating and cooling.

## Applying the lag in reverse, for field operation

In this test the heater warms the block from the sensor side, so the diodes lag the sensors. In the
field the sun heats the diodes and front optics, so the sensors lag the diodes. The model can be
inverted, but it's much harder than the forward direction.

### The maths

With the roles swapped:

    dT_sensor/dt = (T_diode − T_sensor) / τ

Solving for the diode temperature:

    T_diode = T_sensor + τ · dT_sensor/dt

When the sensor reading is steady, the two agree. While the sun is warming the block, the diodes are
ahead of the sensor reading by τ times its rate of rise. The step-by-step version is the forward
update run backwards:

    T_diode[i] = T_sensor[i−1] + (T_sensor[i] − T_sensor[i−1]) / (1 − exp(−Δt/τ))

### Problem 1: it amplifies sensor noise

The forward lag averages noise away. The reverse multiplies it by roughly τ/Δt:

- With τ = 2700 s and 1 s steps, every sensor change is multiplied by about 2700.
- The Dallas sensors report in 0.0625 °C steps, so a single step becomes a spike of about 169 °C in
  the reconstructed diode temperature. On this run's data, the 1 s version is dominated by these
  spikes.
- The sensor rate therefore has to be smoothed over many minutes. The corrected diode temperature is
  then only valid on timescales longer than the smoothing window, so fast changes such as a passing
  cloud can't be recovered.
- Even with 10–20 min smoothing, the correction on this run is tens of °C. A quick check couldn't
  separate how much of that is noise and how much is the real heater cycling.

### Problem 2: τ from this test may not apply

- The 45 min τ describes heat flowing from the heater, past the sensors, into the diodes. In the field
  heat enters at the diodes and front optics and flows the other way. The path isn't necessarily
  symmetric, so the time constant needn't be the same.
- The single-τ model already misfits at the start and end of this run, which suggests more than one
  heat path. The inverse of an approximate model is less forgiving than the model itself.
- With the caps on, this run says nothing about solar heating.

### What would give a usable correction

- **Calibrate it in the right direction:** heat the diode/optics end of the block, with a lamp or the
  sun, while keeping it dark. Measure τ for that path and test the reverse model against the dark
  voltages, the same way the forward model was tested here.
- **Use the dark voltage as the diode thermometer:** at about −26 µV/°C for block 1 and −35 µV/°C for
  block 2, periodic darks give the actual diode temperature directly, with no lag model. Interleaving
  darks during sun tracking could check or replace the reverse model.
- **Measure the diode temperature directly:** for example, with a sensor bonded closer to the diodes.

No reverse option has been added to the scripts. On this run's data it could only show the noise
amplification, not whether the reverse model works.

## Open questions

- Block 2 reads down to about 1.3 °C and block 1 starts near 1.5 °C (its heater-off data starts
  around 6 °C). The IMU reads up to 25 °C. It was a cold day, but these readings should be confirmed.
- Ch8 hardware fault?
- Should the block 1 lag go into the L0.5 processing as a parameter (for example `BLOCK1_TAU`), like
  the swap?
- Does block 2 also benefit from a lag?
- Does the dark voltage really level off above about 27 °C, or is it time drift or lag-model error at
  the end of the run? Needs a run with settled holds above 27 °C.
- What is τ when the block is heated from the diode/optics end, as by the sun? Needed before the lag
  can be applied in reverse in the field.

## Files

| file | contents |
|---|---|
| `plots/dark_vs_temp.png` | hardware-doc layout, no correction |
| `plots/dark_vs_temp_block1_tau2700.png` | block 1 lagged, τ = 2700 s |
| `plots/dark_vs_temp_block1_tau2700_above27C.png` | block 1 lagged, τ = 2700 s, zoomed to ≥ 27 °C |
| `plots/dark_vs_temp_block1_shift2300.png` | block 1 delayed 2300 s |
| `plots/block1_shift_scan.png` | fit scatter against shift and against τ, 0–3600 s |
| `plots/dark_vs_temp_unswapped.png` | same layout as `dark_vs_temp.png`, plotted from the L05 made before the swap flags were added (that L05 has since been deleted) |

The block-1-swapped plot was overwritten when the data was reprocessed back to the hardware-doc
layout. Regenerate it with `SWAP_BLOCK1_TEMPS=1` and `make` if needed.
