import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import Job, SpacedLimiter, analyze, run_fixture, schedule, validate_url

HOSTS = {'nask.example.invalid'}

class TestScope(unittest.TestCase):
    def test_allowed(self):
        validate_url('https://nask.example.invalid/fixture', HOSTS)
        validate_url('https://nask.example.invalid:443/fixture', HOSTS)

    def test_denied_urls(self):
        for url in ['https://nask.pl/', 'https://evil.nask.example.invalid/',
                    'https://nask.example.invalid.evil/', 'https://nask.example.invalid@evil/',
                    'http://nask.example.invalid/', 'https://nask.example.invalid:444/',
                    'https://nask.example.invalid/%2e%2e/', 'https://nask.example.invalid/../x',
                    'https://nask.example.invalid/?x=1', 'https://nask.example.invalid/#a',
                    'https://nask.example.invalid/\nx']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url, HOSTS)

    def test_reject_real_host_even_when_listed(self):
        with self.assertRaises(ValueError):
            validate_url('https://nask.pl/', {'nask.pl'})

class TestSchedule(unittest.TestCase):
    def test_fair_and_priority(self):
        jobs = [Job('NASK', f'/n{i}', 'a') for i in range(4)] + [Job('CERT', f'/c{i}', 'a') for i in range(2)]
        self.assertEqual([j.program for j in schedule(jobs)], ['NASK', 'NASK', 'CERT', 'NASK', 'NASK', 'CERT'])

    def test_all_preserved(self):
        jobs = [Job(str(i % 3), str(i), 'a') for i in range(99)]
        self.assertCountEqual(schedule(jobs), jobs)

class TestLimiter(unittest.TestCase):
    def test_spacing_no_burst(self):
        class Clock:
            now = 0.0
            def read(self): return self.now
            def sleep(self, seconds): self.now += seconds
        c = Clock()
        lim = SpacedLimiter(2, c.read, c.sleep)
        times = []
        for _ in range(5):
            lim.wait(); times.append(c.now)
        self.assertEqual(times, [0, .5, 1, 1.5, 2])
        c.now += 10
        lim.wait(); lim.wait()
        self.assertEqual(c.now, 12.5)

    def test_stop_during_wait_blocks_dispatch(self):
        class Clock:
            now = 0.0
            def read(self): return self.now
            def sleep(self, seconds):
                self.now += seconds
                limiter.stop()
        c = Clock()
        limiter = SpacedLimiter(2, c.read, c.sleep)
        limiter.wait()
        with self.assertRaisesRegex(RuntimeError, 'stopped'):
            limiter.wait()
        with self.assertRaisesRegex(RuntimeError, 'stopped'):
            limiter.wait()

    def test_invalid_rates(self):
        for rate in [0, -1, 3.1, float('nan'), float('inf')]:
            with self.subTest(rate=rate), self.assertRaises(ValueError): SpacedLimiter(rate)

class TestAnalysis(unittest.TestCase):
    def test_demo(self):
        result = run_fixture(Path(__file__).resolve().parents[1] / 'fixtures/demo.json')
        self.assertEqual(result['executed_fixture_jobs'], 10)
        self.assertEqual(len(result['observations']), 1)
        self.assertEqual(result['observations'][0]['program'], 'NASK')
        self.assertIn('nie stanowi dowodu', result['observations'][0]['assessment'])

    def test_identical_not_finding(self):
        rec = {'program':'NASK', 'url':'https://nask.example.invalid/', 'status':200, 'fingerprint':'same'}
        self.assertEqual(analyze([dict(rec, variant='a'), dict(rec, variant='b')]), [])

    def test_duplicate_rejected(self):
        record = {'program':'NASK','url':'https://nask.example.invalid/', 'variant':'a','status':200,'fingerprint':'x'}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'demo.json'
            p.write_text(json.dumps({'allowed_hosts':['nask.example.invalid'],'cases':[record,record]}))
            with self.assertRaises(ValueError): run_fixture(p)

if __name__ == '__main__': unittest.main()
