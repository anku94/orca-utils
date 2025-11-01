import pandas as pd
import glob
import re
import os


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


def get_suite_amr_runtimes(suite_dir: str) -> pd.DataFrame:
    print(f"Getting AMR runtimes for suite {suite_dir}")
    subdirs = glob.glob(f"{suite_dir}/*")
    subdirs = [d for d in subdirs if os.path.isdir(d)]
    subdirs.sort()
    profile_names = [os.path.basename(d) for d in subdirs]

    runtimes = [get_runtime(d) for d in subdirs]
    df = pd.DataFrame({"profile": profile_names, "time_secs": runtimes})
    return df


if __name__ == "__main__":
    suite_root = "/mnt/ltio/orcajobs/suites"
    suite_name = "20251103_amr-r128-psm141-nohugepages-n20"
    suite_dir = f"{suite_root}/{suite_name}"
    get_suite_amr_runtimes(suite_dir)
