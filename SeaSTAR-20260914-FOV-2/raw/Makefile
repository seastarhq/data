2026-09-14_15-23-55_log.csv:
	cat $@_part_* > $@

split:
	split -d --lines=15000 2026-09-14_15-23-55_log.csv-raw_too_big_for_github 2026-09-14_15-23-55_log.csv_part_

clean:
	rm *.txt_part_??
