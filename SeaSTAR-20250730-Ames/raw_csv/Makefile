SeaSTAR_2025-07-30_09-13-47_log.csv:
	cat 2025-07-30_09-13-47_log.csv_part_* > $@

SeaSTAR_2025-07-30_09-29-22_log.csv:
	cat 2025_07_30_09-29-22_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-07-30_09-13-47_log.csv-raw_too_big_for_github 2025-07-30_09-13-47_log.csv_part_
	split -d --lines=15000 2025-07-30_09-29-22_log.csv-raw_too_big_for_github 2025-07-30_09-29_22_log.csv_part_

clean:
	rm *.csv_part_??
