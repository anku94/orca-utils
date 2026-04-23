**TrainCheck (Jiang et al., OSDI '25)**

Framework for detecting silent correctness errors in DL training via automatically inferred training invariants. Offline phase collects traces from known-good sample pipelines and infers invariants with preconditions from five relation templates. Online phase selectively instruments the target pipeline and continuously validates. Detects 18/20 reproduced real-world silent errors within one training iteration. Found 6 unknown bugs in DeepSpeed/Accelerate.

**Relation templates and ORCA mapping**

Five templates, each a predicate over variables (V = object attribute, typically tensor hash), events (E = API call with duration/nesting), or API invocations (I = call identity with args/outputs):

- **Consistent(Va, Vb)**: Va and Vb should have the same value across ranks. Cross-rank check. In ORCA: GROUP BY (name, timestep), COUNT(DISTINCT hash) over timestep dataframe. Partial aggregation at AGG, merge at CTL. Fixed-size intermediates regardless of rank count.
- **EventContain(Ea, Eb)**: Eb must occur within the duration of Ea. Per-rank, per-timestep. In ORCA: filter for Ea and Eb, check containment via map kernel. Pushable to MPI.
- **APISequence(Ia, Ib, ...)**: calls must all occur in specified order. Per-rank. In ORCA: needs a map kernel (ordering over event stream is not SQL-native). Pushable to MPI.
- **APIArg(Ia, is_distinct)**: argument consistency or distinction across calls. Per-rank. In ORCA: likely needs a kernel depending on argument encoding. Pushable to MPI.
- **APIOutput(Ia, bound_type)**: output attributes meet constraints relative to input attributes (dtype matching, shape relationships). Per-rank. In ORCA: predicate filter if attributes are columns, kernel otherwise. Pushable to MPI.

**Anomaly catalog by relation**

*Consistent:*
- Weight divergence across TP ranks from gradient clipping bug in BF16Optimizer (B3/DeepSpeed-1801, BLOOM-176B): precondition `tensor_model_parallel=false && UNEQUAL(TP_RANK)` (§2.2, Fig. 4)
- DDP weight desync from missing gradient sync hooks during serialization (B9/PyTorch-104336)
- DDP weight desync from calling forward on inner module instead of DDP wrapper (B10)
- P2P data loss from incorrect I/O setup (B2/PyTorch-84803, B17/PyTorch-96600)
- P2P data loss from faulty driver (B18)
- DeepSpeed silently overwriting model "id" attributes causing wrong placement (DS-6772)
- Incomplete checkpoints from freezing params before DeepSpeed init (DS-5489)

*EventContain:*
- Optimizer not updating model due to torch.dynamo missing guard (B8/PyTorch-115607): `optimizer.step` should contain parameter data changes
- Optimizer initialized before DDP wrapping, has wrong params (AC-2665): `optimizer.step` should contain math ops on parameters
- Repeated parameter reinitialization from logic bug (B13/TF-17877)

*APISequence:*
- Missing `zero_grad` causing gradient accumulation (B4)

*APIArg:*
- MoE all2all invoked with conflicting arguments causing hang (DS-6714)
- Dropout not set to 0 during eval in flash attention (B12/TF-33844)
- Autocast dtype not respected by function transform (B7/LT-725)

*APIOutput:*
- Input processor returning only first batch item, shape mismatch (B11/TF-34204)
- Misconfiguration causing only BatchNorm layers enabled (B1/PyTorch-Forum-84911)
- Data loader workers having same seed (B6)
- Truncation bug causing output longer than threshold (B5/TF-23723)

**Invariant discovery vs. checking.** TrainCheck's offline inference (Algorithm 2) brute-forces over all variable pairs and attribute combinations to discover which invariants hold, then deduces preconditions to separate passing from failing examples. This combinatorial search compensates for an unstructured flat trace (JSON records with no rank/timestep organization). With ORCA's timestep dataframes — where rank is a dimension and timestep is the partition key — hypothesis generation for Consistent reduces to a single GROUP BY. The structured data model makes invariant *discovery* simpler, not just invariant *checking* cheaper.

**Other notable points**

- Empirical study of 88 real-world silent errors: 32% user code, 32% framework, 12% math ops, 12% HW/driver, 8% compiler (§2.1, Fig. 2)
- BLOOM-176B error undetected for 10 days, 9 more to mitigate; 384 A100 GPUs, 3.5 months (§2.2)
- BloombergGPT loss plateaued 7 days before anyone noticed (§7, citing [44])
- Invariants inferred from 2-GPU, 100-iteration runs transfer to large-scale training (§3.9)
- 23% of PyTorch-level invariants apply to 16+ unrelated pipelines (§5.4)
- Instrumented 2-GPU 70M-param BLOOM pipeline: ~92K records, 50MB per iteration (§3.8)
- Online checking overhead <2% with selective instrumentation for 100 invariants (§5.7)
- Cannot analyze JIT-compiled paths or C++/CUDA internals like FlashAttention (§6)