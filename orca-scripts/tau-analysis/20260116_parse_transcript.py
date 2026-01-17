"""
Parse Claude Code transcript JSONL to extract events for timeline visualization.

Events are categorized into three tracks:
- user: feedback, direction, corrections
- llm: flow creation, code reading, analysis
- app: resume, pause, flow install, probe disable
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import suite_utils as su

TRANSCRIPT_PATH = Path("data/agentic-logs/transcript.jsonl")
CTLLOG_PATH = Path("/mnt/ltio/orcajobs/suites/20260116-agentic-complete/amr-agg4-r4096-n2000-run1/20_or_disable_paused/logs/orca.ctl.log")


@dataclass
class Event:
    ts_wall: datetime  # wall clock
    ts_sim: int | None  # MPI timestep if known
    track: str  # "user" | "llm" | "app"
    event_type: str  # "feedback" | "flow_install" | "code_read" | ...
    label: str  # short description
    details: dict = field(default_factory=dict)


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp from transcript (returns naive UTC)"""
    # Format: 2026-01-17T03:07:54.223Z
    # Strip timezone info for comparison with controller log
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def parse_ctl_timestamp(ts_str: str) -> datetime:
    """Parse controller log timestamp (EST -> UTC)"""
    # Format: 2026/01/16-22:09:15.041
    # Controller logs are in EST (UTC-5), convert to UTC for consistency
    dt = datetime.strptime(ts_str, "%Y/%m/%d-%H:%M:%S.%f")
    return dt + timedelta(hours=5)  # EST to UTC


def parse_controller_log(path: Path) -> list[Event]:
    """Parse controller log for command events"""
    events = []

    # Pattern for InitiateCm lines with command info
    # Example: 2026/01/16-22:09:15.041 ... Cmd[0]: Command[op=RESUME, domains=0x07]
    ts_pattern = re.compile(r"^(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d{3})")
    cmd_pattern = re.compile(r"Cmd\[0\]: Command\[op=(\w+)")
    stringcmd_pattern = re.compile(r"StringCmd\[op=(\w+)")
    tgt_ts_pattern = re.compile(r"tgt_ts=(-?\d+)")

    with open(path) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if "InitiateCm] Admitted command" not in line:
            i += 1
            continue

        # Parse timestamp
        ts_match = ts_pattern.match(line)
        if not ts_match:
            i += 1
            continue
        ts = parse_ctl_timestamp(ts_match.group(1))

        # Next line has the command
        if i + 1 >= len(lines):
            break
        cmd_line = lines[i + 1]

        # Parse command type
        cmd_match = cmd_pattern.search(cmd_line)
        if not cmd_match:
            i += 1
            continue

        op = cmd_match.group(1)

        # For STRING commands, get the sub-operation
        if op == "STRING":
            str_match = stringcmd_pattern.search(cmd_line)
            if str_match:
                op = str_match.group(1)

        # Get target timestep from the third line
        tgt_ts = None
        if i + 2 < len(lines):
            tgt_match = tgt_ts_pattern.search(lines[i + 2])
            if tgt_match:
                tgt_ts = int(tgt_match.group(1))

        # Map op to event type and label
        if op == "RESUME":
            event_type, label = "resume", "resume"
        elif op == "PAUSE":
            event_type, label = "pause", "pause"
        elif op == "UpdateFlow":
            event_type, label = "flow_install", "flow_install"
        elif op == "DisableProbe":
            event_type, label = "disable_probe", "disable_probe"
        elif op == "DisableTracers":
            event_type, label = "disable_tracers", "disable_tracers"
        else:
            event_type, label = "other_cmd", op

        events.append(Event(
            ts_wall=ts,
            ts_sim=tgt_ts,
            track="app",
            event_type=event_type,
            label=f"{label} (ts={tgt_ts})" if tgt_ts and tgt_ts >= 0 else label,
            details={"op": op, "tgt_ts": tgt_ts},
        ))

        i += 3  # Skip the 3-line group

    return events


def extract_user_event(msg: dict, ts: datetime) -> Event | None:
    """Extract event from user message"""
    content = msg.get("message", {}).get("content")
    if content is None:
        return None

    # Skip tool results
    if isinstance(content, list):
        return None

    if not isinstance(content, str):
        return None

    # Skip very short or empty
    content = content.strip()
    if len(content) < 3:
        return None

    # Truncate for label
    label = content[:60] + ("..." if len(content) > 60 else "")

    return Event(
        ts_wall=ts,
        ts_sim=None,
        track="user",
        event_type="feedback",
        label=label,
        details={"full_content": content},
    )


def classify_cmd(cmd: str) -> tuple[str, str]:
    """Classify a single cmdrunner command, return (event_type, label)"""
    if cmd == "resume":
        return "resume", "resume"
    elif cmd == "pause":
        return "pause", "pause"
    elif cmd == "status":
        return "status", "status"
    elif cmd.startswith("set-flow"):
        flow_match = re.search(r"set-flow\s+file\s+(\S+)", cmd)
        flow_name = Path(flow_match.group(1)).name if flow_match else "unknown"
        return "flow_install", f"install: {flow_name}"
    elif cmd.startswith("disable-probe"):
        return "disable_probe", cmd
    else:
        return "other_cmd", cmd[:40]


def extract_cmdrunner_events(bash_cmd: str, ts: datetime) -> list[Event]:
    """Extract app events from cmdrunner_main commands (handles chained commands)"""
    events = []

    # Find all cmdrunner_main commands in the bash string
    matches = re.findall(r'cmdrunner_main\s+["\']([^"\']+)["\']', bash_cmd)

    for cmd in matches:
        event_type, label = classify_cmd(cmd)
        events.append(Event(
            ts_wall=ts,
            ts_sim=None,
            track="app",
            event_type=event_type,
            label=label,
            details={"cmd": cmd},
        ))

    return events


