#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
OUTPUT_DIR="${SCRIPT_DIR}/data"

TIKZ_DIR="${OUTPUT_DIR}/thesis-tikz"
ORCA_TIKZ_DIR="${OUTPUT_DIR}/orca-tikz-new"

setup_dirs() {
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${OUTPUT_DIR}"
}

# Default: handles nested PDFs (e.g., \includegraphics{logo.pdf}) that dvisvgm misses
pdf_to_svg() {
    local pdf_path="$1"
    local basename="${pdf_path##*/}"
    local name="${basename%.pdf}"
    local svg_path="${OUTPUT_DIR}/${name}.svg"

    echo "Converting (cairo): ${basename} -> ${name}.svg"
    pdftocairo -svg "${pdf_path}" "${svg_path}"
}

# dvisvgm mode: converts fonts to outlines, but can't handle nested PDFs
pdf_to_svg_dvisvgm() {
    local pdf_path="$1"
    local basename="${pdf_path##*/}"
    local name="${basename%.pdf}"
    local svg_path="${OUTPUT_DIR}/${name}_outlines.svg"

    echo "Converting (dvisvgm): ${basename} -> ${name}_outlines.svg"
    dvisvgm --pdf --no-fonts --exact --bitmap-format=png \
        --output="${svg_path}" \
        "${pdf_path}"
}

main() {
    setup_dirs

    pdf_to_svg "${TIKZ_DIR}/bsp.pdf"
    pdf_to_svg "${TIKZ_DIR}/feedback-loop.pdf"
    pdf_to_svg "${TIKZ_DIR}/broken-loop.pdf"
    pdf_to_svg "${TIKZ_DIR}/bsp-loop.pdf"
    pdf_to_svg "${TIKZ_DIR}/build/arch.pdf"

    echo "Done. SVGs in: ${OUTPUT_DIR}"
}

main
