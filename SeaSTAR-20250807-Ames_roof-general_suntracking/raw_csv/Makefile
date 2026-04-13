SeaSTAR_2025-08-07_09-40-00.csv:
	cat 2025_08_07_09-40-00_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-08-07_09-40-00_log.csv-raw_too_big_for_github 2025-08-07_09-40-00_log.csv_part_

clean:
	rm *.csv_part_??
