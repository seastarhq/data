SeaSTAR_2025-08-13_13-04-01_log.csv:
	cat 2025-08-13_13-04-01_log.csv_part_* > $@
	cat 2025-08-13_17-59-13_log.csv_part_* >> 2025-08-08_17-59-13_log.csv 
	cat 2025-08-13_18-36-25_log.csv_part_* >> 2025-08-08_18-36-25_log.csv 

split:
	split -d --lines=15000 2025-08-13_13-04-01_log.csv-raw_too_big_for_github 2025-08-13_13-04-01_log.csv_part_
	split -d --lines=15000 2025-08-13_17-59-13_log.csv-raw_too_big_for_github 2025-08-13_17-59-13_log.csv_part_
	split -d --lines=15000 2025-08-13_18-36-25_log.csv-raw_too_big_for_github 2025-08-13_18-36-25_log.csv_part_

clean:
	rm *.csv_part_??
