#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""har_sanitize.py — redakcja zrzutu HAR PRZED jakimkolwiek committem (korekta #33 rozszerzona).

Po co
-----
User ma konto na `hack.cert.pl` (i — miejmy nadzieje — dostanie konto testowe HIVE).
Regulamin (§6) pozwala uzywac WYLACZNIE wlasnych/konkurencyjnie testowych kont, a jedyny
sposob, zebym mogl zmapowac uwierzytelnione API bez poznania hasla, to zrzut HAR z jego
przegladarki. Zrzut HAR zawiera jednak:

* `Cookie:` / `Set-Cookie:` z identyfikatorem sesji,
* `Authorization: Bearer <JWT>`,
* tokeny CSRF w naglowkach i w query,
* haslo w ciele zadania logowania,
* tresci odpowiedzi (dane osobowe usera i — potencjalnie — innych osob),
* identyfikatory obiektow nalezacych do usera.

Ten plik jest zapora: czyta surowy HAR, wyrzuca WARTOSCI wrazliwe, zostawia SAM KSZTALT
(metody, szablony sciezek, kody, typy, rozmiary, odciski sha256, NAZWY naglowkow i
NAZWY pol/parametrow) oraz `session_fingerprint` = sha256[:8] poswiadczenia, dzieki
ktremu analiza asymetrii miedzy dwoma kontami (`vendor/a450b00f/har_triage.py`) dziala
bez znajomosci czegokolwiek.

Zelazne zasady (asertowane w `--selftest` i w testach jednostkowych):
1. Zadna wartosc poswiadczenia nie trafia do wyjscia — ani do zsanityzowanego HAR,
   ani do mapy API, ani na stdout.
2. Zadnego ciala odpowiedzi w wyjsciu: tylko rozmiar, mimeType i sha256[:12].
3. Zadnego ciala zadania: tylko mimeType, dlugosc i NAZWY pol (formularz/JSON).
4. Po wygenerowaniu wyjscia narzedzie SKANUJE je pod katem wszystkich wrazliwych
   wartosci zobaczonych na wejsciu; jedno trafienie = wyjatek i brak plikow.
5. Surowy HAR nigdy nie jest committowany: `.gitignore` w korzeniu repo blokuje
   `*.har` i `nask/har/raw/`, a to narzedzie domyslnie czyta wlasnie stamtad.

Uzycie
------
    python3 nask/tools/har_sanitize.py --in nask/har/raw/hack.cert.pl.har \
        --out-dir nask/har/sanitized --map-out nask/har/mapa-api.json
    python3 nask/tools/har_sanitize.py --selftest

Zero sieci. Zero zapisu poza podanymi sciezkami wyjscia.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from urllib.parse import urlsplit

SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# co jest wrazliwe
# ---------------------------------------------------------------------------

# Naglowki, ktorych WARTOSC zawsze jest wyrzucana (nazwa zostaje).
SENSITIVE_HEADERS = {
    "cookie", "set-cookie", "authorization", "proxy-authorization",
    "x-csrf-token", "csrf-token", "x-xsrf-token", "xsrf-token",
    "x-api-key", "api-key", "x-auth-token", "auth-token", "x-session-id",
    "x-access-token", "x-refresh-token", "x-amz-security-token",
    "x-recaptcha-token", "g-recaptcha-response", "x-forwarded-user",
    "x-remote-user", "x-original-url", "referer", "origin",
}

# Dodatkowo: kazdy naglowek, ktorego NAZWA zawiera jedno z tych slow.
SENSITIVE_NAME_PARTS = (
    "token", "secret", "credential", "password", "passwd", "auth", "cookie",
    "session", "apikey", "api-key", "signature", "jwt", "bearer", "otp",
    "csrf", "xsrf", "recaptcha",
)

# Naglowki, ktorych wartosc jest uzyteczna i nieszkodliwa (allow-lista).
SAFE_HEADER_VALUES = {
    "content-type", "content-length", "cache-control", "etag", "last-modified",
    "x-frame-options", "content-security-policy", "access-control-allow-origin",
    "access-control-allow-credentials", "allow", "vary", "server", "x-cache",
    "strict-transport-security", "x-content-type-options", "referrer-policy",
    "permissions-policy", "date", "expires", "pragma", "accept", "accept-language",
    "accept-encoding", "connection", "upgrade-insecure-requests", "sec-fetch-mode",
    "sec-fetch-site", "sec-fetch-dest", "dnt", "host",
}

