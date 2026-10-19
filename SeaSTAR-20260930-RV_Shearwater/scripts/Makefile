# quicklooks of the day's raw logs, all of them on the one time axis: a time
# series of every column, the sun tracking, the channels while tracking, and
# the ship track.  every plot is written as a PNG and a PDF.
#
#   make            the plots that are out of date
#   make timeseries just the time series quicklooks, a figure per subsystem
#   make tracking   spot against target, tracking error, state and settings
#   make channels   the radiometer channels while sun tracking
#   make map        the ship track on the coastline
#   make zoom START=13:29 END=14:29
#                   all of the above for a window of the day, always redrawn
#   make darks      zoom on each of the dark sequences in DARKS, one run of
#                   zoom per sequence (make -j4 darks runs them side by side)
#   make dark-levels
#                   the dark level of each channel at each sequence in DARKS,
#                   against time and against DARK_TEMPERATURE, with a table of
#                   the levels and one of the fitted slopes
#   make logs       just reassemble the logs from their split parts
#   make show       what make thinks it is working on
#   make clean      throw away the plots
#
# the python in the venv at the top of the tree, which has pandas, matplotlib
# and cartopy, unless told otherwise:
PYTHON ?= $(abspath ../../../bin/python)

RAW_DIR = ../raw
PLOTS_DIR = ../plots

