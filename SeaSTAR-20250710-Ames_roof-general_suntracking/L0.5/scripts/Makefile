SeaSTAR_2025-07-10_09-23-46.L05: SeaSTAR_2025-07-10_09-23-46.L04 
	echo processing L04 to L05 $@
	./L04-to-L05.py SeaSTAR_2025-07-10_09-23-46.L04 --outputfile SeaSTAR_2025-07-10_09-23-46.L05 
	ln -s $(PICKLE_DIR)/$@

SeaSTAR_2025-07-10_09-23-46.L04: SeaSTAR_2025-07-10_09-23-46.csv
	echo processing csv to L04 $@
	./L0-to-L04.py SeaSTAR_2025-07-10_09-23-46.csv --outputfile SeaSTAR_2025-07-10_09-23-46.L04 
	ln -s $(PICKLE_DIR)/$@ 

SeaSTAR_2025-07-10_09-23-46.csv:
	echo reconstructing $@
	cat $(RAW_DATA_DIR)/2025-07-10_09-23-45_log.csv_part_?? > $(RAW_DATA_DIR)/$@
	echo linking $@
	ln -s $(RAW_DATA_DIR)/$@ 

# this doesn't work... 
#environment: 
#	echo sourcing $@ variables
#	. ../setup/environment.sh
#	. ../setup/parameters.sh

