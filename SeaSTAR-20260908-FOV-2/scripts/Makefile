# grid the FOV scan by stage position and draw the quicklooks: the contour and
# map plots of the field of view, and a time series of every column in the log.
#
#   make            the plots that are out of date
#   make fov        just the FOV contour and map quicklooks
#   make contours   the same, named by the plot you want
#   make maps       (one run of the script draws both, so either builds both)
#   make timeseries just the time series quicklooks, a figure per subsystem
#   make windows    redraw and open the interactive FOV figures as well
#   make show       what make thinks it is working on
#   make clean      throw away the plots
#
# the python in the venv at the top of the tree, unless told otherwise:
PYTHON ?= ../../.venv/bin/python

FOV_SCRIPT = ./processFov.py
TS_SCRIPT = ./plotTimeseries.py

RAW_DIR = ../raw
PLOTS_DIR = ../plots

# the scan log, and the test notes the centre below was read out of:
LOG ?= $(lastword $(sort $(wildcard $(RAW_DIR)/*log.csv)))
NOTES = $(wildcard $(RAW_DIR)/notes*.txt)

# 2026-09-08_11-03-43_log.csv -> 2026-09-08_11-03-43_log, which is the stem the
# script names its output files after:
STEM = $(basename $(notdir $(LOG)))

# the centre the scan was run about, from notes or the global config file.  the centre the
# scan finds is printed as "Averaged center" and is not this:
XCENT ?= 0.50905
YCENT ?= 0.51751

# the scan stepped 0.02 in x and 0.03 in y, so binning any finer than the x step
# leaves most of the grid empty and breaks the spot into isolated columns:
DELTA_STEP ?= 0.009

# rows to drop while the stage is still settling at the start of the log:
START_LOG ?= 10

# grid cells below this fraction of a channel's own peak are masked off:
FRAC ?= 0.05

# channels to process, all of them when empty.  8 and 9 are ~200x weaker than
# the rest and are byte-identical to each other in the raw log -- a logger fault
# seen on 2026-09-07 too, not an artefact of processing -- so they contribute
# noise to the averaged centre and are dropped by default.  CHANNELS= (empty)
# puts them back when you want to look at them:
CHANNELS ?= 1-7,10

ifneq ($(strip $(CHANNELS)),)
CHANNEL_FLAG = --channels $(CHANNELS)
endif

# make never wants the blocking figure windows; the windows target overrides it:
SHOW_FLAG ?= --no-show

# scale each time series panel to all its data, spikes included, when set:
FULL_RANGE ?=

CONTOURS = $(PLOTS_DIR)/$(STEM)_fov_contours.png
MAPS = $(PLOTS_DIR)/$(STEM)_fov_maps.png

FOV_PLOTS = $(CONTOURS) $(MAPS)

# which time series figures there are depends on what columns the log carries,
# so they are tracked by a stamp rather than named one by one here:
TS_STAMP = $(PLOTS_DIR)/.$(STEM)_ts.stamp
TS_PLOTS = $(PLOTS_DIR)/$(STEM)_ts_*.png

all: fov timeseries

fov: $(FOV_PLOTS)

contours: $(CONTOURS)

maps: $(MAPS)

timeseries: $(TS_STAMP)

# the centre comes out of the notes, so they are a dependency too.  one run of
# the script draws both plots, hence the grouped target:
$(FOV_PLOTS) &: $(LOG) $(NOTES) $(FOV_SCRIPT)
	$(PYTHON) $(FOV_SCRIPT) $(LOG) \
		--start-log $(START_LOG) \
		--delta-step $(DELTA_STEP) \
		--xcent $(XCENT) --ycent $(YCENT) \
		--frac $(FRAC) $(CHANNEL_FLAG) \
		--outdir $(PLOTS_DIR) $(SHOW_FLAG)

# every column in the log, whether or not it is named in the script's groups:
$(TS_STAMP): $(LOG) $(TS_SCRIPT)
	$(PYTHON) $(TS_SCRIPT) $(LOG) \
		--start-log $(START_LOG) \
		--outdir $(PLOTS_DIR) $(FULL_RANGE)
	@touch $@

# for looking at the scan by hand: always redraw, and leave the windows open.
windows:
	@$(MAKE) --always-make SHOW_FLAG= fov

clean:
	rm -f $(FOV_PLOTS) $(TS_PLOTS) $(TS_STAMP)

# what make thinks it is working on, when the filenames look wrong:
show:
	@echo "log:        $(LOG)"
	@echo "stem:       $(STEM)"
	@echo "centre:     $(XCENT), $(YCENT)"
	@echo "delta step: $(DELTA_STEP)"
	@echo "channels:   $(if $(strip $(CHANNELS)),$(CHANNELS),all)"
	@echo "fov plots:  $(FOV_PLOTS)"
	@echo "ts plots:   $(TS_PLOTS)"

.PHONY: all fov contours maps timeseries windows clean show
