# Section 0: Introduction

## Flow
P1: BSP scale/importance → observability gap
P2: Trace vs view problem (spatial/temporal gaps)
P3: Key insight: sync-window indexing
P4: ORCA solution preview (evolutionary design)

## Paragraph Outlines

**P1: The Problem**
- BSP powers critical workloads at massive scale (10K-100K GPUs)
- Resource footprint (money/energy/hardware) → efficiency paramount
- No structured observability solution (unlike Dapper for microservices)
- Metrics too coarse, HPC tracing post-hoc and expensive

**P2: Gap Between Trace and View**
- Trace = write-optimized, View = query
- Spatial gap: large dataset analyzed without hardware/application context
- Temporal gap: latency of intervention, transient anomalies hard to explain
- Current tools (Score-P, Kineto) all post-hoc

**P3: The Insight**
- Optimize view via indexing (database strategy)
- Index on dimension that captures causality
- For distributed: RPC. For BSP: sync window!
- Enables streaming analytics at causal boundaries

**P4: The Solution**
- ORCA: three-stage evolution
- Stage 1: Superior offline tracer (Parquet, swid partitioning)
- Stage 2: Streaming platform (in-situ SQL/MapReduce)
- Stage 3: Active framework (control plane for steering)
- Paper roadmap
