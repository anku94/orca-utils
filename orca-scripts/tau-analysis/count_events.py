import polars as pl
from pathlib import Path


def count():
    pass


def main():
    data_root = Path("/mnt/ltio/orcajobs/suites")
    suite_root = data_root / "20251203_amr-agg1-r512-n20-psmerrchk141"
    trace_dir = suite_root / "10_tau_tracetgt" / "parquet"

    glob_patt = str(trace_dir / "rank_0.parquet")
    counts = (
        pl.read_parquet(glob_patt, parallel="columns")
        .group_by("name")
        .count()
        .sort("count", descending=True)
    )
    print(counts.to_pandas().head(20))

    trace_dir = suite_root / "07_trace_tgt" / "parquet"
    # polars lazy query
    counts = (
        pl.scan_parquet(trace_dir, extra_columns="ignore")
        .filter(pl.col("rank") == 0)
        .group_by("probe_name", "timestep")
        .count()
        .sort("count", descending=True)
        .collect()
    )

    print(
        counts.group_by("probe_name")
        .agg(pl.col("count").sum())
        .sort("count", descending=True)
        .to_pandas()
        .head(20)
    )

    counts = counts.to_pandas()
    counts = counts[counts["probe_name"] == "region::WeightedSumData"]
    print(counts.sort_values("timestep").head(20))


if __name__ == "__main__":
    main()
