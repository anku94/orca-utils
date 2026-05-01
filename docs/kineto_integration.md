# Kineto Integration Notes

Refer to [kineto_walk_through](./kineto_walk_through.pdf) for a context of how kineto is structured.

## Updates 08/28/2025
The arrow logger is working now. This has been tested by writing arrow to parquet and running `hta_parquet.py` on parquet files.
I also compared the HTA results for the parquet files vs. json files. They show similar breakdown numbers, which is a good indication that the new logics are "correct" in terms of HTA results. Below are some HTA numbers (temporal breakdown) on json and parquet for training step 10-14.
```
# json
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0          478.0            6119.0                 680.0           7277.0            6.57              84.09                   9.34
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0          864.0            3757.0                 730.0           5351.0           16.15              70.21                  13.64
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0          481.0            4297.0                 725.0           5503.0            8.74              78.08                  13.17
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0          826.0            3812.0                 697.0           5335.0           15.48              71.45                  13.06
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0          838.0            3820.0                 710.0           5368.0           15.61              71.16                  13.23
```
```
# parquet
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0            928              3756                   744             5428            17.1               69.2                  13.71
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0            477              3751                   698             4926            9.68              76.15                  14.17
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0            465              6082                   691             7238            6.42              84.03                   9.55
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0            885              3758                   640             5283           16.75              71.13                  12.11
rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0            776              3824                   725             5325           14.57              71.81                  13.62
```

### Implementation notes
Currently the arrow table has these fields:
```
cat                                  string[pyarrow]
name                                 string[pyarrow]
pid                                   int64[pyarrow]
tid                                   int64[pyarrow]
ts                                    int64[pyarrow]
dur                                   int64[pyarrow]
end                                   int64[pyarrow]
stream                                int64[pyarrow]
correlation                           int64[pyarrow]
bytes                                 int64[pyarrow]
memory_bw_gbps                       double[pyarrow]
wait_on_stream                        int64[pyarrow]
wait_on_cuda_event_record_corr_id     int64[pyarrow]
```
I tried to do more preprocessing in the generation time as much as possible. For example, HTA will round the timestamps and durations, then generate the 'end' column, which does not originally exist in the json, but I do these when generating the arrow table in the first place, so it can save some HTA logics overhead when we do real time analysis later on.

There are also some room for optimizations:
- The arrow logger mostly copies json logger's code, but it turns out many trace records that appear in json are not used by HTA (they're dropped anyways). I leave those functions blank, though a better approach is not even calling those functions because before calling them there are some other logics involved. This is NOT a big deal though, because we already found trace preprocessing incurs minimal overhead and optimizing further would not benefit much.
- The HTA part could be further optimized when changing the format from json to parquet without changing analysis results, especially the traces are now within a single step, which breaks HTA's assumptions a little bit, giving us opportunities of removing some code. However, this requires a deeper understanding of what HTA's code is doing (previously I just copied them with a relatively superficial knowledge), and should be better done when porting the python code into rust OrcaFlow.

Note to myself: The 'ProfilerStep' record disappears in our per-step traces. It's accessed by HTA when it was doing some filtering, but it seems not affect the result. Should take a look at some point.

## On generating Arrow tables
Our goal here is to **find the minimum set of fields that are shared by all analysis**.
As an optimization, we can also do some more preprocessing in this phase if that is general in the subsequent HTA analysis, such as type coercions. But these things are a bit involved so let's just start from a working pipeline first.

From the current script that converts json to parquet, we know these columns will be dropped:
1. 'ph', 'id', 'bp', 's'
2. in 'args': "input_dims", "input_type", "input_strides", "external_id". The rests that are in 'args' are extracted out, and 'args' is deleted

These rows are dropped:
1. those whose 'cat' is 'Trace'
2. those whose 'dur' or 'cat' is N/A

The Chrome logger also converts the absolute time to relative time from Chrome's base time. This seems unnecessary in HTA analysis.

