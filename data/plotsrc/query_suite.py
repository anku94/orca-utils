import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mtick
import common as c
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
import re
import math

QUERY_MAP: dict[str, str] = {
    "count_mpi_wait_dur": "Outlier Waits",
    "count_sync_maxdur": "Outlier Collectives",
    "count_window": "Timestamp Range",
}


@dataclass
class RunParams:
    profile: str
    nranks: int
    steps: int
    aggs: int
    run: int


def infer_run_params(trace_dir: Path):
    dir_name = trace_dir.name
    profile = trace_dir.parent.name
    par2_name = trace_dir.parent.parent.name

    assert dir_name in ["parquet", "trace"]
    # amr-agg1-r512-n200-run1
    mobj = re.match(r"amr-agg(\d+)-r(\d+)-n(\d+)-run(\d+)", par2_name)
    assert mobj is not None
    aggs = int(mobj.group(1))
    nranks = int(mobj.group(2))
    steps = int(mobj.group(3))
    run = int(mobj.group(4))

    return RunParams(profile, nranks, steps, aggs, run)


def read_query_suite_data():
    data_dir = c.get_plotdata_dir() / "queries"

    pref = "query_results_20260102_"
    pref_files = list(data_dir.glob(f"{pref}*.csv"))
    pref_df = pd.concat([pd.read_csv(f) for f in pref_files], ignore_index=True)
    pref_df = pref_df[pref_df["run_type"] == "caliper"]

    pref2 = "20260105_query_results_"
    pref2_files = list(data_dir.glob(f"{pref2}*.csv"))
    pref2_df = pd.concat([pd.read_csv(f) for f in pref2_files], ignore_index=True)
    pref2_df = pref2_df[pref2_df["run_type"] == "dftracer"]

    # ORCA numbers, recomputed with a warmup run excluded on 20260401
    # This still uses drop_caches, but first ORCA queries seem to be 
    # suceptible to some Lustre server-side caching effects that result in
    # noise given the low absolute performance.
    # Execution protocol:
    # - Warmup suite, drop cache, actual measured suite (for each iteration)
    pref3 = "query_results_20260401-2303.csv"
    pref3_file = data_dir / pref3
    pref3_df = pd.read_csv(pref3_file)
    pref3_df = pref3_df[pref3_df["run_type"] == "orca"]

    data_df = pd.concat([pref_df, pref2_df, pref3_df], ignore_index=True)
    return data_df


def prep_query_suite_data(df: pd.DataFrame):
    # Cols: ['query_name', 'trace_dir', 'run_type', 'data', 'total_us']
    all_params = [infer_run_params(Path(trace_dir)) for trace_dir in df["trace_dir"]]
    all_pdf = pd.DataFrame(all_params)
    mdf = df.merge(all_pdf, left_index=True, right_index=True)
    mdf["total_ms"] = mdf["total_us"] / 1000.0

    # group by query_name, profile, nranks, steps, aggs: avg and std of total_ms
    group_cols = ["query_name", "profile", "nranks", "steps", "aggs"]
    gdf = mdf.groupby(group_cols).agg({"total_ms": ["mean", "std"]}).reset_index()
    gdf.columns = group_cols + ["total_ms_mean", "total_ms_std"]

    return gdf


def read_query_suite():
    data_dir = c.get_plotdata_dir() / "queries"
    glob_patt = "*20260102*csv"
    all_files = list(data_dir.glob(glob_patt))
    print(all_files)
    all_dfs = [pd.read_csv(file) for file in all_files]
    df = pd.concat(all_dfs, ignore_index=True)

    # Cols: ['query_name', 'trace_dir', 'run_type', 'data', 'total_us']
    all_params = [infer_run_params(Path(trace_dir)) for trace_dir in df["trace_dir"]]
    all_pdf = pd.DataFrame(all_params)
    mdf = df.merge(all_pdf, left_index=True, right_index=True)
    mdf["total_ms"] = mdf["total_us"] / 1000.0

    # group by query_name, profile, nranks, steps, aggs: avg and std of total_ms
    group_cols = ["query_name", "profile", "nranks", "steps", "aggs"]
    gdf = mdf.groupby(group_cols).agg({"total_ms": ["mean", "std"]}).reset_index()
    gdf.columns = group_cols + ["total_ms_mean", "total_ms_std"]

    return gdf


def fmt_dura(x: float) -> str:
    if x < 1000:
        return f"{x:.0f}\,ms"
    elif x < 100 * 1e3:
        return f"{x/1000:.1f}\,s"
    elif x < 100 * 60 * 1e3:
        x_minutes = x / (1000 * 60)
        return f"{x_minutes:.1f}\,m"
    else:
        x_hours = x / (1000 * 60 * 60)
        return f"{x_hours:.1f}\,h"


def fmt_ratio(x: float) -> str:
    if x < 1:
        xstr = f"{x:.1f}"
    elif x <= 100:
        xstr = f"{x:.0f}"
    else:
        exp = int(math.log10(x))
        xstr = f"10\\textsuperscript{{{exp}}}"

    return rf"{xstr}$\times$"


