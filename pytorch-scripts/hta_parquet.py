from collections import defaultdict
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import pyarrow.parquet as pq
import numpy as np
import math
from hta.common.trace_symbol_table import TraceSymbolTable
from hta.utils.utils import KernelType


MetaData = Dict[str, Any]


def normalize_gpu_stream_numbers(df: pd.DataFrame) -> None:
    """
    Normalize the GPU stream numbers to be integers.
    If an event's stream number can't be converted to an int, we set it to -1.
    """
    df["stream"] = pd.to_numeric(df["stream"], errors="coerce").fillna(-1).astype(int)


def _compress_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, TraceSymbolTable]:
    normalize_gpu_stream_numbers(df)

    df.dropna(axis=0, subset=["dur", "cat"], inplace=True)
    df.drop(df[df["cat"] == "Trace"].index, inplace=True)

    columns_to_drop = {"ph", "id", "bp", "s"}.intersection(set(df.columns))
    df.drop(list(columns_to_drop), axis=1, inplace=True)

    # create a local symbol table
    local_symbol_table = TraceSymbolTable()
    symbols = set(df["cat"].unique()).union(set(df["name"].unique()))
    local_symbol_table.add_symbols(symbols)

    sym_index = local_symbol_table.get_sym_id_map()
    for col in ["cat", "name"]:
        df[col + "_id"] = df[col].apply(lambda s: sym_index[s]).astype(int)

    # data type downcast
    for col in df.columns:
        if df[col].dtype.kind == "i":
            df[col] = pd.to_numeric(df[col], errors="coerce", downcast="integer")

    return df, local_symbol_table


def _parse_trace_file(
    trace_file_path: str,
) -> Tuple[MetaData, pd.DataFrame, TraceSymbolTable]:
    meta, df, local_symbol_table = _parse_trace_dataframe_parquet(trace_file_path)

    _add_fwd_bwd_links(df)
    df = _transform_correlation_to_index(df, local_symbol_table)
    _add_iteration(df, local_symbol_table)
    df["end"] = df["ts"] + df["dur"]

    return meta, df, local_symbol_table


def _round_timestamps(df: pd.DataFrame) -> None:
    if df["ts"].dtype != np.dtype("float64"):
        return
    # Don't floor directly, first find the end
    df["end"] = df["ts"] + df["dur"]

    df["ts"] = df[~df["ts"].isnull()]["ts"].apply(lambda x: math.ceil(x))
    df["end"] = df[~df["end"].isnull()]["end"].apply(lambda x: math.floor(x))
    df["dur"] = df["end"] - df["ts"]


def _parse_trace_dataframe_parquet(
    trace_file_path: str,
) -> Tuple[MetaData, pd.DataFrame, TraceSymbolTable]:
    import time

    st = time.perf_counter()
    pq_file = pq.ParquetFile(trace_file_path)
    pq_metadata = pq_file.metadata.metadata
    kineto_metadata: Dict[str, Any] = {}
    if pq_metadata and b"kineto_metadata" in pq_metadata:
        meta_str = pq_metadata[b"kineto_metadata"].decode("utf-8")
        # The metadata is stored as a json string, it doesn't mean we're parsing json file
        kineto_metadata = json.loads(meta_str)
    else:
        kineto_metadata = {}

    # Explicitly use Arrow as the dataframe backend
    df = pq_file.read().to_pandas(types_mapper=pd.ArrowDtype)
    et = time.perf_counter()
    print(f"Time taken to read parquet file into dataframe: {et - st:.2f} seconds")

    local_symbol_table: TraceSymbolTable = TraceSymbolTable()

    _round_timestamps(df)

    df.reset_index(inplace=True)
    df["index"] = pd.to_numeric(df["index"], downcast="integer")
    print("processing {} records...".format(df.shape[0]))

    df, local_symbol_table = _compress_df(df)
    return kineto_metadata, df, local_symbol_table


# TODO:
# 1. align_all_ranks() requires the global minimum timestamp and substract it from all timestamps.
# This is a bad idea. It's also not involved the correctness of the temporal breakdown but without it
# the calculation of time could be wrong due to overflow, so we keep it for now, after all there is only
# one rank and the global minimum timestamp = local minimum timestamp.
# 2. filter_gpu_kernels_for_one_rank() could and should be implemented later, but for now it does not
# affect the analysis.
def _align_and_filter_trace(
    df: pd.DataFrame, symbol_table: TraceSymbolTable
) -> pd.DataFrame:
    _align_all_ranks(df)
    df = _filter_gpu_kernels_for_one_rank(df, symbol_table)
    return df


