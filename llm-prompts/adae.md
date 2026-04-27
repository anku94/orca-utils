# ADAE Appendix

## Context

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

## Goals (priority order)

1. **Basic AD appendix for SC26 submission.** Deadline-sensitive. Cursory is fine — just enough to signal compliance. Templates/paths to be located. Will be revised post-acceptance.
2. **Clean up build + scripts** for seamless unattended building and replication. Incremental work; experiment scope to be defined over time.
3. **Full AD/AE appendix.** Not due imminently, but wrap up now while context is fresh and before starting a new job.
