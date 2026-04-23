import colorsys
import glob as glob
import matplotlib.figure as pltfig
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import subprocess

TEXTWIDTH = 7.0  # inches, across columns
COLWIDTH = 3.33  # inches, single column

RgbaColor = tuple[float, float, float, float]


class Sizes(float, Enum):
    TEXTWIDTH = 7.0
    COLWIDTH = 3.33


class SpecialColors(str, Enum):
    FLAG = "#B22222"
    HATCH = "#aaa"


class Prof(str, Enum):
    BASELINE = "00_noorca"
    ORCA_MPISYNC = "05_or_trace_mpisync"
    ORCA_TGT = "07_or_tracetgt"
    TAU_TGT = "10_tau_tracetgt"
    DFTRACER_TGT = "11_dftracer"
    DFTRACER_COMP = "12_dftracer_comp"
    SCOREP_TGT = "13_scorep"
    ORCA_NTV_WAITCNT = "15_or_ntv_mpiwait_onlycnt"
    ORCA_NTV_WAITTRACE = "16_or_ntv_mpiwait_tracecnt"
    ORCA_NTV_KOKKOS = "17_or_ntv_kokkos"
    CALIPER_TGT = "17_caliper_tracetgt"
    ORCA_TCP_SYNC = "18_or_tcp_tracesync"
    ORCA_TCPTGT = "19_or_tcp_tracetgt"


@dataclass
class ProfProps:
    label: str
    marker: str
    color: str


# Canonical props from amr_tracesizes_line
PROF_PROPS: dict[Prof, ProfProps] = {
    Prof.BASELINE: ProfProps("Baseline", "x", "C0"),
    Prof.ORCA_MPISYNC: ProfProps("ORCA", "o", "C1"),
    Prof.ORCA_TGT: ProfProps("ORCA", "o", "C0"),
    Prof.TAU_TGT: ProfProps("TAU", "s", "C1"),
    Prof.SCOREP_TGT: ProfProps("Score-P", ".", "C2"),
    Prof.DFTRACER_TGT: ProfProps("DFTracer", "D", "C3"),
    Prof.DFTRACER_COMP: ProfProps("DFTracer\n\\emph{(gzip)}", "D", "C3"),
    Prof.CALIPER_TGT: ProfProps("Caliper", "P", "C4"),
    Prof.ORCA_NTV_WAITCNT: ProfProps("ORCA", "o", "C1"),
    Prof.ORCA_NTV_WAITTRACE: ProfProps("ORCA", "o", "C1"),
    Prof.ORCA_NTV_KOKKOS: ProfProps("ORCA", "o", "C1"),
    Prof.ORCA_TCP_SYNC: ProfProps("ORCA", "o", "C1"),
    Prof.ORCA_TCPTGT: ProfProps("ORCA", "o", "C1"),
}


def get_git_root() -> Path:
    # invoke git rev-parse --show-toplevel
    cmd = ["git", "rev-parse", "--show-toplevel"]
    git_root = subprocess.run(cmd, capture_output=True, text=True).stdout
    return Path(git_root.strip())


def get_plotsrc_dir() -> Path:
    return get_git_root() / "data" / "plotsrc"


def get_plotdata_dir() -> Path:
    return get_git_root() / "data" / "plotdata"


def get_plotfigs_dir() -> Path:
    return get_git_root() / "data" / "figs"


def save_plot(fig: pltfig.Figure, fname: str, subdir: str | None = None):
    base = get_plotfigs_dir()
    if subdir:
        base = base / subdir
        base.mkdir(parents=True, exist_ok=True)
    fpath = base / f"{fname}.pdf"
    print(f"[PlotSaver] Writing to {fpath}")
    fig.savefig(fpath, dpi=300, pad_inches=0.01)


def darken_rgba(c, f: float) -> RgbaColor:
    rgba = mcolors.to_rgba(c)
    return (rgba[0] * f, rgba[1] * f, rgba[2] * f, rgba[3])


def darken_hsl(c, l_factor: float, s_boost: float) -> RgbaColor:
    rgba = mcolors.to_rgba(c)
    rgb, a = rgba[:3], rgba[3]
    hue, lum, sat = colorsys.rgb_to_hls(*rgb)
    lum = lum * l_factor
    sat = min(sat * s_boost, 1.0)
    rgb = colorsys.hls_to_rgb(hue, lum, sat)
    return rgb + (a,)


