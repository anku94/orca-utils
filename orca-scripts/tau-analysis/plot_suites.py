import glob
import os
import pandas as pd
import panel as pn
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import polars as pl

from suite_utils import *
from common import PlotSaver
from parse_cycle_log import parse_cycle_log

PlotList = list[pn.pane.Matplotlib]

# set to True to write plot files
WRITE_FILES = False


def save_and_cls(fig: plt.Figure, fname: str):
    "Save figure if WRITE_FILES is True and close it"
    global WRITE_FILES

    fig.tight_layout()
    if WRITE_FILES:
        PlotSaver.save(fig, fname)

    plt.close(fig)


@log_time
def plot_suite_runtimes(suite: Suite, **kwargs) -> pn.pane.Matplotlib:
    rdf = get_suite_amr_runtimes(suite)

    # check if figsize is there in kwargs
    if "figsize" in kwargs:
        figsize = kwargs.pop("figsize")
    else:
        figsize = (9, 5)

    fig, ax = plt.subplots(figsize=figsize)
    data_x = np.arange(len(rdf["profile"]))
    data_y = rdf["time_secs"]
    data_ybase = len(rdf["profile"]) * [data_y.iloc[0]]
    data_yxtra = data_y - data_ybase

    ax.bar(data_x, data_ybase, width=0.6)
    bars = ax.bar(data_x, data_yxtra, width=0.6, bottom=data_ybase)

    labels = [f"{b+x:.1f}s\n({x/b*100:.1f}%)" for x, b in zip(data_yxtra, data_ybase)]
    print(labels)
    ax.bar_label(bars, labels)

    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f"))
    ax.set_ylabel("Runtime (seconds)")
    ax.set_xlabel("Profile")
    ax.set_title(f"Runtime of {suite.name}")

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(mtick.AutoLocator())
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator())

    # rotae x-axis labels 45 degrees
    ax.set_xticks(data_x)
    ax.set_xticklabels(rdf["profile"], rotation=25)
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.3)

    save_and_cls(fig, f"{suite.name}_runtime")

    return pn.pane.Matplotlib(fig, **kwargs)


@pn.cache
def read_orca_overhead(profile_path: Path, probe_name: str) -> pl.DataFrame:
    # orca_tracedirs = glob.glob(f"{profile_path}/parquet/orca_events/**")
    orcaevents_dir = get_tracedir(profile_path) / "orca_events"

    if not orcaevents_dir.exists():
        return pl.DataFrame({"rank": [], "probe_name": [], "time_ms": []})

    orca_pl = pl.read_parquet(orcaevents_dir, parallel="columns")

    orca_pl_x = orca_pl.filter(pl.col("op_type") == "X")
    pl_xg = orca_pl_x.group_by(["rank", "probe_name"]).agg(pl.sum("val"))
    pl_xg = pl_xg.with_columns(pl.col("val") / 1_000_000)
    pl_xg = pl_xg.rename({"val": "time_ms"})
    pl_xg = pl_xg.with_columns(pl.col("time_ms").cast(pl.Int64))

    pl_filtered = pl_xg.filter(pl.col("probe_name").str.contains(probe_name))
    pl_filtered = pl_filtered.sort("rank")

    return pl_filtered


def read_suite_overhead(suite: Suite, probe_name: str) -> pd.DataFrame:
    profile_names = [p.name for p in suite.profiles]
    profile_paths = [p.path for p in suite.profiles]

    profile_times = []
    for p in profile_paths:
        try:
            profile_times.append(read_orca_overhead(p, probe_name)["time_ms"].to_list())
        except Exception as e:
            print(f"Error reading profile {p}: {e}")
            continue

    return pd.DataFrame({"profile": profile_names, "time_ms": profile_times})


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

    # check if figsize is there in kwargs
    if "figsize" in kwargs:
        figsize = kwargs.pop("figsize")
    else:
        figsize = (8, 5)

    # plot counts as a pie chart
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.pie(counts["len"], labels=labels, startangle=30)

    profile_name = os.path.basename(profile_dir)
    suite_name = os.path.basename(os.path.dirname(profile_dir))
    ax.set_title(f"{probe_name}: {profile_name}\n{suite_name}")
    save_and_cls(fig, f"{suite_name}_probe_freqs")
    return pn.pane.Matplotlib(fig, **kwargs)


def plot_overhead_rankwise(
    profile_dir: str, probe_name: str, **kwargs
) -> pn.pane.Matplotlib:
    "Plot rank-wise probe-name overhead for a single profile_dir"

    profile_name = os.path.basename(profile_dir)
    suite_dir = os.path.dirname(profile_dir)
    suite_name = os.path.basename(suite_dir)
    times = read_orca_overhead(profile_dir, probe_name)
    times = times.sort("rank")

    # check if figsize is there in kwargs
    if "figsize" in kwargs:
        figsize = kwargs.pop("figsize")
    else:
        figsize = (8, 5)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(times["rank"], times["time_ms"])
    ax.set_ylabel("Time (s)")
    ax.set_xlabel("Rank")
    ax.set_title(f"{probe_name}: {profile_name}\n{suite_name}")
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(mtick.MultipleLocator(64))
    ax.xaxis.set_minor_locator(mtick.MultipleLocator(16))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: f"{x/1e3:.0f}s"))

    save_and_cls(fig, f"{suite_name}_overhead_rankwise")
    return pn.pane.Matplotlib(fig, **kwargs)


