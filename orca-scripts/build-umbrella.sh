#!/usr/bin/env bash

set -eu

UMBRELLA_REPO="https://github.com/pdlfs/orca-umbrella"
UMBRELLA_BRANCH="adae"

# message: print an info line
message() {
    echo "-INFO- $@"
}

# die: print an error line and exit non-zero
die() {
    echo "-ERROR- $@" >&2
    exit 1
}

# assert_mpi_present: ensure mpicc and mpirun are on PATH, else die
assert_mpi_present() {
    command -v mpicc  >/dev/null 2>&1 || \
        die "mpicc not in PATH; export MPI_HOME and PATH=\$PATH:\$MPI_HOME/bin"
    command -v mpirun >/dev/null 2>&1 || \
        die "mpirun not in PATH; export MPI_HOME and PATH=\$PATH:\$MPI_HOME/bin"
    message "mpicc:  $(command -v mpicc)"
    message "mpirun: $(command -v mpirun)"
}

# assert_rust_present: ensure cargo and rustc are on PATH (needed by rsflow), else die
assert_rust_present() {
    command -v cargo >/dev/null 2>&1 || \
        die "cargo not in PATH; install rust (e.g. via rustup) and source \$HOME/.cargo/env"
    command -v rustc >/dev/null 2>&1 || \
        die "rustc not in PATH; install rust (e.g. via rustup) and source \$HOME/.cargo/env"
    message "cargo: $(command -v cargo) ($(cargo --version 2>/dev/null))"
    message "rustc: $(command -v rustc) ($(rustc --version 2>/dev/null))"
}

# install_rust: install a rust toolchain via rustup (currently unused; reserved for future)
install_rust() {
    message "Installing rust toolchain via rustup"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    # shellcheck disable=SC1091
    . "${HOME}/.cargo/env"
    message "rustc: $(rustc --version)"
}

# perform_checks: run all environment preflight checks (read-only)
perform_checks() {
    message "Running preflight checks"
    assert_mpi_present
    assert_rust_present
}

# prompt_path: prompt for a path with a default
# if VARNAME is already set (e.g. via env), skip the prompt and use that
# usage: prompt_path VARNAME "label" "default"
prompt_path() {
    local __var=$1
    local __label=$2
    local __default=$3
    local __current="${!__var:-}"
    if [ -n "${__current}" ]
    then
        message "${__label}: ${__current} (from env)"
        return 0
    fi
    local __reply
    read -r -p "  ${__label} [${__default}]: " __reply
    if [ -z "${__reply}" ]
    then
        __reply="${__default}"
    fi
    printf -v "${__var}" '%s' "${__reply}"
}

# main: guided clone + configure + build of the orca-umbrella tree
main() {
    message "ORCA umbrella guided build"
    perform_checks

    # seed from env if exported, else leave empty so prompt_path will ask
    local CLONE_PREFIX="${CLONE_PREFIX:-}"
    local BUILD_PREFIX="${BUILD_PREFIX:-}"
    local INSTALL_PREFIX="${INSTALL_PREFIX:-}"
    local TREE
    prompt_path CLONE_PREFIX   "Clone prefix (tree parent dir)" "${HOME}/orca-tree"
    TREE="${CLONE_PREFIX}/orca-umbrella"
    prompt_path BUILD_PREFIX   "Build prefix"                   "${TREE}/build"
    prompt_path INSTALL_PREFIX "Install prefix"                 "${TREE}/install"

    if [ ! -d "${TREE}" ]
    then
        message "Cloning ${UMBRELLA_REPO} (branch: ${UMBRELLA_BRANCH}) -> ${TREE}"
        mkdir -p "${CLONE_PREFIX}"
        git clone -b "${UMBRELLA_BRANCH}" "${UMBRELLA_REPO}" "${TREE}"
    else
        message "Tree present at ${TREE}, skipping clone"
    fi

    mkdir -p "${BUILD_PREFIX}" "${INSTALL_PREFIX}"

    message "Configuring (install prefix: ${INSTALL_PREFIX})"
    ( cd "${BUILD_PREFIX}" && cmake -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" "${TREE}" )

    message "Building with make -j16"
    ( cd "${BUILD_PREFIX}" && /usr/bin/make -j16 )

    message "Done. Install: ${INSTALL_PREFIX}"
}

main
