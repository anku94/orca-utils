#!/usr/bin/env python3
#
# AE driver for A2: run the three benchmark queries (Outlier Waits,
# Outlier Collectives, Timestamp Range) against a populated suitedir,
# emitting a CSV. Reuses tau-analysis/tracequery and run_querybench.
# Documentation-of-intent skeleton; expect to revise against real runs.
#

import sys
from pathlib import Path

import pandas as pd

# Make tau-analysis importable
SCRIPT_DIR = Path(__file__).resolve().parent
TAU_DIR = SCRIPT_DIR.parent / "tau-analysis"
sys.path.insert(0, str(TAU_DIR))

from run_querybench import (
    SingleConfig,
    orca_count_sync_maxdur, orca_count_mpi_wait_dur, orca_count_window,
    dftracer_count_sync_maxdur, dftracer_count_mpi_wait_dur, dftracer_count_window,
    caliper_count_sync_maxdur, caliper_count_mpi_wait_dur, caliper_count_window,
)


def get_suitedir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    sd = Path("/tmp/orca-ae-suites").resolve()
    if not sd.exists():
        raise SystemExit(f"suitedir not found: {sd} (pass as argv[1])")
    return sd


# Profile dir name patterns we know how to query (per tau-analysis convention)
ORCA_PROFILE_NAMES = ("or_trace_mpisync", "or_tracetgt")
DFTRACER_PROFILE_NAMES = ("dftracer",)
CALIPER_PROFILE_NAMES = ("caliper_tracetgt",)


def _find_profiles(suitedir: Path, names: tuple[str, ...]) -> list[Path]:
    out = []
    for child in sorted(suitedir.iterdir()):
        if not child.is_dir():
            continue
        # Profile dirs are like "07_or_tracetgt"
        suffix = child.name.split("_", 1)[-1]
        if suffix in names:
            out.append(child)
    return out


# run_orca: three queries against each ORCA profile's parquet/ subdir
def run_orca(suitedir: Path, results: list):
    for prof in _find_profiles(suitedir, ORCA_PROFILE_NAMES):
        pq = prof / "parquet"
        if not pq.exists():
            print(f"-WARN- skip ORCA profile (no parquet): {prof}")
            continue
        print(f"-INFO- ORCA queries: {prof.name}")
        results.append(orca_count_sync_maxdur(pq))
        results.append(orca_count_mpi_wait_dur(pq))
        results.append(orca_count_window(pq))


# run_dftracer: three queries against each DFTracer profile
def run_dftracer(suitedir: Path, results: list, tmp_dir: Path):
    for prof in _find_profiles(suitedir, DFTRACER_PROFILE_NAMES):
        cfg = SingleConfig(trace_dir=prof, tmp_dir=tmp_dir, nranks=-1, nworkers=16)
        print(f"-INFO- DFTracer queries: {prof.name}")
        results.append(dftracer_count_sync_maxdur(cfg))
        results.append(dftracer_count_mpi_wait_dur(cfg))
        results.append(dftracer_count_window(cfg))


# run_caliper: three queries against each Caliper profile
def run_caliper(suitedir: Path, results: list, tmp_dir: Path):
    for prof in _find_profiles(suitedir, CALIPER_PROFILE_NAMES):
        cfg = SingleConfig(trace_dir=prof, tmp_dir=tmp_dir, nranks=-1, nworkers=16)
        print(f"-INFO- Caliper queries: {prof.name}")
        results.append(caliper_count_sync_maxdur(cfg))
        results.append(caliper_count_mpi_wait_dur(cfg))
        results.append(caliper_count_window(cfg))


def main():
    suitedir = get_suitedir()
    tmp_dir = suitedir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_csv = suitedir / "query_latencies.csv"

    print(f"-INFO- suitedir: {suitedir}")

    results = []
    # Comment out any of the three for a partial trial.
    run_orca(suitedir, results)
    run_dftracer(suitedir, results, tmp_dir)
    run_caliper(suitedir, results, tmp_dir)

    df = pd.DataFrame(results)
    print(df)
    print(f"-INFO- writing to {out_csv}")
    df.to_csv(out_csv, index=False)


if __name__ == "__main__":
    main()
