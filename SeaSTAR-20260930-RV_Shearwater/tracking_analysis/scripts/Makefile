# runs to analyse, named by the date and time in the raw logfile name, <date>_<time>_log.csv
# add more runs separated by spaces
RAWFILES=2026-09-30_07-08-47 2026-09-30_07-11-02 2026-09-30_09-03-17 2026-09-30_09-32-14

SCRIPTS=./tracking_stats.py
MODULES=./seastar_error_flags.py
PARAMFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh

PICKLE=../../pickle
STATS=../stats

# make runs each recipe line in its own /bin/sh, so the setup files are sourced (with . not source)
# on the same line as the script that needs them
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh;

L05_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%.L05)
L06_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%.L06)

# a closer look at part of a run: the plots limited to the window, named after it. here the clear
# sky of the afternoon of the 09-32-14 run. ZOOM_START and ZOOM_END are local times, HH:MM, and either
# can be left empty to run from the start or to the end
ZOOM_RUN=2026-09-30_09-32-14
ZOOM_START=13:35
ZOOM_END=
PLOTS=../plots
ZOOM_NAME=$(ZOOM_RUN)_$(if $(ZOOM_START),$(subst :,,$(ZOOM_START)),start)-$(if $(ZOOM_END),$(subst :,,$(ZOOM_END)),end)
ZOOM_PLOTS=$(foreach p,tracking ch_mean ch_relstd ch_relstd_onecolour,$(PLOTS)/SeaSTAR_$(ZOOM_NAME)_$(p).png)

all: $(STATS)/SeaSTAR_allruns_tracking_summary.csv zoom

zoom: $(ZOOM_PLOTS)

# the L05 and L06 are made by the Makefiles in ../../L0.5/scripts and ../../L0.6/scripts
# all the runs go through in one call, so the pooled summary covers them all
$(STATS)/SeaSTAR_allruns_tracking_summary.csv: $(L05_FILES) $(L06_FILES) $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo analysing tracking for $(RAWFILES)
	$(SETUP) ./tracking_stats.py $(RAWFILES)

$(ZOOM_PLOTS) &: $(PICKLE)/SeaSTAR_$(ZOOM_RUN).L05 $(PICKLE)/SeaSTAR_$(ZOOM_RUN).L06 $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo plotting $(ZOOM_RUN) from $(or $(ZOOM_START),the start) to $(or $(ZOOM_END),the end)
	$(SETUP) ./tracking_stats.py $(ZOOM_RUN) $(if $(ZOOM_START),--start $(ZOOM_START)) $(if $(ZOOM_END),--end $(ZOOM_END))

.PHONY: all zoom
