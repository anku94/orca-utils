import polars as pl
import pandas as pd
from pathlib import Path


def count_events_tau(suite_root: Path):
    tracedir_tau = suite_root / "10_tau_tracetgt" / "parquet"

    glob_patt_tau = str(tracedir_tau / "rank_0.parquet")
    countsdf_tau = (
        pl.scan_parquet(glob_patt_tau, parallel="columns")
        .group_by("name")
        .len()
        .sort("len", descending=True)
        .with_columns(pl.col("len").cum_sum().alias("cumsum"))
        .collect()
    )
    tau_totevnts = countsdf_tau["cumsum"].last()

    print(f"TAU total events: {tau_totevnts}")
    print("TAU event counts:\n====")
    print(countsdf_tau.to_pandas().head(10))


def count_events_orca(suite_root: Path):
    tracedir_orca = suite_root / "07_trace_tgt" / "parquet"
    glob_patt_orca = str(tracedir_orca / "**/*.parquet")
    # polars lazy query
    countsdf_orca_inter = (
        pl.scan_parquet(glob_patt_orca, extra_columns="ignore",
                        parallel="columns")
        .filter(pl.col("rank") == 0)
        .group_by("probe_name", "timestep")
        .len()
        .sort("len", descending=True)
        .collect()
    )

    countsdf_orca = countsdf_orca_inter.group_by("probe_name").agg(
        pl.col("len").sum()).sort("len", descending=True).with_columns(
            pl.col("len").cum_sum().alias("cumsum"))

    orca_totevnts = countsdf_orca["cumsum"].last()
    print(f"\nORCA total events: {orca_totevnts}")
    print("ORCA event counts:\n====")
    print(countsdf_orca.to_pandas().head(4))


def main():
    data_root = Path("/mnt/ltio/orcajobs/suites")
    suite_root = data_root / "20251203_amr-agg1-r512-n20-psmerrchk141"
    count_events_tau(suite_root)
    count_events_orca(suite_root)

if __name__ == "__main__":
    main()
