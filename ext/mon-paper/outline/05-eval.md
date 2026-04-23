# Section 5: Evaluation

## Flow
Bulletproof substrate metrics → workflows enabled

## Structure

**Substrate Properties (MUST HAVE)**
- Throughput: XGB/s telemetry streamed and filtered in-situ
- Overhead: <5% runtime impact (or "no measurable")
- Reduction: 95%+ data reduction via pushdown
- Scalability: X ranks at Y GB/s aggregate bandwidth
- Offline speedup: 1-2 orders magnitude faster than JSON
  - Parquet parsing: 30-50X faster
  - Timestep partitioning: queries touch only relevant data
  - Even offline-only usage = massive win

**Workflows Enabled (ASPIRATIONAL)**
- Time-to-insight: hours → seconds (AMR debugging example)
- Closed-loop latency: <100ms (online tuning POC)

**Narrative Arc**
Arg1 (substrate properties) → Arg2 (workflows enabled)
