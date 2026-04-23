#!/Users/schwifty/miniforge3/bin/python
"""Query suite plot — absolute latencies (not relative to ORCA baseline)."""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mtick
import common as c
import pandas as pd

from query_suite import (
    QUERY_MAP,
    read_query_suite_data,
    prep_query_suite_data,
    fmt_dura,
    fmt_ratio,
    adjust_annots,
)


def get_ratio_range_str(df: pd.DataFrame) -> str:
    # exclude 4096 ranks — dftracer doesn't run at that scale
    # ratios = df[df["nranks"] != 4096]["ratio"]
    ratios = df["ratio"]
    rmin, rmax = ratios.min(), ratios.max()
    return f"\\sffamily\\bfseries {rmin:.0f}$\\times$--{rmax:.0f}$\\times$"


def adjust_eb_zorder(eb: tuple):
    print("Error bar:", eb)
    _, eb_c, eb_m = eb
    for e in [*eb_c, *eb_m]:
        e.set_zorder(e.get_zorder() + 1)


def print_children_recursive(obj, lvl: int = 0):
    print(f"{'  ' * lvl}{lvl:02d}: {obj}")
    for child in obj.get_children():
        print_children_recursive(child, lvl + 1)


def hack_legend_errorbar_order(leg):
    root = leg.get_children()[0]
    rows = root.get_children()[1].get_children()

    for row in rows:
        hp = row.get_children()[0]
        draw_area = hp.get_children()[0]
        children = list(draw_area._children)

        errline = children[0]
        children = children[1:] + [errline]
        draw_area._children[:] = children
        draw_area.stale = True


def plot_query_inner(ax: plt.Axes, qdf: pd.DataFrame):
    pcat = pd.Categorical(
        qdf["profile"],
        categories=[c.Prof.ORCA_TGT, c.Prof.CALIPER_TGT, c.Prof.DFTRACER_TGT],
        ordered=True,
    )
    qdf["profile"] = pcat
    qdf = qdf.sort_values(by=["profile"])

    qdf_base = qdf[qdf["profile"] == c.Prof.ORCA_TGT].copy()
    qdf_base.drop(columns=["profile", "total_ms_std"], inplace=True)
    qdf = qdf.merge(
        qdf_base, on=["query_name", "nranks", "steps", "aggs"], suffixes=["", "_base"]
    )
    qdf["ratio"] = qdf["total_ms_mean"] / qdf["total_ms_mean_base"]
    qdf["ratio_std"] = qdf["total_ms_std"] / qdf["total_ms_mean_base"]
    print(qdf)

    zorders: dict[str, int] = {
        c.Prof.ORCA_TGT: 10,
        c.Prof.CALIPER_TGT: 8,
        c.Prof.DFTRACER_TGT: 6,
    }

    all_annots = []

    for pidx, profile in enumerate(qdf["profile"].unique()):
        pqdf = qdf[qdf["profile"] == profile]

        data_x = pqdf["nranks"]
        data_x = range(len(data_x))
        data_y = pqdf["total_ms_mean"]
        data_yerr = pqdf["total_ms_std"]
        pprops = c.PROF_PROPS[c.Prof(profile)]
        label = pprops.label
        marker = pprops.marker
        col_rgb = mcolors.to_rgba(pprops.color)
        zorder = zorders.get(c.Prof(profile), 5)
        EB_COLOR = "#333"
        eb = ax.errorbar(data_x, data_y, yerr=data_yerr, label=label, marker=marker, capsize=2, color=col_rgb, mec="black", alpha=0.7, zorder=zorder, ecolor=EB_COLOR, elinewidth=0.5, capthick=0.5) # fmt: skip
        adjust_eb_zorder(eb)

        # annotate non-ORCA profiles with ratio range
        if c.Prof(profile) != c.Prof.ORCA_TGT and "ratio" in pqdf.columns:
            mult_str = get_ratio_range_str(pqdf)
            annotsz = plt.rcParams["font.size"] - 3
            txtcolor = c.darken_rgba(col_rgb, 0.6)
            bbox = dict(facecolor="white", ec="none", alpha=0.6, pad=1)
            annot = ax.annotate(mult_str, (list(data_x)[-1], list(data_y)[-1]),
                textcoords="offset points", xytext=(0, 5), ha="center", va="bottom",
                fontsize=annotsz, color=txtcolor, bbox=bbox, rotation=7) # fmt: skip
            all_annots.append(annot)

    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels([512, 1024, 2048, 4096])
    ax.set_yscale("log")

    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmt_dura(x)))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5]))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.tick_params(axis="y", pad=1)

    # all_annots: [0] = Caliper, [1] = DFTracer
    adjust_annots(all_annots, [0], (-30, -23))
    adjust_annots(all_annots, [1], (-10, -4))


def plot_query(all_qdf: pd.DataFrame, query_types: list[str]):
    plt.close("all")
    fig, axes = plt.subplots(1, 3, figsize=(c.TEXTWIDTH * 0.5, 1.6))

    for ax, qtype in zip(axes, query_types):
        qdf = all_qdf[all_qdf["query_name"] == qtype]
        plot_query_inner(ax, qdf)
        ax.set_ylim(1.01, 100 * 60 * 1e3)
        ax.yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=20))
        ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5], numticks=20))
        lblfontsz = plt.rcParams["font.size"] - 1
        ax.set_xlabel(
            f"\\sffamily\\bfseries {QUERY_MAP[qtype]}",
            color="black",
            fontsize=lblfontsz,
        )
        ax.tick_params(axis="both", pad=1)

    fontsz = plt.rcParams["font.size"]
    fontclr = plt.rcParams["axes.labelcolor"]
    fig.text(
        0.05,
        0.082,
        r"\textbf{Ranks}",
        ha="center",
        va="bottom",
        fontsize=fontsz,
        color=fontclr,
    )
    axes[0].set_ylabel(r"\textbf{Query Latency}")
    axes[1].set_yticklabels([])
    axes[2].set_yticklabels([])

    fig.tight_layout(pad=0.1, w_pad=0.1)
    legh, legl = axes[0].get_legend_handles_labels()
    for h in legh:
        print("Legend handle:", h)
        adjust_eb_zorder(h)

    lfsz = plt.rcParams["legend.fontsize"] - 1
    lbbox = (0.25, 1.01)
    leg = fig.legend(
        legh, legl, loc="upper left", ncol=3, bbox_to_anchor=lbbox, fontsize=lfsz
    )
    print_children_recursive(leg)
    hack_legend_errorbar_order(leg)
    fig.subplots_adjust(top=0.85)
    c.save_plot(fig, "query_suite_abs")


def main():
    df = read_query_suite_data()
    gdf = prep_query_suite_data(df)
    gdf20 = gdf[gdf["steps"] == 20]
    query_types = gdf20["query_name"].unique()
    assert len(query_types) == 3

    plot_query(gdf20, query_types)


if __name__ == "__main__":
    plt.close("all")
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1-Dark")
    main()
