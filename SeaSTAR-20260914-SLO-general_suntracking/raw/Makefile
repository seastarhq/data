# Assembled day-long log, built from the GitHub-sized _part_NN chunks.
DATE = 2026-09-14
ASSEMBLED = $(DATE)_log.csv
SCRIPTS = ../../scripts

$(ASSEMBLED): $(wildcard $(ASSEMBLED)_part_*)
	cat $(ASSEMBLED)_part_* > $@

# Merge the per-session too-big files into $(ASSEMBLED) and write the parts.
split:
	$(SCRIPTS)/assemble_raw.py . -o $(ASSEMBLED) --split --force

# Tag freshly copied per-session logs so git ignores them (leaves $(ASSEMBLED) alone).
rename:
	for f in *.csv; do \
		[ "$$f" = "$(ASSEMBLED)" ] && continue; \
		[ -e "$$f" ] && mv -v "$$f" "$$f-raw_too_big_for_github"; \
	done; true

clean:
	rm -f $(ASSEMBLED) $(ASSEMBLED)_part_??

.PHONY: split rename clean
