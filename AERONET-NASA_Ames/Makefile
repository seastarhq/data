# read the AERONET 905 csv for a month, temperature-correct the V columns and
# save them in the same npz layout as the SeaSTAR L0.6 files.
#
#   make            the corrected npz and its plots, if they are out of date
#   make npz        just the corrected npz
#   make plots      time series of the voltages, temperature, geometry, aod,
#                   water vapor and alpha, written to $(MONTH)/plots
#   make windows    redraw the plots and open them as figures as well
#   make show       what make thinks it is working on
#   make clean      throw away the npz and the plots
#
#   make MONTH=202507   another month's directory (it needs its own
#                       calibrs_for_905.txt)
#
# the python in the venv at the top of the tree, unless told otherwise:
PYTHON ?= ../.venv/bin/python

SCRIPT = ./read_aeronet_tempcorr.py
PLOT_SCRIPT = ./plot_aeronet_tempcorr.py
# the csv parser the script imports:
LIB = ./read_aeronet.py

MONTH ?= 202609

CSV = $(MONTH)/NASA_Ames_905_raw_and_aod.csv
CALIB = $(MONTH)/calibrs_for_905.txt
OUT = $(MONTH)/NASA_Ames_905_raw_and_aod_tempcorr.npz

# observation type (sun, moon or both) and the levels to keep, as the script's
# own defaults:
TYPE ?= sun
LEVELS ?= L1.5V

PLOTS_DIR = $(MONTH)/plots
# the script writes <npz stem>_<figure>.png, one per figure:
PLOTS = $(foreach f,voltages geometry aod wv_alpha,$(PLOTS_DIR)/$(basename $(notdir $(OUT)))_$(f).png)

# lines in the plots are broken across gaps longer than this, so nights are
# not drawn as data:
GAP_HOURS ?= 1

# make never wants the blocking figure windows; the windows target overrides it:
SHOW_FLAG ?=

all: npz plots

npz: $(OUT)

plots: $(PLOTS)

$(OUT): $(CSV) $(CALIB) $(SCRIPT) $(LIB)
	$(PYTHON) $(SCRIPT) $(CSV) \
		--calib $(CALIB) \
		--type $(TYPE) $(foreach l,$(LEVELS),--level $(l)) \
		-o $@

# one run of the script draws every figure, hence the grouped target:
$(PLOTS) &: $(OUT) $(PLOT_SCRIPT)
	$(PYTHON) $(PLOT_SCRIPT) $(OUT) \
		--outdir $(PLOTS_DIR) --gap-hours $(GAP_HOURS) $(SHOW_FLAG)

windows:
	@$(MAKE) --always-make SHOW_FLAG=--show plots

clean:
	rm -f $(OUT) $(PLOTS)

show:
	@echo "python: $(PYTHON)"
	@echo "csv:    $(CSV)"
	@echo "calib:  $(CALIB)"
	@echo "type:   $(TYPE)"
	@echo "levels: $(LEVELS)"
	@echo "output: $(OUT)"
	@echo "plots:  $(PLOTS)"

.PHONY: all npz plots windows clean show
