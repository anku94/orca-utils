THESIS_TIKZ := /Users/schwifty/Repos/thesis/thesis/data/tikz/pdf

FIGS := orca-arch

TARGETS := $(addprefix thesis-,$(addsuffix .pdf,$(FIGS)))

all: $(TARGETS)

thesis-%.pdf: $(THESIS_TIKZ)/%.pdf
	cp $< $@

clean:
	rm -f $(TARGETS)

.PHONY: all clean
