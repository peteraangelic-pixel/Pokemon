from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_events import analyze_events

def event(label, ts): return {'source':label, 'started_at':ts}

class Tests(unittest.TestCase):
    def test_global_cross_sources_count(self):
        data = [event('A' if i%2 else 'B', f'2026-11-03T22:00:00.{i*100:03d}Z') for i in range(6)]
        result = analyze_events(data)
        self.assertEqual(result['max_starts_in_one_second'], 6)
        self.assertEqual(result['max_window_sources'], ['A','B'])
        self.assertTrue(result['over_five_observed'])

    def test_half_open_second_and_timezone(self):
        records = [event('A', '2026-11-03T22:00:00.000Z'), event('B', '2026-11-03T23:00:01.000+01:00')]
        result = analyze_events(records)
        self.assertEqual(result['max_starts_in_one_second'], 1)

    def test_reject_coarse_or_missing_zone_and_extra_fields(self):
        for row in [event('A','2026-11-03T22:00:00Z'), event('A','2026-11-03T22:00:00.000'),
                    {'source':'A','started_at':'2026-11-03T22:00:00.000Z','body':'secret'},
                    event('bad label','2026-11-03T22:00:00.000Z')]:
            with self.subTest(row=row), self.assertRaises(ValueError): analyze_events([row])

    def test_no_false_safety_claim_empty(self):
        result = analyze_events([])
        self.assertEqual(result['events'], 0)
        self.assertIn('not verified', result['warning'])

if __name__ == '__main__': unittest.main()
