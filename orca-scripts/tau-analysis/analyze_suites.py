import re
import otf2
from suite_utils import *
from dataclasses import dataclass
import logging


def run_amr_runtimes(suites: list[Suite], save: bool = False):
    # suites = read_all_suites("suites_v2.yaml", suites)
    # all_rdf = []
    # for suite in suites:
    #     rdf = get_suite_amr_runtimes(suite)
    #     all_rdf.append(rdf)
    all_rdf = [get_suite_amr_runtimes(suite) for suite in suites]
    merged_rdf = pd.concat(all_rdf)

    # (nranks, nsteps, run_id) is the primary key
    merged_base = merged_rdf[merged_rdf["name"] == "00_noorca"].copy()
    merged_rdf = merged_rdf.merge(merged_base, on=[
                                  "nranks", "nsteps", "run_id"], how="left", suffixes=("", "_base"), validate="m:1")
    merged_rdf["ratio"] = merged_rdf["time_secs"] / merged_rdf["time_secs_base"]
    colstodrop = ["name_base", "naggs_base"]
    merged_rdf = merged_rdf.drop(columns=colstodrop)
    print(merged_rdf.to_string())

    if save:
        df_out = get_script_root() / "data" / "amr_runtimes.csv"
        logger.info(f"Writing output to: {df_out}")
        merged_rdf.to_csv(df_out, index=False)


def run_amr_tracesizes(suites: list[Suite], save: bool = False):
    all_sdf = []

    for suite in suites:
        sdf = get_suite_tracesizes(suite)
        evtcnts = [profile.get_evtcnt() for profile in suite.profiles]
        sdf["evtcnt"] = evtcnts

        all_sdf.append(sdf)

    merged_sdf = pd.concat(all_sdf)
    print(merged_sdf.to_string())

    if save:
        df_out = get_script_root() / "data" / "amr_tracesizes.csv"
        logger.info(f"Writing output to: {df_out}")
        merged_sdf.to_csv(df_out, index=False)


def run():
    suites = read_v2_suites("20251212")
    run_amr_runtimes(suites, save=True)
    run_amr_tracesizes(suites, save=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