# Parametry query, ktorych wartosc jest wyrzucana (nazwa zostaje).
SENSITIVE_QUERY = {
    "token", "access_token", "refresh_token", "id_token", "api_key", "apikey",
    "key", "secret", "session", "sessionid", "session_id", "sid", "jwt",
    "authorization", "auth", "signature", "sig", "csrf", "xsrf", "_csrf",
    "otp", "code", "password", "pass", "pwd", "g-recaptcha-response",
    "recaptcha", "preview", "previewtoken", "hash", "digest", "sign",
}

# Nazwy pol w ciele zadania, ktorych wartosc jest wyrzucana (nazwa zostaje).
SENSITIVE_FIELDS = SENSITIVE_QUERY | {
    "email", "e-mail", "login", "username", "user", "user_name", "name",
    "firstname", "lastname", "first_name", "last_name", "phone", "telephone",
    "pesel", "nip", "regon", "iban", "account", "card", "cvv", "url", "urls",
    "reason", "content", "message", "text", "body", "file", "attachment",
    "accept", "consent", "zgoda", "dane", "opis",
}

REDACTED = "<REDACTED>"

# ---------------------------------------------------------------------------
# normalizacja sciezek — preferujemy kod vendored (jedno zrodlo prawdy)
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]{12,}$")
_B64_RE = re.compile(r"^[A-Za-z0-9+/=]{24,}$")
_NUM_RE = re.compile(r"^\d{3,}$")


def _local_normalize(path: str) -> str:
    out = []
    for part in (path or "").strip("/").split("/"):
        if _UUID_RE.match(part) or _HEX_RE.match(part) or _B64_RE.match(part) or _NUM_RE.match(part):
            out.append("{id}")
        else:
            out.append(part)
    return "/" + "/".join(out)


def _vendored_normalize():
    """Import `normalize_template` z vendored har_triage.py (jesli jest)."""
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(here, "vendor", "a450b00f", "har_triage.py")
    if not os.path.exists(cand):
        return None
    try:
        spec = importlib.util.spec_from_file_location("vendored_har_triage", cand)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "normalize_template", None)
    except Exception:  # pragma: no cover — vendored kod nie moze zlamac redakcji
        return None


_VENDORED = _vendored_normalize()


def normalize_template(path: str) -> str:
    fn = _VENDORED or _local_normalize
    try:
        return fn(path)
    except Exception:
        return _local_normalize(path)


# ---------------------------------------------------------------------------
# pomocnicze
# ---------------------------------------------------------------------------

def note(seen: set, value) -> None:
    """Zapisuje wrazliwa wartosc do zbioru zobaczonych (koncowa asercja antywyciekowa).

    Ignoruje `<REDACTED>` i wartosci krotsze niz 4 znaki — dzieki temu redakcja jest
    IDEMPOTENTNA: drugi przebieg po juz zsanityzowanym HAR nie blokuje sie na wlasnych
    maskach i nie produkuje falszywego alarmu.
    """
    if value is None:
        return
    text = str(value)
    if not text or text == REDACTED or len(text) < 4:
        return
    seen.add(text)   # JEDYNE miejsce z seen.add — ta funkcja jest filtrem, nie rekursja


def fp(value: str, n: int = 8) -> str:
    """Odcisk wartosci — nigdy sama wartosc (korekta #33)."""
    if value is None:
        return ""
    return hashlib.sha256(str(value).encode("utf-8", "replace")).hexdigest()[:n]


def is_sensitive_header(name: str) -> bool:
    low = (name or "").strip().lower()
    if low in SENSITIVE_HEADERS:
        return True
    return any(part in low for part in SENSITIVE_NAME_PARTS)


