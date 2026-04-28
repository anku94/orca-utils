PAPER := sc26ad
DRAFT_DIR := drafts
DRAFT_NAME := $(shell date '+%Y%m%d_%H00')

.PHONY: all draft rebuild clean cleanroot

all:
	latexmk $(PAPER).tex

draft: all
	@mkdir -p $(DRAFT_DIR)
	cp build/$(PAPER).pdf $(DRAFT_DIR)/$(DRAFT_NAME).pdf
	zip -q $(DRAFT_DIR)/$(DRAFT_NAME).zip *.tex *.sty
	@echo "Saved $(DRAFT_DIR)/$(DRAFT_NAME).{pdf,zip}"

rebuild:
	latexmk -C $(PAPER).tex
	latexmk $(PAPER).tex

clean:
	latexmk -C $(PAPER).tex

cleanroot:
	rm -f $(PAPER).aux $(PAPER).fdb_latexmk $(PAPER).fls $(PAPER).log $(PAPER).out $(PAPER).synctex.gz *.data.minted
