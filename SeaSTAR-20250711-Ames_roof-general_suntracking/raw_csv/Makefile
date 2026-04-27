SeaSTAR_2025-07-11_08-32-23.csv:
	cat 2025-07-11_08-32-23_log.csv_part* > $@

split:
	split -d --lines=15000 2025-07-11_08-32-23.csv_raw_too_big_for_github 2025-07-11_08-32-23.csv_part_

clean:
	rm *.csv_part_??