def set_colormap(cmap: str):
    if cmap == "Pastel1-Dark":
        cmap = plt.colormaps["Pastel1"]
        # colors = [darken_rgba(cmap(i), 0.6) for i in range(cmap.N)]
        colors = [darken_hsl(cmap(i), 0.7, 0.6) for i in range(cmap.N)]
    else:
        cmap = plt.colormaps[cmap]
        colors = [cmap(i) for i in range(cmap.N)]
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=colors)


Frame = tuple[list[int], list[int], list[int]]  # (artists, legend_items, xtick_items)


class StagedBuildout:
    """
    Incrementally reveal plot elements for presentation slides.

    Usage:
        sb = StagedBuildout(ax, fig, "myplot")
        sb.add_frame([artist_indices], [legend_indices], [xtick_indices])
        sb.build()  # saves to data/figs/sb/myplot_0.pdf, myplot_1.pdf, ...

    Manual control: disable_alx(), enable_alx(), toggle_artists()
    """

    def __init__(self, ax: plt.Axes, fig: pltfig.Figure, fname: str, ext: str = "pdf"):
        self.ax = ax
        self.fig = fig
        self.fname = fname
        self.ext = ext
        self.frames: list[Frame] = []

        # Only manage legend if axes has one (skip if using fig.legend)
        if ax.get_legend() is not None:
            handles, labels = ax.get_legend_handles_labels()
            self.ohandles = handles
            self.olabels = labels
            self.olegvis = [True] * len(handles)
        else:
            self.ohandles = []
            self.olabels = []
            self.olegvis = []

        self.oxlabels = ax.get_xticklabels()
        self.oxvis = [True] * len(self.oxlabels)

    def _get_sb_dir(self) -> Path:
        sb_dir = get_plotfigs_dir() / "sb"
        sb_dir.mkdir(parents=True, exist_ok=True)
        return sb_dir

    def add_frame(
        self, artists: list[int], legend_items: list[int] = [], x_items: list[int] = []
    ):
        self.frames.append((artists, legend_items, x_items))

    def build(self):
        for frame in self.frames:
            self.disable_alx(*frame)

        self._save_frame(0)

        for idx, frame in enumerate(self.frames):
            self.enable_alx(*frame)
            self._save_frame(idx + 1)

    def _save_frame(self, idx: int):
        fpath = self._get_sb_dir() / f"{self.fname}_{idx}.{self.ext}"
        print(f"[StagedBuildout] Writing frame {idx} to {fpath}")
        self.fig.savefig(fpath, dpi=300, pad_inches=0.01)

    def disable_legend_entry(self, index: int):
        if self.ohandles and index < len(self.olegvis):
            self.olegvis[index] = False
            self.rebuild_legend()

    def enable_legend_entry(self, index: int):
        if self.ohandles and index < len(self.olegvis):
            self.olegvis[index] = True
            self.rebuild_legend()

    def toggle_legend_entry(self, index: int):
        if self.ohandles and index < len(self.olegvis):
            self.olegvis[index] = not self.olegvis[index]
            self.rebuild_legend()

    def disable_xticklabel(self, index: int):
        self.oxlabels[index].set_visible(False)
        self.oxvis[index] = False

    def enable_xticklabel(self, index: int):
        self.oxlabels[index].set_visible(True)
        self.oxvis[index] = True

    def rebuild_legend(self):
        handles = [h for h, v in zip(self.ohandles, self.olegvis) if v]
        labels = [l for l, v in zip(self.olabels, self.olegvis) if v]
        self.draw_legend(handles, labels)

    def disable_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(False)

    def enable_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(True)

    def toggle_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(not artists[i].get_visible())

    def disable_alx(
        self, artists: list[int], legend_items: list[int] = [], x_items: list[int] = []
    ):
        self.disable_artists(artists)
        for item in legend_items:
            self.disable_legend_entry(item)
        for item in x_items:
            self.disable_xticklabel(item)

    def enable_alx(
        self, artists: list[int], legend_items: list[int] = [], x_items: list[int] = []
    ):
        self.enable_artists(artists)
        for item in legend_items:
            self.enable_legend_entry(item)
        for item in x_items:
            self.enable_xticklabel(item)

    def draw_legend(self, handles, labels):
        if self.ohandles and handles:
            self.ax.legend(handles, labels)
