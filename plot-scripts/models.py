from fsql_client import CLIENT
import pandas as pd
from typing import TypedDict
from datetime import datetime, timedelta
import re

PROFILES: dict[str, dict[str, str]] = {
    "rpc": {
        "msgsz": "%HGRPC_RPCSZ_AVG%",
        "cpu_pct": "%CPU_PCT%",
        "rate_bytes": "%HGRPC_RATE_BYTES%",
        "rate_count": "%HGRPC_RATE_COUNT%"
    }
}


def get_metric_data(metric_pattern: str, start_timestamp: str) -> pd.DataFrame:
    where_clause = f"WHERE metric_name LIKE '{metric_pattern}'"
    if start_timestamp:
        where_clause += f" AND timestamp >= '{start_timestamp}'"

    query = f"""
    SELECT timestamp, ovid, metric_name, metric_val
    FROM orca_metrics 
    {where_clause}
    ORDER BY timestamp DESC
    """

    info = CLIENT.execute(query)
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    table = reader.read_all()
    return table.to_pandas()


def parse_relative_time(time_expr: str) -> str:
    if not time_expr.startswith("now-"):
        return time_expr
    
    time_part = time_expr[4:]
    match = re.match(r"(\d+)([mhd])", time_part)
    
    if not match:
        raise ValueError(f"Invalid time expression: {time_expr}")
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    now = datetime.now()
    
    if unit == "m":
        delta = timedelta(minutes=amount)
    elif unit == "h":
        delta = timedelta(hours=amount)
    elif unit == "d":
        delta = timedelta(days=amount)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")
    
    target_time = now - delta
    return target_time.strftime("%Y-%m-%d %H:%M:%S")


def get_profile_data(profile_name: str,
                     start_timestamp: str) -> dict[str, pd.DataFrame]:
    parsed_timestamp = parse_relative_time(start_timestamp)
    profile = PROFILES[profile_name]
    results = {}
    
    for metric_name, pattern in profile.items():
        results[metric_name] = get_metric_data(pattern, parsed_timestamp)
    
    return results


def run():
    data = get_profile_data("rpc", "now-15m")
    
    for metric_name, df in data.items():
        print(f"\n=== {metric_name.upper()} ===")
        print(f"Shape: {df.shape}")
        print(df.head())


if __name__ == "__main__":
    run()

