# the SeaSTAR campaigns matched against each AERONET site, included by ../scripts/Makefile.
# a campaign left out here isn't used anywhere in calibration_vs_ref (matching, tempcorr, V0
# transfer, AOD comparison). editing this file rebuilds everything that depends on the lists.
# make syntax: space-separated, no quotes

NASA_Ames_CAMPAIGNS=SeaSTAR-20260922-Ames-general_suntracking SeaSTAR-20260923-Ames-general_suntracking

# SeaSTAR-20260925-SLO-general_suntracking is left out: it seems to be an outlier on the AOD-vs-AOD plot
San_Luis_Obispo_CAMPAIGNS=SeaSTAR-20260924-SLO-general_suntracking SeaSTAR-20260929-SLO-general_suntracking
