# Project Formulation Outline

Working title: ROFL (Realtime Online Feedback Loops)

## Users and Benefits

The target users of this monitoring tool are developers and users of large parallel scientific applications (they are often the same group).

The envisioned benefits are:

1. They will be able to observe all aspects of their application in real-time. This could be performance, load imbalance, block and message size distributions, message graphs and communication dependencies etc.

2. Launching an application with this tool will not have any common-case overhead, unless a monitoring task and probes are activated. Thus, a developer does not have to choose whether to run with the tool or not. You always run with the tool, and dynamically activate the analyses/probes you need. We only use resources when monitoring is activated, and we envision being able to do a lot of aggregation without affecting application performance.

3. Should a user want, they can also leverage the control path for online tuning and control decisions. They can expose certain parameters to our tool, and we will provide the ability to update them in an online and timestep-consistent manner.

## Input

1. Input from the user: control inputs on what monitoring to run, what probes to collect, and what tuning decisions to apply, SQL monitoring queries.

2. Input from the application: raw telemetry (per-timestep, per-rank, per-event).

3. Hardware resources: some nodes for monitoring tasks to run on.

## Output

1. An interface to orchestrate telemetry dataflows
2. User inputs consistently applied at the application (at the same timestep)
3. Aggregate statistics visualized at user dashboard

## Measures of success

1. Aggregation and control capabilities being realized, with evaluation at moderate scale (4096 cores).
2. A model of performance and  tradeoffs (aggregation volume vs application overhead, doing communication in a non-interfering way etc.)
3. A working example of these capabilities realized to provide insight into a real parallel app.

## Status Quo and Limitations

**Status quo on workload characterization** The best literature on workloads says that parallel applications spend more than 50% of their time in synchronization, communication etc. This gets worse with scale (few thousand ranks). Literature does not have a good understanding of why. Personal conversations strongly indicate that large parallel codes do not perform well and we do not understand why. A lot of these codes also tend to be behind export control barriers.

**Status quo on monitoring.** Existing monitoring tools either provide offline aggregates, or fine-grained traces. Fine-grained traces are absolutely massive in size, hard to analyze, sparingly used even at moderate scales. Using them at large scales is absolutely out of question.

An attempt was made in this direction using TAU+MRNet 10-15 years ago. That project was abandoned. It also didn't plan on doing things the way we are doing. I haven't looked into what went wrong.

**Status quo on fixing problems.** You analyze aggregate profiles. You modify code by adding MPI barriers around suspected problem areas, recompile it, run it, look at the aggregate profiles, hope to find something. This works only sometimes, and it always takes weeks.

## Insight: Strawman designs

**Collect telemetry offline**: this does not work for three reasons:

1. You don't know how much telemetry to collect apriori. Higher-level telemetry indicates problems, and then you collect low-level telemetry to rule out explanations until you progressively drill deeper and locate the root cause. This is naturally an online process.

2. Offline telemetry is slow and painful to analyze. It needs to be read again and joined and visualized. This requires a nontrivial amount of compute, I/O, and time. All this slows down iterations by 10-100X.

**Emit summarized telemetry from each rank**, say every 5 seconds, and display it. This also does not work. All work followed by a global sync is _one job_. Summaries on the basis of wallclock time show you the aggregate of multiple jobs. You need to see the story of a single job to locate problems --- this requires merging telemetry by timestep during aggregation.

**Configure a static aggregation job** You set up a monitoring system optimized to answer a specific question. This only works if the question is exactly the same question the user is interested in answering. The only reliable aggregation interface is one that is "turing-complete".

## Proposed Approach

The idea is to treat telemetry aggregation as a semi-realtime dataflow problem and to build an overlay that can execute such aggregation tasks. A "turing-complete" interface is achieved with a combination of SQL-based aggregation, a control network, and the principle of extensibility.

1. Available telemetry streams are visible to the user/controller as tables. No data is transferred until the user "installs" an aggregation query, and activates a number of probes.
2. When the user "installs" an aggregation query as SQL, it is parsed, and operators are placed along an aggregation overlay. The aggregation overlay consists of controller, k aggregators, and N application ranks. The bulk of the disruptive work is done on the aggregators, but some work (such as message batching) may be done on application ranks.
3. Raw dataframes are emitted on the leaf ranks every timestep. Operators are applied along the tree and simplified statistics are sent to the controller.

For simplicity, we only have one telemetry stream to begin with. All events will fit under this schema. Multiple schemas only come into picture if user wants to expose certain internal state (such as block distributions, placement insights etc.)

Basic stream:
```
timestamp, timestep, rank, event_id, event_val
```

### Implementation

- `Arrow` in-memory format for all data for efficient analytics.
- Mercury RPC library for portability across fabrics
- `datafusion` for query planning and execution (`duckdb` as backup)
- Lift code from `datafusion-ray` to convert `datafusion` plans to distributed ones
- Implement own executors/partitioners/shufflers on aggregator nodes

### Additional aspects

- Built using libfabric-based communication stack for HPC fabrics, with (hopefully, to be evaluated) super low jitter
- Tree-based overlays with carefully considered fan-in for 100,000s of cores
- Designed to be either synchronous or async, and consistent either way
- Source/sink abstraction: add as many profiling interfaces as you'd like

## Extensions

- Offload placement decisions to controller using the control path.
- Unified SQL-based in-situ analytics for particle data (also Arrow/row-based)
- Unified SQL-based in-situ analytics for all scientific data (bottleneck is the bridge between the SQL world and the HDF5 world. Can possibly be bridged. `arrow-zarr`, `TileDB` are some things to keep an eye out on).
- Offload part of the dataflow to accelerators (SmartNICs, switches etc.)
- Broadcast BPF code from the controller to tap into uprobes, kprobes, static tracepoints etc.