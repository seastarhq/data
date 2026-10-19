# SeaSTAR hardware configuration for Sept 2026

## Channel/wavelength assignments

Two "hot" blocks are installed, each with 5 silicon photodiode detectors. Each block has two Dallas temperature sensors on either end. 

### Block 1

Block 1 is logged as Ch1_1x Ch2_1x Ch3_1x Ch4_1x Ch5_1x in the csv file. Temperatures are T1 on the inboard side and T3 on the outboard side. Wavelength filters by channel are as follows:

1. 380/2 nm #4855 (inboard)
2. 440/10 nm #3362
3. 500/10 nm #4481
4. 550/10 nm, no serial number (Thorlabs part)
5. 675/10 nm, serial number is indistinct. (outboard)

### Block 2

Block 2 is logged as Ch6_1x Ch7_1x Ch8_1x Ch9_1x Ch10_1x in the csv file. Temperatures are T2 on the inboard side and T4 on the outboard side. Wavelength filters by channel are as follows:

1. 340/2 nm # 3682 (inboard)
2. 870/10 nm #077
3. 940/10 nm, no serial number (Thorlabs part)
4. 940/5 nm, old BARR filter
5. 1020/10 nm #045 (outboard)

Serial number filters are Iridian. Arrows point in the direction of light transmission. 
Thorlabs filters similarly - arrows point in the direction of light transmission.
BARR filter does not appear to have an arrow.

## Camera

A new camera Arducam X002CBGEYV B0322 purchased on 9/10/2026 was installed. 

## Hamburger

There is no hamburger board installed. Channels are wired directly into the A/D converter. 

## A/D

LabJack T7 Pro OEM. Serial # TBD. Logging AIN0 thru AIN9. Reading the Dallas sensors via an onboard Lua script.
