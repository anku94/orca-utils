import os
import time
import statistics
import argparse
from typing import List, Dict, Optional
import hta_json
import hta_parquet

# HTA functions may emit FutureWarnings, ignore them because they don't affect the correctness of the analysis.
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)


# TODO: Do not use os.sched_setaffinity() as it's not platform independent.
# Maybe do this via configurating python runtime.
def set_cpu_affinity(num_cores: Optional[int] = None) -> List[int]:
    """
    Set CPU affinity to limit the number of cores used.

    Args:
        num_cores: Number of cores to use. If None, uses all available cores.

    Returns:
        List of CPU cores being used.
    """
    if num_cores is None:
        return list(range(os.cpu_count()))

    available_cores = list(range(min(num_cores, os.cpu_count())))

    try:
        # Set CPU affinity (Linux/Unix only)
        os.sched_setaffinity(0, available_cores)
        print(f"CPU affinity set to cores: {available_cores}")
    except AttributeError:
        # Fallback for systems that don't support sched_setaffinity
        print(
            f"CPU affinity not supported on this system. Using {os.cpu_count()} cores."
        )
        available_cores = list(range(os.cpu_count()))

    return available_cores


def benchmark_local_trace_analysis(
    mode: str,
    trace_file: str,
    hta_func: str,
    warmup_runs: int = 3,
    measurement_runs: int = 10,
    num_cores: Optional[int] = None,
) -> Dict[str, float]:
    """
    Benchmark the local_trace_analysis function with proper warmup and multiple measurements.

    Args:
        trace_file: Path to the trace file
        rank: Rank parameter for analysis
        warmup_runs: Number of warmup runs to discard
        measurement_runs: Number of measurement runs to average
        num_cores: Number of CPU cores to use (None for all)

    Returns:
        Dictionary with timing statistics
    """

    print(f"Benchmarking local_trace_analysis:")
    print(f"  Trace file: {trace_file}")
    print(f"  Warmup runs: {warmup_runs}")
    print(f"  Measurement runs: {measurement_runs}")
    print(f"  Number of CPU cores: {num_cores}")
    print()

    set_cpu_affinity(num_cores)

    analysis_func = (
        hta_json.local_trace_analysis
        if mode == "json"
        else hta_parquet.local_trace_analysis
    )

    # Warmup runs
    print("Running warmup...")
    for i in range(warmup_runs):
        start_time = time.perf_counter()
        result = analysis_func(trace_file, hta_func)
        end_time = time.perf_counter()
        warmup_time = end_time - start_time
        print(f"  Warmup {i+1}/{warmup_runs}: {warmup_time:.4f}s")

    print("\nRunning measurements...")

    # Measurement runs
    times: List[float] = []
    for i in range(measurement_runs):
        start_time = time.perf_counter()
        result = analysis_func(trace_file, hta_func)
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time
        times.append(elapsed_time)
        print(f"  Run {i+1}/{measurement_runs}: {elapsed_time:.4f}s")

    # Calculate statistics
    stats = {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        "min": min(times),
        "max": max(times),
        "runs": len(times),
        "cores_used": num_cores,
    }

    print("\nBenchmark Results:")
    print(f"  Mean:     {stats['mean']:.4f}s ± {stats['stdev']:.4f}s")
    print(f"  Median:   {stats['median']:.4f}s")
    print(f"  Min:      {stats['min']:.4f}s")
    print(f"  Max:      {stats['max']:.4f}s")
    print(f"  Runs:     {stats['runs']}")
    print(f"  Cores:    {stats['cores_used']}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark HTA trace analysis performance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["json", "parquet"],
        default="json",
        help="Input file format mode",
    )

    parser.add_argument(
        "--file", "-f", type=str, required=True, help="Path to the trace file"
    )

    parser.add_argument(
        "--warmup", "-w", type=int, default=3, help="Number of warmup runs"
    )

    parser.add_argument(
        "--runs", "-r", type=int, default=10, help="Number of measurement runs"
    )

    parser.add_argument(
        "--cores",
        "-c",
        type=int,
        default=1,
        help="Number of CPU cores to use (default: 1)",
    )

    # In HTA get_gpu_kernel_breakdown returns two dataframes and we split it
    # into two function in hta_parquet.py.
    parser.add_argument(
        "--hta_func",
        "-hf",
        type=str,
        required=True,
        help="HTA analysis function to use. Available functions: "
        + ", ".join([
            "get_temporal_breakdown",
            "get_comm_comp_overlap",
            "get_memory_bw_time_series",
        ]),
    )

    args = parser.parse_args()

    benchmark_local_trace_analysis(
        mode=args.mode,
        trace_file=args.file,
        warmup_runs=args.warmup,
        measurement_runs=args.runs,
        num_cores=args.cores,
        hta_func=args.hta_func,
    )

    return 0


# Example usage:
# python bench_json_vs_parquet.py --mode json --file h100_trace.json --hta_func get_temporal_breakdown
# python bench_json_vs_parquet.py --mode parquet --file h100_trace.parquet --hta_func get_temporal_breakdown
if __name__ == "__main__":
    exit(main())
