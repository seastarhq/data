# Paths used by the AERONET <-> SeaSTAR calibration workflow.
# Sourced by the Makefile before it runs match_aeronet_seastar.py and plot_matched.py.
# Which AERONET site each SeaSTAR campaign is matched against is set in ../scripts/Makefile,
# since make needs those files to know when to redo the matching.

ROOT_DIR=$LOCALROOT
CALIBRATION_DIR=$LOCALROOT/calibration_vs_ref
SCRIPTS_DIR=$CALIBRATION_DIR/scripts
PICKLE_DIR=$CALIBRATION_DIR/pickle
PLOTS_DIR=$CALIBRATION_DIR/plots

export ROOT_DIR CALIBRATION_DIR SCRIPTS_DIR PICKLE_DIR PLOTS_DIR
