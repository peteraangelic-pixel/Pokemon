#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testy `har_sanitize.py` — redakcja zrzutu HAR przed committem.

Kazdy test asertuje INVARIANTE, nie tylko brak wyjatku:
* zadna wartosc poswiadczenia / tresc zadania / tresc odpowiedzi nie istnieje w wyjsciu,
* ksztalt (metoda, szablon sciezki, kod, rozmiar, nazwy) zostaje,
* odciski (sha256[:8]/[:12]) sa obecne i stabilne.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import har_sanitize as hs  # noqa: E402


SECRET_JWT = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0InQ.PODPIS_1234567890abcdef"
SECRET_COOKIE = "sessionid=SESJA_TESTOWA_abcdef123456; csrftoken=CSRF_TESTOWY_987654"
SECRET_PASSWORD = "TajneHasloTestowe123!"
SECRET_EMAIL = "anna.nowak@przyklad.test"
SECRET_BODY = "odpowiedz-z-danymi-osobowymi-PESEL-90010112345-i-adresem"


def make_har(cookie=SECRET_COOKIE, auth=SECRET_JWT):
    return {
        "log": {
            "creator": {"name": "Chrome"},
            "pages": [{"id": "page_1", "title": "Panel — " + SECRET_EMAIL}],
            "entries": [
                {
                    "startedDateTime": "2026-11-05T10:00:00.000Z", "time": 120.0,
                    "request": {
                        "method": "POST", "url": "https://hack.cert.pl/api/v1/auth/login",
                        "httpVersion": "HTTP/2",
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "X-CSRF-Token", "value": "CSRF_TESTOWY_987654"},
                            {"name": "User-Agent", "value": "Mozilla/5.0 (test)"},
                        ],
                        "cookies": [{"name": "sessionid", "value": cookie}],
                        "queryString": [],
                        "postData": {"mimeType": "application/json",
                                     "text": json.dumps({"login": "tester",
                                                         "password": SECRET_PASSWORD,
                                                         "email": SECRET_EMAIL})},
                    },
                    "response": {
                        "status": 200, "statusText": "OK", "httpVersion": "HTTP/2",
                        "headers": [{"name": "Content-Type", "value": "application/json"},
                                    {"name": "Set-Cookie", "value": cookie}],
                        "cookies": [{"name": "sessionid", "value": cookie}],
                        "content": {"size": 210, "mimeType": "application/json",
                                    "text": json.dumps({"token": auth})},
                        "redirectURL": "",
                    },
                    "timings": {"send": 0, "wait": 100, "receive": 20},
                },
                {
                    "startedDateTime": "2026-11-05T10:00:05.000Z", "time": 90.0,
                    "request": {
                        "method": "GET",
                        "url": ("https://hack.cert.pl/api/v1/reports/1024/internal-notes"
                                "?token=TOKEN_W_QUERY_abcdef123456&page=2"
                                "&email=" + SECRET_EMAIL),
                        "httpVersion": "HTTP/2",
                        "headers": [{"name": "Authorization", "value": auth},
                                    {"name": "Cookie", "value": cookie},
                                    {"name": "Accept", "value": "application/json"},
                                    {"name": "X-Custom-Thing", "value": "jakas-tajemnica-xyz"}],
                        "cookies": [{"name": "sessionid", "value": cookie}],
                        "queryString": [{"name": "token", "value": "TOKEN_W_QUERY_abcdef123456"},
                                        {"name": "page", "value": "2"},
                                        {"name": "email", "value": SECRET_EMAIL}],
                    },
                    "response": {
                        "status": 403, "statusText": "Forbidden", "httpVersion": "HTTP/2",
                        "headers": [{"name": "Content-Type", "value": "application/json"},
                                    {"name": "Allow", "value": "GET, POST"}],
                        "cookies": [],
                        "content": {"size": len(SECRET_BODY), "mimeType": "application/json",
                                    "text": SECRET_BODY},
                        "redirectURL": "",
                    },
                    "timings": {"send": 0, "wait": 80, "receive": 10},
                },
            ],
        }
    }


def sanitize(har=None):
    seen = set()
    clean, rows = hs.sanitize_har(har if har is not None else make_har(), seen)
    return clean, rows, hs.build_map(rows), seen


