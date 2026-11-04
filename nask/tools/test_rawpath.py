"""Testy offline `nask/tools/rawpath.py` — zero sieci, zero zadania.

Uruchamianie (pytest znika z sandboxa miedzy turami, wiec unittest jest kanonem):
    python3 -m unittest test_rawpath -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rawpath  # noqa: E402
from rawpath import (  # noqa: E402
    Limiter, RateError, ScopeError, check_scope, classify, cross_hash_evidence,
    load_plan, raw_path_and_query, run_plan, summarize,
)

GOOD = "https://science.nask.pl/api/media/robots.txt"


class TestScopeGuard(unittest.TestCase):
    def test_twelve_hosts_accepted(self):
        for host in rawpath.SCOPE_HOSTS:
            check_scope(f"https://{host}/x")  # nie moze rzucic

    def test_rejects_out_of_scope(self):
        bad = [
            "http://dns.pl/.env",                      # schemat
            "https://www.nask.pl/",                    # literal spoza §5 (NASK bez `*`)
            "https://www.dns.pl/",                     # subdomena nieobjeta
            "https://panel.dns.pl/",                   # zaplecze
            "https://nask.pl.evil.tld/x",              # podszycie
            "https://user@dns.pl/x",                   # userinfo
            "https://dns.pl:8443/x",                   # port
            "https://hack.cert.pl/",                   # inny program (platforma)
            "https://mwdb.cert.pl/api/server",         # inny program
            "https://gmina-wladyslawowo.pl/",          # wyklaczone przez usera
            "https://science.nask.pl.evil/x",
        ]
        for url in bad:
            with self.assertRaises(ScopeError, msg=url):
                check_scope(url)

    def test_scope_has_exactly_12_hosts(self):
        self.assertEqual(len(rawpath.SCOPE_HOSTS), 12)


class TestLimiter(unittest.TestCase):
    def test_refuses_above_regulation_ceiling(self):
        for rps in (5.1, 6, 50):
            with self.assertRaises(RateError, msg=str(rps)):
                Limiter(rps)

    def test_accepts_ceiling_and_default(self):
        self.assertEqual(Limiter(5.0).min_gap, 1 / 5.0)
        self.assertEqual(Limiter(1.0).min_gap, 1.0)

    def test_rejects_non_positive(self):
        for rps in (0, -1):
            with self.assertRaises(RateError):
                Limiter(rps)


class TestRawPath(unittest.TestCase):
    """Kluczowa wlasnosc: sciezka wychodzi DOSŁOWNIE (bez normalizacji)."""

    def cases(self):
        return [
            ("https://science.nask.pl/api/media/%2e%2e%2frobots.txt",
             "/api/media/%2e%2e%2frobots.txt"),
            ("https://science.nask.pl/api/media/..%2f..%2fwp-content/x.jpg",
             "/api/media/..%2f..%2fwp-content/x.jpg"),
            ("https://science.nask.pl/a/../b", "/a/../b"),
            ("https://science.nask.pl/api/media/%252e%252e%252flicense.txt",
             "/api/media/%252e%252e%252flicense.txt"),
            ("https://dns.pl/.env?x=1&y=2", "/.env?x=1&y=2"),
            ("https://science.nask.pl/api/downloadFile?fileId=-1",
             "/api/downloadFile?fileId=-1"),
        ]

    def test_paths_preserved_verbatim(self):
        for url, expected in self.cases():
            self.assertEqual(raw_path_and_query(check_scope(url)), expected, url)


class TestClassifier(unittest.TestCase):
    def rec(self, **kw):
        base = {"status": 200, "content_type": "text/html", "bytes_read": 1000,
                "markers": {}, "secret_marker_hits": 0, "error": None}
        base.update(kw)
        return base

    def test_soft_404_is_negative_not_hit(self):
        self.assertEqual(classify(self.rec(markers={"HTML_DOC": 1, "SOFT404_PL": 2}, bytes_read=51201)),
                         "soft-404-html")

    def test_homepage_is_plain_html(self):
        self.assertEqual(classify(self.rec(markers={"HTML_DOC": 1})), "html-page")

    def test_spa_shell(self):
        self.assertEqual(classify(self.rec(bytes_read=713, markers={"HTML_DOC": 1, "SPA_SHELL": 1})),
                         "spa-catch-all-shell")

    def test_secret_file_is_candidate(self):
        self.assertEqual(classify(self.rec(content_type="text/plain", bytes_read=300,
                                          markers={"ENV_ASSIGNMENTS": 4, "SECRET_KEYS": 1},
                                          secret_marker_hits=5)),
                         "CANDIDATE-SECRET-FILE")

    def test_php_source_is_candidate(self):
        self.assertEqual(classify(self.rec(content_type="text/plain", bytes_read=3000,
                                          markers={"PHP_SOURCE": 1}, secret_marker_hits=1)),
                         "CANDIDATE-SECRET-FILE")

    def test_405_means_route_exists(self):
        self.assertEqual(classify(self.rec(status=405, content_type="application/json", bytes_read=30)),
                         "method-not-allowed-route-exists")

    def test_403_with_waf_marker(self):
        self.assertEqual(classify(self.rec(status=403, content_type="text/html", bytes_read=1484,
                                          markers={"WAF_BLOCK": 1})),
                         "blocked-waf-or-auth")

    def test_transport_error(self):
        self.assertEqual(classify(self.rec(status=None, error="transport: ConnectionResetError: reset")),
                         "transport-error")

    def test_redirect_not_followed(self):
        self.assertEqual(classify(self.rec(status=302, bytes_read=0, content_type=None)),
                         "redirect-not-followed")

    def test_media_and_json(self):
        self.assertEqual(classify(self.rec(content_type="image/jpeg", bytes_read=65536,
                                          markers={"JPEG_MAGIC": 1})), "media-file")
        self.assertEqual(classify(self.rec(content_type="application/json", bytes_read=9543,
                                          markers={"JSON_BODY": 1})), "json-response")


class TestRedaction(unittest.TestCase):
    def test_sensitive_path_blocks_preview(self):
        self.assertTrue(rawpath.SENSITIVE_ID_RE.search("/api/media/wp-config.php"))
        self.assertTrue(rawpath.SENSITIVE_ID_RE.search("probe-env-file"))
        self.assertIsNone(rawpath.SENSITIVE_ID_RE.search("/api/media/robots.txt"))

    def test_preview_sanitizes_nonprintables(self):
        self.assertEqual(rawpath._sanitize_preview(b"abc\x00\xffdef"), "abc..def")

    def test_preview_truncated(self):
        self.assertLessEqual(len(rawpath._sanitize_preview(b"x" * 5000)), 200)


class TestCrossHash(unittest.TestCase):
    def test_pair_detected(self):
        ev = cross_hash_evidence([
            {"id": "ctl", "raw_path": "/api/media/wp-content/x.jpg", "sha256": "a" * 64, "bytes_read": 64},
            {"id": "trav", "raw_path": "/api/media/%2e%2e%2fwp-content/x.jpg", "sha256": "a" * 64, "bytes_read": 64},
            {"id": "other", "raw_path": "/robots.txt", "sha256": "b" * 64, "bytes_read": 64},
        ])
        self.assertEqual(len(ev), 1)
        self.assertEqual(len(ev[0]["identical_bodies"]), 2)

    def test_empty_bodies_not_paired(self):
        self.assertEqual(cross_hash_evidence([
            {"id": "a", "sha256": None, "bytes_read": 0},
            {"id": "b", "sha256": None, "bytes_read": 0},
        ]), [])


class TestPlan(unittest.TestCase):
    def test_plan_validated_before_any_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "plan.json"
            p.write_text(json.dumps({"probes": [{"id": "x", "url": "https://evil.example/x"}]}),
                         encoding="utf-8")
            with self.assertRaises(ScopeError):
                load_plan(p)

    def test_plan_accepts_scoped_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "plan.json"
            p.write_text(json.dumps([{"id": "a", "url": GOOD, "why": "kontrola"}]), encoding="utf-8")
            plan = load_plan(p)
        self.assertEqual(plan[0]["url"], GOOD)

    def test_dry_run_sends_nothing(self):
        def boom(*a, **kw):  # jakiekolwiek zadanie = oblany test
            raise AssertionError("dry-run wyslal zadanie")
        original, rawpath.probe = rawpath.probe, boom
        try:
            report = run_plan([{"id": "a", "url": GOOD, "why": ""}], dry_run=True)
        finally:
            rawpath.probe = original
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["probes"][0]["raw_path"], "/api/media/robots.txt")


class TestSummarize(unittest.TestCase):
    def test_counts_and_candidates(self):
        s = summarize([
            {"id": "a", "verdict": "soft-404-html"},
            {"id": "b", "verdict": "CANDIDATE-SECRET-FILE", "url": "https://dns.pl/.env",
             "status": 200, "content_type": "text/plain", "bytes_read": 12},
            {"id": "c", "verdict": "transport-error"},
            {"id": "d", "verdict": "refused-out-of-scope"},
        ])
        self.assertEqual(s["count"], 4)
        self.assertEqual(len(s["candidates"]), 1)
        self.assertEqual(s["candidates"][0]["id"], "b")
        self.assertEqual(s["transport_errors"], ["c"])
        self.assertEqual(s["out_of_scope_refusals"], ["d"])


class TestMarkersOnRealBytes(unittest.TestCase):
    """Wzorce sa tekstowe (UTF-8) i kompilowane do bajtow — musza lapac realne strony."""

    def test_polish_soft404(self):
        body = "<html><body>Ups! Coś poszło nie tak... 404 - Strona nieznaleziona</body></html>".encode("utf-8")
        m = rawpath._markers(body)
        self.assertIn("SOFT404_PL", m)
        self.assertIn("HTML_DOC", m)

    def test_dyżurnet_404_page(self):
        body = "<html><h1>Nie znaleziono strony</h1></html>".encode("utf-8")
        self.assertIn("SOFT404_PL", rawpath._markers(body))

    def test_env_file_markers(self):
        body = b"DB_PASSWORD=supersecret\nAPI_KEY=abcdef0123456789\nDEBUG=false\n"
        m = rawpath._markers(body)
        self.assertIn("ENV_ASSIGNMENTS", m)
        self.assertIn("SECRET_KEYS", m)

    def test_git_ref_marker(self):
        self.assertIn("GIT_REF", rawpath._markers(b"ref: refs/heads/main\n"))
        self.assertIn("GIT_REF", rawpath._markers(b"[core]\n\trepositoryformatversion = 0\n"))

    def test_wp_config_marker(self):
        body = b"<?php\n/** WordPress - Web publishing software */\ndefine('DB_NAME', 'x');\n"
        self.assertIn("WP_CONFIG_HEADER", rawpath._markers(body))
        self.assertIn("PHP_SOURCE", rawpath._markers(body))

    def test_binary_magics(self):
        self.assertIn("JPEG_MAGIC", rawpath._markers(b"\xff\xd8\xff\xe0junk"))
        self.assertIn("PNG_MAGIC", rawpath._markers(b"\x89PNG\r\n\x1a\n"))
        self.assertIn("PDF_MAGIC", rawpath._markers(b"%PDF-1.7 ..."))
        self.assertIn("ZIP_MAGIC", rawpath._markers(b"PK\x03\x04zip"))

    def test_apache_status_marker(self):
        self.assertIn("APACHE_STATUS", rawpath._markers(b"<title>Apache Server Status</title>"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