def redact_headers(headers, seen: set) -> tuple[list[dict], list[str]]:
    """Zwraca ( [{name, value?}], nazwy ). Wartosci wrazliwe -> REDACTED."""
    out, names = [], []
    for h in headers or []:
        name = h.get("name", "")
        value = h.get("value", "")
        low = name.strip().lower()
        names.append(low)
        if is_sensitive_header(name):
            if value:
                note(seen, value)
            out.append({"name": name, "value": REDACTED})
        elif low in SAFE_HEADER_VALUES:
            out.append({"name": name, "value": value})
        else:
            # nieznany naglowek: zachowawczo — nazwa tak, wartosc nie
            if value:
                note(seen, value)
            out.append({"name": name, "value": REDACTED})
    return out, names


def session_fingerprint(entry: dict, seen: set) -> str:
    """sha256[:8] poswiadczenia sesji — do grupowania kont BEZ znajomosci wartosci.

    Kanoniczne zrodlo = **cookie sesji** (naglowek `Cookie` i/lub tablica `cookies`),
    bo to ono identyfikuje konto w calym przegladzie; `Authorization` jest fallbackiem
    dopiero, gdy cookie nie ma wcale. Zbior wartosci jest SORTOWANY, wiec ten sam
    przeglad daje ten sam odcisk w kazdym wpisie (inaczej login i zadanie
    uwierzytelnione wygladalyby na dwa rozne konta — blad, ktory wykryl selftest).
    """
    req = entry.get("request", {}) or {}
    cookie_values = set()
    for h in req.get("headers", []) or []:
        if (h.get("name") or "").strip().lower() == "cookie":
            val = h.get("value") or ""
            if val and val != REDACTED:
                cookie_values.add(val)
    for c in req.get("cookies", []) or []:
        val = c.get("value") or ""
        if val and val != REDACTED:
            cookie_values.add(val)
    auth_values = set()
    for h in req.get("headers", []) or []:
        if (h.get("name") or "").strip().lower() in ("authorization", "proxy-authorization"):
            val = h.get("value") or ""
            if val and val != REDACTED:
                auth_values.add(val)
    for val in sorted(cookie_values | auth_values):
        note(seen, val)
    source = cookie_values or auth_values
    if not source:
        return ""
    return fp("|".join(sorted(source)), 8)


PII_VALUE_RE = re.compile(
    r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"      # e-mail
    r"|\b\d{9,11}\b"                                          # PESEL / dlugi numer
    r"|(?:\+?48)?\s?\d{2,3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})"  # telefon PL
)


def value_has_pii(value: str) -> bool:
    """Czy wartosc parametru wyglada na dane osobowe (tylko test, nic nie zwracamy)."""
    return bool(value) and bool(PII_VALUE_RE.search(value))


def redact_url(url: str, seen: set) -> tuple[str, list[str]]:
    """Czyści query z wartosci wrazliwych; zwraca (url_z_REDACTED, nazwy_parametrow).

    Wyrzucamy wartosc, gdy (a) nazwa parametru jest na liscie wrazliwej albo
    (b) wartosc wyglada na dane osobowe (e-mail, PESEL, telefon PL). Nazwa zostaje.
    """
    if not url:
        return url, []
    sp = urlsplit(url)
    names = []
    if not sp.query:
        return url, names
    pairs = []
    for pair in sp.query.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        names.append(k)
        if v and (k.strip().lower() in SENSITIVE_QUERY or value_has_pii(v)):
            note(seen, v)
            pairs.append(k + "=" + REDACTED)
        else:
            pairs.append(pair)
    clean = sp._replace(query="&".join(pairs)).geturl()
    return clean, names


def redact_post(post: dict | None, seen: set) -> dict:
    """Ciala zadan NIE zachowujemy: tylko mimeType, dlugosc i nazwy pol."""
    if not post:
        return {}
    mime = post.get("mimeType", "")
    text = post.get("text") or ""
    if text:
        note(seen, text)
    names = []
    for p in post.get("params") or []:
        nm = p.get("name", "")
        names.append(nm)
        if p.get("value"):
            note(seen, p["value"])
    if text and ("json" in (mime or "").lower()):
        try:
            obj = json.loads(text)
            names.extend(_json_field_names(obj))
        except Exception:
            pass
    elif text and "urlencoded" in (mime or "").lower():
        for pair in text.split("&"):
            if "=" in pair:
                names.append(pair.split("=", 1)[0])
            elif pair:
                names.append(pair)
    prev_len = post.get("text_length")
    return {
        "mimeType": mime,
        # przy drugim przebiegu ciala juz nie ma — zachowujemy ZMIERZONA dlugosc z pierwszego
        "text_length": len(text) if text else (prev_len if isinstance(prev_len, int) else 0),
        "field_names": sorted(set(names)),
        "text": None,  # jawnie: zadnej tresci zadania w wyjsciu
        "params": [{"name": n, "value": REDACTED} for n in sorted(set(names))],
    }


