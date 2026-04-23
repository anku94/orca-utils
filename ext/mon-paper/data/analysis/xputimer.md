**XPUTimer (Cui et al., 2025)**

Diagnostic framework for LLM training deployed on 6000 GPUs for 8 months at Ant Group. Per-process daemon selectively instruments fixed Python APIs and GPU kernels with background CUDA event timing (0.43% overhead). Centralized diagnostic engine computes five metrics and routes anomalies to responsible teams. No online intervention, no coordinated collection, no overlay infrastructure.

**Metrics and ORCA mapping**

Five metrics, three standard and two novel, all computed centrally from per-rank timing data:

- **Training throughput**: dataloader timing, rate of input consumption. In ORCA: per-rank scalar, trivial aggregation. Pushable to MPI.
- **Per-kernel FLOPS**: timing + input layout metadata for computation kernels, with overlap-aware filtering to avoid false positives from comm/compute overlap. In ORCA: per-rank computation, needs input layout in the schema. Pushable to MPI. Cross-rank comparison (to detect underclocking outliers) is a GROUP BY kernel_name, then percentile/outlier detection at CTL.
- **Communication bandwidth**: requires start/end timestamps of final comm kernels across all participating ranks. In ORCA: cross-rank aggregation over timestep dataframe. Coordinated collection guarantees the completeness they lack — they note this metric needs "all ranks" but have no mechanism to ensure it.
- **Issue latency distribution** (novel): CPU kernel launch timestamp minus GPU execution start. Detects kernel-issue stalls from GC, accidental synchronization. CDF shape distinguishes healthy (linear) from unhealthy (steep). In ORCA: per-rank metric if a collector captures CPU-GPU timing pairs. Pushable to MPI. Cross-rank CDF comparison at CTL. However: this is a proxy for collective stall attribution that ORCA observes directly via straggler detection in timestep dataframes.
- **Void percentage** (novel): fraction of step time occupied by uninstrumented ops, split into inter-step CPU ops (Eq. 1) and minority GPU kernels (Eq. 2). In ORCA: per-rank gap detection over the event stream. Pushable to MPI.

**Error diagnosis and ORCA mapping**

- **Non-communication hang**: call stack divergence — hung rank shows non-comm function, others block on comm (§5.1, Fig. 6). In ORCA: TBON liveness — rank stops reporting, aggregator identifies which subtree is incomplete. No search required.
- **Communication hang**: CUDA-GDB register inspection inside hung NCCL kernels to identify faulty link (§5.1, Fig. 7). Reduces from O(log N) binary search to O(1). In ORCA: detection is TBON liveness (same as above). The CUDA-GDB script itself is a control plane command dispatched to relevant ranks — doesn't need timestep consistency since the app is already hung.

**Anomaly catalog by metric**

*Training throughput:*
- Dataloader bottleneck from O(L²) attention mask generation when sequence length changed from 4k to 64k (§7.4)

*FLOPS:*
- GPU underclocking: cross-rank FLOPS comparison identifies outlier GPUs (Table 3)
- Backbone migration regression (FSDP→Megatron): FLOPS drop from tensor-core alignment change in weight dimensions after TP sharding (§7.3)

*Bandwidth:*
- Network jitter with increased CRC errors (Table 3)
- GDR module failure (Table 3)
- Host-side hugepage causing high sysload (Table 3)

*Issue latency distribution:*
- Python GC stall (§5.2.2, Fig. 12)
- Unnecessary GPU synchronization, e.g., accidental Megatron timer (§7.2)
- Package version checking at import time (Table 3)

*Void percentage:*
- Frequent CUDA memory management in PyTorch runtime (Table 3)
- Unoptimized minority kernels from modified PE, ACT, NORM operators (§7.4, Table 4)
- Dataloader bottleneck from inter-step CPU ops (§7.4)

**Other notable points**

- PyTorch profiler produces 5.5GB per GPU per step for Llama-70B on 512 H800s (§4.1)
- eBPF-based RDMA NIC bandwidth tracer noted as in-progress future work (§8.5)
- Table 1 taxonomy with 8-month deployment data: most slowdowns are upper-stack (algorithm/infrastructure), not hardware
- Issue latency distribution detects 2.66% MFU loss from accidental Megatron timer — subtle enough that throughput metric missed it (§7.2)