def _align_all_ranks(df: pd.DataFrame) -> None:
    min_ts = df["ts"].min()
    df["ts"] = df["ts"] - min_ts


def _filter_gpu_kernels_for_one_rank(
    trace_df: pd.DataFrame,
    symbol_table: TraceSymbolTable,
    include_last_profiler_step: bool = False,
) -> pd.DataFrame:
    cpu_kernels = _cpu_operator_filter(trace_df, symbol_table)
    gpu_kernels = _gpu_kernel_filter(trace_df, symbol_table)
    profiler_steps = [
        v for k, v in symbol_table.get_sym_id_map().items() if "ProfilerStep" in k
    ]
    if len(profiler_steps) == 0:
        return trace_df

    last_profiler_start = cpu_kernels[cpu_kernels["name_id"].isin(profiler_steps)][
        "ts"
    ].max()
    last_profiler_end = cpu_kernels[cpu_kernels["name_id"].isin(profiler_steps)][
        "end"
    ].max()

    cpu_kernels = (
        cpu_kernels[cpu_kernels["ts"] <= last_profiler_end]
        if include_last_profiler_step
        else cpu_kernels[cpu_kernels["ts"] < last_profiler_start]
    )
    filtered_gpu_kernels = gpu_kernels.merge(
        cpu_kernels["correlation"], on="correlation", how="inner"
    )
    return pd.concat([filtered_gpu_kernels, cpu_kernels], axis=0)


def _add_iteration(df: pd.DataFrame, symbol_table: TraceSymbolTable) -> pd.DataFrame:
    # Build profiler_step dataframe
    sym_tab = pd.Series(symbol_table.sym_table)
    profiler_step_ids = pd.Series(symbol_table.sym_index)
    profiler_step_ids = profiler_step_ids[
        profiler_step_ids.index.str.startswith("ProfilerStep")
    ].sort_index()

    profiler_steps = df.loc[
        df["name_id"].isin(profiler_step_ids.values), ["ts", "dur", "name_id"]
    ].copy()
    if profiler_steps.empty:
        df["iteration"] = -1
        return profiler_steps  # keep contract

    # Vectorized extraction of iteration numbers from symbol names
    profiler_steps["iter_idx"] = (
        profiler_steps["name_id"]
        .map(lambda i: re.search(r"\d+", sym_tab[i]).group(0))
        .astype(int)
    )

    # Construct bounds: [start, end)
    bounds = profiler_steps[["ts", "dur"]].to_numpy()
    bounds[:, 1] = bounds[:, 0] + bounds[:, 1]
    # iter_labels = profiler_steps["iter_str"].to_numpy()
    iter_ids = profiler_steps["iter_idx"].to_numpy()

    # Assign iterations for CPU events (stream < 0)
    cpu_mask = df["stream"] < 0
    ts_vals = df.loc[cpu_mask, "ts"].to_numpy()
    iter_result = np.full_like(ts_vals, fill_value=-1, dtype=object)

    for i, (start, end) in enumerate(bounds):
        mask = (ts_vals >= start) & (ts_vals < end)
        iter_result[mask] = iter_ids[i]

    df.loc[cpu_mask, "iteration"] = iter_result

    # Assign iterations for GPU events (stream > 0) using index_correlation
    gpu_mask = df["stream"] > 0
    corr_idx = df.loc[gpu_mask, "index_correlation"].to_numpy()
    # fallback to -1 for bad index
    iter_series = df["iteration"]
    valid_mask = (corr_idx > 0) & (corr_idx < len(df))
    gpu_result = np.full(len(corr_idx), -1, dtype=object)
    gpu_result[valid_mask] = iter_series.iloc[corr_idx[valid_mask]].to_numpy()
    df.loc[gpu_mask, "iteration"] = gpu_result

    df["iteration"] = pd.to_numeric(df["iteration"], downcast="integer")

    return profiler_steps


