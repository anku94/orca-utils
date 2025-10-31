#!/usr/bin/env bash
set -eu
OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
OR_UMB_PREFIX=/users/ankushj/repos/orca-workspace/orca-umb-install

# for do_mpirun and gen_hosts
source $OR_PREFIX/scripts/common.sh
source $OR_PREFIX/scripts/orca_common.sh

# Can use check_hosts.py to generate a hostfile on emulab
# e.g. `check_hosts.py -o /tmp/hostfile.txt -e mon8`
HOSTFILE=/tmp/hostfile.txt
OR_SUITEDIR=/mnt/ltio/orcajobs/suites/amr-r128-psmdef
OR_SUITE_DESC="
AMR test suite with 128 ranks per node, default PSM settings.

Goal is to see the performance impact of different AMR tunes
on different ORCA modes.
"

setup_suite_common() {
  # die if suite dir already exists unless -f is passed
  local -i force=0
  while getopts "f" opt; do
    case $opt in
    f) force=1 ;;
    *) die "Invalid option: -$OPTARG" ;;
    esac
  done

  shift $((OPTIND - 1))

  rmdir $OR_SUITEDIR && true # try deleting if empty

  if [ $force -eq 0 ] && [ -d $OR_SUITEDIR ]; then
    die "Suite directory already exists: $OR_SUITEDIR"
  elif [ $force -eq 1 ] && [ -d $OR_SUITEDIR ]; then
    message "!! WARN !! rm -rf-ing suite directory: $OR_SUITEDIR in 3s"
    sleep 3 # give user a chance to cancel
    message "-INFO- rm -rf $OR_SUITEDIR"
    rm -rf $OR_SUITEDIR
  fi

  mkdir -p $OR_SUITEDIR
  echo "$OR_SUITE_DESC" >$OR_SUITEDIR/desc.md
}

# setup_gen_amrdeck: generate AMR deck from template
# - args: $1: policy name, $2: timesteps, $3: dest deck path
# - uses: $OR_AMR_DECK_IN, $OR_JOBDIR, sets: $OR_AMR_DECK
# - copies $OR_AMR_DECK_IN to $OR_JOBDIR and generates $OR_AMR_DECK
setup_gen_amrdeck() {
  local policy=$1
  local -i nlim=$2

  local deck_fname=$(basename $OR_AMR_DECK_IN)
  deck_fname=${deck_fname%.in}
  OR_AMR_DECK=$OR_JOBDIR/$deck_fname

  message "-INFO- Generating AMR deck: $OR_AMR_DECK"
  cat $OR_AMR_DECK_IN | sed \
    -e "s/{policy_name}/$policy/g" \
    -e "s/{nlim}/$nlim/g" >$OR_AMR_DECK
}

# setup_amr_common: common setup for AMR
# - creates jobdir, prepares deck
setup_amr_common() {
  mkdir -p $OR_JOBDIR

  OR_CTL_BIN=$OR_PREFIX/bin/controller_main
  OR_AGG_BIN=$OR_PREFIX/bin/aggregator_main

  add_common_env_var FI_UNIVERSE_SIZE 64  # need on wolf
  add_orca_env_var IPATH_NO_CPUAFFINITY 1 # unpin AGGs

  # Bind AGG to specific CPU/MEM
  OR_AGG_BIN="numactl --physcpubind=0-7 --membind=0 $OR_AGG_BIN"

  OR_AMR_BIN=$OR_UMB_PREFIX/bin/phoebus
  OR_AMR_DECK_IN=$OR_UMB_PREFIX/decks/blast_wave_3d.512.pin.in
  # setup_gen_amrdeck <policy_name> <nlim>
  # policies: baseline, cdpc512par8, hybridX, lpt
  setup_gen_amrdeck $OR_AMR_POLICY $OR_AMR_NSTEPS
  OR_MPI_BIN="$OR_AMR_BIN -i $OR_AMR_DECK"

  OR_CFG_YAML="$OR_PREFIX/config/wfopts.yml" # ORCA config YAML
  OR_ORCA_ENABLED=1                          # enable ORCA by default
}

setup_profile_deftimeout() {
  echo # does nothing
}

