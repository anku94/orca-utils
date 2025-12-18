#!/usr/bin/env bash

set -eu
SCRIPT_DIR=$(dirname $(realpath $0))
# SUITE_ROOT=/mnt/ltio/orcajobs/suites

OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
OR_UMB_PREFIX=/users/ankushj/repos/orca-workspace/orca-umb-install

# setup_suite_common: setup common environment variables
setup_suite_common() {
    # CTL node is implied, and will be added if ORCA is enabled
    # OR_AGGCNT=1 # AGG count
    # OR_MPI_NNODES=16  # MPI nodes
    # OR_MPI_NRANKS=1024 # MPI ranks per node
    OR_DECK_NRANKS=$OR_MPI_NRANKS
    OR_MPI_PPN=16 # MPI ranks per node

    OR_AMR_POLICY="baseline" # policy name
    OR_AMR_BIN=$OR_UMB_PREFIX/bin/phoebus
    OR_AMR_DECK_IN=$OR_UMB_PREFIX/decks/blast_wave_3d.${OR_DECK_NRANKS}.pin.in
    # OR_AMR_BIN=$OR_PREFIX/bin/example_prog
    # OR_AMR_NSTEPS: set in main loop

    OR_FLOW_YAML="" # Flow YAML is optional

    # Suite name: e.g. amr-agg1-r256-n200
    local suite_name="amr-agg${OR_AGGCNT}"
    suite_name="${suite_name}-r${OR_MPI_NRANKS}-n${OR_AMR_NSTEPS}-run${OR_RUN_ID}"
    OR_SUITENAME=$suite_name
    # OR_SUITEDIR="${SUITE_ROOT}/${suite_name}"
}

# sets: OR_SUITEDIR, OR_SUITE_DESC, OR_ALL_COMMON_ENV_VARS,
#       OR_ALL_ORCA_ENV_VARS, OR_ALL_MPI_ENV_VARS
# uses: OR_AMR_NSTEPS
setup_nsteps_psmdef_suite() {
    local suite_type="psmerrchkdef"
    OR_SUITEDIR="$OR_SUITEDIR-${suite_type}"

    OR_SUITE_DESC="
AMR test suite with 128 ranks per node
PSM_ERRCHK_TIMEOUT=default, AMR_NSTEPS=$OR_AMR_NSTEPS
Goal is to see the performance impact of different AMR tunes
on different ORCA modes.
"

    declare -grA OR_ALL_ORCA_ENV=()
    declare -grA OR_ALL_MPI_ENV=()
}

# sets: OR_SUITEDIR, OR_SUITE_DESC, OR_ALL_COMMON_ENV_VARS,
#       OR_ALL_ORCA_ENV_VARS, OR_ALL_MPI_ENV_VARS
# uses: OR_AMR_NSTEPS
setup_nsteps_psm141_suite() {
    local suite_type="psmerrchk141"
    # OR_SUITEDIR="$OR_SUITEDIR-${suite_type}-run${OR_RUN_ID}"
    OR_SUITEDIR="${SUITE_ROOT}-${suite_type}/${OR_SUITENAME}"

    OR_SUITE_DESC="
AMR test suite with 128 ranks per node
PSM_ERRCHK_TIMEOUT=1:4:1, AMR_NSTEPS=$OR_AMR_NSTEPS
Goal is to see the performance impact of different AMR tunes
on different ORCA modes.
"

    declare -gA OR_ALL_ORCA_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
    declare -gA OR_ALL_MPI_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
}

# sets: OR_SUITEDIR, OR_SUITE_DESC, OR_ALL_COMMON_ENV_VARS,
#       OR_ALL_ORCA_ENV_VARS, OR_ALL_MPI_ENV_VARS
# uses: OR_AMR_NSTEPS
setup_nsteps_psm141_nohugepages_suite() {
    local suite_type="psm141-nohugepages"
    local suite_name="amr-r${OR_MPI_NRANKS}-${suite_type}-n${OR_AMR_NSTEPS}"

    OR_SUITEDIR="${SUITE_ROOT}/${suite_name}"
    OR_SUITE_DESC="
AMR test suite with 128 ranks per node
PSM_ERRCHK_TIMEOUT=1:4:1, AMR_NSTEPS=$OR_AMR_NSTEPS
No hugepages. Note that we configure hugepages manually
on wf nodes using the following command:

echo 1024 | sudo tee /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages

!! This suite requires out-of-band config!!
"

    declare -gA OR_ALL_ORCA_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
    declare -gA OR_ALL_MPI_ENV=([PSM_ERRCHK_TIMEOUT]="1:4:1")
}

