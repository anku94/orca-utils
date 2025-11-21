"""Find stragglers in ORCA traces."""

from pathlib import Path

import polars as pl

from orcareader import OrcaReader

SUITES_ROOT = Path("/mnt/ltio/orcajobs/suites")


def run_analyze_orca_events(reader: OrcaReader) -> None:
    files = reader.query_orca_events_files()
    df = (
        pl.read_parquet(files)
        .select(["probe_name", "val"])
        .with_columns(dura_ms=(pl.col("val") / 1_000_000).cast(pl.Int64))
    )

    ptile_vals = [0.5, 0.9, 0.99, 0.999, 1.0]
    ptile_names = [f"p{int(q*1000)/10:.1f}".replace(".", "_") for q in ptile_vals]
    ptiles = list(zip(ptile_names, ptile_vals))


    df_ptiles = (
        df.group_by("probe_name")
        .agg([*[pl.col("dura_ms").quantile(q).alias(n) for (n, q) in ptiles]])
        .sort("p100_0", descending=True)
    )

    print("Percentiles by probe_name:")
    print(df_ptiles)

    # Count occurrences of poi with dura_ms > lim
    poi = "SerializeTsData::GetForwards"
    lim = 1

    df_stragglers = (
        df.filter(pl.col("probe_name") == poi)
        .filter(pl.col("dura_ms") > lim)
        .group_by("probe_name")
        .agg(count_stragglers=pl.len())
    )

    print(df_stragglers)


def main() -> None:
    suite = "20251120_amr-agg4-r4096-n2000-psmerrchk141"
    profile = "07_trace_tgt"
    trace_root = SUITES_ROOT / suite / profile
    reader = OrcaReader(trace_root)
    run_analyze_orca_events(reader)


if __name__ == "__main__":
    main()
