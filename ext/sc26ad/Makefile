PAPER := sc26ad
DRAFT_DIR := drafts
DRAFT_NAME := $(shell date '+%Y%m%d_%H00')

.PHONY: all clean rebuild

all:
	latexmk $(PAPER).tex
	@mkdir -p $(DRAFT_DIR)
	cp build/$(PAPER).pdf $(DRAFT_DIR)/$(DRAFT_NAME).pdf
	@echo "Saved $(DRAFT_DIR)/$(DRAFT_NAME).pdf"

rebuild:
	latexmk -C $(PAPER).tex
	latexmk $(PAPER).tex

clean:
	latexmk -C $(PAPER).tex
