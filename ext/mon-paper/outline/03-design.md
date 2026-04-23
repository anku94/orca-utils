# Section 3: Operationalizing Always-On Dynamic Observability

## Job
Unpack what "always-on production observability with dynamic resolution" actually means, why current workflow doesn't provide it, and show that the pieces exist to build it. Build tension by showing the workflow is broken, then pose the questions section 4 must answer.

## Flow
S1: Fine-grained data is necessary and available
S2: Current workflow is absurd and fundamentally limited
S3: Dynamic resolution needs real-time feedback
S4: Bridge to design - pose the questions

## Subsection Outlines

**S1: Application-Layer Observability Requires Fine-Grained Data**
- Metrics too coarse (hide stragglers, cross-stack interactions)
- Need per-rank, per-timestep, cross-layer correlation
- AMR showed: anomalies only visible at fine granularity
- Instrumentation exists everywhere (CUPTI, MPI profiling, tracers)
- Data is available - question is what to do with it
- Can't aggregate away the problem - so collection is unavoidable

**S2: Current Workflow Doesn't Scale to Always-On**
- Post-hoc tracing: expensive, not production-viable
- **The workflow absurdity**:
  - Capture binary instrumentation data
  - Serialize to CSV/JSON (text formats!)
  - Parse back into columnar analytics engines (pandas/dask)
  - Why roundtrip through text?
- **OLAP solved this**: Arrow/Parquet, columnar from the start
  - Our experiment: Parquet 50X faster than CSV parsing
  - Tuned Parquet: comparable write performance (disable dictionaries)
- But even with speed, **fundamental problem remains: temporal gap**
  - By the time you analyze, moment is gone
  - Can't distinguish transient from structural
  - Can't intervene in real-time
- **What's needed**: Materialize views inline, not post-hoc

**S3: Dynamic Resolution Requires Real-Time Feedback**
- **Overcollection problem**:
  - Can't see what you're capturing
  - So you collect everything "just in case"
  - Tracing becomes forensic artifact, not operational telemetry
- **Tracing-for-debugging paradox**:
  - Don't know what to collect until you see the problem
  - Collect everything → drown in data
  - Collect little → miss the signal
- **Production observability paradigm** (exists elsewhere):
  - Always-on at coarse resolution
  - Detect anomaly → drill down dynamically
  - Adjust collection based on what you observe
- **eBPF showed this works**:
  - Programmable probes: attach/detach dynamically
  - Control what gets captured, when
  - Essential for single-node debugging in AMR work
- **The gap**: eBPF is single-process. BSP is 10K nodes.
  - How to get coordinated, programmable control at cluster scale?
  - Need adaptive collection based on real-time feedback

**S4: The Design Space**
- Goal: **Always-on production observability with dynamic resolution and programmable views**
- This requires: Streaming columnar analytics + programmable control
- Questions section 4 must answer:
  - **Data model**: What's the unit of analysis for BSP telemetry?
  - **Compute**: What's the abstraction for distributed streaming analytics?
  - **Control**: How to coordinate steering across 10K ranks?
  - **Overhead**: How to realize this without perturbing the application?

## Key Transitions
- From S2: "Current workflow is broken, but pieces exist (OLAP)"
- From S3: "eBPF works single-node, need cluster-scale"
- To Section 4: "Here's how we answer each question"