## Updates 08/21/2025
Bunch of improvements:

1. Added a task queue in libkineto so don't need to create a thread in each step.
2. Added CLI options in Dynolog, such as profile knobs including thread pool size and flush interval (i.e. #steps between consecutive flushes). Also the `continuous flush` mode is now enabled by dynolog, not by env variable as this is cleaner.
3. Bunch of minor cleanups.

## Updates 08/20/2025
The async kineto pipeline is now working, emitting cpu and gpu traces for each step to different json files.

<!-- To run it, add the `KINETO_ORCA` env variable along with `KINETO_USE_DAEMON` when running the pytorch program, like below:

```
KINETO_ORCA=1 KINETO_LOG_LEVEL=0 KINETO_USE_DAEMON=1 python train.py
```
This puts kineto in daemon mode. To trigger tracing use dynolog:
```
dynolog --enable_ipc_monitor
# In another terminal
dyno gputrace --log-file /mnt/tmp/trace.json --profile-memory --iterations 10
```
Then the per-step traces will be saved to /mnt/tmp.
```
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:43 kineto_trace_step_14.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_15.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_16.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_17.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_18.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_19.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_20.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_21.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_22.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_23.json
-rw-r--r-- 1 shengj2 NetSketch  27M Aug 20 00:49 kineto_trace_step_24.json
``` -->

A few things: 1) The path where trace files get written to does not respect the path specified in dynolog, it's hardcoded for now; 2) No queueing for processing tasks yet; 3) Haven't directly write traces to arrow.

## Usage
Relevant repos in the modified kineto pipeline are hosted in my personal github for now, all in the `orca` branch:
- Dynolog: https://github.com/jiangxiaosheng/dynolog.git
- Kineto: https://github.com/jiangxiaosheng/kineto.git
- PyTorch: https://github.com/jiangxiaosheng/pytorch.git

Run the pytorch program as usual, except setting `KINETO_DAEMON=1`:
```
KINETO_USE_DAEMON=1 python train.py
```
Then use dynolog to trigger tracing at runtime:
```
$ dynolog --enable_ipc_monitor
# In another terminal
$ dyno gputrace --log-file /mnt/tmp/kineto_trace --profile-memory --iterations 10 --continuous-flush --thread-pool-size 4 --flush-interval 1
Kineto config =
ACTIVITIES_LOG_FILE=/mnt/tmp/kineto_trace
PROFILE_START_ITERATION=0
PROFILE_START_ITERATION_ROUNDUP=1
ACTIVITIES_ITERATIONS=10
PROFILE_REPORT_INPUT_SHAPES=false
PROFILE_PROFILE_MEMORY=true
PROFILE_WITH_STACK=false
PROFILE_WITH_FLOPS=false
PROFILE_WITH_MODULES=false
PROFILE_CONTINUOUS_FLUSH=true
PROFILE_THREAD_POOL_SIZE=4
PROFILE_FLUSH_INTERVAL=1
response length = 147
response = {"activityProfilersBusy":0,"activityProfilersTriggered":[1777855],"eventProfilersBusy":0,"eventProfilersTriggered":[],"processesMatched":[1777855]}
Matched 1 processes
Trace output files will be written to:
    /mnt/tmp/kineto_trace
```
The traces will be written to the specified directory in different json files (the prefix `1777855` is the pid to differentiate tracing runs):
```
$ ll /mnt/tmp/kineto_trace
total 263M
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:55 1777855_step_14.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_15.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_16.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_17.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_18.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_19.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_20.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_21.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_22.json
-rw-r--r-- 1 shengj2 NetSketch 27M Aug 21 01:56 1777855_step_23.json
```


## PyTorch Kineto Client Callbacks
The way PyTorch Kineto interacts with Libkineto is by registering Libkineto's client callbacks, particularly `start()` and `stop()`, which are called when Libkineto starts and stops tracing in the daemon mode.

