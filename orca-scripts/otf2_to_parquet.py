import logging
from pathlib import Path
from typing import Dict

import pyarrow as pa
import pyarrow.parquet as pq
import otf2

import re

from dataclasses import dataclass
import multiprocessing

LocMap = Dict[int, otf2.definitions.Location]


@dataclass
class ConversionJob:
    trace_path: Path
    rank: int
    pq_path: Path


def build_rank_locmap(reader: otf2.reader.Reader) -> LocMap:
    """Build a dictionary from rank -> location id."""

    loc_map = {}
    for loc in reader.definitions.locations:
        mobj = re.match(r"Rank (\d+), CPU Thread (\d+)", loc.name)
        if mobj:
            rank = int(mobj.group(1))
            loc_map[rank] = loc

    return loc_map


def do_conversion(job: ConversionJob) -> None:
    reader = otf2.reader.Reader(str(job.trace_path))
    rank_locmap = build_rank_locmap(reader)
    rank_loc = rank_locmap[job.rank]

    timestamps = []
    names = []
    types = []

    for _, evt in reader.events([rank_loc]):
        if isinstance(evt, otf2.events.Leave):
            continue
        elif isinstance(evt, otf2.events.Metric):
            continue

        timestamp = evt.time
        name = "unknown"
        ev_type = "unknown"

        if hasattr(evt, "region"):
            name = evt.region.name
            ev_type = "region"
        elif hasattr(evt, "collective_op"):
            name = evt.collective_op.name
            ev_type = "collective_op"
        elif hasattr(evt, "program_name"):
            name = evt.program_name
            ev_type = "program"

        timestamps.append(timestamp)
        names.append(name)
        types.append(ev_type)

    table = pa.Table.from_arrays(
        [pa.array(timestamps), pa.array(names), pa.array(types)],
        names=["timestamp", "name", "type"],
    )
    pq.write_table(table, job.pq_path)
    logging.info("wrote %d rows to %s", table.num_rows, job.pq_path)


def main() -> None:
    """Entry point: read an OTF2 archive and emit a small Parquet sample."""

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    data_root = Path("/mnt/ltio/orcajobs/suites")
    suite_root = data_root / "20251202_amr-agg1-r512-n20-psmerrchk141"
    trace_root = suite_root / "10_tau_tracetgt"
    trace_path = trace_root / "tau-trace/traces.otf2"

    pq_dir = trace_root / "parquet"
    pq_dir.mkdir(parents=True, exist_ok=True)

    all_jobs = []

    for rank in range(512):
        pq_path = pq_dir / f"rank_{rank}.parquet"
        all_jobs.append(
            ConversionJob(trace_path=trace_path, rank=rank, pq_path=pq_path)
        )

    with multiprocessing.Pool(processes=32) as pool:
        pool.map(do_conversion, all_jobs)


if __name__ == "__main__":
    main()
