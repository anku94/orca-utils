You are helping with a user study for an agentic workflow with an observability framework called ORCA.

# Backgound

## Background: ORCA

ORCA: Observability with Real-time Control and Aggregation

ORCA is a TBON-style, multi-tier observability + control runtime for BSP applications: MPI ranks emit telemetry into named, fixed-schema Arrow streams via collectors (AddRow), and at each timestep boundary the collectors are drained into per-timestep "timestep dataframes" that become the unit of batching, analysis, and persistence; ranks synchronously push dataframe metadata plus a bulk handle, and aggregators asynchronously pull the actual serialized Arrow buffers via RDMA GET from RDMA-registered memory, using a timestep-ordered priority queue plus tightly controlled RDMA-read concurrency to avoid buffering/OOM and throughput collapse. 

On top of this data model, OrcaFlow provides a YAML-specified programming layer (SQL + optional map kernels) that compiles to tiered Apache DataFusion plans with operator pushdown toward MPI ranks and topology-aware sink placement, so ORCA can run in-situ reductions and/or persist (timestep, rank)-partitioned Parquet for fast post-mortems; a lightweight real-time path ingests aggregates into DuckDB at the controller and serves them via an embedded FlightSQL endpoint for live querying/dashboards. 

The system is implemented as ~40K LOC split between C++ (overlay bootstrap, collectors, control plane, sinks, tier runtime) and Rust (OrcaFlow planner/execution on DataFusion), connected by zero-copy FFI so timestep dataframes are handed to Rust without copying and results are returned to C++ for forwarding/persistence; the overlay bootstraps with an initial TCP handshake then transitions to Mercury RPCs over libfabric (RDMA if available, TCP otherwise) and supports multiple topologies (e.g., DIRECT and MPIREP). Finally, ORCA's steerability comes from a timestep-consistent control plane (TS2PC: timestep-linked two-phase commit with Δ-learning and tier "domains"), ensuring commands like probe/plan changes or tuning actions are acknowledged and then applied atomically at the same targeted timestep across ranks while remaining asynchronous to the application's collective domain.

## OrcaFlow Examples

Dir: /users/ankushj/repos/orca-workspace/orca-utils/orca-scripts/flows/
- kokkos_kernels.yaml
- mpiwait_onlycnt.yaml
- mpiwait_tracecnt.yaml

## Executing Commands

These variables should already be set in the environment (bash).

```bash
export PATH=/users/ankushj/repos/orca-workspace/orca-install/bin:$PATH
export ORCA_CTL_DASHHOST=h258.mon8.tablefs # TBON controller
```

Executing a command:
```bash
cmdrunner_main "<cmd>"
```

## Concepts

### Timestep Dataframe

A timestep dataframe contains all the data from a single BSP timestep (`ts`). If there are multiple schemas (MPI collectives, Kokkos etc), there will be one dataframe per schema.

The other relevant column is `swid` (sync window ID). Each collective call gets a monotonic swid. A timestep may contain multiple swids. swids divide all events into causally partitioned _sync windows_. Usually, you want to keep collecting MPI collective data regardless of the analysis, because it helps map swids to local time ranges etc.

You also want to preserve `ts` and `swid` in any aggregation flows you write. The flow is executed per-timestep, so you can assume that the referenced table there has only one `ts`, but many `swid`s.

### Controlling the application

The application runs a timestep in < 200ms. You want to pause it while you draft your flow, then resume it to run it. This allows you to debug errors etc. in peace.

You can also batch commands with 'cmd1; cmd2; cmd3' syntax. Do not do it initially, as you familiarize yourself with the workflow. Later on you may do it.

You can also do `pause; cmd; resume`, or just `cmd` without having to explicitly pause/resume. But do not do it unless user asks.

### Querying the trace

You can either query the trace directly by reading the Parquet files, or use OrcaReader. Do not modify this codebase as part of the agentic workflow. If it can use some features, suggest them to the user.

Orca Utils Root: `/users/ankushj/repos/orca-workspace/orca-utils`
- OrcaReader: `/orca-scripts/tau-analysis/orcareader`
- Usage example: `/orca-scripts/tau-analysis/orcareader_main.py`

# Agentic Workflow

## Warm-up 1

Note that this is a complex systems research prototype. Not all log messages may be complete or helpful. Some details somewhere may be outdated. Use best judgement.

Execute each step after user confirmation.

Working directory for all artifacts: `/users/ankushj/llm-thinkspace/20260110`

1. Run `status` to get info about the current application state
2. Application starts paused. Run `resume` to start execution, then run `pause`, and observe output.
3. Write a simple flow yaml to log per-probe counts (to see low/high-volume probes, also preserve ts and swid), emitted as parquet. Show to user.
4. Install it with `set-flow file <path/to/flow.yaml>`.
5. If it succeeds, run `resume` then `pause` back to back as separate commands. Note the timestep at which these commands take effect.
6. See if you can see the parquet output from the timestep ranges.
7. Disable unusually high volume probes with `disable-probe <schema name> <probe-name>` and capture counts again. The probes should not appear in the subsequent counts.

## Warm-up 2

We are interested in evaluating the performance of the code. It is an AMR code (Sedov Blast Wave 3D). AMR codes are known to have load imbalance problems. We want to characterize the nature of the problem.

All straggler problems manifest at synchronization points (collectives). Ranks that take less time at collectives are straggler ranks, and delay other ranks.

The first thing we want to do is understand the nature of collective durations. For each collective, if there's a gradual increase in the 0th %-ile, 1st, 10th, 50th %-ile durations: that is probably a load imbalance problem. If the 0th %-ile is 1ms and the 1st %-ile is 100ms, that indicates some tail behavior problem.

Execute a workflow to observe a few timesteps and then analyze their collective durations.

## Final Exercise

We want to debug a performance anomaly in an AMR code and locate the root cause of a straggler given the available data streams.

1. We want to monitor the workload and spot collectives with anomalous p100.
2. For those collectives, we want to see p0/p1 or some such number. If p1 is high, that means 1% of ranks are holding up 99% of them.
3. We want to devise a collection strategy to locate the root cause of the elevated times. The collection strategy should formulate reasonable hypotheses, write a flow to test them, and refine the hypothesis. At any given point, you should minimize the amount of data you are collecting.