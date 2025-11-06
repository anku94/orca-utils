import pandas as pd
import glob
import re
import os
import duckdb
import polars as pl


SUITE_ROOT = "/mnt/ltio/orcajobs/suites"

def get_suitedir(suite_name: str) -> str:
    "Get suite dir from suite name"

    suite_dir = f"{SUITE_ROOT}/{suite_name}"
    if not os.path.exists(suite_dir):
        raise FileNotFoundError(f"Suite directory {suite_dir} does not exist")
    return suite_dir


def get_profile_dir(suite_name: str, profile: str) -> str:
    "Get profile dir from suite name and profile name"

    suite_dir = get_suitedir(suite_name)
    profile_dir = f"{suite_dir}/{profile}"
    if not os.path.exists(profile_dir):
        raise FileNotFoundError(
            f"Profile directory {profile_dir} does not exist")
    return profile_dir

def get_runtime(profile_dir: str) -> float:
    print(f"Getting runtime for profile {profile_dir}")
    mpi_log = f"{profile_dir}/mpi.log"

    with open(mpi_log, "r") as f:
        lines = f.readlines()
        lines = [l.strip() for l in lines if "walltime used" in l]

    print(lines)
    if len(lines) == 0:
        return 0

    mobj = re.match(r"walltime used = (\d+\.\d+)$", lines[0])
    if mobj is None:
        return 0

    return float(mobj.group(1))


def get_suite_profiles(suite_dir: str) -> list[str]:
    """Get the profiles in the suite directory, sorted by PID"""
    subdirs = glob.glob(f"{suite_dir}/*")
    subdirs = [d for d in subdirs if os.path.isdir(d)]

    def get_pid(x: str) -> int:
        xbase = os.path.basename(x)
        mobj = re.match(r"(\d+)_", xbase)
        if mobj is None:
            return 0
        return int(mobj.group(1))
    subdirs = sorted(subdirs, key=get_pid)
    return subdirs


def get_suite_amr_runtimes(suite_dir: str) -> pd.DataFrame:
    print(f"Getting AMR runtimes for suite {suite_dir}")
    profiles = get_suite_profiles(suite_dir)
    profile_names = [os.path.basename(p) for p in profiles]

    runtimes = [get_runtime(p) for p in profiles]
    df = pd.DataFrame({"profile": profile_names, "time_secs": runtimes})
    return df


def compute_probe_freqs(profile_dir: str, tracer: str):
    trace_dir = f"{profile_dir}/parquet/{tracer}"
    q = (
    pl.scan_parquet(trace_dir, rechunk=False, cache=False)
      .group_by(["rank", "probe_name"])
      .agg(pl.len())
      .sort(["rank", "probe_name"])
)

    tdf_counts = q.collect(engine="streaming")
    print(tdf_counts)


def read_duckdb(duckdb_path: str) -> pd.DataFrame:
    print(f"Reading DuckDB for suite {duckdb_path}")
    db = duckdb.connect(duckdb_path)

    query = "SHOW TABLES"
    df = db.execute(query).fetch_df()
    print(df)

    query = "SELECT * from msg_all"
    df = db.execute(query).fetch_df()
    print(df)

    return df


if __name__ == "__main__":
    # suite_root = "/mnt/ltio/orcajobs/suites"
    # suite_name = "20251103_amr-r128-psm141-nohugepages-n20"
    # suite_dir = f"{suite_root}/{suite_name}"
    # # get_suite_amr_runtimes(suite_dir)
    # duckdb_path = "/mnt/ltio/orcajobs/run1/duck.db"
    # read_duckdb(duckdb_path)
    suite_name = "20251106_amr-agg4-r512-n200-psmerrchk141"
    profile_dir = get_profile_dir(suite_name, "7_trace_all")
    compute_probe_freqs(profile_dir, "mpi_messages")