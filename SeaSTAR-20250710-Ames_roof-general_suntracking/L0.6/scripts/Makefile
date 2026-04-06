SeaSTAR_2025-07-10_09-23-46.L06: SeaSTAR_2025-07-10_09-23-46.L05 L05-to-L06_sun.py tripletvar_screen.py tripletvar_temp_screen.py 
	echo processing L05 to L06 $@
	(source ../setup/environment.sh; source ../setup/parameters.sh; ./L05-to-L06_sun.py SeaSTAR_2025-07-10_09-23-46.L05 --outputfile $@)
	(source ../setup/environment.sh; source ../setup/parameters.sh; ./tripletvar_screen.py SeaSTAR_2025-07-10_09-23-46.L06)
	(source ../setup/environment.sh; source ../setup/parameters.sh; ./tripletvar_temp_screen.py SeaSTAR_2025-07-10_09-23-46.L06 --temp_triplet_time=5 --tempslope_tol=0.05)


SeaSTAR_2025-07-10_09-23-46.L05:
	ln -s $(PICKLE_DIR)/$@
