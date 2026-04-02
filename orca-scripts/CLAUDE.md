# TAU Trace Conversion - Context

## Overview
Working on converting TAU (Tuning and Analysis Utilities) trace files to a format compatible with ORCA's trace ingestion pipeline. TAU generates binary `.trc` files with companion `.edf` metadata files. Need to convert these to JSON/Parquet for analysis.

## Problem
TAU's `tau_trace2json` tool generates invalid JSON with:
1. Missing `"events": [` wrapper around event array
2. Trailing comma after metadata sections
3. Overall messy structure

## Solution
Created workflow to:
1. Run `tau_trace2json` to get raw JSON
2. Extract events-only section (find first "event-type" line)
3. Prepend `[` to create valid JSON array
4. Validate with Python

## Key Paths

### TAU Installation
- TAU bin: `/users/ankushj/repos/orca-workspace/tau-prefix/tau-2.34.1/x86_64/bin/`
- `tau_trace2json`: Main converter tool (has bugs)
- `tau_convert`: Alternative tool with `-dump`, `-paraver`, etc. formats
- TAU utils: `/users/ankushj/repos/orca-workspace/tau-prefix/tau-2.34.1/utils/`
- TAU source (trace reading library): Includes `TAU_tf.h`, `tau_trace2json.cpp`

### Trace Data
- Large trace (218MB/rank): `/mnt/ltio/orcajobs/tau-root/trace/`
  - 32 ranks, ~9.5M events per rank
- Small trace (8.2KB/rank): `/mnt/ltio/orcajobs/run6/tau-root/trace/`
  - 32 ranks, ~255 events for rank 0
  - Currently using this for development

### Parsed Output
- `/mnt/ltio/orcajobs/run6/tau-root/trace-parsed/`
  - `rank0.json`: Fixed valid JSON (255 events)

### ORCA Reference
- ORCA codebase: `/l0/orcaroot/orca/`
  - 40K LOC, C++/Rust, 9 months of development
  - Uses Apache Arrow columnar storage
  - Multi-tier overlay with 2PC timestep coordination
  - DuckDB + FlightSQL at root for live queries
- ORCA trace output example: `/mnt/ltio/orcajobs/run2/pqroot/`
  - 402MB Parquet files partitioned by timestep and rank
  - Three schemas: `kokkos_events`, `mpi_collectives`, `mpi_messages`

## TAU Event Schemas

### Event Types (from rank 0, 255 total events)
1. **counter** (240 events): Scalar measurements
   - Fields: `event-type, name, node-id, thread-id, time, value`
   - Examples: "Message size received", "MPI-IO Bytes Read"

2. **entry** (5 events): Function/region entry
   - Fields: `event-type, name, node-id, thread-id, time`
   - Examples: "SmallWorkRegion", "BigWorkRegion"

3. **exit** (9 events): Function/region exit
   - Fields: `event-type, name, node-id, thread-id, time`
   - Examples: "MPI_Wait()", "SmallWorkRegion"

4. **trace end** (1 event): Trace termination marker
   - Fields: `event-type` only

### Data Types
All fields are currently strings in JSON (need casting for Parquet):
- `time`: float64 (microseconds)
- `node-id`, `thread-id`: int32
- `value`: int64 or float64
- `name`: string (categorical/dictionary encoding)

## Scripts Created

Location: `/users/ankushj/repos/orca-workspace/orca-utils/orca-scripts/tau-analysis/`

### `parse_tautrace.sh`
End-to-end conversion script:
- Hardcoded config: rank 0 from run6 trace (override with `RANK=N`)
- Runs `tau_trace2json`
- Fixes JSON format
- Validates output
- Analyzes schemas
- Cleans up intermediate files

### `discover_schemas.py`
Schema analysis tool:
- Reads TAU JSON events (respects `RANK` env var)
- Counts event types
- Shows field schemas
- Prints example events

### `json_to_parquet.py`
Converts JSON to Parquet:
- Single unified DataFrame with padded schema
- Fills missing `value` with 0
- Converts types (float for time/value, int for IDs)
- Outputs to same directory as JSON

## Next Steps

### Parquet Conversion Options
1. **One table per event type** (like ORCA)
   - `counters.parquet`, `entries.parquet`, `exits.parquet`
   - Clean separation, no nullable columns

2. **Single unified table**
   - Add nullable `value` column for counters
   - Single file, but wasteful for entry/exit events

3. **Combined state events**
   - Merge entry/exit into `state_events` with `direction` column
   - Separate `counter_events` table

### TODO
- [ ] Decide on Parquet schema approach
- [ ] Write `json_to_parquet.py` converter
- [ ] Handle type casting (strings → float64/int32)
- [ ] Add partitioning by timestep/rank (like ORCA)
- [ ] Test with larger traces
- [ ] Consider OTF2 format (requires rebuilding TAU with libotf2)

## TAU vs ORCA Architecture

**TAU (1991-present):**
- Post-mortem analysis only
- Binary .trc files (~5.5x smaller than JSON)
- Tools: paraprof, jumpshot, tau_convert
- Sequential event records (24-32 bytes each)

**ORCA (9 months, 1 grad student):**
- Real-time monitoring during MPI execution
- Selective tracing with runtime probe control
- Multi-tier overlay with distributed queries (Apache DataFusion)
- Arrow columnar format → DuckDB → FlightSQL → Grafana
- Timestep-partitioned Parquet (bulk-synchronous parallel awareness)
- 2PC protocol for timestep-coordinated aggregation

Key insight: ORCA can disable 75%+ of trace events at runtime (e.g., Kokkos fence operations), avoiding collection entirely rather than sampling/filtering post-hoc.

## Notes
- TAU's OTF2 converters not built (missing libotf2 dependency)
- Chrome tracing format (`-chrome` flag) also has trailing comma bug
- Consider writing custom parser using TAU's `TAU_tf.h` library if needed
- Modern Python type hints: use `dict[str, int]` not `typing.Dict`
- Avoid performative type hints like `list[dict[str, Any]]`

## Shell Script Best Practices
- Use `set -e` and let the script fail on errors - don't wrap everything in `command -v` checks
- Use `pushd`/`popd` for directory changes, not `cd` or subshells
- Use `readlink -f` to get absolute paths of scripts
- NO unicode symbols (checkmarks, warnings, etc.) - ASCII only
- Derive paths from root variables (e.g., `TAU_TRACE2JSON="${TAU_ROOT}/x86_64/bin/tau_trace2json"`)
- Use `${VAR:-default}` for optional environment variables (e.g., `RANK=${RANK:-0}`)

## Event Schema Details (from rank 9, 765K events)
Much larger than rank 0 (255 events):
- Rank 0: 8.2KB trace (mostly initialization)
- Rank 9: 21MB trace (actual computation)
- Distribution shows ranks 0-7 are small (8KB), ranks 8-31 are large (20-21MB)
- Likely domain decomposition where some ranks handle more work
