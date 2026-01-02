import subprocess
import datetime
from suite_utils import get_repo_data_dir

import pandas as pd
import tracequery as tq
from tracequery import QueryResult, func_micros

from pathlib import Path
from dataclasses import dataclass

CALI_NRANKS = 2
CALI_NWORKERS = 2


def drop_caches():
    """Flush filesystem caches. Requires sudo."""
    subprocess.run(
        ["sudo", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"],
        check=True,
    )


def caliper_count_sync_maxdur(trace_dir: Path, thresh_ms: float = 10.0) -> QueryResult:
    drop_caches()
    cq = tq.CaliperQuery(trace_dir, nranks=CALI_NRANKS, nworkers=CALI_NWORKERS)
    count, us = func_micros(lambda: cq.count_sync_maxdur(thresh_ms))
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=cq.trace_dir,
        run_type="caliper",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def caliper_count_mpi_wait_dur(trace_dir: Path, thresh_ms: float = 1.0) -> QueryResult:
    drop_caches()
    cq = tq.CaliperQuery(trace_dir, nranks=CALI_NRANKS, nworkers=CALI_NWORKERS)
    count, us = func_micros(lambda: cq.count_mpi_wait_dur(thresh_ms))
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=cq.trace_dir,
        run_type="caliper",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def caliper_count_window(trace_dir: Path, window_s: float = 1.0) -> QueryResult:
    cq = tq.CaliperQuery(trace_dir, nranks=CALI_NRANKS, nworkers=CALI_NWORKERS)
    time_range = cq.get_window_bounds(window_s)
    del cq
    drop_caches()
    cq = tq.CaliperQuery(trace_dir, nranks=CALI_NRANKS, nworkers=CALI_NWORKERS)

    count, us = func_micros(lambda: cq.count_window(time_range))
    return QueryResult(
        query_name="count_window",
        trace_dir=cq.trace_dir,
        run_type="caliper",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


def orca_count_sync_maxdur(trace_dir: Path, thresh_ms: float = 10.0) -> QueryResult:
    drop_caches()
    oq = tq.OrcaQuery(trace_dir)
    count, us = func_micros(lambda: oq.count_sync_maxdur(thresh_ms))
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def orca_count_mpi_wait_dur(trace_dir: Path, thresh_ms: float = 1.0) -> QueryResult:
    drop_caches()
    oq = tq.OrcaQuery(trace_dir)
    count, us = func_micros(lambda: oq.count_mpi_wait_dur(thresh_ms))
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def orca_count_window(trace_dir: Path, window_s: float = 1.0) -> QueryResult:
    oq = tq.OrcaQuery(trace_dir)
    time_range = oq.get_window_bounds(window_s)
    del oq
    drop_caches()
    oq = tq.OrcaQuery(trace_dir)

    count, us = func_micros(lambda: oq.count_window(time_range))
    return QueryResult(
        query_name="count_window",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


def dftracer_count_sync_maxdur(trace_dir: Path, thresh_ms: float = 10.0) -> QueryResult:
    drop_caches()
    dq = tq.DfTracerQuery(trace_dir)
    count, us = func_micros(lambda: dq.count_sync_maxdur(thresh_ms))
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=dq.trace_dir,
        run_type="dftracer",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def dftracer_count_mpi_wait_dur(trace_dir: Path, thresh_ms: float = 1.0) -> QueryResult:
    drop_caches()
    dq = tq.DfTracerQuery(trace_dir)
    count, us = func_micros(lambda: dq.count_mpi_wait_dur(thresh_ms))
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=dq.trace_dir,
        run_type="dftracer",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def dftracer_count_window(trace_dir: Path, window_s: float = 1.0) -> QueryResult:
    dq = tq.DfTracerQuery(trace_dir)
    time_range = dq.get_window_bounds(window_s)
    del dq
    drop_caches()
    dq = tq.DfTracerQuery(trace_dir)

    count, us = func_micros(lambda: dq.count_window(time_range))
    return QueryResult(
        query_name="count_window",
        trace_dir=dq.trace_dir,
        run_type="dftracer",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


@dataclass
class BenchmarkConfig:
    caliper_tracedir: Path
    caliper_nranks: int
    caliper_nworkers: int
    orca_tracedir: Path
    dftracer_tracedir: Path


def run_benchmarks(config: BenchmarkConfig) -> list[QueryResult]:
    # assert all dirs exist
    assert config.caliper_tracedir.exists()
    assert config.orca_tracedir.exists()
    assert config.dftracer_tracedir.exists()

    results = []

    cali_dir = config.caliper_tracedir
    results.append(caliper_count_sync_maxdur(cali_dir))
    results.append(caliper_count_mpi_wait_dur(cali_dir))
    results.append(caliper_count_window(cali_dir))

    orca_dir = config.orca_tracedir
    results.append(orca_count_sync_maxdur(orca_dir))
    results.append(orca_count_mpi_wait_dur(orca_dir))
    results.append(orca_count_window(orca_dir))

    dft_dir = config.dftracer_tracedir
    results.append(dftracer_count_sync_maxdur(dft_dir))
    results.append(dftracer_count_mpi_wait_dur(dft_dir))
    results.append(dftracer_count_window(dft_dir))

    return results


def get_rdf_path() -> Path:
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    csv_name = f"query_results_{now_str}.csv"
    csv_path = get_repo_data_dir() / csv_name
    print(f"Writing results to {csv_path}")
    return csv_path


def main():
    suite_root = Path("/mnt/ltio/orcajobs/suites")
    rdf_path = get_rdf_path()

    caliper_profdir = suite_root / "20251230/amr-agg1-r512-n20-run1"
    caliper_tracedir = caliper_profdir / "18_caliper_tracetgt/trace"

    orca_profdir = suite_root / "20251229/amr-agg1-r512-n20-run1"
    orca_tracedir = orca_profdir / "07_or_tracetgt/parquet"

    dftracer_profdir = suite_root / "20251212/amr-agg1-r512-n20-run1"
    dftracer_tracedir = dftracer_profdir / "11_dftracer/trace-small"

    config = BenchmarkConfig(
        caliper_tracedir=caliper_tracedir,
        caliper_nranks=2,
        caliper_nworkers=2,
        orca_tracedir=orca_tracedir,
        dftracer_tracedir=dftracer_tracedir,
    )

    results = run_benchmarks(config)
    rdf = pd.DataFrame(results)
    print(rdf)
    rdf.to_csv(rdf_path, index=False)


if __name__ == "__main__":
    main()
