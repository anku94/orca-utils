set -eu

export MPI_HOME=/users/ankushj/amr-workspace/mvapich-install-ub22
export PATH=$MPI_HOME/bin:$PATH

export UMB_HOME=/users/ankushj/repos/orca-workspace/orca-umb-install
export PATH=$UMB_HOME/bin:$PATH

export ORCA_HOME=/users/ankushj/repos/orca-workspace/orca-install
export MPI_PROG=$ORCA_HOME/bin/example_prog

# export SCOREP=$UMB_HOME/bin/scorep-preload-init
export SCOREP_TRACE=/users/ankushj/repos/orca-workspace/orca-umb-install/bin/scorep-20251119_1331_29524097544584810

run_exp() {
    SCOREP_OUTROOT=/mnt/ltio/orcajobs/scorep-root
    SCOREP_OUTDIR=$SCOREP_OUTROOT/$(date +%Y%m%d)
    mkdir -p $SCOREP_OUTDIR/trace

    LD_PRELOAD_VALUE=$(scorep-preload-init --mpp=mpi --thread=none --value-only "$MPI_PROG" "$SCOREP_OUTDIR")
    local scorep_libkokkos="$UMB_HOME/lib/libscorep_adapter_kokkos_event.so"

    echo "-INFO- LD_PRELOAD_VALUE: $LD_PRELOAD_VALUE"

    mpirun -np 2 \
        -env LD_PRELOAD "$LD_PRELOAD_VALUE" \
        -env SCOREP_ENABLE_TRACING 1 \
        -env SCOREP_ENABLE_PROFILING 1 \
        -env SCOREP_KOKKOS_ENABLE default \
        -env SCOREP_MPI_ENABLE_GROUPS "COLL,P2P" \
        -env SCOREP_EXPERIMENT_DIRECTORY "$SCOREP_OUTDIR/trace" \
        -env KOKKOS_TOOLS_LIBS $scorep_libkokkos \
        $MPI_PROG $SCOREP_OUTDIR

    # Cleanup
    bash $SCOREP_OUTDIR/.scorep_preload/$(basename $MPI_PROG).clean
}

run_scorep_score() {
    echo "-INFO- Analyzing trace: $SCOREP_TRACE"
    scorep-score -r $SCOREP_TRACE/profile.cubex
}

run_cube_info() {
    echo "-INFO- Trace info: $SCOREP_TRACE"
    cube_info $SCOREP_TRACE/profile.cubex
}

run_cube_dump() {
    echo "-INFO- Dumping metrics from: $SCOREP_TRACE"
    cube_dump $SCOREP_TRACE/profile.cubex
}

run_cube_dump_time() {
    echo "-INFO- Dumping time metrics from: $SCOREP_TRACE"
    cube_dump -m time $SCOREP_TRACE/profile.cubex
}

run_cube_stat() {
    echo "-INFO- Per-rank statistics from: $SCOREP_TRACE"
    cube_stat -p $SCOREP_TRACE/profile.cubex
}

run_cube_regioninfo() {
    echo "-INFO- Region info from: $SCOREP_TRACE"
    cube_regioninfo $SCOREP_TRACE/profile.cubex
}

run_cube_calltree() {
    echo "-INFO- Call tree from: $SCOREP_TRACE"
    cube_calltree $SCOREP_TRACE/profile.cubex
}

run_otf2_print() {
    echo "-INFO- Printing OTF2 events from: $SCOREP_TRACE"
    otf2-print $SCOREP_TRACE/traces.otf2
}

main() {
    # Uncomment to run
    run_exp
    # run_scorep_score
    # run_cube_info
    # run_cube_dump_time
    # run_cube_stat
    # run_otf2_print
    # echo "Ready - uncomment functions in main() to run"
}

main
