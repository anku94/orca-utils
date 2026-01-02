# Requires PYTHONPATH to include caliper reader:
# /users/ankushj/repos/orca-workspace/orca-umb-install/lib/caliper

from multiprocessing import Pool
from pathlib import Path

import pandas as pd
from caliperreader import CaliperReader

from .common import Range


# -----------------------------------------------------------------------------
# Module-level worker functions for multiprocessing (must be picklable)
# -----------------------------------------------------------------------------


def _read_cali_df(trace_file: Path) -> pd.DataFrame:
    """Read a .cali file into a DataFrame."""
    reader = CaliperReader()
    reader.read(str(trace_file))
    return pd.DataFrame(reader.records)


COLLECTIVES = {
    "MPI_Allgather",
    "MPI_Allreduce",
    "MPI_Alltoall",
    "MPI_Barrier",
    "MPI_Bcast",
    "MPI_Reduce",
}


def _prep_sync_maxdur_worker(trace_file: Path) -> pd.DataFrame:
    """Worker for count_sync_maxdur."""
    df = _read_cali_df(trace_file)
    df = df[df["mpi.function"].isin(COLLECTIVES)].copy()
    df["ts"] = df["time.offset.ns"].astype(float)
    df["dura_ns"] = df["time.duration.ns"].astype(float)
    df = df.sort_values("ts")
    df["seq"] = range(len(df))
    return df[["seq", "dura_ns"]]


def _prep_mpi_wait_worker(trace_file: Path) -> pd.DataFrame:
    """Worker for count_mpi_wait_dur."""
    df = _read_cali_df(trace_file)
    df = df[df["mpi.function"] == "MPI_Wait"]
    return df[["time.duration.ns"]].astype(float)


def _count_window_worker(args: tuple[Path, float]) -> int:
    """Count events in first window_ns nanoseconds."""
    trace_file, window_ns = args
    df = _read_cali_df(trace_file)
    ts = df["time.offset.ns"].astype(float)
    return int((ts < window_ns).sum())


class CaliperQuery:
    def __init__(self, trace_dir: Path, nranks: int, nworkers: int = 1):
        self.trace_dir = trace_dir
        self.nranks = nranks
        self.nworkers = nworkers

        all_fnames = [f"mpi-{i}.cali" for i in range(nranks)]
        self.trace_files = [trace_dir / fname for fname in all_fnames]
        for fname in self.trace_files:
            assert fname.exists(), f"File {fname} does not exist"

    # -------------------------------------------------------------------------
    # count_sync_maxdur: count collectives where max duration across ranks > threshold
    # -------------------------------------------------------------------------

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> int:
        """Count collectives where max duration across ranks exceeds threshold."""
        if self.nworkers > 1:
            with Pool(self.nworkers) as pool:
                dfs = pool.map(_prep_sync_maxdur_worker, self.trace_files)
        else:
            dfs = [_prep_sync_maxdur_worker(f) for f in self.trace_files]

        combined = pd.concat(dfs, ignore_index=True)
        per_seq_max = combined.groupby("seq")["dura_ns"].max()
        thresh_ns = thresh_ms * 1e6
        count = (per_seq_max > thresh_ns).sum()

        print(
            f"[Caliper] nranks={self.nranks}, collectives={len(per_seq_max)}, "
            f"max_dur>{thresh_ms}ms: {count}"
        )
        return count

    # -------------------------------------------------------------------------
    # count_mpi_wait_dur: count MPI_Wait calls exceeding threshold
    # -------------------------------------------------------------------------

    def count_mpi_wait_dur(self, thresh_ms: float = 1.0) -> int:
        """Count MPI_Wait calls exceeding threshold across all ranks."""
        if self.nworkers > 1:
            with Pool(self.nworkers) as pool:
                dfs = pool.map(_prep_mpi_wait_worker, self.trace_files)
        else:
            dfs = [_prep_mpi_wait_worker(f) for f in self.trace_files]

        combined = pd.concat(dfs, ignore_index=True)
        thresh_ns = thresh_ms * 1e6
        count = (combined["time.duration.ns"] > thresh_ns).sum()

        print(
            f"[Caliper] nranks={self.nranks}, waits={len(combined)}, "
            f"dur>{thresh_ms}ms: {count}"
        )
        return count

    # -------------------------------------------------------------------------
    # count_window: count events within a time window from trace start
    # -------------------------------------------------------------------------

    def get_window_bounds(self, window_s: float = 1.0) -> Range:
        """Get the time range for the first window_s seconds of the trace.

        Caliper's time.offset.ns is already relative to global start, so bounds are trivial.
        """
        return (0.0, window_s * 1e9)

    def count_window(self, time_range: Range) -> int:
        """Count events within a time window."""
        window_ns = time_range[1]  # time_range[0] is 0 for Caliper
        args = [(f, window_ns) for f in self.trace_files]
        if self.nworkers > 1:
            with Pool(self.nworkers) as pool:
                counts = pool.map(_count_window_worker, args)
        else:
            counts = [_count_window_worker(a) for a in args]

        total = sum(counts)
        print(f"[Caliper] events in window: {total}")
        return total
