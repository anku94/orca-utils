#!/usr/bin/env bash

set -eu
SCRIPT_DIR=$(dirname $(realpath $0))
# SUITE_ROOT=/mnt/ltio/orcajobs/suites

OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
OR_UMB_PREFIX=/users/ankushj/repos/orca-workspace/orca-umb-install
MPI_HOME=/users/ankushj/amr-workspace/mvapich-install-ub22

export PATH=$MPI_HOME/bin:$PATH
source $OR_PREFIX/scripts/common.sh
source $OR_PREFIX/scripts/orca_common.sh

# All hostfiles
OR_HOSTFILE=/tmp/hostfile
OR_HOSTFILE_ORCA=${OR_HOSTFILE}_orca
OR_HOSTFILE_MPI=${OR_HOSTFILE}_mpi

# setup_suite_common: setup common environment variables
setup_suite_common() {
    # CTL node is implied, and will be added if ORCA is enabled
    # OR_AGGCNT=1 # AGG count
    # OR_MPI_NNODES=16  # MPI nodes
    # OR_MPI_NRANKS=1024 # MPI ranks per node
    # OR_DECK_NRANKS=512

    OR_NRANKS_DECK=$OR_NRANKS_MPI
    OR_PPN_MPI=16 # MPI ranks per node

    OR_AMR_POLICY="baseline" # policy name
    OR_AMR_BIN=$OR_UMB_PREFIX/bin/phoebus
    OR_AMR_DECK_IN=$OR_UMB_PREFIX/decks/blast_wave_3d.${OR_NRANKS_DECK}.pin.in
    # OR_AMR_BIN=$OR_PREFIX/bin/example_prog
    # OR_AMR_NSTEPS: set in main loop

    OR_FLOW_YAML="" # Flow YAML is optional

    # Suite name: e.g. amr-agg1-r256-n200
    OR_SUITENAME="amr-agg${OR_NNODES_AGG}-r${OR_NRANKS_MPI}-n${OR_AMR_NSTEPS}-run${OR_RUN_ID}"
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
    OR_NNODES_MPI=$(((OR_NRANKS_MPI + OR_PPN_MPI - 1) / OR_PPN_MPI))

    export OR_SUITEDIR="${SUITE_ROOT}/${OR_SUITENAME}"
    export OR_SUITE_DESC
    export OR_HOSTFILE_MPI OR_HOST_CTL OR_HOSTS_AGG # host info
    export OR_NNODES_MPI OR_NNODES_AGG OR_NRANKS_MPI OR_PPN_MPI
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

# allocate_orca_hosts: allocate orca hosts from the total hostfile
# call this function after `update_hostfile`
# - $1: number of nodes to be allocated for ORCA
# - rest are used for MPI
# - generates files: $OR_HOSTFILE_ORCA and $OR_HOSTFILE_MPI
allocate_orca_hosts() {
    local -i nnorca=$1 # number of orca nodes

    # Ensure that $hostfile exists
    [ ! -f $OR_HOSTFILE ] && die "Hostfile does not exist: $OR_HOSTFILE"

    # move the last k nodes to the orca hostfile
    local -i nntot=$(wc -l <$OR_HOSTFILE)
    local -i nnmpi=$((nntot - nnorca))

    message "-INFO- [allocate_orca_hosts] Dividing hostfile=$OR_HOSTFILE into orca and mpi hostfiles"
    message "-INFO- [allocate_orca_hosts] nodecnt tot=$nntot, orca=$nnorca, mpi=$nnmpi"

    # copy first nmpi nodes to the mpi hostfile
    # awk is used to ensure trailing newlines are present
    head -n $nnmpi $OR_HOSTFILE | awk "{print}" >$OR_HOSTFILE_MPI
    tail -n $nnorca $OR_HOSTFILE | awk "{print}" >$OR_HOSTFILE_ORCA

    message "-INFO- [allocate_orca_hosts] generated ORCA hostfile: $OR_HOSTFILE_ORCA with $(wc -l <$OR_HOSTFILE_ORCA) nodes"
    message "-INFO- [allocate_orca_hosts] generated MPI hostfile: $OR_HOSTFILE_MPI with $(wc -l <$OR_HOSTFILE_MPI) nodes"
}

# prep_orca_hosts: prep all ORCA nodes using the prep script
# script applies wolf-specific tuning to qib
# - uses: hostfile at $OR_HOSTFILE_ORCA
# - $1: number of nodes to be prepped for ORCA
# - call this function after `allocate_orca_hosts`
# - generates files: $OR_HOSTFILE_ORCA and $OR_HOSTFILE_MPI
prep_orca_hosts() {
    local orca_script=$SCRIPT_DIR/prep_orcanodes.sh

    [ ! -f $OR_HOSTFILE_ORCA ] && die "ORCA hostfile does not exist: $OR_HOSTFILE_ORCA"
    local orca_hosts=$(cat $OR_HOSTFILE_ORCA | paste -s -d, -)
    local nnorca=$(wc -l <$OR_HOSTFILE_ORCA)
    message "-INFO- [prep_orca_hosts] ORCA hosts (count=$nnorca): $orca_hosts"

    # prep orca nodes
    do_mpirun $nnorca 1 "none" "" "$orca_hosts" "$orca_script" "" ""
}

# ensure_hostfile_nodecnt: ensure that the hostfile has at least $nnodes nodes
# - $1: hostfile
# - $2: number of nodes
# - dies if the hostfile has less than $nnodes nodes
ensure_hostfile_nodecnt() {
    local hostfile=$1
    local -i nnodes=$2

    local nnodes_actual=$(wc -l <$hostfile)
    if [ $nnodes_actual -lt $nnodes ]; then
        die "Hostfile $hostfile has $nnodes_actual nodes, expected $nnodes"
    else
        message "-INFO- [ensure_hostfile_nodecnt] Hostfile $hostfile has $nnodes_actual nodes, expected $nnodes. OK."
    fi
}

# assign_orca_nodes: assign actual AGGs/CTL from $OR_HOSTFILE_ORCA
# - $1: number of AGGs (1 extra CTL node is implied)
# - sets: $OR_AGGCNT, $OR_HOST_CTL, $OR_HOSTS_AGG
# - dies if $OR_HOSTFILE_ORCA has less than $naggs+1 nodes
assign_orca_nodes() {
    local -i naggs=$1
    local -i nnodes_avail=$(wc -l <$OR_HOSTFILE_ORCA)
    if [ $nnodes_avail -lt $((naggs + 1)) ]; then
        die "Hostfile $OR_HOSTFILE_ORCA has $nnodes_avail nodes, need $naggs+1"
    else
        message "-INFO- [assign_orca_nodes] Hostfile $OR_HOSTFILE_ORCA has $nnodes_avail nodes, expected $naggs+1. OK."
    fi

    OR_AGGCNT=$naggs
    OR_HOST_CTL=$(head -n 1 $OR_HOSTFILE_ORCA | awk "{print}" | paste -sd, -)
    OR_HOSTS_AGG=$(tail -n $naggs $OR_HOSTFILE_ORCA | awk "{print}" | paste -sd, -)

    message "-INFO- [assign_orca_nodes] CTL node           : $OR_HOST_CTL"
    message "-INFO- [assign_orca_nodes] AGG nodes (count=$naggs): $OR_HOSTS_AGG"
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
    # local -i nruns=$1
    local -i nrbeg=$1
    local -i nrend=$2

    for run_id in $(seq $nrbeg $nrend); do
        echo "nranks: $OR_NRANKS_MPI, nnodes_agg: $OR_NNODES_AGG, run_id: $run_id"

        echo "Skipping hostfile update"
        # update_hostfile $hostfile

        OR_RUN_ID=$run_id

        setup_suite_common
        setup_nsteps_psm141_suite
        setup_suite_export

        $SCRIPT_DIR/run_amr.sh
    done
}

run() {
    SUITE_ROOT=/mnt/ltio/orcajobs/suites/20251229
    local -i nrepeat=0

    local -i nnodes_max_orca=5 # max nodes we will use for ORCA

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
        [200]=1
        [2000]=3
    )

    local -a all_steps=(20 2000)
    all_steps=(20 2000)
    local -a all_nranks=(512 1024 2048 4096)
    all_nranks=(512 1024 2048)

    # generate $OR_HOSTFILE
    # python $SCRIPT_DIR/check_hosts.py -e mon8 -o $OR_HOSTFILE
    # allocate_orca_hosts $nnodes_max_orca
    # prep_orca_hosts
    # ensure_hostfile_nodecnt $OR_HOSTFILE_ORCA $nnodes_max_orca
    # ensure_hostfile_nodecnt $OR_HOSTFILE_MPI 256
    # exit 0

    for step in "${all_steps[@]}"; do
        for nranks in "${all_nranks[@]}"; do
            OR_NRANKS_MPI=$nranks
            OR_AMR_NSTEPS=$step
            # nrepeat=${steps_reps[$step]}
            nrepeat=1

            OR_NNODES_AGG=${nranks_aggcnt[$nranks]}
            assign_orca_nodes $OR_NNODES_AGG

            echo "nranks: $nranks, nnodes_agg: $OR_NNODES_AGG, step: $step, reps: $nrepeat"
            sweep_all 1 1
        done
    done
}

run
