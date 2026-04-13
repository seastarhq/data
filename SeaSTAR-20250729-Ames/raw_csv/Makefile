SeaSTAR_2025-07-29_14-58-38_log.csv:
	cat 2025-07-29_14-58-38_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-07-29_14-58-38_log.csv-raw_too_big_for_github 2025-07-29_14-58-38_log.csv_part_

clean:
	rm *.csv_part_??
