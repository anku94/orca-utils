Read `orca.md` for a high-level overview of what ORCA is.

Do not take the code organization too seriously. This is an auxiliary repo for the project.

The system is under submission at Supercomputing 2026. The goal is to prepare an artifact description/evaluation appendix.

Note that the above is a fairly complex/compound process, and part of the goal will be to refactor scripts and test builds, and part of it will be to prepare the actual document.

Do not jump the gun and only do what the user says insofar as they say it.

Use this file for memory/learnings. One bullet per appended memory when the user says (only).

Format is: <AGENT>: memory

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

# Memories/Context

- CLAUDE: `ext/sc25-repro/` is the official SC26 artifact submission instructions/template (cloned from https://github.com/weidendo/sc25-repro, maintained as a git subtree on `main`).
- CLAUDE: `ext/carp-sc24ad/` is the user's own SC24 CARP AD/AE appendix — reference for personal style/structure when drafting the SC26 ORCA appendix (not authoritative instructions).
- CLAUDE: `ext/mon-paper/` is the full ORCA paper draft (git subtree from https://github.com/anku94/mon-paper.git, `main`) — consult for paper context (claims, figures, sections) when drafting the AD/AE appendix.
- CLAUDE: LaTeX Makefile convention: `make` = build, `make draft` = build + copy to `drafts/YYYYMMDD_HH00.pdf`, `make rebuild` = clean + build, `make clean` = `latexmk -C`. (Reference Makefile lives at `~/Repos/thesis/thesis` on local mbp only — not present on cluster.)
- CLAUDE: `ext/` layout convention: third-party tracked upstream → git subtree (`ext/sc25-repro`); personal-reference snapshot → vendored copy (`ext/carp-sc24ad`); active work → plain dir (`ext/sc26ad`).
- CLAUDE: Do not create tech debt or exhibit short-term thinking. Be disciplined. Pause and ask user if something is uncertain.
