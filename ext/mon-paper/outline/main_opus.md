## 2. Background & Motivation

**Job:** Establish the problem domain and why current approaches fail.

### 2.1 The BSP Execution Model

The basics a reader needs to understand the rest of the paper.

- **What BSP is:** Alternating phases of independent work and global synchronization. MPI collectives in HPC, NCCL in ML training.
- **Why scale matters:** 10K+ GPUs, weeks of runtime, massive resource investment. Efficiency is paramount.
- **Why BSP is fragile:** Lock-step execution means one straggler blocks everyone. Global sync amplifies local problems. The probability of *someone* being slow approaches 1 at scale.

### 2.2 The Observability Gap

Why understanding BSP performance is uniquely hard.

- **The diagnosis asymmetry:** Root causes take months to find, fixes take days. (AMR experience, cite the paper.) The bottleneck isn't engineering solutions — it's *seeing* the problem.
- **Why existing HPC tools fail:** Profilers aggregate away the signal. Tracers (Score-P, TAU) produce OTF2/CSV — write-optimized, not query-optimized. Fine-grained data exists but is painful to analyze.
- **Why cloud observability doesn't transfer:** Distributed tracing (Dapper, OTEL) assumes request-based causality. BSP has no request. Attribution is "which layer of the stack," not "which microservice."

### 2.3 The Broken Feedback Loop

Frame the core problem this paper addresses.

- **The current workflow:** Collect traces → dump to disk → load into pandas/dask → analyze post-hoc → maybe find something → re-run with different collection → repeat.
- **Why this is untenable:** Parsing overhead dominates. Can't change collection mid-run. Temporal gap between event and insight precludes intervention.
- **The goal:** A closed feedback loop. See what's happening *while it's happening*. Steer collection based on what you see. Intervene in real time.

---

## 3. Challenges and Insights

**Job:** Build tension. Show what's needed, what we tried, what we learned, and pose the questions the design must answer.

### 3.1 Fine-Grained Telemetry Is Necessary But Insufficient

You can't avoid collecting detailed data — but collection alone doesn't solve the problem.

- **Why fine-grained:** Coarse profiles hide stragglers, driver artifacts, cross-stack interactions. The AMR work showed anomalies only visible at per-rank, per-timestep granularity.
- **Why collection isn't enough:** The data exists. The problem is making it useful. Billions of events per second, most of which are irrelevant to any given question.
- **The tracing-for-debugging inversion:** You don't know what to collect until you've seen the problem. But if you collect everything, you drown. If you collect little, you miss it.

### 3.2 From Post-Hoc Analysis to In-Situ Analytics

The pivot: what if analysis happened *during* execution, not after?

- **The OLAP insight:** Columnar formats, vectorized execution, streaming primitives. The analytics world has solved "fast queries over large data." Early experiment: CSV → Parquet = 50× faster parsing.
- **Why not just faster post-hoc?** Speed helps, but the fundamental problem is the *temporal gap*. By the time you analyze, the moment is gone. Transient anomalies can't be reproduced.
- **The in-situ opportunity:** If you aggregate as data is generated, you can discard irrelevant data at the source. Materialize views on demand. Never write what you don't need.

### 3.3 The Need for Programmable Control

Real-time analytics enables a further step: steering collection itself.

- **The eBPF model:** Programmable probes — control what gets captured and when, based on observed state. Essential for single-node debugging in the AMR work.
- **The gap:** eBPF is single-process. BSP runs on 10K nodes. How do you get coordinated, programmable control at cluster scale?
- **The vision:** Cluster-scale eBPF. Start with coarse summaries. Drill down only when anomalies appear. Adjust collection without restarting the job.

### 3.4 Open Questions

The questions the design must answer. (Brief — these are signposts, not exposition.)

- **Data model:** What's the right unit of analysis for BSP telemetry?
- **Aggregation:** What's the compute abstraction for distributed, streaming analytics?
- **Control:** What's the abstraction for coordinated steering across thousands of ranks?
- **Overhead:** How do you do any of this without perturbing the application you're trying to observe?

---

## 4. Design

**Job:** Answer the questions. Each subsection resolves one axis of the design space.

### 4.1 Data Model: The Sync Window as Causal Unit

Answers: *What's the right unit of analysis?*

- **The key insight:** In BSP, causality resets at every global sync. A straggler in timestep T doesn't cause a straggler in timestep T+1 — the barrier resets the slate. The sync window (swid) is the natural partition key.
- **The contract:** ORCA requires two columns: `swid` and `rank`. Everything else is flexible. Arbitrary schemas, multiple streams, application-specific metadata.
- **Why columnar/Arrow:** Analytical efficiency. Parquet for persistence, Arrow for in-memory. The OLAP ecosystem already solved this — we inherit it.

### 4.2 Capture: Efficient Collection Without Perturbation

Answers: *How do you collect fine-grained data without drowning or slowing down the application?*

- **Format choice:** Parquet over JSON/CSV. 50× parsing speedup, comparable write cost after tuning (disable dictionary encoding).
- **Transport:** RDMA-based TBON. Network is faster than storage. Dedicated aggregator nodes (AGG) scale out ingestion. Data never hits disk on compute nodes.
- **Timing discipline:** Drain once per timestep, at the end, in `PostTimestepAdvance()`. Large batches, predictable timing, minimal jitter. The sync boundary is natural — you're already waiting.

### 4.3 Aggregation: In-Situ Analytics Over Streams

Answers: *What's the compute abstraction for distributed aggregation?*

- **The pipeline:** Named streams of Arrow record batches → per-partition processing in aggregators → cross-partition reduction in controller → sinks (real-time views, Parquet files).
- **SQL + MapReduce:** SQL for declarative queries (DataFusion), MapReduce escape hatches for complex operations. Single-pass streaming, no shuffles.
- **Pushdown:** Filter and aggregate as close to the source as possible. Aggregators do the bulk of per-partition work. Controller handles only cross-partition summaries. Data volume collapses before it leaves the compute fabric.

### 4.4 Control: Steerable Observability

Answers: *What's the abstraction for coordinated steering?*

- **The problem:** An asynchronous operator (human, dashboard, automation) needs to send commands to a synchronous application (BSP ranks in lock-step). Commands must be applied consistently — all ranks at the same timestep.
- **TS2PC:** Timestep-aware two-phase commit. Commands are tagged with a target timestep. Ranks accept if they haven't passed it, reject otherwise. Controller learns latency via delta tracking, adjusts automatically.
- **Primitives:** Toggle streams, adjust filters, change aggregation policies, pause/resume. Composable — complex workflows built from simple commands.
- **The payoff:** Start coarse. See an anomaly. Drill down to specific ranks, specific streams, specific timesteps. Without restarting. Without redeploying. The feedback loop closes.
