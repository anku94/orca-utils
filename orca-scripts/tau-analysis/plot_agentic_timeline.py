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

import suite_utils as su

# Import paper plotting conventions
import sys
sys.path.insert(0, "/users/ankushj/llm-thinkspace/mon-paper/data/plotsrc")
import common as c

# Simplified event type mapping
EVENT_MAP = {
    "feedback": "feedback",
    "flow_create": "flow",
    "flow_install": "flow",
    "code_search": "code",
    "code_read": "code",
    "resume": "resume",
    "pause": "pause",
    "disable_probe": "disable",
    "disable_tracers": "disable",
}

# Event styles: (facecolor, edgecolor, marker, size)
# Using darker colors with edges
EVENT_STYLES = {
    "feedback": ("C0", "black", "o", 40),
    "flow": ("C1", "black", "s", 45),
    "code": ("C2", "black", "^", 40),
}

# Simplified band colors: just 2 colors
BAND_COLORS = {
    "app": "C3",      # app running periods
    "analysis": "C4", # LLM analysis periods
}


def load_events() -> pd.DataFrame:
    """Load timeline events from CSV"""
    data_dir = su.get_repo_data_dir() / "agentic-data"
    csv_path = data_dir / "timeline_events.csv"
    df = pd.read_csv(csv_path)
    # Map to simplified event types
    df["event_simple"] = df["event_type"].map(EVENT_MAP).fillna("other")
    return df


def get_running_periods(df: pd.DataFrame) -> list[tuple[float, float, int]]:
    """Extract (start, end, flow_num) tuples for running periods"""
    periods = []
    app_events = df[df["track"] == "app"].sort_values("t_secs")

    current_start = None
    current_flow = 0
    flow_installs = 0

    for _, row in app_events.iterrows():
        t = row["t_secs"] / 60  # minutes
        etype = row["event_type"]

        if etype == "flow_install":
            flow_installs += 1
            current_flow = flow_installs - 1  # 0-indexed

        if etype == "resume":
            current_start = t
        elif etype == "pause" and current_start is not None:
            periods.append((current_start, t, current_flow))
            current_start = None

    return periods


def setup_axes(axes: list[plt.Axes], max_time: float):
    """Configure axes with proper grid and ticks"""
    for i, ax in enumerate(axes):
        # Grid - vertical only
        ax.grid(which="major", axis="x", color="#bbb", linewidth=0.5)
        ax.grid(which="minor", axis="x", color="#ddd", linewidth=0.3)
        ax.grid(which="both", axis="y", visible=False)
        ax.set_axisbelow(True)

        # X limits
        ax.set_xlim(0, max_time + 0.5)

        # X ticks - only on bottom
        ax.xaxis.set_major_locator(mtick.MultipleLocator(5))
        ax.xaxis.set_minor_locator(mtick.MultipleLocator(1))

        if i < len(axes) - 1:
            ax.tick_params(axis="x", labelbottom=False)
        else:
            ax.set_xlabel("Time (minutes)")

        # Y axis - minimal
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([0])
        ax.tick_params(axis="y", length=0)


def plot_marker_with_line(ax: plt.Axes, x_vals, fc, ec, marker, size):
    """Plot markers with vertical black lines through them"""
    y_vals = [0] * len(x_vals)
    # Draw vertical lines first
    for x in x_vals:
        ax.plot([x, x], [-0.4, 0.4], color="black", linewidth=0.8, zorder=5)
    # Draw markers on top
    ax.scatter(x_vals, y_vals, c=fc, edgecolors=ec, marker=marker, s=size, zorder=10, linewidths=0.5)


def plot_user_track(ax: plt.Axes, df: pd.DataFrame):
    """Plot user feedback events"""
    user_df = df[df["event_simple"] == "feedback"]
    style = EVENT_STYLES["feedback"]
    fc, ec, marker, size = style

    x_vals = (user_df["t_secs"] / 60).tolist()
    plot_marker_with_line(ax, x_vals, fc, ec, marker, size)
    ax.set_yticklabels(["User"])


