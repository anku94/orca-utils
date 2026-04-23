# Enable PDF mode
$pdf_mode = 1;

# Set the output directory
$out_dir = 'build';

# Ensure all generated files go to the output directory
$aux_dir = 'build';

# Set the LaTeX command to use pdflatex with the appropriate options
$pdflatex = 'pdflatex -interaction=nonstopmode -synctex=1 -shell-escape -file-line-error %O %S';

# Set the biber command to handle bibliography files
$biber = 'biber --output-directory build %O %B';

# Ensure all files are output to the build directory
$out_dir1 = 'build';

# Ensure all auxiliary files are output to the build directory
$aux_dir1 = 'build';

# Set the PDF viewer to none
$pdf_previewer = 'none';

# Enable verbose mode
$preview_continuous_mode = 1;

# Set the PVC timeout to indefinite
$pvc_timeout = -1;

# Enable continuous preview mode
$pvc_view_file_via_temporary = 0;

# Set default extension for output files to PDF
$pdf_mode = 1;

# Ensure .bbl files are written to the build directory
$bbl_file = 'build/%B.bbl';

# Ensure index files are written to the build directory
$index_file = 'build/%B.idx';

# Ensure all files are output to the build directory
$out_dir = 'build';
