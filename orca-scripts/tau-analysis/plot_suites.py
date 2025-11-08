import glob
import os
import pandas as pd
import panel as pn
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import polars as pl

from suite_utils import *

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
def read_suite_profiles(suite_dir: str, probe_name: str) -> tuple[list[str], list[list[int]]]:
    profile_paths = get_suite_profiles(suite_dir)

    # create an empty dataframe with columns for each profile
    profile_names = [os.path.basename(p) for p in profile_paths]
    profile_times = [read_orca_overhead(
        p, probe_name)["time_ms"].to_list() for p in profile_paths]

    return (profile_names, profile_times)


def get_probe_freqs(profile_dir: str, tracer: str) -> pl.DataFrame:
    counts_cached_path = f"{profile_dir}/{tracer}-probe-freqs.parquet"
    if os.path.exists(counts_cached_path):
        return pl.read_parquet(counts_cached_path)

    trace_dir = f"{profile_dir}/parquet/{tracer}"
    pn.panel(trace_dir).servable()
    q = (
        pl.scan_parquet(trace_dir, rechunk=False, cache=False)
        .group_by(["rank", "probe_name"])
        .agg(pl.len())
        .sort(["rank", "probe_name"])
    )

    tdf_counts = q.collect(engine="streaming")
    tdf_counts.write_parquet(counts_cached_path)

    return tdf_counts


def plot_probe_freqs(profile_dir: str, probe_name: str, **kwargs) -> pn.pane.Matplotlib:
    counts = get_probe_freqs(profile_dir, probe_name)
    counts = counts.group_by("probe_name").agg(pl.sum("len"))

    labels = counts["probe_name"].to_list()
    labels = [l[-14:] for l in labels]

    # plot counts as a pie chart
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.pie(counts["len"], labels=labels, startangle=30)

    profile_name = os.path.basename(profile_dir)
    suite_name = os.path.basename(os.path.dirname(profile_dir))
    ax.set_title(f"{probe_name}: {profile_name}\n{suite_name}")
    plt.close(fig)
    return pn.pane.Matplotlib(fig, **kwargs)


def plot_overhead_rankwise(profile_dir: str, probe_name: str, **kwargs) -> pn.pane.Matplotlib:
    "Plot rank-wise probe-name overhead for a single profile_dir"

    profile_name = os.path.basename(profile_dir)
    suite_dir = os.path.dirname(profile_dir)
    suite_name = os.path.basename(suite_dir)
    times = read_orca_overhead(profile_dir, probe_name)
    times = times.sort("rank")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times["rank"], times["time_ms"])
    ax.set_ylabel("Time (s)")
    ax.set_xlabel("Rank")
    ax.set_title(f"{probe_name}: {profile_name}\n{suite_name}")
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#ddd')
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(mtick.MultipleLocator(64))
    ax.xaxis.set_minor_locator(mtick.MultipleLocator(16))
    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, pos: f"{x/1e3:.0f}s"))

    plt.close(fig)
    return pn.pane.Matplotlib(fig, **kwargs)


def plot_overhead_boxplot(suite_dir: str, probe_name: str, **kwargs) -> pn.pane.Matplotlib:
    suite_name = os.path.basename(suite_dir)
    profile_names, profile_times = read_suite_profiles(suite_dir, probe_name)

    fig, ax = plt.subplots(figsize=(8, 5))
    data_x = np.arange(len(profile_names))
    data_y = profile_times

    ax.boxplot(data_y, positions=data_x, labels=profile_names)
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


def plot_data_volume(suite_name: str, **kwargs) -> pn.pane.Matplotlib:
    suite_dir = get_suitedir(suite_name)
    profile_dirs = get_suite_profiles(suite_dir)
    sizes = [get_tracedir_size(p) for p in profile_dirs]
    profiles = [os.path.basename(p) for p in profile_dirs]

    ONE_MB = 2**20
    ONE_GB = 2**30


    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(profiles, sizes)
    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, pos: f"{x/ONE_GB:.1f}GB"))
    ax.tick_params(axis='x', rotation=15)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(ONE_GB * 10))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(ONE_GB * 1))
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#ddd')
    ax.set_axisbelow(True)
    ax.set_title(f"Data Volume: {suite_name}")

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


def run_add_512x1(plot_kwargs: dict):
    pn.panel("## 512 ranks, NAGGS=1, PSM_ERRCHK_TIMEOUT=1:4:1").servable()
    all_names = [
        "20251105_amr-agg1-r512-n20-psmerrchk141",
        "20251105_amr-agg1-r512-n200-psmerrchk141",
        "20251106_amr-agg1-r512-n2000-psmerrchk141"
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()


def run_add_512x4(plot_kwargs: dict):
    pn.panel("## 512 ranks, NAGGS=4, PSM_ERRCHK_TIMEOUT=1:4:1").servable()
    all_names = [
        "20251106_amr-agg4-r512-n20-psmerrchk141",
        "20251106_amr-agg4-r512-n200-psmerrchk141",
        "20251106_amr-agg4-r512-n2000-psmerrchk141"
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()


def run_add_512misc(plot_kwargs: dict):
    all_names = [
        "20251106_amr-agg4-r512-n20-psmerrchk141",
        "20251106_amr-agg4-r512-n200-psmerrchk141",
        "20251106_amr-agg4-r512-n2000-psmerrchk141"
    ]

    pn.panel("## Misc Stats").servable()
    panes = []
    profile_dir = get_profile_dir(all_names[1], "7_trace_all")
    pane = plot_probe_freqs(profile_dir, "mpi_messages", **plot_kwargs)
    panes.append(pane)

    pane = plot_probe_freqs(profile_dir, "kokkos_events", **plot_kwargs)
    panes.append(pane)

    profile_dir = get_profile_dir(all_names[-1], "3_tracendrop_agg")
    probe_name = "PostTimestepAdvance"
    pane = plot_overhead_rankwise(profile_dir, probe_name, **plot_kwargs)
    panes.append(pane)

    pn.Row(*panes).servable()


def run_add_1024x1(plot_kwargs: dict):
    pn.panel("## 1024 ranks, NAGGS=1, PSM_ERRCHK_TIMEOUT=1:4:1").servable()
    all_names = [
        "20251106_amr-agg1-r1024-n20-psmerrchk141",
        "20251106_amr-agg1-r1024-n200-psmerrchk141",
        "20251106_amr-agg1-r1024-n2000-psmerrchk141"
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()

    all_dvol_panes = []
    for name in all_names:
        pane = plot_data_volume(name, **plot_kwargs)
        all_dvol_panes.append(pane)
    pn.Row(*all_dvol_panes).servable()


def run():
    plt.style.use('../larger_fonts.mplstyle')
    pn.extension()

    plot_kwargs = {
        "dpi": 300,
        "width": 450,
        "format": 'svg',
        "tight": True
    }

    # run_add_512x1(plot_kwargs)
    # run_add_512x4(plot_kwargs)
    # run_add_512misc(plot_kwargs)
    run_add_1024x1(plot_kwargs)


if __name__ == "__main__":
    # use style file 'larger_fonts.mplstyle'
    # run()
    pass

# run_overhead_boxplot()
run()
