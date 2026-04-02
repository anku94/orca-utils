"""
Parse benchmark logs and compute speedup.
Usage: python parse_bench.py <log_dir>
Reads json-*.log and parquet-*.log, averages across iterations, reports speedup.
"""

import glob
import statistics
import sys
from pathlib import Path


def parse_value(logfile: str, key: str) -> float | None:
    with open(logfile) as f:
        for line in f:
            if line.strip().startswith(key):
                return float(line.split()[1].rstrip("s"))
    return None


def parse_logs(log_dir: str, prefix: str) -> dict[str, list[float]]:
    pattern = str(Path(log_dir) / f"{prefix}-*.log")
    files = sorted(glob.glob(pattern))

    results: dict[str, list[float]] = {
        "parse": [],
        "load": [],
        "analysis": [],
        "total": [],
    }

    for f in files:
        parse = parse_value(f, "Parse:")
        load = parse_value(f, "Load:")
        analysis = parse_value(f, "Analysis:")
        total = parse_value(f, "Total:")
        if parse is not None:
            results["parse"].append(parse)
        if load is not None:
            results["load"].append(load)
        if analysis is not None:
            results["analysis"].append(analysis)
        if total is not None:
            results["total"].append(total)

    return results


def fmt_stats(values: list[float]) -> str:
    if not values:
        return "N/A"
    mean = statistics.mean(values)
    if len(values) > 1:
        stdev = statistics.stdev(values)
        return f"{mean:.4f}s ± {stdev:.4f}s ({len(values)} runs)"
    return f"{mean:.4f}s (1 run)"


def speedup(json_vals: list[float], pq_vals: list[float]) -> str:
    if not json_vals or not pq_vals:
        return "N/A"
    return f"{statistics.mean(json_vals) / statistics.mean(pq_vals):.2f}x"


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <log_dir>")
        return 1

    log_dir = sys.argv[1]
    json_r = parse_logs(log_dir, "json")
    pq_r = parse_logs(log_dir, "parquet")

    if not json_r["total"] or not pq_r["total"]:
        print("Failed to parse results")
        return 1

    print(f"JSON:")
    print(f"  Parse:    {fmt_stats(json_r['parse'])}")
    print(f"  Load:     {fmt_stats(json_r['load'])}")
    print(f"  Analysis: {fmt_stats(json_r['analysis'])}")
    print(f"  Total:    {fmt_stats(json_r['total'])}")

    print(f"Parquet:")
    print(f"  Parse:    {fmt_stats(pq_r['parse'])}")
    print(f"  Load:     {fmt_stats(pq_r['load'])}")
    print(f"  Analysis: {fmt_stats(pq_r['analysis'])}")
    print(f"  Total:    {fmt_stats(pq_r['total'])}")

    print(f"\nSpeedup (JSON / Parquet):")
    print(f"  Parse:    {speedup(json_r['parse'], pq_r['parse'])}")
    print(f"  Load:     {speedup(json_r['load'], pq_r['load'])}")
    print(f"  Analysis: {speedup(json_r['analysis'], pq_r['analysis'])}")
    print(f"  Total:    {speedup(json_r['total'], pq_r['total'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
