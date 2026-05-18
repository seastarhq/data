SeaSTAR_2026-05-18_11-03-16.csv:
	cat 2026-05-18_11-03-16_log.csv_part* > $@

split:
	split -d --lines=15000 2026-05-18_11-03-16_log.csv_raw_too_big_for_github 2026-05-18_11-03-16_log.csv_part_
	

clean:
	rm *.csv_part_??
