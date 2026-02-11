SeaSTAR_2025-07-10_09-23-46.L04: SeaSTAR_2025-07-10_09-23-46.csv
	echo processing csv to L04 $@
	./L0-to-L04.py 2025-07-10_09-23-46_log.csv
	ln -s $(PICKLE_DIR)/$_ 

SeaSTAR_2025-07-10_09-23-46.L05: SeaSTAR_2025-07-10_09-23-46.L04 
	echo processing L04 to L05 $@
	./L04-to_L05.py $

SeaSTAR_2025-07-10_09-23-46.csv:
	echo reconstructing $@
	cat $(RAW_DATA_DIR)/2025-07-10-09-23-45_log.csv_part_?? > $@
	echo linking $@
	ln -s $(RAW_DATA_DIR)/2025-07-10_09-23-46_log.csv SeaSTAR_2025-07-10_09-23-46.csv

# this doesn't work... 
#environment: 
#	echo sourcing $@ variables
#	. ../setup/environment.sh
#	. ../setup/parameters.sh

