import os
import inspect
import sys
from hta.trace_analysis import TraceAnalysis


def local_trace_analysis(
    trace_file: str,
    analysis_func: str
):
    trace_file = os.path.abspath(trace_file)
    try:
        analysis_func = getattr(TraceAnalysis, analysis_func)
        traces = {0: trace_file}
        analyzer = TraceAnalysis(trace_files=traces)

        # Check if the analysis function accepts a 'visualize' parameter
        sig = inspect.signature(analysis_func)
        if 'visualize' in sig.parameters:
            result = analysis_func(analyzer, visualize=False)
        else:
            result = analysis_func(analyzer)

        return result

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