Specifically, PyTorch side's `enableProfiler()` gets called in the `start()` callback and `disableProfiler()` gets called in `stop()`. These are the two key functions that are related to PyTorch side's CPU tracing etc. We will dive into them in below.

## Important classes
`KinetoThreadLocalState`: The key class that manages CPU tracer's operations. It's thread local in the frontend mode and is shared/global in the daemon mode.

`RecordQueue`: Used to retrieve captured CPU traces. It itself does not store the traces, which are actually done by `ThreadLocalSubqueue`, but instead it acts more like a manager. It can also get Python traces, but only if `with_stack` profiling option is enabled. It's a member of `KinetoThreadLocalState`.

`ThreadLocalSubqueue`: The actual class that captures CPU traces. It has various kinds of events, such as `op_events_` which denotes tensor operations in ATen, `kwinputs_` and `inputs_outputs_` if the user wants to capture the input shapes, `allocations_` for memory operations, `py_calls_` for python stacks etc.

`Result`: A wrapper of the raw events. The retrieved events from the `ThreadLocalSubqueue` are saved to a vector of `Result` before further processing.

`activity_t`: Basically an equivalent of `Result` that Libkineto speaks. `Result` will be used to construct a corresponding `activity_t` when sending to Libkineto.

## How does Kineto capture CPU traces?
When `enableProfiler()` gets called, Kineto creates a global `KinetoThreadLocalState` and sets profiling callbacks (on function enter and exit) for ATen functions, which will push the event to the `ThreadLocalSubqueue`.

When Kineto needs to retrieve the captured events in `disableProfiler()`, it removes the previously registered profiling callbacks and drains various events from the `ThreadLocalSubqueue`. It then processes the events and calls `addKinetoEvents()` to pass them to Libkineto. After that, it clears relevant data structures.

## What modifications do we need?
1. First of all, we don't want to unregister the profiling callbacks when retrieving the events, although the overhead of callback registration seems not much?
2. We need to make the trace processing logic independent, i.e. we will have many processing threads running simultaneously and they can't intefere with each other. This is similar to what we did in Libkineto by moving the relevant data structures to a snapshot so that the processing logic only cares about local data. We don't need to clear any data when it's done for the same reason.
3. To implement 2, we need to identify which data structures are needed and accessed during the processing logic.

## How am I planning to approach this?
The below is the pseudo workflow of how I planned to do the hack.

Original workflow of retrieving CPU traces:
```
disableProfiler() (entry point)
-> RecordQueue::getRecords()
->-> (1) drain various kinds of raw events from the `ThreadLocalSubqueue` queue and save them in a vector of `Result`.
->-> (2) call addKinetoEvents() to pass the traces to Libkineto.
->-> (3) process the traces. e.g. set up relative orders, parentness, etc.

-> materializeOpEvents(): further loop through the traces and make some parsing there, i.e. setting up relevant metadata of the trace records.
```

Note that it seems `addKinetoEvents()` should be the last thing and processing CPU traces after passing them to Libkineto doesn't make sense, but since there are pointers to the `activity_t` events from `Result`, the `activity_t` saw by Libkineto will still get modified in functions like `materializeOpEvents()`, which essentially are adding certain matadata to the trace records.

The new workflow:
```
disableProfiler() (entry point)
-> (1) makeSnapshot(): New added function. Create a snapshot struct, which saves the raw events from the queue and contains relevant data structures needed to process the events.
-> (2) addKinetoEventsWithCallback(): New added function. Besides addKinetoEvents(), it passes a lambda function as a callback to Libkineto, which encapsulates all trace processing logics against the snapshot.
```

The key ideas here are:

1. Use the snapshot mechanism to decouple the trace processing logic from the actual PyTorch class so that they can be executed simultaneously.
2. Since the trace processing happens in Libkineto's context, we need to wrap up related functions into a single callback and pass it to Libkineto along with the snapshot, so that it can be executed in the thread launched by Libkineto without blocking the main thread.

Note the above is a reflection a rough roadmap. Subtle things might change while I keep implementing it.