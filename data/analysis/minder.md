**Minder (Deng et al., NSDI '25)**

Faulty machine detector for distributed training at ByteDance, deployed for over a year on tasks up to 1500 machines (10,000+ GPUs). Core insight: in 3D-parallel training all machines exhibit similar metric behavior at second-level granularity, so the outlier is the broken one. For each metric independently, an LSTM-VAE denoises the time-series, pairwise Euclidean distance identifies the outlier machine, and a continuity check (same machine flagged for 4 consecutive minutes) filters jitters. A decision tree pre-ranks which metrics to try first. 3.6s average reaction time, 0.90 precision, 0.89 F1.

**Fault taxonomy (Table 1, 7 months production data)**

Every fault ultimately produces either a fail-stop (process dies, NIC drops, machine unreachable) or a fail-slow (PCIe degrades, GPU underclocks, HDFS timeout). Both manifest at collective boundaries as a straggler — the faulty rank either never arrives or arrives late.

- Intra-host hardware (55.8%): ECC error (38.9%), PCIe downgrading (6.6%), NIC dropout (5.7%), GPU card drop (2.0%), NVLink error (1.7%), AOC error (0.9%)
- Intra-host software (28.0%): CUDA execution error (14.6%), GPU execution error (7.7%), HDFS error (5.7%)
- Inter-host network (6.0%): machine unreachable
- No single metric covers all fault types; CPU and GPU are best but still miss cases. PCIe downgrading case study (§2.1) shows cascade: PCIe degrades → NIC buffer fills → PFC surge → throughput drops → GPU underutilized → 128-machine task slowed 40 minutes.

**ORCA mapping**

Minder uses ML over out-of-band hardware metrics to detect fail-stop and fail-slow faults. ORCA subsumes both:

- **Fail-stop**: TBON liveness. Rank stops reporting, aggregator identifies incomplete subtree. Immediate, no model needed.
- **Fail-slow**: straggler detection at collective boundaries. Timestep dataframe shows which rank arrived late and by how much — this is the authoritative fail-slow report. No polling, no denoising, no pairwise distance computation. The synchronization point where every fault eventually manifests is directly observed.
- **Continuity/policy**: a controller-side policy accumulates straggler reports across timesteps. If rank N is in the top-k stragglers for M consecutive timesteps, flag it. Stateless counter over already-aggregated data.
- **Attribution**: Minder identifies *which* machine but not *what* broke — it only infers the fault domain from which metric triggered detection. ORCA provides drill-down: once the straggler rank is identified, its per-timestep event streams (compute, communication, system) localize the cause.

**Key limitations confirming ORCA's value**

- Second-level polling granularity too coarse for concurrent faults (§6.6) — ORCA's event-driven collection at collective boundaries provides sub-timestep resolution by default
- No root cause analysis (§7) — ORCA's multi-stream collection provides the drill-down path
- Only out-of-band hardware counters; explicitly flags in-band traces (Torch Profiler, Megatron timers) as future work (§7) — these are what ORCA collects natively
- VAE denoising compensates for noisy second-level averages; event-driven collection at collective boundaries produces clean per-timestep measurements, reducing the need for learned denoising

**Other notable points**

- Average 2 faults per day in production; scales with task size (Fig. 1)
- Manual diagnosis takes 30+ minutes on average, can be days (Fig. 2)
- Abnormal performance persists 5+ minutes after fault (Fig. 4)
- 21 metrics collected across computation, communication, storage (Table 2, Appendix B)