# runs to process, named by the date and time in the raw logfile name, <date>_<time>_log.csv
# add more runs separated by spaces
RAWFILES=2026-09-22_12-10-16

SCRIPTS=./L05-to-L06_sun.py ./channel_temp_screen.py ./tripletvar_screen.py ./dark_subtraction.py ./temp_correction.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh

PICKLE=../../pickle

# make runs each recipe line in its own /bin/sh, so the setup files are sourced (with . not source)
# on the same line as the script that needs them
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh;

L06_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%.L06)

all: $(L06_FILES)

L06: $(L06_FILES)

# the L05 is made by the L0.5 Makefile, in ../../L0.5/scripts
# the screening and correction scripts update the L06 in place
$(PICKLE)/SeaSTAR_%.L06: $(PICKLE)/SeaSTAR_%.L05 $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing L05 to L06 $@
	$(SETUP) ./L05-to-L06_sun.py $(notdir $<) --outputfile $(notdir $@)
	$(SETUP) ./channel_temp_screen.py $(notdir $@)
	$(SETUP) ./tripletvar_screen.py $(notdir $@)
	$(SETUP) ./dark_subtraction.py $(notdir $@)
	$(SETUP) ./temp_correction.py $(notdir $@)

# if a screening or correction step fails, don't leave a half-processed L06 that looks up to date
.DELETE_ON_ERROR:

.PHONY: all L06
