SeaSTAR_2025-07-10_09-23-46.csv:
	cat 2025-07-10_09-23-45_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-07-10_09-23-46_log.csv-raw_too_big_for_github 2025-07-10_09-23-46_log.csv_part_

clean:
	rm *.csv_part_??
