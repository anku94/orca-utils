# Parallelism Dimensions in Distributed ML Training

URL: https://chatgpt.com/share/689bf699-7600-800a-9c1e-45829c8dfc08

Good way to think about “windows”: use **the smallest sync that is (a) deterministic and (b) shared by all ranks in the relevant group**. Different parallelisms give you different groups and syncs.

Below is “what collectives happen where” and **which window key to use**.

---

## 0) Baseline DP (with grad bucketing, GA)

**Collectives:** per-bucket **all-reduce** (or reduce-scatter/all-reduce depending on stack) of gradients.

* **Microstep window (GA>1):** from first backward op of microstep → **completion of the last grad bucket collective** for that microstep on the DP group.
* **Macro step window:** after GA microsteps, **optimizer step** completion (often implies final grad all-reduce done).

Record: `bucket_id`, `dp_group`, `microstep`, `global_step`. Use “last bucket done” as the barrier.

---

## 1) ZeRO / FSDP (parameter/state sharding)

**Collectives:**

* **ZeRO-2 / FSDP:** gradients via **reduce-scatter** per bucket; later **all-gather** if needed.
* **ZeRO-3 / FSDP full-shard:** per-layer **param all-gather** **before forward**, **reduce-scatter** grads **after backward**, then **reshard**.
* **Window:** same DP logic for micro/macro step. If you want a stricter per-layer window, use *(layer\_i param all-gather start → its grad reduce-scatter done)*, but your **global** window still anchors on the **final grad RS** (or optimizer step) in the DP group.

Record: `fsdp_unit_id|layer_id`, `{param_allgather, grad_reducescatter}`, `bucket_id`.

---

## 2) Tensor Parallel (Megatron TP)

(Weights/activations split across a TP group within each layer.)
**Collectives (typical Megatron patterns):**

* **ColumnParallelLinear:** forward often ends with **all-gather (concat)** of partial outputs (unless kept sharded); backward uses **reduce-scatter/all-reduce** for grads.
* **RowParallelLinear:** forward ends with **all-reduce (sum)** of partial outputs; backward does the complementary collective.
* Attention: heads usually sharded → minimal collectives inside; **output projection** often does an **all-reduce**.
* **Window:** TP collectives are **intra-layer syncs** inside the step; they are *not* a job-wide barrier. Keep your **global step window = DP window**. Optionally define **TP sub-windows per layer op** if you want fine attribution.

Record: `tp_group`, `layer_id`, `{allreduce, allgather, reducescatter}`, `phase={fwd,bwd}`.

---

## 3) Pipeline Parallel (PP)

(Stages hold disjoint layer ranges; microbatches stream through.)
**Comms:** mostly **point-to-point send/recv** of activations/gradients between adjacent stages; **no global collective per microbatch**. If combined with DP, you still have the DP grad collectives.

* **Stage-local microbatch window:** *(recv activation for (step s, microbatch m)) → (send grad upstream for (s,m))* on each stage.
* **Macro step window:** across the PP mesh, **after the last microbatch of step s flushes** and **DP grad collectives complete**, then optimizer step.
* There is **no single per-microbatch global barrier** across all PP ranks—don’t force one.

Record: `pp_stage`, `microbatch_id`, `{act_send/recv, grad_send/recv}` timestamps + DP window markers.

---

## 4) Sequence Parallel (SP)

(Shard along sequence length to cut activation memory.)
**Collectives:** paired **all-gather / reduce-scatter** around ops that need full-sequence visibility (e.g., residual joins, certain norms), arranged to replace would-be all-reduces.

* **Window:** treat these as **intra-layer syncs**; they don’t redefine step boundaries. Keep DP window for global; optionally add **per-layer SP sub-windows**.

Record: `sp_group`, `layer_id`, `{allgather, reducescatter}`, `phase`.

---

## 5) Expert / MoE Parallelism

(Tokens routed to experts; experts sharded across GPUs.)
**Collectives:** two **all-to-all** per MoE layer in forward (dispatch tokens → experts, combine back), mirrored in backward; plus whatever DP/TP you also use.

* **Window:** MoE **all-to-all** are strong **layer-local syncs**; the **global** window remains the DP macro/micro step boundary.

Record: `ep_group`, `moe_layer_id`, `{alltoall_forward, alltoall_backward}`, `topk`, load metrics.

---

## 6) CUDA Graphs, Activation Checkpointing, Mixed Parallelism

* **CUDA Graphs:** doesn’t change sync points; it just makes the intra-step sequence more static. Keep the same windows.
* **Activation checkpointing:** shifts work across fwd/bwd but **doesn’t add collectives**—windows unaffected.
* **Composed parallelism (DP+TP+PP+SP+MoE):** use **composite keys**. Global window = **DP**; add **nested sub-windows** per TP/PP/SP/MoE event if you need finer attribution.

---

## Practical window keys to stamp on every event row

```
(global_step, microstep,
 dp_group, bucket_id,
 pp_stage, microbatch_id,
 tp_group, sp_group, ep_group,
 layer_id, phase={fwd|bwd})
```

Then:

* **Global analysis**: group by `(global_step[, microstep], dp_group)` → DP windows.
* **Stage-local** (PP): group by `(pp_stage, microbatch_id)`.
* **Layer/TP/SP/MoE attribution**: aggregate within DP window but slice by the corresponding group keys.

That’s the minimal scheme that lets you use **collective completions** as unambiguous window boundaries where they exist (DP/ZeRO/FSDP), and **stage-local send/recv** where they don’t (PP), without inventing fake barriers.