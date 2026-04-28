SeaSTAR_2025-08-14_09-41-45_log.csv:
	cat 2025-08-14_09-41-45_log.csv_part_* > $@
	cat 2025-08-14_12-18-03_log.csv_part_* >> SeaSTAR_2025-08-08_12-18-03_log.csv 

split:
	split -d --lines=15000 2025-08-14_09-41-45_log.csv-raw_too_big_for_github 2025-08-14_09-41-45_log.csv_part_
	split -d --lines=15000 2025-08-14_12-18-03_log.csv-raw_too_big_for_github 2025-08-14_12-18-03_log.csv_part_

clean:
	rm *.csv_part_??
