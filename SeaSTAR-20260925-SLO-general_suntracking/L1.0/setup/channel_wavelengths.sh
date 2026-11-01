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
CH6_NM=340
CH7_NM=870
CH8_NM=940
CH9_NM=940
CH10_NM=1020

export CH1_NM CH2_NM CH3_NM CH4_NM CH5_NM CH6_NM CH7_NM CH8_NM CH9_NM CH10_NM

# Channel widths:

CH1_W=2
CH2_W=10
CH3_W=10
CH4_W=10
CH5_W=10
CH6_W=2
CH7_W=10
CH8_W=10
CH9_W=5
CH10_W=10

export CH1_W CH2_W CH3_W CH4_W CH5_W CH6_W CH7_W CH8_W CH9_W CH10_W