def get_llm_activity_periods(df: pd.DataFrame) -> list[tuple[float, float, str]]:
    """Extract LLM activity periods: (start, end, activity_type)

    Activity types:
    - 'analysis': after app pause, analyzing data
    - 'code': code search/read investigation
    - 'flow': designing/writing flow
    """
    periods = []
    df_sorted = df.sort_values("t_secs")

    # Find analysis periods: after pause until next flow or user feedback
    pauses = df_sorted[(df_sorted["event_type"] == "pause")]["t_secs"].tolist()

    for pause_t in pauses:
        pause_min = pause_t / 60
        # Find next significant event after pause
        next_events = df_sorted[
            (df_sorted["t_secs"] > pause_t) &
            (df_sorted["event_simple"].isin(["flow", "feedback"]))
        ]
        if len(next_events) > 0:
            end_t = next_events.iloc[0]["t_secs"] / 60
            if end_t - pause_min > 0.5:  # at least 30s of analysis
                periods.append((pause_min, end_t, "analysis"))

    # Find code investigation periods: clusters of code events
    code_events = df_sorted[df_sorted["event_simple"] == "code"]["t_secs"].tolist()
    if code_events:
        # Group nearby code events (within 2 min)
        clusters = []
        cluster_start = code_events[0]
        cluster_end = code_events[0]
        for t in code_events[1:]:
            if t - cluster_end < 120:  # 2 min gap
                cluster_end = t
            else:
                clusters.append((cluster_start / 60, cluster_end / 60))
                cluster_start = t
                cluster_end = t
        clusters.append((cluster_start / 60, cluster_end / 60))

        for start, end in clusters:
            # Extend slightly before/after
            periods.append((start - 0.3, end + 0.5, "code"))

    return periods


def plot_llm_track(ax: plt.Axes, df: pd.DataFrame):
    """Plot LLM flow and code events with activity bands"""
    # Plot activity bands first (behind markers) - all use same analysis color
    activity_periods = get_llm_activity_periods(df)

    for start, end, atype in activity_periods:
        ax.axvspan(start, end, alpha=0.3, color=BAND_COLORS["analysis"], zorder=1)

    # Plot markers
    llm_df = df[df["track"] == "llm"]

    for event_type in ["flow", "code"]:
        subset = llm_df[llm_df["event_simple"] == event_type]
        if len(subset) == 0:
            continue
        style = EVENT_STYLES[event_type]
        fc, ec, marker, size = style

        x_vals = (subset["t_secs"] / 60).tolist()
        plot_marker_with_line(ax, x_vals, fc, ec, marker, size)

    ax.set_yticklabels(["LLM"])


def plot_app_track(ax: plt.Axes, df: pd.DataFrame):
    """Plot app running periods as shaded bands"""
    periods = get_running_periods(df)

    for start, end, flow_num in periods:
        ax.axvspan(start, end, alpha=0.4, color=BAND_COLORS["app"], zorder=1)

    ax.set_yticklabels(["App"])


def add_legend(fig: plt.Figure):
    """Add legend with event types and band colors"""
    handles = []
    labels = []

    # Event markers
    for event_type, label in [("feedback", "Feedback"), ("flow", "Flow"), ("code", "Code")]:
        fc, ec, marker, size = EVENT_STYLES[event_type]
        h = mlines.Line2D(
            [], [], color=fc, marker=marker, markeredgecolor=ec,
            linestyle="None", markersize=6, markeredgewidth=0.5
        )
        handles.append(h)
        labels.append(label)

    # Band colors (simplified: just 2)
    h_app = mpatches.Patch(facecolor=BAND_COLORS["app"], alpha=0.4, edgecolor="none")
    handles.append(h_app)
    labels.append("App Running")

    h_analysis = mpatches.Patch(facecolor=BAND_COLORS["analysis"], alpha=0.3, edgecolor="none")
    handles.append(h_analysis)
    labels.append("LLM Analysis")

    fig.legend(
        handles=handles, labels=labels,
        loc="upper center", bbox_to_anchor=(0.5, 1.0),
        ncol=len(handles), fontsize=7,
        handletextpad=0.3, columnspacing=0.8,
    )


def run():
    df = load_events()
    print(f"Loaded {len(df)} events, duration: {df['t_secs'].max()/60:.1f} min")

    max_time = df["t_secs"].max() / 60

    fig, axes = plt.subplots(3, 1, figsize=(c.TEXTWIDTH, 1.8), sharex=True)
    fig.subplots_adjust(hspace=0.1)

    setup_axes(axes, max_time)

    plot_user_track(axes[0], df)
    plot_llm_track(axes[1], df)
    plot_app_track(axes[2], df)

    add_legend(fig)

    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.85, hspace=0.15)

    c.save_plot(fig, "agentic_timeline")
    plt.close("all")


if __name__ == "__main__":
    plt.style.use("/users/ankushj/llm-thinkspace/mon-paper/data/plotsrc/paper.mplstyle")
    plt.rcParams["text.usetex"] = False
    c.set_colormap("Pastel1-Dark")  # Darkened pastel
    run()
