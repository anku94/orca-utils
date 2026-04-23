import numpy as np

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.transforms import ScaledTranslation

import common as c

MAT_DIR = c.get_plotdata_dir() / "ndmats"

Mat = np.ndarray
MatData = tuple[Mat, Mat, Mat, Mat]

VF_COLOR = "C0"  # Red
SYNC_COLOR = "C2"


def ordinal(n: int) -> str:
    """Return ordinal string for a number (1st, 2nd, 3rd, 4th, ...)."""
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def load_mat_data() -> MatData:
    def read_mat(mat_name: str) -> Mat:
        return np.load(MAT_DIR / mat_name)

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mi_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")
    mat_mar_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.mpiallred.npy")

    return mat_mi_nodq, mat_mi_wdq, mat_mar_nodq, mat_mar_wdq


def plot_aggregate(ax: plt.Axes, data: MatData):
    minit_ndq, minit_wdq, msync_nodq, msync_wdq = data

    ybot = [minit_ndq.mean(), minit_wdq.mean()]
    ytop = [msync_nodq.mean(), msync_wdq.mean()]
    x = np.array([0, 1])
    width = 0.7

    ax.bar(x, ybot, label=r"\texttt{MPI\_Wait}", color=VF_COLOR, width=width)
    ax.bar(x, ytop, bottom=ybot, label=r"\texttt{MPI\_Allgather}", color=SYNC_COLOR, width=width)

    ax.set_xticks(x)
    tl_bt = r"\textbf{Before}" "\n" r"\textbf{Tuning}"
    tl_aft = r"\textbf{After}" "\n" r"\textbf{Tuning}"
    ax.set_xticklabels([ tl_bt, tl_aft, ], ha="center") # fmt: skip
    ax.set_ylabel(r"\textbf{Avg. Time}")

    ax.yaxis.set_major_locator(ticker.MultipleLocator(10e3))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(2e3))
    # ax.set_ylim(0, 120e3)
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))


def plot_before_tuning(ax: plt.Axes, ax_inset: plt.Axes, data: MatData, tstoplot: int):
    minit_ndq, _, msync_nodq, _ = data

    ax.stackplot(
        np.arange(4096),
        minit_ndq[tstoplot],
        msync_nodq[tstoplot],
        labels=[r"\texttt{MPI\_Wait}", r"\texttt{MPI\_Allgather}"],
        colors=[VF_COLOR, SYNC_COLOR],
    )
    ax.set_ylim([0, 120e3])

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax.set_xticks([])

    ax.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(-0.14, 1.0)

    # Inset
    ax_inset.stackplot(
        np.arange(4096),
        minit_ndq[tstoplot],
        msync_nodq[tstoplot],
        labels=[r"\texttt{MPI\_Wait}", r"\texttt{MPI\_Allgather}"],
        colors=[VF_COLOR, SYNC_COLOR],
    )

    ax.xaxis.set_minor_locator(ticker.MultipleLocator(256))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1024))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50e3))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(10e3))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")


def plot_after_tuning(ax: plt.Axes, data: MatData, tstoplot: int):
    _, minit_wdq, _, msync_wdq = data

    ax.stackplot(
        np.arange(4096),
        minit_wdq[tstoplot],
        msync_wdq[tstoplot],
        labels=[r"\texttt{MPI\_Wait}", r"\texttt{MPI\_Allgather}"],
        colors=[VF_COLOR, SYNC_COLOR],
    )

    ax.set_ylim(0, 120e3)

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax.set_xlabel(r"\textbf{MPI Rank}")

    ax.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(-0.14, 1.0)

    ax.xaxis.set_minor_locator(ticker.MultipleLocator(256))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1024))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50e3))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(10e3))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")


