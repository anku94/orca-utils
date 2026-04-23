# Dashboard Protocol

This document describes the message formats exchanged between the dashboard
process (the TUI) and the controller.  It covers both command messages sent
*to* the controller and status/telemetry updates streamed *from* the
controller.

## Transport

* The dashboard runs a plain TCP server (see `mon::utils::Dashboard`).
* Every message is framed as: `<uint32:length><payload-bytes>`, where the
  length is a 32‑bit unsigned integer in network byte order.
* Payload bytes are UTF‑8 text.  Fields inside the payload are separated by
  the pipe (`|`) character (`SerializeArgs(...)`).
* Only a single client is expected.  If multiple clients connect the server
  services the most recent connection; previous sockets are still accepted but
  no longer receive updates.

## Command Protocol (client → controller)

The controller only recognises messages whose payload starts with
`COMMAND`.  The full grammar is:

```
COMMAND|<domains>|<ncmds>|<argc0>|<op0>|<arg...>|...|<argcN>|<opN>|<arg...>
```

* `<domains>` – `+` separated tokens selecting the targets:
  * `CTL` → controller only
  * `AGG` → aggregators
  * `MPI` → MPI ranks (including MPIREP ranks)
  * `ALL` is **not** currently emitted but the parser accepts combined masks.
* `<ncmds>` – number of commands that follow (`size_t` encoded as decimal).
* For each command:
  * `<argcX>` – number of fields that follow for this command.
  * `<opX>` / `<arg…>` – the command verb and arguments.

Supported commands

| Op token     | Arguments                 | Result                                                |
|--------------|---------------------------|-------------------------------------------------------|
| `PAUSE`      | none                      | Requests the target domain enter block-sync.          |
| `RESUME`     | none                      | Releases block-sync.                                  |
| `UPDATEFLOW` | optional `<plan-path>`    | Issues a two-phase `kUpdateFlow` string command. If
                                             an argument is supplied it is interpreted as the
                                             on-disk YAML plan to apply.  Without an argument
                                             the plan payload must already be staged elsewhere. |
| `cfgupd`     | `<key>` `<value>`         | Control-plane configuration update forwarded verbatim
                                             to `ControlPlane::ClientHandleKeyUpdate`.          |

Any other verb (unknown token, wrong arity) causes the entire batch to be
rejected with an `Invalid dashboard message` log entry; no partial execution
occurs.

## Update / Telemetry Stream (controller → client)

Outgoing messages are also pipe‑delimited (produced via `SerializeArgs`) and
follow these schemas:

| Message      | Payload format                                    | When sent                                                     |
|--------------|---------------------------------------------------|----------------------------------------------------------------|
| `STATUS`     | `STATUS|<human-readable-status>`                   | Controller status changes (`UpdateStatus`).                    |
| `CONFIG`     | `CONFIG|<num_aggs>|<mpi_nranks>`                   | Topology/config updates (`UpdateConfig`).                      |
| `REPS_ADD`   | `REPS_ADD|<agg_id>|<rep_id>|<rank_begin>|<rank_end>` | Discovery announces a new REP covering `[rbeg, rend)`.         |
| `SCHEMA_ADD` | `SCHEMA_ADD|<schema_name>`                         | New telemetry schema registered.                               |
| `PROBE_ADD`  | `PROBE_ADD|<schema>|<probe_id>|<probe_name>|<enabled>` | Probe visibility updates (`enabled` is `true`/`false`).        |
| `TSADV`      | `TSADV|<timestamp_us>|<ts_from>|<ts_to>`           | Timestep advancement notification (`AdvanceTimestep`).         |
| `LOG`        | `LOG|<timestamp_us>|<level>|<message>`             | Routed log entries; `<level>` ∈ {`INFO`, `WARN`, `ERROR`, `DBG0`, `DBG1`, `DBG2`}. |

Clients should be prepared to receive these messages in any order.  If no
client is connected, the dashboard buffers messages and flushes them the next
time a socket is accepted.

## Error handling and defaults

* Invalid command batches are logged but otherwise ignored.
* The controller does not send explicit acknowledgements; success or failure of
two-phase commands is visible through normal control-plane telemetry/logs.
* When the dashboard is disabled (`Dashboard(disabled=true)`), all methods turn
  into no-ops and no sockets are opened.

## Example command batch

```
COMMAND|CTL+MPI|2|1|PAUSE|2|UPDATEFLOW|/tmp/new_plan.yaml
```

Requests the controller and all MPI ranks to pause, then pushes the `/tmp/new_plan.yaml`
flow update to the same domains in a single two-phase batch.
