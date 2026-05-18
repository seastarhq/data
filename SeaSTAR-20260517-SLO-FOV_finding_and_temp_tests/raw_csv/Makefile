SeaSTAR_2026-05-17_13-18-08.csv:
	cat 2026-05-17_13-18-08_log.csv_part* > $@
SeaSTAR_2026-05-17_13-45-38.csv:
	cat 2026-05-17_13-45-38_log.csv_part* > $@
SeaSTAR_2026-05-17_14-06-16.csv:
	cat 2026-05-17_14-06-16_log.csv_part* > $@

split:
	split -d --lines=15000 2026-05-17_13-18-08_log.csv_raw_too_big_for_github 2026-05-17_13-18-08_log.csv_part_
	split -d --lines=15000 2026-05-17_13-45-38_log.csv_raw_too_big_for_github 2026-05-17_13-45-38_log.csv_part_
	split -d --lines=15000 2026-05-17_14-06-16_log.csv_raw_too_big_for_github 2026-05-17_14-06-16_log.csv_part_
	

clean:
	rm *.csv_part_??
