"""Demo using OrcaReader for timestep and swid range queries."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from orcareader import OrcaReader


SUITES_ROOT = Path("/mnt/ltio/orcajobs/suites")

Range = tuple[int, int]


def run_timestep_queries(reader: OrcaReader, ts_range: Range) -> None:
    print(f"=== Timestep: mpi_collectives, range {ts_range} ===")
    df = reader.read_ts("mpi_collectives", ts_range)
    print(f"Shape: {df.shape}")
    print(df.head(10))
    print()

    print(f"=== Timestep: kokkos_events, range {ts_range} ===")
    df = reader.read_ts("kokkos_events", ts_range)
    print(f"Shape: {df.shape}")
    print(df.head(10))
    print()


def run_swid_queries(reader: OrcaReader, swid_range: Range) -> None:
    print(f"=== SWID: mpi_collectives, range {swid_range} ===")
    df = reader.read_swid(swid_range)
    print(f"Shape: {df.shape}")
    print(df.head(10))
    print()


def run_file_queries(reader: OrcaReader, swid_range: Range) -> None:
    print(f"=== File: kokkos_events, SWID {swid_range} ===")
    files = reader.query_swid_files(swid_range, table="kokkos_events")
    print(f"Files: {len(files)}")
    for f in files[:5]:
        print(f"  {f.name}")
    if len(files) > 5:
        print(f"  ... and {len(files) - 5} more")
    print()


def run_orca_events_queries(reader: OrcaReader, rank_range: Range) -> None:
    print(f"=== OrcaEvents: rank_range={rank_range} ===")
    df = reader.read_orca_events(ranks=rank_range)
    print(f"Shape: {df.shape}")
    print(df.head(10))
    print()


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    suite = "20251120_amr-agg4-r4096-n20-psmerrchk141-tmp"
    profile = "07_trace_tgt"
    trace_root = SUITES_ROOT / suite / profile

    print(f"Trace root: {trace_root}")
    reader = OrcaReader(trace_root)
    print(f"Discovered tables: {', '.join(reader.tables)}")
    print()

    run_timestep_queries(reader, ts_range=(13, 15))
    run_swid_queries(reader, swid_range=(60, 90))
    run_file_queries(reader, swid_range=(60, 90))
    run_orca_events_queries(reader, rank_range=(0, 100))


if __name__ == "__main__":
    main()
