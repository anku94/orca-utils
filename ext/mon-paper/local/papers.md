# Related Work Paper Notes

Concise summaries focused on relevance to ORCA.

---

## HOLMES `\cite{Yao2025:Holmes}`
**Yao et al., NSDI'25**

Online detection and localization of communication irregularities in large distributed training. Monitors for abnormal iterations, then progressively fetches a subset of logs and traverses a communication-structure graph (COG) to isolate responsible GPUs/groups.

**Supports ORCA's argument:**
- Real-time/online detection, not post-hoc forensics (feedback latency matters)
- "Progressive fetching" = steerable drill-down, proportional cost
- Localization depends on structured parallelism (DP/PP/TP) — BSP semantics matter, can't treat nodes as independent streams
- Reports localization in seconds at scale — the "actionable window" ORCA argues for

**Doesn't subsume ORCA:**
- Bespoke single-pathology pipeline: specific logs, specific detection logic, specific traversal
- Supports ORCA's critique that "everyone reinvents ad-hoc primitives"
- Not a general programmable substrate for arbitrary telemetry + analytics + control

**Cites:** PerfExpert, continuous program optimization/monitoring literature, graph-based RCA for services—positions itself as specialized diagnosis method (graph/RCA flavored) for training-stack symptom class.

---

## GREYHOUND `\cite{Wu2025:GREYHOUND}`
**Wu et al., 2025**

Targets fail-slows (transient stragglers from compute/communication) in large-scale hybrid-parallel training. Characterization on >10K GPU cluster shows fail-slows last sub-minutes to ~10 hours, delay jobs 1.34× on average; current practice is manual detection + checkpoint/restart.

System: hooks NCCL calls to track iteration time, detects prolonged iterations via Bayesian change-point detection, triggers lightweight profiling to narrow suspicious groups, then micro-benchmarks to pinpoint slow GPUs/links. Escalating mitigation policy (S1→S4) framed as ski-rental decision.

Key insight: coarse telemetry (GPU SM util, RNIC counters) is insufficient — in synchronous training, a single degraded component causes simultaneous utilization drops across all GPUs, making localization impossible.

**Supports ORCA's argument:**
- BSP/lockstep semantics are the core problem: "simultaneous utilization drops" = ORCA's "straggler blocks everyone; naive telemetry lies"
- Online loop: detect → localize → mitigate during training (not post-mortem)
- Steering/proportionality: escalates from lightweight monitoring → profiling → targeted micro-benchmarks only when needed
- Exemplifies "everyone reinvents this" — custom collection + aggregation + detection + mitigation for one pathology

**Cites:** SuperBench, HOLMES—situates itself among targeted systems for specific failure/slowdown modes, not proposing reusable programmable observability substrate.

**Net:** Strongly validates ORCA's motivation and directly exemplifies the ad-hoc reinvention ORCA claims to subsume.

---

## XPUTIMER `\cite{Cui2025:XPUTimer}`
**Cui et al., 2025**

Production anomaly-diagnostics system for large LLM training clusters. Lightweight, long-running per-process daemon instruments curated "key segments" (Python/runtime + GPU compute/comm kernels), streams timing data to central diagnostic engine.

Targets: (1) hang/error diagnosis via intra-kernel tracing (CUDA-GDB) initiated by engine, (2) slowdown diagnosis via derived macro/micro metrics (throughput, FLOPS, bandwidth, issue-latency distributions, "void %"). Claims low overhead, production use at thousands of GPUs over months.

**Supports ORCA's argument:**
- Rejects "post-hoc trace" default: explicitly real-time and long-running, catching issues during training ("observability vs archaeology")
- Proportional-cost collection is mandatory: selective instrumentation of "key segments" due to impractical overhead of comprehensive profiling
- Contains narrow control-plane pattern: on anomalies, engine commands deeper mechanisms (attach CUDA-GDB) — "steer collection depth based on what you observe" as hardcoded escalation
- Exemplifies "point-solution reinvention": fixed curated probes + derived metrics + specialized logic for particular anomaly classes; not composable, extending requires engineering new probes/aggregations/logic inside purpose-built framework

**Cites:** Dynolog, MegaScale—positions these as adjacent "stack-wide / online profiling" systems. XPUTIMER is a timer/anomaly-diagnostics technique that benefits from (and implicitly assumes need for) better operational visibility, but is not itself the general platform.

