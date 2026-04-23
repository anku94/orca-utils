import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

from common import PlotSaver

MAT_DIR = "../plot_data/ndmats"
import os

os.listdir(MAT_DIR)


def plot_scatter(mat_cf, mat_fd):
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    ax.clear()

    mat_cf.shape
    mat_fd.shape
    mat_fd = mat_fd[1:, :]

    # plot a normalized histogram of mat_cf, it is a 2D array (so a PDF)
    ax.hist2d(mat_cf.flatten(), mat_fd.flatten(), bins=100, cmap="Blues")
    ax.hist(mat_cf.flatten(),
            bins=100,
            alpha=0.5,
            color="C0",
            label="CalculateFluxes")
    ax.hist(mat_fd.flatten(),
            bins=100,
            alpha=0.5,
            color="C1",
            label="FillDerived")

    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))

    # ---
    ax.clear()
    # plot mat_cf as a heatmap
    ax.imshow(mat_cf, cmap="Blues", aspect="auto")

    fig.show()
    plt.close(fig)
    pass


def run_volfunc_inner(fig: plt.Figure, axes: list[plt.Axes]):
    vf_color = "C1"
    sync_color = "C0"

    ax1, ax2, ax3, ax2i = axes

    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mi_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")
    mat_mar_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.mpiallred.npy")

    nelems = 4096 * 601

    mi_bef = mat_mi_nodq.sum() / nelems
    mi_aft = mat_mi_wdq.sum() / nelems
    mar_bef = mat_mar_nodq.sum() / nelems
    mar_aft = mat_mar_wdq.sum() / nelems

    # fig = plt.figure(figsize=(10, 7), layout="constrained")

    # ---- Plot 1 -----
    ybot = np.array([mi_bef, mi_aft])
    ytop = np.array([mar_bef, mar_aft])
    x = np.array([0, 1])
    width = 0.7

    ybot
    ytop

    ax = ax1
    if ax:
        ax.bar(x, ybot, label="Volatile Function", color=vf_color, width=width)
        ax.bar(x,
               ytop,
               bottom=ybot,
               label="MPI Collective",
               color=sync_color,
               width=width)

        ax.set_xticks(x)
        ax.set_xticklabels([
            r"\textbf{Before}"
            "\n"
            r"\textbf{Tuning}",
            r"\textbf{After}"
            "\n"
            r"\textbf{Tuning}",
        ],
                           ha="center")
        ax.set_ylabel(r"\textbf{Avg. Time}")

        ax.grid(which="major", color="#bbb")
        ax.grid(which="minor", color="#ddd")
        ax.set_axisbelow(True)

        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))

    # ---- Plot 2 -----

    bad_ts = np.where(np.max(mat_mi_nodq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    # code for a stackplot of meshinit and mpiallred for a bad timestep, x is ranks
    ax = ax2
    ax.stackplot(
        np.arange(4096),
        mat_mi_nodq[tstoplot],
        mat_mar_nodq[tstoplot],
        # labels=["MeshInit", "MPIAllRed"],
        labels=["Volatile Function", "MPI Collective"],
        # colors
        colors=[vf_color, sync_color],
    )
    ax2.set_ylim([0, 120e3])
    ax2.set_title("Before Tuning", fontsize=16)

    ax2.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax2.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax2.set_xticks([])

    ax2.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    ax2.yaxis.set_label_coords(-0.14, 1.05)

    # --- Plot 2 inset ---
    data_x = np.arange(4096)
    data_y1 = mat_mi_nodq[tstoplot]
    data_y2 = mat_mar_nodq[tstoplot]
    labels = ["Volatile Function", "MPI Collective"]
    ax2i.stackplot(data_x,
                   data_y1,
                   data_y2,
                   labels=labels,
                   colors=[vf_color, sync_color])

    ax2.xaxis.set_minor_locator(ticker.MultipleLocator(256))
    ax2.xaxis.set_major_locator(ticker.MultipleLocator(1024))
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(50e3))
    ax2.yaxis.set_minor_locator(ticker.MultipleLocator(10e3))
    ax2.grid(which="major", color="#bbb")
    ax2.grid(which="minor", color="#ddd")

    # ---- Plot 3 -----

    ax = ax3
    ax.stackplot(
        np.arange(4096),
        mat_mi_wdq[tstoplot],
        mat_mar_wdq[tstoplot],
        labels=["MeshInit", "MPIAllRed"],
        colors=[vf_color, sync_color],
    )

    ax3.set_title("After Tuning", fontsize=16)
    ax3.set_ylim(0, 120e3)

    ax3.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax3.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax3.set_xlabel(r"\textbf{MPI Rank}")

    ax3.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    ax3.yaxis.set_label_coords(-0.14, 1.05)

    ax3.xaxis.set_minor_locator(ticker.MultipleLocator(256))
    ax3.xaxis.set_major_locator(ticker.MultipleLocator(1024))
    ax3.yaxis.set_major_locator(ticker.MultipleLocator(50e3))
    ax3.yaxis.set_minor_locator(ticker.MultipleLocator(10e3))
    ax3.grid(which="major", color="#bbb")
    ax3.grid(which="minor", color="#ddd")

    handles = fig.get_axes()[0].get_legend_handles_labels()[0]
    l = fig.legend(handles=handles,
                   loc="upper center",
                   ncol=2,
                   bbox_to_anchor=(0.7, 0.999),
                   fontsize=15)
    # l.remove()

    # create clearance at the top for the legend
    fig.tight_layout(rect=[0, 0, 0.99, 0.93])

    ax1.set_title("Aggregate Telemetry", fontsize=16)
    ax1.set_title("Aggregate Telemetry"
                  "\n(all timesteps)", fontsize=16)
    ax2.set_title("One Timestep - Rankwise - Before Tuning", fontsize=16)
    ax3.set_title("One Timestep - Rankwise - After Tuning", fontsize=16)

    ax1.xaxis.set_tick_params(labelsize=16)
    ax1.yaxis.set_tick_params(labelsize=16)
    ax2.xaxis.set_tick_params(labelsize=16)
    ax2.yaxis.set_tick_params(labelsize=16)
    ax3.xaxis.set_tick_params(labelsize=16)
    ax3.yaxis.set_tick_params(labelsize=16)


def plot_stackplot_before(ax):
    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")

    bad_ts = np.where(np.max(mat_mi_nodq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    # code for a stackplot of meshinit and mpiallred for a bad timestep, x is ranks
    ax = ax
    ax.stackplot(
        np.arange(4096),
        mat_mi_nodq[tstoplot],
        mat_mar_nodq[tstoplot],
        # labels=["MeshInit", "MPIAllRed"],
        labels=["Volatile Function", "Global Sync"],
    )
    ax.set_ylim([0, 120e3])
    # ax.set_title("Before Tuning", fontsize=16)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    # ax.set_xticks([])


def plot_stackplot_after(ax):
    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mi_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.meshinit.npy")
    mat_mar_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.mpiallred.npy")

    bad_ts = np.where(np.max(mat_mi_nodq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    ax.stackplot(
        np.arange(4096),
        mat_mi_wdq[tstoplot],
        mat_mar_wdq[tstoplot],
        labels=["MeshInit", "MPIAllRed"],
    )

    ax.set_title("After Tuning", fontsize=16)
    ax.set_ylim(0, 120e3)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax.set_xlabel("MPI Rank")


def run_volfunc_half_inner(ax):
    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))
    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")

    bad_ts = np.where(np.max(mat_mi_nodq, axis=1) > 40e3)
    tstoplot = bad_ts[0][0]

    mi_bef = mat_mi_nodq[tstoplot].mean()
    mar_bef = mat_mar_nodq[tstoplot].mean()

    # mi_bef = mat_mi_nodq.sum() / (4096 * 601)
    # mar_bef = mat_mar_nodq.sum() / (4096 * 601)

    ax.clear()
    ax.bar([0], mi_bef, color="C0", width=0.7)
    ax.bar([0], mar_bef, bottom=mi_bef, color="C1", width=0.7)
    ax.set_xlim(-0.5, 0.5)

    ax.set_xticks([])
    ax.set_ylabel(r"\textbf{Time (ms)}")
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f} ms"))
    ax.set_ylim(0, 120e3)


def run_volfunc_half():
    fig = plt.figure(figsize=(7, 4))
    fig.clear()

    gs = plt.GridSpec(1, 2, width_ratios=[1, 3])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    run_volfunc_half_inner(ax1)
    plot_stackplot_before(ax2)
    ax2.set_yticks([])
    ax2.set_ylim(0, 120e3)

    fig.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.6, 0.99))
    fig.tight_layout(rect=[0, 0, 0.99, 0.91])

    ax2.set_xlim(2100, 2300)
    ax2.set_xlabel("Worker ID")

    ax1.set_xlabel("Avg Time")
    PlotSaver.save(fig, "", None, "lesson_volfunc_v2_short_half")

    plt.close(fig)