def _json_field_names(obj, prefix: str = "", depth: int = 0) -> list[str]:
    """Nazwy pol JSON (sciezki) — bez wartosci. Glebokosc ograniczona."""
    out = []
    if depth > 4:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = (prefix + "." + k) if prefix else k
            out.append(path)
            if isinstance(v, (dict, list)):
                out.extend(_json_field_names(v, path, depth + 1))
    elif isinstance(obj, list):
        for item in obj[:1]:
            out.extend(_json_field_names(item, prefix + "[]", depth + 1))
    return out


# ---------------------------------------------------------------------------
# glowna redakcja
# ---------------------------------------------------------------------------

def sanitize_har(har: dict, seen: set) -> tuple[dict, list[dict]]:
    """Zwraca (zsanityzowany_har, wiersze_mapy)."""
    entries_in = ((har.get("log") or {}).get("entries")) or []
    entries_out, rows = [], []

    for e in entries_in:
        req = e.get("request", {}) or {}
        res = e.get("response", {}) or {}
        url = req.get("url", "")
        clean_url, query_names = redact_url(url, seen)
        sp = urlsplit(url)
        req_headers, req_header_names = redact_headers(req.get("headers"), seen)
        res_headers, res_header_names = redact_headers(res.get("headers"), seen)

        cookie_names = sorted({(c.get("name") or "") for c in (req.get("cookies") or [])})
        set_cookie_names = sorted({(c.get("name") or "") for c in (res.get("cookies") or [])})
        for c in (req.get("cookies") or []) + (res.get("cookies") or []):
            if c.get("value"):
                note(seen, c["value"])

        sess = session_fingerprint(e, seen) or (e.get("_sessionFp") or "")

        content = res.get("content", {}) or {}
        body_text = content.get("text") or ""
        body_size = content.get("size")
        if body_size in (None, 0, -1):
            body_size = len(body_text)
        # przy drugim przebiegu (po juz zsanityzowanym HAR) ciala juz nie ma —
        # zachowujemy wczesniejszy odcisk, zeby redakcja byla idempotentna
        body_sha = fp(body_text, 12) if body_text else (content.get("_sha256_12") or "")
        if body_text:
            note(seen, body_text)

        post = redact_post(req.get("postData"), seen)

        row = {
            "method": (req.get("method") or "").upper(),
            "host": sp.hostname or "",
            "path_template": normalize_template(sp.path or "/"),
            "status": res.get("status"),
            "response_mime": (content.get("mimeType") or res_header_mime(res_headers)),
            "response_bytes": body_size,
            "response_sha256_12": body_sha,
            "request_header_names": sorted(set(req_header_names)),
            "response_header_names": sorted(set(res_header_names)),
            "cookie_names": cookie_names,
            "set_cookie_names": set_cookie_names,
            "query_param_names": sorted(set(query_names)),
            "post_field_names": post.get("field_names", []),
            "session_fingerprint": sess,
            "started": e.get("startedDateTime", ""),
            "time_ms": e.get("time"),
        }
        rows.append(row)

        entries_out.append({
            "_sanitized": True,
            "_sessionFp": sess,
            "startedDateTime": e.get("startedDateTime", ""),
            "time": e.get("time"),
            "request": {
                "method": row["method"],
                "url": clean_url,
                "httpVersion": req.get("httpVersion", ""),
                "headers": req_headers,
                "queryString": [{"name": n, "value": REDACTED if n.strip().lower() in SENSITIVE_QUERY else ""}
                                for n in query_names],
                "cookies": [{"name": n, "value": REDACTED} for n in cookie_names],
                "headersSize": req.get("headersSize"),
                "bodySize": req.get("bodySize"),
                "postData": post,
            },
            "response": {
                "status": res.get("status"),
                "statusText": res.get("statusText", ""),
                "httpVersion": res.get("httpVersion", ""),
                "headers": res_headers,
                "cookies": [{"name": n, "value": REDACTED} for n in set_cookie_names],
                "content": {
                    "size": body_size,
                    "mimeType": content.get("mimeType", ""),
                    "text": None,          # ZADNYCH tresci odpowiedzi w repo
                    "_sha256_12": body_sha,
                },
                "redirectURL": redact_url(res.get("redirectURL", ""), seen)[0],
                "headersSize": res.get("headersSize"),
                "bodySize": res.get("bodySize"),
            },
            "cache": {},
            "timings": e.get("timings", {}),
        })

    log = dict(har.get("log") or {})
    log["entries"] = entries_out
    log["_sanitized"] = {
        "schema_version": SCHEMA_VERSION,
        "entries": len(entries_out),
        "note": ("Wartosci poswiadczen, tresci zadan i tresci odpowiedzi usuniete; "
                 "zostaly nazwy, rozmiary, kody i odciski sha256. session_fingerprint = "
                 "sha256[:8] poswiadczenia — sluzy WYLACZNIE do grupowania kont."),
    }
    for k in ("creator", "browser", "pages"):
        if k in log:
            # `pages` moze zawierac tytuly z danymi; zostawiamy same nazwy pol
            log[k] = log[k] if k != "pages" else [{"title": REDACTED, "id": p.get("id", "")}
                                                  for p in (log[k] or [])]
    return {"log": log}, rows


