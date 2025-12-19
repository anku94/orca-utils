import time

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from datetime import datetime

import dask
import dftracer.analyzer as analyzer
import pandas as pd
import polars as pl

from suite_utils import get_repo_data_dir

Range = tuple[float, float]
QueryType = Literal["count_window", "count_sync_maxdur", "count_mpi_wait_dur"]


@dataclass
class QueryResult:
    query_name: QueryType
    trace_dir: Path
    run_type: str
    data: str
    total_us: int


def now_micros() -> int:
    return int(time.monotonic_ns() / 1000)


def func_micros(fn):
    start = now_micros()
    result = fn()
    end = now_micros()
    return result, (end - start)


class DfQuery:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.trace_dir = run_dir / "trace"

    def count_window(self) -> QueryResult:
        dfa = analyzer.init_with_hydra(hydra_overrides=[
            "analyzer=dftracer",
            "cluster=local",
            f"trace_path={self.trace_dir}",
        ])

        traces, read_us = func_micros(lambda: dfa.analyzer.read_trace(
            str(self.trace_dir), extra_columns=None, extra_columns_fn=None))

        tstart_min, _ = dask.compute(
            traces.time_start.min(), traces.time_start.max())

        x_us = 1e6
        time_range = (tstart_min, tstart_min + x_us)

        count, query_us = func_micros(lambda: traces.time_start.between(
            *time_range).count().compute())

        print(
            f"[Dftracer]: evtcnt={count}, read_ms={read_us/1e3:.1f} ms, query_ms={query_us/1e3:.1f} ms")

        return QueryResult(
            query_name="count_window",
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"time_range={time_range},evtcnt={count}",
            total_us=read_us + query_us,
        )

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> QueryResult:
        query_name: QueryType = "count_sync_maxdur"
        collectives = {
            "MPI_Allgather",
            "MPI_Allreduce",
            "MPI_Alltoall",
            "MPI_Barrier",
            "MPI_Bcast",
            "MPI_Reduce",
        }
        dfa = analyzer.init_with_hydra(hydra_overrides=[
            "analyzer=dftracer",
            "cluster=local",
            f"trace_path={self.trace_dir}",
        ])

        traces, read_us = func_micros(lambda: dfa.analyzer.read_trace(
            str(self.trace_dir), extra_columns=None, extra_columns_fn=None))

        def run_query() -> int:
            # Filter for collectives and compute to Pandas to avoid Dask shuffle metadata issues.
            # MPI collectives are sparse enough that they should comfortably fit in memory.
            mpi_filtered = traces[(traces.cat == "mpi") &
                                  (traces.func_name.isin(collectives))]
            mpi_pd = mpi_filtered[["pid", "time_start", "time"]].compute()

            if mpi_pd.empty:
                return 0

            # Ensure data is sorted by time_start within each pid for consistent sequence numbering
            mpi_pd = mpi_pd.sort_values(["pid", "time_start"])
            mpi_pd["seq"] = mpi_pd.groupby("pid").cumcount()

            # Find the max duration across all ranks for each collective sequence number
            per_seq = mpi_pd.groupby("seq")["time"].max()
            return int(((per_seq * 1e3) > thresh_ms).sum())

        count, query_us = func_micros(run_query)

        print(
            f"[Dftracer]: collective_max_dura_ms>{thresh_ms:g}, count={count}, "
            f"read_ms={read_us/1e3:.1f} ms, query_ms={query_us/1e3:.1f} ms")

        return QueryResult(
            query_name=query_name,
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"thresh_ms={thresh_ms:g},count={count}",
            total_us=read_us + query_us,
        )

    def count_mpi_wait_dur(self, thresh_ms: float = 10.0) -> QueryResult:
        query_name: QueryType = "count_mpi_wait_dur"
        dfa = analyzer.init_with_hydra(hydra_overrides=[
            "analyzer=dftracer",
            "cluster=local",
            f"trace_path={self.trace_dir}",
        ])

        traces, read_us = func_micros(lambda: dfa.analyzer.read_trace(
            str(self.trace_dir), extra_columns=None, extra_columns_fn=None))

        def run_query() -> int:
            mpi_wait = traces[(traces.cat == "mpi") &
                              (traces.func_name == "MPI_Wait")]
            return ((mpi_wait.time * 1e3) >= thresh_ms).sum().compute()

        count, query_us = func_micros(run_query)

        print(
            f"[Dftracer]: mpi_wait_ms>{thresh_ms:g}, count={count}, "
            f"read_ms={read_us/1e3:.1f} ms, query_ms={query_us/1e3:.1f} ms")

        return QueryResult(
            query_name=query_name,
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"thresh_ms={thresh_ms:g},count={count}",
            total_us=read_us + query_us,
        )


