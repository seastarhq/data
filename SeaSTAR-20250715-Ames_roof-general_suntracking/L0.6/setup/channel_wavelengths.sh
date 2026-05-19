# SeaSTAR photometer channel -> wavelength (nm) mapping.
# Used by the AERONET<->SeaSTAR calibration workflow to match each SeaSTAR
# channel against the corresponding AERONET wavelength voltage.
#
# Set each CH<n>_NM to the central wavelength in nanometres of the bandpass
# filter on that channel, or leave blank if the channel is unused.
#
# Available AERONET wavelengths (from NASA_Ames_905_raw_and_aod.csv):
#   340, 380, 440, 500, 675, 870, 935, 1020, 1640
# (1020 has both Si and InGaAs detectors; use 1020 here and let the
# calibration script pick which detector to compare against.)

CH1_NM=380
CH2_NM=440
CH3_NM=500
CH4_NM=550
CH5_NM=675

export CH1_NM CH2_NM CH3_NM CH4_NM CH5_NM