def adjust_annots(
    annots: list[plt.Annotation],
    idxes: list[int],
    adj: tuple[int, int],
    adj_x: list[float] | None = None,
    adj_y: list[float] | None = None,
):
    if adj_x is None:
        adj_x = [0] * len(idxes)
    if adj_y is None:
        adj_y = [0] * len(idxes)

    for idx, adj_x_i, adj_y_i in zip(idxes, adj_x, adj_y):
        (x, y) = annots[idx].get_position()
        xn, yn = x + adj[0] + adj_x_i, y + adj[1] + adj_y_i
        annots[idx].set_position((xn, yn))


def plot_query_inner(ax: plt.Axes, qdf: pd.DataFrame):
    pcat = pd.Categorical(
        qdf["profile"],
        categories=[c.Prof.ORCA_TGT, c.Prof.CALIPER_TGT, c.Prof.DFTRACER_TGT],
        ordered=True,
    )
    qdf["profile"] = pcat
    qdf = qdf.sort_values(by=["profile"])
    # plot each profile as a line
    qdf_base = qdf[qdf["profile"] == c.Prof.ORCA_TGT].copy()
    qdf_base.drop(columns=["profile", "total_ms_std"], inplace=True)
    qdf = qdf.merge(
        qdf_base, on=["query_name", "nranks", "steps", "aggs"], suffixes=["", "_base"]
    )
    qdf["ratio"] = qdf["total_ms_mean"] / qdf["total_ms_mean_base"]
    qdf["ratio_std"] = qdf["total_ms_std"] / qdf["total_ms_mean_base"]
    print(qdf)

    all_annots = []

    for pidx, profile in enumerate(qdf["profile"].unique()):
        pqdf = qdf[qdf["profile"] == profile]

        data_x = pqdf["nranks"]
        data_x = range(len(data_x))
        data_y = pqdf["ratio"]
        data_yerr = pqdf["ratio_std"]
        pprops = c.PROF_PROPS[c.Prof(profile)]
        label = pprops.label
        marker = pprops.marker
        col_rgb = mcolors.to_rgba(pprops.color)
        ax.errorbar(data_x, data_y, yerr=data_yerr, label=label, marker=marker, capsize=4, color=col_rgb, mec="black", alpha=0.7) # fmt: skip

        labels = pqdf["total_ms_mean"].apply(lambda x: fmt_dura(x)).tolist()
        # ebcolor = eb[0].get_color()
        acol = c.darken_rgba(col_rgb, 0.5)

        for x, y, label in zip(data_x, data_y, labels):
            fontsz = plt.rcParams["font.size"] - 3
            annot = ax.annotate(label, (x, y), textcoords="offset points", xytext=(0, 5), ha="center", va="bottom", fontsize=fontsz, color=acol) # fmt: skip
            all_annots.append(annot)

    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels([512, 1024, 2048, 4096])
    # make y axis log scale
    ax.set_yscale("log")

    # ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmt_dura(x)))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmt_ratio(x)))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5]))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.tick_params(axis="y", pad=1)

    print(all_annots)

    # adjust_annots(all_annots, [0, 1, 2, 3], (0, -3), [7, 2, -2, -7], [1, -10, 1, -10])
    # adjust_annots(all_annots, [4, 5, 6, 7], (0, -15), [7, 2, -2, -7], [0, 0, 0, 2])
    # adjust_annots(all_annots, [8, 9, 10], (0, -2), [7, 2, -2], [1, 0, 0])


def plot_query(all_qdf: pd.DataFrame, query_types: list[str]):
    # 3 plots, one for each query type, x axis is nranks, y axis is total_ms_mean, error bars are total_ms_std
    plt.close("all")
    fig, axes = plt.subplots(1, 3, figsize=(c.TEXTWIDTH * 0.5, 1.6))

    for ax, qtype in zip(axes, query_types):
        qdf = all_qdf[all_qdf["query_name"] == qtype]
        plot_query_inner(ax, qdf)
        ax.set_ylim(1.5e-1, 5e4)
        ax.yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=5))
        ax.yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5], numticks=5))
        # ticksz = plt.rcParams["font.size"] - 3
        lblfontsz = plt.rcParams["font.size"] - 1
        ax.set_xlabel(f"\\sffamily\\bfseries {QUERY_MAP[qtype]}", color="black", fontsize=lblfontsz)
        ax.tick_params(axis="both", pad=1)
        # ax.set_title(qtype, pad=3)

    fontsz = plt.rcParams["font.size"]
    fontclr = plt.rcParams["axes.labelcolor"]
    fig.text(0.05, 0.082, r"\textbf{Ranks}", ha="center", va="bottom", fontsize=fontsz, color=fontclr)
    axes[0].set_ylabel(r"\textbf{Rel. Latency}")
    axes[1].set_yticklabels([])
    axes[2].set_yticklabels([])

    fig.tight_layout(pad=0.1, w_pad=0.1)
    legh, legl = axes[0].get_legend_handles_labels()
    lfsz = plt.rcParams["legend.fontsize"] - 1
    lbbox = (0.25, 1.01)
    fig.legend(legh, legl, loc="upper left", ncol=3, bbox_to_anchor=lbbox, fontsize=lfsz)
    fig.subplots_adjust(top=0.85)
    c.save_plot(fig, "query_suite")


def main():
    df = read_query_suite_data()
    gdf = prep_query_suite_data(df)
    gdf20 = gdf[gdf["steps"] == 20]
    query_types = gdf20["query_name"].unique()
    assert len(query_types) == 3

    print(gdf20)

    plot_query(gdf20, query_types)


if __name__ == "__main__":
    plt.close("all")
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1-Dark")
    main()
