2026-09-08_12-33-57_log.csv:
	cat $@_part_* > $@

split:
	split -d --lines=15000 2026-09-08_12-33-57_log.csv-raw_too_big_for_github 2026-09-08_12-33-57_log.csv_part_

clean:
	rm *.csv_part_??
