## AE Appendix

Commented out in `sc26ad.tex`, to be filled in later.

## Evaluation 0

### Artifact Setup

Provide instructions for installing and compiling libraries and code. Offer guidelines on deploying the code to resources.

### Artifact Execution

Describe the experiment workflow. If encapsulated within a workflow description or equivalent (such as a makefile or script), clearly outline the primary tasks and their interdependencies. Detail the main steps in the workflow. Merely instructing to "Run script.sh" is inadequate.

### Artifact Analysis

- Provide a description of the expected results and a methodology for evaluating these results.
- Explain how the expected results from the experiment workflow correlate with the contributions stated in the article.
- For example, if the article presents results in a figure, the artifact evaluation should also produce a similar figure, depicting the same generalizable outcome. Authors must focus on these aspects to reduce the time required for others to understand and verify an artifact.

## Evaluation 1

### Artifact Setup

We provide instructions for evaluating ORCA functionality using a single Linux node. We recommend using Ubuntu 22.04 or 24.04 to build and run the artifact, as minor changes in package names etc. can break compatibility.

First, C++ and Rust toolchains must be available, as well as an MPI implementation (not covered here). For Ubuntu 22.04, following commands set up the necessary build tooling, except for MPI.

```bash
# Install basic utilities
sudo apt install -y gcc g++ make cmake autoconf \
automake libtool pkg-config git

# Install rust toolchain via rustup (non-interactive, stable)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
| sh -s -- -y --default-toolchain stable
. "$HOME/.cargo/env"
```

Now, ORCA can be built via the `orca-umbrella` artifact. The artifact bundles vendored versions of ORCA along with key dependencies, scripts etc. Internet access is required for third-party Rust/Python dependencies.

```bash
# For mini runs, OR_PREFIX can be any path on the filesystem
OR_PREFIX=/tmp/orca-prefix
OR_BUILD_DIR=$OR_PREFIX/build
OR_INSTALL_DIR=$OR_PREFIX/install
mkdir -p $OR_PREFIX $OR_BUILD_DIR $OR_INSTALL_DIR

# Obtain orca-umbrella via git-clone, or via Zenodo artifact.
# $ORCA_CMAKE_ROOT must point to the CMake project root.
# Zenodo zips sometimes add a hash after file/dir names.
git clone https://github.com/pdlfs/orca-umbrella.git $OR_PREFIX/orca-umbrella
ORCA_CMAKE_ROOT=$OR_PREFIX/orca-umbrella
ls $ORCA_CMAKE_ROOT # Must list: CMakeLists.txt, cache, etc.

cd $OR_BUILD_DIR
cmake -DCMAKE_INSTALL_PREFIX=$OR_INSTALL_DIR $ORCA_CMAKE_ROOT
make -j<nproc> # Takes 20-30 mins

# Polars required for Artifact 2, but demo script 
# interleaves workflows, so it should be installed upfront.
pip install -r $OR_INSTALL_DIR/scripts/requirements.txt
```

Once successfully built, all artifacts will be available in `$OR_INSTALL`, with scripts in `$OR_INSTALL/scripts`.

### Artifact Execution

Once built, `run_orca_ae.sh` will provide a guided tour of all artifact functionality. The following commands are provided for reference, but need not be executed manually.

The script will run 10 timesteps of an AMR code augmented with ORCA under different modes. A single run involves:
- The AMR code, run as 16 ranks of `phoebus` with Sedov Blast Wave decks generated from `decks/blast_wave_3d.512.pin.in`. The AMR code has been modified to link with ORCA's client module.
- ORCA nodes: a single controller and aggregator (`controller_main` and `aggregator_main`, respectively), running on the same node.

A number of tunable parameters are described in `defaults.yml`, passed to ORCA nodes via the env-var `ORCA_CFG_YAML`. All parameters can be overridden using corresponding env-vars, and the scripts override some params to appropriate values for the AMR code.

The script will demonstrate ORCA analytics and control capabilities. Analytics are controlled using OrcaFlow (ORCA's SQL-based programmable interface) and control commands. We explain these using examples.

1. `bootstrap_cmdseq: set-flow enable-tracers; resume` in `defaults.yml` defines two commands supplied by the controller to the simulation at bootstrap. `set-flow enable-tracers` activates all telemetry from all available trace streams (currently MPI and Kokkos), and `resume` asks the simulation to begin right after. ORCA-enabled simulations initialize in a paused state and start only once they have an initial set of commands.
2. At any point while the simulation is running, additional commands may be supplied using the `cmdrunner_main` binary. The same YAML is used by the binary to locate the controller's IP and port to send commands. E.g. `cmdrunner_main "pause"` will pause the simulation.
3. Flows are SQL-based transforms written as OrcaFlow YAMLs, and sent to the application via command `set-flow file <path/to/flow.yml>`. They are committed via TS2PC at runtime, and all pushdowns are applied at the timestep for which the command is committed.
4. Any active telemetry streams are persisted as timestep-partitioned Parquet or DuckDB at either the controller or the aggregators. The scripts only show the Parquet pathway. Parquet files are flushed at configurable timestep intervals.
5. Additional probes may be enabled or disabled at any point while the simulation runs.

### Artifact Analysis

As the workflow above demonstrates capabilities, minimal analysis is required. The following capabilities are demonstrated:
1. Basic telemetry collection and persistence as Parquet via aggregators and controller, with minimal in-situ analytics.
2. An example of SQL-based OrcaFlow analytics, showing pushdown impact on data volume.
3. Interactive control capabilities while the simulation runs: the script demonstrates basic PAUSE/RESUME function, but users are encouraged to try other commands at runtime.

## Evaluation 2

### Artifact Setup

`scripts/run_queries.py` is provided to demonstrate basic analyses over ORCA-generated Parquet. As the format is an industry standard, the goal is basic validation of ORCA-collected telemetry, and not a comprehensive demonstration of format capabilities. 

### Artifact Execution

The script consists of basic Polars queries emitted against the generated Parquet. The following telemetry streams will be available:


```text
parquet/
|-- kokkos_events/
|   `-- ts=<timestep_range>/
|       `-- ranks=<rank_range>.parquet
|-- mpi_collectives/
|   `-- ...
|-- mpi_messages/
|   `-- ...
`-- orca_events/ # ORCA-internal telemetry
```

### Artifact Analysis

ORCA telemetry is guaranteed to be timestep-partitioned. Each `ts=<beg>_<end>` directory only contains telemetry for that timestep. The script will demonstrate this briefly.

## Evaluation 3

### Artifact Setup

The artifact consists of a prompt that was provided to Claude Code in an environment where ORCA was run on a cluster with a known pathology, along with the conversation transcript. While this artifact is provided for archival purposes, ORCA's control capabilities are evaluated via manual invocation of `cmdrunner_main` as described above.

### Artifact Execution

```bash
# Controller is found via ORCA_CFG_YAML, 
# or env vars ORCA_CTL_DASHHOST:ORCA_CTL_DASHPORT
cmdrunner_main "<cmd>"
# cmd = pause | resume | status | set-flow <file> etc.
```

### Artifact Analysis

When run, commands trigger a timestep-linked two-phase commit to control the application. Different protocol messages, such as prepare/commit times, current delta etc. appear on console as the protocol proceeds.
