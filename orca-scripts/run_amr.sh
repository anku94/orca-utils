#!/usr/bin/env bash

set -eu
OR_PREFIX=/users/ankushj/repos/orca-workspace/orca-install
ORUMB_PREFIX=/users/ankushj/repos/orca-workspace/orca-umb-install

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
  [1]="or_tracers_disabled"
  [2]="or_tracendrop_mpi"
  [3]="or_tracendrop_agg"
  [4]="or_tracendrop_agg_tgt"
  [5]="or_trace_mpisync"
  [6]="or_trace_all"
  [7]="or_tracetgt"
  [8]="tau_default"
  [9]="tau_nothrottle"
  [10]="tau_tracetgt"
  [11]="dftracer"
  [12]="dftracer_comp"
  [13]="scorep"
  [14]="or_tracetgt_ofitcp"
  [15]="or_ntv_mpiwait"
)

# cache_dir_filesizes: clear dirs > threshold and cache their fsizes
# args: $1: dir path to clean up
# - generates: $dir_path/filesizes_cached.csv
cache_dir_filesizes() {
  local dir_path=$1
  local csv_file=$dir_path/filesizes_cached.csv
  message "-INFO- compute_dir_filesizes: called with $dir_path"

  # Clear dirs > threshold
  local dirsz_kb_max=$((10 * 1024 * 1024)) # 10GB
  local dirsz_kb_real=$(du -sk $dir_path | awk '{print $1}')
  if [ $dirsz_kb_real -lt $dirsz_kb_max ]; then
    message "-INFO- Directory size is less than $dirsz_kb_max KB, skipping"
    return
  fi

  message "-INFO- Computing cached filesizes for: $dir_path"
  message "-INFO- CSV file: $csv_file"

  echo "fpath,fsize" >$csv_file
  find $dir_path -type f -print0 | while IFS= read -r -d '' file; do
    echo \"$file\",$(stat -c%s "$file")
  done >>$csv_file

  find "$dir_path" -mindepth 1 -type f -print0 | while IFS= read -r -d '' file; do
    local fname=$(basename $file)
    local pardir_name=$(basename $(dirname $file))
    if [ "$fname" != "$(basename $csv_file)" ] && [ "$pardir_name" != "orca_events" ]; then
      message "-INFO- Running rm $file"
      rm $file &
    fi
  done
}

# cleanup_orca_jobdir: cleanup the ORCA job directory
# - uses: $OR_JOBDIR
cleanup_orca_jobdir() {
  message "-INFO- Cleaning up ORCA job directory: $OR_JOBDIR"
  cache_dir_filesizes $OR_JOBDIR/parquet
}

# prep_tau_jobdir: prepare the TAU job directory
# - uses: $OR_JOBDIR
# - sets vars: TRACEDIR, PROFDIR
# - creates subdirs: tau-trace, tau-profile
prep_tau_jobdir() {
  message "-INFO- Preparing TAU job directory: $OR_JOBDIR"
  ensure_clean_dir $OR_JOBDIR/tau-trace
  ensure_clean_dir $OR_JOBDIR/tau-profile
  add_mpi_env_var TRACEDIR $OR_JOBDIR/tau-trace
  add_mpi_env_var PROFDIR $OR_JOBDIR/tau-profile
  add_mpi_env_var TAU_TRACE_FORMAT otf2

  CLEANUP_CMD="cleanup_tau_jobdir"
}

# cleanup_tau_jobdir: cleanup the TAU job directory
cleanup_tau_jobdir() {
  message "-INFO- Cleaning up TAU job directory: $OR_JOBDIR"
  cache_dir_filesizes $OR_JOBDIR/tau-trace
}

# prep_dftracer_jobdir: prepare jobdir for DFTracer
# - uses: $OR_JOBDIR
# - sets: a basic dftracer config
prep_dftracer_jobdir() {
  message "-INFO- Preparing DFTracer job directory: $OR_JOBDIR"

  local libpreload="$ORUMB_PREFIX/lib/libdftracer_preload.so"

  add_mpi_env_var DFTRACER_ENABLE 1
  add_mpi_env_var DFTRACER_INIT PRELOAD
  add_mpi_env_var LD_PRELOAD "$libpreload"
  add_mpi_env_var KOKKOS_TOOLS_LIBS "$libpreload"

  ensure_clean_dir $OR_JOBDIR/trace
  add_mpi_env_var DFTRACER_LOG_FILE "$OR_JOBDIR/trace/trace.log"
  add_mpi_env_var DFTRACER_DATA_DIR all

  add_mpi_env_var DFTRACER_DISABLE_IO 1
  add_mpi_env_var DFTRACER_DISABLE_POSIX 1
  add_mpi_env_var DFTRACER_DISABLE_STDIO 1
  add_mpi_env_var DFTRACER_TRACE_INTERVAL_MS 1000 # does this only log for 1s

  CLEANUP_CMD="cleanup_dftracer_jobdir"
}

