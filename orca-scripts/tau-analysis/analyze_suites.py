import re
from suite_utils import *
from dataclasses import dataclass

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@dataclass
class SuiteProps:
    ranks: int
    aggs: int
    steps: int


def infer_suite_props(suite_name: str) -> dict:
    matches = re.findall(r"r(\d+)", suite_name)
    ranks = int(matches[0])

    aggs = re.findall(r"a(\d+)", suite_name)
    aggs = int(aggs[0])

    steps = re.findall(r"n(\d+)", suite_name)
    steps = int(steps[0])

    return SuiteProps(ranks=ranks, aggs=aggs, steps=steps)


def run_amr_runtimes(suites: list[str]):
    suites = read_all_suites(suites)
    all_rdf = []
    for suite in suites:
        rdf = get_suite_amr_runtimes(suite)
        suite_props = infer_suite_props(suite.name)

        rdf.insert(0, "suite", suite.name)
        rdf.insert(1, "ranks", suite_props.ranks)
        rdf.insert(2, "aggs", suite_props.aggs)
        rdf.insert(3, "steps", suite_props.steps)

        all_rdf.append(rdf)

    merged_rdf = pd.concat(all_rdf)
    df_out = get_script_root() / "data" / "amr_runtimes.csv"
    logger.info(f"Writing output to: {df_out}")
    merged_rdf.to_csv(df_out, index=False)


def run_amr_tracesizes(suites: list[str]):
    suites = read_all_suites(suites)

    all_sdf = []
    for suite in suites:
        sdf = get_suite_tracesizes(suite)
        suite_props = infer_suite_props(suite.name)
        sdf.insert(0, "suite", suite.name)
        sdf.insert(1, "ranks", suite_props.ranks)
        sdf.insert(2, "aggs", suite_props.aggs)
        sdf.insert(3, "steps", suite_props.steps)
        all_sdf.append(sdf)

    merged_sdf = pd.concat(all_sdf)
    print(merged_sdf)

    df_out = get_script_root() / "data" / "amr_tracesizes.csv"
    logger.info(f"Writing output to: {df_out}")
    merged_sdf.to_csv(df_out, index=False)


def run():
    s512 = ["r512_a1_n20_v2", "r512_a1_n200_v2", "r512_a1_n2000_v2"]
    s1024 = ["r1024_a1_n20_v2", "r1024_a1_n200_v2", "r1024_a1_n2000_v2"]
    s2048 = ["r2048_a2_n20_v2", "r2048_a2_n200_v2", "r2048_a2_n2000_v2"]
    s4096 = ["r4096_a4_n20_v2", "r4096_a4_n200_v2", "r4096_a4_n2000_v2"]
    s4096_v3 = ["r4096_a4_n20_v3", "r4096_a4_n200_v3", "r4096_a4_n2000_v3"]
    # s4096_v4 = ["r4096_a4_n2000_v4"]
    all_suites = [*s512, *s1024, *s2048, *s4096, *s4096_v3]  # , *s4096_v4]

    # run_amr_runtimes(all_suites)
    run_amr_tracesizes(all_suites)


if __name__ == "__main__":
    run()
