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


def run():
    test_parse_num()
    r0_log = Path(TRACE_ROOT) / "orca.r0.log"
    assert r0_log.exists(), f"Log file {r0_log} does not exist"
    df = parse_log(r0_log)
    print(df)
    data_dir = su.get_repo_data_dir()
    df_out = data_dir / "agentic_rowcounts.parquet"
    df.to_parquet(df_out)


if __name__ == "__main__":
    run()
