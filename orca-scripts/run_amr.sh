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

declare -A OR_AMR_PROFILES=(
  [0]="noorca"
  [1]="tracers_disabled"
  [2]="tracendrop_mpi"
  [3]="tracendrop_agg"
  [4]="tracendrop_agg_tgt"
  [5]="trace_mpip2p"
  [6]="trace_mpip2p_notest"
  [7]="trace_all"
  [8]="trace_tgt"
  [9]="tau_default"
  [10]="tau_nothrottle"
)

# define outside:
# OR_SUITEDIR: where to create per-run dirs
# OR_SUITE_DESC: description of the suite
# OR_ALL_ORCA_ENV, OR_ALL_MPI_ENV: ORCA and MPI environment variables

# get_suitedir: get the suitedir with YYYYMMDD prefix
# - returns: suitedir with YYYYMMDD prefix
# - uses: OR_SUITEDIR
compute_suitedir_wdate() {
  # Add YYYYMMDD prefix to suite dir
  local date_str=$(date +%Y%m%d)
  local suite_basename=$(basename $OR_SUITEDIR)
  local suite_dirname=$(dirname $OR_SUITEDIR)
  local suite_namewdate=${date_str}_${suite_basename}
  local suitedir=${suite_dirname}/${suite_namewdate}
  echo $suitedir
}

# add_date_to_suitedir: add YYYYMMDD prefix to suite dir if not there
# - uses: $OR_SUITEDIR, sets: $OR_SUITEDIR
# - safe to call multiple times
add_date_to_suitedir() {
  # if OR_SUITEDIR is not set, compute it
  if [ -z "${OR_SUITEDIR:-}" ]; then
    OR_SUITEDIR=$(compute_suitedir_wdate)
    message "-INFO- Computed suite dir: $OR_SUITEDIR"
  fi

  local suite_dirname=$(basename $OR_SUITEDIR)
  # check if YYYYMMDD prefix is present
  if [[ $suite_dirname =~ ^[0-9]{8}_ ]]; then
    message "-INFO- Suite dir is already dated, doing nothing"
  else
    local new_suitedir=$(compute_suitedir_wdate)
    OR_SUITEDIR=$new_suitedir
    message "-INFO- Added YYYYMMDD prefix to suite dir: $OR_SUITEDIR"
  fi
}

# get_existing_profile_count: count the profiles that already exist
# - returns: number of profiles that already exist
# - uses: $OR_AMR_PROFILES, $OR_SUITEDIR
get_existing_profile_count() {
  local count=0
  for profile in "${OR_AMR_PROFILES[@]}"; do
    if [ -d $OR_SUITEDIR/$profile ]; then
      count=$((count + 1))
    fi
  done

  echo $count
}

