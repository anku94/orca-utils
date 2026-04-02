import subprocess
import datetime
import suite_utils as su

import pandas as pd
import tracequery as tq
from tracequery import QueryResult, func_micros

from pathlib import Path
from dataclasses import dataclass
import time


def disable_dask_spillover():
    print("-INFO- Disabling Dask spillover")
    import dask

    dask.config.set({"dataframe.shuffle.method": "tasks"})


@dataclass
class SingleConfig:
    trace_dir: Path
    tmp_dir: Path
    nranks: int = -1
    nworkers: int = 1


def drop_caches():
    """Flush filesystem caches. Requires sudo."""
    subprocess.run(
        ["sudo", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"],
        check=True,
    )


def caliper_count_sync_maxdur(
    config: SingleConfig, thresh_ms: float = 10.0
) -> QueryResult:
    print("-INFO- Running caliper_count_sync_maxdur")

    drop_caches()
    cq = tq.CaliperQuery(
        config.trace_dir, nranks=config.nranks, nworkers=config.nworkers
    )
    count, us = func_micros(lambda: cq.count_sync_maxdur(thresh_ms))
    del cq

    print(f"-INFO- Caliper count_sync_maxdur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=config.trace_dir,
        run_type="caliper",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def caliper_count_mpi_wait_dur(
    config: SingleConfig, thresh_ms: float = 1.0
) -> QueryResult:
    print("-INFO- Running caliper_count_mpi_wait_dur")

    drop_caches()
    cq = tq.CaliperQuery(
        config.trace_dir, nranks=config.nranks, nworkers=config.nworkers
    )
    count, us = func_micros(lambda: cq.count_mpi_wait_dur(thresh_ms))
    del cq

    print(f"-INFO- Caliper count_mpi_wait_dur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=config.trace_dir,
        run_type="caliper",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def caliper_count_window(config: SingleConfig, window_s: float = 1.0) -> QueryResult:
    print("-INFO- Running caliper_count_window")

    cq = tq.CaliperQuery(
        config.trace_dir, nranks=config.nranks, nworkers=config.nworkers
    )
    time_range = cq.get_window_bounds(window_s)
    del cq
    drop_caches()

    cq = tq.CaliperQuery(
        config.trace_dir, nranks=config.nranks, nworkers=config.nworkers
    )
    count, us = func_micros(lambda: cq.count_window(time_range))
    del cq

    print(f"-INFO- Caliper count_window took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_window",
        trace_dir=config.trace_dir,
        run_type="caliper",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


def orca_count_sync_maxdur(trace_dir: Path, thresh_ms: float = 10.0) -> QueryResult:
    print("-INFO- Running orca_count_sync_maxdur")

    drop_caches()
    oq = tq.OrcaQuery(trace_dir)
    count, us = func_micros(lambda: oq.count_sync_maxdur(thresh_ms))

    print(f"-INFO- ORCA count_sync_maxdur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def orca_count_mpi_wait_dur(trace_dir: Path, thresh_ms: float = 1.0) -> QueryResult:
    print("-INFO- Running orca_count_mpi_wait_dur")

    drop_caches()
    oq = tq.OrcaQuery(trace_dir)
    count, us = func_micros(lambda: oq.count_mpi_wait_dur(thresh_ms))

    print(f"-INFO- ORCA count_mpi_wait_dur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def orca_count_window(trace_dir: Path, window_s: float = 1.0) -> QueryResult:
    print("-INFO- Running orca_count_window")

    oq = tq.OrcaQuery(trace_dir)
    time_range = oq.get_window_bounds(window_s)
    del oq
    drop_caches()
    oq = tq.OrcaQuery(trace_dir)

    count, us = func_micros(lambda: oq.count_window(time_range))

    print(f"-INFO- ORCA count_window took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_window",
        trace_dir=oq.trace_dir,
        run_type="orca",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


def dftracer_count_sync_maxdur(
    config: SingleConfig, thresh_ms: float = 10.0
) -> QueryResult:
    print("-INFO- Running dftracer_count_sync_maxdur")

    drop_caches()
    with tq.DfTracerQuery(config.trace_dir, tmp_dir=config.tmp_dir) as dq:
        count, us = func_micros(lambda: dq.count_sync_maxdur(thresh_ms))

    print(f"-INFO- DfTracer count_sync_maxdur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_sync_maxdur",
        trace_dir=config.trace_dir,
        run_type="dftracer",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def dftracer_count_mpi_wait_dur(
    config: SingleConfig, thresh_ms: float = 1.0
) -> QueryResult:
    print("-INFO- Running dftracer_count_mpi_wait_dur")

    drop_caches()
    with tq.DfTracerQuery(config.trace_dir, tmp_dir=config.tmp_dir) as dq:
        count, us = func_micros(lambda: dq.count_mpi_wait_dur(thresh_ms))

    print(f"-INFO- DfTracer count_mpi_wait_dur took {us/1e3:.1f} ms")
    return QueryResult(
        query_name="count_mpi_wait_dur",
        trace_dir=config.trace_dir,
        run_type="dftracer",
        data=f"thresh_ms={thresh_ms},count={count}",
        total_us=us,
    )


def dftracer_count_window(config: SingleConfig, window_s: float = 1.0) -> QueryResult:
    with tq.DfTracerQuery(config.trace_dir, tmp_dir=config.tmp_dir) as dq:
        time_range = dq.get_window_bounds(window_s)
    drop_caches()

    with tq.DfTracerQuery(config.trace_dir, tmp_dir=config.tmp_dir) as dq:
        count, us = func_micros(lambda: dq.count_window(time_range))

    return QueryResult(
        query_name="count_window",
        trace_dir=config.trace_dir,
        run_type="dftracer",
        data=f"window_s={window_s},count={count}",
        total_us=us,
    )


@dataclass
class BenchmarkConfig:
    calicfg: SingleConfig
    orcacfg: SingleConfig
    dftcfg: SingleConfig


def run_benchmarks(config: BenchmarkConfig) -> list[QueryResult]:
    # assert all dirs exist
    assert config.calicfg.trace_dir.exists()
    assert config.orcacfg.trace_dir.exists()
    assert config.dftcfg.trace_dir.exists()

    results = []

    # cali_cfg = config.caliper_config
    # results.append(caliper_count_sync_maxdur(cali_cfg))
    # results.append(caliper_count_mpi_wait_dur(cali_cfg))
    # results.append(caliper_count_window(cali_cfg))

    orca_dir = config.orcacfg.trace_dir
    results.append(orca_count_sync_maxdur(orca_dir))
    results.append(orca_count_mpi_wait_dur(orca_dir))
    results.append(orca_count_window(orca_dir))

    results.append(dftracer_count_sync_maxdur(config.dftcfg, thresh_ms=10.0))
    results.append(dftracer_count_mpi_wait_dur(config.dftcfg, thresh_ms=1.0))
    results.append(dftracer_count_window(config.dftcfg, window_s=1.0))

    return results


def get_rdf_path() -> Path:
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    csv_name = f"query_results_{now_str}.csv"
    csv_path = su.get_repo_data_dir() / csv_name
    print(f"Writing results to {csv_path}")
    return csv_path


def main():
    suite_root = Path("/mnt/ltio/orcajobs/suites")
    rdf_path = get_rdf_path()
    tmp_dir = Path("/tmp/dftracer")

    caliper_profdir = suite_root / "20251230/amr-agg1-r512-n20-run1"
    caliper_tracedir = caliper_profdir / "18_caliper_tracetgt/trace"
    cali_cfg = SingleConfig(
        trace_dir=caliper_tracedir, tmp_dir=tmp_dir, nranks=2, nworkers=2
    )

    orca_profdir = suite_root / "20251229/amr-agg1-r512-n20-run1"
    orca_tracedir = orca_profdir / "07_or_tracetgt/parquet"
    orca_cfg = SingleConfig(
        trace_dir=orca_tracedir, tmp_dir=tmp_dir, nranks=-1, nworkers=16
    )

    dftracer_profdir = suite_root / "20251212/amr-agg1-r512-n20-run1"
    dftracer_tracedir = dftracer_profdir / "11_dftracer/trace-small"
    dftracer_cfg = SingleConfig(
        trace_dir=dftracer_tracedir, tmp_dir=tmp_dir, nranks=-1, nworkers=16
    )

    config = BenchmarkConfig(
        calicfg=cali_cfg,
        orcacfg=orca_cfg,
        dftcfg=dftracer_cfg,
    )

    results = run_benchmarks(config)
    rdf = pd.DataFrame(results)
    print(rdf)
    rdf.to_csv(rdf_path, index=False)


def run_suite(suite: su.Suite, tmp_dir: Path, ntries: int = 1):
    suite_root = suite.suitedir.parent.name
    print(f"Running suite: {suite_root}/{suite.name}")
    rdf_path = su.get_repo_data_dir() / f"20260105_query_results_{suite_root}_{suite.name}.csv"
    print(f"Writing results to {rdf_path}")

    orca_tracedir = suite.get_prof_path("07_or_tracetgt") / "parquet"
    print(f"ORCA tracedir: {orca_tracedir}")
    assert orca_tracedir.exists()
    orca_cfg = SingleConfig(
        trace_dir=orca_tracedir, tmp_dir=tmp_dir, nranks=-1, nworkers=16
    )

    caliper_tracedir = suite.get_prof_path("17_caliper_tracetgt") / "trace"
    assert caliper_tracedir.exists()
    print(f"Caliper tracedir: {caliper_tracedir}")
    cali_cfg = SingleConfig(
        trace_dir=caliper_tracedir, tmp_dir=tmp_dir, nranks=-1, nworkers=16
    )

    dftracer_tracedir = suite.get_prof_path("11_dftracer") / "trace"
    print(f"DfTracer tracedir: {dftracer_tracedir}")
    assert dftracer_tracedir.exists()
    dftracer_cfg = SingleConfig(
        trace_dir=dftracer_tracedir, tmp_dir=tmp_dir, nranks=-1, nworkers=16
    )

    config = BenchmarkConfig(
        calicfg=cali_cfg,
        orcacfg=orca_cfg,
        dftcfg=dftracer_cfg,
    )

    for _ in range(ntries):
        results = run_benchmarks(config)
        if rdf_path.exists():
            rdf_cur = pd.DataFrame(results)
            rdf_prev = pd.read_csv(rdf_path)
            rdf = pd.concat([rdf_prev, rdf_cur], ignore_index=True)
        else:
            rdf = pd.DataFrame(results)

        print(f"Writing {len(rdf)} rows to {rdf_path}")
        rdf.to_csv(rdf_path, index=False)


def main_new():
    tmp_dir = Path("/mnt/ltio/orca-tmp")
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20260102")

    suites = su.read_v2_suites(suite_dir)
    suites = sorted(suites, key=lambda s: s.nsteps)
    # ranks = [2048, 4096]
    suites = [s for s in suites if s.nsteps == 20]

    print(f"Running {len(suites)} suites")
    for suite in suites:
        print(f"Running suite: {suite.name}")
        run_suite(suite, tmp_dir, ntries=3)


if __name__ == "__main__":
    disable_dask_spillover()
    main_new()
