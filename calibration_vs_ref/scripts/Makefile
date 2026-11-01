# match the AERONET sun observations against the SeaSTAR L0.6 voltages, one AERONET site at a
# time, plot the matches, and fit temperature-correction coefficients to them.
#
#   make                 the matched pickles, their plots and the fits, if they are out of date
#   make matched         just the matched pickles
#   make plots           just the plots
#   make tempcorr        just the temperature-correction fits (../fits/tempcorr_<site>.txt and plots)
#   make response        just the SeaSTAR-against-AERONET voltage plots, coloured by temperature, without
#                        and with the residual- and scatter-method temperature corrections from the fits
#   make v0              the SeaSTAR V0s transferred from both sites' AERONET V0s (../fits/v0_seastar.txt)
#   make closure         run a campaign's L1.0 AOD calculation on each site's AERONET voltages and V0s, against
#                        AERONET's AOD (../fits/closure_<site>.txt, ../plots/closure_<site>.png)
#   make aod             plot each day's SeaSTAR L1.0 AOD against the AERONET AOD (../plots/aod_<site>_<date>_*.png,
#                        ../fits/aod_<site>.txt). the .L10 files are made by each campaign's L1.0/scripts/Makefile
#   make aod V0_MODE=origin
#                        the same from the campaigns' SeaSTAR_<run>_v0origin.L10 files (made with
#                        `make V0_MODE=origin` in each campaign's L1.0/scripts), into aod_<site>_v0origin*
#   make closure L10_CAMPAIGN=SeaSTAR-...
#                        another campaign's L1.0 settings
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
FITS=../fits
SETUPFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh
SETUP=. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh;

MATCH_SCRIPT=./match_aeronet_seastar.py
PLOT_SCRIPT=./plot_matched.py
FIT_SCRIPT=./fit_tempcorr.py
RESPONSE_SCRIPT=./plot_response.py
V0_SCRIPT=./transfer_v0.py
CLOSURE_SCRIPT=./aeronet_aod_closure.py
AOD_SCRIPT=./plot_aod_vs_aeronet.py

AERONET_MONTH ?= 202609

