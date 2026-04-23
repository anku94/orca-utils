import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

import common
from orca_native import read_ontv_tracestats, fmt_rowcount, PROF_COLORS

VARIANTS_DIR = Path(__file__).parent.parent.parent / "figs" / "variants"


def plot_ontv_rowcounts_4096(ax: plt.Axes):
    tsdf = read_ontv_tracestats()
    tsdf = tsdf[tsdf["nranks"] == 4096]

    profiles = ["15_or_ntv_mpiwait_onlycnt"]
    profile_labels = [r"Slow \texttt{MPI\_Waits}"]
    n_profiles = len(profiles)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    bar_width = 0.12
    in_out_gap = 0.0
    between_pairs = 0.04
    pair_width = 2 * bar_width + between_pairs
    group_gap = 0.2
    group_width = pair_width + group_gap

    for pidx, profile in enumerate(profiles):
        row = tsdf[tsdf["profile"] == profile].iloc[0]
        x_base = pidx * group_width
        rows_in = row["fljob.nrows_in"]
        rows_out = row["fljob.nrows_out"]

        color = PROF_COLORS[profile]
        color_rgba = mcolors.to_rgba(color)
        color_in = color
        color_out = common.darken_hsl(color_rgba, 0.9, 1.1)

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
            b._hatch_color = mcolors.to_rgba(common.SpecialColors.HATCH.value)
            b.stale = True

        # reduction annotation
        reduction_pct = (1 - rows_out / rows_in) * 100
        ann = f"\\sffamily\\bfseries -{reduction_pct:.3f}\\%"
        rot = 45
        ax.text(x_base, rows_in * 1.5, ann, ha="left", va="bottom", fontsize=smallsz, rotation=rot)

    # x-axis: group labels
    group_centers = [pidx * group_width + bar_width / 2 + in_out_gap / 2 for pidx in range(n_profiles)]
    ax.set_xticks(group_centers)
    ax.set_xticklabels(profile_labels)
    ax.tick_params(axis="x", pad=1)

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
    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0] - 0.1, xlim[1] + 0.1)



if __name__ == "__main__":
    plt.style.use(common.get_plotsrc_dir() / "paper.mplstyle")
    common.set_colormap("Pastel1")
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(common.COLWIDTH * 0.4, 1.3))
    plot_ontv_rowcounts_4096(ax)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3
    handles = [
        mpatches.Patch(fc="#ddd", ec="black", hatch="/////"),
        mpatches.Patch(fc="#bbb", ec="black", hatch="\\\\\\\\\\"),
    ]
    labels = ["MPI Tier: Rows In", "MPI Tier: Rows Out"]
    fig.legend(
        handles=handles,
        labels=labels,
        loc="upper center",
        ncol=1,
        fontsize=smallsz,
    )
    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(top=0.75)
    common.save_plot(fig, VARIANTS_DIR / "ontv_rowcounts_slowwaits_4096")
    plt.close("all")