def run_volfunc():
    # fig = plt.figure(figsize=(10, 7))
    # fig = plt.figure(figsize=(8, 4.2))
    global fig

    fig.clear()
    outer_gs = GridSpec(2,
                        2,
                        width_ratios=[1, 3],
                        height_ratios=[0.7, 10],
                        wspace=0.25,
                        hspace=0.3,
                        figure=fig)
    ax1 = fig.add_subplot(outer_gs[:, 0])

    right_gs = GridSpecFromSubplotSpec(2,
                                       1,
                                       subplot_spec=outer_gs[1, 1],
                                       hspace=0.55,
                                       wspace=0.2)

    ax2 = fig.add_subplot(right_gs[0])
    ax3 = fig.add_subplot(right_gs[1])

    ax2i = ax2.inset_axes([0.6, 0.28, 0.2, 0.8],
                          xlim=(2190, 2240),
                          ylim=(0, 120e3))
    ax2i.set_xticks([])
    ax2i.set_yticks([])

    # [ax.clear() for ax in [ax1, ax2, ax3, ax2i]]
    run_volfunc_inner(fig, [ax1, ax2, ax3, ax2i])
    ax2.indicate_inset_zoom(ax2i, edgecolor="black", linewidth=2)
    fig.subplots_adjust(bottom=0.15, right=0.97, left=0.1)

    outer_gs.update(wspace=0.27,
                    hspace=0.13,
                    left=0.12,
                    right=0.99,
                    bottom=0.13)

    # plot_fname = "lesson_volfunc_v2_short_zoom"
    # PlotSaver.save(fig, "", None, plot_fname)
    # plt.close("all")
    return

    # set padding between fig elements to 0

    # bump up font size for ax2 yticks

    fig.set_constrained_layout_pads(w_pad=0.06,
                                    h_pad=0.06,
                                    wspace=0.01,
                                    hspace=0.01)

    # for v2-short, retreat poster
    fig.clear()
    plt.close(fig)
    gs = plt.GridSpec(2, 2, width_ratios=[1, 3], height_ratios=[1, 1])

    ax1 = fig.add_subplot(gs[:, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 1])

    # get artist for fig.legend

    plot_fname = "lesson_volfunc_v2_short"
    # fig.show()

    PlotSaver.save(fig, "", None, plot_fname)

    fig, axes = plt.subplots(2, 1, figsize=(8, 7))
    ax0, ax1 = axes
    run_volfunc_inner(fig, [None, ax0, ax1])
    ax1.set_xlim(2100, 2300)
    ax0.set_xlim(2100, 2300)
    fig.tight_layout(rect=[0, 0, 0.99, 0.93])
    plot_fname = "lesson_volfunc_v2_short_zoom"
    PlotSaver.save(fig, "", None, plot_fname)
    plt.close(fig)