# cleanup_dftracer_jobdir: cleanup the DFTracer job directory
cleanup_dftracer_jobdir() {
  message "-INFO- Cleaning up DFTracer job directory: $OR_JOBDIR"
  cache_dir_filesizes $OR_JOBDIR/trace
}

# prepare_scorep_jobdir: prepare jobdir for ScoreP
# - uses: $OR_JOBDIR
# - sets: a basic ScoreP config
# - sets: CLEANUP_CMD to cleanup the ScoreP preload
prepare_scorep_jobdir() {
  message "-INFO- Preparing ScoreP job directory: $OR_JOBDIR"

  local tracedir="$OR_JOBDIR/trace"
  ensure_clean_dir $tracedir

  local scp_init="$ORUMB_PREFIX/bin/scorep-preload-init"
  local libkokpre="$ORUMB_PREFIX/lib/libscorep_adapter_kokkos_event.so"
  local preval=$($scp_init --mpp=mpi --thread=none --value-only "$OR_AMR_BIN" "$OR_JOBDIR")

  message "-INFO- ScoreP LD_PRELOAD: $preval"

  add_mpi_env_var LD_PRELOAD "$preval"
  add_mpi_env_var KOKKOS_TOOLS_LIBS "$libkokpre"
  add_mpi_env_var SCOREP_EXPERIMENT_DIRECTORY "$tracedir"
  add_mpi_env_var SCOREP_MPI_ENABLE_GROUPS "COLL,P2P"
  add_mpi_env_var SCOREP_ENABLE_TRACING 0
  add_mpi_env_var SCOREP_ENABLE_PROFILING 1
  add_mpi_env_var SCOREP_KOKKOS_ENABLE 1
  add_mpi_env_var SCOREP_TOTAL_MEMORY $((128 * 1024 * 1024))
  add_mpi_env_var SCOREP_FILTERING_FILE /users/ankushj/llm-thinkspace/mpi-trace-test/scorep.filter
  # add_mpi_env_var SCOREP_TRACE_FORMAT csv
  # add_mpi_env_var SCOREP_TRACE_FILE "$OR_JOBDIR/trace/trace.log"

  # CLEANUP_CMD="bash $OR_JOBDIR/.scorep_preload/$(basename $OR_AMR_BIN).clean"
  CLEANUP_CMD="cleanup_scorep_jobdir"
}

# cleanup_scorep_jobdir: cleanup the ScoreP job directory
cleanup_scorep_jobdir() {
  message "-INFO- Cleaning up ScoreP job directory: $OR_JOBDIR"
  bash $OR_JOBDIR/.scorep_preload/$(basename $OR_AMR_BIN).clean
  cache_dir_filesizes $OR_JOBDIR/trace
}

# prep_mpiexp_jobdir: prepare jobdir for non-ORCA experiments
# - uses: $OR_JOBDIR (this dir must exist)
# - sets vars as per prep function
prep_mpiexp_jobdir() {
  message "-INFO- Preparing MPI experiment job directory: $OR_JOBDIR"
  jobdir=$OR_JOBDIR

  case $OR_RUN_TYPE in
  tau)
    prep_tau_jobdir
    ;;
  dftracer)
    prep_dftracer_jobdir
    ;;
  scorep)
    prepare_scorep_jobdir
    ;;
  *)
    die "Invalid OR_RUN_TYPE: $OR_RUN_TYPE"
    ;;
  esac
}

