import logging
from pathlib import Path
from typing import Dict

import pyarrow as pa
import pyarrow.parquet as pq
import otf2

import re
import argparse

from dataclasses import dataclass
import multiprocessing

LocMap = Dict[int, otf2.definitions.Location]


@dataclass
class Args:
    otf2_path: Path
    num_ranks: int

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


def main(args: Args) -> None:
    """Entry point: read an OTF2 archive and emit a small Parquet sample."""

    trace_path = args.otf2_path
    trace_root = trace_path.parent.parent
    logging.info("Converting %s", trace_path)

    pq_dir = trace_root / "parquet"
    logging.info("Output directory: %s", pq_dir)
    pq_dir.mkdir(parents=True, exist_ok=True)

    all_jobs = []

    for rank in range(args.num_ranks):
        pq_path = pq_dir / f"rank_{rank}.parquet"
        all_jobs.append(
            ConversionJob(trace_path=trace_path, rank=rank, pq_path=pq_path)
        )

    with multiprocessing.Pool(processes=32) as pool:
        pool.map(do_conversion, all_jobs)


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--otf2-path", type=Path, required=True, help="Path to .otf2 file to convert"
    )
    parser.add_argument(
        "--num-ranks", type=int, required=True, help="Number of ranks to convert"
    )
    args = parser.parse_args()

    # ensure the path exists
    if not args.otf2_path.exists():
        raise FileNotFoundError(f"File {args.otf2_path} does not exist")

    return Args(otf2_path=args.otf2_path, num_ranks=args.num_ranks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = parse_args()
    main(args)
