#!/bin/bash
# tau_json_fix.sh - Convert TAU trace to valid JSON event array
# Converts .trc + .edf -> valid JSON array of events

set -e

# Configuration
TRACE_DIR="/mnt/ltio/orcajobs/run6/tau-root/trace"
TRACE_DIR="/mnt/ltio/orcajobs/tau-root/trace"
TRACE_DIR="/mnt/ltio/orcajobs/tau-analysis/sample_traces"
TRACE_PARSED_DIR=${TRACE_DIR}-parsed

RANK=${RANK:-0}
TAU_ROOT="/users/ankushj/repos/orca-workspace/tau-prefix/tau-2.34.1"
TAU_TRACE2JSON="${TAU_ROOT}/x86_64/bin/tau_trace2json"

# File paths
TRC_FILE="${TRACE_DIR}/tautrace.${RANK}.0.0.trc"
EDF_FILE="${TRACE_DIR}/events.${RANK}.edf"
RAW_JSON="${TRACE_PARSED_DIR}/rank${RANK}_raw.json"
FIXED_JSON="${TRACE_PARSED_DIR}/rank${RANK}.json"

log() {
    echo "[$(date +%H:%M:%S)] $*"
}

error() {
    echo "ERROR: $*" >&2
    exit 1
}

check_files() {
    log "Checking input files..."
    [ -f "$TRC_FILE" ] || error "TRC file not found: $TRC_FILE"
    [ -f "$EDF_FILE" ] || error "EDF file not found: $EDF_FILE"
    [ -x "$TAU_TRACE2JSON" ] || error "tau_trace2json not found or not executable: $TAU_TRACE2JSON"
}

convert_to_json() {
    log "Converting trace to JSON..."
    mkdir -p "$TRACE_PARSED_DIR"
    pushd "$TRACE_DIR" > /dev/null
    "$TAU_TRACE2JSON" "$TRC_FILE" "$EDF_FILE" -o "$RAW_JSON" 2>&1 | grep -v "^$" || true
    popd > /dev/null
    log "Raw JSON created: $RAW_JSON ($(wc -l < "$RAW_JSON") lines)"
}

split_events() {
    log "Splitting events by type..."

    # Find first event line
    FIRST_EVENT_LINE=$(grep -n "event-type" "$RAW_JSON" | head -1 | cut -d: -f1)

    if [ -z "$FIRST_EVENT_LINE" ]; then
        error "No event-type found in raw JSON"
    fi

    log "First event at line $FIRST_EVENT_LINE"

    # Extract all events
    EVENTS_TMP="${TRACE_PARSED_DIR}/rank${RANK}_events_tmp.json"
    tail -n +$FIRST_EVENT_LINE "$RAW_JSON" > "$EVENTS_TMP"

    # Split into message and non-message events
    MSG_JSON="${TRACE_PARSED_DIR}/rank${RANK}_msg.json"
    NOMSG_JSON="${TRACE_PARSED_DIR}/rank${RANK}_nomsg.json"

    grep "message-tag" "$EVENTS_TMP" > "$MSG_JSON" || true
    grep -v "message-tag" "$EVENTS_TMP" > "$NOMSG_JSON" || true

    MSG_COUNT=$(wc -l < "$MSG_JSON")
    NOMSG_COUNT=$(wc -l < "$NOMSG_JSON")

    log "Split into $MSG_COUNT message events and $NOMSG_COUNT non-message events"
    rm -f "$EVENTS_TMP"
}

fix_json() {
    log "Fixing JSON format..."

    # Add opening/closing brackets to both files
    MSG_JSON="${TRACE_PARSED_DIR}/rank${RANK}_msg.json"
    NOMSG_JSON="${TRACE_PARSED_DIR}/rank${RANK}_nomsg.json"

    for file in "$MSG_JSON" "$NOMSG_JSON"; do
        if [ -f "$file" ] && [ -s "$file" ]; then
            # Remove trailing comma from last line
            sed -i '$ s/,$//' "$file"

            first_line=$(head -1 "$file")
            last_line=$(tail -1 "$file")
            # if first line is not "[", prepend
            if [ "$first_line" != "[" ]; then
                sed -i '1s/^/[\n/' "$file"
            fi

            # if last line is not "]", append
            if [ "$last_line" != "]" ]; then
                echo "]" >> "$file"
            fi
            # Prepend "[" and append "]"
            # sed -i '1s/^/[\n/' "$file"
            # echo "]" >> "$file"
            log "Fixed $(basename $file)"
        fi
    done
}

validate_json() {
    log "Validating JSON..."
    EVENT_COUNT=$(python3 -c "import json; data=json.load(open('$FIXED_JSON')); print(len(data))")
    log "Valid JSON with $EVENT_COUNT events"
}

analyze_schemas() {
    log "Analyzing event schemas..."
    SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
    python3 "$SCRIPT_DIR/discover_schemas.py" "$FIXED_JSON"
}

cleanup() {
    log "Cleaning up raw JSON..."
    rm -f "$RAW_JSON"
}

main() {
    log "Starting TAU trace conversion for rank $RANK"
    check_files
    convert_to_json
    split_events
    fix_json
    log "Done! Message events: ${TRACE_PARSED_DIR}/rank${RANK}_msg.json"
    log "Done! Non-message events: ${TRACE_PARSED_DIR}/rank${RANK}_nomsg.json"
}

main