def res_header_mime(headers) -> str:
    for h in headers or []:
        if (h.get("name") or "").strip().lower() == "content-type":
            return h.get("value", "")
    return ""


def build_map(rows: list[dict]) -> dict:
    """Zagęszcza wiersze do mapy endpointow (to jest wejscie do analizy IDOR)."""
    per: dict[tuple, dict] = {}
    for r in rows:
        key = (r["host"], r["method"], r["path_template"])
        agg = per.setdefault(key, {
            "host": r["host"], "method": r["method"], "path_template": r["path_template"],
            "statuses": {}, "count": 0, "response_bytes": [], "sessions": set(),
            "response_sha256_12": set(), "query_param_names": set(),
            "post_field_names": set(), "request_header_names": set(),
            "response_header_names": set(), "cookie_names": set(),
            "response_mime": set(),
        })
        agg["count"] += 1
        agg["statuses"][str(r["status"])] = agg["statuses"].get(str(r["status"]), 0) + 1
        if r["response_bytes"]:
            agg["response_bytes"].append(r["response_bytes"])
        if r["session_fingerprint"]:
            agg["sessions"].add(r["session_fingerprint"])
        if r["response_sha256_12"]:
            agg["response_sha256_12"].add(r["response_sha256_12"])
        for k in ("query_param_names", "post_field_names", "request_header_names",
                  "response_header_names", "cookie_names"):
            agg[k].update(r[k] or [])
        if r["response_mime"]:
            agg["response_mime"].add(r["response_mime"])

    endpoints = []
    for agg in sorted(per.values(), key=lambda a: (a["host"], a["method"], a["path_template"])):
        endpoints.append({
            "host": agg["host"], "method": agg["method"], "path_template": agg["path_template"],
            "count": agg["count"], "statuses": agg["statuses"],
            "response_bytes_min": min(agg["response_bytes"]) if agg["response_bytes"] else None,
            "response_bytes_max": max(agg["response_bytes"]) if agg["response_bytes"] else None,
            "sessions_seen": sorted(agg["sessions"]),
            "response_sha256_12": sorted(agg["response_sha256_12"]),
            "response_mime": sorted(agg["response_mime"]),
            "query_param_names": sorted(agg["query_param_names"]),
            "post_field_names": sorted(agg["post_field_names"]),
            "request_header_names": sorted(agg["request_header_names"]),
            "response_header_names": sorted(agg["response_header_names"]),
            "cookie_names": sorted(agg["cookie_names"]),
        })
    hosts = sorted({r["host"] for r in rows if r["host"]})
    sessions = sorted({r["session_fingerprint"] for r in rows if r["session_fingerprint"]})
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": len(rows),
        "hosts": hosts,
        "endpoints": len(endpoints),
        "sessions_detected": sessions,
        "map": endpoints,
        "note": ("Zageszczona mapa API z zsanityzowanego HAR. `sessions_detected` = odciski "
                 "poswiadczen (sha256[:8]), nie wartosci. Analiza asymetrii uprawnien: "
                 "`vendor/a450b00f/har_triage.py` (wspolny dostep do wspolnego zasobu NIE jest "
                 "IDOR-em samym w sobie)."),
    }