def extract_tool_events(tool_use: dict, ts: datetime) -> list[Event]:
    """Extract events from tool use (may return multiple for chained commands)"""
    tool_name = tool_use.get("name", "")
    tool_input = tool_use.get("input", {})

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        # Check if it's a cmdrunner command
        if "cmdrunner_main" in cmd:
            return extract_cmdrunner_events(cmd, ts)
        # Skip other bash commands for now
        return []

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        fname = Path(file_path).name if file_path else "unknown"
        if fname.endswith(".yaml"):
            return [Event(
                ts_wall=ts,
                ts_sim=None,
                track="llm",
                event_type="flow_create",
                label=f"write: {fname}",
                details={"file_path": file_path},
            )]
        return []

    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        # Only track source code reads, not flow reads
        if "/parthenon/" in file_path or "/phoebus/" in file_path:
            fname = Path(file_path).name if file_path else "unknown"
            return [Event(
                ts_wall=ts,
                ts_sim=None,
                track="llm",
                event_type="code_read",
                label=f"read: {fname}",
                details={"file_path": file_path},
            )]
        return []

    elif tool_name in ("Grep", "Glob"):
        pattern = tool_input.get("pattern", "")
        return [Event(
            ts_wall=ts,
            ts_sim=None,
            track="llm",
            event_type="code_search",
            label=f"search: {pattern[:30]}",
            details={"pattern": pattern},
        )]

    return []


def extract_assistant_events(msg: dict, ts: datetime) -> list[Event]:
    """Extract events from assistant message"""
    events = []
    content = msg.get("message", {}).get("content", [])

    if not isinstance(content, list):
        return events

    for item in content:
        if item.get("type") == "tool_use":
            tool_events = extract_tool_events(item, ts)
            events.extend(tool_events)

    return events


def parse_transcript(path: Path, cutoff_marker: str | None = None) -> list[Event]:
    """Parse transcript JSONL and extract all events.

    Args:
        path: Path to transcript JSONL
        cutoff_marker: If provided, stop parsing after user message containing this string
    """
    events: list[Event] = []
    stop_parsing = False

    with open(path) as f:
        for line in f:
            if stop_parsing:
                break

            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts_str = msg.get("timestamp")
            if not ts_str:
                continue

            ts = parse_timestamp(ts_str)
            msg_type = msg.get("type")

            if msg_type == "user":
                event = extract_user_event(msg, ts)
                if event:
                    events.append(event)
                    # Check for cutoff marker
                    if cutoff_marker and cutoff_marker in event.details.get("full_content", ""):
                        stop_parsing = True

            elif msg_type == "assistant":
                assistant_events = extract_assistant_events(msg, ts)
                events.extend(assistant_events)

    return events


def print_events(events: list[Event]):
    """Print events in a readable format"""
    if not events:
        print("No events found")
        return

    t0 = events[0].ts_wall
    for e in events:
        dt = (e.ts_wall - t0).total_seconds()
        print(f"{dt:6.1f}s | {e.track:5s} | {e.event_type:15s} | {e.label}")


def merge_events(transcript_events: list[Event], ctl_events: list[Event]) -> list[Event]:
    """Merge transcript and controller events, using controller for app events.

    Rebases all timestamps relative to first user event.
    """
    # Keep only user and llm events from transcript
    non_app_events = [e for e in transcript_events if e.track != "app"]

    # Combine and sort by timestamp
    all_events = non_app_events + ctl_events
    all_events.sort(key=lambda e: e.ts_wall)

    # Find first user event
    first_user = next((e for e in all_events if e.track == "user"), None)
    if first_user is None:
        return all_events

    t0 = first_user.ts_wall

    # Filter to events >= t0 and rebase timestamps
    filtered = []
    for e in all_events:
        if e.ts_wall >= t0:
            filtered.append(e)

    return filtered


def events_to_df(events: list[Event], t0: datetime) -> pd.DataFrame:
    """Convert events to DataFrame with relative timestamps"""
    rows = []
    for e in events:
        dt_secs = (e.ts_wall - t0).total_seconds()
        rows.append({
            "t_secs": dt_secs,
            "ts_wall": e.ts_wall.isoformat(),
            "ts_sim": e.ts_sim,
            "track": e.track,
            "event_type": e.event_type,
            "label": e.label,
        })
    return pd.DataFrame(rows)


def run():
    script_dir = Path(__file__).parent
    transcript_path = script_dir / TRANSCRIPT_PATH

    # Study ends when user asks to add completion timestamp
    cutoff = "please add the current time as the time of completion"

    print(f"Parsing transcript: {transcript_path}")
    transcript_events = parse_transcript(transcript_path, cutoff_marker=cutoff)
    print(f"Found {len(transcript_events)} transcript events")

    print(f"\nParsing controller log: {CTLLOG_PATH}")
    ctl_events = parse_controller_log(CTLLOG_PATH)
    print(f"Found {len(ctl_events)} controller events")

    # Merge events (rebased to first user event)
    events = merge_events(transcript_events, ctl_events)
    print(f"\nMerged: {len(events)} total events")

    # Find t0 for DataFrame conversion
    t0 = events[0].ts_wall if events else datetime.now()

    # Convert to DataFrame and save
    df = events_to_df(events, t0)

    out_dir = su.get_repo_data_dir() / "agentic-data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "timeline_events.csv"

    print(f"\nSaving to {out_path}")
    df.to_csv(out_path, index=False)

    print(f"\nTimeline ({len(df)} events, {df['t_secs'].max():.1f}s duration):\n")
    print_events(events)


if __name__ == "__main__":
    run()
