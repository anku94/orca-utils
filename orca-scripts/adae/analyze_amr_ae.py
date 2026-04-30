#!/usr/bin/env python3
#
# AE analysis for A1: drive tau-analysis entry points to produce
# trace-size and runtime CSVs from a populated suitedir.
# Documentation-of-intent skeleton; expect to revise against real runs.
#

import sys
from pathlib import Path

# Make tau-analysis importable
SCRIPT_DIR = Path(__file__).resolve().parent
TAU_DIR = SCRIPT_DIR.parent / "tau-analysis"
sys.path.insert(0, str(TAU_DIR))

from suite_utils import read_v2_suites
from analyze_suites import run_amr_tracesizes, run_amr_runtimes


def get_suitedir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    sd = Path("/tmp/orca-ae-suites").resolve()
    if not sd.exists():
        raise SystemExit(f"suitedir not found: {sd} (pass as argv[1] or set up first)")
    return sd


# analyze_tracesizes: per-profile bytes, written to trace_sizes.csv
def analyze_tracesizes(suitedir: Path, suites):
    out = suitedir / "trace_sizes.csv"
    print(f"-INFO- writing trace sizes to {out}")
    run_amr_tracesizes(suites, df_path=out, save=True)


# analyze_overhead: per-profile wall-clock + overhead vs baseline, via tau-analysis
def analyze_overhead(suitedir: Path, suites):
    out = suitedir / "runtimes.csv"
    print(f"-INFO- writing runtimes to {out}")
    run_amr_runtimes(suites, df_path=out, save=True)


def main():
    suitedir = get_suitedir()
    print(f"-INFO- suitedir: {suitedir}")
    suites = read_v2_suites(suitedir.parent)
    suites = [s for s in suites if s.suitedir.parent == suitedir.parent and s.suitedir.name == suitedir.name]
    if not suites:
        raise SystemExit(f"no suites found under {suitedir}")

    # Comment out either step for partial trials.
    analyze_tracesizes(suitedir, suites)
    analyze_overhead(suitedir, suites)


if __name__ == "__main__":
    main()
