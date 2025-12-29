"""Find stragglers in ORCA traces."""

import polars as pl
from pathlib import Path
from orcareader import OrcaReader
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mtick

SUITES_ROOT = Path("/mnt/ltio/orcajobs/suites/20251227")

def read_syncmat(prof_root: Path) -> np.ndarray:
    reader = OrcaReader(prof_root)
    glob_patt = reader.get_glob_pattern("mpi_collectives")
    df = pl.scan_parquet(glob_patt, parallel="columns").select(
        ["swid", "rank", "dura_ns"]).collect()

    df_pivot = df.pivot(on="rank", index="swid",
                        values="dura_ns").fill_null(0).drop("swid")
    npmat = df_pivot.to_numpy()

    return npmat


def analyze_syncmat(npmat: np.ndarray) -> None:
    stragger_rankcnt = Counter()
    straggler_nodecnt = Counter()
    k = 32

    for ts in range(npmat.shape[0]):
        row = npmat[ts, :]
        ksmallest = np.argpartition(row, k)[:k]
        for rank in ksmallest:
            rint = int(rank)
            nint = rint // 16
            stragger_rankcnt[rint] += 1
            straggler_nodecnt[nint] += 1

    node_cntmax = 16 * npmat.shape[0]

    # print top 10 straggler nodes
    print("Top 10 straggler nodes:")
    for node, cnt in straggler_nodecnt.most_common(10):
        print(f"Node {node}: {cnt} occurrences ({cnt/node_cntmax*100:.1f}%)")



def run_analyze_orca_events(reader: OrcaReader) -> None:
    files = reader.query_orca_events_files()
    files
    df = (
        pl.read_parquet(files)
        .select(["probe_name", "rank", "val"])
        .with_columns(dura_ms=(pl.col("val") / 1_000_000).cast(pl.Int64))
    )

    ptile_vals = [0.5, 0.9, 0.99, 0.999, 1.0]
    ptile_names = [f"p{int(q*1000)/10:.1f}".replace(".", "_")
                   for q in ptile_vals]
    ptiles = list(zip(ptile_names, ptile_vals))

    df_ptiles = (
        df.group_by("probe_name")
        .agg([*[pl.col("dura_ms").quantile(q).alias(n) for (n, q) in ptiles]])
        .sort("p100_0", descending=True)
    )

    print("Percentiles by probe_name:")
    print(df_ptiles.to_pandas())

    # Count occurrences of poi with dura_ms > lim
    poi = "SerializeTsData::GetForwards"
    lim = 1

    df_stragglers = (
        df.filter(pl.col("probe_name") == poi)
        .filter(pl.col("dura_ms") > lim)
    )

    # sort by dura_ms
    dfs = df_stragglers.sort("dura_ms", descending=True).to_pandas()
    print(dfs.head(20))


def main() -> None:
    suite = "amr-agg4-r4096-n1000-run3"
    profile = "05_or_trace_mpisync"
    prof_root = SUITES_ROOT / suite / profile
    syncmat = read_syncmat(prof_root)
    analyze_syncmat(syncmat)


if __name__ == "__main__":
    main()