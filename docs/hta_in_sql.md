# How to express HTA functions using SQL

First, the schema of the trace table looks like below. I selected theese fields out of the original json as they are common for the basic HTA queries.
```
rank: Int32
cat: String
name: String
pid: Int64
tid: Int64
ts: Int64
dur: Int64
end: Int64
stream: Int64
correlation: Int64
bytes: Int64
memory_bw_gbps: Float64
wait_on_stream: Int64
wait_on_cuda_event_record_corr_id: Int64
```

Note that original HTA has bunch of preprocessing on this schema, such as building the symbol table for compression, adding extra fields etc. However, that is based on the assumption that the trace could contain multiple steps and thus `ProfilerStep` does not exist, making the preprocessing functions essentially no-ops.

Therefore, this fact simplifies our code as we don't need any preprocessing after reading from the parquet. We just directly run HTA functions on this table, which we're interested in if it's possible or easy to express them in standard SQL.

## Example: get_temporal_breakdown()
This HTA function calculates the breakdown of idle, non-compute, and compute time of all kernels. The output schema:
```
rank: Int32
idle_time(us): Int64
compute_time(us): Int64
non_compute_time(us): Int64
kernel_time(us): Int64
idle_time_pctg: Float64
compute_time_pctg: Float64
non_compute_time_pctg: Float64
```
So apparently the key is to categorize different kernels and retrieve their start and end times.

Logically we follow these steps:
1. Filter out kernel events from the trace table. This means cpu traces are ignored.
2. Merge kernels by the largest covering interval. Suppose we have a projection on the `ts` and `end` field:

    ```
    ts  end
    10  25
    15  30
    35  50
    40  55
    60  70
    ```
    We want the output to be this:
    ```
    ts  end
    10  30
    35  55
    60  70
    ```
3. Based on the merged gpu kernels, we can calculate the total kernel time and the actual kernel running time. The former is `end_last - ts_first = 70 - 10 = 60`, while the latter is `sum(end - ts) = 20 + 20 + 10 = 50`. Therefore, the idle time is `60 - 50 = 10`.
4. Further classify the kernels by regex matching the `name` field to filter out the compute kernels, and repeat the above merging procedure to get compute time.
5. With total time, idle time, and compute time, we can finally calculate the output table.

### How to write these steps in SQL?
This function does not need cpu traces, so we can do a filtering by `stream` first (non-gpu events have `stream = -1`).

The merging function can get a bit tricky. We could probably rewrite it in SQL, but it seems to be complex and involves multiple CTEs and advanced SQL primitives. Performance might not be good with SQL either: Our Polars approach just does on full scan.

Also note that in step 4 we classify events into `communication`, `memory`, `compute`, and `other`, but we only care about `compute` in this specific HTA function, which means we can just select those events only.

So a pseudo OrcaFlow could be like this:
```
#UDAF: merge_kernel_intervals()

HTA SQL:
  gpu_kernels:
    select * from kineto_trace where stream != -1;
  
  merged_gpu_kernels:
    select merge_kernel_intervals(*) from gpu_kernels;
  
  compute_kernels:
    select * from gpu_kernels where not regexp_matches('name', "^(?:nccl.*Kernel)|.*(?:Memcpy|Memset)|.*Sync");
  
  merged_compute_kernels:
    select merge_kernel_intervals(*) from compute_kernels;
  
  temporal_breakdown:
    with
    idle_and_kernel_time as (
      select
        (max(end) - min(ts)) as kernel_time,
        (max(end) - min(ts)) - sum(end - ts) as idle_time
      from merged_gpu_kernels
    ),
    compute_time as (
      select
        sum(end - ts) as compute_time
      from merged_compute_kernels
    ),
    combined_metrics as (
      select
        a.idle_time,
        a.kernel_time,
        b.compute_time,
        a.kernel_time - a.idle_time - b.compute_time as non_compute_time
      from idle_and_kernel_time a
      cross join compute_time b
    ),
    select
      idle_time as "idle_time(us)",
      compute_time as "compute_time(us)",
      non_compute_time as "non_compute_time(us)",
      kernel_time as "kernel_time(us)",
      idle_time / kernel_time as idle_time_pctg,
      compute_time / kernel_time as compute_time_pctg,
      non_compute_time / kernel_time as non_compute_time_pctg
    from combined_metrics;
```

## Example: get_comm_comp_overlap()
The output of this function is simply a single percentage of computation communication overlap.

The key procedure is `get_comm_comp_overlap_value()`, which internally calls `merge_kernel_intervals()` two times as well as many complicated dataframe manipulations such as `concat`, `melt`, `merge`, `cumsum`, `shift` etc. These are hard to express with SQL, so we could wrap this whole function into a dedicated UDAF which takes in as input the whole table and returns a float. Other things are similar.

Pseudo OrcaFlow:
```
#UDAF: get_comm_comp_overlap_value()

HTA SQL:
  gpu_kernels:
    select * from kineto_trace where stream != -1;

  comm_comp_overlap:
    select get_comm_comp_overlap_value(*) from gpu_kernels;
```

## Conclusion
Many HTA functions follow the above way to calculate the output table. The core logics are too complex to express in standard SQL, while also could lead to bad performance if doing in that way. It's probably easier, cleaner, and more efficient to wrap the core logics into an UDAF and write SQL on the intermediate tables from those UDAFs.