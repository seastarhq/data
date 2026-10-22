# match the AERONET sun observations against the SeaSTAR L0.6 voltages, one AERONET site at a
# time, and plot the matches.
#
#   make                 the matched pickles and their plots, if they are out of date
#   make matched         just the matched pickles
#   make plots           just the plots
#   make AERONET_MONTH=202610
#                        another month's AERONET data
#   make show            what make thinks it is working on
#   make clean           throw away the matched pickles and the plots
#
# the AERONET npz files are made by the Makefiles in ../../AERONET-*, and the L06 files by each
# campaign's L0.6/scripts/Makefile; the Makefile at the top of the data tree runs them first.
# matching and plotting parameters are in ../setup/parameters.sh

ROOT=../..
PICKLE=../pickle
PLOTS=../plots
SETUPFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh;

MATCH_SCRIPT=./match_aeronet_seastar.py
PLOT_SCRIPT=./plot_matched.py

AERONET_MONTH ?= 202609

# each AERONET site, its temperature-corrected data, and the SeaSTAR campaigns made beside it.
# the SeaSTAR data from the RV Shearwater (20260930) is at sea and from a day neither site
# covers, so it isn't matched
SITES=NASA_Ames San_Luis_Obispo

NASA_Ames_AERONET=$(ROOT)/AERONET-NASA_Ames/$(AERONET_MONTH)/NASA_Ames_905_raw_and_aod_tempcorr.npz
NASA_Ames_CAMPAIGNS=SeaSTAR-20260922-Ames-general_suntracking SeaSTAR-20260923-Ames-general_suntracking

San_Luis_Obispo_AERONET=$(ROOT)/AERONET-SLO/$(AERONET_MONTH)/San_Luis_Obispo_608_raw_and_aod_tempcorr.npz
San_Luis_Obispo_CAMPAIGNS=SeaSTAR-20260924-SLO-general_suntracking SeaSTAR-20260925-SLO-general_suntracking SeaSTAR-20260929-SLO-general_suntracking

# every L06 file of a site's campaigns
site_l06 = $(foreach c,$($(1)_CAMPAIGNS),$(wildcard $(ROOT)/$(c)/pickle/*.L06))

MATCHED=$(SITES:%=$(PICKLE)/matched_%.pkl)
# the plots are named after the days in the data, so each site's are tracked by a stamp
PLOT_STAMPS=$(SITES:%=$(PLOTS)/.matched_%.stamp)

all: matched plots

matched: $(MATCHED)

plots: $(PLOT_STAMPS)

.SECONDEXPANSION:
$(PICKLE)/matched_%.pkl: $$($$*_AERONET) $$(call site_l06,$$*) $(MATCH_SCRIPT) $(SETUPFILES)
	@[ -n "$(call site_l06,$*)" ] || { echo "no .L06 files for $*: build them with each campaign's L0.6/scripts/Makefile"; exit 1; }
	mkdir -p $(PICKLE)
	$(SETUP) $(MATCH_SCRIPT) --aeronet $($*_AERONET) \
		$(foreach f,$(call site_l06,$*),--seastar-l06 $(f)) \
		$${START:+--start $$START} $${END:+--end $$END} \
		--window-seconds "$$WINDOW_SECONDS" \
		--drop-on-flags "$$DROP_ON_FLAGS" \
		--dropout-fraction "$$AERONET_DROPOUT_FRACTION" \
		--no-plots -o $@

$(PLOTS)/.matched_%.stamp: $(PICKLE)/matched_%.pkl $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	mkdir -p $(PLOTS)
	$(SETUP) $(PLOT_SCRIPT) $< --outdir $(PLOTS) --timezone "$$SEASTAR_TIMEZONE"
	@touch $@

clean:
	rm -f $(MATCHED) $(PLOT_STAMPS) $(PLOTS)/matched_*.png

show:
	@$(foreach s,$(SITES),echo "$(s): $($(s)_AERONET)"; echo "  $(call site_l06,$(s))";)

.PHONY: all matched plots clean show