class OrcaQuery:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.trace_dir = run_dir / "parquet"

    def get_schemas(self, exclude: list[str] = []) -> list[Path]:
        "Get all available schemas except orca_events and exclude'd"

        subdirs = [f for f in self.trace_dir.iterdir() if f.is_dir()
                   and f.name != "orca_events" and f.name not in exclude]
        return subdirs

    def get_rowcnt_in_timerange(self, schema_dir: Path, time_range: Range) -> int:
        glob_pattern = str(schema_dir / "**/*.parquet")
        qexpr = pl.col("ts_ns").is_between(*time_range)
        df = pl.scan_parquet(glob_pattern, parallel="columns").select(
            pl.col("ts_ns")).filter(qexpr).count().collect()
        return df["ts_ns"].item()

    def count_window(self) -> QueryResult:
        query_name: QueryType = "count_window"
        patt = str(self.trace_dir / "mpi_collectives" / "**/*.parquet")
        min_expr = pl.col("ts_ns").min().alias("tsns_min")
        max_expr = pl.col("ts_ns").max().alias("tsns_max")
        df = pl.scan_parquet(
            patt, parallel="columns").select(min_expr, max_expr).collect()

        x_ns = 1e9
        tsns_min = df["tsns_min"].item()
        time_range = (tsns_min, tsns_min + x_ns)

        orca_schemas = self.get_schemas(exclude=["mpi_messages"])
        evtcnt, scan_us = func_micros(lambda: sum(
            self.get_rowcnt_in_timerange(schema_dir, time_range)
            for schema_dir in orca_schemas))

        print(f"[Orca]: evtcnt={evtcnt}, scan_ms={scan_us/1e3:.1f} ms")

        return QueryResult(
            query_name=query_name,
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"time_range={time_range},evtcnt={evtcnt}",
            total_us=scan_us,
        )

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> QueryResult:
        query_name: QueryType = "count_sync_maxdur"
        patt = str(self.trace_dir / "mpi_collectives" / "**/*.parquet")

        def run_query() -> int:
            df = (pl.scan_parquet(patt, parallel="columns")
                  .group_by("swid")
                  .agg((pl.col("dura_ns") / 1e6).max().alias("max_dura_ms"))
                  .filter(pl.col("max_dura_ms") > thresh_ms)
                  .select(pl.len())
                  .collect())
            return df["len"].item()

        count, query_us = func_micros(run_query)

        print(
            f"[Orca]: collective_max_dura_ms>{thresh_ms:g}, count={count}, query_ms={query_us/1e3:.1f} ms")

        return QueryResult(
            query_name=query_name,
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"thresh_ms={thresh_ms:g},count={count}",
            total_us=query_us,
        )

    def count_mpi_wait_dur(self, thresh_ms: float = 10.0) -> QueryResult:
        query_name: QueryType = "count_mpi_wait_dur"
        patt = str(self.trace_dir / "mpi_messages" / "**/*.parquet")

        def run_query() -> int:
            df = (pl.scan_parquet(patt, parallel="columns")
                  .filter(pl.col("probe_name") == "MPI_Wait")
                  .filter((pl.col("dura_ns") / 1e6) > thresh_ms)
                  .select(pl.len())
                  .collect())
            return df["len"].item()

        count, query_us = func_micros(run_query)

        print(
            f"[Orca]: mpi_wait_ms>{thresh_ms:g}, count={count}, query_ms={query_us/1e3:.1f} ms")

        return QueryResult(
            query_name=query_name,
            trace_dir=self.trace_dir,
            run_type=self.run_dir.name,
            data=f"thresh_ms={thresh_ms:g},count={count}",
            total_us=query_us,
        )


def run():
    suite_dir = Path(
        "/mnt/ltio/orcajobs/suites/20251212/amr-agg1-r512-n20-run1")

    # get string yyyymmdd-hhmm from time now
    now_str = datetime.now().strftime("%Y%m%d-%H%M")
    csv_name = f"query_results_{now_str}.csv"
    csv_path = get_repo_data_dir() / csv_name

    print(f"Writing results to {csv_path}")

    df_query = DfQuery(suite_dir / "11_dftracer")
    orca_query = OrcaQuery(suite_dir / "07_trace_tgt")
    results = [
        df_query.count_window(),
        orca_query.count_window(),
        orca_query.count_sync_maxdur(thresh_ms=10.0),
        df_query.count_sync_maxdur(thresh_ms=10.0),
        df_query.count_mpi_wait_dur(thresh_ms=1.0),
        orca_query.count_mpi_wait_dur(thresh_ms=1.0),
    ]
    df = pd.DataFrame(results)
    df.to_csv(csv_path, index=False)
    print(df)


if __name__ == "__main__":
    run()
