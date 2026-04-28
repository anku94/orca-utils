# AD/AE Appendix

Markdown mirror of the SC25 AD/AE LaTeX template (`ext/sc25-repro/for-paper-authors/sc25_ad_ae_template.tex`). Filled-in content here will be mechanically transcribed to LaTeX in `ext/sc26ad/sc26ad.tex`.

A0 below is the canonical template block carrying the LaTeX `\artexpl{}` instructions in italics — duplicate it as the starting point for any new artifact. Real artifact blocks (A1, A2, ...) omit the instructions and contain only filled-in content.

---

## AD Appendix

### Overview of Contributions and Artifacts

#### Paper's Main Contributions

- **C1 — Low-overhead tracing.** Always-on conventional tracing at ~0.8–2% overhead (vs 18–81% for TAU/dftracer), with Parquet traces 3.6–44× smaller than other formats. Figs. 5, 6, 8.
- **C2 — Faster post-mortem analysis.** ORCA traces enable post-mortem queries multiple orders of magnitude faster than other analytics-oriented tracers. Fig. 7.
- **C3 — In-situ analytics.** Operator pushdown lets MPI-tier flows run at sub-2% overhead while cutting data movement out of MPI ranks by 98.5–99.999%. Fig. 9 and Table 1. *Not supported by conventional tracers.*
- **C4 — Agentic debugging.** Steerable telemetry lets an LLM agent localize a months-long 4096-rank AMR anomaly in 27 minutes, with 144× volume reduction when reverting to baseline. Fig. 10. *Not supported by conventional tracers.*

#### Computational Artifacts

> *List the computational artifacts related to this paper along with their respective DOIs. Note that all computational artifacts may be archived under a single DOI.*

- **A1** ORCA-Augmented AMR Code
- **A2** Post-Mortem Query Scripts
- **A3** LLM Prompt for Agentic Workflow

#### Contributions × Artifacts table

> *Provide a table with the relevant computational artifacts, highlight their relation to the contributions (from above) and point to the elements in the paper that are reproducible by each artifact, e.g., which figures or tables were generated with the artifact.*

| Artifact ID | Contributions Supported | Related Paper Elements |
|---|---|---|
| A1 | C1, C3, C4 | Figs. 5, 6, 8 (C1) — Fig. 9 and Table 1 (C3) — Fig. 10 as the live system A3 attaches to (C4) |
| A2 | C2 | Fig. 7 |
| A3 | C4 | Fig. 10 |

### Artifact Identification

#### A0 — Template

##### Artifact–Contribution Relationship

> *Briefly explain the relationship between the artifact and contributions.*

TODO

##### Expected Outcome

> *Provide a higher level description of what outcome to expect from the corresponding experiments. Provide an explanation of how the results substantiate the main contributions. (Example: "Algorithm A should be faster than Algorithms C and B in all GPU scenarios.")*

TODO

##### Estimated Time

> *Estimate the time required to reproduce the artifact, providing separate estimates for the individual steps: Artifact Setup, Artifact Execution, and Artifact Analysis.*

- Setup: TODO
- Execution: TODO
- Analysis: TODO

##### Inputs

###### Hardware

> *Specify the hardware requirements and dependencies (e.g., a specific interconnect or GPU type is required).*

TODO

###### Software

> *Introduce all required software packages, including the computational artifact. For each software package, specify the version and provide the URL.*

TODO

###### Datasets / Inputs

> *Describe the datasets required by the artifact. Indicate whether the datasets can be generated, including instructions, or if they are available for download, providing the corresponding URL.*

TODO

###### Installation and Deployment

> *Detail the requirements for compiling, deploying, and executing the experiments, including necessary compilers and their versions.*

TODO

##### Computation

> *Provide an abstract description of the experiment workflow of the artifact. Identify the main tasks and their dependencies (e.g., T1 → T2 → T3 where T1 generates a dataset, T2 consumes it, and T3 produces final plots/tables). Provide details on experimental parameters — sizes, repetitions, statistical parameters — and why they were set as they were.*

TODO

##### Output

TODO

#### A1 — ORCA-Augmented AMR Code

##### Artifact–Contribution Relationship

A1 is the instrumented BSP workload — Phoebus + Parthenon's Sedov Blast Wave 3D AMR code linked against ORCA — used as the common substrate for three contributions:

- **C1** (Figs. 5, 6, 8): running A1 under different tracer configurations produces the runtime overhead, trace size, and architectural ablation measurements.
- **C3** (Fig. 9, Table 1): running A1 with ORCA's in-situ flows enabled produces the pushdown overhead and data-reduction measurements.
- **C4** (Fig. 10): A1 is the live system that A3's LLM agent attaches to and steers.

Artifact is provided with two profiles: _mini_ and _detailed_. 

- _Mini_ triggers short runs, sufficient to verify artifact function. 
- _Detailed_ requires 262 nodes on the PDL Wolf cluster and triggers longer experiments, necessary to replicate all results.

##### Expected Outcome