**ORCA's novelty claim:** Generalize this loop into a programmable, reusable analytics + control substrate so these systems don't need to be rebuilt monolithically for each pathology.

---

## Aegis `\cite{Hu2025:Aegis}`
**Hu et al., NSDI'25**

Production diagnosis system from a large model-training provider. Goal: diagnose failures at runtime without modifying customer code—providers need coverage "during entire lifecycle" and must be general/transparent across customers.

Core argument: traditional cloud diagnosis doesn't transfer because training failures spread from single point to entire cluster, hiding culprit among error reports from all hosts. Phase-1 uses training-output logs + runtime procedure, with offline diagnosis as backstop. Offline proved painful (requires isolating all hosts, hurts scheduling/utilization), motivating Phase-2: customize CCL layer to gather runtime status without customer code changes, defining CCL metrics + runtime diagnosis to raise runtime diagnosis ratio from 77% to ~100%.

Scope: urgent production task is locating which device introduces failure/degradation for isolation; deeper root-cause analysis is explicitly "offline, not covered in Aegis."

**Supports ORCA's argument:**
- Validates BSP/lockstep "blast radius" premise: training failures propagate cluster-wide, hiding culprit among distributed error reports
- Validates "feedback latency determines action" by negative example: offline-backstop forces host isolation, harming utilization—system evolves specifically to avoid offline diagnosis
- Fits "everyone reinvents this" characterization: pick one boundary layer (CCL), customize it, define metrics/procedures, build diagnosis workflow—valuable but tightly coupled to (LLM stack × provider constraints × CCL surface)

**Gap ORCA claims:** Aegis targets device isolation (fast triage); interactive drill-down and general programmability out of scope. In ORCA terms: specialized control/diagnosis pipeline, not programmable "summary → targeted detail" observability substrate.

**Cites:** Dynolog, MegaScale—consistent with characterization as vertically-integrated production diagnosis system, not general-purpose programmable BSP observability/control plane.

**Net:** Strong background for "problem is real, high-value, currently solved via ad-hoc layer-specific instrumentation + rigid procedures"—sets up ORCA's novelty as generalization: provide reusable substrate so systems don't keep hardcoding one-off diagnosis stacks.

---

## Minder `\cite{Deng2025:Minder}`
**Deng et al., NSDI'25**

Online faulty-machine detector for large-scale distributed training. Targets production reality: ~2 faults/day, can halt jobs for hours; current practice is manual, multi-team, log-driven diagnosis that is slow and incomplete.

Core idea: in synchronous training, machines should look similar at coarse time granularity; faulty machine exhibits persistent divergence. Pulls second-level monitoring metrics, denoises with per-metric models (LSTM-VAE), computes similarity/outlier scores, applies continuity check. Prioritizes metrics via decision tree. Reports alerts within seconds.

**Supports ORCA's argument:**
- Directly reinforces "observability vs archaeology": their critique is you only get notified after a stop, then engineers trawl logs/counters for hours/days; logs incomplete/redundant; diagnosis trigger is late
- BSP semantics essential for detection: relies on assumption that DP/PP/TP training has balanced loads, so machine metrics are similar; faulty machine detectable as outlier — "lockstep implies comparability"
- Point solution that reimplements "collection → aggregation → decision": specific pipeline with per-metric denoise models, similarity checks, continuity thresholding, decision tree; extending means engineering more metrics/models/logic
- Surfaces "no single metric is sufficient" complexity: task-dependent normality, noisy telemetry → supports ORCA's claim for programmable signal combination, not fixed dashboard

**Cites:** MegaScale, Dynolog as representative monitoring/telemetry efforts. Explicitly flags "fine-grained runtime monitoring" as future direction for root-causing issues—implicitly motivates the missing substrate for deeper drill-down / intervention loops.

**For background:** Clean example of "industry building online diagnosis loops as specialized systems with custom telemetry pipelines" — exactly the gap ORCA generalizes into reusable substrate.

---

## Lumos `\cite{Liang2025:Lumos}`
**Liang et al., 2025**

Trace-driven performance modeling + what-if estimation for large-scale LLM training. Takes small number of Kineto traces and reconstructs fine-grained execution graph by recovering CPU↔GPU and GPU↔GPU dependencies (including inter-stream dependencies via CUDA event mechanisms).

