# Makefile to copy figures referenced in poster
# Run from poster/figs/ directory

FIGS_DIR = ../../data/figs
TIKZ_DIR = ../../data/tikz-figs-new

# Figures from data/figs/
FROM_FIGS = \
	lesson_volfunc_single_narrow.pdf \
	runtime_query_combo.pdf \
	amr_tracesizes_line.pdf \
	agentic_timeline.pdf

# Figures from data/tikz-figs-new/
FROM_TIKZ = \
	plan.pdf \
	arch.pdf

# Missing figures (not yet created)
# broken-loop.pdf
# bsp.pdf

all: $(FROM_FIGS) $(FROM_TIKZ)

$(FROM_FIGS):
	cp $(FIGS_DIR)/$@ $@

$(FROM_TIKZ):
	cp $(TIKZ_DIR)/$@ $@

clean:
	rm -f $(FROM_FIGS) $(FROM_TIKZ)

.PHONY: all clean
