# Paths used by the AERONET <-> SeaSTAR calibration workflow.
# Source this before invoking match_aeronet_seastar.py via the Makefile.

ROOT_DIR=~steve/nothing/seastarhq/data
CALIBRATION_DIR=$ROOT_DIR/calibration
SCRIPTS_DIR=$CALIBRATION_DIR/scripts
PICKLE_DIR=$CALIBRATION_DIR/pickle
PLOTS_DIR=$CALIBRATION_DIR/plots

AERONET_PICKLE=$ROOT_DIR/AERONET-NASA_Ames/NASA_Ames_905_raw_and_aod.pkl

# SeaSTAR L0.6 inputs. Each entry must be a path to a .L06 file produced by
# the campaign's L0.6/scripts/Makefile. The matcher reads channel<->wavelength
# mapping from <campaign>/L0.6/setup/channel_wavelengths.sh (sibling to the
# .L06's campaign dir).
SEASTAR_CAMPAIGN_DIRS=(
    "$ROOT_DIR/SeaSTAR-20250710-Ames_roof-general_suntracking"
    "$ROOT_DIR/SeaSTAR-20250711-Ames_roof-general_suntracking"
)

export ROOT_DIR CALIBRATION_DIR SCRIPTS_DIR PICKLE_DIR PLOTS_DIR
export AERONET_PICKLE SEASTAR_CAMPAIGN_DIRS
