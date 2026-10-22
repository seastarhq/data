# re-process the SeaSTAR campaigns from FROM to TO (by the date in the directory name),
# running each campaign's own Makefiles in order: L0.5, then L0.6 and tracking_analysis
# where the campaign has them. the campaigns are independent, so with -j they go in
# parallel, and the -j is passed down so that the runs within a campaign do too.
#
#   make -j6                 bring every stage of every campaign up to date
#   make -j6 reprocess       redo every stage of every campaign, whether out of date or not
#   make L05 / L06 / tracking
#                            just that stage (and the stages before it)
#   make SeaSTAR-20260930-RV_Shearwater
#                            every stage of one campaign
#   make FROM=20260924 TO=20260929 -j4
#                            a different range of campaigns
#   make aeronet             just the AERONET temperature-corrected npz files and their plots
#   make calibration         the AERONET <-> SeaSTAR matching and its plots (and everything before it)
#   make AERONET_MONTH=202610 aeronet
#                            another month of AERONET data
#   make show                which campaigns and stages make has found
#
# the AERONET sites (AERONET-NASA_Ames, AERONET-SLO) are processed by their own Makefiles for
# AERONET_MONTH. they don't depend on the SeaSTAR data, so they run alongside the campaigns.
# calibration_vs_ref matches the two, so it goes last, once both AERONET sites and every
# campaign's L0.6 are done. which campaign is matched to which site is set in its Makefile.
#
# the campaign quicklook Makefiles (e.g. SeaSTAR-20260930-RV_Shearwater/scripts) only plot
# the raw logs, so they aren't run from here

FROM ?= 20260922
TO ?= 20261014

# the campaigns in the date range that have an L0.5 stage
CAMPAIGNS := $(shell for mk in SeaSTAR-*/L0.5/scripts/Makefile; do \
		c=$${mk%%/*}; d=$${c#SeaSTAR-}; d=$${d%%-*}; \
		[ "$$d" -ge $(FROM) ] && [ "$$d" -le $(TO) ] && echo $$c; done)
L06_CAMPAIGNS := $(foreach c,$(CAMPAIGNS),$(if $(wildcard $(c)/L0.6/scripts/Makefile),$(c)))
TRACKING_CAMPAIGNS := $(foreach c,$(CAMPAIGNS),$(if $(wildcard $(c)/tracking_analysis/scripts/Makefile),$(c)))

L05_TARGETS = $(addprefix L05-,$(CAMPAIGNS))
L06_TARGETS = $(addprefix L06-,$(L06_CAMPAIGNS))
TRACKING_TARGETS = $(addprefix tracking-,$(TRACKING_CAMPAIGNS))

# the AERONET sites, and the month of their data to process (a <month> directory in each site)
AERONET_SITES = AERONET-NASA_Ames AERONET-SLO
AERONET_MONTH ?= 202609
AERONET_TARGETS = $(addprefix aeronet-,$(AERONET_SITES))

# set to -B (as reprocess does) to make every stage rebuild everything
SUBMAKE_FLAGS ?=

all: $(L05_TARGETS) $(L06_TARGETS) $(TRACKING_TARGETS) $(AERONET_TARGETS) calibration

L05: $(L05_TARGETS)

L06: $(L06_TARGETS)

tracking: $(TRACKING_TARGETS)

aeronet: $(AERONET_TARGETS)

calibration: $(L06_TARGETS) $(AERONET_TARGETS)
	$(MAKE) -C calibration_vs_ref/scripts AERONET_MONTH=$(AERONET_MONTH) $(SUBMAKE_FLAGS)

reprocess:
	$(MAKE) all SUBMAKE_FLAGS=-B

# each stage of a campaign waits for the one before it, but not for the other campaigns
$(L05_TARGETS): L05-%:
	$(MAKE) -C $*/L0.5/scripts $(SUBMAKE_FLAGS)

$(L06_TARGETS): L06-%: L05-%
	$(MAKE) -C $*/L0.6/scripts $(SUBMAKE_FLAGS)

$(TRACKING_TARGETS): tracking-%: L06-%
	$(MAKE) -C $*/tracking_analysis/scripts $(SUBMAKE_FLAGS)

$(AERONET_TARGETS): aeronet-%:
	$(MAKE) -C $* MONTH=$(AERONET_MONTH) $(SUBMAKE_FLAGS)

# a campaign's name makes all of its stages. the rules are written out one per campaign
# because a pattern rule would replace the % in filter's pattern with the campaign name
$(foreach c,$(CAMPAIGNS),$(eval $(c): $(filter %-$(c),$(L05_TARGETS) $(L06_TARGETS) $(TRACKING_TARGETS))))

show:
	@echo "campaigns $(FROM) to $(TO):"
	@$(foreach c,$(CAMPAIGNS),echo "  $(c): L0.5$(if $(filter $(c),$(L06_CAMPAIGNS)), L0.6)$(if $(filter $(c),$(TRACKING_CAMPAIGNS)), tracking_analysis)";)
	@echo "AERONET $(AERONET_MONTH): $(AERONET_SITES)"
	@echo "then: calibration_vs_ref"

.PHONY: all L05 L06 tracking aeronet calibration reprocess show $(CAMPAIGNS) $(L05_TARGETS) $(L06_TARGETS) $(TRACKING_TARGETS) $(AERONET_TARGETS)
