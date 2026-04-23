import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import common
from pathlib import Path
from tracer_runtimes import prep_runtime_data
from query_suite import RunParams, infer_run_params

PROF_LABELS = {
    "15_or_ntv_mpiwait_onlycnt": f"Slow Waits: \emph{{Counts}}",
    "16_or_ntv_mpiwait_tracecnt": f"Slow Waits: \emph{{Traces}}",
    "17_or_ntv_kokkos": "Kokkos Kernels",
}

PROF_COLORS = {
    "15_or_ntv_mpiwait_onlycnt": "C1",
    "16_or_ntv_mpiwait_tracecnt": "C1",
    "17_or_ntv_kokkos": "C3",
}

HATCHES = {
    "15_or_ntv_mpiwait_onlycnt": "...",
    "16_or_ntv_mpiwait_tracecnt": "ooo",
    "17_or_ntv_kokkos": "+++",
}


def read_ontv_runtimes():
    df_path = common.get_plotdata_dir() / "runtimes" / "20251229.csv"
    profiles = [
        "15_or_ntv_mpiwait_onlycnt",
        "16_or_ntv_mpiwait_tracecnt",
        "17_or_ntv_kokkos",
    ]
    df = prep_runtime_data(df_path, profiles)
    return df


def read_ontv_tracestats():
    df_path = common.get_plotdata_dir() / "tracestats" / "20251229.csv"
    profiles = [
        "15_or_ntv_mpiwait_onlycnt",
        "16_or_ntv_mpiwait_tracecnt",
        "17_or_ntv_kokkos",
    ]
    df = pd.read_csv(df_path)
    df = df[df["profile"].isin(profiles)]
    df_agg = df.groupby(["suite", "profile", "tracedir"], as_index=False).agg(
        {
            "fljob.nrows_in": "sum",
            "fljob.nrows_out": "sum",
        }
    )
    all_run_params = [
        infer_run_params(Path(tracedir)) for tracedir in df_agg["tracedir"]
    ]
    pdf = pd.DataFrame(all_run_params)
    df_agg = df_agg.merge(
        pdf, left_index=True, right_index=True, how="left", suffixes=["", "_o"]
    )
    df_agg = df_agg[df_agg["steps"] == 2000]
    df_agg = df_agg.groupby(["profile", "nranks"], as_index=False).agg(
        {
            "fljob.nrows_in": "sum",
            "fljob.nrows_out": "sum",
        }
    )
    df_agg["nrows_ratio"] = df_agg["fljob.nrows_out"] / df_agg["fljob.nrows_in"]

    return df_agg


def fmt_rowcount(x: float, pos=None) -> str:
    if x == 1e12:
        return f"{x/1e12:.0f}\,T"
    if x == 1e9:
        return f"{x/1e9:.0f}\,B"
    elif x == 1e6:
        return f"{x/1e6:.0f}\,M"
    elif x == 1e3:
        return f"{x/1e3:.0f}\,K"
    else:
        return ""


def fmt_overhead(x: float) -> str:
    if x < 10:
        xval = f"{x:.1f}"
    else:
        xval = f"{x:.0f}"
    return f"\\sffamily\\bfseries +{xval}\\%"


def plot_ontv_runtimes(ax: plt.Axes):
    rdf = read_ontv_runtimes()
    profiles = rdf["profile"].unique().tolist()
    all_ranks = rdf["ranks"].unique().tolist()
    n_profiles = len(profiles)
    n_ranks = len(all_ranks)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    bar_width = 0.18
    group_gap = 0.25
    group_width = n_ranks * bar_width + group_gap

    for pidx, profile in enumerate(profiles):
        rdf_prof = rdf[rdf["profile"] == profile]
        for ridx, nranks in enumerate(all_ranks):
            row = rdf_prof[rdf_prof["ranks"] == nranks].iloc[0]
            x = pidx * group_width + ridx * bar_width
            base = row["tsecs_base_mean"]
            overhead = row["tsecs_mean"] - base
            overhead_pct = (row["ratio_mean"] - 1) * 100

            color = PROF_COLORS[profile]
            color_rgba = mcolors.to_rgba(color)

            base_bar = ax.bar(
                x,
                base,
                width=bar_width,
                color=color,
                ec="black",
                hatch=HATCHES[profile],
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
                # b._hatch_color = (0.5, 0.5, 0.5, 1.0)
                b._hatch_color = mcolors.to_rgba(common.SpecialColors.HATCH.value)
                b.stale = True

            # overhead label (vertical, rotated)
            lbl = fmt_overhead(overhead_pct)
            rot = 45
            ax.text(x, base + overhead + 12, lbl, ha="left", va="bottom", fontsize=smallsz, rotation=rot) # fmt: skip

            # rank label inside bar (vertical, light gray)
            rank_lbl = f"\\sffamily\\bfseries {nranks} ranks"
            bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
            lbl_color = common.darken_hsl(color_rgba, 0.5, 0.4)
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

    # x-axis: group labels (query type)
    group_centers = [
        pidx * group_width + (n_ranks - 1) * bar_width / 2 for pidx in range(n_profiles)
    ]
    ax.set_xticks(group_centers)
    ax.set_xticklabels([PROF_LABELS[p] for p in profiles])
    ax.tick_params(axis="x", pad=1)

    # y-axis
    ax.set_ylabel(r"\textbf{Runtime}")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(100))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(25))
    ax.set_ylim(0, 500)

    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0], xlim[1] + 0.1)

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)


