## Report: ORCA vs Holmes (and the “COG” weirdness), plus 3D parallelism + NCCL/PyTorch group plumbing

### 1) Why Holmes’s COG construction feels wrong

* Holmes defines a bipartite “communication operator graph” with operator nodes and GPU nodes, with an edge if a GPU participates in an operator.
* They claim the naive edge count is (|E| = |O|\cdot |D|), which implicitly assumes **every comm op spans all GPUs**.
* In real 3D training, most communication is scoped to **DP/TP/EP/PP groups**, so per-op participation is (k) (group size), not (|D|). The natural count is (|E|\approx |O|\cdot k), often with (k\ll |D|).
* Their “curse of dimensionality” framing is therefore misleading. Hierarchical group-scoped collectives are the entire point of training communication structure (NVLink/NVSwitch islands, etc.).

### 2) “Grouping reconstruction” is mostly “use communicator IDs”

* Holmes’s fix is to substitute GPUs with “groups” and connect each operator to one group node.
* Conceptually, this is just **representing an operator as belonging to a communicator/process group** instead of enumerating per-member edges.
* That is not a novel insight; it is the normal representation in distributed runtimes. It looks like they defined an intentionally inflated representation to justify a graph contribution.

### 3) Why this makes ORCA’s relational story look “complex”

* Holmes turns “per-group comparisons + aggregation” into “graph construction + traversal,” which can make straightforward ORCA-style logic (GROUPBY/AGG/MAX–MIN/outliers) look like it requires fancy graph algorithms.
* For collectives, the core work is: “for a given (group, collective-id, iteration), compare replicas across members,” which is naturally a **groupby aggregate**.

### 4) “BFS for collective communication” is mostly nonsense

* Their line about BFS “traversing GPUs within a collective group” reads like:

  * given an abnormal collective instance, find its group and check the same collective across all GPUs in that group.
* That is not BFS; it is “iterate members and compute all/any predicates” (all abnormal → likely comm; some normal → look for compute-side late arrival).
* Graph search becomes more defensible only when they **alternate** between:

  * the per-GPU execution-order chain (“previous op”), and
  * cross-rank group membership (“same collective across peers”),
    which is basically packaging repeated joins/filters as BFS.

### 5) When traversal is actually justified: P2P / pipeline edges

* For point-to-point/pipeline structures, there is a directed dependency graph (send→recv, stage→stage).
* Localization can require walking predecessors (“who blocked me”), which is a real causal-chain traversal problem.
* For collectives, the structure is closer to “replicated op over a communicator,” so groupwise aggregation is the right primitive.

### 6) What Holmes is trying to decide (the underlying diagnosis question)

* They observe inflated “compute + sync/comm time” and want to attribute it to:

  * **compute-side delay** on one/few ranks (late arrival → others wait inside comm),
  * versus **communication-side slowdown** (everyone enters on time but the collective itself runs long).

### 7) ORCA mapping and the correct “online vs intra-iteration” distinction

* ORCA’s default emission is **end-of-timestep / end-of-iteration flush** (streaming-batch / nearline).
* That is still “online control” at timestep cadence (e.g., 200 ms later), not “post-hoc” in the sense of accumulating giant logs and analyzing later.
* The real missing capability is **intra-iteration progress under non-completion**:

  * If a rank hangs or a mid-iteration collective never completes, end-of-iteration flush never happens, so you need a separate progress signal.

### 8) ProgressTracker applet: coherent separation

* The decomposition is coherent:

  * keep timestep dataframes for high-volume analysis;
  * add a low-rate ProgressTracker applet that emits pre/post markers per collective (or other monotonic progress signals).
* This is primarily needed to stay online under **fail-stop/hang** (no flush boundary). It is not required just to detect fail-slow at timestep cadence.

### 9) Sync points are the only clean causal anchors

* Between synchronizations, timelines overlap and attribution becomes underdetermined.
* The practical diagnosis strategy is:

  * collect intermediate events (per-collective markers) into the timestep dataframe;
  * anchor reasoning at stalls/spreads at sync points;
  * walk backward from sync stalls to attribute compute-side vs comm-side contributions.
* This is exactly where Holmes’s graph machinery largely implements what ORCA can express as grouped aggregates plus predecessor joins.

### 10) “ORCA conceptually subsumes Holmes” — what is safe to claim

* Defensible claim: **ORCA can express/host Holmes-style diagnosis logic** as applets/operators (groupwise comparisons, spreads/outliers, predecessor linkage).
* Required honesty: ORCA is currently missing implementation details needed for a faithful reproduction:

  * 3D topology/group ID plumbing (DP/TP/EP/PP group identification and stable IDs),
  * any per-collective event capture needed within the timestep,
  * traversal kernels as needed in OrcaFlow for performance.
* Framing that stays true: “Holmes affirms ORCA’s substrate claim” (diagnosis reduces to BSP boundary signals + groupwise aggregates), not “ORCA already matches their full system end-to-end.”

### 11) NCCL: what it can tell you

* NCCL fundamentally operates on **communicators** (groups of ranks). It does not know DP/TP/PP/EP semantics.
* NCCL can expose **physical topology** via debug/topology dump mechanisms (e.g., topology dump files/log subsystems), but it does not provide a clean public API that returns “this collective’s schedule/topology” as a structured object for arbitrary frameworks.
* The right source of DP/TP/EP/PP semantics is above NCCL: the framework that created the groups.

### 12) Where DP/TP/PP/EP group IDs come from

* In Megatron/DeepSpeed/PyTorch stacks, DP/TP/PP/EP are realized by constructing **separate process groups** and routing different collectives/p2p ops to those groups.
* NCCL sees only a communicator; the label “this is DP” lives in framework code.

### 13) “Universal PyTorch interface” question

* What is universal: PyTorch distributed can give you **group membership/rank mappings** if you have the `ProcessGroup` handle (rank list, translations, sizes).
* What is not universal: a portable, stable way to label a group as **DP vs TP vs EP vs PP** across Megatron/DeepSpeed variants.
* So:

  * framework-agnostic instrumentation can record “which group was used” + membership;
  * DP/TP/EP/PP semantics typically require hooks at the framework layer (or heuristics, which are brittle).
