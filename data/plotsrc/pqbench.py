import os
import pandas as pd
import glob
import numpy as np
from common import PlotSaver
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DATA_ROOT = "../plotdata"


def sort_by_order(df: pd.DataFrame) -> pd.DataFrame:
    # pq_uncomp is just pq_nodict, will drop it

    order = [
        "json",
        "csv",
        "pq_default",
        "pq_def_snappy",
        "pq_nodict",
        "pq_nostats",
    ]

    # arrange df labels in this order, skip the ones not in order
    df = df[df["label"].isin(order)].copy()
    df["label"] = pd.Categorical(df["label"], categories=order, ordered=True)
    df = df.sort_values(by="label")

    return df


def load_and_prep(csv_path: str) -> pd.DataFrame:
    csv_name = os.path.basename(csv_path).split(".")[0]  # noqa: F821

    df = pd.read_csv(csv_path)
    df["run"] = csv_name
    cols2retain = ["run", "label", "rows_per_sec"]

    # group by label, compute mean and err for rows_per_sec
    df = (
        df.groupby(["run", "label"])
        .agg({"rows_per_sec": ["mean", "std"]})
        .reset_index()
    )
    df.columns = ["run", "label", "rps_mean", "rps_std"]
    df = sort_by_order(df)

    return df

def get_bar_labels(dy, dyn):
    #bar_labels = [f"{yn*100:.0f}\% ({y/1e6:.1f}M)" for (y, yn) in zip(dy, dyn)]
    # rel pct values for other bars
    bar_labels = [f"{yn*100:.0f}\%" for (y, yn) in zip(dy, dyn)]
    # counts only for the firstbar
    bar_labels[0] = f"{dy[0]/1e6:.1f}M/s"
    return bar_labels


def plot_rps(all_dfs: list[pd.DataFrame]):
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    #ax.clear()

    ndfs = len(all_dfs)
    width = 0.7 / ndfs

    for i, df in enumerate(all_dfs):
        dx0 = np.arange(len(df)) + width * i

        dy = df["rps_mean"]
        norm_factor = dy.iloc[0]
        dyn = dy / norm_factor

        dyerr = df["rps_std"]
        dyerrn = dyerr / norm_factor

        df_label = df["run"][0]
        # bar outline is black thick
        errbc = 0.3
        errbcol = (errbc, errbc, errbc, 0.6)
        bars = ax.bar(dx0, dyn, yerr=dyerrn, label=df_label, width=width, edgecolor="black", linewidth=1, zorder=3, ecolor=errbcol, capsize=3)
        bar_labels = get_bar_labels(dy, dyn)
        ax.bar_label(bars, labels=bar_labels, label_type="center", padding=0, fontsize=11, rotation=90, zorder=4)


    ylabfontsz = plt.rcParams.get("axes.labelsize")
    ax.set_ylabel("Write Perf. (rows/sec, relative)", fontsize=ylabfontsz + 2)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x * 100:.0f} \%"))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.set_xticks(np.arange(len(df)) + width * (ndfs - 1) / 2)  # center ticks under bars
    labels = [
            "JSON",
            "CSV",
            "Parquet\n\emph{(default)}",
            "Parquet\n\emph{(snappy)}",
            "Parquet\n\emph{(dict=off)}",
            "Parquet\n\emph{(stats=off)}",
            ]
    ax.set_xticklabels(labels, rotation=0, ha="center")
    fig.tight_layout()

    h, l = ax.get_legend_handles_labels()
    labels = ["Intel/NFS", "Intel/Lustre", "Mac/Local"]
    ax.legend(h, labels)
    PlotSaver.save(fig, None, None, "pqbench_write_rps")
    plt.close(fig)


def run():
    pqbench_data = glob.glob(f"{DATA_ROOT}/pqbench*")
    pqbench_data = pqbench_data[::-1]
    print(pqbench_data)
    all_dfs = [load_and_prep(data) for data in pqbench_data]
    plot_rps(all_dfs)
    pass


if __name__ == "__main__":
    plt.close("all")
    plt.style.use("././paper.mplstyle")
    cmap = plt.colormaps["Pastel1"]
    colors = [cmap(i) for i in range(cmap.N)]
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=colors)
    plt.close("all")
    run()
