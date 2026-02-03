SeaSTAR_2025-07-10_09-23-46.L04: SeaSTAR_2025-07-10_09-23-46.csv environment
	echo processing csv to L04 $@
	./L0-to-L0.4.py 2025-07-10_09-23-46_log.csv
	ln -s $(PICKLE_DIR)/$_ 

SeaSTAR_2025-07-10_09-23-46.L05: SeaSTAR_2025-07-10_09-23-46.L04 environment
	echo processing L04 to L05 $@
	./L04-to_L05.py $

SeaSTAR_2025-07-10_09-23-46.csv: 
	echo linking $@
	ln -s $(RAW_DATA_DIR)/2025-07-10_09-23-46_log.csv SeaSTAR_2025-07-10_09-23-46.csv

environment: 
	echo sourcing $@ variables
	. ../setup/environment.sh
	. ../setup/parameters.sh

