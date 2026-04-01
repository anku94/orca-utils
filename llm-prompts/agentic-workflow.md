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

# Agentic Workflow

## Warm-up

Note that this is a complex systems research prototype. Not all log messages may be complete or helpful. Some details somewhere may be outdated. Use best judgement.

Execute each step after user confirmation.

Working directory for all artifacts: `/users/ankushj/llm-thinkspace/<YYYMMDD>-<AGENT>` (agent: codex/claude/gemini).

1. Run `status` to get info about the current application state
2. Application starts paused. Run `resume` to start execution, then run `pause`, and observe output.
3. Write a simple flow yaml to log per-probe counts (to see low/high-volume probes, also preserve ts and swid), emitted as parquet. Show to user.
4. Install it with `set-flow file <path/to/flow.yaml>`.
5. If it succeeds, run `resume` then `pause` back to back as separate commands. Note the timestep at which these commands take effect.
6. See if you can see the parquet output from the timestep ranges.
7. Disable unusually high volume probes with `disable-probe <schema name> <probe-name>` and capture counts again. The probes should not appear in the subsequent counts.

## Final Exercise

You are given a running AMR code that presents a performance anomaly. The anomaly appears on a few ranks at random and holds up the rest of them. It does not seem to be correlated with any particular rank or node, but appears randomly.

Your task is to infer as much as you can about the anomaly from the available data streams. Some points to keep in mind:

1. Collect `mpi_collectives` all the time. No need to use complicated percentiles. These will help you track the bad `swids`.

2. Remember that `swid` is a monotonic counter: it is a proxy for logical time. You can only collect more data for future `swids`, the simulation is progressing forward and you can not go back and collect data for past `swids`.

3. You want to collect as little data as possible, but do not use complex aggregations or joins. Use simple filters. Be wary of inducing anomalies with reckless raw event capture, but 10,000s of events/sec is not a problem.

4. Remember that collective times are inversely proportional to stragglers. If one rank takes an extra 50ms, its collective duration will be zero and the others' collective time will be 50ms+. Lower collective times are the soruces of stragglers. You are not debugging elevated collective times but elevated times for events preceding the collective.

5. Remember that the anomalies you are looking for do not appear reliably. You can not assume that every timestep will have the anomaly or anything like that. Let the simulation run for a few hundred timesteps. Isolate interesting areas from a decent dataset. Then focus on the most unusual patterns.

6. Once you have some data, you can use this codebase to correlate application stats with what you see: `/l0/orcaroot/orca-umbrella/build/phoebus-prefix/src/phoebus/external/parthenon/src`

7. Run the application for about 30 seconds at a time to collect data.

8. Try to produce a complete explanation of the anomaly.

9. Maintain an audit trail of decisions. Number each flow you write, like '0-<flow-name>' and so on.

To query a stream, you can use this pattern:

```python
import polars as pl

stream_name = "mpi_collectives"
glob_patt = f"{parquet_root}/{stream_name}/**/*.parquet"
df = (
    pl.scan_parquet(glob_patt, parallel="columns")
    # more lazy filters here
    .collect()
)
```