import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

import common as c
from th_volfunc import (
    load_mat_data,
    run_volfunc_single_narrow_inner,
    run_volfunc_cdf_inner,
    VF_COLOR,
    SYNC_COLOR,
)

VARIANTS_DIR = Path(__file__).parent.parent / "figs" / "variants"
FIGSIZE = (1.75, 1.0)
FIGSIZE_STACKPLOT = (1.95, 1.0)


def remove_inset(ax):
    for child in ax.child_axes[:]:
        child.remove()
    for artist in ax.get_children()[:]:
        if type(artist).__name__ == "InsetIndicator":
            artist.remove()
        if type(artist).__name__ == "Rectangle" and artist.get_alpha() is not None and artist.get_alpha() < 1:
            artist.remove()


def make_stackplot(fig, ax, minit_row, msync_row):
    run_volfunc_single_narrow_inner(ax, minit_row[np.newaxis], msync_row[np.newaxis], 0)
    ax.set_ylabel(r"\textbf{Dura.}", labelpad=0)
    ax.yaxis.label.set_rotation(90)
    ax.get_legend().remove() if ax.get_legend() else None
    fig.tight_layout(pad=0.1)


def make_legend(fig):
    handles = [
        plt.Rectangle((0, 0), 1, 1, fc=VF_COLOR, label=r"\texttt{MPI\_Wait}"),
        plt.Rectangle((0, 0), 1, 1, fc=SYNC_COLOR, label=r"\texttt{MPI\_Allgather}"),
    ]
    fig.legend(handles=handles, loc="center", ncol=1)


def make_cdf(fig, ax, msync_row):
    run_volfunc_cdf_inner(ax, msync_row[np.newaxis], 0)
    ax.get_legend().remove() if ax.get_legend() else None
    ax.set_ylabel("")
    fig.tight_layout(pad=0.1)

    # Fix inset ylim and add translucent background
    fig.canvas.draw()
    for child in ax.child_axes:
        child.set_ylim(0, 90)
        child.axvline(1, color="black", linestyle="--", linewidth=0.75)
        bbox = child.get_tightbbox(fig.canvas.get_renderer())
        bbox_data = bbox.transformed(ax.transData.inverted())
        rect = plt.Rectangle(
            (bbox_data.x0, bbox_data.y0),
            bbox_data.width,
            bbox_data.height,
            facecolor="white",
            alpha=0.5,
            transform=ax.transData,
            zorder=child.get_zorder() - 0.1,
        )
        ax.add_patch(rect)


def make_percentile_plot(fig, ax, msync):
    """Plot 0th, 1st, 100th percentiles of MPI_Allgather durations across timesteps."""
    n_timesteps = msync.shape[0]
    timesteps = np.arange(n_timesteps)

    pct_0 = np.percentile(msync, 0, axis=1) / 1e3
    pct_1 = np.percentile(msync, 1, axis=1) / 1e3
    pct_100 = np.percentile(msync, 100, axis=1) / 1e3

    ax.plot(timesteps, pct_0, linewidth=0.75, label=r"0\textsuperscript{th}")
    ax.plot(timesteps, pct_1, linewidth=1.5, label=r"1\textsuperscript{st}")
    ax.plot(timesteps, pct_100, linewidth=0.75, label=r"100\textsuperscript{th} \%ile")

    ax.set_ylabel(r"\textbf{Sync Duration}")
    ax.set_xlim(0, 50)
    ax.set_ylim(-5, 120)

    ax.xaxis.set_major_locator(ticker.AutoLocator())
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"TS={int(x)}"))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}\\,ms"))

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    fig.tight_layout(pad=0.3)
    fig.legend(loc="outside upper center", ncol=3)
    fig.subplots_adjust(top=0.82)


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1-Dark")
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)

    minit_ndq, minit_wdq, msync_nodq, msync_wdq = load_mat_data()
    bad_ts = np.where(np.max(minit_ndq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    fig, ax = plt.subplots(figsize=FIGSIZE_STACKPLOT)
    make_stackplot(fig, ax, minit_ndq[tstoplot], msync_nodq[tstoplot])
    fig.tight_layout(pad=0.3)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_stackplot_before")

    fig, ax = plt.subplots(figsize=FIGSIZE_STACKPLOT)
    make_stackplot(fig, ax, minit_wdq[tstoplot], msync_wdq[tstoplot])
    remove_inset(ax)
    fig.tight_layout(pad=0.3)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_stackplot_after")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    make_cdf(fig, ax, msync_nodq[tstoplot])
    c.save_plot(fig, VARIANTS_DIR / "volfunc_cdf_before")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    make_cdf(fig, ax, msync_nodq[tstoplot])
    remove_inset(ax)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_cdf_before_noinset")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    make_cdf(fig, ax, msync_wdq[tstoplot])
    c.save_plot(fig, VARIANTS_DIR / "volfunc_cdf_after")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    make_cdf(fig, ax, msync_wdq[tstoplot])
    remove_inset(ax)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_cdf_after_noinset")

    fig = plt.figure(figsize=(1.5, 0.5))
    make_legend(fig)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_legend")

    # Percentile plot: percentiles of MPI_Allgather across timesteps
    fig, ax = plt.subplots(figsize=(3.0, 1.5))
    make_percentile_plot(fig, ax, msync_nodq)
    c.save_plot(fig, VARIANTS_DIR / "volfunc_pct_before")
