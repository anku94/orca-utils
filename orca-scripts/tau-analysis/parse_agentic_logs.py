import pandas as pd
import multiprocessing as mp
import re
from pathlib import Path
from dataclasses import dataclass
import suite_utils as su

TRACE_ROOT = "/mnt/ltio/orcajobs/suites/20260116-agentic-complete/amr-agg4-r4096-n2000-run1/20_or_disable_paused/logs"


@dataclass
class Row:
    ts: str
    step: int
    rows_in: int
    rows_out: int


def parse_num(s: str) -> int:
    # if last digit is K/M/B
    s = s.strip()
    units = {"K": 1e3, "M": 1e6, "B": 1e9}
    lc = s[-1].upper()
    # assert that lc is either a key in units or a digit
    assert lc in units or lc.isdigit(), f"Invalid unit: {lc}"

    if lc.isdigit():
        return int(float(s))

    sn_base = float(s[:-1])
    return int(sn_base * units[lc])


def parse_log(log_path: Path):
    print(f"Parsing log file {log_path}")
    lines = log_path.read_text().splitlines()
    lines = [line for line in lines if "rows_in" in line]
    all_rows: list[Row] = []
    regex = r"^([^ ]+) .*?ts=([-\d.]+): rows_in=([^,]+)\s*, rows_out=([^ ]+).*$"
    robj = re.compile(regex)

    for l in lines:
        try:
            mobj = re.match(robj, l)
            assert mobj is not None
            (ts, s, rin, rout) = mobj.groups()
            r = Row(ts, int(s), parse_num(rin), parse_num(rout))
            all_rows.append(r)
        except Exception as e:
            print(f"Error parsing line {l}: {e}")
            continue

    df = pd.DataFrame(all_rows)
    df.insert(0, "fname", log_path.name)
    return df


def test_parse_num():
    assert parse_num("100K") == 100_000
    assert parse_num("100M") == 100_000_000
    assert parse_num("100 B") == 100_000_000_000
    assert parse_num("100.00") == 100
    assert parse_num("100.00 K") == 100_000


def run_parse_all(all_files: list[Path], df_path: Path):
    with mp.Pool(processes=mp.cpu_count()) as pool:
        results = pool.map(parse_log, all_files)
    df = pd.concat(results)
    print(f"Saving to {df_path}")
    df.to_parquet(df_path)


def run_mini_test(one_file: Path):
    df = parse_log(one_file)
    print(df)


def run():
    test_parse_num()
    trace_root = Path(TRACE_ROOT)
    assert trace_root.exists(), f"Trace root {trace_root} does not exist"
    all_files = list(trace_root.glob("*.log"))
    print(f"Found {len(all_files)} log files")

    run_mini_test(all_files[0])

    data_dir = su.get_repo_data_dir()
    df_path = data_dir / "20260116-agentic-complete-rowcounts.parquet"
    run_parse_all(all_files, df_path)


if __name__ == "__main__":
    run()