def assert_clean(outputs: list[str], seen: set) -> None:
    """Zelazna invarianta: zadna wrazliwa wartosc z wejscia nie istnieje w wyjsciu."""
    blob = "\n".join(outputs)
    leaks = []
    for v in seen:
        if not v or len(str(v)) < 4:
            continue
        if str(v) in blob:
            leaks.append(fp(v, 12))
    if leaks:
        raise SystemExit("PRZERWANO: wartosci wrazliwe w wyjsciu (odciski): %s" % ", ".join(sorted(leaks)))


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

SELFTEST_SECRETS = [
    "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXIifQ.PODPIS_TESTOWY_1234567890",
    "sessionid=abc123TESTSESSIONVALUE; csrftoken=xyz987TESTCSRFVALUE",
    "SuperTajneHaslo123!",
    "jan.kowalski@przyklad.test",
    "tajny-token-w-query-9876543210",
    "tresc-odpowiedzi-z-danymi-osobowymi-PESEL-90010112345",
]


def selftest_har() -> dict:
    return {
        "log": {
            "creator": {"name": "test"},
            "pages": [{"id": "page_1", "title": "Panel - Moje zgloszenia - jan.kowalski@przyklad.test"}],
            "entries": [
                {
                    "startedDateTime": "2026-11-05T10:00:00.000Z", "time": 120.0,
                    "request": {
                        "method": "POST", "url": "https://hack.cert.pl/api/v1/auth/login",
                        "httpVersion": "HTTP/2",
                        "headers": [{"name": "Content-Type", "value": "application/json"},
                                    {"name": "X-CSRF-Token", "value": SELFTEST_SECRETS[1]}],
                        "cookies": [{"name": "sessionid", "value": SELFTEST_SECRETS[1]}],
                        "queryString": [],
                        "postData": {"mimeType": "application/json",
                                     "text": json.dumps({"login": "tester", "password": SELFTEST_SECRETS[2]})},
                    },
                    "response": {
                        "status": 200, "statusText": "OK", "httpVersion": "HTTP/2",
                        "headers": [{"name": "Content-Type", "value": "application/json"},
                                    {"name": "Set-Cookie", "value": SELFTEST_SECRETS[1]}],
                        "cookies": [{"name": "sessionid", "value": SELFTEST_SECRETS[1]}],
                        "content": {"size": 210, "mimeType": "application/json",
                                    "text": json.dumps({"token": SELFTEST_SECRETS[0]})},
                        "redirectURL": "",
                    },
                    "timings": {"send": 0, "wait": 100, "receive": 20},
                },
                {
                    "startedDateTime": "2026-11-05T10:00:05.000Z", "time": 90.0,
                    "request": {
                        "method": "GET",
                        "url": ("https://hack.cert.pl/api/v1/reports/1024/internal-notes?token="
                                + SELFTEST_SECRETS[4] + "&page=1"),
                        "httpVersion": "HTTP/2",
                        "headers": [{"name": "Authorization", "value": SELFTEST_SECRETS[0]},
                                    {"name": "Cookie", "value": SELFTEST_SECRETS[1]},
                                    {"name": "Accept", "value": "application/json"}],
                        "cookies": [{"name": "sessionid", "value": SELFTEST_SECRETS[1]}],
                        "queryString": [{"name": "token", "value": SELFTEST_SECRETS[4]},
                                        {"name": "page", "value": "1"}],
                    },
                    "response": {
                        "status": 200, "statusText": "OK", "httpVersion": "HTTP/2",
                        "headers": [{"name": "Content-Type", "value": "application/json"}],
                        "cookies": [],
                        "content": {"size": len(SELFTEST_SECRETS[5]), "mimeType": "application/json",
                                    "text": SELFTEST_SECRETS[5]},
                        "redirectURL": "",
                    },
                    "timings": {"send": 0, "wait": 80, "receive": 10},
                },
            ],
        }
    }


