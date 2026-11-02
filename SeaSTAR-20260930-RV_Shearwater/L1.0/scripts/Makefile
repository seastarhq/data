# runs to process, named by the date and time in the raw logfile name, <date>_<time>_log.csv
# add more runs separated by spaces
RAWFILES=2026-09-30_07-08-47 2026-09-30_07-11-02 2026-09-30_09-03-17 2026-09-30_09-32-14

SCRIPTS=./L06-to-L10_sun.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_atmosphere.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
# calibration.sh is written by calibration_vs_ref/scripts/write_v0_params.py
PARAMFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh ../setup/calibration.sh

PICKLE=../../pickle

# make runs each recipe line in its own /bin/sh, so the setup files are sourced (with . not source)
# on the same line as the script that needs them
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; . ../setup/calibration.sh;

# `make V0_MODE=origin` (or intercept) processes with that V0 calibration instead of parameters.sh's, into
# SeaSTAR_<run>_v0<mode>.L10 beside the usual SeaSTAR_<run>.L10, so the two can be compared
L10_TAG=$(if $(V0_MODE),_v0$(V0_MODE))
L10_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%$(L10_TAG).L10)

# the AOD plot (plot_aod.py): every run on one figure, at AOD_PLOT_NM
AOD_PLOT_NM ?= 500
# the aod_flags that screen it (plot_aod.py --screen: cloud tracking temp_low pressure position signal_low)
AOD_PLOT_SCREEN ?= tracking
# other plot_aod.py options: the axis limits, leaving out the timesteps where the AOD is undefined,
# and leaving out the timesteps with bad tracking entirely
AOD_PLOT_OPTIONS ?= --ymax 0.3 --xmin 10:30 --hide-undefined --tracked-only
AOD_PLOT=../plots/aod_$(AOD_PLOT_NM)nm$(L10_TAG).stamp
# overlaid with the campaign's Microtops L1.5 groups file, if there is one
MICROTOPS=$(firstword $(wildcard ../../microtops/*_L15_groups_*.txt))

all: $(L10_FILES) plots

plots: $(AOD_PLOT)

L10: $(L10_FILES)

# the L06 is made by the L0.6 Makefile, in ../../L0.6/scripts
$(PICKLE)/SeaSTAR_%$(L10_TAG).L10: $(PICKLE)/SeaSTAR_%.L06 $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing L06 to L10 $@
	$(SETUP) ./L06-to-L10_sun.py $(notdir $<) --outputfile $(notdir $@) $(if $(V0_MODE),--v0-mode $(V0_MODE))

# the plot is named after the date in the data, so it's tracked by a stamp
$(AOD_PLOT): $(L10_FILES) ./plot_aod.py $(MODULES) $(PARAMFILES) $(MICROTOPS)
	$(SETUP) ./plot_aod.py $(notdir $(L10_FILES)) --nm $(AOD_PLOT_NM) --screen $(AOD_PLOT_SCREEN) $(AOD_PLOT_OPTIONS) $(if $(MICROTOPS),--microtops $(MICROTOPS))
	@touch $@

.DELETE_ON_ERROR:

.PHONY: all L10 plots
