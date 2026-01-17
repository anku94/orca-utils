import time
from typing import Callable

from orcareader import OrcaReader
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import hvplot.pandas

import polars as pl
import pandas as pd
import panel as pn

pn.extension()

SUITES_ROOT = Path("/mnt/ltio/orcajobs/suites")
TRACE_ROOT = SUITES_ROOT / "20260108/amr-agg4-r4096-n2000-run1" / "20_or_disable_paused"

SWID_DEFAULT = 1171
RANK_DEFAULT = 3278


# define a timeit decorator
def timeit(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        func_name = func.__name__
        delta = end_time - start_time
        print(f"{func_name} took {delta * 1e3:.2f} ms")
        return result

    return wrapper


class DashboardData:

    def __init__(self, trace_root: Path):
        self.trace_root = trace_root
        self.ord = OrcaReader(trace_root)
        self.swid_maxdura = pn.rx(self.get_swid_maxdura())
        self.swid_max = self.swid_maxdura.rx.pipe(lambda df: int(df["swid"].max()))
        self.swid_flagged = self.swid_maxdura.rx.pipe(
            lambda df: self.get_swid_flagged(df)
        )

    @timeit
    def get_swid_maxdura(self) -> pd.DataFrame:
        gp = self.ord.get_glob_pattern("mpi_collectives")
        dmax = (pl.max("dura_ns") / 1e6).alias("dura_ms_max")
        dmin = (pl.min("dura_ns") / 1e6).alias("dura_ms_min")
        p01 = (pl.col("dura_ns") / 1e6).quantile(0.01).alias("dura_ms_p01")
        p50 = (pl.col("dura_ns") / 1e6).quantile(0.5).alias("dura_ms_p50")
        p90 = (pl.col("dura_ns") / 1e6).quantile(0.9).alias("dura_ms_p90")
        # group by swid, get max dura_ns / 1e9 as dura_ms
        df = (
            pl.scan_parquet(gp, parallel="columns")
            .group_by("timestep", "swid", "probe_name")
            .agg(dmin, p01, p50, p90, dmax)
            .sort(["timestep", "swid"])
            .collect()
        )
        return df.to_pandas()

    @timeit
    def get_swid_dura(self, swid: int) -> pd.DataFrame:
        gp = self.ord.get_glob_pattern("mpi_collectives")
        df = (
            pl.scan_parquet(gp, parallel="columns")
            .filter(pl.col("swid") == swid)  # sort by rank
            .sort("rank")
            .select("rank", (pl.col("dura_ns") / 1e6).alias("dura_ms"))
            .collect()
            .to_pandas()
        )
        return df

    def get_swid_flagged(self, maxdura_df: pd.DataFrame) -> list[int]:
        return maxdura_df[maxdura_df["dura_ms"] > 50]["swid"].tolist()

    def get_swid_data(self, swid: int, rank: int) -> pd.DataFrame:
        gp = self.ord.get_glob_pattern("mpi_collectives")
        dura_ms_expr = (pl.col("dura_ns") / 1e6).alias("dura_ms")
        ts_ms_expr = (pl.col("ts_ns") / 1e6).alias("ts_ms")
        # subtract ts_ms_min from ts_ms
        ts_ms_min = ts_ms_expr.min()
        ts_ms_expr = ts_ms_expr - ts_ms_min
        df = (
            pl.scan_parquet(gp, parallel="columns")
            .filter(pl.col("swid").is_between(swid - 8, swid + 5))
            .filter(pl.col("rank") == rank)
            .with_columns(dura_ms_expr, ts_ms_expr)
            .collect()
            .to_pandas()
        )
        return df

    def get_swid_rank_data(self, swid: int, rank: int) -> pd.DataFrame:
        gp = self.ord.get_glob_pattern("kfilt")
        dura_ms_expr = (pl.col("dura_ns") / 1e6).alias("dura_ms")
        ts_ms_expr = (pl.col("ts_ns") / 1e6).alias("ts_ms")
        # subtract ts_ms_min from ts_ms
        ts_ms_min = ts_ms_expr.min()
        ts_ms_expr = ts_ms_expr - ts_ms_min
        df = (
            pl.scan_parquet(gp, parallel="columns")
            .filter(pl.col("swid").is_between(swid - 8, swid + 5))
            .filter(pl.col("rank") == rank)
            .filter(pl.col("dura_ns") > 10_000_000)
            # .filter(pl.col("depth").is_between(1, 2))
            .with_columns(dura_ms_expr, ts_ms_expr)
            # .filter(pl.col("dura_ms") > 50)
            .collect()
            .to_pandas()
        )
        return df

    def refresh(self):
        self.swid_maxdura.rx.value = self.get_swid_maxdura()


def plot_swid_maxdura(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["swid"], df["dura_ms"])
    ax.set_xlabel("SWID")
    ax.set_ylabel("Max Duration (ms)")
    ax.set_title("Max Duration by SWID")

    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")

    # ax.set_xlim([1800, 2100])
    ax.set_xlim(left=0)

    ax.xaxis.set_major_locator(mtick.MultipleLocator(50))
    ax.xaxis.set_minor_locator(mtick.MultipleLocator(10))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: f"{x:.0f} ms"))
    fig.tight_layout()

    plt.close(fig)
    return fig


