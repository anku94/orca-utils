import os
import inspect
import sys
import time
from dataclasses import dataclass
from typing import Any, Optional
from hta.trace_analysis import TraceAnalysis


@dataclass
class AnalysisResult:
    load_time: float      # seconds to load/parse the trace
    analysis_time: float  # seconds to run the analysis function
    total_time: float     # load_time + analysis_time
    result: Any           # the analysis output


def local_trace_analysis(
    trace_file: str,
    analysis_func: str
) -> Optional[AnalysisResult]:
    trace_file = os.path.abspath(trace_file)
    try:
        analysis_func = getattr(TraceAnalysis, analysis_func)

        t0 = time.perf_counter()
        traces = {0: trace_file}
        analyzer = TraceAnalysis(trace_files=traces)
        t1 = time.perf_counter()

        # Check if the analysis function accepts a 'visualize' parameter
        sig = inspect.signature(analysis_func)
        if 'visualize' in sig.parameters:
            result = analysis_func(analyzer, visualize=False)
        else:
            result = analysis_func(analyzer)
        t2 = time.perf_counter()

        return AnalysisResult(
            load_time=t1 - t0,
            analysis_time=t2 - t1,
            total_time=t2 - t0,
            result=result,
        )

    except AttributeError:
        print(f"Analysis function {analysis_func} not found")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python hta_json.py <input_json_path> <analysis_func>")
        sys.exit(1)
    trace_file = sys.argv[1]
    analysis_func = sys.argv[2]
    result = local_trace_analysis(trace_file, analysis_func)
    print(result)
