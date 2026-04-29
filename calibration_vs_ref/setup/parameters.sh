# Tunable parameters for the AERONET <-> SeaSTAR matching script.

# Half-width of the time window used to average L0.6 around each AERONET
# observation timestamp. Total window = 2 * WINDOW_SECONDS.
WINDOW_SECONDS=30

# Date range (UTC, ISO 8601). Inclusive START, exclusive END.
# Leave blank to use the full overlap of available L0.6 + AERONET data.
START=
END=

# Flag policy: drop L0.6 rows where ANY of the listed flag fields is non-zero
# before averaging. Comma-separated. Valid: tracking_flags, robot_flags,
# housekeeping_flags, radiometer_1x_flags, radiometer_100x_flags,
# radiometer_10kx_flags, cloud_flags.
DROP_ON_FLAGS=cloud_flags,tracking_flags

export WINDOW_SECONDS START END DROP_ON_FLAGS