# run_mpiexp: run a MPI experiment, used for non-ORCA experiments
# will prepare jobdir as per $OR_RUN_TYPE (must not be orca)
# wil not modify $MPI_BIN unless prep function does so
# - $OR_JOBDIR must be mkdir-ed by caller
run_mpiexp() {
  message "-INFO- Running exp type: $OR_RUN_TYPE"

  # assert jobdir is set and points to a valid directory
  [ -z "$OR_JOBDIR" ] && die "OR_JOBDIR is not set"
  [ ! -d "$OR_JOBDIR" ] && die "OR_JOBDIR is not a valid directory: $OR_JOBDIR"
  prep_mpiexp_jobdir

  [ -z $HOSTFILE ] && die "HOSTFILE is not set"
  [ ! -f $HOSTFILE ] && die "HOSTFILE does not exist"
  validate_hostcnt

  # for common.sh, set nodes=MPI nodes
  nodes=$OR_MPI_NNODES # dont set bbos_buddies

  # Let common.sh generate $vpic_nodes and $bbos_nodes
  gen_hosts
  message "-INFO- vpic_nodes: $vpic_nodes"

  local mpi_logfile=$OR_JOBDIR/mpi.log

  # ---- do not add more env vars after this point ----
  log_all_env_vars

  # 'activate' the env vars and run MPI app
  local mpi_env_vars=($OR_MPI_ENV_STR)
  do_mpirun $OR_MPI_NRANKS $OR_MPI_PPN "none" mpi_env_vars[@] \
    "$vpic_nodes" "$OR_MPI_BIN" "" $mpi_logfile

  # if cleanup command is set, run it, and unset it
  if [ -n "${CLEANUP_CMD:-}" ]; then
    message "-INFO- Running cleanup command: $CLEANUP_CMD"
    $CLEANUP_CMD
    unset CLEANUP_CMD
  fi
}

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

  echo "Deleting directory: $dir_todel"

  # delete the directory
  rm -rf $dir_todel
}

