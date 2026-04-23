# Section 4: Implementation

## Flow
S1: Architecture overview
S2: Aggregation mechanics
S3: Control mechanics
S4: Runtime overhead and perturbation

## Subsection Outlines

**S1: Architecture**
- Named streams: (swid, rank) + arbitrary schema Arrow dataframes
- TBON: SRC (leaf ranks) → AGG (scale-out tier) → CTL (root)
- Sinks: CTL for real-time, AGG for partitioned Parquet persistence
- Bootstrap: schema discovery, tier plan computation

**S2: Aggregation**
- Tier plans installed on SRC/AGG/CTL after bootstrap
- Schemas discovered from trace collectors
- Rank 0 as lead for metadata exchanges
- Distributed query execution via DataFusion

**S3: Control**
- TS2PC protocol: bridge async operator ↔ sync application
- Controller has stale view, generates 2PC for ts+X
- Delta tracking: learn X via increment-on-failure + retry
- kPause/kResume special: synchronous state, immediate apply
- Composability: batch commands (e.g., [update flow, resume])
- Hierarchical broadcast/reduction enables 100K rank management

**S4: Runtime Overhead**
- Approaches optimal: collect only what's needed
- RDMA drainage (network faster than storage)
- Drain once per timestep (efficient RPCs)
- Inline work in PostTimestepAdvance (minimal jitter)
- Async interactions, QoS-amenable
- Example: 10MB/10K events in 1ms of 250ms timestep