def run_volfunc_stack3():
    pass


def run_volfunc_avg():
    vf_color = "C0"
    sync_color = "C1"

    plt.close("all")
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))

    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")
    a = mat_mi_nodq.sum(axis=0)
    b = mat_mar_nodq.sum(axis=0)
    ax.clear()

    anorm = a / (a + b)
    bnorm = b / (a + b)

    ax.stackplot(
        np.arange(4096),
        anorm,
        bnorm,
        labels=["Function (\%)", "Global Sync (\%)"],
        colors=[vf_color, sync_color],
    )

    leg = ax.legend(ncol=2,
                    loc="upper center",
                    bbox_to_anchor=(0.5, 1.3),
                    fontsize=15,
                    frameon=True)
    leg.remove()

    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{x*100:.0f} \%"))
    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.set_xlabel(r"\textbf{MPI Rank}")
    ax.set_ylabel(r"\textbf{Time}", rotation=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(-0.12, 1.05)
    fig.tight_layout(rect=[0, 0, 0.99, 0.93])

    plot_fname = "lesson_volfunc_avg"
    PlotSaver.save(fig, "", None, plot_fname)
    plt.close(fig)

    pass


def run():
    mat_cf_name = "nd4096wdq.hybrid25.cmx8192.calcflx.npy"
    mat_fd_name = "nd4096wdq.hybrid25.cmx8192.fillder.npy"

    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_cf = np.load(os.path.join(MAT_DIR, mat_cf_name))
    mat_fd = np.load(os.path.join(MAT_DIR, mat_fd_name))

    mat_cf = read_mat("nd4096wdq.hybrid25.cmx8192.calcflx.npy")
    mat_fd = read_mat("nd4096wdq.hybrid25.cmx8192.fillder.npy")

    mat_cf.shape

    read_mat = lambda mat_name: np.load(os.path.join(MAT_DIR, mat_name))

    mat_mi_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.meshinit.npy")
    mat_mar_nodq = read_mat("nd4096nodq.hybrid25.cmx8192.norcv.mpiallred.npy")
    mat_mi_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.meshinit.npy")
    mat_mar_wdq = read_mat("nd4096wdq.hybrid25.cmx8192.mpiallred.npy")

    bad_ts = np.where(np.max(mat_mi_nodq, axis=1) > 40e3)
    len(bad_ts[0])
    tstoplot = bad_ts[0][0]
    bad_ts

    mat_mi_nodq[tstoplot].mean()
    mat_mar_nodq[tstoplot].mean()
    mat_mi_wdq[tstoplot].mean()
    mat_mar_wdq[tstoplot].mean()

    pass


if __name__ == "__main__":
    plt.close("all")
    plt.style.use("././paper.mplstyle")
    cmap = plt.colormaps["Dark2"]
    colors = [cmap(i) for i in range(cmap.N)]
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=colors)
    plt.close("all")
    run()

    fig = plt.figure(figsize=(8, 4.2))
    run_volfunc()
    plot_fname = "lesson_volfunc_v2_short_zoom"
    PlotSaver.save(fig, "", None, plot_fname)
    plt.close("all")