# ensure_empty_dir: delete dir if not exists, then create it
ensure_empty_dir() {
  local path=$1

  # if exists and is not a dir, die
  [ -e "$path" ] && [ ! -d "$path" ] && die "Path is not a directory: $path"

  if [ -d "$path" ]; then
    message "-INFO- Path already exists, will clean up: $path"
    safe_delete_dir $path
  fi

  mkdir -p $path
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

  add_common_env_var PSM_CONNECT_TIMEOUT 30 # 30s timeout
  add_common_env_var FI_UNIVERSE_SIZE 512   # need on wolf
  add_common_env_var FI_OFI_RXM_BUFFER_SIZE 64
  # add_common_env_var MV2_CM_RECV_BUFFERS 2048
  add_common_env_var MV2_ON_DEMAND_THRESHOLD 8192

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

# update_cfgyaml_with_cmdseq: modify yaml to set new cmdseq
# creates a new yaml in $jobdir and overwrites $OR_CFG_YAML
update_cfgyaml_with_cmdseq() {
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

# or_tracers_disabled: load ORCA but disable tracers
setup_profile_or_tracers_disabled() {
  local cmdseq="set-flow disable-tracers; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"

  # add_orca_env_var FI_OFI_RXM_RX_SIZE 4096
  # add_orca_env_var FI_OFI_RXM_MSG_RX_SIZE 512
  # add_orca_env_var FI_OFI_RXM_COMP_PER_PROGRESS 128
  # add_orca_env_var FI_LOG_LEVEL debug
  # add_orca_env_var FI_LOG_SUBSYS ep_ctrl
  # add_common_env_var FI_OFI_RXM_BUFFER_SIZE 8192
}

# or_tracendrop_mpi: trace and drop at MPI
setup_profile_or_tracendrop_mpi() {
  local cmdseq="set-flow trace-and-drop-mpi; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# or_tracendrop_agg: trace and drop at MPI
setup_profile_or_tracendrop_agg() {
  local cmdseq="set-flow trace-and-drop-agg"
  cmdseq="$cmdseq; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# or_tracendrop_agg_tgt: trace and drop at AGG, targeted disabling of probes
setup_profile_or_tracendrop_agg_tgt() {
  local cmdseq="set-flow trace-and-drop-agg"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

setup_profile_or_trace_mpisync() {
  local cmdseq="set-flow enable-tracers mpi_collectives; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# or_trace_all: trace all tracers
setup_profile_or_trace_all() {
  local cmdseq="set-flow enable-tracers; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
  OR_RUN_TYPE="orca"
}

# or_tracetgt: trace all tracers
setup_profile_or_tracetgt() {
  local cmdseq="set-flow enable-tracers"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
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

setup_profile_tau_tracetgt() {
  OR_ORCA_ENABLED=0
  add_common_env_var TAU_TRACE 1
  add_common_env_var TAU_THROTTLE 0
  #add_common_env_var TAU_SELECT_FILE /users/ankushj/llm-thinkspace/select-mpi-kokkos.tau

  local tau_filter=$OR_JOBDIR/filter.tau
  cat <<EOF >$tau_filter
BEGIN_EXCLUDE_LIST
MPI_Test()#
MPI_Iprobe#
TaskRegion::CheckAndUpdate#
END_EXCLUDE_LIST
EOF

  add_common_env_var TAU_SELECT_FILE $tau_filter
  # TAU hallucinates because of sizeof bugs without this
  add_common_env_var TAU_PLUGINS_PATH ${TAU_ROOT}/x86_64/lib/shared-ompt-mpi-pdt-openmp
  add_common_env_var TAU_PLUGINS "libTAU-filter-plugin.so(/users/ankushj/llm-thinkspace/select-mpi-kokkos.tau)"

  OR_RUN_TYPE="tau"
  OR_MPI_BIN="tau_exec $OR_MPI_BIN"
}

# dftracer: run with DFTracer preload (MPI + Kokkos tracing)
setup_profile_dftracer() {
  OR_ORCA_ENABLED=0
  OR_RUN_TYPE="dftracer"
  add_mpi_env_var DFTRACER_TRACE_COMPRESSION 0
}

# dftracer_comp: run with DFTracer preload (MPI + Kokkos tracing)
setup_profile_dftracer_comp() {
  OR_ORCA_ENABLED=0
  OR_RUN_TYPE="dftracer"
  add_mpi_env_var DFTRACER_TRACE_COMPRESSION 1
}

# scorep: run with ScoreP preload (MPI + Kokkos tracing)
setup_profile_scorep() {
  OR_ORCA_ENABLED=0
  OR_RUN_TYPE="scorep"
}

# or_tracetgt_ofitcp: trace all tracers
setup_profile_or_tracetgt_ofitcp() {
  OR_RUN_TYPE="orca"

  local cmdseq="set-flow enable-tracers"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"

  add_common_env_var ORCA_HG_PROTO "ofi+tcp"
  # add_common_env_var ORCA_NA_NO_BLOCK 1
  # add_common_env_var NA_OFI_UNEXPECTED_TAG_MSG 1
  add_common_env_var FI_TCP_IFACE ibs2
  # add_common_env_var HG_LOG_LEVEL info
  # add_common_env_var FI_LOG_LEVEL debug
}

# or_ntv_mpiwait: trace all tracers
setup_profile_or_ntv_mpiwait() {
  OR_RUN_TYPE="orca"
  local cmdseq="set-flow file /users/ankushj/repos/orca-workspace/orca-utils/orca-scripts/flows/mpiwait.yaml"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Test"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Iprobe"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Isend"
  cmdseq="$cmdseq; disable-probe mpi_messages MPI_Irecv"
  cmdseq="$cmdseq; disable-probe kokkos_events region::TaskRegion::CheckAndUpdate"
  cmdseq="$cmdseq; resume"
  update_cfgyaml_with_cmdseq "$cmdseq"
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
  OR_JOBDIR=$profile_dir

  setup_amr_common    # common setup
  setup_profile $pidx # profile-specific setup/overrides

  # call run_main for ORCA, run_mpiexp for other types
  case $OR_RUN_TYPE in
  orca)
    run_orcaexp
    cleanup_orca_jobdir
    ;;
  *)
    run_mpiexp
    # echo "TODO: run_mpiexp"
    ;;
  esac

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
  # if OR_PROFILES is not set, set a default
  #local profiles_def="0,1,4,5,7,8,10,11,12" # 12 scorep needs tuning
  # local profiles_def="0,1,4,5,7,8,10,11" # 12 scorep needs tuning
  local profiles_def="0,5,7,15" # no competition here
  OR_PROFILES=${OR_PROFILES:-$profiles_def}

  message "-INFO- Running profiles: $OR_PROFILES"

  IFS=',' read -r -a PROFILES_ARRAY <<<"$OR_PROFILES"

  # Setup SUITEDIR. Add date, mkdir, write desc
  # add_date_to_suitedir: disabled, we do it manually
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
    # read -r
  )

  message "-INFO- Starting to run profiles..."
  for pidx in "${PROFILES_ARRAY[@]}"; do
    message "-INFO- Running profile: ${OR_AMR_PROFILES[$pidx]}"

    local pdir=$(get_profile_dir $OR_SUITEDIR $pidx)
    ensure_empty_dir $pdir
    run_profile $pidx
  done
}

main

# data_root=/mnt/ltio/orcajobs/suites
# # find all dirs named tau_trace in $data_root
# for dir in $(fdfind tau-trace $data_root); do
#   echo $dir
#   cache_dir_filesizes $dir
# done