Core argument: modern LLM training has complex overlap and dependency structure (compute/comm overlap creates inter-stream dependencies) that existing trace-driven models miss, leading to large prediction gaps. Lumos claims to be first to capture these dependencies for LLMs.

Supports graph manipulation to answer "what-if" questions (different GPU counts, parallelism configs, architecture tweaks) via simulation, avoiding repeated hardware deployment. Profiling overhead kept small by tracing only a few iterations, relying on execution pattern consistency.

**Relationship to ORCA:** Complementary, not competing.
- Lumos: modeling/what-if planning from traces (offline)
- ORCA: telemetry + real-time intervention (online)

**Shared premise:** Both care about extracting semantics-aware structure from low-level events. Lumos's core contribution is reconstructing dependency structure (especially inter-stream dependencies) because naive interpretations of overlap are wrong.

**Cites:** ASTRA-sim, HeterSim and other simulators—supports "complementary" framing: Lumos is primarily modeling/estimation layer (what-if / prediction) that can sit on top of an ORCA-like substrate rather than substitute for it.

**What Lumos doesn't address:** Does not argue about JSON parsing overhead or "post-hoc archaeology" as central problem; treats traces as input to offline modeling pipeline, focuses on accuracy + estimation + reducing cost of hardware experiments.

---

## Reveal `\cite{Chen2025:Anomalies}`
**Chen et al., 2025**

Hardware-centric profiling + unsupervised anomaly detection for cloud operators who lack visibility into tenant workloads due to virtualization/PaaS isolation. Thesis: workload knowledge isn't necessary for system-level anomaly detection; operators can rely on hardware/OS-level signals they can always access.

Pipeline: collects host-visible telemetry (perf, procfs, nvidia-smi), prunes redundant metrics, derives indicators (IPC, stall ratios), applies unsupervised detection over sliding windows, maps anomalies to subsystems (CPU/GPU/memory/network/storage), produces reports for intra/inter-node correlation. Claims 5.97% DeepSeek speedup after fixing identified issues.

**Supports ORCA's argument:**
- Confirms operator observability gap is real: virtualization/PaaS blocks "inside the workload" views, making developer-oriented profiling hard for operators
- Reinforces low-overhead, always-on constraint: explicitly motivates away from heavy instrumentation, builds for continuous operation
- Shows "anomaly detection + attribution" built as specialized system: specific pipeline (metric selection → window features → unsupervised detectors → subsystem attribution), engineered around host-visible counters

**What Reveal doesn't provide:**
- Not a streaming, BSP-semantic, drill-down substrate from summary → fine-grained per-syncpoint detail
- Leans on host-level signals and operator constraints rather than workload-structured telemetry and interactive steering

**Cites:** Groups MegaScale and GREYHOUND as diagnosing performance anomalies; mentions HOLMES as localizing irregularities. Treats surrounding telemetry/analysis infrastructure as given (or bespoke), not as the main contribution.

**For background:** Evidence that online, low-overhead operator-facing anomaly detection is real need, but current answers are domain-specific pipelines (Reveal for host telemetry; others for CCL logs, comm traces, etc.)—leaves room for ORCA's "general programmable substrate" contribution.

---

## TraceSim `\cite{Liang2024:TraceSim}`
**Liang et al., MLArchSys/ISCA'24**

Trace-driven execution-graph reconstruction + simulator for distributed ML training. Uses PyTorch Kineto traces (operators, CUDA runtime events, GPU kernels) to build fine-grained execution graph with CPU↔CPU, CPU↔GPU, GPU↔CPU, GPU↔GPU dependencies, explicitly modeling concurrent streams and inter-stream dependencies (via cudaEventRecord/cudaStreamWaitEvent).

Simulates executions from this graph to reproduce iteration time and derived stats (exposed comm time, SM utilization). Supports "what-if" by modifying graph parts (e.g., comm timing for scaled DP) to predict larger-scale performance from small-scale traces.

**Relationship to ORCA:** Complementary—primarily offline modeling/simulation, not real-time observability.

**Useful for ORCA background:**
- Reinforces that getting correct "semantic structure" from traces is hard but necessary: naive models ignoring concurrent streams / inter-stream dependencies become inaccurate
- Argues for minimal-intrusion collection: uses built-in profiling (Kineto), avoids custom instrumentation
- Clean example of "traces → execution graph → derived views" pipeline—same raw-to-derived transformation ORCA wants to make cheaper/faster/online

