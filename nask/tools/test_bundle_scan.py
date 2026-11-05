"""Unit tests for nask/tools/bundle_scan.py — offline, no network."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bundle_scan import classify_id, scan_text, shannon  # noqa: E402

JS = """
const api = axios.create({ baseURL: "/api/v2" });
export async function loadTask(id) {
  const r = await fetch(`/api/v2/task/${id}?include=labels&owner=1`);
  return r.json();
}
axios.get("/api/v2/projects");
axios.patch("/api/v2/user/{userId}");
const cfg = { apiKey: "AKIAIOSFODNN7EXAMPLE", token: "changeme", password: "undefined" };
const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U";
const ids = ["1", "2", "3", "42", "3f2504e0-4f89-11d3-9a0c-0305e82c3301"];
"""


class TestScan(unittest.TestCase):
    def test_endpoints_extracted(self):
        r = scan_text("t.js", JS)
        self.assertIn("/api/v2/projects", r["endpoints"])
        self.assertIn("/api/v2/user/{userId}", r["endpoints"])

    def test_params_extracted(self):
        r = scan_text("t.js", JS)
        self.assertIn("include", r["params"])
        self.assertIn("userId", r["params"])

    def test_secrets_filtered(self):
        r = scan_text("t.js", JS)
        kinds = {s["kind"] for s in r["secrets"]}
        self.assertIn("aws_access_key_id", kinds)
        self.assertIn("jwt", kinds)
        # allow-lista: "changeme" i "undefined" nie daja wpisu
        self.assertEqual(len([s for s in r["secrets"] if s["length"] == len("changeme")]), 0)

    def test_secret_values_never_serialized(self):
        """KOREKTA #33: raport nie moze zawierac ZADNEGO fragmentu wartosci sekretu."""
        r = scan_text("t.js", JS)
        blob = json.dumps(r, ensure_ascii=False)
        for secret in ("AKIAIOSFODNN7EXAMPLE",
                       "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"):
            for frag in (secret, secret[:8], secret[:4] + "\u2026" + secret[-2:], secret[-6:]):
                self.assertNotIn(frag, blob, f"fragment sekretu w raporcie: {frag!r}")
        for s in r["secrets"]:
            self.assertEqual(sorted(s.keys()), ["entropy", "fingerprint", "kind", "length"])

    def test_fingerprint_stable_and_value_free(self):
        from bundle_scan import fingerprint
        self.assertEqual(fingerprint("abc123"), fingerprint("abc123"))
        self.assertNotEqual(fingerprint("abc123"), fingerprint("abc124"))
        self.assertEqual(len(fingerprint("x" * 100)), 12)
        self.assertNotIn("abc123", fingerprint("abc123"))

    def test_id_format_classifier(self):
        self.assertEqual(classify_id("42"), "sequential-int-candidate")
        self.assertEqual(classify_id("3f2504e0-4f89-11d3-9a0c-0305e82c3301"), "uuid")
        self.assertEqual(classify_id("01ARZ3NDEKTSV4RRFFQ69G5FAV"), "ulid")
        self.assertEqual(classify_id("0" * 40), "hash")

    def test_entropy_monotonic(self):
        self.assertGreater(shannon("aAbBcCdD12!@"), shannon("aaaaaaaaaaaa"))

    def test_no_crash_on_empty(self):
        r = scan_text("empty.js", "")
        self.assertEqual(r["endpoints"], [])
        self.assertEqual(r["secrets"], [])


