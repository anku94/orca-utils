#!/usr/bin/env bash

set -eu
OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install

# for TAU
MPI_HOME=/users/ankushj/amr-workspace/mvapich-install-ub22
TAU_ROOT=/users/ankushj/repos/orca-workspace/tau-prefix/tau-2.34.1
export PATH=$MPI_HOME/bin:$PATH
export PATH=$PATH:${TAU_ROOT}/x86_64/bin

# for do_mpirun and gen_hosts
source $OR_PREFIX/scripts/common.sh
source $OR_PREFIX/scripts/orca_common.sh

# Can use check_hosts.py to generate a hostfile on emulab
# e.g. `check_hosts.py -o /tmp/hostfile.txt -e mon8`
HOSTFILE=/tmp/hostfile.txt

# define outside:
# OR_SUITEDIR: where to create per-run dirs
# OR_SUITE_DESC: description of the suite
# OR_ALL_ORCA_ENV, OR_ALL_MPI_ENV: ORCA and MPI environment variables

# setup_suite_common: mostly just prevents accidental overwrites
# - checks for -f flag to force overwrite of an existing suite dir
# - do not set env vars here, as they will get reset,
# set them in `setup_amr_common` instead
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

  # Add YYYYMMDD prefix to suite dir
  local date_str=$(date +%Y%m%d)
  local suite_basename=$(basename $OR_SUITEDIR)
  local suite_dirname=$(dirname $OR_SUITEDIR)
  local suite_namewdate=${date_str}_${suite_basename}
  OR_SUITEDIR=${suite_dirname}/${suite_namewdate}

  if [ -d $OR_SUITEDIR ]; then
    rmdir $OR_SUITEDIR && true # try deleting if empty
  fi

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

# setup_amr_common_add_env_vars: add all env vars to the environment
# - used internally in setup_amr_common
# - uses: OR_ALL_COMMON_ENV_VARS, OR_ALL_ORCA_ENV_VARS, OR_ALL_MPI_ENV_VARS
setup_amr_common_add_env_vars() {
  # add all common env vars
  for key in "${!OR_ALL_ORCA_ENV[@]}"; do
    local val=${OR_ALL_ORCA_ENV[$key]}
    message "-INFO- Adding ORCA env var: $key = $val"
    add_orca_env_var "$key" "$val"
  done

  for key in "${!OR_ALL_MPI_ENV[@]}"; do
    local val=${OR_ALL_MPI_ENV[$key]}
    message "-INFO- Adding MPI env var: $key = $val"
    add_mpi_env_var "$key" "$val"
  done
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

  # setup_gen_amrdeck <policy_name> <nlim>
  # policies: baseline, cdpc512par8, hybridX, lpt
  setup_gen_amrdeck $OR_AMR_POLICY $OR_AMR_NSTEPS
  OR_MPI_BIN="$OR_AMR_BIN -i $OR_AMR_DECK"

  OR_CFG_YAML="$OR_PREFIX/config/wfopts.yml" # ORCA config YAML
  OR_ORCA_ENABLED=1                          # enable ORCA by default

  # add_common_env_var PSM_ERRCHK_TIMEOUT "1:4:1"
  # add all common env vars
  setup_amr_common_add_env_vars
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
  OR_RUN_TYPE="orca" # dir layout is still orc
}

# orcadisabled: load ORCA but disable tracers
setup_profile_tracers_disabled() {
  local cmdseq="set-flow disable-tracers; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# tracendrop: trace and drop at MPI
setup_profile_tracendrop() {
  local cmdseq="set-flow trace-and-drop; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# trace_mpip2p: trace mpi p2p messages
setup_profile_trace_mpip2p() {
  local cmdseq="set-flow enable-tracers mpi_messages; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# trace_mpip2p_notest: trace mpi p2p messages but disable MPI_Test probe
setup_profile_trace_mpip2p_notest() {
  local cmdseq="set-flow enable-tracers mpi_messags; disable-probe mpi_messages MPI_Test; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# trace_all: trace all tracers
setup_profile_trace_all() {
  local cmdseq="set-flow enable-tracers; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# tau: run with TAU tracing=on, throttling=off
setup_profile_tau() {
  OR_ORCA_ENABLED=0
  add_common_env_var TAU_TRACE 1
  add_common_env_var TAU_THROTTLE 0
  OR_RUN_TYPE="tau"
  OR_MPI_BIN="tau_exec $OR_MPI_BIN"
}

# setup_profile: run ``
setup_profile() {
  local profile=$1
  local profile_name=${profile#[0-9]*_} # strip leading digits and underscore
  local setup_func="setup_profile_$profile_name"

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
  run_main
  reset_all_env_vars # reset everything for next run
}

# main: main function to run hardcoded profiles
main() {
  profiles=("noorca" "tracers_disabled" "tracendrop"
    "trace_mpip2p" "trace_mpip2p_notest" "trace_all" "tau")
  # profiles=("noorca" "tracers_disabled" "trace_all")
  # profiles=("trace_mpip2p")
  # profiles=("tau")
  pidx=0 # profile_idx to prefix for sorted order

  # Pick up env vars from outer script
  source <(printf "%s" "$OR_ALL_ORCA_ENV_EXP")
  source <(printf "%s" "$OR_ALL_MPI_ENV_EXP")

  for profile in "${profiles[@]}"; do
    profile_name=${pidx}_${profile}
    run_profile $profile_name
    pidx=$((pidx + 1))
  done
}

# setup will fail if suite dir already exists unless -f is passed
setup_suite_common $@
main
