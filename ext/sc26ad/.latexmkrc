use File::Path qw(make_path);
make_path('build') unless -d 'build';

# Prepend miniforge bin to PATH so latexminted picks up Python <= 3.13
# (TeXLive 2025 latexminted-0.6.0 incompatible with Homebrew Python 3.14)
my $miniforge = "$ENV{HOME}/miniforge3/bin";
$ENV{PATH} = "$miniforge:$ENV{PATH}" if -d $miniforge;

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
