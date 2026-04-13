SeaSTAR_2025-08-04_17-22-41.csv:
	cat 2025_08_04_17-22-41_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-08-04_17-22-41_log.csv-raw_too_big_for_github 2025-08-04_17-22-41_log.csv_part_

clean:
	rm *.csv_part_??
