SCRIPTS=./L05-to-L06_sun.py ./temp_screen.py ./tripletvar_screen.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py 
PARAMSFILES=../setup/environment.sh ../setup/parameters.sh
vpath %.L05 ../../pickle

SeaSTAR_2025-07-10_09-23-46.L06: SeaSTAR_2025-07-10_09-23-46.L05 $(SCRIPTS) $(MODULES) $(PARAMSFILES) 
	echo processing L05 to L06 $@
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./L05-to-L06_sun.py $< --outputfile $@)
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./temp_screen.py $@)
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./tripletvar_screen.py $@)
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./temp_correction.py $@)


SeaSTAR_2025-07-10_09-23-46.L05:
	(source ../setup/local.sh; source ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@)
