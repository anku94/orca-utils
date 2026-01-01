# first set pythonpath to /users/ankushj/repos/orca-workspace/orca-umb-install/lib/caliper
from pathlib import Path
import pandas as pd
from caliperreader import CaliperReader


class CaliperQuery:
    def __init__(self, trace_dir: Path, nranks: int):
        self.trace_dir = trace_dir
        self.nranks = nranks

        all_fnames = [f"mpi-{i}.cali" for i in range(nranks)]
        self.trace_files = [trace_dir / fname for fname in all_fnames]
        # assert that all files exist
        for fname in self.trace_files:
            assert fname.exists(), f"File {fname} does not exist"

    def _read_rank_df(self, rank: int) -> pd.DataFrame:
        cali_file = self.trace_files[rank]
        reader = CaliperReader()
        reader.read(str(cali_file))
        return pd.DataFrame(reader.records)

    def prep_count_sync_maxdur(self, rank: int = 0) -> pd.DataFrame:
        collectives = {
            "MPI_Allgather",
            "MPI_Allreduce",
            "MPI_Alltoall",
            "MPI_Barrier",
            "MPI_Bcast",
            "MPI_Reduce",
        }

        df = self._read_rank_df(rank)

        # Filter to MPI collectives with duration available.
        df = df[df["mpi.function"].isin(collectives)].copy()

        # Normalize types and names for downstream aggregation.
        df["dura_ns"] = pd.to_numeric(df["time.duration.ns"], errors="coerce")
        df["ts_offset_ns"] = pd.to_numeric(df.get("time.offset.ns"), errors="coerce")
        df["rank"] = pd.to_numeric(df.get("mpi.rank", rank), errors="coerce").fillna(
            rank
        )

        df = df[df["dura_ns"].notna()]

        if "ts_offset_ns" in df.columns:
            df = df.sort_values(["rank", "ts_offset_ns"], kind="stable")
        else:
            df = df.sort_values(["rank"], kind="stable")

        df["seq"] = df.groupby("rank").cumcount()
        df = df[["rank", "seq", "mpi.function", "dura_ns", "ts_offset_ns"]]
        df = df.rename(columns={"mpi.function": "func"})
        return df

    def count_sync_maxdur(self, thresh_ms: float = 10.0) -> int:
        """Count collectives where max duration across ranks exceeds threshold."""
        # Read and prep data for all ranks (serial)
        dfs = [self.prep_count_sync_maxdur(rank=r) for r in range(self.nranks)]
        combined = pd.concat(dfs, ignore_index=True)

        # Group by sequence number, find max duration across ranks
        per_seq_max = combined.groupby("seq")["dura_ns"].max()

        # Count how many exceed threshold
        thresh_ns = thresh_ms * 1e6
        count = (per_seq_max > thresh_ns).sum()

        print(
            f"[Caliper] nranks={self.nranks}, total_collectives={len(per_seq_max)}, "
            f"max_dur>{thresh_ms}ms: {count}"
        )
        return count

    def prep_count_mpi_wait_dur(self, rank: int = 0) -> pd.DataFrame:
        """Prep MPI_Wait calls for a single rank."""
        df = self._read_rank_df(rank)

        # Filter to MPI_Wait with duration available
        df = df[df["mpi.function"] == "MPI_Wait"].copy()

        # Normalize types
        df["dura_ns"] = pd.to_numeric(df["time.duration.ns"], errors="coerce")
        df["rank"] = rank

        df = df[df["dura_ns"].notna()]
        return df[["rank", "dura_ns"]]

    def count_mpi_wait_dur(self, thresh_ms: float = 1.0) -> int:
        """Count MPI_Wait calls exceeding threshold across all ranks."""
        dfs = [self.prep_count_mpi_wait_dur(rank=r) for r in range(self.nranks)]
        combined = pd.concat(dfs, ignore_index=True)

        thresh_ns = thresh_ms * 1e6
        count = (combined["dura_ns"] > thresh_ns).sum()

        print(
            f"[Caliper] nranks={self.nranks}, total_waits={len(combined)}, "
            f"dur>{thresh_ms}ms: {count}"
        )
        return count

    def prep_count_window(self, rank: int = 0) -> pd.DataFrame:
        """Prep all events with timestamps for a single rank."""
        df = self._read_rank_df(rank)

        # Keep only rows with timestamp
        df["ts_offset_ns"] = pd.to_numeric(df.get("time.offset.ns"), errors="coerce")
        df = df[df["ts_offset_ns"].notna()].copy()
        df["rank"] = rank

        return df[["rank", "ts_offset_ns"]]

    def count_window(self, window_s: float = 1.0) -> int:
        """Count events within a time window from trace start."""
        dfs = [self.prep_count_window(rank=r) for r in range(self.nranks)]
        combined = pd.concat(dfs, ignore_index=True)

        # Find min timestamp and define window
        ts_min = combined["ts_offset_ns"].min()
        window_ns = window_s * 1e9
        ts_max = ts_min + window_ns

        # Count events in window
        count = ((combined["ts_offset_ns"] >= ts_min) & 
                 (combined["ts_offset_ns"] < ts_max)).sum()

        print(
            f"[Caliper] nranks={self.nranks}, total_events={len(combined)}, "
            f"in_first_{window_s}s: {count}"
        )
        return count


def main() -> None:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20251230")
    trace_dir = suite_dir / "amr-agg1-r512-n20-run1/18_caliper_tracetgt/trace"
    trace_file = trace_dir / "mpi-0.cali"

    # reader = CaliperReader()
    # reader.read(str(trace_file))
    # reader.attributes()
    # print(reader.globals)

    # df = pd.DataFrame(reader.records)
    # # column 'event.
    # print(df)

    cq = CaliperQuery(trace_dir, 2)
    # cq.count_sync_maxdur(thresh_ms=10.0)
    # cq.count_mpi_wait_dur(thresh_ms=1.0)
    cq.count_window(window_s=1.0)


if __name__ == "__main__":
    main()
