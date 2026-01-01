import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

QueryType = Literal["count_window", "count_sync_maxdur", "count_mpi_wait_dur"]


@dataclass
class QueryResult:
    query_name: QueryType
    trace_dir: Path
    run_type: str
    data: str
    total_us: int


def now_micros() -> int:
    return int(time.monotonic_ns() / 1000)


def func_micros(fn):
    """Time a function and return (result, duration_us)."""
    start = now_micros()
    result = fn()
    end = now_micros()
    return result, (end - start)

