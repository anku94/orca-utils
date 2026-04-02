import copy
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
    print("-INFO- Dropping caches")
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


def get_rdf_path() -> Path:
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    csv_name = f"query_results_{now_str}.csv"
    csv_path = su.get_repo_data_dir() / csv_name
    print(f"Writing results to {csv_path}")
    return csv_path


def main_dftracer(basecfg: SingleConfig) -> list[QueryResult]:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20260102")
    suites = su.read_v2_suites(suite_dir)
    suites = sorted(suites, key=lambda s: s.nsteps)
    suites = [s for s in suites if s.nsteps == 20 and s.ranks == 4096]
    profs = [s.get_prof_path("11_dftracer") for s in suites]

    print(f"-INFO- Running DfTracer queries for {len(profs)} profiles")
    results: list[QueryResult] = []

    for prof in profs:
        print(f"-INFO- Running DfTracer queries for: {prof}")
        dftracer_cfg = copy.deepcopy(basecfg)
        dftracer_cfg.trace_dir = prof

        results.append(dftracer_count_sync_maxdur(dftracer_cfg, thresh_ms=10.0))
        results.append(dftracer_count_mpi_wait_dur(dftracer_cfg, thresh_ms=1.0))
        results.append(dftracer_count_window(dftracer_cfg, window_s=1.0))

    return results


def main_orca() -> list[QueryResult]:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20260102")
    suites = su.read_v2_suites(suite_dir)
    suites = sorted(suites, key=lambda s: s.nsteps)
    suites = [s for s in suites if s.nsteps == 20]
    profs = [s.get_prof_path("07_or_tracetgt") for s in suites]

    print(f"-INFO- Running ORCA queries for {len(profs)} profiles")
    results: list[QueryResult] = []

    for prof in profs:
        # Since ORCA queries are fast, we sneak in a warmup run to reduce variance
        # Unfortunately drop_caches() does not factor in some lustre server-side warmup
        print(f"-INFO- Warming up ORCA for: {prof}")
        prof_pqdir = prof / "parquet"
        assert prof_pqdir.exists()

        _ = orca_count_sync_maxdur(prof_pqdir)
        _ = orca_count_mpi_wait_dur(prof_pqdir)
        _ = orca_count_window(prof_pqdir)

        print(f"-INFO- Running ORCA queries for: {prof}")
        results.append(orca_count_sync_maxdur(prof_pqdir))
        results.append(orca_count_mpi_wait_dur(prof_pqdir))
        results.append(orca_count_window(prof_pqdir))

    return results


def main_caliper(basecfg: SingleConfig) -> list[QueryResult]:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20260106")
    suites = su.read_v2_suites(suite_dir)
    suites = sorted(suites, key=lambda s: s.nsteps)
    suites = [s for s in suites if s.nsteps == 20]
    profs = [s.get_prof_path("17_caliper_tracetgt") for s in suites]

    print(f"-INFO- Running Caliper queries for {len(profs)} profiles")
    results: list[QueryResult] = []

    for prof in profs:
        print(f"-INFO- Running Caliper queries for: {prof}")
        caliper_cfg = copy.deepcopy(basecfg)
        caliper_cfg.trace_dir = prof

        results.append(caliper_count_sync_maxdur(caliper_cfg))
        results.append(caliper_count_mpi_wait_dur(caliper_cfg))
        results.append(caliper_count_window(caliper_cfg))

    return results


def main():
    rdf_path = get_rdf_path()

    basecfg = SingleConfig(
        trace_dir=Path("/mnt/ltio/orca-tmp"),
        tmp_dir=Path("/mnt/ltio/orca-tmp"),
        nranks=-1,
        nworkers=16,
    )

    num_iters = 3

    results: list[QueryResult] = []
    for _ in range(num_iters):
        results.extend(main_dftracer(basecfg))
        # results.extend(main_orca())
        # results.extend(main_caliper(basecfg))
        pass

    rdf = pd.DataFrame(results)
    print(rdf)

    print(f"-INFO- Writing results to {rdf_path}")
    rdf.to_csv(rdf_path, index=False)


if __name__ == "__main__":
    # disable_dask_spillover()
    # main_new()
    main()
