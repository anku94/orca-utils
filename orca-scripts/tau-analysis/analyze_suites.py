import re
import otf2
from suite_utils import *
from dataclasses import dataclass
import logging


def log_rdf_summary(rdf: pd.DataFrame):
    # group by [profile, ranks, steps, and get mean of time_secs
    rdf_agg = rdf.groupby(["steps", "ranks", "profile"]).agg(
        {"time_secs": "mean", "ratio": "mean"}).reset_index()
    # convert ratio to +x%
    rdf_agg["ratio"] = rdf_agg["ratio"].apply(lambda x: f"+{(x-1)*100:.1f}%")
    # pivot to make profiles a column
    rdf_agg = rdf_agg.pivot(
        index=["steps", "ranks"], columns="profile", values="ratio")
    print(rdf_agg.to_string())


def log_sdf_summary(sdf: pd.DataFrame):
    # filter for trace_size > 0
    sdf = sdf[sdf["trace_size"] > 0]
    # group by [profile, ranks, steps, and get mean of trace_size
    sdf_agg = sdf.groupby(["steps", "ranks", "profile"]).agg(
        {"trace_size": "mean"}).reset_index()

    # convert trace_size to GB
    sdf_agg["trace_size"] = sdf_agg["trace_size"].apply(
        lambda x: f"{x/2**30:.0f} GB")
    # pivot to make profiles a column
    sdf_agg = sdf_agg.pivot(
        index=["steps", "ranks"], columns="profile", values="trace_size")
    print(sdf_agg.to_string())


def run_amr_runtimes(suites: list[Suite], df_path: Path, save: bool = False):
    all_rdf = [get_suite_amr_runtimes(suite) for suite in suites]
    merged_rdf = pd.concat(all_rdf)

    # (nranks, nsteps, run_id) is the primary key
    merged_base = merged_rdf[merged_rdf["profile"] == "00_noorca"].copy()
    merged_rdf = merged_rdf.merge(merged_base, on=[
                                  "ranks", "steps", "run_id"], how="left", suffixes=("", "_base"), validate="m:1")
    merged_rdf["ratio"] = merged_rdf["time_secs"] / \
        merged_rdf["time_secs_base"]
    colstodrop = ["root_base", "name_base", "profile_base", "aggs_base"]
    merged_rdf = merged_rdf.drop(columns=colstodrop)
    # print(merged_rdf.to_string())
    log_rdf_summary(merged_rdf)

    if save:
        logger.info(f"Writing output to: {df_path}")
        merged_rdf.to_csv(df_path, index=False)


def run_amr_tracesizes(suites: list[Suite], df_path: Path, save: bool = False):
    all_sdf = []

    for suite in suites:
        sdf = get_suite_tracesizes(suite)
        evtcnts = [profile.get_evtcnt() for profile in suite.profiles]
        sdf["evtcnt"] = evtcnts

        all_sdf.append(sdf)

    merged_sdf = pd.concat(all_sdf)
    # print(merged_sdf.to_string())
    log_sdf_summary(merged_sdf)

    if save:
        logger.info(f"Writing output to: {df_path}")
        merged_sdf.to_csv(df_path, index=False)


def parse_opts() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    pargs = parser.parse_args()
    return pargs.suite_dir


def run(suite_dir: Path):
    suites = read_v2_suites(suite_dir)
    suite_name = suite_dir.name
    runtimes_path = get_script_root() / "data" / f"{suite_name}_runtimes.csv"
    tracesizes_path = get_script_root() / "data" / \
        f"{suite_name}_tracesizes.csv"
    run_amr_runtimes(suites, runtimes_path, save=False)
    run_amr_tracesizes(suites, tracesizes_path, save=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    suite_dir = parse_opts()
    logger.info(f"Analyzing suites in: {suite_dir}")
    run(suite_dir)
