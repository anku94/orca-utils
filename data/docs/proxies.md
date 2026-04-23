# Why not use TSDBs as baseline

URL: https://chatgpt.com/share/689bf699-7600-800a-9c1e-45829c8dfc08

Your pushback is sound: a TSDB baseline is a **category error** for BSP-style, rank-partitioned, step-indexed observability. The mismatch is along fundamentals, not tuning.

# Why TSDB/OLAP isn’t a valid baseline for ORCA

* **Window semantics (time vs step):** TSDBs aggregate on wall-clock windows; BSP analysis is over **timestep windows** (semantic barriers). Rolling time bins introduce phase jitter and cross-rank skew; ORCA groups by `(rank, step[, micro, pp_stage…])` and aligns flush to the **BSP barrier**. That’s correctness, not a feature toggle.
* **Topology & fan-in:** A TSDB expects tens–hundreds of scrapers/agents, not **50k–100k producers**. You need a fleet of proxies/shards before ingestion. ORCA **is** that overlay (leaf→aggregator→controller), handling fan-in, backpressure, and failure domains.
* **Pushdown & data movement:** TSDBs ingest points, then aggregate **centrally**. ORCA pushes `project/filter/partial-agg` to leaves, ships only algebraic partials (and sketches), and reduces data volume by orders of magnitude **before** the network.
* **Data model:** TSDB = scalar time series keyed by labels; PromQL/InfluxQL style ops, no joins, limited relational expressiveness. ORCA = **columnar events + step summaries** with **SQL** over Arrow/Parquet and proper partition keys; joins (when needed) happen after pushdown at aggregator/controller.
* **Control semantics:** TSDBs do not provide **step-consistent control**. ORCA’s 2PC-at-step (non-blocking) makes sampling/zoom **causally aligned** with computation; you won’t get half-applied tracing during a step.
* **Transport & cost model:** TSDB paths assume TCP pull/push, per-metric cardinality explosions, and disk-heavy ingestion. ORCA keeps emission **in-memory**, RDMA when available, and persists **columnar** (Parquet) at the aggregation tier—cheaper CPU, fewer copies, far lower write amplification.
* **Operator cardinality / identity stability:** ML/HPC runs emit high-cardinality op IDs (per-kernel, per-bucket, per-stage). TSDB label sets blow up; ORCA dictionary-encodes IDs at source and preserves stable operator signatures through the pipeline.
* **Feasibility at scale:** If you “harden” a TSDB to cope (sidecars, pre-agg, step bucketing, fan-in proxies), you’ve **recreated ORCA’s overlay** minus RDMA and step-consistent control, and you still lack SQL pushdown at the leaf.

# What *does* constitute a fair baseline

* **Per-rank Kineto → JSON → offline ETL** into Parquet/ClickHouse, with post-hoc queries. (Today’s norm; offline, not real-time.)
* **Kineto with sidecar pre-aggregation** that bins by BSP step at the node and writes to an OLAP sink. (Closest “DB” variant; still lacks leaf pushdown and control semantics.)
* **Classic HPC stacks** (TAU/HPCToolkit/Caliper + ADIOS) doing trace→file→post-processing. (Mature, but offline and not step-consistent control.)

These baselines are inferior on the axes you care about (latency to insight, network volume, correctness under BSP semantics, ability to steer tracing at step granularity). They are baselines because they **exist**; a “TSDB that behaves like ORCA” does not.

# Evaluation dimensions (what you can state, crisply)

* **Overhead:** emitter + CUPTI budget (p99 and mean), target <\~2–3% wall time.
* **Latency to dashboard:** step-end → metric availability (ms).
* **Egress volume per step:** leaf→agg bytes vs total raw events; reduction factor from pushdown/sketches.
* **Scale:** max sustained producers (ranks/GPUs) and events/s without loss; backpressure behavior.
* **Correctness under BSP:** identical step windows across ranks; no cross-step bleed during control changes.
* **Query power:** expressiveness (SQL over step-partitioned frames) vs time-series algebra; ability to join with runtime/cluster telemetry.

If someone insists on a TSDB “baseline,” the honest statement is: to make it semantically comparable, you must add step-aware binning, leaf pre-aggregation, and an ingest overlay—at which point you’ve **reimplemented ORCA’s core**.

# Is PGBouncer the right mental model for these proxies?

