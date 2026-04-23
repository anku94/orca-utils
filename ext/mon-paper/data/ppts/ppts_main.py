from pathlib import Path
from pptapi import (
    ContentSlide,
    EvalSlide,
    MarkdownList,
    Text,
    Slide,
    TextObject,
    FigureObject,
    build_deck,
    TitleSlide,
    Presentation,
)

SB_DIR = Path("/Users/schwifty/Repos/mon-paper/data/figs/sb")
DATA_DIR = Path(__file__).parent / "data"
TEMPLATE = DATA_DIR / "pdltemplate.pptx"

# Default text size is 45

slides: list[Slide] = []

s = TitleSlide(title="Introduction", subtitle="Subtitle")
slides.append(s)

s = ContentSlide(
    "Introduction",
    MarkdownList(
        """
- ORCA: Observability framework
- Low overhead tracing
- Scales to 4096+ ranks
""",
        fontsz=16,
    ),
)
slides.append(s)

s = EvalSlide(
    title="Runtime Overhead",
    bullets=MarkdownList(
        """
- Compare with TAU, DFTracer, Score-P, Caliper
- Measure relative runtime
- 512 to 4096 ranks
"""
    ),
    figures=sorted(SB_DIR.glob("tracer_runtimes_line_*.pdf")),
)
slides.append(s)

s = ContentSlide(
    title="Objects Demo",
    content=Text("Main content area"),
    objects=[
        TextObject(
            left=10, top=5, width=4, height=1, content=Text("Positioned text box")
        ),
        FigureObject(
            left=10, top=6.5, width=3, path=SB_DIR / "tracer_runtimes_line_1.pdf"
        ),
    ],
)
slides.append(s)

pres = Presentation(slides=slides, theme="Nord-1")

ppt_fpath = DATA_DIR / "main_tmp.pptx"
build_deck(pres, ppt_fpath, TEMPLATE)