# safe_delete_dir: delete a directory if it exists
# will only delete directories that are subdirs of OR_SUITEDIR
safe_delete_dir() {
  local dir_todel=$1

  # first, ensure OR_SUITEDIR is set and is a valid path
  [ -z "$OR_SUITEDIR" ] && die "OR_SUITEDIR is not set"
  [ ! -d "$OR_SUITEDIR" ] && die "OR_SUITEDIR is not a valid directory: $OR_SUITEDIR"

  # Ensure that dir_todel is a subdir of OR_SUITEDIR
  if [[ $dir_todel != $OR_SUITEDIR/* ]]; then
    die "Directory to delete is not a subdir of OR_SUITEDIR: $dir_todel"
  fi

  # if dir_todel does not exist or is not a directory, die
  [ ! -d "$dir_todel" ] && die "Directory to delete does not exist: $dir_todel"

  # delete the directory
  rm -rf $dir_todel
}

# cleanup_suitedir: cleanup the suite dir
# - checks for -f flag to force overwrite of an existing suite dir
# - do not set env vars here, as they will get reset,
# set them in `setup_amr_common` instead
safe_cleanup_suitedir() {
  # die if suite dir already exists unless -f is passed
  local -i force=0
  while getopts "f" opt; do
    case $opt in
    f) force=1 ;;
    *) die "Invalid option: -$OPTARG" ;;
    esac
  done

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

  OR_CTL_BIN="$OR_PREFIX/scripts/orcawf_wrapper.sh ctl"
  OR_AGG_BIN="$OR_PREFIX/scripts/orcawf_wrapper.sh agg"

  add_common_env_var FI_UNIVERSE_SIZE 64
  # add_common_env_var MV2_CM_RECV_BUFFERS ${arg_recvbuf:-1024} # def is 1024
  add_common_env_var MV2_ON_DEMAND_THRESHOLD 2048
  # need on wolf

  # setup_gen_amrdeck <policy_name> <nlim>
  # policies: baseline, cdpc512par8, hybridX, lpt
  setup_gen_amrdeck $OR_AMR_POLICY $OR_AMR_NSTEPS
  OR_MPI_BIN="$OR_AMR_BIN -i $OR_AMR_DECK"

  OR_CFG_YAML="$OR_PREFIX/config/wfopts.yml" # ORCA config YAML
  OR_ORCA_ENABLED=1                          # enable ORCA by default

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
setup_profile_tracendrop_mpi() {
  local cmdseq="set-flow trace-and-drop-mpi; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# tracendrop: trace and drop at MPI
setup_profile_tracendrop_agg() {
  # local cmdseq="set-flow trace-and-drop-agg; disable-probe mpi_messages MPI_Test; disable-probe kokkos_events TaskRegion::CheckAndUpdate; resume"
  local cmdseq="set-flow trace-and-drop-agg"
  # cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  # cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# tracendrop_agg_tgt: trace and drop at AGG, targeted disabling of probes
setup_profile_tracendrop_agg_tgt() {
  local cmdseq="set-flow trace-and-drop-agg"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
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
  # cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  # cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# trace_tgt: trace all tracers
setup_profile_trace_tgt() {
  local cmdseq="set-flow enable-tracers; resume"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  set_new_yaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# tau: run with TAU tracing=on, throttling=off
setup_profile_tau_default() {
  OR_ORCA_ENABLED=0
  add_common_env_var TAU_TRACE 1
  OR_RUN_TYPE="tau"
  OR_MPI_BIN="tau_exec $OR_MPI_BIN"
}

# tau: run with TAU tracing=on, throttling=off
setup_profile_tau_nothrottle() {
  OR_ORCA_ENABLED=0
  add_common_env_var TAU_TRACE 1
  add_common_env_var TAU_THROTTLE 0
  OR_RUN_TYPE="tau"
  OR_MPI_BIN="tau_exec $OR_MPI_BIN"
}

# setup_profile: call profile-specific setup function
# - args: $1: profile index
setup_profile() {
  local -i pidx=$1
  local profile_name=${OR_AMR_PROFILES[$pidx]}
  local setup_func="setup_profile_$profile_name"

  if declare -f "$setup_func" >/dev/null; then
    $setup_func
  else
    echo "No setup function for profile: $profile"
    exit 1
  fi
}

# run: computes some variables and runs the experiment
# - args: $1: profile index
# - uses: $OR_AGGCNT, $OR_MPI_NRANKS, $OR_MPI_NNODES
# - sets vars: OR_ORCA_NNODES, OR_MPI_PPN
run_profile() {
  local -i pidx=$1
  local profile_name=${OR_AMR_PROFILES[$pidx]}
  local profile_dir=$(get_profile_dir $OR_SUITEDIR $pidx)

  # Auto-computed variables
  OR_ORCA_NNODES=$((OR_AGGCNT + 1)) # Add +1 for CTL
  OR_JOBDIR=$profile_dir

  setup_amr_common    # common setup
  setup_profile $pidx # profile-specific setup/overrides
  run_main
  reset_all_env_vars # reset everything for next run
}

# get_profile_dir: get the profile dir from a numeric profile index
# - args: $1: suitedir, $2: profile index
# - echoes: profile dir (like 20251108_$OR_SUITEDIR/02_tracendrop_agg)
get_profile_dir() {
  local suitedir=$1
  local -i pidx=$2 # profile index
  local profile_name=${OR_AMR_PROFILES[$pidx]}
  local pnamewidx=$(printf "%02d_%s" $pidx $profile_name)
  local profile_dir=$suitedir/$pnamewidx
  echo $profile_dir
}

# get_profile_name_from_dir: get the profile name from a profile dir
# - echoes: profile name (like tracendrop_agg)
get_profile_name_from_dir() {
  local profile_dir=$1
  local profile_name=$(basename $profile_dir)
  # strip leading digits and underscore
  profile_name=${profile_name#[0-9]*_}
  echo $profile_name
}

# main_new: main function to run profiles
# - uses: $OR_PROFILES (comma-separated list of profile indices)
main() {
  message "-INFO- Running profiles: $OR_PROFILES"

  IFS=',' read -r -a PROFILES_ARRAY <<<"$OR_PROFILES"

  # Setup SUITEDIR. Add date, mkdir, write desc
  add_date_to_suitedir
  message "-INFO- Suite dir: $OR_SUITEDIR"
  mkdir -p $OR_SUITEDIR
  echo "$OR_SUITE_DESC" >$OR_SUITEDIR/desc.md

  # Pick up env vars from outer script
  source <(printf "%s" "$OR_ALL_ORCA_ENV_EXP")
  source <(printf "%s" "$OR_ALL_MPI_ENV_EXP")

  for pidx in "${PROFILES_ARRAY[@]}"; do
    local pdir=$(get_profile_dir $OR_SUITEDIR $pidx)
    local pname=$(get_profile_name_from_dir $pdir)
    local pname_aligned=$(printf "%20s" $pname)
    message "-INFO- Profile [$pidx]: $pname_aligned    ($pdir)"

    # check if profile dir already exists
    if [ -d $pdir ]; then
      message "!!WARN!!  - Profile dir already exists, will clean up"
    else
      message "-INFO-    - Profile dir does not exist, will create"
    fi
  done

  # Announce plan, wait for user to confirm/abort
  (
    message "-INFO- Press Enter or Ctrl+C to abort..."
    read -r
  )

  message "-INFO- Starting to run profiles..."
  for pidx in "${PROFILES_ARRAY[@]}"; do
    message "-INFO- Running profile: ${OR_AMR_PROFILES[$pidx]}"
    local pdir=$(get_profile_dir $OR_SUITEDIR $pidx)
    if [ -d $pdir ]; then
      message "!!WARN!!  - Dir already exists, cleaning up: $pdir"
      safe_delete_dir $pdir
    else
      message "-INFO-    - Profile dir does not exist, will create"
    fi
    run_profile $pidx
  done
}

main
