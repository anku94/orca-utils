PAPER := sc26ad
DRAFT_DIR := drafts
DRAFT_NAME := $(shell date '+%Y%m%d_%H00')

.PHONY: all draft rebuild clean

all:
	latexmk $(PAPER).tex

draft: all
	@mkdir -p $(DRAFT_DIR)
	cp build/$(PAPER).pdf $(DRAFT_DIR)/$(DRAFT_NAME).pdf
	@echo "Saved $(DRAFT_DIR)/$(DRAFT_NAME).pdf"

rebuild:
	latexmk -C $(PAPER).tex
	latexmk $(PAPER).tex

clean:
	latexmk -C $(PAPER).tex
