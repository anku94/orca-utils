from .types import Palette, ThemeMapping

Theme = tuple[Palette, ThemeMapping]

NORD_PALETTE: Palette = {
    # Polar Night (dark backgrounds)
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord2": "#434C5E",
    "nord3": "#4C566A",
    # Snow Storm (light backgrounds/text)
    "nord4": "#D8DEE9",
    "nord5": "#E5E9F0",
    "nord6": "#ECEFF4",
    # Frost (primary accents - blues/cyans)
    "nord7": "#8FBCBB",
    "nord8": "#88C0D0",
    "nord9": "#81A1C1",
    "nord10": "#5E81AC",
    # Aurora (secondary accents)
    "nord11": "#BF616A",  # red
    "nord12": "#D08770",  # orange
    "nord13": "#EBCB8B",  # yellow
    "nord14": "#A3BE8C",  # green
    "nord15": "#B48EAD",  # purple
}

NORD_1_MAPPING = ThemeMapping(
    dk1="nord0",
    lt1="nord6",
    dk2="nord1",
    lt2="nord5",
    accent1="nord10",
    accent2="nord11",
    accent3="nord12",
    accent4="nord13",
    accent5="nord14",
    accent6="nord15",
    hlink="nord8",
    folHlink="nord9",
)

THEMES: dict[str, Theme] = {
    "Nord-1": (NORD_PALETTE, NORD_1_MAPPING),
}
