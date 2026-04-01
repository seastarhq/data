#!/usr/bin/bash

. ../setup/environment.sh

./extract_temperatures.py SeaSTAR_2025-07-10_09-23-46.L06 > $EXTRACTED_DATA_DIR/SeaSTAR_2025-07-10_09-23-46-temperatures.txt
./extract_radiometers.py SeaSTAR_2025-07-10_09-23-46.L06 > $EXTRACTED_DATA_DIR/SeaSTAR_2025-07-10_09-23-46-radiometers.txt
./extract_tracking.py SeaSTAR_2025-07-10_09-23-46.L06 > $EXTRACTED_DATA_DIR/SeaSTAR_2025-07-10_09-23-46-tracking.txt
