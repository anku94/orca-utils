import glob
import pandas as pd
import panel as pn
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import polars as pl


SUITE_ROOT = "/mnt/ltio/orcajobs/suites"


def read_suitedir(suitedir: str) -> pd.DataFrame:
    suite_runtimes = f"{suitedir}/amr_runtimes.csv"
    rdf = pd.read_csv(suite_runtimes)
    rdf.columns = ["profile", "time_secs"]
    return rdf


def plot_suitedir(suite_dir: str) -> pn.pane.Matplotlib:
    rdf = read_suitedir(suite_dir)
    fig, ax = plt.subplots(figsize=(10, 5))
    data_x = np.arange(len(rdf["profile"]))
    data_y = rdf["time_secs"]
    data_ybase = len(rdf["profile"]) * [data_y.iloc[0]]
    data_yxtra = data_y - data_ybase

    ax.bar(data_x, data_ybase, width=0.6)
    bars = ax.bar(data_x, data_yxtra, width=0.6, bottom=data_ybase)

    labels = [
        f"{b+x:.1f}s ({x/b*100:.1f}%)" for x, b in zip(data_yxtra, data_ybase)
    ]
    print(labels)
    ax.bar_label(bars, labels)

    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    ax.set_ylabel("Runtime (seconds)")
    ax.set_xlabel("Profile")
    ax.set_title(f"Runtime of {suite_dir}")

    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#ddd')
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(mtick.MultipleLocator(20))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(5))

    # rotae x-axis labels 45 degrees
    ax.set_xticks(data_x)
    ax.set_xticklabels(rdf["profile"], rotation=25)

    ax.set_ylim(0, 220)

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, dpi=300, width=800, format='svg', tight=True)


def tmp():
    suite = f"{SUITE_ROOT}/amr-r128-psmdef"
    run_profile = "tracendrop"
    orca_tracedirs = glob.glob(f"{suite}/{run_profile}/parquet/orca_events/**")
    orca_pl = pl.read_parquet(orca_tracedirs, parallel="columns")
    # filter by op_type == "X"
    orca_pl_x = orca_pl.filter(pl.col("op_type") == "X")
    # group by probe_name and sum the time
    pn.panel(orca_pl_x.head()).servable()
    pl_xg = orca_pl_x.group_by(["rank", "probe_name"]).agg(pl.sum("val"))
    pl_xg = pl_xg.with_columns(pl.col("val") / 1_000_000)
    pl_xg = pl_xg.rename({"val": "time_ms"})
    pl_xg = pl_xg.with_columns(pl.col("time_ms").cast(pl.Int64))

    pl_pta = pl_xg.filter(
        pl.col("probe_name").str.contains("PostTimestepAdvance"))
    pl_pta = pl_pta.sort("rank")
    pn.panel(pl_pta.head()).servable()


def run():
    plt.style.use('../larger_fonts.mplstyle')

    pn.extension()
    pn.panel("Hello World").servable()

    suites = glob.glob(f"{SUITE_ROOT}/*")
    print(suites)
    pn.panel(f"Suites found: {suites}").servable()

    all_panes = []
    psmdef_pane = plot_suitedir(f"{SUITE_ROOT}/amr-r128-psmdef")
    all_panes.append(psmdef_pane)
    psmerrchk141_pane = plot_suitedir(f"{SUITE_ROOT}/amr-r128-psmerrchk141")
    all_panes.append(psmerrchk141_pane)

    pn.Row(*all_panes).servable()
    tmp()


if __name__ == "__main__":
    # use style file 'larger_fonts.mplstyle'
    # run()
    # tmp()
    # run()
    tmp()

tmp()