**Cites:** CUPTI/Nsight/nvprof, Kineto, Daydream, Astra-sim 2.0—the space is rich in point tools (profilers, tracers, simulators), but those don't by themselves give the "live navigate + steer collection" loop ORCA foregrounds.

**What TraceSim doesn't argue for:**
- Real-time intervention, streaming aggregation, or operator "drill-down while the job runs" loop
- Motivation is "what to optimize / why" and avoiding expensive large-scale experimentation via simulation

---

## SuperBench `\cite{Xiong2024:SuperBench}`
**Xiong et al., USENIX ATC'24**

Proactive validation system for cloud AI infrastructure targeting "gray failure" / gradual performance degradation caused by hardware redundancies masking partial failures until they manifest as regressions or hangs.

Premise: distributed AI workloads are gang-scheduled + synchronized, so incidents propagate across many nodes and penalties get magnified. Reactive troubleshooting is slow (~38% of incidents take >1 day to recover; MTBI example of ~17.5 hours in Azure A100 context).

System: (1) benchmark suite (end-to-end model benchmarks + microbenchmarks + pattern-wise microbenchmarks including overlap patterns and network collectives), (2) Validator that runs selected benchmarks and classifies nodes as defective using distribution-level criteria from historical results, (3) Selector that decides when/which benchmarks to run by predicting incident probability and trading off validation time vs coverage. Production deployment validating hundreds of thousands of GPUs over ~2 years; claims MTBI improvements up to 22.61×.

**Relationship to ORCA:** Complementary—provider-side reliability gate, not in-job telemetry + real-time drilldown. Stresses hardware/network/software paths before customers hit them, because organic workload monitoring misses issues (some regressions only appear under specific overlap/traffic patterns; redundancies hide partial degradations).

**Supports ORCA's broader motivation:**
- Strongly reinforces lockstep / blast-radius reality: one node/link issue can hang 100+ node job, forces cluster-wide investigation
- Documents reactive troubleshooting is slow and messy, with non-determinism and cross-layer misattribution (symptoms as NVLink errors while root cause is IB timeout)—compatible with "you need better operational tooling" (SuperBench → proactive validation; ORCA → runtime observability)

**Related work worth flagging:**
- Gray failure / fail-slow literature (gradual degradation, partial failures)
- Elastic / fault-tolerant training (TorchElastic, Horovod Elastic)—cited as mitigation but introduces nondeterminism, not transparent to customers
- Benchmarking suites (MLPerf, DeepBench, DAWNBench)—contrast "ranking peak performance" vs "validation to detect defects across nominally identical systems"

---

## eGPU `\cite{Yang2025:eGPU}`
**Yang et al., HCDS'25**

Framework to run eBPF-style instrumentation on GPUs by dynamically translating eBPF bytecode into PTX and injecting into running GPU kernels ("dynamic PTX injection"). Goal: fine-grained GPU observability (kernel execution, memory transfers, orchestration) with low overhead and without interrupting active kernels.

Architecture: builds on userspace eBPF runtime (bpftime), shared-memory "maps" usable across CPU/GPU, and PTX JIT/injection—aims to make GPU instrumentation look like "normal eBPF" from tooling standpoint.

**Relationship to ORCA:** Infrastructure for instrumentation, not telemetry aggregation/analytics/control platform. Plausible probe mechanism (GPU-side, dynamic, low-overhead) that could feed an ORCA-style streaming/steering substrate, but by itself doesn't provide BSP-wide aggregation, drill-down workflows, or operator control plane.

**Cites:**
- Dynolog / Meta observability stack: describes as distributed telemetry daemon collecting low-overhead bare-metal metrics, with selective precise tracing via CUPTI/Kineto and BPF-based attachments (Strobelight/BPF style)—consistent with how we discussed Dynolog/XPUTIMER-era stacks as layered telemetry + selective tracing
- CUPTI and NVBit: positions as existing GPU instrumentation options with higher overhead or more invasive, motivating PTX-level injection as lower-overhead path
- bpftime (userspace eBPF): uses to avoid kernel context-switch overhead for uprobes and support shared-memory maps
- ParallelGPUOS (POS): enabling technique for PTX self-modifying code / injection
- Amanda: unified DNN instrumentation framework, adjacent work

---

## Collie `\cite{Kong2022:Collie}`
**Kong et al., NSDI'22**