def run_volfunc_inner(fig: plt.Figure, axes: list[plt.Axes]):
    ax1, ax2, ax3, ax2i = axes

    data = load_mat_data()
    minit_ndq = data[0]

    # Find a timestep with high variance
    bad_ts = np.where(np.max(minit_ndq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    plot_aggregate(ax1, data)
    plot_before_tuning(ax2, ax2i, data, tstoplot)
    plot_after_tuning(ax3, data, tstoplot)

    handles = fig.get_axes()[0].get_legend_handles_labels()[0]
    lfntsz = plt.rcParams["legend.fontsize"] - 1
    fig.legend(
        handles=handles,
        loc="upper center",
        ncol=2,
        bbox_to_anchor=(0.69, 1.01),
        fontsize=lfntsz,
    )

    # create clearance at the top for the legend
    fig.tight_layout(rect=[0, 0, 0.99, 0.93])

    tfntsz = plt.rcParams["axes.titlesize"] - 3.2
    ax1.set_title("Aggregate Telemetry" "\n(all timesteps)", fontsize=tfntsz)
    ax2.set_title("One Timestep --- Rankwise --- Before Tuning", fontsize=tfntsz)
    ax3.set_title("One Timestep --- Rankwise --- After Tuning", fontsize=tfntsz)

    tickfsz = plt.rcParams["xtick.labelsize"] - 1
    axlblfsz = plt.rcParams["axes.labelsize"] - 2
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_tick_params(labelsize=tickfsz)
        ax.yaxis.set_tick_params(labelsize=tickfsz)
        ax.xaxis.label.set_fontsize(axlblfsz)
        ax.yaxis.label.set_fontsize(axlblfsz)
        ax.tick_params(axis="both", pad=1)
        ax.set_title(ax.get_title(), pad=3, fontsize=tfntsz)

    ax1.tick_params(axis="x", labelsize=tickfsz + 1)

    # ONly for the right two axes
    for ax in [ax2, ax3]:
        ax.set_xlim(0, 4096)

        # Bring the extreme labels a little bit inwards
        for lbl in ax.get_xticklabels():
            adj_map = {"0": 0.01, "4096": -0.08}
            adj = adj_map.get(lbl.get_text(), None)
            if adj is not None:
                adj_tr = ScaledTranslation(adj, 0, fig.dpi_scale_trans)
                lbl.set_transform(lbl.get_transform() + adj_tr)


def run_volfunc_single():
    """Generate single-panel plot with just the spiky 'before tuning' panel + inset."""
    fig, ax = plt.subplots(figsize=(c.COLWIDTH * 0.85, 1.3))

    data = load_mat_data()
    minit_ndq = data[0]

    # Find a timestep with high variance
    bad_ts = np.where(np.max(minit_ndq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    # Create inset
    ax_inset = ax.inset_axes([0.6, 0.28, 0.2, 0.8], xlim=(2190, 2240), ylim=(0, 120e3))
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])

    plot_before_tuning(ax, ax_inset, data, tstoplot)

    # Add x-axis label (not in plot_before_tuning)
    ax.set_xlabel(r"\textbf{MPI Rank}")
    ax.set_xlim(0, 4096)

    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    lfntsz = plt.rcParams["legend.fontsize"] - 1

    # Inset zoom indicator
    ax.indicate_inset_zoom(ax_inset, edgecolor="black", linewidth=0.6)

    # Formatting
    tickfsz = plt.rcParams["xtick.labelsize"] - 0
    axlblfsz = plt.rcParams["axes.labelsize"] - 0
    ax.xaxis.set_tick_params(labelsize=tickfsz)
    ax.yaxis.set_tick_params(labelsize=tickfsz)
    ax.xaxis.label.set_fontsize(axlblfsz)
    ax.yaxis.label.set_fontsize(axlblfsz)
    ax.tick_params(axis="both", pad=1)
    ax.yaxis.set_label_coords(-0.16, 1.0)

    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.78)
    lbbox = (0.5, 1.41)
    ax.legend(handles, labels, loc="upper center", fontsize=lfntsz, ncols=2, bbox_to_anchor=lbbox)
    c.save_plot(fig, "lesson_volfunc_single")


def run_volfunc_single_narrow_inner(ax: plt.Axes, minit: Mat, msync: Mat, tstoplot: int):
    """Inner function for narrower single-panel stackplot."""
    # Create inset: x0, y0, width, height
    ax_inset = ax.inset_axes([0.6, 0.14, 0.3, 0.8], xlim=(2190, 2240), ylim=(0, 120e3))
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])

    # Stackplot
    ax.stackplot(
        np.arange(4096),
        minit[tstoplot],
        msync[tstoplot],
        labels=[r"\texttt{MPI\_Wait}", r"\texttt{MPI\_Allgather}"],
        colors=[VF_COLOR, SYNC_COLOR],
    )
    ax.set_ylim([0, 120e3])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax.set_xticks([])
    # ax.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    # ax.yaxis.set_label_coords(-0.14, 1.0)
    #
    # Inset
    ax_inset.stackplot(
        np.arange(4096),
        minit[tstoplot],
        msync[tstoplot],
        colors=[VF_COLOR, SYNC_COLOR],
    )
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(256))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1024))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50e3))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(10e3))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")

    # Add x-axis label (not in plot_before_tuning)
    ax.set_xlabel(r"\textbf{MPI Rank}")
    ax.set_xlim(0, 4096)

    # Inset zoom indicator
    ax.indicate_inset_zoom(ax_inset, edgecolor="black", linewidth=0.6)

    # Formatting
    tickfsz = plt.rcParams["xtick.labelsize"]
    axlblfsz = plt.rcParams["axes.labelsize"]
    ax.xaxis.set_tick_params(labelsize=tickfsz)
    ax.yaxis.set_tick_params(labelsize=tickfsz)
    ax.xaxis.label.set_fontsize(axlblfsz)
    ax.yaxis.label.set_fontsize(axlblfsz)
    ax.tick_params(axis="both", pad=1)
    ax.yaxis.set_label_coords(-0.32, 1.00)


