SeaSTAR_2025-08-05_07-57-31.csv:
	cat 2025_08_05_07-57-31_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-08-05_07-57-31_log.csv-raw_too_big_for_github 2025-08-05_07-57-31_log.csv_part_

clean:
	rm *.csv_part_??
