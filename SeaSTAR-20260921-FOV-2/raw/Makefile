LOG = 2026-09-21_14-33-36_log.csv

$(LOG):
	cat $@_part_* > $@

split:
	split -d --lines=15000 $(LOG)-raw_too_big_for_github $(LOG)_part_

clean:
	rm $(LOG)_part_??
