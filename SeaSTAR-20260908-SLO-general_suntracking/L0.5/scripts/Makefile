SCRIPTS=./L0-to-L04.py ./L04-to-L05.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh
vpath %.L06 ../../pickle
vpath %.L04 ../../pickle
vpath %.csv ../../raw_csv

SeaSTAR_2025-07-10_09-23-46.L05: SeaSTAR_2025-07-10_09-23-46.L04 $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing L04 to L05 $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./L04-to-L05.py $< --outputfile $@
	echo making symlink
	# this somehow doesn't work:
	source ../setup/local.sh; source ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@

SeaSTAR_2025-07-10_09-23-46.L04: SeaSTAR_2025-07-10_09-23-46.csv $(SCRIPTS) $(MODULES) $(PARAMFILES)
	echo processing csv to L04 $@
	#(source $(PARAMFILES); ./L0-to-L04.py $< --outputfile $@)
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; ./L0-to-L04.py $< --outputfile $@
	echo making symlink
	# this somehow doesn't work:
	source ../setup/local.sh; source ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@

# this needs to be done by going to the RAW_DATA_DIR and running make
#SeaSTAR_2025-07-10_09-23-46.csv:
#	echo reconstructing $@
#	cat $(RAW_DATA_DIR)/2025-07-10_09-23-45_log.csv_part_?? > $(RAW_DATA_DIR)/$@
#	echo linking $@
#	ln -s $(RAW_DATA_DIR)/$@ 

# this doesn't work... 
#environment: 
#	echo sourcing $@ variables
#	. ../setup/environment.sh
#	. ../setup/parameters.sh

