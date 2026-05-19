SCRIPTS=./L0-to-L04.py ./L04-to-L05.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMSFILES=../setup/environment.sh ../setup/parameters.sh
vpath %.L04 ../../pickle
vpath %.L05 ../../pickle
vpath %.csv ../../raw_csv

SeaSTAR_2026-05-17_14-06-16.L05: SeaSTAR_2026-05-17_14-06-16.L04 
	echo processing L04 to L05 $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./L04-to-L05.py $< --outputfile $@
	echo linking file
	. ../setup/local.sh; . ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@

SeaSTAR_2026-05-17_14-06-16.L04: SeaSTAR_2026-05-17_14-06-16.csv
	echo processing csv to L04 $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./L0-to-L04.py $< --outputfile $@
	echo linking file
	. ../setup/local.sh; . ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@




SeaSTAR_2026-05-14_14-06-16_log.csv:
	. ../setup/environment.sh; . ../setup/parameters.sh; ln -s $(PICKLE_DIR)$@