def run_volfunc_cdf_inner(ax: plt.Axes, msync: Mat, tstoplot: int):
    """Inner function for CDF plot of MPI_Allgather times."""
    # Get MPI_Allgather times for this timestep (4096 ranks)
    allgather_times = msync[tstoplot]

    # Compute percentiles
    sorted_times = np.sort(allgather_times)
    percentiles = np.arange(1, len(sorted_times) + 1) / len(sorted_times) * 100

    # Plot
    ax.plot(percentiles, sorted_times / 1e3, color=SYNC_COLOR, linewidth=1.5)

    # Inset for 0-2nd percentile: x0, y0, width, height
    ax_inset = ax.inset_axes([0.45, 0.2, 0.3, 0.7])
    ax_inset.plot(percentiles, sorted_times / 1e3, color=SYNC_COLOR, linewidth=1.5)
    ax_inset.set_xlim(0, 2)
    # Set ylim based on data in 0-2nd percentile range
    p5_idx = int(0.02 * len(sorted_times))
    ax_inset.set_ylim(0, sorted_times[p5_idx] / 1e3 * 1.1)

    ax_inset.grid(which="major", color="#bbb")
    ax_inset.grid(which="minor", color="#ddd")
    ax_inset.set_axisbelow(True)

    ax_inset.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax_inset.xaxis.set_minor_locator(ticker.AutoMinorLocator(10))
    ax_inset.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: ordinal(x)))
    ax_inset.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax_inset.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f} ms"))
    ax_inset.tick_params(axis="both", labelsize=plt.rcParams["xtick.labelsize"] - 1, pad=1)
    ax.indicate_inset_zoom(ax_inset, edgecolor="black", linewidth=0.6)

    # Formatting
    ax.set_xlabel(r"\textbf{Percentile}")
    ax.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    # ax.yaxis.tick_right()
    # ax.yaxis.set_label_position("right")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 120)

    ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: ordinal(x)))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(10))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f} ms"))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    tickfsz = plt.rcParams["xtick.labelsize"]
    axlblfsz = plt.rcParams["axes.labelsize"]
    ax.xaxis.set_tick_params(labelsize=tickfsz)
    ax.yaxis.set_tick_params(labelsize=tickfsz)
    ax.xaxis.label.set_fontsize(axlblfsz)
    ax.yaxis.label.set_fontsize(axlblfsz)
    ax.tick_params(axis="both", pad=1)

    ax.yaxis.set_label_coords(1.04, 1.16)


