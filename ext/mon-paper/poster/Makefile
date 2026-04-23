# Makefile for ORCA poster

ZIP_NAME = orca-poster-ankushj.zip

TEX_FILES = poster.tex poster-content.tex

all: pdf

# Build PDF with latexmk
pdf:
	latexmk -pdf poster.tex
	cp poster.pdf orca-poster-ankushj.pdf

# Update figures from source directories
figs:
	$(MAKE) -C figs

# Create zip for submission (figs + tex)
# Extracts to orca-poster-ankushj/ directory
ZIP_DIR = orca-poster-ankushj

zip: figs
	rm -rf $(ZIP_DIR) $(ZIP_NAME)
	mkdir -p $(ZIP_DIR)/figs
	cp $(TEX_FILES) $(ZIP_DIR)/
	cp figs/*.pdf $(ZIP_DIR)/figs/
	zip -r $(ZIP_NAME) $(ZIP_DIR)
	rm -rf $(ZIP_DIR)

clean:
	latexmk -c
	rm -f $(ZIP_NAME)

cleanall: clean
	latexmk -C
	$(MAKE) -C figs clean

.PHONY: all pdf figs zip clean cleanall
