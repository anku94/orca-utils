use File::Path qw(make_path);
make_path('build') unless -d 'build';

$pdf_mode = 1;
$out_dir = 'build';
$aux_dir = 'build';

$pdflatex = 'pdflatex -shell-escape -synctex=1 -file-line-error -halt-on-error %O %S';
$biber = 'biber --output-directory build %O %B';

$pdf_previewer = 'none';
$preview_continuous_mode = 0;
$pvc_timeout = -1;
$pvc_view_file_via_temporary = 0;

$bbl_file = 'build/%B.bbl';
$index_file = 'build/%B.idx';
