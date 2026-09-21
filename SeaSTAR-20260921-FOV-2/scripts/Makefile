# grid the FOV scan by stage position and draw the quicklooks: the contour and
# map plots of the field of view, and a time series of every column in the log.
#
#   make            the plots that are out of date
#   make fov        just the FOV plots: contours, maps and the fitted centre
#   make contours   the contour and map quicklooks, named by the plot you want
#   make maps       (one run of the script draws both, so either builds both)
#   make fit        the FOV gridded on the commanded position, with a fitted
#                   centre per channel: the number to take the centre from
#   make cuts       x and y cross-sections through the centre at the scan step
#   make timeseries just the time series quicklooks, a figure per subsystem
#   make windows    redraw and open the interactive FOV figures as well
#   make show       what make thinks it is working on
#   make clean      throw away the plots
#
# the python in the venv at the top of the tree, unless told otherwise:
PYTHON ?= ../../.venv/bin/python

FOV_SCRIPT = ./processFov.py
FIT_SCRIPT = ./fitFov.py
CUT_SCRIPT = ./cutFov.py
TS_SCRIPT = ./plotTimeseries.py

RAW_DIR = ../raw
PLOTS_DIR = ../plots

# the scan log, and the test notes the centre below was read out of:
LOG ?= $(lastword $(sort $(wildcard $(RAW_DIR)/*log.csv)))
NOTES = $(wildcard $(RAW_DIR)/notes*.txt)

# 2026-09-14_15-23-55_log.csv -> 2026-09-14_15-23-55_log, which is the stem the
# script names its output files after:
STEM = $(basename $(notdir $(LOG)))

# the centre the scan was run about, from notes_20260921.txt (14:33): the
# second scan of the day, re-centred on what the 13:28 scan found.  the centre
# this scan finds is printed as "Averaged center"/"Fitted centre" and is not
# this:
XCENT ?= 0.5472
YCENT ?= 0.5357

# the 14:33 scan stepped 0.004 in x and 0.006 in y (xRange 0.04, yRange 0.06,
# 21 points each), finer than the 13:28 one.  binning finer than the coarser of
# the two leaves most of the grid empty and breaks the spot into isolated
# columns, so this wants to be >= the y step; the centre this plot prints moves
# with it either way, which is why the fit target, not this one, is the number
# to quote:
DELTA_STEP ?= 0.006

# rows to drop at the start of the log.  this log opens with 131 rows of zeros
# (state 0, commanded position 0,0) before the scan starts; left in, they add a
# stray row and column at 0 to the commanded-position grid:
START_LOG ?= 140

# grid cells below this fraction of a channel's own peak are masked off:
FRAC ?= 0.05

# channels to process, all of them when empty.  all ten carry signal in this
# run; ch6 is ~7x weaker than ch4 but still fits cleanly, and ch8 has a baseline
# that wanders over 30% of its own peak: set CHANNELS=1-7,9,10 to drop ch8.
CHANNELS ?=

ifneq ($(strip $(CHANNELS)),)
CHANNEL_FLAG = --channels $(CHANNELS)
endif

# channels still fitted and drawn but left out of the averaged centre.  in the
# 2026-09-17 logs 8 and 9 were the same column twice and 9 was excluded so it
# would not count double; from 2026-09-21 they are separate channels again, so
# nothing is excluded by default:
EXCLUDE ?=

ifneq ($(strip $(EXCLUDE)),)
EXCLUDE_FLAG = --exclude $(EXCLUDE)
endif

# half-width of the fit plot's window about the centre, the whole scan when
# empty.  the scan range is ~3x the spot, so a window shows it better:
WINDOW ?= 0.035

ifneq ($(strip $(WINDOW)),)
WINDOW_FLAG = --window $(WINDOW)
endif

# how far a sample may sit from the commanded position and still be counted as
# settled at that grid point.  it has to clear the stage's steady-state error:
# in this scan the stage parked a median 0.0009 from where it was told to go
# (+0.0003 in x, ~0 in y), well inside the scripts' own 0.002 default, unlike
# the 13:28 scan where it sat 0.0034 off.  0.003 keeps a margin without
# reaching the next x point at 0.004:
SETTLE ?= 0.003

# rows/columns either side of the centre cut drawn faintly behind it, and the
# fraction of peak above background that counts as signal when trimming the
# cross-section plots to the spot:
NEIGHBOURS ?= 2
CUT_FLOOR ?= 0.01

# make never wants the blocking figure windows; the windows target overrides it:
SHOW_FLAG ?= --no-show

# scale each time series panel to all its data, spikes included, when set:
FULL_RANGE ?=

CONTOURS = $(PLOTS_DIR)/$(STEM)_fov_contours.png
MAPS = $(PLOTS_DIR)/$(STEM)_fov_maps.png

FIT = $(PLOTS_DIR)/$(STEM)_fov_fit.png
CUTS = $(PLOTS_DIR)/$(STEM)_fov_cuts.png

FOV_PLOTS = $(CONTOURS) $(MAPS) $(FIT) $(CUTS)

# which time series figures there are depends on what columns the log carries,
# so they are tracked by a stamp rather than named one by one here:
TS_STAMP = $(PLOTS_DIR)/.$(STEM)_ts.stamp
TS_PLOTS = $(PLOTS_DIR)/$(STEM)_ts_*.png

all: fov timeseries

fov: $(FOV_PLOTS)

contours: $(CONTOURS)

maps: $(MAPS)

fit: $(FIT)

cuts: $(CUTS)

timeseries: $(TS_STAMP)

# the centre comes out of the notes, so they are a dependency too.  one run of
# the script draws both plots, hence the grouped target:
$(CONTOURS) $(MAPS) &: $(LOG) $(NOTES) $(FOV_SCRIPT)
	$(PYTHON) $(FOV_SCRIPT) $(LOG) \
		--start-log $(START_LOG) \
		--delta-step $(DELTA_STEP) \
		--xcent $(XCENT) --ycent $(YCENT) \
		--frac $(FRAC) $(CHANNEL_FLAG) \
		--outdir $(PLOTS_DIR) $(SHOW_FLAG)

# gridded on the commanded position instead, so no bin step is needed; the
# centre from the notes is only drawn for reference:
$(FIT): $(LOG) $(NOTES) $(FIT_SCRIPT)
	$(PYTHON) $(FIT_SCRIPT) $(LOG) \
		--start-log $(START_LOG) \
		--xcent $(XCENT) --ycent $(YCENT) --settle $(SETTLE) \
		$(CHANNEL_FLAG) $(EXCLUDE_FLAG) $(WINDOW_FLAG) \
		--outdir $(PLOTS_DIR) $(SHOW_FLAG)

# the cut goes through the centroid the script finds itself, not the centre
# from the notes, so the notes are not a dependency here:
$(CUTS): $(LOG) $(CUT_SCRIPT)
	$(PYTHON) $(CUT_SCRIPT) $(LOG) \
		--start-log $(START_LOG) \
		--neighbours $(NEIGHBOURS) --floor $(CUT_FLOOR) --settle $(SETTLE) \
		$(CHANNEL_FLAG) \
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
	@echo "excluded:   $(if $(strip $(EXCLUDE)),$(EXCLUDE),none)"
	@echo "settle:     $(SETTLE)"
	@echo "fov plots:  $(FOV_PLOTS)"
	@echo "ts plots:   $(TS_PLOTS)"

.PHONY: all fov contours maps fit cuts timeseries windows clean show
