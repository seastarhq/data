# the tracking thresholds are not set here: they are read from each run's L05 metadata,
# since those are the ones that set the tracking flags at L0 to L04

# plots are drawn in local time
SEASTAR_TIMEZONE="US/Pacific"

export SEASTAR_TIMEZONE

# the tracking levels are screened over a window around each second, from TRACKING_PRE_MARGIN seconds
# before it starts to TRACKING_POST_MARGIN seconds after it ends. the pre margin should match the L0.5
# ANALYSIS_MARGIN (../../L0.5/setup/parameters.sh); the script checks this against the L05 flags
TRACKING_PRE_MARGIN=0.25
TRACKING_POST_MARGIN=0.25

export TRACKING_PRE_MARGIN TRACKING_POST_MARGIN