- _Mini_: three timesteps of a simple example program execute, generating Parquet traces.
- _Detailed_: 1000 timesteps of the Blast Wave code execute, generating Parquet traces. A baseline run is also triggered for comparison.

##### Estimated Time

- Setup: ~30 minutes (building the entire project)
- Execution: < 1 min for mini, 2-3 hours for detailed (Baseline and ORCA only)
- Analysis: < 10 minutes

##### Inputs

###### Hardware

- Mini: one multi-core Linux node
- Detailed: 262 nodes on the PDL Wolf cluster

###### Software

**Required dependencies, must be present in the build environment**

Versions used in evaluation environment are noted in parenthesis.
Other environments may necessitate tweaks to build params or API calls.

- A Linux environment (Ubuntu 22.04)
- An MPI implementation (MVAPICH2 2.3.7)
- C/C++ compiler (GCC 11.4)
- CMake (3.22)
- Rust toolchain (cargo/rustc, stable 1.92)
- TAU (2.34.1)

**Built by the `orca-umbrella` harness** (https://github.com/pdlfs/orca-umbrella; specific tags/pins to be frozen in the stable release):

*ORCA-Augmented AMR Code*

- ORCA — https://github.com/pdlfs/orca
- Phoebus — https://github.com/lanl/phoebus
- Parthenon — https://github.com/parthenon-hpc-lab/parthenon
- amr-tools — https://github.com/pdlfs/amr-tools
- Kokkos `4.0.01` — https://github.com/kokkos/kokkos
- HDF5 `1.12.2` — https://github.com/HDFGroup/hdf5

*ORCA runtime / data-path:*

- Apache Arrow `19.0.0` — https://github.com/apache/arrow
- Snappy `1.2.2` — https://github.com/google/snappy
- Mercury — https://github.com/mercury-hpc/mercury
- libfabric `v2.5.1` — https://github.com/ofiwg/libfabric
- DuckDB `v1.2.1` — https://github.com/duckdb/duckdb
- yaml-cpp `0.9.0` — https://github.com/jbeder/yaml-cpp
- PSM (forked) — https://github.com/pdlfs/psm

*Comparison tracers (for complete results replication):*

- DFTracer `v2.0.2` (forked) — https://github.com/anku94/dftracer
- Score-P `9.3` (patched, patch automatically applied during build) — https://www.vi-hps.org/projects/score-p/
- Caliper (patched, patch automatically applied during build) — https://github.com/LLNL/Caliper

###### Datasets / Inputs

- AMR decks: `blast_wave_3d.<nranks>.pin` (nranks in 512, 1024, 2048, 4096)
- `wfopts.yml`: tuned config for Wolf cluster, only needed for detailed profile

###### Installation and Deployment

Preparation commands (indicative, from Ubuntu 22.04, may vary across environments)

```bash
# Install basic utilities
sudo apt install -y gcc g++ make cmake autoconf automake libtool pkg-config git
# Install rust toolchain via rustup (non-interactive, stable)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
. "$HOME/.cargo/env"
```

Now, `orca-umbrella` can be built, and will also build the rest of the dependencies in-tree.

```bash
OR_PREFIX=/tmp/orca-prefix # Ideally a shared dir on cluster
OR_BUILD=$OR_PREFIX/build
OR_INSTALL=$OR_PREFIX/install

mkdir -p $OR_PREFIX $OR_BUILD $OR_INSTALL
git clone https://github.com/pdlfs/orca-umbrella.git $OR_PREFIX
cd $OR_BUILD
cmake -DCMAKE_INSTALL_PREFIX=$OR_INSTALL $OR_PREFIX/orca-umbrella
make -j16 # Replace with nproc
```

Once successfully built, all built artifacts will be available in `$OR_INSTALL`. Running the artifact:

`mini`: a script `run_amr_test.sh` available at `$OR_INSTALL/scripts`
`detailed`: Generate a valid hostfile as per MPI configuration, with at least 262 nodes,
and run `OR_HOSTFILE=/path/to/hostfile $OR_INSTALL/scripts/run_orca_detailed.sh`

##### Computation

- The relevant MPI codes are executed under exhaustive MPI/Kokkos trace collection modes,
as per the configured scales and timesteps. 
- (Detailed profile) Executes a baseline run and ORCA in lightweight and detailed modes,
and reports aggregated overhead at different scales.
##### Output

- Each run yields a per-run jobdir containing Parquet traces, organized by schema:

```
parquet/
|-- kokkos_events/
|   `-- ts=<timestep_range>/
|       `-- ranks=<rank_range>.parquet
|-- mpi_collectives/
|   `-- ...
|-- mpi_messages/
|   `-- ...
`-- orca_events/
```

- (Detailed profile) Wall-clock times are compared with baseline, and measured runtime overhead of different modes is reported.

#### A2 — Post-Mortem Query Scripts

##### Artifact–Contribution Relationship

A2 is the post-mortem analytics suite that executes a fixed query benchmark (Outlier Waits, Outlier Collectives, Timestamp Range) against traces captured by A1 under each tracer (ORCA, dftracer, Caliper). It supports **C2** by producing the query-latency comparison in Fig. 7.

##### Expected Outcome

The query suite runs against all available traces. Row counts in executed queries are displayed for verification and time taken by queries is logged as a CSV.

##### Estimated Time

- Setup: < 5 minutes
- Execution: < 1 minute (ORCA only)
- Analysis: < 1 minute

##### Inputs

###### Hardware

- One multi-core Linux node

###### Software

ORCA trace queries: Python 3 environment with Polars

- Python (3.12.11)
- Polars (1.39.3)
- Pandas (2.3.3)

###### Datasets / Inputs

Parquet traces generated by the AMR codes ran as A1.

###### Installation and Deployment

All Python scripts will be copied to `$INSTALL_TREE/scripts/orcaquery` during the `orca-umbrella` build (see A1).
Polars may be installed by running `pip install -r requirements.txt` or equivalent
for the test environment.

##### Computation

The script automatically detects all available runs in the suite, and runs
each query for each available run.

##### Output

Matching row counts emitted to stdout for verification of successful query execution, and
a CSV + a Pandas dataframe logged to stdout with the query latencies.

#### A3 — LLM Prompt for Agentic Workflow

##### Artifact–Contribution Relationship

A3 is the LLM agent specification — the prompt, tool wiring (ORCA controller CLI + Polars analytics), and operator-in-the-loop protocol — used to drive the agentic debugging session against a running 4096-rank instance of A1. It supports **C4** by producing the localization timeline in Fig. 10.

##### Expected Outcome

1. (Warmup) LLM is able to interface with the running code, manipulate its lifecycle (pause/result), request and analyze telemetry.
2. (Exercise) LLM is able to progressively localize the anomaly by requesting more telemetry.
3. Common case telemetry is two orders of magnitude less than detailed tracing.

Caveat: continued evolution in LLM capabilities and the interactive user-guided nature of the experiment intrinsically make this demonstration challenging to reliably replicate.
The anomaly demonstrated in the paper is specific to our fabric, which is relatively rare,
and requires our environment for reproduction.

##### Estimated Time

- Setup: 5 minutes
- Execution: < 1 hour
- Analysis: < 1 minute

##### Inputs

###### Hardware

See A1.

###### Software

See A1, plus:

- Claude Code with a valid Claude subscription or API key — https://www.anthropic.com/claude-code

###### Datasets / Inputs

A prompt `agentic-workflow.md` describing ORCA and documenting the experimental workflow.

###### Installation and Deployment

Claude code installation: `curl -fsSL https://claude.ai/install.sh | bash`

Deployment:
1. `run_orca_agentic.sh` triggers a 4096-rank AMR run with configuration parameters designed to disable anomaly mitigations and exacerbate occurences. Simulation starts in paused mode.
2. Claude Code must be started on another tab, and provided the IP/port of the controller interface of the ORCA controller. It is then asked to initiate the warmup exercise.
3. After the warmup exercise is complete, the agent should be asked to start the main exercise. Minimal and guided interventions may be necessary in case it makes suboptimal steering choices.

##### Computation

(Warmup) Agent interacts with ORCA, understands how to pause/resume the simulation, Parquet output structure, and analysis tools.
(Exercise) Agent uses high-level telemetry to detect the presence of stragglers, and progressively requests additional telemetry by writing custom in-situ flows to identify the root cause (up to MPI\_Wait, but not beyond).

##### Output

(Warmup) Manipulation effects are visible in simulation stdout
(Exercise) Agent reports a complete callflow graph of Kokkos regions up to the anomalous MPI\_Wait.

---

## AE Appendix

### A0 — Template

#### Inputs (install instructions)

> *Provide instructions for installing and compiling libraries and code. Offer guidelines on deploying the code to resources.*

TODO

#### Computation (workflow steps a reviewer runs)

> *Describe the experiment workflow. If encapsulated within a workflow description or equivalent (such as a makefile or script), clearly outline the primary tasks and their interdependencies. Detail the main steps in the workflow. Merely instructing to "Run script.sh" is inadequate.*

TODO

#### Output (expected results, methodology, correlation to paper claims)

> *Provide a description of the expected results and a methodology for evaluating these results. Explain how the expected results correlate with the contributions stated in the article. If the article presents results in a figure, the AE should produce a similar figure depicting the same generalizable outcome.*

TODO

### A1 — ORCA-Augmented AMR Code

#### Inputs (install instructions)

TODO

#### Computation (workflow steps a reviewer runs)

TODO

#### Output (expected results, methodology, correlation to paper claims)

TODO

### A2 — Post-Mortem Query Scripts

#### Inputs (install instructions)

TODO

#### Computation (workflow steps a reviewer runs)

TODO

#### Output (expected results, methodology, correlation to paper claims)

TODO

### A3 — LLM Prompt for Agentic Workflow

#### Inputs (install instructions)

TODO

#### Computation (workflow steps a reviewer runs)

TODO

#### Output (expected results, methodology, correlation to paper claims)

TODO
