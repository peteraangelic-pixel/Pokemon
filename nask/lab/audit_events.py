#!/usr/bin/env python3
"""Offline audit of sanitized request start times; never makes network requests.

Accepts JSONL events with exactly source and started_at, no URLs, bodies, or tokens.
Records must include an explicit timezone and at least millisecond precision.
This is a lower-bound audit: missing events or drifting clocks make it inconclusive.
"""
from __future__ import annotations
import argparse
from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

STAMP = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3,6}(?:Z|[+-]\d\d:\d\d)$')
SOURCE = re.compile(r'^[a-zA-Z0-9_-]{1,40}$')


def analyze_events(events):
    parsed = []
    for record in events:
        if not isinstance(record, dict) or set(record) != {'source', 'started_at'}:
            raise ValueError('only sanitized source and started_at fields are accepted')
        source, timestamp = record['source'], record['started_at']
        if not isinstance(source, str) or not SOURCE.fullmatch(source):
            raise ValueError('invalid source label')
        if not isinstance(timestamp, str) or not STAMP.fullmatch(timestamp):
            raise ValueError('timestamp needs timezone and 3-6 fractional digits')
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc)
        parsed.append((dt, source))
    parsed.sort()
    window = deque()
    max_count = 0
    source_labels = set()
    max_sources = set()
    for moment, source in parsed:
        while window and (moment - window[0][0]).total_seconds() >= 1:
            window.popleft()
        window.append((moment, source))
        source_labels.add(source)
        if len(window) > max_count:
            max_count = len(window)
            max_sources = {x[1] for x in window}
    return {'events': len(parsed), 'sources': len(source_labels),
            'max_starts_in_one_second': max_count,
            'max_window_sources': sorted(max_sources),
            'over_five_observed': max_count > 5,
            'warning': 'lower bound only; completeness and clock synchronization not verified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path)
    args = parser.parse_args()
    try:
        with args.events.open(encoding='utf-8') as f:
            events = [json.loads(line) for line in f if line.strip()]
        print(json.dumps(analyze_events(events), indent=2))
    except (ValueError, OSError, TypeError) as e:
        print('invalid sanitized event input:', str(e), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
