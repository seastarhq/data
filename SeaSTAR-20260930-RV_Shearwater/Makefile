# process this campaign through every level, running each level's own Makefile in order.
# those Makefiles don't build the level before them, so the order is set here.
#
#   make -j4                 bring everything up to date, through L1.0 and its AOD plot
#   make L04 / L05 / L06 / L10
#                            just that level (and the levels before it)
#   make V0_MODE=origin      process L1.0 with that V0 calibration (see L1.0/scripts/Makefile)
#
# the runs to process are listed in RAWFILES in each level's Makefile

all: L10

L04:
	$(MAKE) -C L0.5/scripts L04

L05: L04
	$(MAKE) -C L0.5/scripts L05

L06: L05
	$(MAKE) -C L0.6/scripts L06

# L1.0's all target, so that the AOD plot is included
L10: L06
	$(MAKE) -C L1.0/scripts all

.PHONY: all L04 L05 L06 L10