def plot_ontv_rowcounts(ax: plt.Axes):
    tsdf = read_ontv_tracestats()
    # Skip B, use A/B label for first group
    profiles = ["15_or_ntv_mpiwait_onlycnt", "17_or_ntv_kokkos"]
    profile_labels = ["Slow Waits", "Kokkos Kernels"]
    all_ranks = tsdf["nranks"].unique().tolist()
    n_profiles = len(profiles)
    n_ranks = len(all_ranks)

    fontsz = plt.rcParams["font.size"]
    smallsz = fontsz - 3

    bar_width = 0.08
    in_out_gap = 0.0
    between_pairs = 0.03
    pair_width = 2 * bar_width + between_pairs
    group_gap = 0.15
    group_width = n_ranks * pair_width + group_gap

    for pidx, profile in enumerate(profiles):
        tsdf_prof = tsdf[tsdf["profile"] == profile]
        for ridx, nranks in enumerate(all_ranks):
            row = tsdf_prof[tsdf_prof["nranks"] == nranks].iloc[0]
            x_base = pidx * group_width + ridx * pair_width
            rows_in = row["fljob.nrows_in"]
            rows_out = row["fljob.nrows_out"]

            color = PROF_COLORS[profile]
            # convert color to rgba
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

            # set hatch color to grey
            for b in [bar_in[0], bar_out[0]]:
                b._hatch_color = mcolors.to_rgba(common.SpecialColors.HATCH.value)
                b.stale = True

            # reduction annotation
            reduction_pct = (1 - rows_out / rows_in) * 100
            ann = f"\\sffamily\\bfseries -{reduction_pct:.3f}\\%"
            rot = 45
            ax.text(x_base, rows_in * 1.5, ann, ha="left", va="bottom", fontsize=smallsz, rotation=rot) # fmt: skip

            # rank label inside first bar
            rank_lbl = f"\\sffamily\\bfseries {nranks} ranks"
            bbox = dict(facecolor="white", ec="none", alpha=0.5, pad=0.5)
            lbl_color = common.darken_hsl(color_rgba, 0.5, 0.4)
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

    # x-axis: group labels
    group_centers = [
        pidx * group_width + (n_ranks * pair_width - between_pairs) / 2 - bar_width / 2
        for pidx in range(n_profiles)
    ]
    ax.set_xticks(group_centers)
    ax.set_xticklabels(profile_labels)
    ax.tick_params(axis="x", pad=1)

    # y-axis
    ax.set_yscale("log")
    ax.set_ylabel(r"\textbf{Dataframe Rows}")
    ax.set_ylim(1e3, 1e15)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_rowcount))
    ax.yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=15))
    # ax.set_yticks([1e3, 1e6, 1e9, 1e12])
    ax.yaxis.set_minor_locator(
        mtick.LogLocator(base=1000, subs=[2, 5, 10, 20, 50, 100, 200, 500], numticks=15)
    )
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0], xlim[1] + 0.1)

    # create two handles with patches with hatches
    handles = [
        mpatches.Patch(fc="#ddd", ec="black", hatch="/////"),
        mpatches.Patch(fc="#bbb", ec="black", hatch="\\\\\\\\\\"),
    ]
    labels = ["MPI Tier: Rows In", "MPI Tier: Rows Out"]
    anchor = (0.5, 1.03)
    ax.legend(
        handles=handles,
        labels=labels,
        loc="upper center",
        ncol=2,
        fontsize=smallsz,
        bbox_to_anchor=anchor,
    )


def plot_ontv_combined():
    fig, axes = plt.subplots(2, 1, figsize=(common.COLWIDTH, 2.5))
    plot_ontv_runtimes(axes[0])
    plot_ontv_rowcounts(axes[1])
    fig.tight_layout(pad=0.2, h_pad=0.6)
    common.save_plot(fig, "ontv_combined")
    plt.close("all")


def main():
    rdf = read_ontv_runtimes()
    print(rdf)
    tsdf = read_ontv_tracestats()
    print(tsdf)
    plot_ontv_combined()


if __name__ == "__main__":
    plt.style.use(common.get_plotsrc_dir() / "paper.mplstyle")
    common.set_colormap("Pastel1")
    main()
