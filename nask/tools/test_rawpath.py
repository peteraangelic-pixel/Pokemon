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


class TestRegressionFromRun1(unittest.TestCase):
    """Odtworzone DOKLADNE przypadki z `nask/reports/rawpath-001-run1.json`.

    Zasada przyjeca od Gemmy-A (ich 52 falszywe trafienia): kazdy blad pomiaru
    dostaje test regresyjny, zeby nie wrocil w nastepnym przebiegu.
    """

    def test_dns_env_is_homepage_not_secret_file(self):
        # run1: dns-B01 200/51213 B text/html — run007 (7911) mial to jako "interesting"
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 51213,
               "markers": {"HTML_DOC": 2, "SPA_SHELL": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "html-page")

    def test_dyżurnet_homepage_is_not_waf_block(self):
        # KOREKTA #28: "cloudflare" w ciele strony glownej nie jest blokada
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 65536,
               "markers": {"HTML_DOC": 2, "WAF_VENDOR": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "html-page")

    def test_dyżurnet_soft404_beats_vendor_word(self):
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 58279,
               "markers": {"SOFT404_PL": 8, "HTML_DOC": 2, "WAF_VENDOR": 1},
               "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "soft-404-html")

    def test_zglos_soft404(self):
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 30260,
               "markers": {"SOFT404_PL": 4, "HTML_DOC": 2}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "soft-404-html")

    def test_real_block_page_still_detected(self):
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 1484,
               "markers": {"WAF_BLOCK": 1, "HTML_DOC": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "blocked-waf-200")
        rec403 = dict(rec, status=403)
        self.assertEqual(classify(rec403), "blocked-waf-or-auth")

    def test_hive_shell_and_control_share_hash(self):
        # run1: /.env i / daly IDENTYCZNY sha256 (908ce0b4) = catch-all, nie plik
        shell = {"status": 200, "content_type": "text/html", "bytes_read": 713,
                 "markers": {"HTML_DOC": 2, "SPA_SHELL": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(shell), "spa-catch-all-shell")
        ev = cross_hash_evidence([
            {"id": "hive-B09", "raw_path": "/.env", "sha256": "9" * 64, "bytes_read": 713},
            {"id": "hive-B10", "raw_path": "/", "sha256": "9" * 64, "bytes_read": 713},
        ])
        self.assertEqual(len(ev), 1)

    def test_pdf_control_is_media(self):
        rec = {"status": 200, "content_type": "application/pdf", "bytes_read": 65536,
               "markers": {"PDF_MAGIC": 1, "JSON_BODY": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "media-file")

    def test_hive_405_route_exists(self):
        rec = {"status": 405, "content_type": "application/json", "bytes_read": 31,
               "markers": {"JSON_BODY": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "method-not-allowed-route-exists")

    def test_timeout_is_transport_error_not_clean(self):
        # run1: sci-A07 i sci-A15 = timeout 15 s. Brak odpowiedzi NIGDY nie jest "czysto"
        rec = {"status": None, "content_type": None, "bytes_read": 0, "markers": {},
               "secret_marker_hits": 0, "error": "timeout: TimeoutError"}
        self.assertEqual(classify(rec), "transport-error")


class TestDecidePreview(unittest.TestCase):
    def test_small_error_page_always_recorded(self):
        out = rawpath.decide_preview(400, b"<html><body>Bad Request</body></html>",
                                     "sci-A12-wpconfig-depth3-secret",
                                     "/api/media/%2e%2e%2fwp-config.php", 0)
        self.assertIsNotNone(out)
        self.assertIn("Bad Request", out)

    def test_sensitive_body_never_recorded(self):
        out = rawpath.decide_preview(200, b"<?php define('DB_PASSWORD','sekret');",
                                     "sci-A09-wpconfig-depth0-secret",
                                     "/api/media/wp-config.php", 3)
        self.assertIsNone(out)

    def test_secret_marker_blocks_preview_even_for_innocent_id(self):
        out = rawpath.decide_preview(200, b"DB_PASSWORD=x\nAPI_KEY=y\n", "dns-B01", "/.env", 2)
        self.assertIsNone(out)

    def test_ordinary_html_preview_ok(self):
        out = rawpath.decide_preview(200, b"<!doctype html><html>strona</html>",
                                     "dns-B05-home-ctl", "/", 0)
        self.assertIn("doctype", out)

    def test_large_error_body_not_previewed_if_sensitive(self):
        out = rawpath.decide_preview(500, b"x" * 5000, "probe-credentials", "/creds", 0)
        self.assertIsNone(out)


class TestJsonKeySchema(unittest.TestCase):
    def test_names_without_values(self):
        body = json.dumps({"centres": [{"address": {"city": "Slawno", "street": "Gdanska"},
                                        "email": "a@b.c", "phone": "123"}]}).encode()
        schema = rawpath.json_key_schema(body)
        self.assertIn("centres[].address.city", schema["keys"])
        self.assertIn("centres[].email", schema["keys"])
        blob = json.dumps(schema, ensure_ascii=False)
        for value in ("Slawno", "Gdanska", "a@b.c", "123"):
            self.assertNotIn(value, blob, f"WARTOSC {value} wyciekla do schematu")

    def test_personal_like_flagged(self):
        body = json.dumps({"user": {"email": "x", "phone": "y", "nickname": "z"}}).encode()
        schema = rawpath.json_key_schema(body)
        joined = " ".join(schema["personal_like"])
        self.assertIn("email", joined)
        self.assertIn("phone", joined)

    def test_truncated_json_is_safe(self):
        self.assertEqual(rawpath.json_key_schema(b'{"centres":[{"a"'), {})

    def test_non_json_is_safe(self):
        self.assertEqual(rawpath.json_key_schema(b"<!doctype html><html>"), {})

    def test_depth_and_key_caps(self):
        deep = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        schema = rawpath.json_key_schema(json.dumps(deep).encode(), max_depth=2)
        self.assertTrue(all(k.count(".") <= 2 for k in schema["keys"]), schema["keys"])
        wide = {f"k{i}": i for i in range(500)}
        schema2 = rawpath.json_key_schema(json.dumps(wide).encode(), max_keys=10)
        self.assertLessEqual(len(schema2["keys"]), 11)


class TestRegressionFromRun2Run3(unittest.TestCase):
    """Rekordy z `rawpath-002-run2.json` i `rawpath-003-run3.json`."""

    def test_root_robots_is_not_a_candidate(self):
        # run3 H02: 200 text/plain 73 B = publiczny robots.txt (KOREKTA #30)
        rec = {"status": 200, "content_type": "text/plain", "bytes_read": 73,
               "markers": {}, "secret_marker_hits": 0, "raw_path": "/robots.txt"}
        self.assertEqual(classify(rec), "public-root-file")

    def test_same_file_via_traversal_still_candidate(self):
        rec = {"status": 200, "content_type": "text/plain", "bytes_read": 73,
               "markers": {}, "secret_marker_hits": 0,
               "raw_path": "/api/media/%2e%2e/%2e%2e/%2e%2e/%2e%2e/robots.txt"}
        self.assertEqual(classify(rec), "CANDIDATE-PLAINTEXT-FILE")

    def test_well_known_security_txt_is_public(self):
        rec = {"status": 200, "content_type": "text/plain", "bytes_read": 300,
               "markers": {}, "secret_marker_hits": 0, "raw_path": "/.well-known/security.txt"}
        self.assertEqual(classify(rec), "public-root-file")

    def test_env_file_at_root_is_still_candidate(self):
        # `/.env` nie jest na liscie publicznych plikow korzenia
        rec = {"status": 200, "content_type": "text/plain", "bytes_read": 300,
               "markers": {"ENV_ASSIGNMENTS": 3}, "secret_marker_hits": 3, "raw_path": "/.env"}
        self.assertEqual(classify(rec), "CANDIDATE-SECRET-FILE")

    def test_remote_disconnected_is_transport_error(self):
        # run3 H04/H05/H07: brzeg zrywa polaczenie przy probie ucieczki
        rec = {"status": None, "content_type": None, "bytes_read": 0, "markers": {},
               "secret_marker_hits": 0,
               "error": "transport: RemoteDisconnected: Remote end closed connection without response"}
        self.assertEqual(classify(rec), "transport-error")

    def test_app_404_page_after_normalization(self):
        # run3 H06: 404/17524 B text/html = strona 404 aplikacji (nginx zwija `..` i clampuje)
        rec = {"status": 404, "content_type": "text/html", "bytes_read": 17524,
               "markers": {"HTML_DOC": 2, "SPA_SHELL": 1}, "secret_marker_hits": 0}
        self.assertEqual(classify(rec), "not-found")

    def test_static_cookie_hash_is_not_a_finding_by_itself(self):
        # run2 F01-F03: identyczny sha256 ciala w 3 probkach => wartosc stala
        recs = [{"id": f"sos-F0{i}", "raw_path": "/api/fetch-cookie-hash",
                 "sha256": "3" * 64, "bytes_read": 30} for i in (1, 2, 3)]
        ev = cross_hash_evidence(recs)
        self.assertEqual(len(ev), 1)
        self.assertEqual(len(ev[0]["identical_bodies"]), 3)

    def test_json_schema_of_public_directory(self):
        body = json.dumps({"centres": [{"name": "X", "phone": "Y", "email": "Z",
                                        "geoCords": {"lat": 1, "lon": 2}}],
                           "totalItems": 1, "lastPage": 1}).encode()
        schema = rawpath.json_key_schema(body)
        self.assertIn("centres[].geoCords.lat", schema["keys"])
        self.assertIn("totalItems", schema["keys"])
        blob = json.dumps(schema, ensure_ascii=False)
        for value in ("X", "Y", "Z"):
            self.assertNotIn('"%s"' % value, blob)


class TestRegressionFromRun7(unittest.TestCase):
    """Rekordy z `rawpath-004-run7.json` (mining 129 bundli)."""

    def test_js_bundle_is_not_secret_file(self):
        # KOREKTA #38: polyfills z `SECRET_KEYS` x8 to bundel JS, nie plik konfiguracyjny
        rec = {"status": 200, "content_type": "application/javascript", "bytes_read": 112594,
               "markers": {"WAF_VENDOR": 2, "SECRET_KEYS": 8}, "secret_marker_hits": 8}
        self.assertEqual(classify(rec), "js-bundle-with-keyword-hits")

    def test_html_with_keyword_hits_is_not_secret_file(self):
        rec = {"status": 200, "content_type": "text/html", "bytes_read": 417741,
               "markers": {"HTML_DOC": 3, "SECRET_KEYS": 1}, "secret_marker_hits": 1}
        self.assertEqual(classify(rec), "html-page")

    def test_real_config_file_is_still_candidate(self):
        rec = {"status": 200, "content_type": "text/plain", "bytes_read": 300,
               "markers": {"ENV_ASSIGNMENTS": 4, "SECRET_KEYS": 1}, "secret_marker_hits": 5}
        self.assertEqual(classify(rec), "CANDIDATE-SECRET-FILE")

    def test_octet_stream_with_secret_hits_is_candidate(self):
        rec = {"status": 200, "content_type": "application/octet-stream", "bytes_read": 900,
               "markers": {"GIT_REF": 1}, "secret_marker_hits": 1}
        self.assertEqual(classify(rec), "CANDIDATE-SECRET-FILE")

    def test_extension_from_content_type_when_url_has_none(self):
        from rawpath import CT_EXT
        self.assertEqual(CT_EXT["application/json"], ".json")
        self.assertEqual(CT_EXT["application/javascript"], ".js")


class TestParamFilter(unittest.TestCase):
    """KOREKTA #39: 662 surowe 'parametry' z run7 to w wiekszosci szum minifikatora."""

    def test_minifier_noise_rejected(self):
        from bundle_scan import is_real_param
        for noise in ("null", "return", "this", "NaN", "ut", "io", "en", "break", "as",
                      "gl", "vi", "Ii", "Ir", "Lr", "Qi", "ec", "ia", "Ba", "Bm",
                      "password", "text", "true", "u1", "q7"):
            self.assertFalse(is_real_param(noise), noise)

    def test_real_params_kept(self):
        from bundle_scan import is_real_param
        for real in ("fileId", "query", "lang", "perPage", "domain", "_format",
                     "rest_route", "userId", "locales", "searchPhrase", "reason",
                     "urls", "accept", "type"):
            self.assertTrue(is_real_param(real), real)

    def test_scan_text_filters_params(self):
        from bundle_scan import scan_text
        js = 'fetch("/api/v1/tasks?fileId=1&type=x&perPage=10");var null=this;function(a){return a}'
        r = scan_text("t.js", js)
        self.assertIn("fileId", r["params"])
        self.assertIn("perPage", r["params"])
        self.assertNotIn("null", r["params"])
        self.assertNotIn("return", r["params"])
        self.assertNotIn("this", r["params"])


class TestPiiMarkers(unittest.TestCase):
    """KOREKTA #43: liczniki PII (tylko liczby) + wyciszenie podgladu."""

    @staticmethod
    def _valid_pesel(base="8001011234"):
        w = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
        tot = sum(int(d) * wi for d, wi in zip(base, w))
        return base + str((10 - tot % 10) % 10)

    def test_pesel_validator(self):
        from rawpath import pesel_ok
        good = self._valid_pesel()
        self.assertTrue(pesel_ok(good))
        self.assertFalse(pesel_ok(good[:10] + str((int(good[10]) + 1) % 10)))
        self.assertFalse(pesel_ok("80130112345"))   # miesiac 13
        self.assertFalse(pesel_ok("80013212345"))   # dzien 32
        self.assertFalse(pesel_ok("00000000000"))
        self.assertFalse(pesel_ok("1234567890"))    # 10 cyfr
        self.assertFalse(pesel_ok("abcdefghijkl"))

    def test_counts_only_and_types(self):
        from rawpath import pii_markers
        pesel = self._valid_pesel()
        body = ('{"email":"anna.nowak@przyklad.pl","tel":"+48 601 234 567",'
                '"pesel":"%s","iban":"PL00000000000000000000000000"}' % pesel).encode()
        m = pii_markers(body, "application/json")
        self.assertEqual(m, {"PII_EMAIL": 1, "PII_PESEL": 1,
                             "PII_PHONE_PL": 1, "PII_IBAN": 1})
        self.assertEqual(pii_markers(body, "text/html"), {})
        self.assertEqual(pii_markers(body, "application/javascript"), {})
        self.assertEqual(pii_markers(b'{"x":"plain"}', "application/json"), {})

    def test_timestamp_is_not_pesel(self):
        from rawpath import pii_markers
        body = b'{"ts":"1730700000000","n":17000000001}'
        self.assertEqual(pii_markers(body, "application/json").get("PII_PESEL"), None)

    def test_preview_suppressed_when_pii(self):
        from rawpath import decide_preview
        self.assertIsNone(decide_preview(200, b'{"e":"a@b.pl"}', "p", "/api/x", 0,
                                         pii_marker_hits=1))
        self.assertIsNotNone(decide_preview(200, b'{"e":1}', "p", "/api/x", 0,
                                            pii_marker_hits=0))
        # mala strona bledu nadal jest zapisywana (zasada 1 z korekty #28b)
        self.assertIsNotNone(decide_preview(404, b'not found', "p", "/api/x", 0,
                                            pii_marker_hits=0))

    def test_verdict_pii(self):
        from rawpath import classify
        rec = {"status": 200, "content_type": "application/json", "bytes_read": 500,
               "markers": {"PII_EMAIL": 7}, "pii_marker_hits": 7, "raw_path": "/api/x"}
        self.assertEqual(classify(rec), "CANDIDATE-PII-IN-RESPONSE")
        rec2 = dict(rec, markers={"SECRET_KEYS": 1}, secret_marker_hits=1,
                    content_type="application/octet-stream", pii_marker_hits=0)
        self.assertEqual(classify(rec2), "CANDIDATE-SECRET-FILE")

    def test_report_never_contains_pii_values(self):
        """Nawet przy trafieniu PII raport nie moze zawierac wartosci."""
        import rawpath
        pesel = self._valid_pesel()
        body = ('{"e":"anna.nowak@przyklad.pl","p":"%s"}' % pesel).encode()
        # bez sieci: sciezka raportowania na syntetycznym ciele
        m = rawpath.pii_markers(body, "application/json")
        blob = json.dumps({"markers": m,
                           "preview": rawpath.decide_preview(200, body, "p", "/api/x", 0,
                                                             pii_marker_hits=sum(m.values()))},
                          ensure_ascii=False)
        self.assertNotIn("anna.nowak", blob)
        self.assertNotIn(pesel, blob)
        self.assertNotIn("@przyklad.pl", blob)
        self.assertIn("PII_EMAIL", blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
