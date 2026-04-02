from pathlib import Path

import dask
import dftracer.analyzer as analyzer

from .common import Range

COLLECTIVES = {
    "MPI_Allgather",
    "MPI_Allreduce",
    "MPI_Alltoall",
    "MPI_Barrier",
    "MPI_Bcast",
    "MPI_Reduce",
}


class DfTracerQuery:

    def __init__(self, trace_dir: Path, tmp_dir: Path):
        """trace_dir should contain the dftracer trace files.
           tmp_dir is used for shuffler spills and all
        """
        self.trace_dir = trace_dir
        self._tmp_dir = tmp_dir
        self._traces = None
        self._dfa = None

        assert self._tmp_dir.exists()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Shutdown Dask cluster."""
        if self._dfa is not None:
            self._dfa.shutdown()
            self._dfa = None
            self._traces = None

    def _load_traces(self):
        """Lazy load traces."""
        if self._traces is None:
            self._dfa = analyzer.init_with_hydra(hydra_overrides=[
                "analyzer=dftracer",
                "cluster=local",
                f"trace_path={self.trace_dir}",
                f"cluster.local_directory={self._tmp_dir}",
            ])
            self._traces = self._dfa.analyzer.read_trace(str(self.trace_dir),
                                                         extra_columns=None,
                                                         extra_columns_fn=None)
        return self._traces

    # -------------------------------------------------------------------------
    # count_sync_maxdur: count collectives where max duration across ranks > threshold
    # -------------------------------------------------------------------------

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> int:
        """Count collectives where max duration across ranks exceeds threshold."""
        traces = self._load_traces()

        mpi_filtered = traces[(traces.cat == "mpi")
                              & (traces.func_name.isin(COLLECTIVES))]
        mpi_pd = mpi_filtered[["pid", "time_start", "time"]].compute()

        if mpi_pd.empty:
            return 0

        mpi_pd = mpi_pd.sort_values(["pid", "time_start"])
        mpi_pd["seq"] = mpi_pd.groupby("pid").cumcount()
        per_seq_max = mpi_pd.groupby("seq")["time"].max()
        # time is in seconds, thresh_ms in ms
        count = int(((per_seq_max * 1e3) > thresh_ms).sum())

        print(f"[DfTracer] max_dur>{thresh_ms}ms: {count}")
        return count

    # -------------------------------------------------------------------------
    # count_mpi_wait_dur: count MPI_Wait calls exceeding threshold
    # -------------------------------------------------------------------------

    def count_mpi_wait_dur(self, thresh_ms: float = 1.0) -> int:
        """Count MPI_Wait calls exceeding threshold."""
        traces = self._load_traces()

        mpi_wait = traces[(traces.cat == "mpi")
                          & (traces.func_name == "MPI_Wait")]
        # time is in seconds
        count = ((mpi_wait.time * 1e3) >= thresh_ms).sum().compute()

        print(f"[DfTracer] waits dur>{thresh_ms}ms: {count}")
        return int(count)

    # -------------------------------------------------------------------------
    # count_window: count events within a time window from trace start
    # -------------------------------------------------------------------------

    def get_window_bounds(self, window_s: float = 1.0) -> Range:
        """Get the time range for the first window_s seconds of the trace."""
        traces = self._load_traces()
        # time_start is in microseconds
        win_start = traces.time_start.min().compute()
        win_end = win_start + window_s * 1e6
        return (win_start, win_end)

    def count_window(self, time_range: Range) -> int:
        """Count events within a time window."""
        traces = self._load_traces()
        count = traces.time_start.between(*time_range).count().compute()

        print(f"[DfTracer] events in window: {count}")
        return int(count)
