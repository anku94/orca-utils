from pathlib import Path
from .types import (
    Text,
    MarkdownList,
    Content,
    Object,
    TextObject,
    FigureObject,
    TitleSlide,
    ContentSlide,
    EvalSlide,
    Slide,
    Bullet,
    parse_md_bullets,
    Palette,
    ThemeMapping,
    Presentation,
)
from .themes import THEMES, Theme
from .deck_builder import DeckBuilder


def build_deck(pres: Presentation, output: Path, template: Path):
    output.parent.mkdir(parents=True, exist_ok=True)

    builder = DeckBuilder(template)
    if pres.theme:
        palette, mapping = THEMES[pres.theme]
        builder.apply_theme(palette, mapping)
    builder.add_slides(pres.slides)
    builder.save(output)