# the logs are kept in git as split parts; they are reassembled by the Makefile
# in ../raw, so the list comes from the parts rather than the assembled files:
ALL_LOGS = $(patsubst %_part_00,%,$(wildcard $(RAW_DIR)/*_log.csv_part_00))

# 2026-09-30_07-11-02_log.csv runs for 97 s inside the 07:08 log, which logs
# straight through it, and the two disagree: a fixed position at the dock
# (34.4087 N) and the spot sitting on the target against the ship under way.
# put together they would interleave, so it is left out of the day unless
# EXCLUDE is set to something else:
EXCLUDE ?= 2026-09-30_07-11-02_log.csv

LOGS = $(filter-out $(addprefix $(RAW_DIR)/,$(EXCLUDE)),$(ALL_LOGS))

# rows to drop at the start of each log, while it is starting up:
START_LOG ?= 10

# scale each time series and channel panel to all its data, spikes included,
# when set to --full-range:
FULL_RANGE ?=

DAY = $(firstword $(subst _, ,$(notdir $(firstword $(LOGS)))))

COMMON = ./quicklook.py
FLAGS = --start-log $(START_LOG) --outdir $(PLOTS_DIR)

TRACKING = $(PLOTS_DIR)/$(DAY)_tracking.png $(PLOTS_DIR)/$(DAY)_tracking.pdf
CHANNELS = $(PLOTS_DIR)/$(DAY)_channels_tracking.png $(PLOTS_DIR)/$(DAY)_channels_tracking.pdf
MAP = $(PLOTS_DIR)/$(DAY)_track_map.png $(PLOTS_DIR)/$(DAY)_track_map.pdf

# which time series figures there are depends on what columns the logs carry,
# so they are tracked by a stamp rather than named one by one here:
TS_STAMP = $(PLOTS_DIR)/.$(DAY)_ts.stamp
TS_PLOTS = $(PLOTS_DIR)/$(DAY)_ts_*.png $(PLOTS_DIR)/$(DAY)_ts_*.pdf

all: timeseries tracking channels map dark-levels

logs: $(LOGS)

timeseries: $(TS_STAMP)

tracking: $(TRACKING)

channels: $(CHANNELS)

map: $(MAP)

# reassembled whenever a part is newer than the log; -B because the rule in
# ../raw has no prerequisites and would otherwise call an old log up to date:
$(RAW_DIR)/%_log.csv: $(RAW_DIR)/%_log.csv_part_00
	$(MAKE) -C $(RAW_DIR) -B $(notdir $@)

$(TS_STAMP): $(LOGS) ./plotTimeseries.py $(COMMON)
	mkdir -p $(PLOTS_DIR)
	$(PYTHON) ./plotTimeseries.py $(LOGS) $(FLAGS) $(FULL_RANGE)
	@touch $@

# the states are named on the plot from ../setup/states:
$(TRACKING) &: $(LOGS) ./plotTracking.py $(COMMON) ../setup/states
	$(PYTHON) ./plotTracking.py $(LOGS) $(FLAGS)

$(CHANNELS) &: $(LOGS) ./plotChannels.py $(COMMON)
	$(PYTHON) ./plotChannels.py $(LOGS) $(FLAGS) $(FULL_RANGE)

$(MAP) &: $(LOGS) ./plotTrackMap.py $(COMMON)
	$(PYTHON) ./plotTrackMap.py $(LOGS) $(FLAGS)

# a window of the day; the scripts name these plots after the window, so they
# sit beside the whole-day ones rather than replacing them:
START ?=
END ?=
WINDOW = $(if $(START),--start $(START)) $(if $(END),--end $(END))

zoom: $(LOGS)
	@[ -n "$(START)$(END)" ] || { echo "zoom wants START= and/or END="; exit 1; }
	$(PYTHON) ./plotTimeseries.py $(LOGS) $(FLAGS) $(WINDOW) $(FULL_RANGE)
	$(PYTHON) ./plotTracking.py $(LOGS) $(FLAGS) $(WINDOW)
	$(PYTHON) ./plotChannels.py $(LOGS) $(FLAGS) $(WINDOW) $(FULL_RANGE)
	$(PYTHON) ./plotTrackMap.py $(LOGS) $(FLAGS) $(WINDOW)

# the dark sequences, each channel darkened in turn from ch10 down to ch1 while
# the instrument went on sun tracking (state 2), so no state marks them.  the
# notes give them to the minute; these are where the channels are seen to drop
# out one after another, with half a minute either side.  the 11:31 and 13:05
# sequences were taken under cloud and can not be told apart from it in the
# signal, so their windows are the notes' times, widened.  written with dots
# for the colons, which make will not have in a target name:
DARKS ?= 11.02.00-11.04.30 \
	 11.30.00-11.35.00 \
	 13.04.00-13.09.00 \
	 14.24.20-14.26.40 \
	 14.58.40-15.00.50 \
	 15.20.00-15.22.20 \
	 15.36.15-15.38.30

darks: $(addprefix dark-,$(DARKS))

# the darks are picked out of each window by the order the channels go dark in,
# so a window only has to hold the whole of one sequence:
# the temperature the darks are plotted and fitted against:
DARK_TEMPERATURE ?= t3

DARK_LEVELS = $(PLOTS_DIR)/$(DAY)_dark_levels.png $(PLOTS_DIR)/$(DAY)_dark_levels.pdf \
	      $(PLOTS_DIR)/$(DAY)_dark_vs_$(DARK_TEMPERATURE).png \
	      $(PLOTS_DIR)/$(DAY)_dark_vs_$(DARK_TEMPERATURE).pdf
DARK_TABLE = $(PLOTS_DIR)/$(DAY)_dark_levels.txt
DARK_FITS = $(PLOTS_DIR)/$(DAY)_dark_vs_$(DARK_TEMPERATURE)_fits.txt

dark-levels: $(DARK_LEVELS)

$(DARK_LEVELS) $(DARK_TABLE) $(DARK_FITS) &: $(LOGS) ./plotDarks.py $(COMMON)
	mkdir -p $(PLOTS_DIR)
	$(PYTHON) ./plotDarks.py $(LOGS) $(FLAGS) --windows $(DARKS) \
		--table $(DARK_TABLE) \
		--temperature $(DARK_TEMPERATURE) --fit-file $(DARK_FITS)

dark-%: $(LOGS)
	$(MAKE) zoom START=$(subst .,:,$(word 1,$(subst -, ,$*))) \
		END=$(subst .,:,$(word 2,$(subst -, ,$*)))

clean:
	rm -f $(TS_PLOTS) $(TS_STAMP) $(TRACKING) $(CHANNELS) $(MAP) $(DARK_LEVELS) $(DARK_TABLE) $(DARK_FITS)

# what make thinks it is working on, when the filenames look wrong:
show:
	@echo "python:   $(PYTHON)"
	@echo "logs:     $(LOGS)"
	@echo "excluded: $(EXCLUDE)"
	@echo "day:      $(DAY)"
	@echo "darks:    $(subst .,:,$(DARKS))"
	@echo "plots:    $(TRACKING) $(CHANNELS) $(MAP) $(TS_PLOTS)"

.PHONY: all logs timeseries tracking channels map zoom darks dark-levels clean show
