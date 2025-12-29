"""High-level reader for ORCA parquet traces returning DataFrames."""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from .index import OrcaIndex
from .interval import Range

logger = logging.getLogger(__name__)


def _apply_trace_transforms(df: pl.DataFrame) -> pl.DataFrame:
    """Apply transforms for trace tables (mpi_collectives, kokkos_events, mpi_messages)."""
    if df.is_empty():
        return df
    result = df
    if "dura_ns" in result.columns:
        result = result.with_columns(
            (pl.col("dura_ns") / 1_000_000).cast(pl.Int64).alias("dura_ms")
        ).drop("dura_ns")
    if "probe_hash" in result.columns:
        result = result.drop("probe_hash")
    return result


class OrcaReader:
    """High-level interface for querying ORCA traces, returns DataFrames.

    Wraps OrcaIndex to provide DataFrame-level queries using polars.
    """

    def __init__(self, root: Path):
        self._index = OrcaIndex(root)

    @property
    def tables(self) -> list[str]:
        """Return list of discovered tables."""
        return self._index.tables

    def read_ts(self, table: str, ts_range: Range) -> pl.DataFrame:
        """Read table data for timestep range {ts_range}."""
        logger.info(f"read_ts: table={table}, range={ts_range}")
        files = self._index.query_ts(table, ts_range)

        if not files:
            logger.warning(f"read_ts: no files found")
            return pl.DataFrame()

        logger.debug(f"read_ts: reading {len(files)} files")
        df = pl.read_parquet(files)
        return _apply_trace_transforms(df)

    def read_swid(
        self, swid_range: Range, table: str = "mpi_collectives"
    ) -> pl.DataFrame:
        """Read table data for swid range {swid_range}."""
        logger.info(f"read_swid: table={table}, range={swid_range}")
        files = self._index.query_swid(swid_range, table)

        if not files:
            logger.warning(f"read_swid: no files found")
            return pl.DataFrame()

        logger.debug(f"read_swid: reading {len(files)} files")
        df = pl.read_parquet(files)
        return _apply_trace_transforms(df)

    def query_ts_files(self, table: str, ts_range: Range) -> list[Path]:
        """Low-level access: return file paths for timestep range (no reading)."""
        return self._index.query_ts(table, ts_range)

    def query_swid_files(
        self, swid_range: Range, table: str = "mpi_collectives"
    ) -> list[Path]:
        """Low-level access: return file paths for swid range (no reading)."""
        return self._index.query_swid(swid_range, table)

    def query_orca_events_files(self, ranks: Range | None = None) -> list[Path]:
        """Low-level access: return file paths for orca_events (no reading)."""
        orca_events_dir = self._index.root / "orca_events"

        if ranks:
            rbeg, rend = ranks
            return [orca_events_dir / f"R{r}.parquet" for r in range(rbeg, rend)]
        else:
            return list(orca_events_dir.glob("R*.parquet"))

    def read_orca_events(self, ranks: Range | None = None) -> pl.DataFrame:
        """Read orca_events table for specified rank range.

        Args:
            ranks: Range of rank numbers to read. If None, reads all ranks.
        """
        files = self.query_orca_events_files(ranks)
        logger.info(f"read_orca_events: reading {len(files)} files")
        df = pl.read_parquet(files)
        return df

    def get_glob_pattern(self, table: str) -> str:
        """Get glob pattern for table."""
        if table == "orca_events":
            return self._index.root / "orca_events" / "R*.parquet"
        else:
            table_dir = self._index.root / table
            if not table_dir.exists():
                raise FileNotFoundError(f"Table directory not found: {table_dir}")
            return self._index.root / table / "**"/ "*.parquet"
