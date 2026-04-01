#!/bin/bash
set -eu
# Benchmark JSON vs Parquet HTA analysis
# Runs both modes ITERS times with cache drops between each, then reports speedup

# Toggle: set to 1 to clone HTA to /tmp/hta, 0 to use HTA_DIR as-is
CLONE_HTA=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HTA_DIR="/l0/orcaroot/orcahax/build-exps/HolisticTraceAnalysis"
HTA_REPO="https://github.com/facebookresearch/HolisticTraceAnalysis.git"
DATA_DIR="$SCRIPT_DIR/data"
LOG_DIR="$SCRIPT_DIR/logs"
TRACE_JSON="$DATA_DIR/h100_trace.json.gz"
TRACE_PARQUET="$DATA_DIR/h100_trace.parquet"
HTA_FUNC="get_temporal_breakdown"
ITERS=2
CORES=16

setup_hta() {
    if [ "$CLONE_HTA" -eq 1 ]; then
        HTA_DIR="/tmp/hta"
        if [ ! -d "$HTA_DIR" ]; then
            echo "Cloning HTA to $HTA_DIR..."
            git clone --depth 1 "$HTA_REPO" "$HTA_DIR"
        fi
    fi
    export PYTHONPATH="$HTA_DIR:${PYTHONPATH:-}"
}

convert_trace() {
    if [ -f "$TRACE_PARQUET" ]; then
        return
    fi

    echo "Converting JSON to Parquet..."
    # kineto_json_to_parquet.py dispatcher doesn't handle .gz, but the internal
    # function does. Decompress first, convert, clean up.
    TRACE_UNZIPPED="${TRACE_JSON%.gz}"
    if [ ! -f "$TRACE_UNZIPPED" ]; then
        gunzip -k "$TRACE_JSON"
    fi
    python3 "$SCRIPT_DIR/kineto_json_to_parquet.py" "$TRACE_UNZIPPED" "$TRACE_PARQUET"
    /bin/rm -f "$TRACE_UNZIPPED"
    echo ""
}

drop_caches() {
    if sudo -n sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null; then
        echo "  [dropped caches]"
    else
        echo "  [warning: could not drop caches]"
    fi
}

run_one() {
    local mode=$1
    local trace=$2
    local logfile=$3

    python3 "$SCRIPT_DIR/bench_json_vs_parquet.py" \
        --mode "$mode" --file "$trace" \
        --hta_func "$HTA_FUNC" --warmup 0 --runs 1 --cores "$CORES" \
        2>&1 | tee "$logfile"
}

run_iters() {
    /bin/rm -f "$LOG_DIR"/json-*.log "$LOG_DIR"/parquet-*.log
    mkdir -p "$LOG_DIR"

    for i in $(seq 1 $ITERS); do
        echo "=== Iteration $i/$ITERS ==="

        echo "  JSON:"
        drop_caches
        run_one json "$TRACE_JSON" "$LOG_DIR/json-$i.log"

        echo "  Parquet:"
        drop_caches
        run_one parquet "$TRACE_PARQUET" "$LOG_DIR/parquet-$i.log"

        echo ""
    done
}

report() {
    echo "=== Speedup ==="
    python3 "$SCRIPT_DIR/parse_bench.py" "$LOG_DIR"
}

main() {
    setup_hta
    convert_trace

    echo "HTA Benchmark: JSON vs Parquet"
    echo "  HTA_FUNC: $HTA_FUNC"
    echo "  ITERS: $ITERS, CORES: $CORES"
    echo ""

    run_iters
    report
}

main