Short answer: yes—PgBouncer is the *right* mental model for the **connection-multiplexing** problem, but production observability stacks also add **aggregation/sharding tiers** in front of the DB. ORCA is that whole overlay (pooling + sharding + pre-aggregation + step semantics), not just a pooler.

Concrete fan-in patterns you’d see in a conventional DC:

* **Prometheus → Mimir/Thanos**: you don’t point 50k producers at a DB. You deploy node agents/Prometheus shards, then a **receive/distributor → ingester** tier that **shards and replicates** incoming series via consistent hashing before storage/query tiers. (Mimir: *distributor shards & replicates to ingesters; replication-factor=3 by default*.) ([Grafana Labs][1])
  Thanos adds **sidecar/receiver/store-gateway** to fan-in and expose blocks; again, ingestion is fronted by dedicated components, not the DB directly. ([thanos.io][2])

* **VictoriaMetrics (cluster mode)**: producers push to **vmagent** (filter/relabel), which forwards to **vminsert → vmstorage**; reads go via **vmselect**. vmagent is the fan-in edge; vminsert handles sharding to storage nodes. ([VictoriaMetrics][3])

* **InfluxDB**: producers talk to **Telegraf** agents which buffer/transform and then write to the DB—again, fan-in via agents, not direct DB connections. ([docs.influxdata.com][4])

* **Graphite lineage**: you deploy **carbon-relay-ng** (or StatsD) as an **aggregating relay** in front of storage to reduce connection count and datapoint volume on the backend. ([Grafana Labs][5], [GitHub][6])

* **Uber M3**: explicit **coordinator/aggregator** tier that downsamples/rolls up streams before M3DB—i.e., a purpose-built fan-in/aggregation layer. ([Uber][7], [Medium][8])

Where PgBouncer fits: it’s a **connection pooler** that multiplexes many client sockets to a small server pool (good analogy for the *“100k writers → small backend socket budget”* pressure), but it doesn’t shard, pre-aggregate, or push down computations. TSDB stacks need both **pooling** and **ingest sharding/aggregation** tiers; they ship those as separate components. ([PgBouncer][9])

What that means for your claim

* “You need a fleet of proxies/shards before ingestion” — that’s exactly how Prom/Mimir/Thanos, VictoriaMetrics, Influx, Graphite/M3 are deployed at scale. ORCA *is* that fleet for BSP workloads, with two extras those systems don’t natively provide:

  1. **Semantic pushdown** (project/filter/partial-agg keyed by `(rank, step, …)`) before the network, and
  2. **Step-consistent control** (your 2PC at T) so zoom levels change atomically at BSP boundaries.
     The TSDB world’s fan-in tiers (distributor/receiver/vminsert/relay/agent) solve sockets and throughput; they don’t give you step windows or SQL pushdown at the leaf.

If someone insists on a TSDB baseline, the *fair* construction is: **agent/relay → per-node pre-aggregation keyed by step → receive/distributor → storage**, i.e., rebuild ORCA’s overlay with weaker semantics. The fact you must assemble that pipeline at all is the point.

[1]: https://grafana.com/docs/mimir/latest/references/architecture/components/distributor/?utm_source=chatgpt.com "Grafana Mimir distributor"
[2]: https://thanos.io/v0.6/thanos/getting-started.md/?utm_source=chatgpt.com "Thanos components"
[3]: https://docs.victoriametrics.com/victoriametrics/vmagent/?utm_source=chatgpt.com "VictoriaMetrics: vmagent"
[4]: https://docs.influxdata.com/influxdb3/clustered/write-data/use-telegraf/?utm_source=chatgpt.com "Use Telegraf to write data - InfluxData Documentation - InfluxDB"
[5]: https://grafana.com/docs/grafana-cloud/send-data/metrics/metrics-graphite/data-ingestion/?utm_source=chatgpt.com "Graphite data ingestion | Grafana Cloud documentation"
[6]: https://github.com/grafana/carbon-relay-ng/blob/main/docs/aggregation.md?utm_source=chatgpt.com "carbon-relay-ng/docs/aggregation.md at main"
[7]: https://www.uber.com/blog/m3/?utm_source=chatgpt.com "M3: Uber's Open Source, Large-scale Metrics Platform for Prometheus"
[8]: https://aiven-io.medium.com/m3-vs-other-time-series-databases-b307900c6f1a?source=---------2----------------------------&utm_source=chatgpt.com "M3 vs other time series databases | by Aiven - Medium"
[9]: https://www.pgbouncer.org/usage.html?utm_source=chatgpt.com "PgBouncer command-line usage"
