# List of source files to compile
FILES = overlay.tex sampling.tex ts2pc.tex overlay-agg-new.tex overlay-agg-new-2.tex

# Output directories (should match .latexmkrc)
BUILD_DIR = build
PDF_DIR = pdf

# Default target
all: $(addprefix $(PDF_DIR)/,$(FILES:.tex=.pdf))

# Pattern rule for PDF compilation
$(PDF_DIR)/%.pdf: %.tex
	latexmk -pdf $<

# Cleaning targets
clean:
	rm -rf $(BUILD_DIR)/*

cleanpdf:
	rm -rf $(PDF_DIR)/*

cleanall: clean cleanpdf
	latexmk -C
	rm -f *.bbl *.run.xml *.synctex.gz

.PHONY: all clean cleanpdf cleanall