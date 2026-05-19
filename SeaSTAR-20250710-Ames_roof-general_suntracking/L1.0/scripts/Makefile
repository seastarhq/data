SCRIPTS=./L06-to-L10_sun.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMSFILES=../setup/environment.sh ../setup/parameters.sh ../setup/calibration.sh
vpath %.L05 ../../pickle
vpath %.L06 ../../pickle

SeaSTAR_2025-07-10_09-23-46.L10: SeaSTAR_2025-07-10_09-23-46.L06 $(SCRIPTS) $(MODULES) $(PARAMSFILES)
	echo processing L06 to L10
	(source ../setup/environment.sh; source ../setup/parameters.sh; source ../setup/calibration.sh; ./L06-to-L10-sun.py $< --outputfile $@)