Systematic search tool for uncovering RDMA subsystem performance anomalies (unexpectedly low throughput, PFC pause-frame storms) in production-like deployments, without needing access to RNIC internal designs.

Key idea: instead of testing a few benchmarks or "representative" applications (which miss failures triggered by unknown/evolving workloads), Collie constructs huge workload search space from stable "narrow waist" abstraction—RDMA verbs—and uses simulated annealing to drive performance + diagnostic counters toward extreme regions where anomalies are more likely. Computes Minimal Feature Set (MFS): smallest workload conditions needed to reproduce anomaly, avoiding redundant search and giving developers actionable "avoid this pattern" guidance. Found 15 new anomalies (18 total including 3 known), all vendor-acknowledged.

**Relationship to ORCA:** Complementary—pre-deployment / integration-testing + "fuzzing"-style search, not runtime BSP-aware telemetry → drill-down → steer probes.

**Supports ORCA's background:**
- Concrete evidence that real RDMA deployment anomalies depend on interactions across RNIC + PCIe + NUMA + memory placement + message patterns; simple benchmarks/app tests miss them
- Supports "everyone reinvents bespoke machinery" theme in RDMA domain: Collie built whole substrate (search space definition, workload generator, anomaly monitor, counter-guided search, MFS extraction) because default ecosystem (Perftest, OSU microbenchmarks, "run some apps") doesn't cover the space

**Best positioned as:** Collie finds subsystem-level bad regions ahead of time; ORCA helps localize + respond to emergent behavior in live BSP workloads.

**Cites:**
- Perftest and OSU micro-benchmarks: common RDMA testing baselines, insufficiently comprehensive
- BytePS: distributed ML setting where anomalies matter, Collie helped bypass an issue
- IRN and RoCE reliability/flow-control discussions: lack of end-to-end flow control in RoCEv2, some issues tied to PFC reliance

---

## STAD `\cite{Xuan2025:STAD}`
**Xuan et al., 2025**

Post-hoc trace analysis method to identify and localize performance inefficiencies in parallel programs across where (rank), when (iteration/time), and what (communication/compute pattern).

Approach: represents each iteration's inter-rank behavior as Spatial Communication Pattern Graph (SCPG), models time evolution using spatial–temporal DGNN, uses VAE to detect anomalies/inefficiency "roots" and localize them. Explicitly notes analysis cost grows with trace volume (more ranks / longer runs → more cost).

**Relationship to ORCA:** Point solution in offline analysis, not observability/control substrate.
- Supports premise that operators need structured ways to go from global symptoms to localized causes—invents new derived structure (SCPG + spatiotemporal model) to make traces interpretable at scale
- Lives in forensics pipeline: must already have traces, paper acknowledges scaling pressure from trace volume

**Best positioned as:** Complementary—STAD is the kind of analysis that could run on top of better telemetry substrate, but doesn't itself provide "streaming views + steerable collection + runtime intervention."

**Cites:**
- Scalasca: trace analysis / bottleneck detection
- Vapro, Prodigy: trace-driven debugging / localization
- Tao: pathology-focused performance tool

---

## Dynolog (Meta)
**Meta Open Source, MIT License**

Production monitoring daemon for heterogeneous CPU-GPU systems in large-scale AI training. Two operational modes: (1) always-on continuous polling (CPU/network at 60s, GPU via DCGM at 10s), (2) on-demand deep-dive profiling via RPC triggering Kineto/PyTorch traces.

**Architecture:**
- Multi-threaded daemon with modular monitors (KernelCollector for /proc, PerfMonitor for PMU, DcgmGroupInfo for GPU)
- IPC fabric (Unix domain socket) for PyTorch process registration
- JSON-RPC control plane (port 1778) for remote commands
- Composite logger supporting multiple backends (JSON, Prometheus, ODS, Scuba)

**Telemetry:**
- CPU: utilization modes, MIPS, cycles, network I/O
- GPU: SM activity/occupancy, tensor core activity, HBM bandwidth, NVLink/PCIe throughput, power
- PyTorch: on-demand operator traces with shapes, stacks, FLOP estimates

**Control plane:**
- gflags at startup, systemd config, runtime RPC commands (`dyno gputrace`, `dcgm-pause/resume`)
- Distributed coordination via `unitrace.py` script querying SLURM for job nodes

