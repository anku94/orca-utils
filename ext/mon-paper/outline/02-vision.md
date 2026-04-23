# Section 3: What Could That Look Like?

## Job
Develop the vision of "always-on programmable observability" - what it means in practice, what it could enable, what pieces exist to build it, what's hard, and what questions the design must answer. This is the bridge from motivation to design.

## Flow
S1: Unpack the concept (what does it mean?)
S2: What this could enable (the payoff)
S3: What pieces exist (the opportunity)
S4: What's hard / what's missing (the challenges)
S5: Design questions (bridge to section 4)

## Subsection Outlines

**S1: Unpacking the Concept**
- Section 2 concluded: "need always-on programmable production observability"
- What does that actually mean in practice?
- **Always-on**:
  - Not "turn on tracing when you suspect a problem"
  - Production-viable overhead continuously
  - Ready to observe at all times
- **Programmable**:
  - Schemas: inject application-specific metadata (block IDs, kernel info)
  - Analyses: custom queries, not just canned dashboards
  - What to collect: which streams, which layers
  - When to collect: dynamic enabling/disabling
  - How to aggregate: from summaries to raw events
- **The operating model**:
  - Common case: Coarse monitoring, low overhead
  - Anomaly detected: Drill down dynamically
    - Specific ranks, specific timesteps, specific streams
    - Refine resolution based on what you observe
  - No restart, no redeploy, same job run

**S2: What This Could Enable**
- Recall AMR runs 1-90:
  - Each iteration: full job run + post-hoc analysis
  - Took months to localize root cause
- **With real-time visibility**:
  - Run 1: Start with coarse monitoring
  - See anomaly (some timesteps take 100ms extra)
  - Drill down immediately: enable collective-level telemetry
  - See which ranks are slow
  - Drill down again: enable task-level telemetry for those ranks
  - See which functions
  - Add eBPF probes for MPI internals
  - All in same job run
- **Collapse feedback loop**: Months to minutes
- **Dynamic resolution**: Start coarse, refine based on observations
- **Real-time intervention**: Potentially adjust job parameters, skip bad nodes

**S3: What Pieces Exist**
Show that the building blocks are available - this is an opportune time to build this.

- **OLAP maturity**:
  - Arrow/Parquet/DataFusion are production-ready (not research prototypes)
  - We saw 50X parsing speedup with columnar formats in AMR work
  - SQL at scale, streaming primitives available
  - Vectorized execution, compression, efficient formats
  - Rich ecosystem (pandas/polars compatible)

- **Programmable instrumentation concepts**:
  - eBPF showed dynamic control works
  - Attach/detach probes based on observed state
  - Control what gets captured, when
  - Essential for AMR drill-down (runs 8-90)
  - Proven at single-node scale

- **In-memory analytics efficiency**:
  - Needle-in-haystack: 1M MPI_Wait calls, find anomalous ones
  - If data in memory in Arrow: cheap to filter
  - If move over network → compress → write → read → decompress → filter: expensive
  - Data movement dominates cost
  - Need to sift where data lives (in-situ)

- **Scale inflection point** (why now):
  - Exascale systems operational, LLM training at 10K+ GPU scale
  - Efficiency matters more than ever (cost, energy)
  - Workloads long-running enough that adaptive observability pays off

**S4: What's Hard / What's Missing**
Identify the gaps that need to be solved (not complaining, but showing what needs synthesis).

- **Cluster-scale coordination**:
  - eBPF works great for single process/node
  - BSP workloads span 10K nodes
  - How to coordinate steering across thousands of ranks?
  - Commands must be applied consistently (all ranks at same logical point)
  - Need distributed control mechanism

- **Streaming not offline**:
  - OLAP tools (Parquet, DataFusion) designed for offline batch analytics
  - We need real-time streaming
  - Data generated continuously, views materialized on-the-fly
  - Can't wait to write full dataset then query

- **In-situ analytics at scale**:
  - Can't move all data to central location (too expensive, see S3)
  - Need distributed streaming analytics
  - Pushdown: filter/aggregate close to source
  - Scale-out: can't bottleneck on single node
  - Need architecture that handles 10K data sources

- **The workflow absurdity**:
  - Current: Binary instrumentation data → serialize to CSV/JSON → parse into columnar (pandas/dask)
  - Why roundtrip through text formats?
  - Why not columnar from the start?
  - Need to integrate columnar formats into collection pipeline

- **The temporal gap**:
  - Post-hoc analysis: by the time you see it, moment is gone
  - Can't distinguish transient from structural issues
  - Can't intervene in real-time
  - Need to materialize views inline, while job runs

**S5: Design Questions**
Bridge to section 4 by posing explicit questions the design must answer.

- We've established:
  - What we want (always-on programmable observability)
  - What it could enable (collapse feedback loop)
  - What pieces exist (OLAP, eBPF concepts, in-memory analytics)
  - What's missing (cluster-scale, streaming, in-situ)

- This raises specific design questions:

  - **Data model**: What's the unit of analysis for BSP telemetry?
    - Generic event streams? Request-based traces? Something else?
    - What's the natural partitioning key?

  - **Compute**: What's the abstraction for distributed streaming analytics?
    - How to express views? SQL? MapReduce? Custom DSL?
    - How to execute across 10K sources with pushdown?

  - **Control**: How to coordinate steering across 10K ranks?
    - How to send commands consistently?
    - How to handle asynchrony (operator vs application)?
    - What primitives to expose?

  - **Overhead**: How to realize this without perturbing the application?
    - Collection overhead? Transport cost? Analysis cost?
    - How to minimize jitter in critical path?

- Section 4 answers each of these questions

## Key Transitions
- From Section 2: "We need always-on programmable observability" → "What does that mean?"
- From S2 to S3: "This would be powerful, and we have pieces to build it"
- From S3 to S4: "But there are gaps that need solving"
- From S4 to S5: "These gaps lead to specific design questions"
- To Section 4: "Here's how we answer each question"