class TestRedakcjaPoswiadczen(unittest.TestCase):
    def test_zadnego_sekretu_w_wyjsciu(self):
        clean, rows, mapa, seen = sanitize()
        blob = json.dumps(clean, ensure_ascii=False) + json.dumps(mapa, ensure_ascii=False)
        for secret in (SECRET_JWT, SECRET_COOKIE, SECRET_PASSWORD, SECRET_EMAIL,
                       "TOKEN_W_QUERY_abcdef123456", "CSRF_TESTOWY_987654",
                       SECRET_BODY, "jakas-tajemnica-xyz"):
            self.assertNotIn(secret, blob)
        self.assertGreaterEqual(len(seen), 6, "narzedzie nie zobaczylo wszystkich wrazliwych wartosci")

    def test_naglowki_zostaja_jako_nazwy(self):
        clean, rows, mapa, _ = sanitize()
        rep = [x for x in mapa["map"] if x["path_template"].endswith("internal-notes")][0]
        self.assertIn("authorization", rep["request_header_names"])
        self.assertIn("cookie", rep["request_header_names"])
        self.assertIn("x-custom-thing", rep["request_header_names"])  # nazwa tak, wartosc nie
        self.assertIn("allow", rep["response_header_names"])

    def test_bezpieczne_wartosci_naglowkow_sa_zachowane(self):
        clean, *_ = sanitize()
        e = clean["log"]["entries"][1]
        resp_vals = {h["name"].lower(): h["value"] for h in e["response"]["headers"]}
        self.assertEqual(resp_vals.get("content-type"), "application/json")
        self.assertEqual(resp_vals.get("allow"), "GET, POST")
        req_vals = {h["name"].lower(): h["value"] for h in e["request"]["headers"]}
        self.assertEqual(hs.REDACTED, req_vals.get("authorization"))
        self.assertEqual(hs.REDACTED, req_vals.get("cookie"))
        self.assertEqual(hs.REDACTED, req_vals.get("x-custom-thing"))
        self.assertEqual("application/json", req_vals.get("accept"))

    def test_tresci_zadan_i_odpowiedzi_wyzerowane(self):
        clean, *_ = sanitize()
        for e in clean["log"]["entries"]:
            self.assertIsNone(e["response"]["content"]["text"])
            pd = e["request"].get("postData") or {}
            self.assertIn(pd.get("text"), (None, ""))

    def test_nazwy_pol_zadania_zostaly(self):
        _, _, mapa, _ = sanitize()
        log = [x for x in mapa["map"] if x["path_template"].endswith("login")][0]
        self.assertIn("password", log["post_field_names"])
        self.assertIn("email", log["post_field_names"])
        self.assertIn("login", log["post_field_names"])

    def test_query_tokeny_i_pii_wyczyszczone_nazwy_zostaly(self):
        clean, _, mapa, _ = sanitize()
        e = clean["log"]["entries"][1]
        self.assertNotIn("TOKEN_W_QUERY_abcdef123456", e["request"]["url"])
        self.assertNotIn(SECRET_EMAIL, e["request"]["url"])
        self.assertIn(hs.REDACTED, e["request"]["url"])
        self.assertIn("page=2", e["request"]["url"])  # parametr nie wrazliwy zostaje
        rep = [x for x in mapa["map"] if x["path_template"].endswith("internal-notes")][0]
        self.assertEqual(["email", "page", "token"], rep["query_param_names"])

    def test_tytuly_stron_wyczyszczone(self):
        clean, *_ = sanitize()
        self.assertNotIn(SECRET_EMAIL, json.dumps(clean["log"].get("pages"), ensure_ascii=False))


class TestKsztaltIDowody(unittest.TestCase):
    def test_normalizacja_id_do_szablonu(self):
        _, _, mapa, _ = sanitize()
        tpls = {x["path_template"] for x in mapa["map"]}
        self.assertIn("/api/v1/reports/{id}/internal-notes", tpls)
        self.assertIn("/api/v1/auth/login", tpls)

    def test_odcisk_ciala_odpowiedzi(self):
        _, _, mapa, _ = sanitize()
        rep = [x for x in mapa["map"] if x["path_template"].endswith("internal-notes")][0]
        self.assertEqual(1, len(rep["response_sha256_12"]))
        self.assertEqual(12, len(rep["response_sha256_12"][0]))
        self.assertEqual(len(SECRET_BODY), rep["response_bytes_max"])

    def test_odcisk_sesji_stabilny_i_osmiobajtowy(self):
        _, _, mapa, _ = sanitize()
        self.assertEqual(1, len(mapa["sessions_detected"]))
        self.assertEqual(8, len(mapa["sessions_detected"][0]))
        # ten sam HAR drugi raz = ten sam odcisk (grupowanie kont dziala)
        _, _, mapa2, _ = sanitize()
        self.assertEqual(mapa["sessions_detected"], mapa2["sessions_detected"])

    def test_dwa_konta_dwa_odciski(self):
        har = make_har()
        har2 = make_har(cookie="sessionid=DRUGA_SESJA_ZZZ_999888777",
                        auth="Bearer DRUGI_JWT_PODPIS_qwertyuiop123456")
        seen = set()
        _, rows_a = hs.sanitize_har(har, seen)
        _, rows_b = hs.sanitize_har(har2, seen)
        mapa = hs.build_map(rows_a + rows_b)
        self.assertEqual(2, len(mapa["sessions_detected"]), mapa["sessions_detected"])

    def test_agregacja_statusow_i_licznikow(self):
        _, _, mapa, _ = sanitize()
        rep = [x for x in mapa["map"] if x["path_template"].endswith("internal-notes")][0]
        self.assertEqual({"403": 1}, rep["statuses"])
        self.assertEqual(1, rep["count"])
        self.assertEqual("hack.cert.pl", rep["host"])
        self.assertEqual(["hack.cert.pl"], mapa["hosts"])

    def test_idempotencja(self):
        clean, *_ = sanitize()
        seen2 = set()
        clean2, rows2 = hs.sanitize_har(clean, seen2)
        self.assertEqual(json.dumps(clean, sort_keys=True), json.dumps(clean2, sort_keys=True))
        self.assertEqual(0, len(seen2), "drugi przebieg nie powinien nic nowego znalezc")


class TestZapora(unittest.TestCase):
    def test_assert_clean_lapie_wyciek(self):
        with self.assertRaises(SystemExit):
            hs.assert_clean(['{"a": "' + SECRET_PASSWORD + '"}'], {SECRET_PASSWORD})

    def test_assert_clean_przepuszcza_odciski(self):
        odcisk = hs.fp(SECRET_PASSWORD, 12)
        hs.assert_clean(['{"a": "' + odcisk + '"}'], {SECRET_PASSWORD})  # bez wyjatku

    def test_krotkie_wartosci_nie_blokuja(self):
        hs.assert_clean(['{"a": "OK"}'], {"OK", ""})  # bez wyjatku (len < 4)


class TestSelftest(unittest.TestCase):
    def test_selftest_przechodzi(self):
        self.assertEqual(0, hs.selftest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
