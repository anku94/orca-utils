import pandas as pd
import polars as pl
import glob

TRACE_ROOT = "/mnt/ltio/orcajobs"

class TraceData:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.trace_dirs = self.get_tracedirs(self.run_dir)

    @classmethod
    def get_tracedirs(cls, run_dir):
        trace_dirs = glob.glob(f"{run_dir}/pqroot/*")
        return trace_dirs

    @classmethod
    def get_tracefiles(cls, run_dir: str, trace_name: str):
        glob_patt = f"{run_dir}/pqroot/{trace_name}/**/*.parquet"
        trace_dirs = glob.glob(glob_patt, recursive=True)
        return trace_dirs

    def get_trace_files(self, trace_name: str):
        return self.get_tracefiles(self.run_dir, trace_name)

    def read_entire_trace(self, trace_name: str):
        trace_dir = f"{self.run_dir}/pqroot/{trace_name}"
        ds = pl.read_parquet(f"{trace_dir}/**/*.parquet", parallel="columns")

        return ds

def get_rundir(run_id: int) -> str:
    run_dir = f"{TRACE_ROOT}/run{run_id}"
    return run_dir


def get_last_rundir() -> str:
    ptr_path = "/mnt/ltio/orcajobs/current"
    dir_path = open(ptr_path, "r").read().strip()
    return dir_path

def count_kokkos_events():
    tr = TraceData(f"{TRACE_ROOT}/run4")
    kokkos = tr.read_entire_trace("kokkos_events")
    counts = kokkos.group_by("probe_name").count()
    # divide count by (512 * 30)
    counts = counts.with_columns(
        (pl.col("count") / (512 * 30)).alias("avg_per_rank_per_timestep")
        )
    counts

    tr = TraceData(f"{TRACE_ROOT}/run4")
    mpi_msgs = tr.read_entire_trace("mpi_messages")
    pass


def check_mpi_waits():
    tr0 = TraceData(f"{TRACE_ROOT}/run7")
    msgs = tr0.read_entire_trace("mpi_messages")
    #msgs["msg_bytes"].describe()
    nzbytes = msgs.filter(pl.col("msg_bytes") > 0)
    nzbytes["msg_bytes"].quantile(0.85)
    waits = msgs.filter(pl.col("probe_name") == "MPI_Wait")
    waits["dura_ns"].describe()

    kokkos = tr0.read_entire_trace("kokkos_events")
    regions = kokkos.filter(pl.col("probe_name") == "region")
    regions["dura_ns"].describe()
    regions

    # group regions by name, get percentiles on dura_ns
    regions.groupby("probe_name").agg(
        [
            pl.col("dura_ns").min(),
            pl.col("dura_ns").max(),
            pl.col("dura_ns").mean(),
            pl.col("dura_ns").sum(),
            pl.col("dura_ns").count(),
            pl.col("dura_ns").quantile(0.5).alias("p50"),
            pl.col("dura_ns").quantile(0.9).alias("p90"),
            pl.col("dura_ns").quantile(0.99).alias("p99"),
        ]
    )

    # add dura_ms
    regions = regions.with_columns(
        (pl.col("dura_ns") / 1_000_000).alias("dura_ms")
    )

    regs0 = regions.filter(pl.col("rank") == 0)
    regs0.sort(by=["timestep", "ts_ns"])
    regs0.write_csv("kokkos_regions_r0.csv")

    regs820 = regions.filter((pl.col("timestep") == 82) & (pl.col("rank") == 0))
    regs820.sort(by="ts_ns")
    regs820.write_csv("kokkos_regions_t82_r0.csv")


    grouped = regions.group_by(["timestep", "name"]).agg([
        pl.col("dura_ms").min().alias("min"),
        pl.col("dura_ms").max().alias("max"),
        pl.col("dura_ms").mean().alias("mean"),
        pl.col("dura_ms").sum().alias("sum"),
        pl.col("dura_ms").count().alias("count"),
        pl.col("dura_ms").quantile(0.5).alias("p50"),
        pl.col("dura_ms").quantile(0.9).alias("p90"),
        pl.col("dura_ms").quantile(0.99).alias("p99"),
    ])

    print(grouped)
    # sort by timestep, then mean
    grouped = grouped.sort(by=["timestep", "mean"])
    grouped
    # write to csv
    grouped.write_csv("kokkos_region_summary.csv")
    pass

def stepwise_totals_dura_df(df: pd.DataFrame):
    df["dura_us"] = df["dura_ns"] / 1_000
    df["dura_ms"] = df["dura_ns"] / 1_000_000

    pta_filter = df["probe_name"].str.contains("PostTimestepAdvance")
    df2 = df[pta_filter]

    cols = ["timestep", "probe_name", "dura_ms", "dura_us"]
    df2 = df2[cols]

    df2
    df[df["timestep"] == 13][cols]
    return df_2


