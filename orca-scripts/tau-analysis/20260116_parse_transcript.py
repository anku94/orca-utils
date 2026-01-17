"""
Parse Claude Code transcript + controller log to build timeline_events.csv

Events:
- user: feedback from transcript
- app: resume/pause/flow_install/disable_probe from controller log
- llm: flow_create, code_search, code_read from transcript
- llm: polars analyses from transcript (with curated descriptions)
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

TRANSCRIPT = Path("data/agentic-logs/transcript.jsonl")
CTLLOG = Path("/mnt/ltio/orcajobs/suites/20260116-agentic-complete/amr-agg4-r4096-n2000-run1/20_or_disable_paused/logs/orca.ctl.log")
POLARS_DESC = Path("data/agentic-data/tool_use_descriptions.txt")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)

def parse_ctl_ts(s):
    return datetime.strptime(s, "%Y/%m/%d-%H:%M:%S.%f") + timedelta(hours=5)


def load_polars_descriptions(path):
    """Load idx -> description for polars events"""
    desc = {}
    if not path.exists():
        return desc
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(" | ", 1)
        if len(parts) == 2:
            try:
                desc[int(parts[0])] = parts[1]
            except ValueError:
                pass
    return desc


def parse_controller_log(path):
    """Extract app events from controller log"""
    events = []
    lines = open(path).readlines()
    ts_pat = re.compile(r"^(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d{3})")
    cmd_pat = re.compile(r"Cmd\[0\]: Command\[op=(\w+)")
    str_pat = re.compile(r"StringCmd\[op=(\w+)")
    tgt_pat = re.compile(r"tgt_ts=(-?\d+)")

    i = 0
    while i < len(lines):
        if "InitiateCm] Admitted command" not in lines[i]:
            i += 1
            continue
        ts_m = ts_pat.match(lines[i])
        if not ts_m or i + 1 >= len(lines):
            i += 1
            continue

        ts = parse_ctl_ts(ts_m.group(1))
        cmd_m = cmd_pat.search(lines[i + 1])
        if not cmd_m:
            i += 1
            continue

        op = cmd_m.group(1)
        if op == "STRING":
            str_m = str_pat.search(lines[i + 1])
            if str_m:
                op = str_m.group(1)

        tgt_ts = None
        if i + 2 < len(lines):
            tgt_m = tgt_pat.search(lines[i + 2])
            if tgt_m:
                tgt_ts = int(tgt_m.group(1))

        etype = {"RESUME": "resume", "PAUSE": "pause", "UpdateFlow": "flow_install",
                 "DisableProbe": "disable_probe"}.get(op)
        if etype:
            label = f"{etype} (ts={tgt_ts})" if tgt_ts and tgt_ts >= 0 else etype
            events.append({"ts": ts, "ts_sim": tgt_ts, "track": "app", "event_type": etype, "label": label})
        i += 3
    return events


def parse_transcript(path, polars_desc, cutoff):
    """Extract user events and llm events from transcript"""
    events = []
    t0 = None
    tool_idx = 0
    stop = False

    for line in open(path):
        if stop:
            break
        obj = json.loads(line)
        ts_str = obj.get("timestamp")
        if not ts_str:
            continue
        ts = parse_ts(ts_str)

        # User feedback
        if obj.get("type") == "user":
            content = obj.get("message", {}).get("content")
            if isinstance(content, str) and len(content) > 3:
                if t0 is None:
                    t0 = ts
                if cutoff in content:
                    stop = True
                label = content[:60] + ("..." if len(content) > 60 else "")
                events.append({"ts": ts, "ts_sim": None, "track": "user", "event_type": "feedback", "label": label})

        # Tool uses
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if item.get("type") != "tool_use":
                continue

            name = item.get("name", "")
            inp = item.get("input", {})

            # Check if it's a polars event (from descriptions)
            if tool_idx in polars_desc:
                events.append({"ts": ts, "ts_sim": None, "track": "llm",
                              "event_type": "polars", "label": polars_desc[tool_idx]})
            # flow_create
            elif name == "Write":
                fpath = inp.get("file_path", "")
                if fpath.endswith(".yaml"):
                    fname = Path(fpath).name
                    events.append({"ts": ts, "ts_sim": None, "track": "llm",
                                  "event_type": "flow_create", "label": f"write: {fname}"})
            # code_search
            elif name in ("Grep", "Glob"):
                pattern = inp.get("pattern", "")[:30]
                events.append({"ts": ts, "ts_sim": None, "track": "llm",
                              "event_type": "code_search", "label": f"search: {pattern}"})
            # code_read
            elif name == "Read":
                fpath = inp.get("file_path", "")
                if "/parthenon/" in fpath or "/phoebus/" in fpath:
                    fname = Path(fpath).name
                    events.append({"ts": ts, "ts_sim": None, "track": "llm",
                                  "event_type": "code_read", "label": f"read: {fname}"})

            tool_idx += 1

    return events, t0


def run():
    script_dir = Path(__file__).parent

    polars_desc = load_polars_descriptions(script_dir / POLARS_DESC)
    print(f"Loaded {len(polars_desc)} polars descriptions")

    cutoff = "please add the current time as the time of completion"
    transcript_events, t0 = parse_transcript(script_dir / TRANSCRIPT, polars_desc, cutoff)
    print(f"Found {len(transcript_events)} transcript events")

    app_events = parse_controller_log(CTLLOG)
    print(f"Found {len(app_events)} app events")

    # Merge and filter
    all_events = transcript_events + app_events
    all_events = [e for e in all_events if e["ts"] >= t0]
    all_events.sort(key=lambda e: e["ts"])

    # To DataFrame
    rows = [{"t_secs": (e["ts"] - t0).total_seconds(), "ts_wall": e["ts"].isoformat(),
             "ts_sim": e["ts_sim"], "track": e["track"], "event_type": e["event_type"],
             "label": e["label"]} for e in all_events]

    df = pd.DataFrame(rows)
    out = script_dir / "data/agentic-data/timeline_events.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} events to {out}")


if __name__ == "__main__":
    run()
