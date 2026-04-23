from dataclasses import dataclass, field
from pathlib import Path
import mistune


Palette = dict[str, str]  # name -> hex, e.g. {"nord10": "#5E81AC"}


@dataclass
class Text:
    text: str
    fontsz: int | None = None


@dataclass
class MarkdownList:
    text: str
    fontsz: int | None = None


Content = Text | MarkdownList


@dataclass
class Object:
    left: float    # inches
    top: float     # inches
    width: float = 0
    height: float = 0


@dataclass
class TextObject(Object):
    content: Content = ""  # str | MarkdownList


@dataclass
class FigureObject(Object):
    path: Path = None
    # width/height: 0 = auto. If both set, one is ignored (aspect-preserving)


@dataclass
class Slide:
    title: str
    objects: list[Object] = field(default_factory=list, kw_only=True)


@dataclass
class TitleSlide(Slide):
    subtitle: str = ""


@dataclass
class ContentSlide(Slide):
    content: Content


@dataclass
class EvalSlide(Slide):
    bullets: Content
    figures: list[Path]


@dataclass
class ThemeMapping:
    dk1: str
    lt1: str
    dk2: str
    lt2: str
    accent1: str
    accent2: str
    accent3: str
    accent4: str
    accent5: str
    accent6: str
    hlink: str
    folHlink: str


@dataclass
class Presentation:
    slides: list[Slide]
    theme: str | None = None  # key into THEMES


Bullet = tuple[int, str]


def parse_md_bullets(md_text: str) -> list[Bullet]:
    def extract(tokens, level=0):
        result = []
        for token in tokens:
            if token["type"] == "list":
                for child in token["children"]:
                    result.extend(extract([child], level))
            elif token["type"] == "list_item":
                for child in token["children"]:
                    if child["type"] == "block_text":
                        text = "".join(c.get("raw", "") for c in child["children"])
                        result.append((level, text))
                    elif child["type"] == "list":
                        result.extend(extract([child], level + 1))
        return result

    md = mistune.create_markdown(renderer=None)
    tokens = md(md_text.strip())
    return extract(tokens)
