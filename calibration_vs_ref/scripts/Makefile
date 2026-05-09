SCRIPT=./match_aeronet_seastar.py
SETUP=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh

# Default target: build the matched pickle for the configured date range.
# Inputs (AERONET_PICKLE, SEASTAR_CAMPAIGN_DIRS, START, END, ...) come from
# ../setup/environment.sh and ../setup/parameters.sh.
.PHONY: matched
matched: $(SCRIPT) $(SETUP)
	@( \
	  . ../setup/local.sh; \
	  . ../setup/environment.sh; \
	  . ../setup/parameters.sh; \
	  L06_ARGS=""; \
	  for d in "$${SEASTAR_CAMPAIGN_DIRS[@]}"; do \
	    for f in "$$d"/pickle/*.L06; do \
	      [ -e "$$f" ] && L06_ARGS="$$L06_ARGS --seastar-l06 $$f"; \
	    done; \
	  done; \
	  if [ -z "$$L06_ARGS" ]; then \
	    echo "no .L06 files found under $${SEASTAR_CAMPAIGN_DIRS[*]}"; \
	    echo "build them first with each campaign's L0.6/scripts/Makefile"; \
	    exit 1; \
	  fi; \
	  RANGE_ARGS=""; \
	  [ -n "$$START" ] && RANGE_ARGS="$$RANGE_ARGS --start $$START"; \
	  [ -n "$$END" ]   && RANGE_ARGS="$$RANGE_ARGS --end $$END"; \
	  TAG=$$( [ -n "$$START$$END" ] && echo "$${START//:/}_$${END//:/}" || echo "all" ); \
	  OUT="$$PICKLE_DIR/matched_$$TAG.pkl"; \
	  $(SCRIPT) \
	    --aeronet-pickle "$$AERONET_PICKLE" \
	    $$L06_ARGS \
	    $$RANGE_ARGS \
	    --window-seconds "$$WINDOW_SECONDS" \
	    --drop-on-flags "$$DROP_ON_FLAGS" \
	    --plots-dir "$$PLOTS_DIR" \
	    -o "$$OUT" \
	)

.PHONY: clean
clean:
	rm -f ../pickle/matched_*.pkl
	rm -f ../plots/*.png