def _transform_correlation_to_index(
    df: pd.DataFrame, symbol_table: TraceSymbolTable
) -> pd.DataFrame:
    if "correlation" not in df.columns:
        return df

    # Initialize the index_correlaion to the fallback value first
    df["index_correlation"] = np.minimum(df["correlation"], 0)
    corr_df = df.loc[
        df["correlation"].ne(-1), ["index", "correlation", "stream", "name_id"]
    ]

    on_cpu = _cpu_operator_filter(corr_df, symbol_table)
    on_gpu = _gpu_kernel_filter(corr_df, symbol_table)

    # We only need to merge once.
    # index_x --> index_y will be cpu to gpu mapping
    # index_y --> index_x will be gpu to cpu mapping
    merged = on_cpu.merge(on_gpu, on="correlation", how="inner")

    df.loc[merged["index_x"], "index_correlation"] = merged["index_y"].values
    df.loc[merged["index_y"], "index_correlation"] = merged["index_x"].values
    df["index_correlation"] = pd.to_numeric(df["index_correlation"], downcast="integer")
    return df


def _filter_gpu_kernels_with_cuda_sync(
    df: pd.DataFrame, symbol_table: TraceSymbolTable
):
    event_sync_id = symbol_table.get_sym_id_map().get("Event Sync", -1)
    context_sync_id = symbol_table.get_sym_id_map().get("Context Sync", -1)
    return ((df["stream"] >= 0) & (df["correlation"] >= 0)) | df["name_id"].isin(
        [event_sync_id, context_sync_id]
    )


def _cpu_operator_filter(df: pd.DataFrame, symbol_table: TraceSymbolTable):
    if "stream" not in df.columns:
        return df

    return df.loc[~_filter_gpu_kernels_with_cuda_sync(df, symbol_table)]


def _gpu_kernel_filter(df: pd.DataFrame, symbol_table: TraceSymbolTable):
    if "stream" not in df.columns:
        return df

    return df.loc[_filter_gpu_kernels_with_cuda_sync(df, symbol_table)]


def _add_fwd_bwd_links(df: pd.DataFrame) -> None:
    if df.cat.eq("fwdbwd").sum() == 0:
        return

    # Initialize the fwdbwd columns to -1
    df["fwdbwd_index"] = -1
    df["fwdbwd"] = -1
    df["key"] = list(zip(df["ts"], df["tid"], df["pid"]))

    # Get the fwdbwd events. Only the "id" and "key" columns are needed for merging.
    df_fwdbwd = df.loc[df.cat.eq("fwdbwd")]
    df_fwdbwd_start = df_fwdbwd.query("ph == 's'")[["id", "key"]]
    df_fwdbwd_end = df_fwdbwd.query("ph == 'f' and bp == 'e'")[["id", "key"]]

    # The "index" column for the cpu event will be used when merging with the fwdbwd events.
    # The "key" column will be used for the merge.
    df_cpu = df.loc[df.cat.eq("cpu_op")][["index", "key"]]

    # Merge the fwdbwd events with the cpu events.
    # We will be using the index of last cpu event when multiple cpu events start from the same ts.
    df_fwdbwd_start_events = (
        df_fwdbwd_start.merge(df_cpu, how="inner", on="key")[["index", "id"]]
        .groupby("id")
        .max()
    )
    df_fwdbwd_end_events = (
        df_fwdbwd_end.merge(df_cpu, how="inner", on="key")[["index", "id"]]
        .groupby("id")
        .max()
    )
    if df_fwdbwd_start_events.empty or df_fwdbwd_end_events.empty:
        return

    # Merge the start and end events based on the "id" column.
    df_fwdbwd_merged = df_fwdbwd_start_events.merge(
        df_fwdbwd_end_events, how="inner", on="id", suffixes=("_start", "_end")
    )

    start_indices = df_fwdbwd_merged["index_start"]
    end_indices = df_fwdbwd_merged["index_end"]

    # Add the fwdbwd_index and fwdbwd columns to the dataframe.
    df.loc[start_indices, "fwdbwd_index"] = end_indices.values
    df.loc[end_indices, "fwdbwd_index"] = start_indices.values
    df.loc[start_indices, "fwdbwd"] = 0
    df.loc[end_indices, "fwdbwd"] = 1
    df.drop(columns=["key"], inplace=True)


