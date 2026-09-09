2026-09-08_11-52-59_log.csv:
	cat $@_part_* > $@

split:
	split -d --lines=15000 2026-09-08_11-52-59_log.csv-raw_too_big_for_github 2026-09-08_11-52-59_log.csv_part_

clean:
	rm *.txt_part_??
