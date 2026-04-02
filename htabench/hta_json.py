import os
import inspect
import sys
import time
from dataclasses import dataclass
from typing import Any, Optional
import pandas as pd
from hta.trace_analysis import TraceAnalysis
from hta.common.trace_parser import parse_trace_dict
from hta.configs.parser_config import ParserConfig


@dataclass
class AnalysisResult:
    parse_time: float     # seconds to parse raw trace into dataframe
    load_time: float      # seconds for full load (parse + post-processing)
    analysis_time: float  # seconds to run the analysis function
    total_time: float     # parse_time + load_time + analysis_time
    result: Any           # the analysis output


def local_trace_analysis(
    trace_file: str,
    analysis_func: str
) -> Optional[AnalysisResult]:
    trace_file = os.path.abspath(trace_file)
    try:
        analysis_func = getattr(TraceAnalysis, analysis_func)
        cfg = ParserConfig.get_default_cfg()

        # Phase 1: IO only (JSON decompress + parse into dict + DataFrame)
        t0 = time.perf_counter()
        trace_record = parse_trace_dict(trace_file)
        df = pd.DataFrame(trace_record.get("traceEvents", []))
        print(f"Found {len(df)} trace events in json: {trace_file}")
        t1 = time.perf_counter()

        # Phase 2: full load (IO + post-processing via TraceAnalysis constructor)
        traces = {0: trace_file}
        analyzer = TraceAnalysis(trace_files=traces)
        t2 = time.perf_counter()

        # Phase 3: analysis
        sig = inspect.signature(analysis_func)
        if 'visualize' in sig.parameters:
            result = analysis_func(analyzer, visualize=False)
        else:
            result = analysis_func(analyzer)
        t3 = time.perf_counter()

        return AnalysisResult(
            parse_time=t1 - t0,
            load_time=t2 - t1,
            analysis_time=t3 - t2,
            total_time=t3 - t1,
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
