#!/usr/bin/env python3

import csv
import json
import sys


def convert_csv_to_chrome_trace(csv_path: str, output_path: str) -> None:
    events = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_us = int(row['ts_ns']) // 1000
            dur_us = int(row['dura_ns']) // 1000

            event = {
                'name': row['name'],
                'cat': row['probe_name'],
                'ph': 'X',
                'ts': ts_us,
                'dur': dur_us,
                'pid': int(row['rank']),
                'tid': int(row['depth'])
            }
            events.append(event)

    with open(output_path, 'w') as f:
        json.dump(events, f)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.csv> <output.json>')
        sys.exit(1)

    convert_csv_to_chrome_trace(sys.argv[1], sys.argv[2])
