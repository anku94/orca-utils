# ORCA Talk Outline (30 min, ~18 content slides)

## Pre-Background (1 slide)

- Overview

## Background (3 slides)

- Traces Create Visibility Bottlenecks
- Observability As A Feedback Loop
- BSP Structure Defines The Loop
- Requirements For Closing The Loop

## ORCA (7 slides)

- Architecture overview: three-tier TBON, columnar pipeline, SQL analytics, control plane
- Timestep dataframes: rank-major → timestep-major transposition, causally independent units
- Transport: RDMA-based async collection, receiver-driven flow control
- OrcaFlow: SQL over the TBON, operator pushdown to source
- OrcaFlow compilation: filter example + aggregation example (Fig 3)
- TS2PC: timestep-consistent control — commit/abort/stall
- Integration + putting it together: the closed-loop workflow

## Eval (6 slides)

- Setup: AMR code, 512–4096 ranks, comparison against TAU/DFTracer/ScoreP/Caliper
- Runtime overhead: 1–2% vs 56–81%
- Storage + query performance: 3.6–44× smaller, 3–4 OOM faster queries
- In-situ workflows: pushdown discards 99.999% at sub-2% overhead
- Agentic debugging: 27 minutes vs months, 144× data reduction
- Takeaway + future directions