def run_volfunc_single_cdf():
    """Generate 2x2 plot with stackplot (left) and CDF (right), before (top) and after (bottom)."""
    fig, axes = plt.subplots(2, 2, figsize=(3.5, 2.0))

    minit_ndq, minit_wdq, msync_nodq, msync_wdq = load_mat_data()

    # Find a timestep with high variance
    bad_ts = np.where(np.max(minit_ndq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    # Top row: before tuning
    run_volfunc_single_narrow_inner(axes[0, 0], minit_ndq, msync_nodq, tstoplot)
    run_volfunc_cdf_inner(axes[0, 1], msync_nodq, tstoplot)

    # Bottom row: after tuning
    run_volfunc_single_narrow_inner(axes[1, 0], minit_wdq, msync_wdq, tstoplot)
    run_volfunc_cdf_inner(axes[1, 1], msync_wdq, tstoplot)

    # Remove xlabels from top row
    axes[0, 0].set_xlabel("")
    axes[0, 1].set_xlabel("")

    # Set ylabels for left column to Before/After Tuning
    axes[0, 0].set_ylabel(r"\textbf{Bef. Tuning}", labelpad=0)
    axes[1, 0].set_ylabel(r"\textbf{Aft. Tuning}", labelpad=0)

    # Add "Dura." text above [0][0] yticks
    axes[0, 0].text(
        -0.15, 1.02, r"\textbf{Dura.}",
        transform=axes[0, 0].transAxes, ha="center", va="bottom",
        fontsize=plt.rcParams["axes.labelsize"] - 1,
        color=plt.rcParams["axes.labelcolor"],
    )

    # Remove ylabels from right column
    axes[0, 1].set_ylabel("")
    axes[1, 1].set_ylabel("")

    # EXPERIMENT: no yticklabels for col 1
    axes[0, 1].set_yticklabels([])
    axes[1, 1].set_yticklabels([])

    # EXPERIMENT: no xticklabels for row 0
    axes[0, 0].set_xticklabels([])
    axes[0, 1].set_xticklabels([])

    # EXPERIMENT: push extreme labels inward
    adj_map = {"0": 0.01, "1024": 0, "2048": 0, "3072": -0.03, "4096": -0.08}
    for lbl in axes[1, 0].get_xticklabels():
        adj = adj_map.get(lbl.get_text(), None)
        if adj is not None:
            adj_tr = ScaledTranslation(adj, 0, fig.dpi_scale_trans)
            lbl.set_transform(lbl.get_transform() + adj_tr)

    # EXPERIMENT: push CDF extreme labels inward
    adj_map_cdf = {"0th": 0.04, "20th": 0.01, "40th": 0, "60th": 0, "80th": -0.04, "100th": -0.06}
    for lbl in axes[1, 1].get_xticklabels():
        adj = adj_map_cdf.get(lbl.get_text(), None)
        if adj is not None:
            adj_tr = ScaledTranslation(adj, 0, fig.dpi_scale_trans)
            lbl.set_transform(lbl.get_transform() + adj_tr)

    # Remove inset and zoom indicator from bottom-left (after tuning stackplot doesn't need it)
    for child in axes[1, 0].child_axes[:]:
        child.remove()
    for artist in axes[1, 0].get_children()[:]:
        if type(artist).__name__ == "InsetIndicator":
            artist.remove()

    # Fix both CDF insets ylim and add translucent background behind tick labels
    fig.canvas.draw()  # needed to compute tight bboxes
    for parent_ax in [axes[0, 1], axes[1, 1]]:
        for child in parent_ax.child_axes:
            child.set_ylim(0, 90)
            child.axvline(1, color="black", linestyle="--", linewidth=0.75)
            # Get tight bbox including ticks/labels, in parent axes coords
            bbox = child.get_tightbbox(fig.canvas.get_renderer())
            bbox_data = bbox.transformed(parent_ax.transData.inverted())
            rect = plt.Rectangle(
                (bbox_data.x0, bbox_data.y0),
                bbox_data.width,
                bbox_data.height,
                facecolor="white",
                alpha=0.5,
                transform=parent_ax.transData,
                zorder=child.get_zorder() - 0.1,
            )
            parent_ax.add_patch(rect)

    # Add legend for left panel
    handles, labels = axes[0, 0].get_legend_handles_labels()
    lfntsz = plt.rcParams["legend.fontsize"] - 1
    fig.legend(
        handles,
        labels,
        loc="upper center",
        fontsize=lfntsz,
        ncols=2,
        bbox_to_anchor=(0.5, 1.02),
    )

    #fig.tight_layout(pad=0.5, h_pad=0.5, w_pad=0.5)
    fig.tight_layout(pad=0.5)
    fig.subplots_adjust(top=0.90)
    c.save_plot(fig, "lesson_volfunc_single_cdf")


def run_volfunc():
    fig = plt.figure(figsize=(c.COLWIDTH, 1.8))
    outer_gs = GridSpec(
        2,
        2,
        width_ratios=[1, 3],
        height_ratios=[0.7, 10],
        wspace=0.25,
        hspace=0.3,
        figure=fig,
    )
    ax1 = fig.add_subplot(outer_gs[:, 0])

    right_gs = GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer_gs[1, 1], hspace=0.6, wspace=0.25
    )

    ax2 = fig.add_subplot(right_gs[0])
    ax3 = fig.add_subplot(right_gs[1])

    ax2i = ax2.inset_axes([0.6, 0.28, 0.2, 0.8], xlim=(2190, 2240), ylim=(0, 120e3))
    ax2i.set_xticks([])
    ax2i.set_yticks([])

    run_volfunc_inner(fig, [ax1, ax2, ax3, ax2i])
    ax2.indicate_inset_zoom(ax2i, edgecolor="black", linewidth=0.6)
    fig.subplots_adjust(bottom=0.15, right=0.97, left=0.1)

    outer_gs.update(wspace=0.3, hspace=0.13, left=0.13, right=0.99, bottom=0.14)

    plot_fname = "lesson_volfunc_zoom"
    c.save_plot(fig, plot_fname)
    return


if __name__ == "__main__":
    import sys

    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1-Dark")

    run_volfunc_single()
    run_volfunc_single_cdf()