def load_trace(trace_file_path: str):
    meta, df, local_symbol_table = _parse_trace_file(trace_file_path)
    df = _align_and_filter_trace(df, local_symbol_table)
    df = df.set_index("index", drop=False)
    df.index.names = [None]
    return meta, df, local_symbol_table


# ===== Trace analysis =====


def _merge_kernel_intervals(kernel_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge all kernel intervals in the given dataframe such that there are no overlapping.
    """
    kernel_df.sort_values(by="ts", inplace=True)
    kernel_df["end"] = kernel_df["ts"] + kernel_df["dur"]
    # Operators within the same group need to be merged together to form a larger interval.
    conds = (
        (kernel_df["ts"] > kernel_df["end"].shift().cummax())
        .fillna(False)
        .astype(np.int8)
    )
    kernel_df["group"] = conds.cumsum()

    kernel_df = (
        kernel_df.groupby("group", as_index=False)
        .agg({"ts": "min", "end": "max"})
        .drop(["group"], axis=1)
        .sort_values(by="ts")
    )
    return kernel_df


def _get_idle_time_for_kernels(kernels_df: pd.DataFrame) -> Tuple[int, int]:
    merged_kernels = _merge_kernel_intervals(kernels_df)
    kernel_time = merged_kernels.iloc[-1]["end"] - merged_kernels.iloc[0]["ts"]
    # differences of end - ts are commutative
    kernel_run_time = merged_kernels.end.sum() - merged_kernels.ts.sum()
    return kernel_time - kernel_run_time, kernel_time


def get_temporal_breakdown(trace_df: pd.DataFrame, rank: int) -> pd.DataFrame:
    """returns idle_time (us) , compute_time (us), non_compute_time (us), total_time (us)"""
    gpu_kernels = trace_df[trace_df["stream"].ne(-1)].copy()
    idle_time, kernel_time = _get_idle_time_for_kernels(gpu_kernels)

    NCCL_KERNEL_RE = r"^nccl.*Kernel"
    MEMORY_KERNEL_RE = r"^(?:Memcpy|Memset|dma)"
    NCCL_COMPUTE_KERNEL_RE = r"^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync"

    comm_kernels = gpu_kernels["name"].str.contains(NCCL_KERNEL_RE, na=False)
    memory_kernels = gpu_kernels["name"].str.contains(MEMORY_KERNEL_RE, na=False)
    compute_kernels = ~gpu_kernels["name"].str.contains(
        NCCL_COMPUTE_KERNEL_RE, na=False
    )

    conds = [
        comm_kernels,
        memory_kernels,
        compute_kernels,
    ]
    gpu_kernels["kernel_type"] = np.select(
        conds,
        [
            KernelType.COMMUNICATION.name,
            KernelType.MEMORY.name,
            KernelType.COMPUTATION.name,
        ],
        default=KernelType.OTHER.name,
    )

    # Isolate computation kernels and merge each one of them.
    comp_kernels = _merge_kernel_intervals(
        gpu_kernels[gpu_kernels["kernel_type"].eq(KernelType.COMPUTATION.name)].copy()
    )
    compute_time = comp_kernels.end.sum() - comp_kernels.ts.sum()
    non_compute_time = kernel_time - compute_time - idle_time

    assert idle_time <= kernel_time
    assert compute_time <= kernel_time
    assert non_compute_time >= 0

    result: Dict[str, List[float]] = defaultdict(list)
    result["rank"] = [rank]
    result["idle_time(us)"] = [idle_time]
    result["compute_time(us)"] = [compute_time]
    result["non_compute_time(us)"] = [non_compute_time]
    result["kernel_time(us)"] = kernel_time

    result_df = pd.DataFrame(result)
    result_df["idle_time"] = result_df["idle_time(us)"] / result_df["kernel_time(us)"]
    result_df["idle_time_pctg"] = round(100 * result_df["idle_time"], 2)
    result_df["compute_time"] = (
        result_df["compute_time(us)"] / result_df["kernel_time(us)"]
    )
    result_df["compute_time_pctg"] = round(100 * result_df["compute_time"], 2)
    result_df["non_compute_time"] = (
        result_df["non_compute_time(us)"] / result_df["kernel_time(us)"]
    )
    result_df["non_compute_time_pctg"] = round(100 * result_df["non_compute_time"], 2)

    return result_df[
        [
            "rank",
            "idle_time(us)",
            "compute_time(us)",
            "non_compute_time(us)",
            "kernel_time(us)",
            "idle_time_pctg",
            "compute_time_pctg",
            "non_compute_time_pctg",
        ]
    ]


def _get_gpu_kernel_type_time(
    gpu_kernels: pd.DataFrame, kernel_type_to_analysis: List[str]
) -> pd.DataFrame:
    overlap_kernel_type_df = pd.DataFrame(
        {
            "status": pd.Series(dtype="str"),
            "time": pd.Series(dtype="int"),
        }
    )

    kernel_t_mapping: Dict[str, int] = defaultdict(int)
    for idx, kernel_type in enumerate(kernel_type_to_analysis):
        value = 1 << idx
        kernel_t_mapping[kernel_type] = value
        kernel_t_df = _merge_kernel_intervals(
            gpu_kernels[gpu_kernels["kernel_type"].eq(kernel_type)].copy()
        )

        overlap_kernel_type_df = (
            pd.concat(
                [
                    overlap_kernel_type_df,
                    kernel_t_df.melt(var_name="status", value_name="time").replace(
                        {"ts": value, "end": -value}
                    ),
                ]
            )
            .sort_values(by="time")
            .reset_index(drop=True)
        )

    overlap_kernel_type_df["running"] = overlap_kernel_type_df["status"].cumsum()
    overlap_kernel_type_df["next_time"] = overlap_kernel_type_df["time"].shift(-1)
    unique_running = overlap_kernel_type_df["running"].unique()
    running_mapping: Dict[int, str] = defaultdict(str)
    for u_running in unique_running:
        if u_running > 0:
            for k_t, v_t in kernel_t_mapping.items():
                if u_running & v_t:
                    if u_running not in running_mapping:
                        running_mapping[u_running] = k_t
                    else:
                        # FIXME linter mismatch between fbcode and git T183519933
                        # fmt: off
                        running_mapping[u_running] = (
                            f"{running_mapping[u_running]} overlapping {k_t}"
                        )
                        # fmt: on

    overlap_kernel_type_df["kernel_type"] = ""
    overlap_kernel_type_df = overlap_kernel_type_df[
        overlap_kernel_type_df["running"] > 0
    ]
    for running in running_mapping:
        overlap_kernel_type_df.loc[
            overlap_kernel_type_df["running"].eq(running), "kernel_type"
        ] = running_mapping[running]
    overlap_kernel_type_df["dur"] = (
        overlap_kernel_type_df["next_time"] - overlap_kernel_type_df["time"]
    ).astype(int)

    overlap_kernel_type_df = overlap_kernel_type_df.groupby(by=["kernel_type"])[
        "dur"
    ].agg(["sum"])
    overlap_kernel_type_df.reset_index(inplace=True)

    return overlap_kernel_type_df


def get_gpu_kernel_breakdown_by_type(trace_df: pd.DataFrame, rank: int) -> pd.DataFrame:
    kernel_type_df = pd.DataFrame(
        {
            "kernel_type": pd.Series(dtype="str"),
            "sum": pd.Series(dtype="int"),
        }
    )
    kernel_type_to_analysis: List[str] = [
        KernelType.COMPUTATION.name,
        KernelType.COMMUNICATION.name,
        KernelType.MEMORY.name,
    ]

    gpu_kernels = trace_df[trace_df["stream"].ne(-1)].copy()

    NCCL_KERNEL_RE = r"^nccl.*Kernel"
    MEMORY_KERNEL_RE = r"^(?:Memcpy|Memset|dma)"
    NCCL_COMPUTE_KERNEL_RE = r"^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync"

    comm_kernels = gpu_kernels["name"].str.contains(NCCL_KERNEL_RE, na=False)
    memory_kernels = gpu_kernels["name"].str.contains(MEMORY_KERNEL_RE, na=False)
    compute_kernels = ~gpu_kernels["name"].str.contains(
        NCCL_COMPUTE_KERNEL_RE, na=False
    )

    conds = [
        comm_kernels,
        memory_kernels,
        compute_kernels,
    ]
    gpu_kernels["kernel_type"] = np.select(
        conds,
        [
            KernelType.COMMUNICATION.name,
            KernelType.MEMORY.name,
            KernelType.COMPUTATION.name,
        ],
        default=KernelType.OTHER.name,
    )

    kernel_type_df = pd.concat(
        [
            kernel_type_df,
            _get_gpu_kernel_type_time(gpu_kernels, kernel_type_to_analysis),
        ],
        ignore_index=True,
    )

    kernel_type_df = kernel_type_df.groupby(by=["kernel_type"])["sum"].agg(["sum"])
    kernel_type_df.reset_index(inplace=True)
    kernel_type_df.sort_values(
        by=["sum"], ignore_index=True, inplace=True, ascending=False
    )
    kernel_type_df["percentage"] = (
        kernel_type_df["sum"] / kernel_type_df["sum"].sum()
    ) * 100
    kernel_type_df = kernel_type_df.round({"percentage": 1})
    kernel_type_df["rank"] = int(rank)

    return kernel_type_df


def _aggr_gpu_kernel_time(
    gpu_kernel_time: pd.DataFrame,
    num_kernels: int = 10,
    duration_ratio: float = 0.8,
    allowlist_names: Optional[List[str]] = None,
) -> pd.DataFrame:
    gpu_kernel_time = gpu_kernel_time.groupby(by=["name"])["dur"].agg(
        ["sum", "max", "min", "mean", "std"]
    )
    gpu_kernel_time.reset_index(inplace=True)
    gpu_kernel_time = gpu_kernel_time.sort_values(
        by=["sum"], ascending=False, ignore_index=True
    )
    gpu_kernel_time.fillna({"std": 0}, inplace=True)

    # if there are more than num_kernels kernels, starting to aggregate kernels
    if gpu_kernel_time.shape[0] > num_kernels:
        if allowlist_names is not None:
            keep_idx = gpu_kernel_time.name.isin(allowlist_names)
        else:
            # always false
            keep_idx = gpu_kernel_time["sum"] < 0

        gpu_kernel_time["cumsum"] = gpu_kernel_time["sum"].cumsum()
        quantiles = gpu_kernel_time["cumsum"].quantile(duration_ratio)
        # FIXME linter mismatch between fbcode and git T183519933
        # fmt: off
        gpu_kernel_time.loc[~keep_idx & (gpu_kernel_time["cumsum"] > quantiles), "name"] = (
            "others"
        )
        # fmt: on
        gpu_kernel_time.loc[
            ~keep_idx & (gpu_kernel_time.index >= num_kernels), "name"
        ] = "others"
        gpu_kernel_time = gpu_kernel_time.groupby(by=["name"])["sum"].agg(
            ["sum", "max", "min", "mean", "std"]
        )
        gpu_kernel_time.reset_index(inplace=True)
        gpu_kernel_time.fillna({"std": 0}, inplace=True)

    return gpu_kernel_time


def get_gpu_kernel_breakdown_all_kernels(
    trace_df: pd.DataFrame, rank: int
) -> pd.DataFrame:
    duration_ratio = 0.8
    num_kernels = 10

    all_kernel_df = pd.DataFrame(
        {
            "name": pd.Series(dtype="str"),
            "sum": pd.Series(dtype="int"),
            "max": pd.Series(dtype="int"),
            "min": pd.Series(dtype="int"),
            "std": pd.Series(dtype="float"),
            "mean": pd.Series(dtype="int"),
            "kernel_type": pd.Series(dtype="str"),
            "rank": pd.Series(dtype="int"),
        }
    )
    kernel_type_to_analysis: List[str] = [
        KernelType.COMPUTATION.name,
        KernelType.COMMUNICATION.name,
        KernelType.MEMORY.name,
    ]
    gpu_kernels = trace_df[trace_df["stream"].ne(-1)].copy()
    NCCL_KERNEL_RE = r"^nccl.*Kernel"
    MEMORY_KERNEL_RE = r"^(?:Memcpy|Memset|dma)"
    NCCL_COMPUTE_KERNEL_RE = r"^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync"

    comm_kernels = gpu_kernels["name"].str.contains(NCCL_KERNEL_RE, na=False)
    memory_kernels = gpu_kernels["name"].str.contains(MEMORY_KERNEL_RE, na=False)
    compute_kernels = ~gpu_kernels["name"].str.contains(
        NCCL_COMPUTE_KERNEL_RE, na=False
    )

    conds = [
        comm_kernels,
        memory_kernels,
        compute_kernels,
    ]
    gpu_kernels["kernel_type"] = np.select(
        conds,
        [
            KernelType.COMMUNICATION.name,
            KernelType.MEMORY.name,
            KernelType.COMPUTATION.name,
        ],
        default=KernelType.OTHER.name,
    )

    for kernel_type in kernel_type_to_analysis:
        gpu_kernel_time = gpu_kernels[gpu_kernels["kernel_type"] == kernel_type]

        gpu_kernel_time = _aggr_gpu_kernel_time(
            gpu_kernel_time,
            duration_ratio=duration_ratio,
            num_kernels=num_kernels,
        )

        gpu_kernel_time["kernel_type"] = kernel_type
        gpu_kernel_time["rank"] = int(rank)
        all_kernel_df = pd.concat([all_kernel_df, gpu_kernel_time], ignore_index=True)

    all_kernel_df.sort_values(
        by=["kernel_type", "name"], ignore_index=True, inplace=True
    )
    all_kernel_df.rename(
        columns={
            "sum": "sum (us)",
            "mean": "mean (us)",
            "max": "max (us)",
            "min": "min (us)",
            "std": "stddev",
        },
        inplace=True,
    )

    return all_kernel_df


def _get_comm_comp_overlap_value(trace_df: pd.DataFrame) -> float:
    gpu_kernels = trace_df[trace_df["stream"].ne(-1)].copy()
    NCCL_KERNEL_RE = r"^nccl.*Kernel"
    MEMORY_KERNEL_RE = r"^(?:Memcpy|Memset|dma)"
    NCCL_COMPUTE_KERNEL_RE = r"^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync"

    comm_kernels = gpu_kernels["name"].str.contains(NCCL_KERNEL_RE, na=False)
    memory_kernels = gpu_kernels["name"].str.contains(MEMORY_KERNEL_RE, na=False)
    compute_kernels = ~gpu_kernels["name"].str.contains(
        NCCL_COMPUTE_KERNEL_RE, na=False
    )

    conds = [
        comm_kernels,
        memory_kernels,
        compute_kernels,
    ]
    gpu_kernels["kernel_type"] = np.select(
        conds,
        [
            KernelType.COMMUNICATION.name,
            KernelType.MEMORY.name,
            KernelType.COMPUTATION.name,
        ],
        default=KernelType.OTHER.name,
    )

    # Isolate communication and computation kernels and merge each one of them.
    comp_kernels = _merge_kernel_intervals(
        gpu_kernels[gpu_kernels["kernel_type"].eq(KernelType.COMPUTATION.name)].copy()
    )
    comm_kernels = _merge_kernel_intervals(
        gpu_kernels[gpu_kernels["kernel_type"].eq(KernelType.COMMUNICATION.name)].copy()
    )

    # When a communication kernel starts and ends, the cumulative status is changed by 1 and -1;
    # when a computation kernel starts and ends, the cumulative status is changed by 2 and -2.
    status_df = (
        pd.concat(
            [
                comm_kernels.melt(var_name="status", value_name="time").replace(
                    {"ts": 1, "end": -1}
                ),
                comp_kernels.melt(var_name="status", value_name="time").replace(
                    {"ts": 2, "end": -2}
                ),
            ]
        )
        .sort_values(by="time")
        .reset_index(drop=True)
    )
    status_df["running"] = status_df["status"].cumsum()
    # Time intervals when status is 3 indicate overlapping communication and computation kernels.
    overlap = status_df[status_df["running"].eq(3)]
    shifted_overlap = overlap.merge(
        status_df.shift(-1).dropna(), left_index=True, right_index=True
    )
    return (shifted_overlap["time_y"] - shifted_overlap["time_x"]).sum() / (
        comm_kernels["end"] - comm_kernels["ts"]
    ).sum()


def get_comm_comp_overlap(trace_df: pd.DataFrame, rank: int) -> pd.DataFrame:
    result: Dict[str, List[float]] = defaultdict(list)
    result["rank"].append(rank)
    result["comp_comm_overlap_ratio"].append(_get_comm_comp_overlap_value(trace_df))
    result_df = pd.DataFrame(result)
    result_df["comp_comm_overlap_pctg"] = round(
        100 * result_df["comp_comm_overlap_ratio"], 2
    )
    return result_df[["rank", "comp_comm_overlap_pctg"]]


def get_memory_bw_time_series(trace_df: pd.DataFrame, rank: int) -> pd.DataFrame:
    gpu_kernels = trace_df[trace_df["stream"].ne(-1)].copy()
    NCCL_KERNEL_RE = r"^nccl.*Kernel"
    MEMORY_KERNEL_RE = r"^(?:Memcpy|Memset|dma)"
    NCCL_COMPUTE_KERNEL_RE = r"^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync"

    comm_kernels = gpu_kernels["name"].str.contains(NCCL_KERNEL_RE, na=False)
    memory_kernels = gpu_kernels["name"].str.contains(MEMORY_KERNEL_RE, na=False)
    compute_kernels = ~gpu_kernels["name"].str.contains(
        NCCL_COMPUTE_KERNEL_RE, na=False
    )

    conds = [
        comm_kernels,
        memory_kernels,
        compute_kernels,
    ]
    gpu_kernels["kernel_type"] = np.select(
        conds,
        [
            KernelType.COMMUNICATION.name,
            KernelType.MEMORY.name,
            KernelType.COMPUTATION.name,
        ],
        default=KernelType.OTHER.name,
    )

    memcpy_kernels = gpu_kernels[
        gpu_kernels.kernel_type == KernelType.MEMORY.name
    ].copy()

    is_memset = memcpy_kernels["name"].str.startswith("Memset", na=False)
    is_memcpy_known = memcpy_kernels["name"].str.startswith("Memcpy", na=False)
    memcpy_sliced_names = memcpy_kernels["name"].str.slice(0, 11)

    conds = [
        is_memset,
        is_memcpy_known,
    ]
    memcpy_kernels["name"] = np.select(
        conds,
        ["Memset", memcpy_sliced_names],
        default="Memcpy Unknown",
    )

    # In case of 0 us duration events round it up to 1 us to avoid -ve values
    # see https://github.com/facebookresearch/HolisticTraceAnalysis/issues/20
    memcpy_kernels.loc[memcpy_kernels.dur == 0, ["dur"]] = 1

    membw_time_series_a = memcpy_kernels[["ts", "name", "pid", "memory_bw_gbps"]]
    membw_time_series_b = memcpy_kernels[
        ["ts", "name", "dur", "pid", "memory_bw_gbps"]
    ].copy()

    # The end events have timestamps = start timestamp + duration
    membw_time_series_b.ts = membw_time_series_b.ts + membw_time_series_b.dur
    membw_time_series_b.memory_bw_gbps = -membw_time_series_b.memory_bw_gbps

    membw_time_series = pd.concat(
        [
            membw_time_series_a,
            membw_time_series_b[["ts", "pid", "name", "memory_bw_gbps"]],
        ],
        ignore_index=True,
    ).sort_values(by="ts")

    result_df_list = []
    for _, membw_df in membw_time_series.groupby("name"):
        membw_df.memory_bw_gbps = membw_df.memory_bw_gbps.cumsum()
        result_df_list.append(membw_df)

    if len(result_df_list) == 0:
        return None

    result_df = pd.concat(result_df_list)[["ts", "pid", "name", "memory_bw_gbps"]]
    return result_df


def local_trace_analysis(
    trace_file: str,
    analysis_func: str,
):
    import time

    trace_file = os.path.abspath(trace_file)
    st = time.perf_counter()
    _, trace_df, _ = load_trace(trace_file)
    et = time.perf_counter()
    print(f"Time taken to load trace: {et - st:.2f} seconds")
    try:
        current_module = sys.modules[__name__]
        analysis_func = getattr(current_module, analysis_func)
        result = analysis_func(trace_df, 0)
    except AttributeError:
        print(f"Analysis function {analysis_func} not found")
        return None
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python hta_parquet.py <input_parquet_path> <analysis_func>")
        print(
            "Available functions: get_temporal_breakdown, get_gpu_kernel_breakdown_all_kernels, get_comm_comp_overlap, get_memory_bw_time_series"
        )
        sys.exit(1)
    trace_file = sys.argv[1]
    analysis_func = sys.argv[2]
    result_df = local_trace_analysis(trace_file, analysis_func)
    print(result_df)
