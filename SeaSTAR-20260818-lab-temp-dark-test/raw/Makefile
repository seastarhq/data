HamburgerData_2026_08_18_10_58_58.txt:
	cat $@_part_* > $@

split:
	split -d --lines=15000 HamburgerData_2026_08_18_10_58_58.txt-raw_too_big_for_github HamburgerData_2026_08_18_10_58_58.txt_part_

clean:
	rm *.txt_part_??
