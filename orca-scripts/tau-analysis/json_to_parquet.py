"""
json_to_parquet.py - Convert TAU JSON events to single Parquet file

Creates one unified DataFrame with padded missing values.
"""

import json
import time
import pandas as pd
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper


@timeit
def read_dataframe_json(json_file: str) -> pd.DataFrame:
    """Read TAU JSON events and return DataFrame with proper types."""

    with open(json_file) as f:
        events = json.load(f)

    # Create DataFrame
    df = pd.DataFrame(events)
    return df


@timeit
def read_dataframe_parquet(parquet_file: str) -> pd.DataFrame:
    """Read Parquet file and return DataFrame."""
    return pd.read_parquet(parquet_file)


@timeit
def read_dataframe_feather(feather_file: str) -> pd.DataFrame:
    """Read Feather file and return DataFrame."""
    return pd.read_feather(feather_file)



def convert_to_parquet(json_file: str) -> None:
    """Convert TAU JSON to Parquet and verify by reading back."""

    parquet_file = json_file.replace('.json', '.parquet')
    feather_file = json_file.replace('.json', '.feather')

    # Read and convert
    df = read_dataframe_json(json_file)
    print(f"Read {len(df)} events from JSON")

    # Write to Parquet
    df.to_parquet(parquet_file, index=False)
    print(f"Wrote to {parquet_file}")

    df.to_feather(feather_file)
    print(f"Wrote to {feather_file}")

    # Read back to verify
    df_verify = read_dataframe_parquet(parquet_file)
    print(f"Verified {len(df_verify)} events from Parquet")

    df_verify = read_dataframe_feather(feather_file)
    print(f"Verified {len(df_verify)} events from Feather")


def analyze_data(df: pd.DataFrame) -> None:
    unique_names = df["name"].unique()
    unique_names
    print(df["name"].value_counts().to_string())



if __name__ == '__main__':
    trace_dir = '/mnt/ltio/orcajobs/tau-analysis/sample_traces'
    parsed_dir = f'{trace_dir}-parsed'
    rank = 20

    json_file = f'{parsed_dir}/rank{rank}_msg.json'
    print(f"Converting: {json_file}")
    convert_to_parquet(json_file)

    json_file = f'{parsed_dir}/rank{rank}_nomsg.json'
    convert_to_parquet(json_file)