def plot_swid_maxdura_hv(df: pd.DataFrame):
    return df.hvplot.line(
        x="swid", y="dura_ms", title="Max Duration by SWID", width=1500
    )


def plot_swid_dura(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(df["rank"], df["dura_ms"])
    ax.set_xlabel("Rank")
    ax.set_ylabel("Duration (ms)")
    ax.set_title("Duration by Rank")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: f"{x:.0f} ms"))
    fig.tight_layout()
    plt.close(fig)
    return fig


class App:

    def __init__(self, trace_root: Path):
        self.data = DashboardData(trace_root)
        self.swid_text = self.get_swid_text()
        self.rank_text = self.get_rank_text()
        self.swid_int = self.swid_text.rx.pipe(lambda x: int(x))
        self.rank_int = self.rank_text.rx.pipe(lambda x: int(x))

    def get_header(self):
        time_str = time.strftime("%H:%M:%S", time.localtime())
        text_pane = pn.pane.Markdown(f"## Dashboard - {time_str}")

        def update():
            time_str = time.strftime("%H:%M:%S", time.localtime())
            text_pane.object = f"## Dashboard - {time_str}"

        pn.state.add_periodic_callback(update, 1000)
        return text_pane

    @timeit
    def get_swid_maxdura_plot(self):
        return pn.panel(self.data.swid_maxdura.rx.pipe(plot_swid_maxdura), height=400)

    def get_swid_text(self):
        return pn.widgets.TextInput(
            name="SWID", value=str(SWID_DEFAULT), width=100, align="center"
        )

    def get_rank_text(self):
        return pn.widgets.TextInput(
            name="Rank", value=str(RANK_DEFAULT), width=100, align="center"
        )

    def get_swid_plot(self):
        dura_rx = self.swid_int.rx.pipe(self.data.get_swid_dura)
        plot_rx = dura_rx.pipe(plot_swid_dura)
        return pn.pane.Matplotlib(plot_rx, height=400)

    def get_flagged_widget(self):
        fltext_rx = self.data.swid_flagged.rx.pipe(
            lambda swids: f"**Flagged SWIDs:** {', '.join(map(str, swids))}"
        )
        return pn.pane.Markdown(fltext_rx)

    def analyze_swid(self, swid: int):
        print(f"Analyzing SWID: {swid}")
        swid_df = self.data.get_swid_dura(swid)
        swid_df.sort_values(by="dura_ms", inplace=True)
        print(swid_df.head(10))
        pane = pn.Column(
            pn.pane.DataFrame(swid_df.head(10)),
        )
        return pane

    def analyze_swid_rank(self, swid: int, rank: int):
        print(f"Analyzing SWID: {swid}, Rank: {rank}")
        text_str = f"Analyzing SWID: {swid}, Rank: {rank}"
        swid_rank_df = self.data.get_swid_rank_data(swid, rank)
        swid_data_df = self.data.get_swid_data(swid, rank)
        swid_data_df["depth"] = 1
        cols = ["probe_name", "timestep", "swid", "rank", "depth", "ts_ns", "dura_ms"]

        srdf = swid_rank_df[cols].copy()
        sddf = swid_data_df[cols].copy()
        sdf = pd.concat([srdf, sddf], ignore_index=True)
        sdf.sort_values(by="ts_ns", inplace=True)
        sdf["ts_ms"] = sdf["ts_ns"] / 1e6
        sdf["ts_ms"] -= sdf["ts_ms"].min()
        sdf.drop(columns=["ts_ns"], inplace=True)
        pane = pn.Row(
            pn.pane.Markdown(text_str),
            pn.pane.DataFrame(sdf),
        )
        return pane

    @timeit
    def layout(self) -> pn.Column:
        swid_analysis = pn.bind(self.analyze_swid, self.swid_int.rx())
        # swid_rank_analysis = pn.bind(
        #     self.analyze_swid_rank, self.swid_int.rx(), self.rank_int.rx()
        # )
        return pn.Column(
            self.get_header(),
            self.get_swid_maxdura_plot(),
            self.get_flagged_widget(),
            pn.Row(
                self.swid_text,
                self.rank_text,
                align="center",
            ),
            self.get_swid_plot(),
            pn.Row(
                # swid_analysis,
                # swid_rank_analysis,
            ),
            margin=(25, 75, 75, 75),
        )

    def serve(self):
        # pn.state.add_periodic_callback(self.data.refresh, 3000)
        self.layout().servable()


def run():
    reader = OrcaReader(TRACE_ROOT)
    print(f"Discovered tables: {', '.join(reader.tables)}")
    # gp = reader.get_glob_pattern("mpiw")
    # df = (
    #     pl.scan_parquet(gp, parallel="columns")
    #     .filter(pl.col("dura_ns") > 10_000_000)
    #     .group_by("probe_name")
    #     .agg(pl.len().alias("count"))
    #     .collect()
    #     .to_pandas()
    # )
    # print(df)

    dd = DashboardData(TRACE_ROOT)
    df = dd.get_swid_maxdura()
    print(df[df["dura_ms_max"] > 50])


if __name__ == "__main__":
    run()

# run_panel().servable()
App(TRACE_ROOT).serve()