def selftest() -> int:
    seen: set = set()
    har, rows = sanitize_har(selftest_har(), seen)
    mapa = build_map(rows)
    out_blob = json.dumps(har, ensure_ascii=False) + json.dumps(mapa, ensure_ascii=False)

    # 1) zadnego sekretu w wyjsciu
    for s in SELFTEST_SECRETS:
        assert s not in out_blob, "sekret w wyjsciu: " + fp(s, 12)
    # 2) zadnych tresci odpowiedzi i zadania
    for e in har["log"]["entries"]:
        assert e["response"]["content"]["text"] is None
        assert (e["request"].get("postData") or {}).get("text") in (None, "")
    # 3) ksztalt zostal: metody, szablony, kody, nazwy
    eps = {(x["host"], x["method"], x["path_template"]) for x in mapa["map"]}
    assert ("hack.cert.pl", "GET", "/api/v1/reports/{id}/internal-notes") in eps, eps
    assert ("hack.cert.pl", "POST", "/api/v1/auth/login") in eps, eps
    # 4) nazwy pol i parametrow zostaly, wartosci nie
    rep = [x for x in mapa["map"] if x["path_template"].endswith("internal-notes")][0]
    assert "token" in rep["query_param_names"]
    assert SELFTEST_SECRETS[4] not in json.dumps(rep, ensure_ascii=False)
    log = [x for x in mapa["map"] if x["path_template"].endswith("login")][0]
    assert "password" in log["post_field_names"], log["post_field_names"]
    assert SELFTEST_SECRETS[2] not in json.dumps(log, ensure_ascii=False)
    # 5) odcisk sesji istnieje i jest stabilny (grupowanie kont)
    assert len(mapa["sessions_detected"]) == 1, mapa["sessions_detected"]
    assert all(len(s) == 8 for s in mapa["sessions_detected"])
    # 6) invarianta antywyciekowa dziala na prawdziwym wyjsciu
    assert_clean([out_blob], seen)
    # 7) odcisk ciala odpowiedzi (sha256[:12]) jest — dowod bez tresci
    assert all(len(x) == 12 for e in mapa["map"] for x in e["response_sha256_12"])
    print("selftest: OK (7 grup, sekrety=%d, endpointy=%d)" % (len(SELFTEST_SECRETS), len(mapa["map"])))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Redakcja zrzutu HAR przed committem")
    ap.add_argument("--in", dest="inp", help="surowy HAR (domyslnie poza repo: nask/har/raw/)")
    ap.add_argument("--out-dir", default="nask/har/sanitized", help="katalog na zsanityzowany HAR")
    ap.add_argument("--map-out", default="nask/har/mapa-api.json", help="sciezka mapy API (JSON)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.inp:
        ap.error("--in jest wymagane (albo --selftest)")
    if not os.path.exists(args.inp):
        raise SystemExit("brak pliku: %s" % args.inp)

    with open(args.inp, encoding="utf-8", errors="replace") as fh:
        har = json.load(fh)

    seen: set = set()
    clean, rows = sanitize_har(har, seen)
    mapa = build_map(rows)

    blob = json.dumps(clean, ensure_ascii=False) + json.dumps(mapa, ensure_ascii=False)
    assert_clean([blob], seen)   # przed zapisem czegokolwiek

    os.makedirs(args.out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.inp))[0]
    out_har = os.path.join(args.out_dir, base + ".sanitized.har")
    with open(out_har, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(clean, ensure_ascii=False, indent=1) + "\n")
    os.makedirs(os.path.dirname(args.map_out) or ".", exist_ok=True)
    with open(args.map_out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(mapa, ensure_ascii=False, indent=1) + "\n")

    print("wpisow: %d | hosty: %s | endpointy: %d | sesje(odciski): %s"
          % (mapa["entries"], ", ".join(mapa["hosts"]) or "-", mapa["endpoints"],
             ", ".join(mapa["sessions_detected"]) or "-"))
    print("wrazliwych wartosci zobaczonych i wyrzuconych: %d (nie zapisano zadnej)" % len(seen))
    print("zsanityzowany HAR: %s" % out_har)
    print("mapa API:          %s" % args.map_out)
    print("SUROWY HAR (%s) zostaje poza git — .gitignore blokuje *.har" % args.inp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
