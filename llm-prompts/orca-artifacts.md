Read `orca.md` for a high-level overview of what ORCA is.

Do not take the code organization too seriously. This is an auxiliary repo for the project.

The system is under submission at Supercomputing 2026. The goal is to prepare an artifact description/evaluation appendix.

Note that the above is a fairly complex/compound process, and part of the goal will be to refactor scripts and test builds, and part of it will be to prepare the actual document.

Do not jump the gun and only do what the user says insofar as they say it.

Use this file for memory/learnings. One bullet per appended memory when the user says (only).

Format is: <AGENT>: memory

## List of Figures

- **Fig. 1** — `fig:orca:bg-volatile`, §2. Background/Irrelevant (AMR anomaly motivation; same anomaly is later localized in §6.3).
- **Fig. 2** — `fig:orca:des-arch`, §4. Design/Irrelevant (architecture diagram).
- **Fig. 3** — `fig:orca:des-plan`, §4. Design/Irrelevant (OrcaFlow query plan).
- **Fig. 4** — `fig:orca:des-twopc`, §4. Design/Irrelevant (TS2PC control-plane protocol).
- **Fig. 5** — `fig:orca:eval-runtime`, §6.1.1. Runtime overhead vs TAU/Score-P/Caliper/dftracer, 512–4096 ranks. *C1*
- **Fig. 6** — `fig:orca:eval-tracesize`, §6.1.2. Trace size + per-record size by tool/format. *C1*
- **Fig. 7** — `fig:orca:eval-query`, §6.1.3. Post-mortem query latency (3 queries) vs dftracer/Caliper. *C1*
- **Fig. 8** — `fig:orca:eval-arch` (8a `eval-arch-dft`, 8b `eval-arch-tcp`), §6.1.4. Architectural ablations at 512 ranks: (a) compression cost, (b) verbs vs TCP transport. *C1*
- **Fig. 9** — `fig:orca:eval-ontv`, §6.2. In-situ flows: runtime overhead + data reduction at MPI tier across scales. *C2*
- **Fig. 10** — `fig:orca:eval-agentic`, §6.3. Agentic debugging timeline at 4096 ranks. *C3*
- **Table 1** — `tab:ontv-flows`, §6.2. Three in-situ flows: mpiwait count, mpiwait → Parquet, AMR compute imbalance. *C2*

## Goals (priority order)

1. **Basic AD appendix for SC26 submission.** Deadline-sensitive. Cursory is fine — just enough to signal compliance. Templates/paths to be located. Will be revised post-acceptance.
2. **Clean up build + scripts** for seamless unattended building and replication. Incremental work; experiment scope to be defined over time.
3. **Full AD/AE appendix.** Not due imminently, but wrap up now while context is fresh and before starting a new job.

## Context

This workflow will span multiple copies of this repo: local (my macbook) and remote (cluster on which the system actually works). Do not assume you have access to both.

- **ORCA**: see [orca.md](orca.md) — observability/control runtime, ~40K LOC C++/Rust, layout under `orca/src/{client,common,core,trace,flow,overlay,rsflow,...}`.
- **ORCA umbrella build system**: see [orca-umbrella.md](orca-umbrella.md) — CMake-based fetch/build of the full dep tree.
- **Build branch tracked for ADAE**: `adae` of `pdlfs/orca-umbrella` (set as `UMBRELLA_BRANCH` in `orca-scripts/build-umbrella.sh`).
- **Driver scripts**: `orca-utils/orca-scripts/build-umbrella.sh` (guided) and `build-umbrella-aj.sh` (hardcoded instantiation).
- **Stack pinned for the artifact build**:
  - phoebus: `anku94/phoebus` @ `lb`
  - parthenon: `anku94/parthenon` @ `lb3bar`
  - kokkos: `4.0.01` (min 4.x; phoebus forces `PARTHENON_IMPORT_KOKKOS=ON`)
  - hdf5: `hdf5_1_12_2`, parallel ON
  - orca: `pdlfs/orca` @ `main`
- **Working reference build** (read-only): `/l0/orcaroot/orca-umbrella` (fully built tree, install at `/users/ankushj/repos/orca-workspace/orca-umb-install`) — used to cross-check artifacts.
- **WIP appendix scratchpad**: [adae.md](adae.md) — markdown mirror of the SC25 AD/AE LaTeX template, where appendix content (contributions, artifacts, per-artifact subsections) is accumulated before being transcribed to `ext/sc26ad/sc26ad.tex`.

# Memories/Context

- CLAUDE: `ext/sc25-repro/` is the official SC26 artifact submission instructions/template (cloned from https://github.com/weidendo/sc25-repro, maintained as a git subtree on `main`).
- CLAUDE: `ext/carp-sc24ad/` is the user's own SC24 CARP AD/AE appendix — reference for personal style/structure when drafting the SC26 ORCA appendix (not authoritative instructions).
- CLAUDE: `ext/mon-paper/` is the full ORCA paper draft (git subtree from https://github.com/anku94/mon-paper.git, `main`) — consult for paper context (claims, figures, sections) when drafting the AD/AE appendix.
- CLAUDE: LaTeX Makefile convention: `make` = build, `make draft` = build + copy to `drafts/YYYYMMDD_HH00.pdf`, `make rebuild` = clean + build, `make clean` = `latexmk -C`. (Reference Makefile lives at `~/Repos/thesis/thesis` on local mbp only — not present on cluster.)
- CLAUDE: `ext/` layout convention: third-party tracked upstream → git subtree (`ext/sc25-repro`); personal-reference snapshot → vendored copy (`ext/carp-sc24ad`); active work → plain dir (`ext/sc26ad`).
- CLAUDE: Do not create tech debt or exhibit short-term thinking. Be disciplined. Pause and ask user if something is uncertain.
