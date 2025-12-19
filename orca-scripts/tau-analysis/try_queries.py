import dask
import sys
import logging
import json
import pandas as pd
from pathlib import Path
import polars as pl
import time
import dftracer.analyzer as analyzer

from dataclasses import dataclass

logger = logging.getLogger(__name__)

Range = tuple[float, float]


@dataclass
class QueryResult:
    trace_dir: Path
    time_range: Range
    evtcnt: int
    read_us: int
    comp_us: int


def now_micros() -> int:
    # get monotonic time for benchmarking
    return int(time.monotonic_ns() / 1000)


def test_dftracer(run_dir: Path):
    trace_dir = run_dir / 'trace-small'
    dfa = analyzer.init_with_hydra(hydra_overrides=[
        'analyzer=dftracer',
        'cluster=local',
        f'trace_path={trace_dir}',
    ])

    _ts_readbeg = now_micros()
    traces = dfa.analyzer.read_trace(
        str(trace_dir), extra_columns=None, extra_columns_fn=None)
    _ts_readend = now_micros()

    # get min/max for time_start via dask.compute
    tstart_min, _ = dask.compute(
        traces.time_start.min(), traces.time_start.max())

    x_us = 1e6
    _ts_compstart = now_micros()
    time_range = (tstart_min, tstart_min + x_us)

    count = traces.time_start.between(
        *time_range).count().compute()
    _ts_compend = now_micros()

    read_us = (_ts_readend - _ts_readbeg)
    comp_us = (_ts_compend - _ts_compstart)

    print(f"DFTracer: {count} events in {x_us/1e3:.1f} ms")
    print(
        f"Read time: {read_us/1e3:.1f} ms, Compute time: {comp_us/1e3:.1f} ms")
    return QueryResult(
        trace_dir=trace_dir,
        time_range=time_range,
        evtcnt=count,
        read_us=read_us,
        comp_us=comp_us,
    )


def get_orca_schemas(run_dir: Path, exclude: list[str] = []) -> list[Path]:
    pq_dir = run_dir / 'parquet'
    # get all immediate subdirs
    subdirs = [f for f in pq_dir.iterdir() if f.is_dir()
               and f.name != "orca_events" and f.name not in exclude]
    return subdirs


def get_orca_evtcnt(schema_dir: Path, time_range: Range) -> int:
    glob_pattern = str(schema_dir / '**/*.parquet')
    df = pl.scan_parquet(glob_pattern, parallel="columns").select(
        pl.col('ts_ns')).filter(
        pl.col('ts_ns').is_between(time_range[0], time_range[1])).count().collect()

    return df['ts_ns'].item()


def test_orca(run_dir: Path) -> QueryResult:
    trace_dir = run_dir / 'parquet'
    patt = str(trace_dir / 'mpi_collectives' / '**/*.parquet')
    min_expr = pl.col('ts_ns').min().alias('tsns_min')
    max_expr = pl.col('ts_ns').max().alias('tsns_max')
    df = pl.scan_parquet(patt, parallel="columns").select(
        min_expr, max_expr).collect()

    x_ns = 1e9
    tsns_min = df['tsns_min'].item()
    time_range = (tsns_min, tsns_min + x_ns)

    orca_schemas = get_orca_schemas(run_dir, exclude=["mpi_messages"])
    print(f"ORCA: {len(orca_schemas)} schemas")

    _ts_scanbeg = now_micros()
    evtcnt = 0
    for schema_dir in orca_schemas:
        evtcnt += get_orca_evtcnt(schema_dir, time_range)
    _ts_scanend = now_micros()

    scan_us = (_ts_scanend - _ts_scanbeg)

    print(f"ORCA: {evtcnt} events in {x_ns/1e6:.1f} ms")
    print(f"ORCA scan time: {scan_us/1e3:.1f} ms")

    return QueryResult(
        trace_dir=run_dir,
        time_range=time_range,
        evtcnt=evtcnt,
        read_us=scan_us,
        comp_us=0,
    )


def run():
    suite_dir = Path(
        '/mnt/ltio/orcajobs/suites/20251212/amr-agg1-r512-n20-run1')
    df_qr = test_dftracer(suite_dir / '11_dftracer')
    orca_qr = test_orca(suite_dir / '07_trace_tgt')
    df = pd.DataFrame([df_qr, orca_qr])
    # df.to_csv('query_results.csv', index=False)
    print(df)


if __name__ == "__main__":
    run()
