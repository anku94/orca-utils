import logging
from functools import wraps
import time
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import re
import os
import duckdb
import polars as pl
from datetime import datetime
import otf2
import yaml
from concurrent.futures import ThreadPoolExecutor
import argparse

SUITE_ROOT = Path("/mnt/ltio/orcajobs/suites")


logger = logging.getLogger(__name__)


def _get_linecount_ascii(fpath: Path) -> int:
    with open(fpath, "r") as f:
        return len(f.readlines())


class Profile:
    def __init__(self, path: Path):
        self.name = os.path.basename(path)
        self.path = path

    def __lt__(self, other: 'Profile') -> bool:
        return self.sort_key() < other.sort_key()

    def __eq__(self, other: 'Profile') -> bool:
        return self.sort_key() == other.sort_key()

    def sort_key(self) -> tuple[int, int, int]:
        mobj = re.match(r"^(\d+)_(.*)$", self.name)
        assert mobj is not None
        return int(mobj.group(1))

    def get_tracedir(self) -> Path:
        if os.path.exists(f"{self.path}/parquet"):
            return Path(f"{self.path}/parquet")
        elif os.path.exists(f"{self.path}/tau-trace"):
            return Path(f"{self.path}/tau-trace")
        elif os.path.exists(f"{self.path}/trace"):
            return Path(f"{self.path}/trace")
        else:
            raise FileNotFoundError(f"No trace directory found in {self.path}")

    def _get_evtcount_otf2(self) -> int:
        logger.info(f"Getting event count for profile {self.name}")

        all_files = list(self.get_tracedir().glob("**/*.otf2"))
        if len(all_files) == 0:
            return -1

        evtcnt = 0
        for f in all_files:
            reader = otf2.reader.Reader(str(f))
            evtcnt += len(reader.events)
        return evtcnt

    def _get_evtcount_dft(self) -> int:
        logger.info(f"Getting event count for profile {self.name}")

        all_files = list(self.get_tracedir().glob("**/*.pfw"))
        if len(all_files) == 0:
            return -1

        evtcnt = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_get_linecount_ascii, f)
                       for f in all_files]
            results = [future.result() for future in futures]
        return sum(results)

    def _get_evtcnt_parquet(self) -> int:
        logger.info(f"Getting event count for profile {self.name}")

        evtcnt = 0
        for item in self.get_tracedir().iterdir():
            if item.name == "orca_events" or not item.is_dir():
                continue

            glob_pattern = f"{item}/**/*.parquet"
            try:
                pl_df = pl.scan_parquet(glob_pattern, parallel="columns")
                evtcnt += pl_df.count().collect().item(0, 0)
            except Exception as e:
                logger.error(f"Error scanning parquet files in {item}: {e}")
                evtcnt = -1
                continue

        return evtcnt

    def get_evtcnt(self, cached: bool = True) -> int:
        evtcnt = -1

        evtcnt_file = self.path / ".evtcnt"
        if cached and evtcnt_file.exists():
            with open(evtcnt_file, "r") as f:
                evtcnt = int(f.read())
            return evtcnt

        if self.name == "07_trace_tgt":
            evtcnt = self._get_evtcnt_parquet()
        elif self.name == "10_tau_tracetgt":
            evtcnt = self._get_evtcount_otf2()
        elif self.name == "11_dftracer":
            evtcnt = self._get_evtcount_dft()

        with open(evtcnt_file, "w") as f:
            f.write(str(evtcnt))

        return evtcnt


class Suite:
    def __init__(self, suitedir: Path, profiles: list[Profile]):
        self.name = os.path.basename(suitedir)
        self.suitedir = suitedir
        self.profiles = sorted(profiles)

        mobj = re.match(r"^(.*)-agg(\d+)-r(\d+)-n(\d+)-run(\d+)$", self.name)
        assert mobj is not None

        self.run_type = mobj.group(1)
        self.naggs = int(mobj.group(2))
        self.ranks = int(mobj.group(3))
        self.nsteps = int(mobj.group(4))
        self.run_id = int(mobj.group(5))

    def __repr__(self) -> str:
        s = f"Suite(name={self.name:28s}, "
        s += f"ranks={self.ranks:4d}, "
        s += f"naggs={self.naggs}, "
        s += f"nsteps={self.nsteps:4d}, "
        s += f"run_id={self.run_id}, "
        s += f"nprofs={len(self.profiles)}"
        s += ")"

        # profs = ', '.join([p.name for p in self.profiles])
        # s += f"\n  profiles[{len(self.profiles)}]: {profs}"
        return s

    def sort_key(self) -> tuple[int, int, int]:
        return (self.ranks, self.nsteps, self.run_id)

    def get_prof_path(self, prof_name: str) -> Path:
        profs = [p for p in self.profiles if p.name == prof_name]
        if len(profs) == 0:
            raise ValueError(
                f"Profile {prof_name} not found in suite {self.name}")
        return profs[0].path


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
    logger.info(f"Getting trace sizes for suite {suite}")

    df = get_suitedf(suite)
    tracedirs = [get_tracedir(p.path) for p in suite.profiles]
    trace_dfs = [get_dir_size_cached(td) for td in tracedirs]

    tracesizes = []
    for prof, ptdf in zip(suite.profiles, trace_dfs):
        mobj = re.match(r"^(\d+)_or_(.*)$", prof.name)
        if mobj:
            # filter out orca_events
            logger.warning(f"{prof.name}: excluding orca_events from tracesz calc")
            ptdf = ptdf[~ptdf["fpath"].str.contains("orca_events", na=False)]
            tracesizes.append(ptdf["fsize"].sum())
        else:
            tracesizes.append(ptdf["fsize"].sum())

    df["trace_size"] = tracesizes
    return df


