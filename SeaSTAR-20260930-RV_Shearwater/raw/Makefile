LOGS = 2026-09-30_07-08-47_log.csv \
       2026-09-30_07-11-02_log.csv \
       2026-09-30_09-03-17_log.csv \
       2026-09-30_09-32-14_log.csv

all: $(LOGS)

$(LOGS):
	cat $@_part_* > $@

split:
	for f in $(LOGS); do \
		split -d --lines=15000 $$f-raw_too_big_for_github $${f}_part_; \
	done

# Tag freshly copied logs so git ignores them and they don't collide with the reassembled ones.
rename:
	for f in $(LOGS); do \
		[ -e "$$f" ] && mv -v "$$f" "$$f-raw_too_big_for_github"; \
	done; true

clean:
	rm -f $(foreach f,$(LOGS),$(f)_part_??)

.PHONY: all split rename clean
