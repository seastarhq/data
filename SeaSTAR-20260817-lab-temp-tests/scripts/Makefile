# make the pickled 1-second averages from the raw Hamburger data, and the
# quicklook plots from that pickle.
#
#   make            everything that is out of date
#   make pickle     just the 1-second averages
#   make timeseries just the time series quicklooks
#   make fits       just the table of fitted temperature slopes
#   make clean      throw away the plots, the fits and the pickle
#
# the python in the venv at the top of the data tree, unless told otherwise:
PYTHON ?= ../../.venv/bin/python

ROOT_DIR = ..
RAW_DIR = ../raw
PICKLE_DIR = ../pickle
PLOTS_DIR = ../plots

INTERVAL ?= 1s

# the gain settings the channels were read at, plotted and fitted one at a time:
GAINS = 0 2

SCRIPTS = ./raw_to_pickle.py ./plot_timeseries.py ./plot_vs_temperature.py

# the raw data, either as one file or as the split parts, and the test notes:
RAWFILES = $(wildcard $(RAW_DIR)/HamburgerData_*)
NOTES = $(wildcard $(RAW_DIR)/notes*.txt)

# HamburgerData_2026_08_17_12_23_41.txt-raw... -> HamburgerData_2026_08_17_12_23_41
NAME = $(firstword $(subst ., ,$(notdir $(firstword $(RAWFILES)))))
# ...and the date out of the middle of that, for the plot filenames:
DATE = $(subst $() $(),_,$(wordlist 2,4,$(subst _, ,$(NAME))))

PICKLE = $(PICKLE_DIR)/$(NAME)_$(INTERVAL)avg.pkl

TIMESERIES = $(PLOTS_DIR)/temperatures_$(DATE).png \
	     $(PLOTS_DIR)/channels_gain0_$(DATE).png \
	     $(PLOTS_DIR)/channels_gain2_$(DATE).png

VS_TEMPERATURE = $(foreach gain,$(GAINS),\
		   $(PLOTS_DIR)/channels_gain$(gain)_vs_temperature_$(DATE).png)

# the same runs write the slopes fitted against Temp3, one table with a row per
# channel: each run rewrites its own gain and leaves the rows for the others be:
FITS = $(ROOT_DIR)/fit_coefficients.txt

all: timeseries vs-temperature fits

pickle: $(PICKLE)

timeseries: $(TIMESERIES)

vs-temperature: $(VS_TEMPERATURE)

fits: $(FITS)

# the flags in the pickle come from the notes, so they are a dependency too:
$(PICKLE): $(RAWFILES) $(NOTES) ./raw_to_pickle.py
	mkdir -p $(PICKLE_DIR)
	$(PYTHON) ./raw_to_pickle.py --interval $(INTERVAL) --outputfile $@

# one run of the script draws all three of these, hence the grouped target:
$(TIMESERIES) &: $(PICKLE) ./plot_timeseries.py
	$(PYTHON) ./plot_timeseries.py $(PICKLE) --outdir $(PLOTS_DIR)

# every gain in one grouped rule, so that the table of coefficients they share
# is written by a single recipe: two rules writing it would race under make -j,
# and the table could not then be asked for on its own.
$(VS_TEMPERATURE) $(FITS) &: $(PICKLE) ./plot_vs_temperature.py
	rm -f $(FITS)
	for gain in $(GAINS); do \
		$(PYTHON) ./plot_vs_temperature.py $(PICKLE) --gain $$gain \
			--outdir $(PLOTS_DIR) --fit-file $(FITS) || exit 1; \
	done

clean:
	rm -f $(TIMESERIES) $(VS_TEMPERATURE) $(FITS) $(PICKLE)

# what make thinks it is working on, when the filenames look wrong:
show:
	@echo "raw files: $(RAWFILES)"
	@echo "name:      $(NAME)"
	@echo "date:      $(DATE)"
	@echo "pickle:    $(PICKLE)"
	@echo "plots:     $(TIMESERIES) $(VS_TEMPERATURE)"
	@echo "fits:      $(FITS)"

.PHONY: all pickle timeseries vs-temperature fits clean show
