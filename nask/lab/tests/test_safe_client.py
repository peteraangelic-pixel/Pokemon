import io
import os
from datetime import date
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import safe_client as c

class Resp(io.BytesIO):
    def __init__(self, status):
        super().__init__(b'private body MUST NOT be read')
        self.code = status
    def read(self, *args):
        raise AssertionError('response body read')

class Opener:
    def __init__(self, statuses): self.statuses, self.calls = iter(statuses), []
    def open(self, req, timeout):
        self.calls.append(req.full_url)
        status = next(self.statuses)
        if status == 'error': raise URLError('test')
        if status >= 300:
            raise HTTPError(req.full_url, status, 'fixture', {}, Resp(status))
        return Resp(status)

class Clock:
    def __init__(self): self.now = 0
    def clock(self): return self.now
    def sleep(self, seconds): self.now += seconds

class Tests(unittest.TestCase):
    def test_controversial_hosts_and_wladyslawowo_absent(self):
        hosts = {h for values in c.HOSTS.values() for h in values}
        self.assertFalse(hosts & {'pllum.org.pl','plum.org.pl','mwdb.cert.pl','wmdb.cert.pl','ctf.hack.cert.pl'})
        self.assertNotIn('wladyslawowo', c.HOSTS)
        self.assertIn('mas.komunikator.narodowy.gov.pl', hosts)

    def test_round_robin_and_unknown(self):
        jobs = c.plan(['nask', 'cert', 'gov', 'mszyfr'])
        self.assertEqual([p for p, _ in jobs[:4]], ['nask','cert','gov','mszyfr'])
        for p in [[], ['nask','nask'], ['wladyslawowo']]:
            with self.assertRaises(ValueError): c.plan(p)

    def test_edition_review_required_today(self):
        c.verify_review('2026-11-03', date(2026, 11, 3))
        for reviewed, now in [('2026-11-02', date(2026, 11, 3)), ('2026-12-01', date(2026, 12, 1)), (None, date(2026, 11, 3))]:
            with self.assertRaises(ValueError): c.verify_review(reviewed, now)

    def test_stop_codes_and_network_errors(self):
        for status in [403, 429, 500, 503, 'error']:
            opener, clock = Opener([status, 200]), Clock()
            result = c.run(['nask', 'cert'], 2, opener, clock.clock, clock.sleep)
            self.assertEqual(len(result), 1)
            self.assertEqual(len(opener.calls), 1)
            self.assertIn('stop', result[0])

    def test_spacing_root_only_and_no_body_reads(self):
        opener, clock = Opener([200, 302, 200]), Clock()
        result = c.run(['nask', 'cert', 'gov'], 3, opener, clock.clock, clock.sleep)
        self.assertEqual(len(result), 3)
        self.assertEqual(clock.now, 2)
        self.assertEqual(opener.calls, ['https://nask.pl/', 'https://cert.pl/', 'https://www.gov.pl/'])
        self.assertNotIn('body', str(result))

    def test_disallow_redirect_following(self):
        self.assertIsNone(c.NoRedirect().redirect_request(Request('https://cert.pl/'), None, 302, 'redirect', {}, 'https://outside.invalid/'))

    def test_lock_exclusive_and_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            lock = Path(d) / 'lock'
            with c.machine_lock(lock):
                with self.assertRaises(FileExistsError):
                    with c.machine_lock(lock): pass
            self.assertFalse(lock.exists())

    def test_live_collection_disabled_in_actions(self):
        env = dict(os.environ, GITHUB_ACTIONS='true')
        p = subprocess.run([sys.executable, str(Path(c.__file__)), '--program', 'nask',
                            '--execute', '--sole-operator', '--reviewed-on', '2026-11-03'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 2)
        self.assertIn('disabled in GitHub Actions', p.stderr)

    def test_bad_budget_and_preview_without_network(self):
        for n in [0, 17, True]:
            with self.assertRaises(ValueError): c.run(['nask'], n, Opener([]))
        p = subprocess.run([sys.executable, str(Path(c.__file__)), '--program','nask','--requests','1'], capture_output=True, text=True, check=True)
        self.assertIn('"network_requests": 0', p.stdout)

if __name__ == '__main__': unittest.main()