def summarize_dura_df(df: pd.DataFrame):
    df["dura_us"] = df["dura_ns"] / 1_000
    df["dura_ms"] = df["dura_ns"] / 1_000_000

    cols = ["probe_name", "dura_ms", "dura_us"]
    df2 = df[cols]
    df2[df2["probe_name"].str.contains("PostTimestepAdvance")]
    df_agg = df2.groupby("probe_name").agg(
        {"dura_ms": ["min", "max", "mean", "sum", "count"]}
    )
    return df_agg

def read_mpi_messages():
    base_dir = f"{TRACE_ROOT}/run7/pqroot/mpi_messages"
    base_dir
    ds = pl.read_parquet(f"{base_dir}/**/*.parquet", parallel="columns")
    ds

    # filter on probe_name == "MPI_wait"
    ds_waits = ds.filter(pl.col("probe_name") == "MPI_Wait")
    #ds_waits["dura_ms"] = ds_waits["dura_ns"] / 1_000_000
    ds_waits = ds_waits.with_columns(
        (pl.col("dura_ns") / 1_000_000).alias("dura_ms")
    )
    ds_waits["dura_ns"].describe()
    ds_waits["dura_ms"].quantile(0.999999)
    # filter by dura_ms
    # get statistics on column dura_ns

    ds_waits.select(
        [
            pl.col("dura_ns").min(),
            pl.col("dura_ns").max(),
            pl.col("dura_ns").mean(),
            pl.col("dura_ns").sum(),
            pl.col("dura_ns").count(),
        ]
    )

    tr0 = TraceData(f"{TRACE_ROOT}/run7")
    msgs = tr0.read_entire_trace("mpi_messages")
    tf = tr0.get_trace_files("mpi_messages")[1]
    df = pd.read_parquet(tf)
    df["probe_name"].unique()
    df[df["probe_name"] == "MPI_Wait"]["dura_ns"].describe()
    pass


def analyze_orca_trace_polars(run_dir: str):
    orca_events = f"{run_dir}/pqroot/orca_events"
    ds = pl.read_parquet(f"{orca_events}/*.parquet", parallel="columns")
    ds
    pta_filter = ds["probe_name"].str.contains("PostTimestepAdvance")
    pta_ds = ds.filter(pta_filter).sort(by=["timestep"])
    pta_ds
    #groupby rank, aggregate val
    pta_times = pta_ds.group_by("rank").agg(pl.col("val").sum())
    pta_ms = pta_times.with_columns(
        (pl.col("val") / 1_000_000).alias("dura_ms")
    )
    pta_ms = pta_ms.sort(by="dura_ms")
    print(pta_ms.to_pandas().to_string())


def analyze_orca_trace(run_dir: str, rank: int):
    rank_trace = f"{run_dir}/pqroot/orca_events/rank_{rank}.parquet"
    rdf = pd.read_parquet(rank_trace)

    dura_df = rdf[rdf["op_type"] == "X"].copy()
    cntr_df = rdf[rdf["op_type"] == "C"].copy()

    cols = ["probe_name", "timestep", "val"]
    dura_df = dura_df[cols].copy()
    dura_df["dura_us"] = dura_df["val"] / 1_000 # val is dura_ns
    dura_df["dura_ms"] = dura_df["val"] / 1_000_000
    dura_df.drop(columns=["val"], inplace=True)

    dura_df_agg = dura_df.groupby("probe_name").agg(
        {
            "dura_ms": ["min", "max", "mean", "sum", "count"]
        }
    )

    print("\nAggregate times: ")
    print(dura_df_agg)

    pta_filter = dura_df["probe_name"].str.contains("PostTimestepAdvance")
    pta_df = dura_df[pta_filter].sort_values(by=["timestep"]).copy()

    print("\n\nTimestep-wise hook times: ")
    print(pta_df)


def analyze_event_volumes(run_dir: str):
    tr = TraceData(run_dir)
    kokkos_events = tr.read_entire_trace("kokkos_events")
    kokkos_events.group_by("name").count().sort(by="count")

    mpi_messages = tr.read_entire_trace("mpi_messages")
    mpi_messages.group_by("probe_name").count().sort(by="count")
    pass


def run():
    run_dir = get_rundir(0)
    rank = 20
    analyze_orca_trace(run_dir, 100)
    analyze_orca_trace(run_dir, 0)


if __name__ == "__main__":
    run()
