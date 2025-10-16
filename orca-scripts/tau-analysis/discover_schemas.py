#!/usr/bin/env python3
"""
discover_schemas.py - Analyze TAU JSON event schemas

Reads a TAU JSON event file and prints schema information including:
- Event type counts
- Field schemas for each event type
- Example events
"""

import json
from collections import Counter, defaultdict
import sys


def discover_schemas(json_file: str) -> None:
    """Analyze and print schemas from TAU JSON events."""

    with open(json_file) as f:
        data = json.load(f)

    # Count event types
    event_counts = Counter(e['event-type'] for e in data)

    print("=== EVENT TYPE COUNTS ===")
    for etype, count in sorted(event_counts.items()):
        print(f"{etype:15s}: {count:4d} events")

    print("\n=== FIELD SCHEMAS BY EVENT TYPE ===")

    # Get all possible fields for each event type
    schemas = defaultdict(set)

    for event in data:
        etype = event['event-type']
        for key in event.keys():
            schemas[etype].add(key)

    for etype in sorted(schemas.keys()):
        print(f"\n{etype}:")
        print(f"  Fields: {sorted(schemas[etype])}")

        # Show 2 examples
        examples = [e for e in data if e['event-type'] == etype][:2]
        for i, ex in enumerate(examples, 1):
            print(f"  Example {i}: {ex}")


if __name__ == '__main__':
    json_file = sys.argv[1]
    print(f"Analyzing TAU JSON events from: {json_file}")
    discover_schemas(json_file)

