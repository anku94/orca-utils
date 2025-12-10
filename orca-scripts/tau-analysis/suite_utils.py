from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import glob
import re
import os
import duckdb
import polars as pl
from datetime import datetime
import yaml
from concurrent.futures import ThreadPoolExecutor

SUITE_ROOT = "/mnt/ltio/orcajobs/suites"

import time
from functools import wraps


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    path: Path


@dataclass(frozen=True, slots=True)
class Suite:
    name: str
    suitedir: Path
    profiles: list[Profile]

    def __repr__(self) -> str:
        s = f"Suite(name={self.name}, {len(self.profiles)} profiles):\n"
        for p in sorted(self.profiles, key=lambda x: x.name):
            s += f"  {p.name:20s}: {p.path}\n"
        return s


SuiteMap = dict[str, Suite]  # suite name -> suite


def log_time(func):
    "Log the time taken by a decorated function"

    @wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        t1 = time.perf_counter()
        print(f"{func.__name__} took {(t1 - t0)*1000:.2f} ms")
        return result

    return wrapper


def pretty_size(size: float) -> str:
    "Pretty print size in GB"

    all_units = ["B", "KB", "MB", "GB", "TB"]
    for unit in all_units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} TB"


def get_dir_size(dir_path: Path) -> int:
    "Get `du -sh` equivalent of directory"
    total_size = 0
    for fpath in dir_path.rglob("*"):
        if fpath.is_file():
            total_size += fpath.stat().st_size
    return total_size


def get_file_size(fpath: Path) -> int:
    "Get the size of a file"
    return fpath.stat().st_size


def get_dir_size_cached(dir_path: Path, cache: bool = True) -> pd.DataFrame:
    df_cache = f"{dir_path}/filesizes_cached.csv"
    if cache and os.path.exists(df_cache):
        return pd.read_csv(df_cache)

    # get size as a dataframe fpath, fsize
    all_fpaths = list(dir_path.rglob("*"))
    # all_fsizes = [fpath.stat().st_size for fpath in all_fpaths]
    # multiprocessing does not behave well with Panel
    with ThreadPoolExecutor(max_workers=32) as ex:
        all_fsizes = list(ex.map(get_file_size, all_fpaths))

    df = pd.DataFrame({"fpath": all_fpaths, "fsize": all_fsizes})
    df.to_csv(df_cache, index=False)

    return df


def get_tracedir(profile_dir: Path) -> Path:
    "Returns the dir containing trace data"

    # check which of parquet, tau-trace, or trace exists
    if os.path.exists(f"{profile_dir}/parquet"):
        return Path(f"{profile_dir}/parquet")
    elif os.path.exists(f"{profile_dir}/tau-trace"):
        return Path(f"{profile_dir}/tau-trace")
    elif os.path.exists(f"{profile_dir}/trace"):
        return Path(f"{profile_dir}/trace")
    else:
        raise FileNotFoundError(f"No trace directory found in {profile_dir}")


def get_suite_tracesizes(suite: Suite) -> pd.DataFrame:
    "Get the size of the trace directories for all profiles in a suite"
    tracedirs = [get_tracedir(p.path) for p in suite.profiles]
    trace_dfs = [get_dir_size_cached(td) for td in tracedirs]
    print(trace_dfs)
    tracesizes = [df["fsize"].sum() for df in trace_dfs]
    profile_names = [p.name for p in suite.profiles]

    df = pd.DataFrame({"profile": profile_names, "trace_size": tracesizes})
    return df


def get_profile_amr_runtime(profile_dir: Path) -> float:
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


def get_suite_amr_runtimes(suite: Suite) -> pd.DataFrame:
    print(f"Getting AMR runtimes for suite {suite.name}")

    # Returns a dataframe like this:
    #               profile  time_secs
    # 0     10_dftracer     2.5723
    # 1       11_scorep     2.6378
    # 2  08_tau_default     3.1165

    runtimes = [get_profile_amr_runtime(p.path) for p in suite.profiles]
    profile_names = [p.name for p in suite.profiles]
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


def read_suites(suites_yaml: str) -> SuiteMap:
    with open(suites_yaml, "r") as f:
        yaml_data = yaml.load(f, Loader=yaml.FullLoader)

    print(f"YAML data: {yaml_data}")

    rootdir = Path(yaml_data["root"])
    suites: SuiteMap = {}
    for yd in yaml_data["suites"]:
        suitedir = rootdir / yd["suitedir"]
        # enumerate all directories in suitedir
        if not suitedir.exists():
            print(f"Suite {yd['name']} directory {suitedir} does not exist")
            continue

        prof_dirs = [d for d in suitedir.iterdir() if d.is_dir()]
        prof_dirs = sorted(prof_dirs, key=lambda x: x.name)

        # Override profiles if any specified
        prof_dict = {os.path.basename(d): d for d in prof_dirs}
        for o in yd.get("overrides", []):
            prof_dict[o["name"]] = rootdir / o["suitedir"]
        profiles = [Profile(name=n, path=p) for n, p in prof_dict.items()]

        print(f"Data: {yd}")

        s = Suite(
            name=yd["name"],
            suitedir=suitedir,
            profiles=profiles,
        )
        suites[yd["name"]] = s

    return suites


if __name__ == "__main__":
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_fpath = os.path.join(parent_dir, "suites.yaml")
    suites = read_suites(yaml_fpath)
    df = get_suite_amr_runtimes(suites["idk"])
    print(df)
    df = get_suite_tracesizes(suites["idk"])
    print(df)