# the campaign whose L1.0 AOD calculation the closure checks: its seastar_atmosphere.py, and the gas settings
# and channel wavelengths in its L1.0/setup
L10_CAMPAIGN ?= SeaSTAR-20260930-RV_Shearwater
L10_DIR=$(ROOT)/$(L10_CAMPAIGN)/L1.0
L10_SETUPFILES=$(L10_DIR)/setup/parameters.sh $(L10_DIR)/setup/channel_wavelengths.sh

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
# and every L10 file: with V0_MODE set, the SeaSTAR_<run>_v0<mode>.L10 files, otherwise the untagged ones
L10_TAG=$(if $(V0_MODE),_v0$(V0_MODE))
site_l10 = $(filter-out $(if $(V0_MODE),,%_v0origin.L10 %_v0intercept.L10),\
	$(foreach c,$($(1)_CAMPAIGNS),$(wildcard $(ROOT)/$(c)/pickle/*$(L10_TAG).L10)))

MATCHED=$(SITES:%=$(PICKLE)/matched_%.pkl)
# the plots are named after the days in the data, so each site's are tracked by a stamp
PLOT_STAMPS=$(SITES:%=$(PLOTS)/.matched_%.stamp)

TEMPCORR=$(SITES:%=$(FITS)/tempcorr_%.txt)
RESPONSE=$(SITES:%=$(PLOTS)/response_%.png)
V0=$(FITS)/v0_seastar.txt
CLOSURE=$(SITES:%=$(FITS)/closure_%.txt)
AOD=$(SITES:%=$(FITS)/aod_%$(L10_TAG).txt)

all: matched plots tempcorr response v0 closure aod

matched: $(MATCHED)

plots: $(PLOT_STAMPS)

tempcorr: $(TEMPCORR)

response: $(RESPONSE)

v0: $(V0)

closure: $(CLOSURE)

aod: $(AOD)

.SECONDEXPANSION:
$(PICKLE)/matched_%.pkl: $$($$*_AERONET) $$(call site_l06,$$*) $(MATCH_SCRIPT) $(SETUPFILES)
	@[ -n "$(call site_l06,$*)" ] || { echo "no .L06 files for $*: build them with each campaign's L0.6/scripts/Makefile"; exit 1; }
	mkdir -p $(PICKLE)
	$(SETUP) $(MATCH_SCRIPT) --aeronet $($*_AERONET) \
		$(foreach f,$(call site_l06,$*),--seastar-l06 $(f)) \
		$${START:+--start $$START} $${END:+--end $$END} \
		--window-seconds "$$WINDOW_SECONDS" \
		--drop-on-flags "$$DROP_ON_FLAGS" \
		--drop-on-bits "$$DROP_ON_BITS" \
		--dropout-fraction "$$AERONET_DROPOUT_FRACTION" \
		--no-plots -o $@

$(PLOTS)/.matched_%.stamp: $(PICKLE)/matched_%.pkl $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	mkdir -p $(PLOTS)
	$(SETUP) $(PLOT_SCRIPT) $< --outdir $(PLOTS) --timezone "$$SEASTAR_TIMEZONE"
	@touch $@

$(FITS)/tempcorr_%.txt: $(PICKLE)/matched_%.pkl $(FIT_SCRIPT) $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	$(SETUP) $(FIT_SCRIPT) $< --tref "$$TEMPCORR_TREF" --min-points "$$TEMPCORR_MIN_POINTS" \
		--outdir $(FITS) --plotdir $(PLOTS)

$(PLOTS)/response_%.png: $(PICKLE)/matched_%.pkl $(FITS)/tempcorr_%.txt $(RESPONSE_SCRIPT) $(FIT_SCRIPT) $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	mkdir -p $(PLOTS)
	$(SETUP) $(RESPONSE_SCRIPT) $< --coeffs $(FITS)/tempcorr_$*.txt --method residual scatter --outdir $(PLOTS)

$(V0): $(MATCHED) $(TEMPCORR) $(V0_SCRIPT) $(RESPONSE_SCRIPT) $(FIT_SCRIPT) $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	$(SETUP) $(V0_SCRIPT) $(foreach s,$(SITES),--site $(PICKLE)/matched_$(s).pkl $(FITS)/tempcorr_$(s).txt) -o $@

$(FITS)/closure_%.txt: $$($$*_AERONET) $(CLOSURE_SCRIPT) $(V0_SCRIPT) $(MATCH_SCRIPT) $(PLOT_SCRIPT) $(SETUPFILES) $(L10_SETUPFILES) $(L10_DIR)/scripts/seastar_atmosphere.py
	mkdir -p $(FITS) $(PLOTS)
	$(SETUP) . $(L10_DIR)/setup/parameters.sh; . $(L10_DIR)/setup/channel_wavelengths.sh; \
		$(CLOSURE_SCRIPT) $($*_AERONET) --pressure "$$AERONET_PRESSURE_$*" --l10-scripts $(L10_DIR)/scripts \
		--dropout-fraction "$$AERONET_DROPOUT_FRACTION" -o $@ --plot $(PLOTS)/closure_$*.png

$(FITS)/aod_%$(L10_TAG).txt: $$($$*_AERONET) $$(call site_l10,$$*) $(AOD_SCRIPT) $(PLOT_SCRIPT) $(MATCH_SCRIPT) $(SETUPFILES)
	@[ -n "$(call site_l10,$*)" ] || { echo "no .L10 files for $*: build them with each campaign's L1.0/scripts/Makefile"; exit 1; }
	$(SETUP) $(AOD_SCRIPT) --aeronet $($*_AERONET) $(foreach f,$(call site_l10,$*),--seastar-l10 $(f)) \
		--window-seconds "$$WINDOW_SECONDS" --timezone "$$SEASTAR_TIMEZONE" --outdir $(PLOTS) --table $@ \
		$(if $(L10_TAG),--tag $(L10_TAG))

clean:
	rm -f $(MATCHED) $(PLOT_STAMPS) $(PLOTS)/matched_*.png $(TEMPCORR) $(V0) $(CLOSURE) $(PLOTS)/closure_*.png $(FITS)/aod_*.txt $(PLOTS)/aod_*.png $(PLOTS)/tempcorr_*.png $(PLOTS)/response_*.png

show:
	@$(foreach s,$(SITES),echo "$(s): $($(s)_AERONET)"; echo "  $(call site_l06,$(s))";)

.PHONY: all matched plots tempcorr response v0 closure aod clean show
