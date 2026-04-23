import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import pandas as pd
import common as c
from orca_native import read_ontv_tracestats, fmt_rowcount, fmt_overhead
from tracer_runtimes import prep_runtime_data

PROFILE = "15_or_ntv_mpiwait_onlycnt"
PROFILE_LABEL = "Slow Wait Counts"
PROFILE_COLOR = "C1"
HATCH = "..."


def read_ontv_runtimes():
    df_path = c.get_plotdata_dir() / "runtimes" / "20251229.csv"
    profiles = [PROFILE]
    df = pd.read_csv(df_path)
    df = prep_runtime_data(df, profiles)
    return df


def plot_slowwait_runtimes(ax: plt.Axes):
    rdf = read_ontv_runtimes()
    rdf = rdf[rdf["profile"] == PROFILE]
    all_ranks = rdf["ranks"].unique().tolist()
    n_ranks = len(all_ranks)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    bar_width = 0.25

    for ridx, nranks in enumerate(all_ranks):
        row = rdf[rdf["ranks"] == nranks].iloc[0]
        x = ridx * bar_width
        base = row["tsecs_base_mean"]
        overhead = row["tsecs_mean"] - base
        overhead_pct = (row["ratio_mean"] - 1) * 100

        color = PROFILE_COLOR
        color_rgba = mcolors.to_rgba(color)

        base_bar = ax.bar(
            x,
            base,
            width=bar_width,
            color=color,
            ec="black",
            hatch=HATCH,
        )
        ax.bar(
            x,
            overhead,
            bottom=base,
            width=bar_width,
            color="C0",
            ec="black",
            hatch="xxx",
        )

        for b in base_bar:
            b._hatch_color = mcolors.to_rgba(c.SpecialColors.HATCH.value)
            b.stale = True

        # overhead label
        lbl = fmt_overhead(overhead_pct)
        rot = 45
        bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
        ax.text(x, base + overhead + 12, lbl, ha="left", va="bottom", fontsize=smallsz, rotation=rot, bbox=bbox)

        # rank label inside bar
        rank_lbl = f"\\sffamily\\bfseries {nranks}"
        bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
        lbl_color = c.darken_hsl(color_rgba, 0.5, 0.4)
        ax.text(
            x,
            15,
            rank_lbl,
            ha="center",
            va="bottom",
            fontsize=smallsz,
            rotation=90,
            color=lbl_color,
            bbox=bbox,
        )

    ax.set_xticks([])

    # y-axis
    ax.set_ylabel(r"\textbf{Runtime}")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(100))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(25))
    ax.set_ylim(0, 500)

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)


def plot_slowwait_rowcounts(ax: plt.Axes):
    tsdf = read_ontv_tracestats()
    tsdf = tsdf[tsdf["profile"] == PROFILE]
    all_ranks = tsdf["nranks"].unique().tolist()
    n_ranks = len(all_ranks)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    bar_width = 0.12
    in_out_gap = 0.02
    pair_width = 2 * bar_width + in_out_gap

    for ridx, nranks in enumerate(all_ranks):
        row = tsdf[tsdf["nranks"] == nranks].iloc[0]
        x_base = ridx * pair_width
        rows_in = row["fljob.nrows_in"]
        rows_out = row["fljob.nrows_out"]

        color = PROFILE_COLOR
        color_rgba = mcolors.to_rgba(color)
        color_in = color
        color_out = c.darken_hsl(color_rgba, 0.9, 1.1)

        bar_in = ax.bar(
            x_base,
            rows_in,
            width=bar_width,
            color=color_in,
            ec="black",
            hatch="///",
        )
        bout_x = x_base + bar_width + in_out_gap
        bar_out = ax.bar(
            bout_x,
            rows_out,
            width=bar_width,
            color=color_out,
            ec="black",
            hatch="\\\\\\",
        )

        for b in [bar_in[0], bar_out[0]]:
            b._hatch_color = mcolors.to_rgba(c.SpecialColors.HATCH.value)
            b.stale = True

        # reduction annotation
        reduction_pct = (1 - rows_out / rows_in) * 100
        ann = f"\\sffamily\\bfseries -{reduction_pct:.3f}\\%"
        rot = 45
        bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
        ax.text(x_base, rows_in * 1.5, ann, ha="left", va="bottom", fontsize=smallsz, rotation=rot, bbox=bbox)

        # rank label inside first bar
        rank_lbl = f"\\sffamily\\bfseries {nranks}"
        bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
        lbl_color = c.darken_hsl(color_rgba, 0.5, 0.4)
        ax.text(
            x_base,
            2e3,
            rank_lbl,
            ha="center",
            va="bottom",
            fontsize=smallsz,
            rotation=90,
            color=lbl_color,
            bbox=bbox,
        )

    ax.set_xticks([])

    # y-axis
    ax.set_yscale("log")
    ax.set_ylabel(r"\textbf{Dataframe Rows}")
    ax.set_ylim(1e3, 1e15)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_rowcount))
    ax.yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=15))
    ax.yaxis.set_minor_locator(
        mtick.LogLocator(base=1000, subs=[2, 5, 10, 20, 50, 100, 200, 500], numticks=15)
    )
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    # legend
    handles = [
        mpatches.Patch(fc="#ddd", ec="black", hatch="/////"),
        mpatches.Patch(fc="#bbb", ec="black", hatch="\\\\\\\\\\"),
    ]
    labels = ["Rows In", "Rows Out"]
    ax.legend(
        handles=handles,
        labels=labels,
        loc="upper right",
        ncol=1,
        fontsize=smallsz,
    )


def plot_slowwait_combined():
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.0))
    plot_slowwait_runtimes(axes[0])
    plot_slowwait_rowcounts(axes[1])
    fig.tight_layout(pad=0.3)
    c.save_plot(fig, "ontv_slowwait", subdir="sb")
    plt.close("all")


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "ppt.mplstyle")
    c.set_colormap("Pastel1")
    plot_slowwait_combined()
