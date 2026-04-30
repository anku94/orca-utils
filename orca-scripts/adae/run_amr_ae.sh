#!/usr/bin/env bash
#
# AE driver for A1: invokes run_amr.sh once, looping internally over a small
# AE-scale profile set. Tweak any of the below blocks (env, profiles) for
# partial trials. This is a documentation-of-intent skeleton; expect to
# revise it against real runs.
#

set -eu
SCRIPT_DIR=$(dirname $(realpath $0))
PARENT_DIR=$(dirname $SCRIPT_DIR)

# setup_paths: install/MPI prefixes (mirror run_amr_outer.sh)
setup_paths() {
    OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
    OR_UMB_PREFIX=/users/ankushj/repos/orca-workspace/orca-umb-install
    MPI_HOME=/users/ankushj/amr-workspace/mvapich-install-ub22

    export PATH=$MPI_HOME/bin:$PATH
    source $OR_PREFIX/scripts/common.sh
    source $OR_PREFIX/scripts/orca_common.sh
}

# setup_ae_scale: AE-scale knobs (16 nodes, 10 timesteps)
setup_ae_scale() {
    OR_NNODES_MPI=16
    OR_PPN_MPI=16
    OR_NRANKS_MPI=$((OR_NNODES_MPI * OR_PPN_MPI))
    OR_NRANKS_DECK=$OR_NRANKS_MPI
    OR_NNODES_AGG=1
    OR_AMR_NSTEPS=10
    OR_RUN_ID=1
}

# setup_amr_params: phoebus binary + deck (mirror run_amr_outer.sh:setup_suite_common)
setup_amr_params() {
    OR_AMR_POLICY="baseline"
    OR_AMR_BIN=$OR_UMB_PREFIX/bin/phoebus
    OR_AMR_DECK_IN=$OR_UMB_PREFIX/decks/blast_wave_3d.${OR_NRANKS_DECK}.pin.in
    OR_FLOW_YAML=""
    OR_SUITENAME="amr-agg${OR_NNODES_AGG}-r${OR_NRANKS_MPI}-n${OR_AMR_NSTEPS}-run${OR_RUN_ID}"
}

# setup_orca_envs: ORCA/MPI env-var maps (mirror run_amr_outer.sh:setup_*_psm*)
setup_orca_envs() {
    declare -gA OR_ALL_ORCA_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
    declare -gA OR_ALL_MPI_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
}

# setup_profiles: AE profile set. Comment out lines for partial trials.
setup_profiles() {
    local ae_profiles=()
    ae_profiles+=("0")    # noorca / baseline
    ae_profiles+=("5")    # or_trace_mpisync (lightweight ORCA)
    ae_profiles+=("7")    # or_tracetgt (detailed ORCA)
    ae_profiles+=("10")   # tau_tracetgt
    ae_profiles+=("11")   # dftracer
    ae_profiles+=("13")   # scorep
    ae_profiles+=("17")   # caliper_tracetgt
    OR_PROFILES=$(IFS=,
        echo "${ae_profiles[*]}")
}

# setup_suite_export: export everything run_amr.sh needs
setup_suite_export() {
    SUITE_ROOT=${SUITE_ROOT:-/tmp/orca-ae-suites}
    OR_SUITEDIR="${SUITE_ROOT}/$(date +%Y%m%d)_${OR_SUITENAME}"
    OR_SUITE_DESC="ORCA AE run: ${OR_NNODES_MPI} nodes, ${OR_AMR_NSTEPS} timesteps, profiles=${OR_PROFILES}"

    export OR_SUITEDIR OR_SUITE_DESC
    export OR_HOSTFILE_MPI
    export OR_NNODES_MPI OR_NNODES_AGG OR_NRANKS_MPI OR_PPN_MPI
    export OR_AMR_POLICY OR_AMR_BIN OR_AMR_DECK_IN OR_AMR_NSTEPS
    export OR_FLOW_YAML
    export OR_PROFILES
    export OR_PREFIX OR_UMB_PREFIX MPI_HOME

    export OR_ALL_ORCA_ENV_EXP=$(declare -p OR_ALL_ORCA_ENV)
    export OR_ALL_MPI_ENV_EXP=$(declare -p OR_ALL_MPI_ENV)
}

# validate_env: sanity-check the hostfile
validate_env() {
    OR_HOSTFILE_MPI=${OR_HOSTFILE_MPI:-/tmp/hostfile_mpi}
    if [ ! -f "$OR_HOSTFILE_MPI" ]
    then
        die "OR_HOSTFILE_MPI=$OR_HOSTFILE_MPI does not exist (set or use check_hosts.py)"
    fi
    local count=$(wc -l <"$OR_HOSTFILE_MPI")
    if [ "$count" -lt "$OR_NNODES_MPI" ]
    then
        die "Hostfile has $count lines, need >= $OR_NNODES_MPI"
    fi
    message "-INFO- Hostfile: $OR_HOSTFILE_MPI ($count entries)"
    message "-INFO- Suitedir: $OR_SUITEDIR"
    message "-INFO- Profiles: $OR_PROFILES"
}

# run_suite: invoke run_amr.sh, which loops internally over OR_PROFILES
run_suite() {
    $PARENT_DIR/run_amr.sh
}

main() {
    setup_paths
    setup_ae_scale
    setup_amr_params
    setup_orca_envs
    setup_profiles
    setup_suite_export
    validate_env
    run_suite
}

main