# shorttimeout: set short timeout for PSM
setup_profile_shorttimeout() {
  add_common_env_var PSM_ERRCHK_TIMEOUT "1:4:1"
  #add_common_env_var PSM_COALESCE_ACKS=0
  # add_common_env_var PSM_FLOW_CREDITS=32
}

# set_new_yaml_with_cmdseq: modify yaml to set new cmdseq
# creates a new yaml in $jobdir and overwrites $OR_CFG_YAML
set_new_yaml_with_cmdseq() {
  local cmdseq=$1
  # can not pass space-separated values via env vars easily
  # we must hack the YAML directly
  sed -e 's|^bootstrap_cmdseq: .*|bootstrap_cmdseq: "'"$cmdseq"'"|' \
    $OR_CFG_YAML >$OR_JOBDIR/cfg-mod.yml
  OR_CFG_YAML="$OR_JOBDIR/cfg-mod.yml"
  message "Replaced cmdsed. New YAML: $OR_CFG_YAML"
}

# noorca: disable ORCA
setup_profile_noorca() {
  OR_ORCA_ENABLED=0
}

# orcadisabled: load ORCA but disable tracers
setup_profile_tracers_disabled() {
  local cmdseq="set-flow disable-tracers; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
}

# tracendrop: trace and drop at MPI
setup_profile_tracendrop() {
  local cmdseq="set-flow trace-and-drop; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
}

# trace_mpip2p: trace mpi p2p messages
setup_profile_trace_mpip2p() {
  local cmdseq="set-flow enable-tracers mpi_messages; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
}

# trace_mpip2p_notest: trace mpi p2p messages but disable MPI_Test probe
setup_profile_trace_mpip2p_notest() {
  local cmdseq="set-flow enable-tracers mpi_messags; disable-probe mpi_messages MPI_Test; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
}

# trace_all: trace everything
setup_profile_trace_all() {
  local cmdseq="set-flow enable-tracers; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
}

# setup_profile: run ``
setup_profile() {
  local profile=$1
  local setup_func="setup_profile_$profile"

  if declare -f "$setup_func" >/dev/null; then
    $setup_func
  else
    echo "No setup function for profile: $profile"
    exit 1
  fi
}

# run: computes some variables and runs the experiment
# - uses: $OR_AGGCNT, $OR_MPI_NRANKS, $OR_MPI_NNODES
# - sets vars: OR_ORCA_NNODES, OR_MPI_PPN
run_profile() {
  local profile=$1

  # Auto-computed variables
  OR_ORCA_NNODES=$((OR_AGGCNT + 1)) # Add +1 for CTL
  OR_MPI_PPN=$((OR_MPI_NRANKS / OR_MPI_NNODES))

  OR_JOBDIR=$OR_SUITEDIR/$profile

  setup_amr_common       # common setup
  setup_profile $profile # profile-specific setup/overrides
  run_orcaexp
  reset_all_env_vars # reset everything for next run
}

# extract_runtime: extract runtime from mpi.log from AMR
# - generates: amr_runtimes.csv
extract_runtime() {
  local profile=$1
  local amr_log=$OR_SUITEDIR/$profile/mpi.log
  local runtime=$(cat $amr_log | grep "walltime used" | cut -d= -f2)
  local runtime_fmt=$(echo $runtime | awk '{printf "%f\n", $1}')

  echo "$profile runtime: $runtime_fmt seconds"
  echo "$profile,$runtime_fmt" >>$OR_SUITEDIR/amr_runtimes.csv
}

main() {
  # CTL node is implied, and will be added if ORCA is enabled
  OR_AGGCNT=1              # AGG count
  OR_MPI_NNODES=8          # MPI nodes
  OR_MPI_NRANKS=128        # MPI ranks per node
  OR_FLOW_YAML=""          # Flow YAML is optional
  OR_AMR_POLICY="baseline" # policy name
  OR_AMR_NSTEPS=500        # timesteps

  profiles=("noorca" "tracers_disabled" "tracendrop"
    "trace_mpip2p" "trace_mpip2p_notest" "trace_all")
  # profiles=("noorca" "tracers_disabled" "trace_all")

  for profile in "${profiles[@]}"; do
    run_profile $profile
    extract_runtime $profile
  done
}

# setup will fail if suite dir already exists unless -f is passed
setup_suite_common $@
main
