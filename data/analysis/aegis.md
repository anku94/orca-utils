**Aegis (Dong et al., NSDI '25)**

Fault diagnosis system for Alibaba Cloud's public AI training service, deployed over one year on clusters with O(1K) hosts and O(10K) GPUs. Central constraint: as a cloud provider, they cannot modify customer code. Evolved in two phases. Phase-1 enhanced existing datacenter diagnosis tools (network monitoring, RDMA Pingmesh, in-band tracing) with training-log error parsing and offline diagnosis as backstop. Phase-2 customized the CCL to get runtime procedure-aware information — CCL is a modular plugin in Megatron/DeepSpeed, so replacing it is transparent to customers. Reduced diagnosis idle time by 97%, task restarts by 84%, performance degradation by 71%.

**Phase-2 CCL instrumentation (§4.2)**

Three counters per GPU per collective per iteration, incremented in-process with near-zero overhead during normal training. Only read post-mortem when CCL timeout fires:

- Collective launch count (CL): how many times collective C_i was launched by GPU G_j
- Work request count (WR): how many work requests issued
- Work completion count (WC): how many work requests finished

Computation failure (Scenario-1): CL divergence — one GPU behind on launch count, meaning it never entered the collective. Communication failure (Scenario-2): WR ≠ WC — GPU entered the collective but work requests didn't complete. For degradation diagnosis, they add per-iteration collective duration (TD) and throughput for last 5 work requests (N), with thresholds α=0.8 and β=1.5 to distinguish computation vs communication degradation.

**Fault taxonomy (Fig. 2, production data)**

- GPU-related (45.6%): execution error (13.1%), ECC error (10.2%), NVLink error (9.2%), memory error (8.6%), CUDA error (3.3%), driver error (1.2%)
- Host hardware (38.5%): CPU error (13.7%), PCIe error (10.4%), memory error (9.1%), NIC error (9.1%), power/fan (3.7%), disk (1.6%)
- Network (6.7%): optic module & fiber error
- 100–230 critical failures per week in one production cluster
- A100 MTTF ~400 days, H100 MTTF ~200 days
- 73% of failed tasks fail within first 10 minutes (initialization phase)

**Phase-1 diagnosis procedure (Algorithm 1, §4.1)**

Priority-ordered: (1) critical errors (double-bit ECC, GPU missing, link down) → isolate host directly; (2) distributed errors on ≤2 hosts → isolate both; (3) distributed errors across many hosts → RootDiag clusters by source/destination to find common GPU; (4) ConfigCheck + NetDiag for systematic issues; (5) offline diagnosis as final backstop. Key lesson: 71% of distributed failures turn out to be host-side, not network-side.

Offline backstop (§4.1.2): topology-aware binary search. Split hosts along pod/ToR boundaries so parallel diagnosis tasks don't share network links, run a reference model on each subset, recurse into the failing one. Discovery: when neither subset reproduced the failure, it meant the root cause was in aggregation switches — silent packet loss on packets >1KB, missed by Pingmesh's 64B probes.

**Check Before Delivery (CBD, §6)**

Pre-delivery validation in <10 minutes: configuration checks (<1 min), single-host stress tests (3 min), multi-host collective tests (6 min). Catches 1–2% problematic hosts before delivery. Lightweight version (<1 min) for PaaS mode.

You're right. Let me redo just the ORCA mapping section:

**ORCA mapping**

Aegis's CCL counters (CL, WR, WC) are zero-cost in-process integers read only when a CCL timeout fires. During normal training they provide no value — they exist solely to answer "what happened" after a fault. This is a fundamentally different cost model from ORCA's continuous push-based emission.

Two open questions for ORCA:

*Fail-stop vs fail-slow.* ORCA's TBON liveness detects absent ranks but cannot currently distinguish "didn't enter the collective" (computation failure, Aegis Scenario-1) from "entered but didn't complete" (communication failure, Aegis Scenario-2). Aegis's CL vs WR/WC distinction only works because the faulty rank's process is still alive and its counters can be read post-mortem. For hard crashes, Aegis falls back to log scraping — same information as ORCA liveness. The distinction matters only for partial failures / hangs, where the rank is stuck but reachable.

*Per-collective vs per-timestep visibility.* ORCA currently emits dataframes at PostTimestepAdvance (after the last collective in a timestep). A hang at a mid-timestep collective produces silence indistinguishable from a pre-timestep computation hang. Two possible approaches: (a) a lightweight ProgressTracker that pushes a monotonic counter per collective up the TBON — continuous overhead but early detection, (b) a pull-based path where the controller queries rank-local counters (like Aegis does) only after a fault is suspected. Both are implementable on ORCA's reduction topology. The choice is a policy decision, not an architectural limitation, but neither is currently implemented.

*Deployment model.* Aegis is a platform-level service monitoring all customer jobs on shared infrastructure. ORCA's model is one overlay per job. Cross-job infrastructure diagnosis (NIC firmware bugs, optic contamination, switch misbehavior) is outside ORCA's scope. Multi-tenant deployment is future work.

**Other notable points**

- Dual-ToR design converts link failures from crashes to degradation (Appendix B) — O(10K) link hotfixes executed without isolating hosts
- Optic modules/fiber have 1.2–10× higher failure ratio than DAC (§2.1.1)
- NIC congestion control firmware bug (§8): continuous ECN signals caused NIC to enter preset max rate limit; no per-host outlier visible, required cross-host infrastructure-level diagnosis
- Batch link failure during cluster delivery: overlapping construction/wiring timelines caused optic contamination, 10–20× normal failure rate for weeks (Fig. 15)
- Explicitly rejected MegaScale's approach (instrument CUDA events in customer code) as impractical for public cloud — validates that the computation/communication boundary (CCL/ORCA's collector model) is the right instrumentation point for multi-tenant environments