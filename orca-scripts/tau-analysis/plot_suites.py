import glob
import os
import pandas as pd
import panel as pn
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import polars as pl

from suite_utils import get_suite_amr_runtimes

SUITE_ROOT = "/mnt/ltio/orcajobs/suites"

PlotList = list[pn.pane.Matplotlib]



def plot_suitedir(suite_dir: str, **kwargs) -> pn.pane.Matplotlib:
    rdf = get_suite_amr_runtimes(suite_dir)
    fig, ax = plt.subplots(figsize=(9, 5))
    data_x = np.arange(len(rdf["profile"]))
    data_y = rdf["time_secs"]
    data_ybase = len(rdf["profile"]) * [data_y.iloc[0]]
    data_yxtra = data_y - data_ybase

    ax.bar(data_x, data_ybase, width=0.6)
    bars = ax.bar(data_x, data_yxtra, width=0.6, bottom=data_ybase)

    labels = [
        f"{b+x:.1f}s\n({x/b*100:.1f}%)" for x, b in zip(data_yxtra, data_ybase)
    ]
    print(labels)
    ax.bar_label(bars, labels)

    suite_name = os.path.basename(suite_dir)

    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    ax.set_ylabel("Runtime (seconds)")
    ax.set_xlabel("Profile")
    ax.set_title(f"Runtime of {suite_name}")

    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#ddd')
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(mtick.AutoLocator())
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator())

    # rotae x-axis labels 45 degrees
    ax.set_xticks(data_x)
    ax.set_xticklabels(rdf["profile"], rotation=25)

    # ax.set_ylim(0, 220)
    # bump ylim by 10%
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.1)

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, **kwargs)
    # return pn.pane.Matplotlib(fig, dpi=300, width=800, format='svg', tight=True)


@pn.cache
def read_orca_overhead(profile_path: str, probe_name: str) -> pl.DataFrame:
    orca_tracedirs = glob.glob(f"{profile_path}/parquet/orca_events/**")

    if not orca_tracedirs:
        return pl.DataFrame({"rank": [], "probe_name": [], "time_ms": []})

    orca_pl = pl.read_parquet(orca_tracedirs, parallel="columns")

    orca_pl_x = orca_pl.filter(pl.col("op_type") == "X")
    pl_xg = orca_pl_x.group_by(["rank", "probe_name"]).agg(pl.sum("val"))
    pl_xg = pl_xg.with_columns(pl.col("val") / 1_000_000)
    pl_xg = pl_xg.rename({"val": "time_ms"})
    pl_xg = pl_xg.with_columns(pl.col("time_ms").cast(pl.Int64))

    pl_filtered = pl_xg.filter(pl.col("probe_name").str.contains(probe_name))
    pl_filtered = pl_filtered.sort("rank")

    return pl_filtered


@pn.cache
def read_suite_profiles(suite: str, probe_name: str) -> dict[str, list[int]]:
    profiles = glob.glob(f"{suite}/*")
    profiles = [p for p in profiles if os.path.isdir(p)]
    profiles.sort()

    data = {}
    for profile_path in profiles:
        profile_name = profile_path.split('/')[-1]
        df = read_orca_overhead(profile_path, probe_name)
        data[profile_name] = df["time_ms"].to_list()

    return data


def plot_overhead_boxplot(suite: str, probe_name: str, **kwargs) -> pn.pane.Matplotlib:
    suite_name = os.path.basename(suite)
    data = read_suite_profiles(suite, probe_name)

    fig, ax = plt.subplots(figsize=(8, 5))

    profile_names = list(data.keys())
    values = [data[p] for p in profile_names]

    data_x = np.arange(len(profile_names))

    ax.boxplot(values, positions=data_x, labels=profile_names)
    ax.set_ylabel("Time (s)")
    ax.set_xlabel("Profile")
    ax.set_title(f"{probe_name}: {suite_name}")
    ax.tick_params(axis='x', rotation=25)

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, pos: f"{x/1e3:.1f}s"))

    # ax.set_ylim(bottom=0, top=2000)
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.1)
    ax.grid(which='major', color='#bbb')
    ax.yaxis.grid(which='minor', color='#ddd')
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(mtick.AutoLocator())
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator())

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, **kwargs)


def plot_suite(suite_names: list[str], plot_kwargs: dict) -> tuple[PlotList, PlotList]:
    suite_dirs = [f"{SUITE_ROOT}/{s}" for s in suite_names]

    all_rt_panes = []
    for sdir in suite_dirs:
        plot_pane = plot_suitedir(sdir, **plot_kwargs)
        all_rt_panes.append(plot_pane)

    all_bp_panes = []
    for sdir in suite_dirs:
        plot_pane = plot_overhead_boxplot(
            sdir, "PostTimestepAdvance", **plot_kwargs)
        all_bp_panes.append(plot_pane)

    return (all_rt_panes, all_bp_panes)


def run():
    plt.style.use('../larger_fonts.mplstyle')
    pn.extension()

    plot_kwargs = {
        "dpi": 300,
        "width": 450,
        "format": 'svg',
        "tight": True
    }

    pn.panel("## 128 ranks, TAU").servable()

    pn.panel("## 128 ranks, PSM_ERRCHK_TIMEOUT=1:4:1").servable()
    all_names = [
        "20251101_amr-r128-psmerrchk141-n20",
        "20251101_amr-r128-psmerrchk141-n200",
        "20251101_amr-r128-psmerrchk141-n2000"
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()

    pn.panel("## 128 ranks, PSM_ERRCHK_TIMEOUT=1:4:1, no hugepages").servable()

    nohp_names = [
        "20251103_amr-r128-psm141-nohugepages-n20",
        "20251103_amr-r128-psm141-nohugepages-n200",
        "20251103_amr-r128-psm141-nohugepages-n2000"
    ]
    nohp_rt_panes, nohp_bp_panes = plot_suite(nohp_names, plot_kwargs)
    pn.Row(*nohp_rt_panes).servable()
    pn.Row(*nohp_bp_panes).servable()

    all_names = [
        "20251103_amr-r512-psmerrchk141-n20",
        "20251103_amr-r512-psmerrchk141-n200",
        "20251103_amr-r512-psmerrchk141-n2000"
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()

if __name__ == "__main__":
    # use style file 'larger_fonts.mplstyle'
    # run()
    pass

# run_overhead_boxplot()
run()
