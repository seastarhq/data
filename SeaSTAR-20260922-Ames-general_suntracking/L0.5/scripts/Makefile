# runs to process, named by the date and time in the raw logfile name, <date>_<time>_log.csv
# add more runs separated by spaces
RAWFILES=2026-09-22_12-10-16

SCRIPTS=./L0-to-L04.py ./L04-to-L05.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh

RAW=../../raw
PICKLE=../../pickle

# make runs each recipe line in its own /bin/sh, so the setup files are sourced (with . not source)
# on the same line as the script that needs them
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh;

L04_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%.L04)
L05_FILES=$(RAWFILES:%=$(PICKLE)/SeaSTAR_%.L05)

all: $(L05_FILES)

L04: $(L04_FILES)

L05: $(L05_FILES)

$(PICKLE)/SeaSTAR_%.L05: $(PICKLE)/SeaSTAR_%.L04 $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing L04 to L05 $@
	$(SETUP) ./L04-to-L05.py $(notdir $<) --outputfile $(notdir $@)

$(PICKLE)/SeaSTAR_%.L04: $(RAW)/%_log.csv $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing csv to L04 $@
	$(SETUP) ./L0-to-L04.py $(notdir $<) --outputfile $(notdir $@)

# the raw logfiles are too big for github, so they are stored as parts and reconstructed here
$(RAW)/%_log.csv:
	echo reconstructing $@
	cat $@_part_?? > $@

# otherwise make deletes the reconstructed csv after using it, since it is an intermediate file
.PRECIOUS: $(RAW)/%_log.csv

.PHONY: all L04 L05
