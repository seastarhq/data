# make the pickled 1-second averages from the raw Hamburger data, and the
# quicklook plots from that pickle.
#
#   make               everything that is out of date
#   make pickle        just the 1-second averages
#   make timeseries    just the time series quicklooks
#   make vs-temperature just the channels against block temperature
#   make cooling       the same, fitted over the cooling leg only
#   make fits          just the table of fitted temperature slopes
#   make clean         throw away the plots, the fits and the pickle
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

# the raw data, either as one file or as the split parts, and the test notes:
RAWFILES = $(wildcard $(RAW_DIR)/HamburgerData_*)
NOTES = $(wildcard $(RAW_DIR)/notes*.txt)

# HamburgerData_2026_08_18_10_58_58.txt-raw... -> HamburgerData_2026_08_18_10_58_58
NAME = $(firstword $(subst ., ,$(notdir $(firstword $(RAWFILES)))))
# ...and the date out of the middle of that, for the plot filenames:
DATE = $(subst $() $(),_,$(wordlist 2,4,$(subst _, ,$(NAME))))

PICKLE = $(PICKLE_DIR)/$(NAME)_$(INTERVAL)avg.pkl

TIMESERIES = $(PLOTS_DIR)/temperatures_$(DATE).png \
	     $(PLOTS_DIR)/channels_gain0_$(DATE).png \
	     $(PLOTS_DIR)/channels_gain2_$(DATE).png

VS_TEMPERATURE = $(foreach gain,$(GAINS),\
		   $(PLOTS_DIR)/channels_gain$(gain)_vs_temperature_$(DATE).png)

# the heater goes off at 11:10, so from there on the instrument is cooling
# steadily and the channels can be fitted against temperature without the
# hysteresis of the heating leg:
COOLING_START ?= 11:10

COOLING = $(foreach gain,$(GAINS),\
	    $(PLOTS_DIR)/channels_gain$(gain)_vs_temperature_$(DATE)_cooling.png)

# both legs write their slopes against Temp3 into the one table, a row per
# channel per gain per leg, so the cooling fit can be read against the whole
# run without opening two files:
FITS = $(ROOT_DIR)/fit_coefficients.txt

all: timeseries vs-temperature cooling fits

pickle: $(PICKLE)

timeseries: $(TIMESERIES)

vs-temperature: $(VS_TEMPERATURE)

cooling: $(COOLING)

fits: $(FITS)

# the flags in the pickle come from the notes, so they are a dependency too:
$(PICKLE): $(RAWFILES) $(NOTES) ./raw_to_pickle.py
	mkdir -p $(PICKLE_DIR)
	$(PYTHON) ./raw_to_pickle.py --interval $(INTERVAL) --outputfile $@

# one run of the script draws all three of these, hence the grouped target:
$(TIMESERIES) &: $(PICKLE) ./plot_timeseries.py
	$(PYTHON) ./plot_timeseries.py $(PICKLE) --outdir $(PLOTS_DIR)

# this is a dark test: the lamp was off for the whole run, so the lamp-off
# samples are the measurement rather than something to leave out.
#
# every gain and both legs go in the one grouped rule, so that the table of
# coefficients they share is written by a single recipe: several rules writing
# it would race under make -j, and the table could not then be asked for on
# its own.
$(VS_TEMPERATURE) $(COOLING) $(FITS) &: $(PICKLE) ./plot_vs_temperature.py
	rm -f $(FITS)
	for gain in $(GAINS); do \
		$(PYTHON) ./plot_vs_temperature.py $(PICKLE) --gain $$gain \
			--keep-lamp-off --outdir $(PLOTS_DIR) \
			--fit-file $(FITS) || exit 1; \
		$(PYTHON) ./plot_vs_temperature.py $(PICKLE) --gain $$gain \
			--keep-lamp-off --start $(COOLING_START) --tag _cooling \
			--outdir $(PLOTS_DIR) --fit-file $(FITS) || exit 1; \
	done

clean:
	rm -f $(TIMESERIES) $(VS_TEMPERATURE) $(COOLING) $(FITS) $(PICKLE)

# what make thinks it is working on, when the filenames look wrong:
show:
	@echo "raw files: $(RAWFILES)"
	@echo "name:      $(NAME)"
	@echo "date:      $(DATE)"
	@echo "pickle:    $(PICKLE)"
	@echo "plots:     $(TIMESERIES) $(VS_TEMPERATURE) $(COOLING)"
	@echo "fits:      $(FITS)"

.PHONY: all pickle timeseries vs-temperature cooling fits clean show
