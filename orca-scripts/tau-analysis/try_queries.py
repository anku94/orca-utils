import dask
import sys
import logging
import json
import pandas as pd
from pathlib import Path
import polars as pl
import time
import dftracer.analyzer as analyzer

suite_dir = Path('/mnt/ltio/orcajobs/suites/20251212/amr-agg1-r512-n20-run1')

logger = logging.getLogger(__name__)


def now_micros() -> int:
    # get monotonic time for benchmarking
    return int(time.monotonic_ns() / 1000)


def test_dftracer():
    logger.info(f"Initializing dfanalyzer")

    _ts_start = now_micros()

    trace_dir = suite_dir / '11_dftracer' / 'trace-small'
    dfa = analyzer.init_with_hydra(hydra_overrides=[
        'analyzer=dftracer',
        'cluster=local',
        f'trace_path={trace_dir}',
    ])

    _ts_init = now_micros()
    print(f"Cluster initialized, analyzing trace")

    _ts_readbeg = now_micros()
    traces = dfa.analyzer.read_trace(
        trace_dir, extra_columns=None, extra_columns_fn=None)
    _ts_readend = now_micros()

    # get min/max for time_start via dask.compute
    tstart_min, _ = dask.compute(
        traces.time_start.min(), traces.time_start.max())

    x_us = 1e6
    _ts_compstart = now_micros()
    count = traces.time_start.between(
        tstart_min, tstart_min + x_us).count().compute()
    _ts_compend = now_micros()

    read_us = (_ts_readend - _ts_readbeg)
    comp_us = (_ts_compend - _ts_compstart)

    print(f"DFTracer: {count} events in {x_us/1e3} ms")
    print(
        f"Read time: {read_us/1e3:.1f} ms, Compute time: {comp_us/1e3:.1f} ms")


def get_orca_schemas(run_dir: Path) -> list[Path]:
    pq_dir = run_dir / 'parquet'
    # get all immediate subdirs
    subdirs = [f for f in pq_dir.iterdir() if f.is_dir()
               and f.name != "orca_events"]
    return subdirs


def get_orca_evtcnt(schema_dir: Path) -> int:
    glob_pattern = str(schema_dir / '**/*.parquet')
    df = pl.scan_parquet(glob_pattern, parallel="columns").select(
        pl.col('dura_ns').count()).collect()
    return df['dura_ns'].item()


def test_orca():
    run_dir = suite_dir / '07_trace_tgt'
    # lazy scan, print head
    glob_pattern = str(run_dir / 'parquet' /
                       'mpi_collectives' / '**/*.parquet')
    min_expr = pl.col('ts_ns').min().alias('min_ts_ns')
    max_expr = pl.col('ts_ns').max().alias('max_ts_ns')
    df = pl.scan_parquet(glob_pattern, parallel="columns").select(
        min_expr, max_expr).collect()

    x_ns = 1e9
    min_ts_ns = df['min_ts_ns'].item()

    orca_schemas = get_orca_schemas(run_dir)
    print(f"ORCA: {len(orca_schemas)} schemas")

    _ts_scanbeg = now_micros()
    evtcnt = 0
    for schema_dir in orca_schemas:
        evtcnt += get_orca_evtcnt(schema_dir)
    _ts_scanend = now_micros()

    scan_us = (_ts_scanend - _ts_scanbeg)

    print(f"ORCA: {evtcnt} events in {x_ns/1e6:.1f} ms")
    print(f"ORCA scan time: {scan_us/1e3:.1f} ms")


def run():
    test_dftracer()
    test_orca()


if __name__ == "__main__":
    run()
