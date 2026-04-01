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
        "load": [],
        "analysis": [],
        "total": [],
    }

    for f in files:
        load = parse_value(f, "Load:")
        analysis = parse_value(f, "Analysis:")
        total = parse_value(f, "Total:")
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


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <log_dir>")
        return 1

    log_dir = sys.argv[1]
    json_results = parse_logs(log_dir, "json")
    pq_results = parse_logs(log_dir, "parquet")

    if not json_results["total"] or not pq_results["total"]:
        print("Failed to parse results")
        return 1

    print(f"JSON:")
    print(f"  Load:     {fmt_stats(json_results['load'])}")
    print(f"  Analysis: {fmt_stats(json_results['analysis'])}")
    print(f"  Total:    {fmt_stats(json_results['total'])}")

    print(f"Parquet:")
    print(f"  Load:     {fmt_stats(pq_results['load'])}")
    print(f"  Analysis: {fmt_stats(pq_results['analysis'])}")
    print(f"  Total:    {fmt_stats(pq_results['total'])}")

    json_load = statistics.mean(json_results["load"])
    json_total = statistics.mean(json_results["total"])
    pq_load = statistics.mean(pq_results["load"])
    pq_total = statistics.mean(pq_results["total"])

    print(f"\nSpeedup (JSON / Parquet):")
    print(f"  Load:  {json_load / pq_load:.2f}x")
    print(f"  Total: {json_total / pq_total:.2f}x")

    return 0


if __name__ == "__main__":
    sys.exit(main())
