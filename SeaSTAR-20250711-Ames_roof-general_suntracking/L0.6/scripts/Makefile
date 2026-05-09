SCRIPTS=./L05-to-L06_sun.py ./temp_screen.py ./tripletvar_screen.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py 
PARAMSFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh
vpath %.L05 ../../pickle

SeaSTAR_2025-07-11_08-32-23.L06: SeaSTAR_2025-07-11_08-32-23.L05 $(SCRIPTS) $(MODULES) $(PARAMSFILES) 
	echo processing L05 to L06 $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./L05-to-L06_sun.py $< --outputfile $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./temp_screen.py $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./tripletvar_screen.py $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./temp_correction.py $@


SeaSTAR_2025-07-11_08-32-23.L05:
	# somehow this does not work:
	echo making symlink
	. ../setup/local.sh; . ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@