def get_profile_amr_runtime(profile_dir: Path) -> float:
    logger.debug(f"Getting runtime for profile {profile_dir}")
    mpi_log = f"{profile_dir}/mpi.log"

    with open(mpi_log, "r") as f:
        lines = f.readlines()
        lines = [l.strip() for l in lines if "walltime used" in l]

    # print(lines)
    if len(lines) == 0:
        return 0

    mobj = re.match(r"walltime used = (\d+\.\d+)$", lines[0])
    if mobj is None:
        return 0

    return float(mobj.group(1))


def get_suitedf(suite: Suite) -> pd.DataFrame:
    df_rows = []
    for p in suite.profiles:
        df_rows.append({
            "root": suite.suitedir.parent,
            "name": suite.name,
            "profile": p.name,
            "ranks": suite.ranks,
            "aggs": suite.naggs,
            "steps": suite.nsteps,
            "run_id": suite.run_id})

    df = pd.DataFrame(df_rows)
    return df


def get_suite_amr_runtimes(suite: Suite) -> pd.DataFrame:
    logger.info(f"Getting AMR runtimes for suite {suite}")

    # Returns a dataframe like this:
    #               profile  time_secs
    # 0     10_dftracer     2.5723
    # 1       11_scorep     2.6378
    # 2  08_tau_default     3.1165
    df = get_suitedf(suite)
    runtimes = [get_profile_amr_runtime(p.path) for p in suite.profiles]
    df["time_secs"] = runtimes
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

    # print(f"YAML data: {yaml_data}")

    rootdir = Path(yaml_data["root"])
    suites: SuiteMap = {}
    for yd in yaml_data["suites"]:
        suitedir = rootdir / yd["suitedir"]
        # enumerate all directories in suitedir
        if not suitedir.exists():
            logger.warning(f"No suite {yd['name']} in dir: {suitedir}")
            continue

        prof_dirs = [d for d in suitedir.iterdir() if d.is_dir()]
        prof_dirs = sorted(prof_dirs, key=lambda x: x.name)

        # Override profiles if any specified
        prof_dict = {os.path.basename(d): d for d in prof_dirs}
        for o in yd.get("overrides", []):
            prof_dict[o["name"]] = rootdir / o["suitedir"]
        profiles = [Profile(name=n, path=p) for n, p in prof_dict.items()]

        # print(f"Data: {yd}")

        s = Suite(
            name=yd["name"],
            suitedir=suitedir,
            profiles=profiles,
        )
        suites[yd["name"]] = s

    return suites


def read_v2_suites(suite_rootdir: Path) -> list[Suite]:
    suite_dirs = [d for d in suite_rootdir.iterdir() if d.is_dir()]
    logger.info(f"Found {len(suite_dirs)} suites in {suite_rootdir}")

    suites: list[Suite] = []
    for suite_rootdir in suite_dirs:
        prof_dirs = [d for d in suite_rootdir.iterdir() if d.is_dir()]
        logger.debug(f"Found {len(prof_dirs)} profiles in suite {suite_rootdir}")

        profiles = [Profile(path=d) for d in prof_dirs]
        suite = Suite(suitedir=suite_rootdir, profiles=profiles)
        suites.append(suite)

    return sorted(suites, key=lambda x: x.sort_key())


def get_script_root() -> Path:
    return Path(os.path.dirname(os.path.abspath(__file__)))


def get_repo_data_dir() -> Path:
    return get_script_root() / "data"


def read_all_suites(yaml_fname: str, suite_names: list[str] | None) -> SuiteMap:
    yaml_fpath = get_script_root() / yaml_fname
    suites = read_suites(yaml_fpath)

    if suite_names is None:
        return suites
    else:
        return [suites[name] for name in suite_names]


if __name__ == "__main__":
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_fpath = os.path.join(parent_dir, "suites.yaml")
    suites = read_suites(yaml_fpath)
    df = get_suite_amr_runtimes(suites["idk"])
    print(df)
    df = get_suite_tracesizes(suites["idk"])
    print(df)
