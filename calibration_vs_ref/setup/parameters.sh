# Tunable parameters for the AERONET <-> SeaSTAR matching script.

# Half-width of the time window used to average L0.6 around each AERONET
# observation timestamp. Total window = 2 * WINDOW_SECONDS.
WINDOW_SECONDS=15

# Date range (UTC, ISO 8601). Inclusive START, exclusive END.
# Leave blank to use the full overlap of available L0.6 + AERONET data.
START=
END=

# Flag policy: drop L0.6 rows where ANY of the listed flag fields is non-zero
# before averaging. Comma-separated. Valid: tracking_flags, robot_flags,
# housekeeping_flags, radiometer_1x_flags, radiometer_100x_flags,
# radiometer_10kx_flags, cloud_flags.
DROP_ON_FLAGS=cloud_flags,tracking_flags

# Flag-bit policy: also drop L0.6 rows where any of these bits is set, as comma-separated
# <flag field>:<integer mask> entries (for fields where only some bits matter).
# 65536 is CHANNEL_TEMP_LOW in housekeeping_flags: a channel below CHANNEL_TEMP_MIN (28 C)
# in the campaign's L0.6 parameters.sh. the whole housekeeping field isn't used, because
# HOT_BLOCK_1_HOT is set on most of the SLO data
DROP_ON_BITS=housekeeping_flags:65536

# AERONET voltages are the mean of each wavelength's V1/V2/V3 triplet. A triplet member below
# this fraction of the triplet's median is a dropout and is left out of the mean. The triplets
# normally agree to ~0.5% (down to ~0.8 at 340 nm, from sky variability); dropouts go to 0.1-0.3
AERONET_DROPOUT_FRACTION=0.8

# the time zone the plots' time axes are drawn in
SEASTAR_TIMEZONE="US/Pacific"

# temperature-correction fits (fit_tempcorr.py): the reference temperature the coefficients are
# written about, in degrees C, and the fewest matches a channel is fitted with
TEMPCORR_TREF=30
TEMPCORR_MIN_POINTS=10

export WINDOW_SECONDS START END DROP_ON_FLAGS DROP_ON_BITS AERONET_DROPOUT_FRACTION SEASTAR_TIMEZONE
export TEMPCORR_TREF TEMPCORR_MIN_POINTS
