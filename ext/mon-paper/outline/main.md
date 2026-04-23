# ORCA Paper-Level Outline

## Core Thesis
BSP workloads need always-on production observability with dynamic resolution and programmable views. The real bottleneck isn't fixing problems (solutions are idiosyncratic and quick) - it's diagnosing them. ORCA provides structured application-layer observability via sync-window indexed streaming analytics and control plane.

## Story Arc
1. **Problem**: BSP at scale has well-known problem classes (25 years of literature), but diagnosis takes months while fixes take days. Gap is structured production observability.
2. **Reframing**: Current workflow is broken (post-hoc tracing, overcollection). The pieces exist (OLAP maturity, programmable instrumentation). Time to synthesize.
3. **Insight**: Sync windows are the causal unit. Streaming columnar analytics + programmable control = always-on observability with dynamic resolution.
4. **Solution**: ORCA as evolutionary design: offline tracer → streaming platform → active framework

## Sections

### 1. Introduction
**Job**: Hook the reader, establish the problem, preview the solution.

**Arc**:
- BSP powers critical workloads at massive scale, efficiency paramount
- No structured observability: HPC has basic metrics, cloud tools (Dapper) don't apply
- The gap: trace vs view (spatial/temporal gaps in current workflow)
- Key insight: sync windows as causal unit enables streaming analytics + control
- ORCA as evolutionary design

### 2. Background & Motivation
**Job**: Complete, self-contained motivation for why BSP observability is critical and current approaches fail.

**Arc**:
- BSP context: scale, fragility, known problem classes (20+ years)
- The diagnosis asymmetry: finding root cause takes months, fix takes days
- AMR case study: full story showing programmability needs, iterative drill-down, weeks per iteration
- PyTorch parallel: validates pattern across domains
- Landscape: HPC tools have post-hoc gap, cloud tools wrong model for BSP
- Conclusion: Need always-on programmable production observability

### 3. Towards Always-On Programmable Observability
**Job**: Bridge from motivation to design. Develop vision, show what exists, identify gaps, pose design questions.

**Arc**:
- Unpack the concept: what does "always-on programmable" actually mean?
- What it could enable: collapse AMR's months-long feedback loop to minutes
- What pieces exist: OLAP maturity, eBPF concepts, in-memory analytics efficiency
- What's missing: cluster-scale coordination, streaming not offline, in-situ at scale
- Design questions: data model, compute abstraction, control mechanism, overhead management

### 4. Design
**Job**: Answer the design questions from section 3. Each subsection resolves one axis.

**Arc**:
- Data model: Sync window (swid, rank) as causal unit, columnar for analytics
- Capture: Parquet + RDMA TBON, drain at sync boundaries
- Aggregation: Streaming SQL/MapReduce pipeline with pushdown
- Control: TS2PC for coordinated steering across 10K ranks
- Why not existing systems: Kafka/etc lack timestep-dataframe semantics

### 5. Implementation
**Job**: Show how design is realized in practice.

**Arc**:
- Architecture: Named streams → TBON (SRC/AGG/CTL) → sinks
- Aggregation mechanics: tier plans, schema discovery, distributed query execution
- Control mechanics: TS2PC protocol, delta tracking, hierarchical broadcast
- Runtime overhead: RDMA drainage, sync-boundary timing, minimal jitter

### 6. Evaluation
**Job**: Validate substrate properties and demonstrate enabled workflows.

**Arc**:
- Substrate metrics (bulletproof): throughput, overhead, reduction, scalability, offline speedup vs JSON
- Workflows enabled (aspirational): time-to-insight collapse, closed-loop latency

### 7. Related Work
**Job**: Position ORCA in landscape.

**Categories**: In-situ systems, monitoring/metrics, tracing, ML observability, analytics frameworks, hardware accelerators. Analogy: SLAC/LHC FPGA-based DAQ.

### 8. Discussion & Future Work
**Job**: Extensions and broader implications.

**Topics**: Dynamic instrumentation (eBPF/DynInst), observability for correctness, generality across BSP variants, ideal vision (telemetry on tap), modular interfaces, accelerator integration.

### 9. Conclusion
**Job**: Tie it together with the supercomputer-as-single-machine vision.

**Message**: Supercomputer pretends to be single machine. We should observe and control it the same way.
