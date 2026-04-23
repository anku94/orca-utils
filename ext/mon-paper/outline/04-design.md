# Section 4: Design

## Job
Answer the questions from section 3.4. Each subsection resolves one axis of the design space. Show how ORCA synthesizes ideas from multiple domains (OLAP, observability platforms, control systems) for BSP.

## Flow
S1: Data model (unit of analysis)
S2: Capture (collection without perturbation)
S3: Aggregation (distributed streaming analytics)
S4: Control (coordinated steering)
S5: Why not existing systems (justification)

## Subsection Outlines

**S1: Data Model - The Sync Window as Causal Unit**
*Answers: What's the unit of analysis for BSP telemetry?*

- **Key insight**: BSP causality resets at every global sync
  - Straggler in timestep T doesn't cause straggler in T+1
  - Barrier resets the slate
  - Sync window (swid) is natural partition key
- **The contract**: ORCA requires two columns: `swid` and `rank`
  - Everything else is flexible
  - Arbitrary schemas, multiple streams, application-specific metadata
- **Why columnar/Arrow**: Analytical efficiency
  - Parquet for persistence, Arrow for in-memory
  - Inherit OLAP ecosystem (already solved fast queries on big data)
- **Unit of analysis**: Timestep dataframe indexed by (swid, rank)
  - Example query: "distribution of barrier time across ranks" = GROUP BY swid, SORT BY rank
  - BSP provides clear completion signal: all ranks enter next collective
  - Generic event streams can't provide this guarantee

**S2: Capture - Efficient Collection Without Perturbation**
*Answers: How collect fine-grained data without drowning or slowing the application?*

- **Format choice**: Parquet over JSON/CSV
  - 50X parsing speedup
  - Comparable write cost after tuning (disable dictionary encoding)
  - Columnar from the start (skip text roundtrip)
- **Transport**: RDMA-based TBON
  - Network is faster than storage
  - Dedicated aggregator nodes (AGG) scale out ingestion
  - Data never hits disk on compute nodes
- **Timing discipline**: Drain once per timestep, at end, in PostTimestepAdvance()
  - Large batches, predictable timing, minimal jitter
  - Sync boundary is natural - already waiting
  - Example: 10MB/10K events in 1ms of 250ms timestep
- **In-situ partitioning**: TBON preserves (swid, rank) structure
  - Precedent: DeltaFS/CARP shuffling-based partitioning
  - Simpler for traces: preserve existing partitioning, don't shuffle

**S3: Aggregation - In-Situ Analytics Over Streams**
*Answers: What's the compute abstraction for distributed streaming analytics?*

- **The pipeline**:
  - Named streams of Arrow record batches (from SRC)
  - Per-partition processing in aggregators (AGG)
  - Cross-partition reduction in controller (CTL)
  - Sinks (real-time views, Parquet files)
- **SQL + MapReduce**:
  - SQL for declarative queries (DataFusion)
  - MapReduce escape hatches for complex operations
  - SQL updatable at runtime; Map kernels compiled in (for now)
- **Single-pass streaming, no shuffles**:
  - Static distributed query planning (no cost models)
  - Baked-in decision: streaming only
- **Pushdown strategy**:
  - Filter and aggregate as close to source as possible
  - Aggregators do bulk of per-partition work
  - Controller handles only cross-partition summaries
  - Data volume collapses before it leaves compute fabric
  - Like PySpark but single-pass
- **OrcaFlow**: Dataflow DSL
  - Streams and sinks
  - YAML-based specification
  - Enables view materialization inline

**S4: Control - Steerable Observability**
*Answers: How coordinate steering across 10K ranks?*

- **The problem**:
  - Asynchronous operator (human, dashboard, automation) needs to send commands
  - To synchronous application (BSP ranks in lock-step)
  - Commands must be applied consistently - all ranks at same timestep
- **TS2PC: Timestep-aware two-phase commit**:
  - Commands tagged with target timestep (ts + X)
  - Ranks accept if they haven't passed it, reject otherwise
  - Controller learns latency via delta tracking, adjusts automatically
  - Only one uncommitted txn at a time
- **Special handling for kPause/kResume**:
  - kPause creates synchronous pause state
  - Commands applied immediately (not tied to future timestep)
  - Prevents deadlock: paused system never reaches future timestep
- **Hierarchical broadcast and reduction**:
  - 2PC requests broadcast hierarchically via TBON
  - 2PC responses reduced: 99 ACKs + 1 NACK = 1 NACK
  - Enables controller to manage 100K ranks
- **Primitives**: Toggle streams, adjust filters, change aggregation policies, pause/resume
  - Composable - complex workflows from simple commands
  - Example: bootstrap uses [schema discovery → compute flow → resume]
- **The payoff**:
  - Start with coarse summaries
  - See anomaly in real-time
  - Drill down to specific ranks, streams, timesteps
  - Without restarting, without redeploying
  - Feedback loop closes

**S5: Why Not Existing Streaming Infrastructure?**
*Justifies why we built ORCA instead of using Kafka/Flink/etc.*

- **Generic event streaming systems don't fit**:
  - Event-oriented, not timestep-dataframe oriented
  - No BSP awareness: can't know when timestep data is complete
  - TCP-based event processing triggers syscall per event
  - Can't provide timestep completion guarantee that BSP enables
- **ORCA's Arrow + RDMA TBON is purpose-built**:
  - Arrow creates contiguous memory regions efficient for RDMA exchange
  - Tight control of backpressure, buffer recycling to minimize jitter
  - Batching all events into single message per timestep
  - Both retrieval efficiency and timestep dataframe semantics
- **Analytics architecture is novel**:
  - MapReduce/SQL pipeline distributed across TBON tiers
  - DataFusion makes this tractable
  - No one has done distributed query execution in observability TBON
- **Control plane capabilities**:
  - Coalescing ACKs, hierarchical broadcast
  - Timestep tracking and consistency (TS2PC)
  - Elevates ORCA beyond data collection to closed-loop system

## Key Narrative
Each subsection shows synthesis:
- S1: Database indexing strategy + BSP structure → sync window indexing
- S2: OLAP formats + HPC scale-out patterns → efficient capture
- S3: Streaming analytics + TBON → in-situ aggregation
- S4: Control theory + BSP structure → TS2PC
- S5: Why existing systems don't provide this (validates novelty)
