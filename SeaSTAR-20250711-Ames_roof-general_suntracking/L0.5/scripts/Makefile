SCRIPTS=./L0-to-L04.py ./L04-to-L05.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMSFILES=../setup/environment.sh ../setup/parameters.sh
vpath %.L04 ../../pickle
vpath %.L05 ../../pickle
vpath %.csv ../../raw_csv

SeaSTAR_2025-07-11_08-32-23.L05: SeaSTAR_2025-07-11_08-32-23.L04 
	echo processing L04 to L05 $@
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./L04-to-L05.py $< --outputfile $@)
	echo linking file
	(source ../setup/local.sh; source ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@)

SeaSTAR_2025-07-11_08-32-23.L04: SeaSTAR_2025-07-11_08-32-23.csv
	echo processing csv to L04 $@
	(source ../setup/local.sh; source ../setup/environment.sh; source ../setup/parameters.sh; ./L0-to-L04.py $< --outputfile $@)
	echo linking file
	(source ../setup/local.sh; source ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@)




#SeaSTAR_2025-07-10_09-23-46.L05: SeaSTAR_2025-07-10_09-23-46_log.csv
#	(source ../setup/environment.sh; source ../setup/parameters.sh; ./L0-to-L05-screen_suntracking.py $< --outfile $@)