**Relationship to ORCA:**
- Exemplifies "layered telemetry + selective tracing" pattern that ORCA's background discusses
- Polling + on-demand tracing is the right decomposition, but:
  - No clear semantics for when tracing takes effect at timestep granularity
  - No coordination/consistency for distributed activation (ranks may start at different times)
  - Kineto emits JSON; downstream analytics (HTA) is single-node Pandas—neither scales to real-time over thousands of ranks
- Control plane is ad-hoc triggers (RPC), not transactions with BSP-consistent semantics

**Cited by:** XPUTIMER, Minder, Aegis position Dynolog as representative monitoring/telemetry effort in training stack.

---

## Logical Structure Recovery `\cite{Isaacs2015:LogicalStructure}`
**Isaacs et al., SC'15**

Tackles pain that Charm++ traces are hard to interpret because asynchrony + nondeterministic scheduling + task migration break the clean "timeline = algorithm" mental model.

Core contribution: post-processing framework that transforms Charm++ event trace from physical time order into "logical structure" matching developer intent:
- Partition events into dependency phases (phase DAG), merging using message dependencies, serial-block structure, cycle merges
- Assign logical steps within phases using happened-before constraints
- Reorder operations within phases to reduce nondeterminism artifacts and reveal repeated structure/patterns

Also defines metrics mapped onto logical structure (idle experienced, differential duration, imbalance) for performance debugging. Explicitly discusses missing control-dependency information in traces, proposes heuristics to infer/repair ordering.

**Supports ORCA's argument:**
- Direct evidence that raw traces are not self-explanatory at scale; making them usable requires additional structure extraction (phase inference, dependency repair, reordering)—more than "just collect traces and view them"
- Reinforces that missing/implicit dependencies (especially through runtime behavior) are core barrier; either change what you record or do heuristic inference after the fact
- But fundamentally post-hoc trace transformation + visualization/metrics approach, not runtime streaming analytics + steering/intervention substrate

**Best positioned as:** Strong prior-art evidence that "post-mortem traces require heavy lifting to become actionable."

**Cites:**
- Projections (Charm++ tooling): stats/plots + process timeline visualization, user-guided outlier discovery
- Scalasca: automated trace analysis detecting known patterns, maps severity to code/machine locations; message-passing focused, doesn't support task-based models
- Vampir, Paraver, Jumpshot: "physical time over resources" visualization baselines

---

## Accelerating Big Data Infrastructure `\cite{Brown2017:BigData}`
**Brown et al., 2017**

Short position/progress report on HPC↔Big-Data convergence with three thrusts:
1. Measure + model extreme-scale I/O workloads under realistic production effects (multi-job contention, failures)—argues understanding I/O performance requires holistic, full-stack/system-wide measurement because bottlenecks emerge from interactions across I/O hierarchy and shared resources
2. Design low-latency, scalable, on-demand burst buffer ("HuronFS") in user space (FUSE) with hierarchical caching/buffering in front of parallel file system, using high-performance networking (CCI/InfiniBand)
3. Optimize graph analytics for dynamic graphs via locality-aware dynamic graph store ("DegAwareRHH") and distributed extensions

**Supports ORCA's background:**
- System-wide telemetry produces streams that only become useful after aggregation + correlation; paper explicitly says doing that analysis is non-trivial, especially with multiple concurrent jobs on shared systems
- Same "raw data isn't insight; you need an analytics/aggregation layer" argument, expressed in I/O/Big-Data context
- Adjacent evidence that HPC operations repeatedly end up building on-demand, low-latency infrastructure layers to cope with shared-system variability and data-movement bottlenecks

**Cites:**
- TOKIO, SIOX: full-system metrics collection projects producing performance-data streams requiring aggregation/correlation
- CODES: I/O modeling framework with detailed network/storage models, need to incorporate failures + contention
- Burst buffer work (CloudBB), FUSE, CCI, IOR in storage-acceleration stack
- STINGER, PowerGraph: dynamic-graph ecosystem

---

## DFTracer `\cite{Devar2024:DFTracer}`
**Devarajan et al., 2024**

Tracing + analysis pipeline aimed at AI-driven workflows (mixed compute/I/O) where developers want rich contextual metadata and analysis is done in Python dataframe ecosystems.

