import gzip
from typing import Any, Dict
import numpy as np
import pyarrow as pa
import json
import pandas as pd
import pyarrow.parquet as pq
import os
import sys
from hta.configs.parser_config import ParserConfig


# The goal here is to convert a trace JSON file to a parquet file,
# that contains only needed columns for HTA temporal breakdown analysis.
def _convert_trace_json_to_parquet(trace_json_path: dict, parquet_path: str):
    trace_record: Dict[str, Any] = {}
    if trace_json_path.endswith('.gz'):
        with gzip.open(trace_json_path, 'rb') as f:
            trace_record = json.loads(f.read())
    elif trace_json_path.endswith('.json'):
        with open(trace_json_path, 'r') as f:
            trace_record = json.loads(f.read())
    else:
        raise ValueError(f"Invalid trace JSON path: {trace_json_path}")

    meta: Dict[str, Any] = {k: v for k,
                            v in trace_record.items() if k != "traceEvents"}
    df = pd.DataFrame(trace_record["traceEvents"])
    initial_total_rows = len(df)
    print(f"Initial row count: {initial_total_rows}")

    print(f'Initial dtypes:\n{df.dtypes}')

    # Note: the below back and forth are partly what HTA's compress_df() does.
    # We do this to make sure the traces can share a fixed schema, and we
    # shouldn't do this part again when preprocessing parquet-based traces.

    # These special pid cannot be converted to int64
    df.drop(df[df["pid"] == "Spans"].index, inplace=True)
    df.drop(df[df["pid"] == "Traces"].index, inplace=True)


    # Extract fields from args and make them separate columns
    columns = set(df.columns)
    if "args" in columns:
        args_to_keep = ParserConfig.get_default_args()
        for arg in args_to_keep:
            df[arg.name] = df["args"].apply(
                lambda row, arg=arg: (
                    row.get(arg.raw_name, arg.default_value)
                    if isinstance(row, dict)
                    else arg.default_value
                )
            )
        df.drop(["args"], axis=1, inplace=True)
    
    # Convert pid/tid to int64, replace empty strings with -1
    for col in ("pid", "tid"):
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace(["", None], "-1")
            # Convert to numeric, coercing errors to NaN, then fill NaN with -1
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(np.int64)
    
    # Convert specific columns with complex types (lists, dicts) to JSON strings
    complex_cols = ['input_dims', 'input_type', 'input_strides']
    for col in complex_cols:
        if col in df.columns:
            has_complex = df[col].apply(lambda x: isinstance(x, (list, dict))).any()
            if has_complex:
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else ('' if pd.isna(x) else str(x)))

    df["rank"] = 0
    df["rank"] = df["rank"].astype(np.int32)

    print(f'Final dtypes:\n{df.dtypes}')

    # Save the kineto metadata in the parquet file. In json they are individual blocks.
    final_row_count = len(df)
    total_dropped = initial_total_rows - final_row_count
    drop_pct = (total_dropped / initial_total_rows * 100) if initial_total_rows > 0 else 0
    print("\n=== End-to-end summary ===")
    print(f"Initial rows: {initial_total_rows}")
    print(f"Final rows: {final_row_count}")
    print(f"Total dropped: {total_dropped} ({drop_pct:.2f}%)")

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_metadata = table.schema.metadata or {}
    # The metadata of parquet must be in bytes, so encode it as a json string for simplicity
    # and then encode it as bytes.
    metadata = {**existing_metadata,
                b'kineto_metadata': json.dumps(meta).encode('utf-8')}
    new_schema = table.schema.with_metadata(metadata)
    table = table.cast(new_schema)
    pq.write_table(table, parquet_path)


# Either specify input and output directories, or a single input and output file.
def convert_trace_json_to_parquet(trace_json_path_or_dir: str, parquet_path_or_dir: str):
    if os.path.isdir(trace_json_path_or_dir):
        if not os.path.isdir(parquet_path_or_dir):
            if parquet_path_or_dir.endswith('.parquet'):
                raise ValueError(
                    f"Parquet path must be a directory, not a file: {parquet_path_or_dir}")
            os.makedirs(parquet_path_or_dir)

        for file in os.listdir(trace_json_path_or_dir):
            if file.endswith('.json'):
                _convert_trace_json_to_parquet(os.path.join(trace_json_path_or_dir, file), os.path.join(
                    parquet_path_or_dir, file.replace('.json', '.parquet')))
    else:
        if trace_json_path_or_dir.endswith('.json'):
            if not parquet_path_or_dir.endswith('.parquet'):
                raise ValueError(
                    f"Parquet path must be a file, not a directory: {parquet_path_or_dir}")
            _convert_trace_json_to_parquet(
                trace_json_path_or_dir, parquet_path_or_dir)
        else:
            raise ValueError(
                f"Invalid trace JSON path: {trace_json_path_or_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python kineto_json_to_parquet.py <input_json_path> <output_parquet_path>")
        sys.exit(1)
    convert_trace_json_to_parquet(sys.argv[1], sys.argv[2])
