#!/usr/bin/bash

. ../setup/environment.sh
. ../setup/parameters.sh

echo process L0.5 to L0.6
./avg_L05_to_L06_sun.py SeaSTAR-L05_2025-07-10_09-23-46.npz

echo do triplet_var 
./tripletvar_screen SeaSTAR-L06_2025-07-10_09-23-46.npz
