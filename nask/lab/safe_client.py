#!/usr/bin/env python3
"""Conservative, single-process public-root status checks. No bodies or redirects.

The caller must ensure no other device/process is performing contest requests.
This is not a vulnerability scanner. Never use it unattended.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

# Exact names from the edition scope, subject to a fresh manual check before use.
# Deliberately omitted: the ambiguous pllum/plum, mwdb/wmdb and ctf entries;
# wildcard discovery, DNS enumeration, and Wladyslawowo are never performed.
HOSTS = {
    'nask': ('nask.pl', 'dyzurnet.pl', 'dns.pl', 'oad.nask.pl',
             'zglos-dezinformacje.nask.pl', 'bezpiecznymiesiac.pl',
             'secure.edu.pl', 'bezpiecznewybory.pl', '116sos.pl',
             'science.nask.pl', 'dataannotation.pllum.org.pl'),
    'cert': ('cert.pl', 'm.cert.pl', 'incydent.cert.pl', 'moje.cert.pl',
             'n6portal.cert.pl', 'hack.cert.pl'),
    'gov': ('www.gov.pl',),
    # Exact name observed in public search, covered by the published wildcard;
    # manual edition/scope verification still mandatory at each run.
    'mszyfr': ('mas.komunikator.narodowy.gov.pl',),
}
START = date(2026, 11, 3)
END = date(2026, 11, 30)
MAX_REQUESTS = 16


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def plan(programs):
    if not programs or len(set(programs)) != len(programs) or any(p not in HOSTS for p in programs):
        raise ValueError('unknown, duplicate or empty program selection')
    groups = [HOSTS[p] for p in programs]
    return [(programs[j], group[i]) for i in range(max(map(len, groups)))
            for j, group in enumerate(groups) if i < len(group)]


def verify_review(reviewed_on, today=None):
    today = today or date.today()
    if not START <= today <= END or reviewed_on != today.isoformat():
        raise ValueError('edition inactive or review date is not today')


@contextmanager
def machine_lock(path):
    """Local same-user lock; independent hosts/runners are NOT coordinated."""
    path = Path(path)
    with path.open('x', encoding='ascii') as f:
        f.write(str(os.getpid()) + '\n')
    try:
        yield
    finally:
        path.unlink()


def request_status(host, opener):
    """HTTPS GET / only. Read no response bodies; follow no redirects."""
    url = 'https://' + host + '/'
    response = None
    try:
        try:
            response = opener.open(Request(url, headers={'User-Agent': 'NASKLab/0.2 public status check',
                                                         'Accept-Encoding': 'identity'}), timeout=10)
        except HTTPError as e:
            response = e  # only status, not headers or error body
        return response.code
    finally:
        if response is not None:
            response.close()


def run(programs, max_requests, opener, clock=time.monotonic, sleep=time.sleep):
    if type(max_requests) is not int or not 1 <= max_requests <= MAX_REQUESTS:
        raise ValueError('request budget must be 1..16')
    jobs = plan(programs)[:max_requests]
    results = []
    previous = None
    for program, host in jobs:
        if previous is not None:
            remaining = 1.0 - (clock() - previous)
            if remaining > 0:
                sleep(remaining)
        previous = clock()
        try:
            status = request_status(host, opener)
        except (OSError, URLError, TimeoutError):
            results.append({'program': program, 'host': host, 'status': None, 'stop': 'transport_error'})
            break
        row = {'program': program, 'host': host, 'status': status}
        # Stop the entire run immediately on access denial, rate limiting or server errors.
        if status in (403, 429) or 500 <= status <= 599:
            row['stop'] = 'access_denied_rate_limited_or_service_error'
            results.append(row)
            break
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', action='append', required=True, choices=list(HOSTS))
    parser.add_argument('--requests', type=int, default=4)
    parser.add_argument('--execute', action='store_true', help='explicitly allow bounded requests')
    parser.add_argument('--reviewed-on', help='date YYYY-MM-DD, after manually checking current terms and scope')
    parser.add_argument('--sole-operator', action='store_true', help='confirm no other machines/runners are testing')
    args = parser.parse_args()
    try:
        if not 1 <= args.requests <= MAX_REQUESTS:
            raise ValueError('request budget must be 1..16')
        jobs = plan(args.program)[:args.requests]
        if not args.execute:
            print(json.dumps({'mode': 'dry-run', 'planned': jobs, 'network_requests': 0}))
            return
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            raise ValueError('live collection disabled in GitHub Actions')
        verify_review(args.reviewed_on)
        if not args.sole_operator:
            raise ValueError('confirm no other concurrent contest traffic with --sole-operator')
        # Explicit direct networking, no environment-configured proxies or cookie jar.
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with machine_lock(Path.home() / '.nasklab-network.lock'):
            results = run(args.program, args.requests, opener)
        print(json.dumps({'mode': 'root-status-only', 'results': results}, ensure_ascii=False))
    except (ValueError, FileExistsError) as e:
        parser.exit(2, 'Nie uruchomiono: ' + str(e) + '\n')


if __name__ == '__main__':
    main()
