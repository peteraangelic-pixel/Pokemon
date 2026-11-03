#!/usr/bin/env python3
"""Offline research workbench: synthetic fixtures only; no network transport."""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Job:
    program: str
    url: str
    variant: str


def validate_url(url: str, allowlist: set[str]) -> None:
    """Exact hostname matching only; example.invalid is the only lab domain."""
    if not isinstance(url, str) or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise ValueError("invalid URL characters")
    p = urlsplit(url)
    try:
        port = p.port
    except ValueError as e:
        raise ValueError("invalid port") from e
    if (p.scheme != "https" or not p.hostname or p.username is not None or
            p.password is not None or port not in (None, 443) or p.fragment or
            p.query or not p.hostname.isascii() or p.hostname != p.netloc.lower().removesuffix(':443')):
        raise ValueError("invalid URL form")
    host = p.hostname.lower()
    if host not in allowlist or not host.endswith('.example.invalid'):
        raise ValueError("host outside offline fixture allowlist")
    if not p.path.startswith('/') or '%' in p.path or '\\' in p.path or any(x in ('.', '..') for x in p.path.split('/')):
        raise ValueError("invalid path")


class SpacedLimiter:
    """No burst. Testable monotonic clock; one owner, not a distributed limiter."""
    def __init__(self, rate: float = 2.0, clock=time.monotonic, sleep=time.sleep):
        if not math.isfinite(rate) or not 0 < rate <= 3:
            raise ValueError('offline rate must be > 0 and <= 3/s')
        self.interval = 1.0 / rate
        self.clock, self.sleep = clock, sleep
        self.next_at = None
        self.stopped = threading.Event()
        self.lock = threading.Lock()

    def stop(self):
        self.stopped.set()

    def wait(self):
        with self.lock:
            if self.stopped.is_set():
                raise RuntimeError("limiter stopped")
            now = self.clock()
            if self.next_at is not None and now < self.next_at:
                self.sleep(self.next_at - now)
            # Stop may have arrived while a worker was waiting.
            if self.stopped.is_set():
                raise RuntimeError("limiter stopped")
            self.next_at = self.clock() + self.interval


def schedule(jobs: list[Job]) -> list[Job]:
    """Round robin programs, two NASK jobs per cycle, preserving each queue."""
    queues = defaultdict(deque)
    for job in jobs:
        queues[job.program].append(job)
    order = sorted(queues, key=lambda p: (p != 'NASK', p))
    result = []
    while any(queues.values()):
        for p in order:
            for _ in range(2 if p == 'NASK' else 1):
                if queues[p]:
                    result.append(queues[p].popleft())
    return result


def analyze(records: list[dict]) -> list[dict]:
    """Compare fixture metadata only; no request/response body storage."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r['program'], r['url'])].append(r)
    observations = []
    for (program, url), entries in sorted(grouped.items()):
        if len(entries) < 2:
            continue
        statuses = sorted({r['status'] for r in entries})
        fingerprints = {r['fingerprint'] for r in entries}
        if len(statuses) > 1 or len(fingerprints) > 1:
            observations.append({'program': program, 'url': url,
                'variants': sorted(r['variant'] for r in entries),
                'status_codes': statuses, 'different_fingerprints': len(fingerprints) > 1,
                'assessment': 'roznica metadanych; nie stanowi dowodu podatnosci'})
    return observations


def run_fixture(path: Path, limiter=None) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != {'allowed_hosts', 'cases'} or not isinstance(data['cases'], list):
        raise ValueError('invalid fixture schema')
    hosts = data['allowed_hosts']
    if not isinstance(hosts, list) or not all(isinstance(h, str) and re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)*\.example\.invalid', h) for h in hosts):
        raise ValueError('only synthetic example.invalid hosts allowed')
    cases = {}
    for item in data['cases']:
        if set(item) != {'program', 'url', 'variant', 'status', 'fingerprint'}:
            raise ValueError('invalid case schema')
        if (not isinstance(item['program'], str) or not re.fullmatch(r'[A-Z0-9_-]{1,32}', item['program']) or
            not isinstance(item['variant'], str) or not re.fullmatch(r'[a-z0-9_-]{1,32}', item['variant']) or
            type(item['status']) is not int or not 100 <= item['status'] <= 599 or
            not isinstance(item['fingerprint'], str) or not re.fullmatch(r'[a-z0-9_-]{1,32}', item['fingerprint'])):
            raise ValueError('invalid case values')
        validate_url(item['url'], set(hosts))
        job = Job(item['program'], item['url'], item['variant'])
        if job in cases:
            raise ValueError('duplicate job')
        cases[job] = item
    records = []
    for job in schedule(list(cases)):
        if limiter:
            limiter.wait()
        # This is a dictionary lookup, not an HTTP request.
        records.append(cases[job])
    return {'mode': 'synthetic-offline', 'executed_fixture_jobs': len(records),
            'order': [r['program'] for r in records], 'observations': analyze(records)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Offline-only synthetic fixture analyzer; never contacts hosts')
    parser.add_argument('fixture', type=Path, help='JSON fixture using *.example.invalid')
    args = parser.parse_args()
    try:
        result = run_fixture(args.fixture)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(f'Fixture error: {e}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
