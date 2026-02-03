#!/usr/bin/bash

. ../setup/environment.sh
. ../setup/parameters.sh

echo process L0.5 to 0.6
./avg_L05_to_L06_sun.py SeaSTAR-L05_2025-07-11_08-32-23.npz

echo screen the L0.6
./tripletvar_screen.py SeaSTAR-L06_2025-07-11_08-32-23.npz