class TestKorekta44(unittest.TestCase):
    """paths/hosts + sekrety w query stringu (bez wartosci w raporcie — #33)."""

    def test_query_value_secret_detected_fingerprint_only(self):
        from bundle_scan import scan_text
        token = "EAABsbCS1" + "kQ7zXpR2mV9dL4nT6yH8bC3fG5jW1sA0"
        js = 'var u="https://graph.example/x?access_token=' + token + '";fetch(u);'
        r = scan_text("t.js", js)
        self.assertEqual(len(r["secrets"]), 1)
        sec = r["secrets"][0]
        self.assertEqual(sec["kind"], "query_value_access_token")
        self.assertEqual(sec["length"], len(token))
        blob = json.dumps(r, ensure_ascii=False)
        self.assertNotIn(token, blob)
        self.assertNotIn(token[:12], blob)
        self.assertNotIn(token[-8:], blob)
        self.assertEqual(len(sec["fingerprint"]), 12)

    def test_template_placeholder_is_not_a_secret(self):
        from bundle_scan import scan_text
        js = 'u="/events/?access_token=${cfg.token}&key="+encodeURIComponent(k);'
        self.assertEqual(scan_text("t.js", js)["secrets"], [])

    def test_share_library_false_positive(self):
        """Bundel `35g9u-wrehnzi.js` (bezpiecznymiesiac) to biblioteka share-buttonow:
        `graph.facebook.com/?id=`, `access_token` jako NAZWA parametru. Bez literowej
        wartosci nie ma sekretu — to byl trop fałszywy i tak ma zostac."""
        from bundle_scan import scan_text
        js = ('var s=["https://www.facebook.com/sharer/sharer.php?u=",'
              '"https://graph.facebook.com/?id=","https://api.tumblr.com/v2/share/stats",'
              '"http://b.hatena.ne.jp/add?mode=confirm&url=",'
              '"/events/?access_token="+encodeURIComponent(t)+"&fields=id,title"];')
        r = scan_text("t.js", js)
        self.assertEqual(r["secrets"], [])          # brak literowej wartosci = brak sekretu
        self.assertIn("graph.facebook.com", r["hosts"])
        self.assertIn("access_token", r["params"])   # nazwa parametru zostaje (nie jest sekretem)
        self.assertIn("fields", r["params"])

    def test_paths_prioritise_api_over_static(self):
        from bundle_scan import scan_text
        js = ('a="/_next/static/chunks/x.js";b="/api/v1/users";c="/trendy";'
              'd="/assets/logo.svg";e="/wyniki-wyszukiwania?type=publication";')
        paths = scan_text("t.js", js)["paths"]
        self.assertIn("/api/v1/users", paths)
        self.assertIn("/trendy", paths)
        self.assertLess(paths.index("/api/v1/users"), paths.index("/_next/static/chunks/x.js"))

    def test_paths_capped(self):
        from bundle_scan import scan_text, MAX_PATHS
        js = "".join('x%d="/route%d/page";' % (i, i) for i in range(MAX_PATHS + 50))
        self.assertLessEqual(len(scan_text("t.js", js)["paths"]), MAX_PATHS)

    def test_hosts_capped_and_lowercase(self):
        from bundle_scan import scan_text, MAX_HOSTS
        js = "".join('u%d="https://H%d.Example.COM/a";' % (i, i) for i in range(MAX_HOSTS + 30))
        hosts = scan_text("t.js", js)["hosts"]
        self.assertLessEqual(len(hosts), MAX_HOSTS)
        self.assertTrue(all(h == h.lower() for h in hosts))

    def test_minified_concat_is_not_a_secret(self):
        """KOREKTA #45: `token="+encodeURIComponent(t)+"` to sklejenie, nie sekret."""
        from bundle_scan import scan_text
        for js in ('var u="/x?token="+encodeURIComponent(t)+"&y=1";',
                   'a={token:t.get("token")};',
                   'h.set("x-csrf-token",n);',
                   'let s="Bearer "+e+" ";'):
            self.assertEqual(scan_text("t.js", js)["secrets"], [], js)

    def test_real_literal_secret_still_caught(self):
        from bundle_scan import scan_text
        js = 'const cfg={api_key:"aK91zQ7mT4vX2pL8nR3w"};'
        r = scan_text("t.js", js)
        self.assertEqual(len(r["secrets"]), 1)
        self.assertEqual(r["secrets"][0]["kind"], "generic_assignment")
        self.assertNotIn("aK91zQ7mT4vX2pL8nR3w", json.dumps(r))

    def test_report_has_new_keys(self):
        from bundle_scan import scan_text
        r = scan_text("t.js", 'fetch("/api/x")')
        for k in ("paths", "hosts", "endpoints", "params", "secrets", "id_formats"):
            self.assertIn(k, r)


if __name__ == "__main__":
    unittest.main()
