SeaSTAR_2025-08-01_10-56-08.csv:
	cat 2025_08_01_10-56-08_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-08-01_10-56-08_log.csv-raw_too_big_for_github 2025-08-01_10-56-08_log.csv_part_

clean:
	rm *.csv_part_??
