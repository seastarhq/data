# L1.0 aerosol optical depth (L06-to-L10_sun.py) parameters. the V0 calibration is in calibration.sh

SEASTAR_TIMEZONE="US/Pacific"

# the IMU pressure (hPa) outside these bounds is a dropout, and AOD_PRESSURE_FALLBACK_HPA is used instead
# (and AOD_PRESSURE_FILLED set). the IMU records pascals; it is converted to hPa first
IMU_PRESS_MIN=800
IMU_PRESS_MAX=1100
AOD_PRESSURE_FALLBACK_HPA=1013.25

# which V0 calibration (calibration.sh): intercept, the intercept line |V| = a + b*V_aeronet, with
# tau*airmass = ln((V0 - a) / (|V| - a)); or origin, the line through the origin |V| = b*V_aeronet, with
# tau*airmass = ln(V0 / |V|). `make V0_MODE=origin` in L1.0/scripts overrides it, and writes SeaSTAR_<run>_v0origin.L10
V0_MODE=intercept

# the tracking error level (1, 2 or 3, set by TRACKING_EUCLIDIAN_MAX1/2/3 in the L0.5 parameters) at which a
# timestep gets AOD_TRACKING. no camera data and camera brightness out of bounds always count as bad tracking
AOD_TRACKING_LEVEL=1

# gas columns, in Dobson units, taken as constant over the run. rough climatology for the Santa Barbara Channel
# at the end of September; replace with the day's satellite values (e.g. OMI) when they're to hand
OZONE_COLUMN_DU=300
NO2_COLUMN_DU=0.1

# absorption cross-sections at each channel's centre wavelength, in cm^2/molecule (1 DU = 2.687e16 molecules/cm^2),
# for the channels with a V0. approximate values read from the standard laboratory sets: ozone from the
# Bass-Paur/Serdyuchenko Huggins and Chappuis bands, NO2 from Vandaele et al. (1998). 0 where the absorption
# is negligible. ch1 (380 nm) sits between the ozone Huggins and Chappuis bands
OZONE_XSEC_CH1=0
OZONE_XSEC_CH2=1.0e-22
OZONE_XSEC_CH3=1.3e-21
OZONE_XSEC_CH5=1.65e-21
OZONE_XSEC_CH6=9.0e-22
OZONE_XSEC_CH7=4.0e-23
OZONE_XSEC_CH10=0
NO2_XSEC_CH1=5.0e-19
NO2_XSEC_CH2=5.5e-19
NO2_XSEC_CH3=2.5e-19
NO2_XSEC_CH5=1.5e-20
NO2_XSEC_CH6=4.5e-19
NO2_XSEC_CH7=0
NO2_XSEC_CH10=0

# airmasses, one per constituent as AERONET does: Rayleigh from Kasten & Young (1989), aerosol from Kasten (1966),
# and ozone and NO2 from the spherical-shell form of Komhyr et al. (1989) with the absorbing layer at these heights
AIRMASS_OZONE_HEIGHT_KM=22
AIRMASS_NO2_HEIGHT_KM=22

# the Angstrom exponent is the slope of a straight line fitted to -ln(AOD) against ln(wavelength) over the channels
# with these wavelengths (nm), where all their AODs are positive
ANGSTROM_WAVELENGTHS="440 500 675 870"

export SEASTAR_TIMEZONE
export IMU_PRESS_MIN IMU_PRESS_MAX AOD_PRESSURE_FALLBACK_HPA
export V0_MODE
export AOD_TRACKING_LEVEL
export OZONE_COLUMN_DU NO2_COLUMN_DU
export OZONE_XSEC_CH1 OZONE_XSEC_CH2 OZONE_XSEC_CH3 OZONE_XSEC_CH5 OZONE_XSEC_CH6 OZONE_XSEC_CH7 OZONE_XSEC_CH10
export NO2_XSEC_CH1 NO2_XSEC_CH2 NO2_XSEC_CH3 NO2_XSEC_CH5 NO2_XSEC_CH6 NO2_XSEC_CH7 NO2_XSEC_CH10
export AIRMASS_OZONE_HEIGHT_KM AIRMASS_NO2_HEIGHT_KM
export ANGSTROM_WAVELENGTHS
