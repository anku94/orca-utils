import pandas as pd
import glob

PQ_ROOT = "/mnt/ltio/orcajobs/run5/pqroot"

def get_tracedirs(pq_root: str) -> list[str]:
    tracedirs = sorted(glob.glob(f"{pq_root}/*"))
    return tracedirs

def get_all_pqfiles(pq_root: str, stream: str):
    pqfiles = glob.glob(f"{pq_root}/{stream}/**/*.parquet", recursive=True)
    return pqfiles

def run():
    all_tracedirs = get_tracedirs(PQ_ROOT)
    pq_files = get_all_pqfiles(PQ_ROOT, "kokkos_events")

    f0 = pq_files[0]
    df = pd.read_parquet(f0)
    # groupby probe_name, show counts
    df["probe_name"].value_counts()

    pq_root = PQ_ROOT
    stream = "kokkos_events"
    pass

if __name__ == "__main__":
    run()
