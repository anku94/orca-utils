# ORCA

ORCA: Observability with Real-time Control and Aggregation

ORCA is a TBON-style, multi-tier observability + control runtime for BSP applications: MPI ranks emit telemetry into named, fixed-schema Arrow streams via collectors (AddRow), and at each timestep boundary the collectors are drained into per-timestep "timestep dataframes" that become the unit of batching, analysis, and persistence; ranks synchronously push dataframe metadata plus a bulk handle, and aggregators asynchronously pull the actual serialized Arrow buffers via RDMA GET from RDMA-registered memory, using a timestep-ordered priority queue plus tightly controlled RDMA-read concurrency to avoid buffering/OOM and throughput collapse.

On top of this data model, OrcaFlow provides a YAML-specified programming layer (SQL + optional map kernels) that compiles to tiered Apache DataFusion plans with operator pushdown toward MPI ranks and topology-aware sink placement, so ORCA can run in-situ reductions and/or persist (timestep, rank)-partitioned Parquet for fast post-mortems; a lightweight real-time path ingests aggregates into DuckDB at the controller and serves them via an embedded FlightSQL endpoint for live querying/dashboards.

The system is implemented as ~40K LOC split between C++ (overlay bootstrap, collectors, control plane, sinks, tier runtime) and Rust (OrcaFlow planner/execution on DataFusion), connected by zero-copy FFI so timestep dataframes are handed to Rust without copying and results are returned to C++ for forwarding/persistence; the overlay bootstraps with an initial TCP handshake then transitions to Mercury RPCs over libfabric (RDMA if available, TCP otherwise) and supports multiple topologies (e.g., DIRECT and MPIREP). Finally, ORCA's steerability comes from a timestep-consistent control plane (TS2PC: timestep-linked two-phase commit with Δ-learning and tier "domains"), ensuring commands like probe/plan changes or tuning actions are acknowledged and then applied atomically at the same targeted timestep across ranks while remaining asynchronous to the application's collective domain.

## Key Concepts

### Timestep Dataframe
A timestep dataframe contains all the data from a single BSP timestep (`ts`). If there are multiple schemas (MPI collectives, Kokkos etc), there will be one dataframe per schema.

The other relevant column is `swid` (sync window ID). Each collective call gets a monotonic swid. A timestep may contain multiple swids. swids divide all events into causally partitioned _sync windows_.

### Event Base Schema
All events share: `{timestep, swid, rank, ts_ns}` + type-specific fields. Probes are lazy-discovered via XXHash64, dynamically enable/disable via control plane.

### Current Instrumentation
Source: `orca/src/trace/` (PMPI hooks) and `orca/src/client/` (client-side tracers).

- MPI collective hooks (18 collectives) — TIMEIT macro + LogCollective
- MPI P2P hooks (20+ ops) — captures src/dst/tag/bytes
- Kokkos profiling hooks — stack-based nesting with depth tracking
- Schema tracers — macro-driven Arrow schema collectors (CollectiveEvent, KokkosEvent, MsgEvent)

## Source Layout
- `orca/src/client/` — client library (`liborcaclient.so`), linked by applications
- `orca/src/client-common/` — shared object library used by both client and ORCA (logging, buf_pool, schema_tracer_base)
- `orca/src/common/` — ORCA-internal utilities (logger, options, context, arrow utils)
- `orca/src/core/` — ORCA core (aggregator, controller, MPI rank, serdes, twopc)
- `orca/src/trace/` — ORCA-internal trace writer
- `orca/src/flow/` — OrcaFlow execution engine
- `orca/src/overlay/` — Mercury/libfabric overlay network
- `orca/src/rsflow/` — Rust DataFusion planner (built via cargo, linked via CXX FFI)
- `orca/include/orca/` — public installed headers
- `orca/tools/` — binaries (controller, aggregator, mpirank, cmdrunner, examples)
