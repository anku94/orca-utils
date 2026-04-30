#!/usr/bin/env bash
#
# Quick MPI sanity check: launches one rank per host listed in the hostfile,
# each running `hostname`. Useful for verifying that MPI/launcher/SSH wiring
# is working before driving real AE runs.
#

set -eu
SCRIPT_DIR=$(dirname $(realpath $0))

OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
source $OR_PREFIX/scripts/common.sh

MPI_HOME=/users/ankushj/amr-workspace/mvapich-install-ub22
export PATH=$MPI_HOME/bin:$PATH

OR_JOBDIR=$(mktemp -d /tmp/mpi_test.XXXXXX)
ORCA_UTILS=/l0/orcaroot/orcahax/build-exps/orca-utils
ORCA_SCRIPTS=$ORCA_UTILS/orca-scripts

OR_HOSTFILE=/tmp/hostfile.txt

WF_EXPNAME=mon8 # experiment name on Wolf

preflight_hostfile_wf() {
    if [ -f "$OR_HOSTFILE" ]; then
        message "-INFO- OR_HOSTFILE=$OR_HOSTFILE already exists, skipping check_hosts"
        message "-INFO- Delete hostfile to re-run check_hosts"
        return
    fi

    python $ORCA_SCRIPTS/check_hosts.py -e $WF_EXPNAME -o $OR_HOSTFILE --add-lustre-check /mnt/ltio
}

preflight_hostfile_nowf() {
    if [ ! -f "$OR_HOSTFILE" ]; then
        message "!! WARN !! Set up \$OR_HOSTFILE with an MPI hostfile to run this script"
        die "OR_HOSTFILE=$OR_HOSTFILE does not exist"
    fi
}

# preflight_checks: generate or ensure $OR_HOSTFILE
# if on Wolf, generates one using check_hosts.py
# else, checks for existence and dies otherwise
preflight_checks() {
    local fqdn=$(hostname -f)
    if [[ $fqdn =~ ^wf[0-9]+\.narwhal\.pdl\.cmu\.edu$ ]]; then
        message "-INFO- Detected Wolf host ($fqdn), running main_wf"
        preflight_hostfile_wf
    else
        message "-INFO- Non-Wolf host ($fqdn), running main_nowf"
        preflight_hostfile_nowf
    fi
}

# run_mpitest: runs `ls` on all nodes in $OR_HOSTFILE
run_mpitest() {
    # assert OR_HOSTFILE exists
    [ -f "$OR_HOSTFILE" ] || die "OR_HOSTFILE=$OR_HOSTFILE does not exist"
    [ -d "$OR_JOBDIR" ] || die "OR_JOBDIR=$OR_JOBDIR does not exist"

    nodes=$(wc -l <"$OR_HOSTFILE")
    message "-INFO- Hostfile: $OR_HOSTFILE ($nodes nodes found)"

    # set common.sh variables
    HOSTFILE=$OR_HOSTFILE
    bbos_buddies=0
    jobdir=$OR_JOBDIR

    gen_hosts # generates $vpic_nodes
    message "-INFO- vpic_nodes: $vpic_nodes"

    do_mpirun $nodes 1 "none" "" "$vpic_nodes" "hostname" "" $jobdir/out.log $jobdir/exp.log
    cat $jobdir/out.log
}

# main: run preflight_checks to handle hostfile, then run_mpitest
main() {
    preflight_checks
    run_mpitest
}

main