def plot_overhead_boxplot(
    suite: Suite, probe_name: str, **kwargs
) -> pn.pane.Matplotlib:
    # profile_names = [p.name for p in suite.profiles]
    # profile_times = [read_orca_overhead(p.path, probe_name)["time_ms"].to_list() for p in suite.profiles]
    ohdf = read_suite_overhead(suite, probe_name)
    print(ohdf)
    profile_names = ohdf["profile"]
    profile_times = ohdf["time_ms"]

    # check if figsize is there in kwargs
    if "figsize" in kwargs:
        figsize = kwargs.pop("figsize")
    else:
        figsize = (8, 5)

    fig, ax = plt.subplots(figsize=figsize)
    data_x = np.arange(len(profile_names))
    data_y = profile_times

    ax.boxplot(data_y, positions=data_x, labels=profile_names)
    ax.set_ylabel("Time (s)")
    ax.set_xlabel("Profile")
    ax.set_title(f"{probe_name}: {suite.name}")
    ax.tick_params(axis="x", rotation=25)

    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: f"{x/1e3:.1f}s"))

    # ax.set_ylim(bottom=0, top=2000)
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.1)
    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(mtick.AutoLocator())
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator())

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, **kwargs)


@log_time
def plot_suite_data_volume(suite: Suite, **kwargs) -> pn.pane.Matplotlib:
    tracesizes_df = get_suite_tracesizes(suite)
    profiles = tracesizes_df["profile"]
    sizes = tracesizes_df["trace_size"]

    ONE_MB = 2**20
    ONE_GB = 2**30
    majfmt = ONE_GB
    # if max(sizes) > majfmt:
    #     majfmt = majfmt * 10
    while max(sizes) > majfmt * 10:
        majfmt = majfmt * 10

    # check if figsize is there in kwargs
    if "figsize" in kwargs:
        figsize = kwargs.pop("figsize")
    else:
        figsize = (7, 4)

    fig, ax = plt.subplots(figsize=figsize)
    plt_bars = ax.bar(profiles, sizes)

    labels = [pretty_size(s) for s in sizes]
    ax.bar_label(plt_bars, labels)

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, pos: f"{x/ONE_GB:.1f}GB")
    )
    ax.tick_params(axis="x", rotation=15)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(majfmt))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(majfmt / 10))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)

    # set an extra margin on the top
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.2)
    ax.set_title(f"Data Volume: {suite.name}")

    plot_fname = f"{suite.name}_data_volume"
    save_and_cls(fig, plot_fname)
    return pn.pane.Matplotlib(fig, **kwargs)


def run_add_512x4(plot_kwargs: dict):
    pn.panel("## 512 ranks, NAGGS=4, PSM_ERRCHK_TIMEOUT=1:4:1").servable()
    all_names = [
        "20251106_amr-agg4-r512-n20-psmerrchk141",
        "20251106_amr-agg4-r512-n200-psmerrchk141",
        "20251106_amr-agg4-r512-n2000-psmerrchk141",
    ]
    all_rt_panes, all_bp_panes = plot_suite(all_names, plot_kwargs)
    pn.Row(*all_rt_panes).servable()
    pn.Row(*all_bp_panes).servable()


def run_add_512misc(plot_kwargs: dict):
    all_names = [
        "20251106_amr-agg4-r512-n20-psmerrchk141",
        "20251106_amr-agg4-r512-n200-psmerrchk141",
        "20251106_amr-agg4-r512-n2000-psmerrchk141",
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


def run_add_suites(suites: list[Suite], plot_kwargs: dict):
    rtplot_panes = [plot_suite_runtimes(s, **plot_kwargs) for s in suites]
    pn.Row(*rtplot_panes).servable()

    dvolplot_panes = [plot_suite_data_volume(s, **plot_kwargs) for s in suites]
    pn.Row(*dvolplot_panes).servable()

    ohprobe = "PostTimestepAdvance"
    ohplot_panes = [plot_overhead_boxplot(s, ohprobe, **plot_kwargs) for s in suites]
    pn.Row(*ohplot_panes).servable()


def run():
    plt.style.use("../larger_fonts.mplstyle")
    pn.extension()

    plot_kwargs = {
        "dpi": 300,
        "width": 450,
        # "height": 300,
        "figsize": (7, 4),
        "format": "svg",
        "tight": True,
    }

    parent_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_fpath = os.path.join(parent_dir, "suites.yaml")
    all_suites = read_suites(yaml_fpath)

    suite_names = ["r2048_a2_n20", "r2048_a2_n200", "r2048_a2_n2000"]
    suites = [all_suites[name] for name in suite_names]

    run_add_suites(suites, plot_kwargs)

    suite_names = ["r4096_a4_n20", "r4096_a4_n200", "r4096_a4_n2000"]
    suites = [all_suites[name] for name in suite_names]
    run_add_suites(suites, plot_kwargs)


if __name__ == "__main__":
    # use style file 'larger_fonts.mplstyle'
    # run()
    pass

# run_overhead_boxplot()
run()
