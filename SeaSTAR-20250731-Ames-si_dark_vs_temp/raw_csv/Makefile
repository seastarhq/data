SeaSTAR_2025-07-31_08-35-02_log.csv:
	cat 2025-07-31_08-35-02_log.csv_part_* > $@

SeaSTAR_2025-07-31_14-03-03.csv:
	cat 2025_07_31_14-03-03_log.csv_part_* > $@

split:
	split -d --lines=15000 2025-07-31_08-35-02_log.csv-raw_too_big_for_github 2025-07-31_08-35-02_log.csv_part_
	split -d --lines=15000 2025-07-31_14-03-03_log.csv-raw_too_big_for_github 2025-07-31_14-03_03_log.csv_part_

clean:
	rm *.csv_part_??