Core pieces:
- Unified tracing interface (C++) with small API surface (get_time(), log_event()), low overhead, standardize event capture across layers
- "Analysis-friendly" trace format: JSON Lines (dynamic per-event metadata) + indexed GZip compression (parallel reads from compressed data)
- Explicit motivation around tooling friction: expensive to convert binary trace formats into Python dataframes; key bottleneck is C↔Python conversion (ctypes) and out-of-core limitations
- DFAnalyzer: pipelined/parallel loader using gzip index to read batches, repartition across workers, materialize partitioned Dask dataframe
- Calls out LD_PRELOAD limitations when ML frameworks spawn worker processes (PyTorch/DALI data loaders); adds Python bindings for fork/spawned processes
- Argues existing tracers under-capture key events for their workloads (Unet3D case study shows different event counts vs Score-P/Darshan DXT/Recorder)

**Supports ORCA's argument:**
- Format + analysis pipeline dominates feasibility: central thesis is "we can collect events, but turning them into something analyzable (in Python) is the real bottleneck"—directly backs ORCA's motivation that core challenge is constructing useful views efficiently
- Point-solution evidence: team building custom tracer + storage/ingest design specifically to make analysis tractable at scale (parallel reads, load balancing into Dask, caching)—aligned with "everyone reinventing bespoke pipelines"
- Cross-layer correlation pain: combining traces from app-level + system-call tools is non-trivial (parsing multiple trace types, time resolution mismatches)—supports "everyone is reinventing this badly" narrative

**What DFTracer doesn't solve:**
- Still fundamentally offline trace → load → analyze pipeline; accelerates post-hoc analysis but doesn't propose BSP-aware streaming aggregation or online control plane to steer collection mid-run
- JSON Lines choice is "analysis-friendly" in Python portability sense, while ORCA argues post-hoc pipelines built on JSON/trace dumps obstruct real-time feedback

**Best positioned as:** Good citation for "teams building custom tracer+analysis stacks because existing tracing ecosystems don't meet modern workflow needs" and "data representation + ingest path can dominate practicality." Strengthens claim that space is fragmented and tooling stops at better offline forensics, not general real-time feedback substrate.

**Cites:**
- Score-P
- Darshan DXT, Recorder: specifically complains about binary→Python conversion cost
- PerfFlowAspect, Caliper: exceptions in "binary format makes Python reading expensive" discussion

---

## IOMax `\cite{Yildi2023:IOMax}`
**Yildirim et al., SC-W'23**

Out-of-core analysis accelerator for HPC I/O traces aimed at "data drilling" workflows (iterative slice/aggregate/query to find I/O pathologies). Argues existing analysis practice is inefficient because tools treat each query independently and trace columns are optimized for production, not for analysis/data slicing.

Design has three main ideas:
- Build cacheable aggregate view containing only indices/keys needed for query set, so multiple drill-down queries can reuse work
- Apply dataset transformations to make slicing/indexing efficient (datatype corrections; encode/rehash string columns like file paths into integer IDs for indexing)
- Emphasize practical out-of-core constraints (Pandas failing, Dask succeeding but still wasting work without reuse), showing large speed/memory wins when system exploits reuse and optimized representations

**Supports ORCA's argument:**
- Strong support for one specific ORCA motivation: hard part is not "collect traces," it's making iterative analysis feasible and fast by (a) materializing the right views and (b) exploiting reuse across drill-down steps
- IOMax's entire contribution is view/cache/representation optimization layer for drill-down analysis

**What IOMax doesn't solve:**
- Does not overlap ORCA's core novelty claim (runtime streaming + steering/control plane)
- Assumes post-hoc trace dataset (they convert raw traces into Parquet because raw traces are "not efficient for analysis purposes" and "incompatible with Pandas and Dask")

**Best positioned as:** Evidence that even after you already have trace data, "drill down iteratively" remains expensive without substrate that builds reusable views and optimizes representation—exactly the principle ORCA can generalize (but do online).

**Cites:**
- Darshan and companions (PyDarshan, DXT Explorer, VaniDL): I/O profiling + analysis tooling
- Recorder, Recorder-viz: choose Recorder because event-level traces suit their queries better than Darshan's aggregated stats; convert to Parquet for analysis
- UMAMI, TOKIO, IOMiner: holistic I/O analysis / log analytics systems
- Devarajan et al. (2022) "Extracting and characterizing I/O behavior of HPC workloads": close but lacks query/caching/format optimizations

---

