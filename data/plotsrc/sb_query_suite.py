import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mtick
import common as c
from query_suite import read_query_suite_data, prep_query_suite_data, fmt_dura, fmt_ratio

QUERY_TYPE = "count_mpi_wait_dur"
QUERY_LABEL = "Outlier Waits"

# Per-profile y offset for annotations (in points)
ANNOT_Y_OFFSET = {
    c.Prof.ORCA_TGT: 0,
    c.Prof.CALIPER_TGT: -30,
    c.Prof.DFTRACER_TGT: 0,
}


def plot_query_inner(ax: plt.Axes, qdf):
    import pandas as pd

    pcat = pd.Categorical(
        qdf["profile"],
        categories=[c.Prof.ORCA_TGT, c.Prof.CALIPER_TGT, c.Prof.DFTRACER_TGT],
        ordered=True,
    )
    qdf["profile"] = pcat
    qdf = qdf.sort_values(by=["profile"])

    # baseline is ORCA
    qdf_base = qdf[qdf["profile"] == c.Prof.ORCA_TGT].copy()
    qdf_base.drop(columns=["profile", "total_ms_std"], inplace=True)
    qdf = qdf.merge(
        qdf_base, on=["query_name", "nranks", "steps", "aggs"], suffixes=["", "_base"]
    )
    qdf["ratio"] = qdf["total_ms_mean"] / qdf["total_ms_mean_base"]
    qdf["ratio_std"] = qdf["total_ms_std"] / qdf["total_ms_mean_base"]

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    for pidx, profile in enumerate(qdf["profile"].unique()):
        pqdf = qdf[qdf["profile"] == profile]

        data_x = range(len(pqdf["nranks"]))
        data_y = pqdf["ratio"]
        data_yerr = pqdf["ratio_std"]
        pprops = c.PROF_PROPS[c.Prof(profile)]
        label = pprops.label
        marker = pprops.marker
        col_rgb = mcolors.to_rgba(pprops.color)
        ax.errorbar(data_x, data_y, yerr=data_yerr, label=label, marker=marker, capsize=4, color=col_rgb, mec="black", alpha=0.7)

        # duration labels
        labels = pqdf["total_ms_mean"].apply(lambda x: fmt_dura(x)).tolist()
        acol = c.darken_rgba(col_rgb, 0.5)
        bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
        y_off = 8 + ANNOT_Y_OFFSET.get(c.Prof(profile), 0)

        for x, y, lbl in zip(data_x, data_y, labels):
            ax.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, y_off), ha="center", va="bottom", fontsize=smallsz, color=acol, bbox=bbox)

    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels([512, 1024, 2048, 4096])
    ax.set_xlabel(r"\textbf{Ranks}")

    ax.set_yscale("log")
    ax.set_ylim(1.5e-1, 5e4)
    ax.set_ylabel(r"\textbf{Rel. Latency}")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmt_ratio(x)))
    ax.yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=5))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5], numticks=5))

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)


def plot_query_outlier_waits():
    df = read_query_suite_data()
    gdf = prep_query_suite_data(df)
    gdf20 = gdf[gdf["steps"] == 20]
    qdf = gdf20[gdf20["query_name"] == QUERY_TYPE].copy()

    fig, ax = plt.subplots(1, 1, figsize=(4.0, 4.0))
    plot_query_inner(ax, qdf)

    # legend
    legh, legl = ax.get_legend_handles_labels()
    lfsz = plt.rcParams["legend.fontsize"]
    fig.legend(legh, legl, loc="upper center", ncol=3, fontsize=lfsz, columnspacing=0.8, handletextpad=0.4)

    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.88)
    c.save_plot(fig, "query_outlier_waits", subdir="sb")

    sb_query_outlier_waits(fig, ax)

    plt.close("all")


def sb_query_outlier_waits(fig, ax):
    # Debug: print artist indices
    # for i, a in enumerate(ax.get_children()):
    #     print(i, type(a).__name__, getattr(a, 'get_label', lambda: '')())

    # Indices:
    #   ORCA: 0-3 (errorbar), 4-7 (annots)
    #   CALIPER: 8-11 (errorbar), 12-15 (annots)
    #   DFTRACER: 16-19 (errorbar), 20-22 (annots)

    sb = c.StagedBuildout(ax, fig, "query_outlier_waits")
    # Frame 1: Caliper + DFTracer
    sb.add_frame([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], [], [])
    # Frame 2: + ORCA
    sb.add_frame([0, 1, 2, 3, 4, 5, 6, 7], [], [])
    sb.build()


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "ppt.mplstyle")
    c.set_colormap("Pastel1-Dark")
    plot_query_outlier_waits()
