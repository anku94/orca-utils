"""
Plot 3-track timeline of agentic debugging session.

Tracks (top to bottom):
- user: feedback events
- llm: flow and code events
- app: running periods as shaded bands
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.ticker as mtick
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Literal

import common as c

# --- Globals for consistent styling ---
FONTSIZE_SMALL = 6  # emoji, annotations, flow labels (lower plot)
FONTSIZE_MED = 7    # flow labels (upper plot), ratio annotation
FONTSIZE_LG = 8    # ratio annotation
FONTSIZE_LEGEND = 7

MARKER_SIZE_LG = 140   # user feedback markers
MARKER_SIZE_MD = 90   # flow markers
MARKER_SIZE_SM = 30   # polars, code markers

LINEWIDTH_THIN = 0.5
LINEWIDTH_MED = 0.8


@dataclass
class SpanEvent:
    secs: tuple[float, float]  # secs when active
    track: Literal["user", "llm", "app"]
    ev_type: str
    desc: str


@dataclass
class PointEvent:
    secs: float
    track: Literal["user", "llm", "app"]
    ev_type: str
    desc: str

    @staticmethod
    def from_span(se: SpanEvent) -> "PointEvent":
        return PointEvent(
            secs=se.secs[0], track=se.track, ev_type=se.ev_type, desc=se.desc
        )


@dataclass
class Timeline:
    spans: list[SpanEvent]
    points: list[PointEvent]

    def __str__(self) -> str:
        s = f"Timeline(spans={len(self.spans)}, points={len(self.points)})"
        s += "\n- Spans:"
        for sidx, se in enumerate(self.spans):
            s += f"\n  {sidx:2d}: {se}"
        s += "\n\n- Points:"
        for pidx, pe in enumerate(self.points):
            s += f"\n  {pidx:2d}: {pe}"

        return s


# Event styles: (facecolor, edgecolor, marker, size)
# Using darker colors with edges
EVENT_STYLES = {
    "feedback": ("C0", "black", "o", 40),
    "flow": ("C1", "black", "s", 45),
    "code": ("C2", "black", "^", 40),
}

# Simplified band colors: just 2 colors
BAND_COLORS = {
    "app": "C3",  # app running periods
    "analysis": "C4",  # LLM analysis periods
}


def load_events() -> pd.DataFrame:
    """Load timeline events from CSV"""
    data_dir = c.get_plotdata_dir() / "agentic-data"
    csv_path = data_dir / "timeline_events.csv"
    df = pd.read_csv(csv_path)
    return df


def transform_events(df: pd.DataFrame) -> Timeline:
    """Transform raw events into SpanEvents and PointEvents."""
    tl = Timeline(spans=[], points=[])

    # App spans: pair resumes with pauses
    df_app = df[df["track"] == "app"]
    resumes = df_app[df_app["event_type"] == "resume"]
    pauses = df_app[df_app["event_type"] == "pause"]
    for (_, r), (_, p) in zip(resumes.iterrows(), pauses.iterrows()):
        s_time = (r.t_secs, p.t_secs)
        s_steps = (int(r["ts_sim"]), int(p["ts_sim"]))
        # s_desc = f"$T_{{{s_steps[0]}}} \\rightarrow T_{{{s_steps[1]}}}$"
        s_desc = f"T{s_steps[0]},T{s_steps[1]}"
        s_evt = SpanEvent(secs=s_time, track="app", ev_type="app", desc=s_desc)
        tl.spans.append(s_evt)

    # LLM tool spans: pair tool calls with completions
    df_llm = df[df["track"] == "llm"]
    toolbeg = df_llm[df_llm["event_type"] != "completion"]
    toolend = df_llm[df_llm["event_type"] == "completion"]
    assert len(toolbeg) == len(toolend), "beg/end len mismatch"
    for (_, b), (_, e) in zip(toolbeg.iterrows(), toolend.iterrows()):
        s_time = (b.t_secs, e.t_secs)
        s_evtype = b.event_type
        s_desc = b.label
        s_evt = SpanEvent(secs=s_time, track="llm", ev_type=s_evtype, desc=s_desc)
        tl.spans.append(s_evt)

    # User feedback as point events
    df_user = df[df["event_type"] == "feedback"]
    for _, row in df_user.iterrows():
        pe = PointEvent(secs=row["t_secs"], track="user", ev_type="", desc=row["label"])
        tl.points.append(pe)

    return tl


def add_synthetic_events(tl: Timeline):
    start_evt = tl.points[3]
    assert start_evt.desc == "start the final exercise"

    app_evts = [e for e in tl.spans if e.track == "app"]
    for app_evt in app_evts:
        print(app_evt)

    # zip app events pairwise
    app_pairs = list(zip(app_evts[:-1], app_evts[1:]))
    for ap0, ap1 in app_pairs:
        gap_start = ap0.secs[1]
        gap_end = ap1.secs[0]

        if gap_start < start_evt.secs < gap_end:
            bef_secs = (gap_start, start_evt.secs)
            aft_secs = (start_evt.secs, gap_end)
            se_bef = SpanEvent(secs=bef_secs, track="llm", ev_type="activity", desc="")
            se_aft = SpanEvent(secs=aft_secs, track="llm", ev_type="activity", desc="")
            tl.spans.append(se_bef)
            tl.spans.append(se_aft)
        else:
            se_secs = (gap_start, gap_end)
            se = SpanEvent(secs=se_secs, track="llm", ev_type="activity", desc="")
            tl.spans.append(se)

    # compute final span as the time between last app event and last user feedback
    fe_time = (app_evts[-1].secs[1], tl.points[-2].secs)
    fe_evtype = "activity"
    fe_evt = SpanEvent(secs=fe_time, track="llm", ev_type=fe_evtype, desc="")
    tl.spans.append(fe_evt)

    # remove the last point event (just reporting)
    tl.points.pop()


def setup_axes(axes: list[plt.Axes], max_tsecs: float):
    """Configure axes with proper grid and ticks"""
    for i, ax in enumerate(axes):
        # Grid - vertical only
        ax.grid(which="major", axis="x", color="#bbb", linewidth=0.5)
        ax.grid(which="minor", axis="x", color="#ddd", linewidth=0.3)
        ax.grid(which="both", axis="y", visible=False)
        ax.set_axisbelow(True)

        # X limits
        ax.set_xlim(0, max_tsecs)

        # X ticks - only on bottom
        ax.xaxis.set_major_locator(mtick.MultipleLocator(200))
        ax.xaxis.set_minor_locator(mtick.MultipleLocator(50))

        if i < len(axes) - 1:
            ax.tick_params(axis="x", labelbottom=False)
        else:
            ax.set_xlabel("Time (minutes)")

        # Y axis - minimal
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", pad=1)
        ax.yaxis.labelpad = 4
        ax.set_axisbelow(True)


def track_to_idx(track: Literal["user", "llm", "app"]) -> int:
    return {"user": 0, "llm": 1, "app": 2}[track]


def add_span_event(axes: list[plt.Axes], se: SpanEvent, props: dict, idx: int):
    track_idx = track_to_idx(se.track)
    ax = axes[track_idx]
    ax.axvspan(se.secs[0], se.secs[1], **props)
    scol = props["color"]
    ecol = c.darken_hsl(scol, 0.8, 0.5)
    ax.axvline(se.secs[0], color=ecol, linewidth=0.3)
    ax.axvline(se.secs[1], color=ecol, linewidth=0.3)


def add_point_event(
    axes: list[plt.Axes], pe: PointEvent, lprops: dict, mprops: dict, idx: int
):
    track_idx = track_to_idx(pe.track)
    ax = axes[track_idx]
    ax.axvline(pe.secs, **lprops)
    edge = lprops["color"]
    ax.scatter([pe.secs], [0], color="#fff", edgecolor=edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_LG, zorder=10, marker="o")  # fmt: skip


def span_props(col: str) -> dict:
    return {"color": col, "alpha": 0.4, "linewidth": LINEWIDTH_THIN}


def point_props(col: str) -> tuple[dict, dict]:
    edge = c.darken_hsl(col, 0.4, 0.4)
    lprops = {"color": edge, "linewidth": LINEWIDTH_MED}
    mprops = {
        "color": "#fff",
        "edgecolor": edge,
        "linewidth": LINEWIDTH_THIN,
        "zorder": 10,
        "s": MARKER_SIZE_MD,
    }
    return lprops, mprops


def add_user_feedback_point(
    axes: list[plt.Axes], pe: PointEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(pe.secs) else "C0"
    edge = c.darken_hsl(col, 0.4, 0.4)
    ax = axes[track_to_idx("user")]
    ax.axvline(pe.secs, color=edge, linewidth=LINEWIDTH_MED)
    if idx < 3:
        return
    ax.scatter([pe.secs], [0], color="#fff", edgecolor=edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_LG, zorder=idx, marker="o")  # fmt: skip

    emoji_map = {3: r"{\emojifont 🚀}", 4: r"{\emojifont ⚠️}", 5: r"{\emojifont 🔍}", 6: r"{\emojifont ❌}", 8: r"{\emojifont 🔍}", 9: r"{\emojifont 🏁}"}  # fmt: skip

    if idx in emoji_map:
        ax.text(pe.secs, 0, emoji_map[idx], ha="center", va="center", fontsize=FONTSIZE_MED, zorder=idx)  # fmt: skip


def add_app_span(
    axes: list[plt.Axes], se: SpanEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(se.secs[0]) else c.darken_hsl("C2", 0.8, 0.6)
    add_span_event(axes, se, span_props(col), idx)
    ax = axes[track_to_idx("app")]
    mid_x = (se.secs[0] + se.secs[1]) / 2

    tbeg, tend = se.desc.split(",")
    tbeg, tend = tbeg.strip("T"), tend.strip("T")

    if idx == 0:
        return
    if idx == 1:
        tbeg, tend, mid_x = "0", "83", 122

    txt = rf"$T_{{{tbeg}}} \rightarrow T_{{{tend}}}$"
    ymap = {0: 0.2, 1: -0.2, 2: 0.2, 3: -0.2, 4: 0.1}
    y = ymap.get(idx, 0)

    xmap = {0: mid_x, 1: mid_x, 2: mid_x, 3: mid_x + 200, 4: mid_x - 200}
    x = xmap.get(idx, mid_x)

    bbox = dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.3", linewidth=0.3, alpha=0.6)  # fmt: skip
    ax.text(x, y, txt, ha="center", va="center", fontsize=FONTSIZE_MED, zorder=11, bbox=bbox)  # fmt: skip


def add_activity_span(
    axes: list[plt.Axes], se: SpanEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(se.secs[0]) else "C2"
    col = c.darken_hsl(col, 0.8, 0.6)
    add_span_event(axes, se, span_props(col), idx)


def add_flow_create_point(
    axes: list[plt.Axes], se: SpanEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(se.secs[0]) else "C1"
    edge = c.darken_hsl(col, 0.4, 0.4)
    ax = axes[track_to_idx("llm")]

    ax.axvline(se.secs[0], color=edge, linewidth=LINEWIDTH_THIN)
    h = ax.scatter([se.secs[0]], [0], color=col, edgecolor=edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_MD, zorder=10, marker="o")  # fmt: skip
    if idx == 33:
        h.set_linestyle("--")

    label_map = {9: "1", 14: "2", 34: "3"}
    label = label_map.get(idx, "")
    if label:
        ax.text(se.secs[0], 0, label, ha="center", va="center", fontsize=FONTSIZE_MED, zorder=11, fontweight="bold")  # fmt: skip


def add_polars_point(
    axes: list[plt.Axes], se: SpanEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(se.secs[0]) else "C4"
    edge = c.darken_hsl(col, 0.4, 0.4)
    ax = axes[track_to_idx("llm")]
    ax.axvline(se.secs[0], color=edge, linewidth=LINEWIDTH_THIN)
    ax.scatter([se.secs[0]], [0], color=col, edgecolor=edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_SM, zorder=10, marker="s")  # fmt: skip


def add_code_point(
    axes: list[plt.Axes], se: SpanEvent, is_warmup: Callable[[float], bool], idx: int
):
    col = "#aaa" if is_warmup(se.secs[0]) else "C3"
    edge = c.darken_hsl(col, 0.4, 0.4)
    ax = axes[track_to_idx("llm")]
    ax.axvline(se.secs[0], color=edge, linewidth=LINEWIDTH_THIN)
    ax.scatter([se.secs[0]], [0], color=col, edgecolor=edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_SM, zorder=10, marker="^")  # fmt: skip


def make_legend(subfig):
    # Manual horizontal legend
    h_warmup = mpatches.Patch(facecolor="#aaa", edgecolor=c.darken_hsl("#aaa", 0.4, 0.4))  # fmt: skip
    active_col = c.darken_hsl("C2", 0.8, 0.6)
    active_ecol = c.darken_hsl(active_col, 0.8, 0.5)
    h_active = mpatches.Patch(facecolor=active_col, edgecolor=active_ecol)  # fmt: skip
    h_flow = mlines.Line2D([], [], color="C1", marker="o", markersize=5, linestyle="None", markeredgecolor=c.darken_hsl("C1", 0.4, 0.4))  # fmt: skip
    h_polars = mlines.Line2D([], [], color="C4", marker="s", markersize=5, linestyle="None", markeredgecolor=c.darken_hsl("C4", 0.4, 0.4))  # fmt: skip
    h_code = mlines.Line2D([], [], color="C3", marker="^", markersize=5, linestyle="None", markeredgecolor=c.darken_hsl("C3", 0.4, 0.4))  # fmt: skip

    handles = [h_warmup, h_active, h_flow, h_polars, h_code]
    labels = ["Warmup", "Active", "Flow", "Analytics", "Code Scan"]
    lbbox = (0.51, 1.01)
    subfig.legend(handles=handles, labels=labels, loc="outside upper center", ncol=5, frameon=True, fontsize=FONTSIZE_LEGEND, columnspacing=0.7, handletextpad=0.5, handlelength=1.4)  # fmt: skip


def load_rowcounts():
    fn_tgt = "20251229-tracetgt-aggr-tierwise.csv"
    fn_sync = "20251229-mpisync-aggr-tierwise.csv"
    fn_ag = "20260116-agentic-complete-aggr-tierwise.csv"

    def get_df(fn: str) -> pd.DataFrame:
        df = pd.read_csv(c.get_plotdata_dir() / "agentic-data" / fn)
        df.drop(columns=["ts"], inplace=True)
        df = df.astype({"step": "int"})
        df = df[df["step"] >= 0]  # drop -1
        return df

    df_tgt = get_df(fn_tgt)
    df_sync = get_df(fn_sync)
    df_ag = get_df(fn_ag)

    ntot = 1000
    df_tgt_agg = df_tgt[df_tgt["tier"] == "agg"]
    df_tgt_agg = df_tgt_agg[df_tgt_agg["step"] < ntot]

    df_sync_agg = df_sync[df_sync["tier"] == "agg"]
    df_sync_agg = df_sync_agg[df_sync_agg["step"] <= ntot]

    df_agnt_agg = df_ag[df_ag["tier"] == "agg"]
    df_agnt_agg = df_agnt_agg[df_agnt_agg["step"] <= ntot]

    max_step = df_agnt_agg["step"].max()
    df_sync_agg = df_sync_agg[df_sync_agg["step"] > max_step]
    # Claude installed two flows for mpi_sync in the agentic version
    # This doubled the row counts. So double them before splicing mpi_sync.
    df_sync_agg["rows_in"] *= 2
    df_sync_agg["rows_out"] *= 2
    df_agnt_agg = pd.concat([df_agnt_agg, df_sync_agg], ignore_index=True)

    df_agnt_agg["tier"] = "agnt_agg"
    df_tgt_agg["tier"] = "tgt_agg"
    df_agg = pd.concat([df_tgt_agg, df_agnt_agg], ignore_index=True)

    return df_agg


def plot_rowcounts(df: pd.DataFrame, subfig):
    c.set_colormap("Pastel1-Dark")
    ax = subfig.subplots()

    # Warmup region (T0-T32)
    ax.axvspan(0, 83, color="#aaa", alpha=0.4)
    edge = c.darken_hsl("#aaa", 0.8, 0.5)
    ax.axvline(0, color=edge, linewidth=LINEWIDTH_THIN)
    ax.axvline(83, color=edge, linewidth=LINEWIDTH_THIN)

    # Flow markers (corresponding to top plot)
    flow_col, flow_edge = "#b3cde3", c.darken_hsl("#b3cde3", 0.2, 0.2)
    flow_markers = [(84, "1"), (278, "2"), (466, "3"), (658, "1")]
    for x, label in flow_markers:
        y = 1e2
        ax.axvline(x, color=flow_edge, linewidth=LINEWIDTH_THIN, zorder=10, linestyle="--")
        ax.scatter([x], [y], color=flow_col, edgecolor=flow_edge, linewidth=LINEWIDTH_THIN, s=MARKER_SIZE_MD, zorder=10, marker="o", clip_on=False)  # fmt: skip
        ax.text(x, y, label, ha="center", va="center", fontsize=FONTSIZE_MED, zorder=11, fontweight="bold", clip_on=False)  # fmt: skip

    df_tgt_agg = df[df["tier"] == "tgt_agg"]
    df_agnt_agg = df[df["tier"] == "agnt_agg"]

    ax.plot(df_tgt_agg["step"], df_tgt_agg["rows_in"], label="Detailed")
    ax.plot(df_agnt_agg["step"], df_agnt_agg["rows_in"], label="Agentic")
    ax.set_yscale("log")

    # Double-headed arrow showing gap at x=800
    x_annot, flag_col = 800, c.SpecialColors.FLAG.value
    y_tgt = np.interp(x_annot, df_tgt_agg["step"], df_tgt_agg["rows_in"])
    y_agnt = np.interp(x_annot, df_agnt_agg["step"], df_agnt_agg["rows_in"])
    ratio = y_tgt / y_agnt
    ax.annotate("", xy=(x_annot, y_tgt), xytext=(x_annot, y_agnt), arrowprops=dict(arrowstyle="<->", color=flag_col, lw=LINEWIDTH_MED, shrinkA=0, shrinkB=0))  # fmt: skip
    y_mid = np.sqrt(y_tgt * y_agnt)  # geometric mean for log scale
    ax.text(x_annot + 20, y_mid, f"{ratio:.0f}$\\times$", fontsize=FONTSIZE_LG, va="center", color=flag_col)  # fmt: skip
    ax.set_ylim(bottom=1e0)
    ax.set_xlabel("\\textbf{Timestep}")
    ax.set_ylabel("\\textbf{Rows/Step}")
    ax.tick_params(axis="x", pad=1)
    ax.tick_params(axis="y", pad=1)

    ax.yaxis.set_major_locator(mtick.LogLocator(base=100, numticks=20))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=100, subs=[10], numticks=20))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    def fmt_rows(x, _):
        if x >= 1e6: return f"{x/1e6:.0f}\\,M"
        if x >= 1e3: return f"{x/1e3:.0f}\\,K"
        return f"{x:.0f}"
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_rows))
    # ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs="all", numticks=20))
    ax.set_xlim(0, 1000)

    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax.xaxis.set_major_locator(mtick.MultipleLocator(100))
    ax.xaxis.set_minor_locator(mtick.MultipleLocator(25))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.legend(fontsize=FONTSIZE_LEGEND, frameon=True)


def run():
    df = load_events()
    tldata = transform_events(df)
    add_synthetic_events(tldata)
    print(tldata)

    start_evt = tldata.points[3]
    print(f"Start event: {start_evt}")

    fig = plt.figure(figsize=(c.COLWIDTH, 3.0), constrained_layout=True)
    fig.get_layout_engine().set(hspace=0.01, h_pad=0.03)
    subfigs = fig.subfigures(2, 1, height_ratios=[2, 1])
    axes = subfigs[0].subplots(3, 1, sharex=True)
    # ax_bottom = subfigs[1].subplots()

    setup_axes(axes, 2000)

    split_t = start_evt.secs
    bef_col = "#aaa"

    def is_warmup(t) -> bool:
        return t < split_t

    llm_handlers = {
        "activity": add_activity_span,
        "flow_create": add_flow_create_point,
        "polars": add_polars_point,
        "code_search": add_code_point,
        "code_read": add_code_point,
    }

    for sidx, se in enumerate(tldata.spans):
        if se.track == "app":
            add_app_span(axes, se, is_warmup, sidx)
        elif se.track == "llm":
            handler = llm_handlers[se.ev_type]
            handler(axes, se, is_warmup, sidx)

    for pidx, pe in enumerate(tldata.points):
        if pe.desc.startswith("This session is"):
            # Claude compaction
            continue
        add_user_feedback_point(axes, pe, is_warmup, pidx)

    axes[0].set_ylabel(r"\textbf{User}")
    axes[1].set_ylabel(r"\textbf{LLM}")
    axes[2].set_ylabel(r"\textbf{App}")
    axes[2].set_xlabel(r"\textbf{Wall-Clock Time (s)}")
    axes[2].xaxis.set_major_formatter(
        # mtick.FuncFormatter(lambda x, _: f"{x/60:.0f}\,m")
        mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s")
    )

    axes[2].set_xlim(0, 1599)

    make_legend(subfigs[0])

    df = load_rowcounts()
    plot_rowcounts(df, subfigs[1])

    c.save_plot(fig, "agentic_timeline")
    plt.close("all")


if __name__ == "__main__":
    import matplotlib

    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    matplotlib.use("pgf")
    plt.rcParams["pgf.texsystem"] = "lualatex"
    plt.rcParams["pgf.rcfonts"] = False
    plt.rcParams["pgf.preamble"] = (
        r"\usepackage{lmodern}"
        r"\usepackage{fontspec}"
        r"\usepackage{fontawesome5}"
        r"\newfontface\emojifont{Noto Color Emoji}[Renderer=Harfbuzz]"
    )
    c.set_colormap("Pastel1")
    run()
