import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from har_triage import analyze, normalize_template, Observation

OBS = [
    Observation("GET", "https://example.invalid/api/tasks/101", "/api/tasks/{id}", 200, "A", ("id", "title")),
    Observation("GET", "https://example.invalid/api/tasks/102", "/api/tasks/{id}", 200, "A", ("id", "title")),
    Observation("GET", "https://example.invalid/api/tasks/101", "/api/tasks/{id}", 403, "B", ("detail",)),
    Observation("GET", "https://example.invalid/api/users/me", "/api/users/me", 200, "A"),
    Observation("GET", "https://example.invalid/api/users/me", "/api/users/me", 200, None),
    Observation("GET", "https://example.invalid/api/export?token=abc", "/api/export", 200, "A"),
    Observation("GET", "https://example.invalid/api/report", "/api/report", 200, None, cache_control="public, max-age=3600"),
    Observation("GET", "https://out.of.scope/api/x", "/api/x", 200, "A"),
]


class Tests(unittest.TestCase):
    def test_normalize_ids(self):
        self.assertEqual(normalize_template("/api/tasks/101"), "/api/tasks/{id}")
        self.assertEqual(normalize_template("/api/tasks/abc123deadbeef"), "/api/tasks/{id}")
        self.assertEqual(normalize_template("/api/public/5"), "/api/public/{id}")

    def test_permission_asymmetry_and_idor(self):
        findings = analyze(OBS)
        kinds = [f.kind for f in findings]
        self.assertIn("permission_asymmetry", kinds)
        self.assertIn("idor_candidate", kinds)
        for f in findings:
            self.assertEqual(f.severity_hypothesis, "hipoteza_do_weryfikacji")

    def test_unauth_and_token_and_cached(self):
        findings = analyze(OBS)
        kinds = [f.kind for f in findings]
        self.assertIn("unauth_access", kinds)
        self.assertIn("token_in_url", kinds)
        self.assertIn("sensitive_cached", kinds)

    def test_scope_excludes_out_of_scope(self):
        findings = analyze(OBS, scope_hosts=["example.invalid"])
        urls = {e for f in findings for e in f.evidence_sample}
        self.assertFalse(any("out.of.scope" in str(e) for e in urls))
        self.assertTrue(any(f.kind == "idor_candidate" for f in findings))

    def test_no_network_by_construction(self):
        # Module defines no network functions; this test documents intent.
        import har_triage as ht
        self.assertFalse(hasattr(ht, "requests"))
        self.assertFalse(hasattr(ht, "urlopen"))
        self.assertFalse(hasattr(ht, "get"))

    def test_reject_bad_status(self):
        with self.assertRaises(ValueError):
            Observation("GET", "https://example.invalid/x", "/x", 600)


if __name__ == "__main__":
    unittest.main()
