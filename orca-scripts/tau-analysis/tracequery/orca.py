from pathlib import Path

import polars as pl

from .common import Range


class OrcaQuery:
    def __init__(self, trace_dir: Path):
        """trace_dir should be the parquet directory containing schema subdirs."""
        self.trace_dir = trace_dir

    def _get_schemas(self, exclude: list[str] = []) -> list[Path]:
        """Get all schema dirs except orca_events and exclude'd."""
        return [
            f for f in self.trace_dir.iterdir()
            if f.is_dir() and f.name != "orca_events" and f.name not in exclude
        ]

    # -------------------------------------------------------------------------
    # count_sync_maxdur: count collectives where max duration across ranks > threshold
    # -------------------------------------------------------------------------

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> int:
        """Count collectives where max duration across ranks exceeds threshold."""
        patt = str(self.trace_dir / "mpi_collectives" / "**/*.parquet")
        count = (
            pl.scan_parquet(patt)
            .group_by("swid")
            .agg((pl.col("dura_ns") / 1e6).max().alias("max_dura_ms"))
            .filter(pl.col("max_dura_ms") > thresh_ms)
            .select(pl.len())
            .collect()["len"]
            .item()
        )
        print(f"[Orca] max_dur>{thresh_ms}ms: {count}")
        return count

    # -------------------------------------------------------------------------
    # count_mpi_wait_dur: count MPI_Wait calls exceeding threshold
    # -------------------------------------------------------------------------

    def count_mpi_wait_dur(self, thresh_ms: float = 1.0) -> int:
        """Count MPI_Wait calls exceeding threshold."""
        patt = str(self.trace_dir / "mpi_messages" / "**/*.parquet")
        count = (
            pl.scan_parquet(patt)
            .filter(pl.col("probe_name") == "MPI_Wait")
            .filter((pl.col("dura_ns") / 1e6) > thresh_ms)
            .select(pl.len())
            .collect()["len"]
            .item()
        )
        print(f"[Orca] waits dur>{thresh_ms}ms: {count}")
        return count

    # -------------------------------------------------------------------------
    # count_window: count events within a time window from trace start
    # -------------------------------------------------------------------------

    def get_window_bounds(self, window_s: float = 1.0) -> Range:
        """Get the time range for the first window_s seconds of the trace."""
        patt = str(self.trace_dir / "mpi_collectives" / "**/*.parquet")
        ts_min = (
            pl.scan_parquet(patt)
            .select(pl.col("ts_ns").min())
            .collect()["ts_ns"]
            .item()
        )
        return (ts_min, ts_min + window_s * 1e9)

    def count_window(self, time_range: Range) -> int:
        """Count events within a time window across all schemas (except mpi_messages)."""
        schemas = self._get_schemas(exclude=["mpi_messages"])
        total = 0
        for schema_dir in schemas:
            patt = str(schema_dir / "**/*.parquet")
            cnt = (
                pl.scan_parquet(patt)
                .filter(pl.col("ts_ns").is_between(*time_range))
                .select(pl.len())
                .collect()["len"]
                .item()
            )
            total += cnt

        print(f"[Orca] events in window: {total}")
        return total

