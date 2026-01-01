# Driver script for testing tracequery.CaliperQuery
# Requires PYTHONPATH: /users/ankushj/repos/orca-workspace/orca-umb-install/lib/caliper

from pathlib import Path

# from tracequery import CaliperQuery, OrcaQuery
import tracequery as tq


def main_caliper() -> None:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20251230")
    trace_dir = suite_dir / "amr-agg1-r512-n20-run1/18_caliper_tracetgt/trace"

    # Test all three queries, serial then parallel
    for nworkers in [1, 2]:
        print(f"\n=== nworkers={nworkers} ===")
        cq = tq.CaliperQuery(trace_dir, nranks=2, nworkers=nworkers)
        cq.count_sync_maxdur(thresh_ms=10.0)
        cq.count_mpi_wait_dur(thresh_ms=1.0)
        cq.count_window(window_s=1.0)


def main_orca() -> None:
    suite_dir = Path("/mnt/ltio/orcajobs/suites/20251229")
    trace_dir = suite_dir / "amr-agg1-r512-n20-run1/07_or_tracetgt/parquet"
    oq = tq.OrcaQuery(trace_dir)
    oq.count_sync_maxdur(thresh_ms=10.0)
    oq.count_mpi_wait_dur(thresh_ms=1.0)
    time_range = oq.get_window_bounds(window_s=1.0)
    oq.count_window(time_range)


def main():
    # main_caliper()
    main_orca()


if __name__ == "__main__":
    main()
