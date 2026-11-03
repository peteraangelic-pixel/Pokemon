"""Unit tests for nask/tools/bundle_scan.py — offline, no network."""
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
        # "changeme" i "undefined" maja byc odfiltrowane allow-lista
        previews = " ".join(s["preview"] for s in r["secrets"])
        self.assertNotIn("changeme", previews)
        self.assertNotIn("undefined", previews)

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


if __name__ == "__main__":
    unittest.main()
