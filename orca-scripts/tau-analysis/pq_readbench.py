#!/usr/bin/env python3
# Fastest end-to-end reads of a nested Parquet tree into a single pandas DataFrame.
# Targets: DuckDB, Polars, Pandas (pyarrow engine), PyArrow Dataset.

import os, sys, time, traceback
import pandas as pd

# ---- config ----
BASE = "/mnt/ltio/orcajobs/run7/pqroot/mpi_messages"
THREADS = os.cpu_count()

# Pin thread env so C++ libs don’t oversubscribe unpredictably
os.environ.setdefault("OMP_NUM_THREADS", str(THREADS))
os.environ.setdefault("MKL_NUM_THREADS", str(THREADS))
os.environ.setdefault("ARROW_NUM_THREADS", str(THREADS))
os.environ.setdefault("POLARS_MAX_THREADS", str(THREADS))

def timeit(label, fn):
    t0 = time.time()
    df = fn()
    t1 = time.time()
    n = len(df) if hasattr(df, "__len__") else -1
    print(f"{label:12s} {t1 - t0:7.2f}s  rows={n:,}")
    return df

# ---------- Pandas (PyArrow engine) ----------
# Fastest simple way in pandas: let PyArrow dataset recurse and parallelize.
def read_pandas():
    # recursive=True triggers Arrow’s dataset scanner; multithreaded in C++.
    return pd.read_parquet(f"{BASE}/**/*.parquet", engine="pyarrow", recursive=True)

# ---------- PyArrow Dataset ----------
# Read fully with Arrow, then convert once to pandas (keeps engine fast).
def read_pyarrow():
    import pyarrow.dataset as ds
    dset = ds.dataset(f"{BASE}", format="parquet")
    tbl = dset.to_table(use_threads=True)
    return tbl.to_pandas(types_mapper=pd.ArrowDtype)
    # Zero-copy to pandas where possible (pandas>=2 with ArrowDtype)
    # try:
    #     return tbl.to_pandas(types_mapper=pd.ArrowDtype)
    # except Exception:
    #     return tbl.to_pandas()
    #
# ---------- DuckDB ----------
# Fastest path: parallel parquet scan -> fetch Arrow -> convert once.
def read_duckdb():
    import duckdb
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={THREADS}")
    # No hive/filename parsing; that adds overhead we don’t need.
    tbl = con.execute(
        f"SELECT * FROM read_parquet('{BASE}/**/*.parquet')"
    ).fetch_arrow_table()
    try:
        return tbl.to_pandas(types_mapper=pd.ArrowDtype)
    except Exception:
        return tbl.to_pandas()

# ---------- Polars ----------
# Fastest path with many files: lazy scan + streaming collect (threaded).
def read_polars():
    import polars as pl
    lf = pl.scan_parquet(f"{BASE}/**/*.parquet")  # no hive parsing
    # streaming=True keeps memory stable and still parallel-decodes.
    return lf.collect(streaming=True).to_pandas()

def main():
    print(f"Dataset root: {os.path.abspath(BASE)}")
    print(f"Threads: {THREADS}\n")

    #timeit("pandas+pa", read_pandas)
    timeit("pyarrow   ", read_pyarrow)
    #timeit("duckdb    ", read_duckdb)
    #timeit("polars    ", read_polars)

if __name__ == "__main__":
    main()
