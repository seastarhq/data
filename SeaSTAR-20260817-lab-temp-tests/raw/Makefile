HamburgerData_2026_08_17_12_23_41.txt:
	cat $@_part_* > $@

split:
	split -d --lines=15000 HamburgerData_2026_08_17_12_23_41.txt-raw_too_big_for_github HamburgerData_2026_08_17_12_23_41.txt_part_

clean:
	rm *.txt_part_??