# setup_suite_export: run after setting up a suite
# to export the suite variables to the environment
setup_suite_export() {
    OR_MPI_NNODES=$((OR_MPI_NRANKS / OR_MPI_PPN))

    export OR_SUITEDIR="${SUITE_ROOT}/${OR_SUITENAME}"
    export OR_SUITE_DESC
    export OR_AGGCNT OR_MPI_NNODES OR_MPI_NRANKS OR_MPI_PPN
    export OR_AMR_POLICY OR_AMR_BIN OR_AMR_DECK_IN OR_AMR_NSTEPS
    export OR_FLOW_YAML

    export OR_ALL_ORCA_ENV_EXP=$(declare -p OR_ALL_ORCA_ENV)
    export OR_ALL_MPI_ENV_EXP=$(declare -p OR_ALL_MPI_ENV)
}

sweep_amr_nsteps() {
    # local all_amr_nsteps=(20 200 2000)

    for amr_nsteps in "${all_amr_nsteps[@]}"; do
        OR_AMR_NSTEPS=$amr_nsteps
        setup_suite_common
        setup_nsteps_psm141_suite
        # setup_nsteps_psmdef_suite
        # setup_nsteps_psm141_nohugepages_suite
        # setup_tau_suite
        setup_suite_export

        # to pass -f to run_amr.sh if there
        $SCRIPT_DIR/run_amr.sh
    done
}

# update_hostfile: compute stragglers and update hostfile
update_hostfile() {
    local hostfile=$1
    local check_script=/users/ankushj/repos/orca-workspace/orca-utils/orca-scripts/check_hosts.py

    python $check_script -e mon8 -o $hostfile
}

# resize_exp: call with 90,180,260
# will resize to 90 nnodes first then 180 then 260
resize_exp() {
    local -i nnodes=$1

    local resize_script=/users/ankushj/scripts/emulab-workflow.sh
    $resize_script $nnodes
}

# sweep_all: supply nruns as $1
sweep_all() {
    local -i nruns=$1
    local hostfile=/tmp/hostfile.txt
    for run_id in $(seq 1 $nruns); do
        echo "nranks: $OR_MPI_NRANKS, aggcnt: $OR_AGGCNT, run_id: $run_id"

        update_hostfile $hostfile
        export HOSTFILE=$hostfile
        OR_RUN_ID=$run_id

        setup_suite_common
        setup_nsteps_psm141_suite
        setup_suite_export

        $SCRIPT_DIR/run_amr.sh
    done
}

run() {
    SUITE_ROOT=/mnt/ltio/orcajobs/suites/20251212
    local -i nrepeat=0

    # export OR_PROFILES=0
    # OR_AMR_NSTEPS=20
    # OR_MPI_NRANKS=2048
    # OR_AGGCNT=2
    # # resize_exp 161
    # sweep_all $nrepeat

    # declare a nranks->aggcnt map
    declare -A nranks_aggcnt=(
        [512]=1
        [1024]=1
        [2048]=2
        [4096]=4
    )

    declare -A steps_reps=(
        [20]=1
        [2000]=3
    )

    local -a all_steps=(20 2000)
    # all_steps=(20)
    local -a all_nranks=(512 1024 2048)
    all_nranks=(4096)

    for step in "${all_steps[@]}"; do
        for nranks in "${all_nranks[@]}"; do
            OR_MPI_NRANKS=$nranks
            OR_AMR_NSTEPS=$step
            nrepeat=${steps_reps[$step]}
            OR_AGGCNT=${nranks_aggcnt[$nranks]}
            echo "nranks: $nranks, aggcnt: $OR_AGGCNT, step: $step, reps: $nrepeat"
            sweep_all $nrepeat
        done
    done
}

run
