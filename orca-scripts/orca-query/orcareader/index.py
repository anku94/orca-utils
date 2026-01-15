"""Low-level index for ORCA parquet file paths."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import polars as pl

from .interval import Interval, IntervalIndex, Range

logger = logging.getLogger(__name__)


class OrcaIndex:
    """Index for timestep/swid range queries returning file paths.

    Indices built from mpi_collectives (canonical):
    - Timestep intervals from directory names
    - SWID intervals from polars parallel scan

    All tables share the same timestep structure (flushed together).
    """

    def __init__(self, root: Path):
        self.root = Path(root) / "parquet"
        self._ts_intervals: list[Interval] = []  # Canonical timestep intervals
        self._swid_index = IntervalIndex()  # swid -> mpi_collectives files
        self._tables: list[str] = []
        logger.info(f"Initializing OrcaIndex for {root}")
        self._build_indices()
        logger.info(
            f"Index built: {len(self._tables)} tables, {len(self._ts_intervals)} timestep intervals"
        )

    @property
    def tables(self) -> list[str]:
        """Return list of discovered tables."""
        return sorted(self._tables)

    def _build_indices(self) -> None:
        """Build timestep/swid indices from mpi_collectives."""
        if not self.root.exists():
            logger.warning(f"Trace root does not exist: {self.root}")
            return

        # Discover all tables
        self._tables = [d.name for d in self.root.iterdir() if d.is_dir()]
        logger.debug(f"Discovered tables: {self._tables}")

        # Build timestep intervals from mpi_collectives
        mpi_coll_root = self.root / "mpi_collectives"
        if not mpi_coll_root.exists():
            logger.warning("mpi_collectives table not found")
            return

        logger.debug("Building timestep intervals from mpi_collectives")
        ts_dirs = sorted(mpi_coll_root.iterdir())
        for ts_dir in ts_dirs:
            if not ts_dir.is_dir():
                continue

            m = re.match(r"ts=(-?\d+)_(-?\d+)", ts_dir.name)
            if not m:
                continue

            ts_interval = Interval(int(m.group(1)), int(m.group(2)))
            self._ts_intervals.append(ts_interval)

        logger.debug(f"Found {len(self._ts_intervals)} timestep intervals")

        # Build swid index from mpi_collectives
        self._build_swid_index()

    def _build_swid_index(self) -> None:
        """Build swid index using one parallel polars query on mpi_collectives."""
        mpi_coll_root = self.root / "mpi_collectives"
        glob_pattern = str(mpi_coll_root / "**" / "*.parquet")

        logger.info("Building SWID index from mpi_collectives (parallel scan)")
        try:
            df = (
                pl.read_parquet(
                    glob_pattern,
                    parallel="columns",
                    hive_partitioning=False,
                    use_statistics=True,
                    rechunk=False,
                    include_file_paths="path",
                )
                .group_by("path")
                .agg(
                    [
                        pl.col("swid").min().alias("swid_min"),
                        pl.col("swid").max().alias("swid_max"),
                    ]
                )
            )

            num_files = len(df)
            logger.debug(f"Polars scan completed: {num_files} files")

            for row in df.iter_rows(named=True):
                fpath = Path(row["path"])
                swid_min = row["swid_min"]
                swid_max = row["swid_max"]

                if swid_min is not None and swid_max is not None:
                    self._swid_index.add(Interval(swid_min, swid_max + 1), fpath)

            self._swid_index.finalize()
            logger.info(f"SWID index built: {len(self._swid_index._entries)} entries")

        except Exception as e:
            logger.error(f"Failed to build SWID index: {e}")

    def query_ts(self, table: str, ts_range: Range) -> list[Path]:
        """Return file paths from table overlapping timestep range."""
        ts_start, ts_end = ts_range
        query = Interval(ts_start, ts_end)
        logger.debug(f"query_ts: table={table}, range={ts_range}")
        result = []

        table_root = self.root / table
        if not table_root.exists():
            logger.warning(f"Table {table} not found")
            return []

        for ts_interval in self._ts_intervals:
            if not ts_interval.overlaps(query):
                continue

            # Construct expected directory path
            ts_dir = table_root / f"ts={ts_interval.start}_{ts_interval.end}"
            if ts_dir.exists():
                result.extend(ts_dir.glob("*.parquet"))

        logger.debug(f"query_ts: found {len(result)} files")
        return sorted(result)

    def query_swid(
        self, swid_range: Range, table: str = "mpi_collectives"
    ) -> list[Path]:
        """Return file paths from table overlapping swid range.

        SWID index built from mpi_collectives. For other tables, maps swid to
        timesteps (assumes synchronized flushing).
        """
        swid_start, swid_end = swid_range
        query = Interval(swid_start, swid_end)
        logger.debug(f"query_swid: table={table}, range={swid_range}")

        if table == "mpi_collectives":
            result = sorted(self._swid_index.query(query))
            logger.debug(f"query_swid: found {len(result)} files")
            return result

        # For other tables: map swid -> mpi_collectives files -> timestep dirs -> other table files
        logger.debug(f"query_swid: mapping via mpi_collectives for table {table}")
        mpi_files = self._swid_index.query(query)
        if not mpi_files:
            logger.debug("query_swid: no matching mpi_collectives files")
            return []

        # Extract timestep directories from mpi_collectives file paths
        ts_dirs = {f.parent.name for f in mpi_files}
        logger.debug(f"query_swid: mapped to {len(ts_dirs)} timestep directories")

        # Find corresponding files in requested table
        result = []
        table_root = self.root / table
        if table_root.exists():
            for ts_dir_name in ts_dirs:
                ts_dir = table_root / ts_dir_name
                if ts_dir.exists():
                    result.extend(ts_dir.glob("*.parquet"))

        logger.debug(f"query_swid: found {len(result)} files")
        return sorted(result)
