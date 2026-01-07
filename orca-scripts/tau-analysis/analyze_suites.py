import re
import otf2
from suite_utils import *
from dataclasses import dataclass
import logging
from pathlib import Path
import sys


@dataclass
class ParseOpts:
    suite_dir: Path
    save: bool = False


def log_rdf_summary(rdf: pd.DataFrame):
    # group by [profile, ranks, steps, and get mean of time_secs
    rdf_agg = (
        rdf.groupby(["steps", "ranks", "profile"])
        .agg({"time_secs": "mean", "ratio": "mean"})
        .reset_index()
    )
    # convert ratio to +x%
    rdf_agg["ratio"] = rdf_agg["ratio"].apply(lambda x: f"+{(x-1)*100:.1f}%")
    # pivot to make profiles a column
    rdf_agg = rdf_agg.pivot(index=["steps", "ranks"], columns="profile", values="ratio")
    print(rdf_agg.to_string())


def log_sdf_summary(sdf: pd.DataFrame):
    # filter for trace_size > 0
    sdf = sdf[sdf["trace_size"] > 0]
    # group by [profile, ranks, steps, and get mean of trace_size
    sdf_agg = (
        sdf.groupby(["steps", "ranks", "profile"])
        .agg({"trace_size": "mean"})
        .reset_index()
    )

    # convert trace_size to GB
    sdf_agg["trace_size"] = sdf_agg["trace_size"].apply(lambda x: f"{x/2**30:.2f} GB")
    # pivot to make profiles a column
    sdf_agg = sdf_agg.pivot(
        index=["steps", "ranks"], columns="profile", values="trace_size"
    )
    print(sdf_agg.to_string())


def run_amr_runtimes(suites: list[Suite], df_path: Path, save: bool = False):
    all_rdf = [get_suite_amr_runtimes(suite) for suite in suites]
    merged_rdf = pd.concat(all_rdf)

    # (nranks, nsteps, run_id) is the primary key
    merged_base = merged_rdf[merged_rdf["profile"] == "00_noorca"].copy()
    merged_rdf = merged_rdf.merge(
        merged_base,
        on=["ranks", "steps", "run_id"],
        how="left",
        suffixes=("", "_base"),
        validate="m:1",
    )
    merged_rdf["ratio"] = merged_rdf["time_secs"] / merged_rdf["time_secs_base"]
    colstodrop = ["root_base", "name_base", "profile_base", "aggs_base"]
    merged_rdf = merged_rdf.drop(columns=colstodrop)
    # sort by: steps, ranks, agg, profile, run_id
    merged_rdf = merged_rdf.sort_values(
        by=["steps", "ranks", "aggs", "profile", "run_id"]
    )
    print(merged_rdf.to_string())
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
    print(merged_sdf.to_string())
    log_sdf_summary(merged_sdf)

    if save:
        logger.info(f"Writing output to: {df_path}")
        merged_sdf.to_csv(df_path, index=False)


def parse_opts() -> ParseOpts:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", "-d", type=Path, required=True)
    parser.add_argument("--save", "-s", action="store_true", default=False)
    pargs = parser.parse_args()
    return ParseOpts(suite_dir=pargs.suite_dir, save=pargs.save)


def run(opts: ParseOpts):
    suites = read_v2_suites(opts.suite_dir)

    suite_name = f"{opts.suite_dir.name}"

    rdf_path = get_repo_data_dir() / "runtimes" / f"{suite_name}.csv"
    rdf_path.parent.mkdir(parents=True, exist_ok=True)
    sdf_path = get_repo_data_dir() / "tracesizes" / f"{suite_name}.csv"
    sdf_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Will write runtimes to: {rdf_path}")
    logger.info(f"Will write tracesizes to: {sdf_path}")

    run_amr_runtimes(suites, rdf_path, save=opts.save)
    run_amr_tracesizes(suites, sdf_path, save=opts.save)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    opts = parse_opts()
    logger.info(f"Analyzing suites in: {opts.suite_dir}, save={opts.save}")
    run(opts)
