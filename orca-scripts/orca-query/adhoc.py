import polars as pl

PQDIR = "/mnt/ltio/orcajobs/suites/20260108/amr-agg4-r4096-n2000-run1/20_or_disable_paused/parquet"

stream = "kokkos_slow"
glob_pattern = f"{PQDIR}/{stream}/*/*.parquet"

dura_ms_expr = (pl.col("dura_ns") / 1e6).alias("dura_ms")
df = (
    pl.scan_parquet(glob_pattern, parallel="columns")
    .with_columns([dura_ms_expr])
    .filter(pl.col("dura_ms") > 50)
    .collect()
)
print(df)

df_probes = df.select("probe_name").group_by(["probe_name"]).count()
print(df_probes.to_pandas())


stream = "mpi_wait_slow"
glob_pattern = f"{PQDIR}/{stream}/*/*.parquet"

dura_ms_expr = (pl.col("dura_ns") / 1e6).alias("dura_ms")
df = (
    pl.scan_parquet(glob_pattern, parallel="columns")
    .with_columns([dura_ms_expr])
    .filter(pl.col("dura_ms") > 50)
    .collect()
)
print(df)