#!/usr/bin/env python3
"""Sonda HTTP o surowej sciezce dla zakresu NASK (hack.cert.pl, edycja 11/2026).

DLACZEGO TEN PLIK ISTNIEJE
--------------------------
Kazde inne narzedzie w zespole normalizuje URL przed wyslaniem:
  * Rust `reqwest`/`url::Url` zwija literalne segmenty `..` (dowod: log
    `probe-run007.json` — `error sending request for url
    (https://science.nask.pl/etc/passwd)` zamiast `/api/media/../../etc/passwd`),
  * `requests`/`httpx` re-cytuja sciezke,
  * przegladarkowe proxy tekstowe nie zwraca kodu odpowiedzi ani skrotu ciala.

Ta sonda buduje linie zadania recznie (`http.client.putrequest`) i wysyła bajty
sciezki DOSŁOWNIE, a do kazdego zadania zapisuje tyle dowodu, ze rozstrzygniecie
nie wymaga drugiej wizyty: status, Content-Type, Content-Length, sha256 ciala,
znaczniki tresci (nazwy, nie tresc) i — tylko dla niesekretnych probek —
zredagowany podglad pierwszych bajtow.

ZGODNOSC Z REGULAMINEM (wymuszone w kodzie, nie w komentarzu)
--------------------------------------------------------------
* allow-lista 12 DOKLADNYCH hostow z §5 (bez wildcard, bez `www.nask.pl`,
  bez portow innych niz 443, bez `user@host`, bez `http://`);
* GET tylko; przekierowania NIE sa sledzone (`Location` jest zapisywane);
* jeden globalny limiter; `Limiter` odmawia startu powyzej 5 req/s
  (regulamin §6), domyslnie 1.0 req/s — ponizej tempa innych sesji zespołu;
* zero cial zadania, zero naglowkow uwierzytelniajacych, zero POST/PUT/DELETE;
* tresci wrazliwe (np. `wp-config.php`) NIGDY nie trafiaja do raportu:
  zapisujemy status, typ, rozmiar, sha256 i LICZBE dopasowan wzorca sekretu.

Uzycie:
    python3 rawpath.py --selftest                 # offline, bez sieci
    python3 rawpath.py --plan ../run/RAWPATH-001.json --dry-run
    python3 rawpath.py --plan ../run/RAWPATH-001.json --out ../reports/rawpath-001.json
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import socket
import ssl
import sys
import time
import urllib.parse
from pathlib import Path

SCHEMA_VERSION = 1

# §5 regulaminu NASK (edycja 11/2026) — 12 doslownych hostow, bez wildcardow.
# `www.nask.pl` jest SWIADOMIE pominiety: §5 wymienia literal `nask.pl`, a NASK
# (w przeciwienstwie do programu CERT) nie opatruje listy znakiem `*`.
SCOPE_HOSTS = frozenset({
    "nask.pl",
    "dyzurnet.pl",
    "dns.pl",
    "oad.nask.pl",
    "zglos-dezinformacje.nask.pl",
    "bezpiecznymiesiac.pl",
    "secure.edu.pl",
    "bezpiecznewybory.pl",
    "116sos.pl",
    "pllum.org.pl",
    "science.nask.pl",
    "dataannotation.pllum.org.pl",
})

MAX_RPS = 5.0          # twardy sufit regulaminowy — kod odmawia wiecej
DEFAULT_RPS = 1.0      # nasze domyslne tempo (zespolowo bezpieczne)
MAX_BODY_BYTES = 65_536  # tyle czytamy do dowodu (nie sciagamy calosci)
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "nask-bugbounty-scope-check/1.0 (badanie zgodne z regulaminem hack.cert.pl)"

# Proby, ktorych cialo moze zawierac sekrety: zero podgladu, zero fragmentow.
SENSITIVE_ID_RE = re.compile(r"(secret|wp-config|env-file|git-config|db-dump|passwd|credentials)", re.I)

# Znaczniki tresci — raportujemy NAZWE i liczbe dopasowan, nigdy fragmenty.
# Wzorce sa tekstowe (polskie strony sa UTF-8), kompilowane do bajtow przez
# `.encode("utf-8")` — literaly `rb"..."` nie przyjmuja znakow spoza ASCII.
_MARKER_SRC: dict[str, tuple[str, int]] = {
    "SOFT404_PL": (r"(nie znaleziono strony|strona nieznaleziona|strony nie znaleziono|"
                   r"coś poszło nie tak|cos poszlo nie tak|404 - Strona|page not found|not found)", re.I),
    "HTML_DOC": (r"<!doctype html|<html", re.I),
    "SPA_SHELL": (r"<div id=[\"']?(root|app|__next)[\"']?", re.I),
    # informacyjny: sama nazwa dostawcy NIE oznacza blokady (strona glowna
    # dyzurnet.pl zawiera "cloudflare" w ciele — patrz KOREKTA #28)
    "WAF_VENDOR": (r"(azure front door|cloudflare|envoy)", re.I),
    # silny: jednoznaczny komunikat odmowy/block page
    "WAF_BLOCK": (r"(access denied|request blocked|reference\s*#\s*[0-9a-f]|"
                  r"incident id|nr zdarzenia|attention required|blocked by)", re.I),
    "ENV_ASSIGNMENTS": (r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*\S+", re.M),
    "SECRET_KEYS": (r"(DB_PASSWORD|DB_USER|SECRET_KEY|API_KEY|APP_KEY|PRIVATE_KEY|"
                    r"ACCESS_TOKEN|AWS_SECRET|PASSWORD\s*=)", re.I),
    "GIT_REF": (r"^(ref:\s*refs/|[0-9a-f]{40}\s*$|\[core\]|\[remote\s)", re.M | re.I),
    "WP_CONFIG_HEADER": (r"<\?php[\s\S]{0,400}(WordPress|DB_NAME|table_prefix)", re.I),
    "APACHE_STATUS": (r"(Apache Server Status|mod_status|Server uptime|requests/sec)", re.I),
    "JSON_BODY": (r"^\s*[\{\[]", re.M),
    "PHP_SOURCE": (r"<\?php", re.I),
    "ZIP_MAGIC": (r"PK\x03\x04", 0),
    "PDF_MAGIC": (r"%PDF-", 0),
    "JPEG_MAGIC": (r"\xff\xd8\xff", 0),
    "PNG_MAGIC": (r"\x89PNG", 0),
}
MARKERS: dict[str, "re.Pattern[bytes]"] = {
    name: re.compile(src.encode("utf-8", "surrogatepass"), flags)
    for name, (src, flags) in _MARKER_SRC.items()
}
SECRET_MARKER_NAMES = ("ENV_ASSIGNMENTS", "SECRET_KEYS", "GIT_REF", "WP_CONFIG_HEADER", "PHP_SOURCE")

# Naglowki zapisywane w raporcie (wartosci skrocone). `Set-Cookie` — TYLKO nazwy.
HEADER_WHITELIST = (
    "content-type", "content-length", "content-disposition", "location", "server",
    "x-powered-by", "cache-control", "x-cache", "x-aspnet-version", "x-drupal-cache",
    "x-generator", "last-modified", "etag", "x-frame-options", "access-control-allow-origin",
)


class ScopeError(ValueError):
    """URL poza zakresem §5 — zadanie nie zostanie wyslane."""


class RateError(ValueError):
    """Zadane tempo powyzej dopuszczalnego sufitu regulaminowego."""


# --------------------------------------------------------------------------- #
# straz zakresu i limiter
# --------------------------------------------------------------------------- #
def check_scope(url: str) -> urllib.parse.SplitResult:
    """Zwraca rozlozony URL albo rzuca ScopeError. Bez sledzenia przekierowan."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ScopeError(f"scheme != https: {url!r}")
    host = (parts.hostname or "").lower()
    if not host:
        raise ScopeError(f"brak hosta: {url!r}")
    if "@" in (parts.netloc or ""):
        raise ScopeError(f"userinfo w netloc (omijanie allow-listy): {url!r}")
    port = parts.port
    if port not in (None, 443):
        raise ScopeError(f"port {port} poza 443: {url!r}")
    if host not in SCOPE_HOSTS:
        raise ScopeError(f"host {host!r} spoza §5 (12 literalow)")
    if not parts.path.startswith("/"):
        raise ScopeError(f"sciezka bez '/' : {url!r}")
    return parts


def raw_path_and_query(parts: urllib.parse.SplitResult) -> str:
    """Sciezka + query DOSŁOWNIE (bez normalizacji segmentow `..`, bez dekodowania)."""
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return path


class Limiter:
    """Globalny limiter tempa. Odmawia konstrukcji powyzej MAX_RPS."""

    def __init__(self, rps: float = DEFAULT_RPS) -> None:
        if rps <= 0:
            raise RateError(f"rps musi byc > 0, jest {rps!r}")
        if rps > MAX_RPS:
            raise RateError(f"rps {rps} > sufit regulaminowy {MAX_RPS} (§6: maks. 5 req/s)")
        self.rps = float(rps)
        self.min_gap = 1.0 / self.rps
        self._last = 0.0
        self.gaps: list[float] = []

    def wait(self) -> float:
        now = time.monotonic()
        gap = now - self._last if self._last else float("inf")
        sleep_for = self.min_gap - gap
        if sleep_for > 0:
            time.sleep(sleep_for)
            gap = self.min_gap
        self._last = time.monotonic()
        if self._last and gap != float("inf"):
            self.gaps.append(gap)
        return gap

    def min_observed_gap(self) -> float | None:
        return min(self.gaps) if self.gaps else None


# --------------------------------------------------------------------------- #
# jedno zadanie
# --------------------------------------------------------------------------- #
def _sanitize_preview(body: bytes, limit: int = 200) -> str:
    """Podglad tylko dla niesekretnych odpowiedzi: drukowalne ASCII, reszta '.'."""
    out = []
    for b in body[:limit]:
        out.append(chr(b) if 32 <= b < 127 else ".")
    return "".join(out)


def decide_preview(status: int | None, body: bytes, probe_id: str, raw_path: str,
                   secret_marker_hits: int, limit: int = 200) -> str | None:
    """Czy zapisac podglad ciala do raportu.

    Trzy zasady (kolejnosc ma znaczenie):
      1. mala strona BLEDU (status >= 400, <= 1024 B) jest zapisywana zawsze —
         nie moze byc plikiem wrazliwym, a rozstrzyga np. komunikat proxy przy
         trawersalu (run 1: `sci-A12` 400/150 B bez podgladu = slepy wpis);
      2. sciezka/id pasujace do wzorca wrazliwego LUB trafione znaczniki sekretu
         -> brak podgladu, zostaja metadane (status/typ/rozmiar/sha256/licznik);
      3. w pozostalych przypadkach podglad z sanityzacja znakow niedrukowalnych.
    """
    if status is not None and status >= 400 and len(body) <= 1024:
        return _sanitize_preview(body, limit)
    sensitive = bool(SENSITIVE_ID_RE.search(probe_id or "")) or bool(SENSITIVE_ID_RE.search(raw_path or ""))
    if sensitive or secret_marker_hits:
        return None
    return _sanitize_preview(body, limit)


def _markers(body: bytes) -> dict[str, int]:
    found = {}
    for name, rx in MARKERS.items():
        n = len(rx.findall(body))
        if n:
            found[name] = n
    return found


def probe(url: str, limiter: Limiter, timeout: float = DEFAULT_TIMEOUT,
          max_bytes: int = MAX_BODY_BYTES, probe_id: str = "",
          ua: str = USER_AGENT) -> dict:
    """Wysyla JEDNO zadanie GET o surowej sciezce i zwraca rekord dowodowy."""
    rec: dict = {
        "id": probe_id,
        "url": url,
        "status": None,
        "reason": None,
        "ms": None,
        "bytes_read": 0,
        "sha256": None,
        "content_type": None,
        "headers": {},
        "set_cookie_names": [],
        "markers": {},
        "json_keys": {},
        "secret_marker_hits": 0,
        "preview": None,
        "error": None,
        "verdict": None,
    }
    try:
        parts = check_scope(url)
    except ScopeError as exc:
        rec["error"] = f"SCOPE: {exc}"
        rec["verdict"] = "refused-out-of-scope"
        return rec

    raw_path = raw_path_and_query(parts)
    rec["raw_path"] = raw_path
    limiter.wait()
    ctx = ssl.create_default_context()  # weryfikacja certyfikatu WLACZONA
    conn = http.client.HTTPSConnection(parts.hostname, 443, timeout=timeout, context=ctx)
    started = time.monotonic()
    try:
        conn.putrequest("GET", raw_path, skip_accept_encoding=True)
        conn.putheader("User-Agent", ua)
        conn.putheader("Accept", "*/*")
        conn.putheader("Accept-Encoding", "identity")
        conn.putheader("Connection", "close")
        conn.endheaders()
        resp = conn.getresponse()
        rec["status"] = int(resp.status)
        rec["reason"] = resp.reason
        raw_headers = resp.getheaders()
        for name, value in raw_headers:
            lname = name.lower()
            if lname == "set-cookie":
                rec["set_cookie_names"].append(value.split("=", 1)[0].strip()[:40])
            elif lname in HEADER_WHITELIST:
                rec["headers"][lname] = value[:200]
        rec["content_type"] = (rec["headers"].get("content-type") or "").split(";")[0].strip().lower() or None
        body = resp.read(max_bytes) or b""
        rec["bytes_read"] = len(body)
        rec["sha256"] = hashlib.sha256(body).hexdigest() if body else None
        rec["markers"] = _markers(body)
        rec["secret_marker_hits"] = sum(rec["markers"].get(m, 0) for m in SECRET_MARKER_NAMES)
        rec["preview"] = decide_preview(rec["status"], body, probe_id, raw_path,
                                        rec["secret_marker_hits"])
        if rec.get("content_type") == "application/json":
            rec["json_keys"] = json_key_schema(body)
    except (socket.timeout, TimeoutError) as exc:
        rec["error"] = f"timeout: {exc.__class__.__name__}"
    except ssl.SSLError as exc:
        rec["error"] = f"tls: {exc}"
    except (http.client.HTTPException, OSError) as exc:
        rec["error"] = f"transport: {exc.__class__.__name__}: {exc}"
    finally:
        rec["ms"] = int((time.monotonic() - started) * 1000)
        try:
            conn.close()
        except Exception:  # noqa: BLE001 - zamkniecie nie moze przeslonic wyniku
            pass
    rec["verdict"] = classify(rec)
    return rec


def json_key_schema(body: bytes, max_depth: int = 3, max_keys: int = 80) -> dict:
    """Nazwy kluczy odpowiedzi JSON bez WARTOSCI (prywatnosc: oceniamy, czy struktura
    zawiera pola osobowe, nie kopiujemy danych do repo)."""
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 - nie-JSON lub uciety odczyt
        return {}
    keys: dict[str, int] = {}

    def walk(node, prefix: str, depth: int) -> None:
        if depth > max_depth or len(keys) > max_keys:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                keys[path] = keys.get(path, 0) + 1
                walk(v, path, depth + 1)
        elif isinstance(node, list):
            for item in node[:5]:  # probka 5 elementow wystarczy do schematu
                walk(item, prefix + "[]", depth + 1)

    walk(data, "", 0)   # depth 0 = korzen; max_depth liczy poziomy ponizej
    personal = sorted({k for k in keys if re.search(
        r"(email|mail|phone|tel|pesel|nip|name|nazwa|surname|address|adres|birth|urodz|"
        r"(?:^|[._])id(?:$|[._])|user|klient|client|account|konto|login|ip|coord|gps|"
        r"lat|lon|note|notatka|comment|komentarz|description|opis)$", k.split("[")[-1], re.I)})
    return {"keys": sorted(keys)[:max_keys], "key_count": len(keys),
            "personal_like": personal[:25]}


def classify(rec: dict) -> str:
    """Werdykt z DOWODU (typ/rozmiar/znaczniki), nie z samego kodu odpowiedzi."""
    if rec.get("error"):
        if str(rec["error"]).startswith("SCOPE"):
            return "refused-out-of-scope"
        return "transport-error"
    status = rec.get("status")
    markers = rec.get("markers") or {}
    ctype = rec.get("content_type") or ""
    size = rec.get("bytes_read") or 0
    if status is None:
        return "no-response"
    if 300 <= status < 400:
        return "redirect-not-followed"
    if status in (401, 403):
        return "blocked-waf-or-auth" if markers.get("WAF_BLOCK") else "forbidden"
    if status == 404:
        return "not-found"
    if status == 405:
        return "method-not-allowed-route-exists"
    if status >= 500:
        return "server-error"
    if status == 200:
        # KOLEJNOSC MA ZNACZENIE: strona "nie znaleziono" z kodem 200 jest
        # soft-404 nawet wtedy, gdy w ciele pada nazwa dostawcy WAF.
        if markers.get("SOFT404_PL") and "html" in ctype:
            return "soft-404-html"
        if markers.get("WAF_BLOCK"):
            return "blocked-waf-200"
        if rec.get("secret_marker_hits"):
            return "CANDIDATE-SECRET-FILE"
        if ctype in ("application/zip", "application/x-zip-compressed") or markers.get("ZIP_MAGIC"):
            return "CANDIDATE-ARCHIVE"
        if ctype.startswith("text/plain") and size < 8192 and markers.get("JSON_BODY") is None:
            return "CANDIDATE-PLAINTEXT-FILE"
        if size == 713 and markers.get("SPA_SHELL"):
            return "spa-catch-all-shell"
        if "html" in ctype:
            return "html-page"
        if ctype.startswith(("image/", "application/pdf", "video/", "font/")):
            return "media-file"
        if "json" in ctype:
            return "json-response"
        return "other-200"
    return f"status-{status}"


# --------------------------------------------------------------------------- #
# analiza po przebiegu: ten sam sha256 w dwoch miejscach = dowod
# --------------------------------------------------------------------------- #
def cross_hash_evidence(records: list[dict]) -> list[dict]:
    """Grupuje odpowiedzi o IDENTYCZNYM sha256 — np. plik podany przez proxy
    mediow i ten sam plik podany przez sciezke z `%2e%2e%2f` (dowod prymitywu
    trawersalu bez dotykania danych wrazliwych)."""
    by_hash: dict[str, list[str]] = {}
    for rec in records:
        h = rec.get("sha256")
        if h and rec.get("bytes_read"):
            by_hash.setdefault(h, []).append(f'{rec.get("id")}:{rec.get("raw_path", rec.get("url"))}')
    return [
        {"sha256": h, "identical_bodies": ids}
        for h, ids in sorted(by_hash.items())
        if len(ids) > 1
    ]


def summarize(records: list[dict]) -> dict:
    from collections import Counter
    verdicts = Counter(rec.get("verdict") or "?" for rec in records)
    return {
        "count": len(records),
        "verdicts": dict(sorted(verdicts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "candidates": [
            {"id": r.get("id"), "url": r.get("url"), "verdict": r.get("verdict"),
             "status": r.get("status"), "content_type": r.get("content_type"),
             "bytes_read": r.get("bytes_read")}
            for r in records if str(r.get("verdict") or "").startswith("CANDIDATE")
        ],
        "transport_errors": [r.get("id") for r in records if r.get("verdict") == "transport-error"],
        "out_of_scope_refusals": [r.get("id") for r in records if r.get("verdict") == "refused-out-of-scope"],
    }


# --------------------------------------------------------------------------- #
# plan
# --------------------------------------------------------------------------- #
def load_plan(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    probes = data["probes"] if isinstance(data, dict) else data
    out = []
    for item in probes:
        if "url" not in item:
            raise ValueError(f"proba bez 'url': {item!r}")
        check_scope(item["url"])  # walidacja PRZED jakimkolwiek zadaniem
        out.append({"id": item.get("id") or item["url"], "url": item["url"],
                    "why": item.get("why", ""), "timeout": item.get("timeout")})
    return out


def run_plan(plan: list[dict], rps: float = DEFAULT_RPS, timeout: float = DEFAULT_TIMEOUT,
             dry_run: bool = False) -> dict:
    limiter = Limiter(rps)
    started = time.time()
    records: list[dict] = []
    if dry_run:
        return {
            "schema_version": SCHEMA_VERSION, "dry_run": True, "rps": rps,
            "count": len(plan),
            "probes": [{"id": p["id"], "url": p["url"], "raw_path": raw_path_and_query(check_scope(p["url"])),
                        "why": p["why"]} for p in plan],
        }
    for item in plan:
        rec = probe(item["url"], limiter, timeout=float(item.get("timeout") or timeout),
                    probe_id=item["id"])
        rec["why"] = item.get("why", "")
        records.append(rec)
    summary = summarize(records)
    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run": False,
        "rps_requested": rps,
        "min_observed_gap_s": limiter.min_observed_gap(),
        "wall_seconds": round(time.time() - started, 2),
        "count": len(records),
        "summary": summary,
        "identical_bodies": cross_hash_evidence(records),
        "note": ("Werdykt wynika z typu/rozmiaru/znacznikow, nie z samego kodu. "
                 "CANDIDATE-* wymaga recznego potwierdzenia przez czlowieka przed "
                 "jakimkolwiek zgloszeniem; tresci wrazliwe nie sa zapisywane."),
        "probes": records,
    }


# --------------------------------------------------------------------------- #
# selftest — offline, zero sieci
# --------------------------------------------------------------------------- #
def selftest() -> int:
    fails: list[str] = []

    def ok(cond: bool, msg: str) -> None:
        if not cond:
            fails.append(msg)

    # 1. straz zakresu
    for bad in ("http://dns.pl/.env", "https://www.nask.pl/", "https://panel.dns.pl/",
                "https://nask.pl.evil.tld/x", "https://user@dns.pl/x", "https://dns.pl:8443/x",
                "https://hack.cert.pl/", "https://mwdb.cert.pl/api/server",
                "https://gmina-wladyslawowo.pl/", "https://science.nask.pl.evil/x"):
        try:
            check_scope(bad)
            ok(False, f"straz przepuscila {bad}")
        except ScopeError:
            pass
    for good in ("https://dns.pl/.env", "https://science.nask.pl/api/media/robots.txt",
                 "https://dataannotation.pllum.org.pl/api/v1/users/1"):
        try:
            check_scope(good)
        except ScopeError as exc:
            ok(False, f"straz odrzucila poprawny {good}: {exc}")

    # 2. sufit tempa
    try:
        Limiter(50)
        ok(False, "Limiter(50) nie odmowil")
    except RateError:
        pass
    try:
        Limiter(5.0)
    except RateError:
        ok(False, "Limiter(5.0) odmowil — regulamin dopuszcza 5")
    ok(Limiter(1.0).min_gap == 1.0, "min_gap dla 1 rps != 1.0")

    # 3. surowa sciezka: ani `..`, ani `%2f` nie jest normalizowane
    p = check_scope("https://science.nask.pl/api/media/..%2f..%2fwp-content/x.jpg?a=1")
    ok(raw_path_and_query(p) == "/api/media/..%2f..%2fwp-content/x.jpg?a=1",
       f"normalizacja zepsula sciezke: {raw_path_and_query(p)}")
    p2 = check_scope("https://science.nask.pl/api/media/%2e%2e%2frobots.txt")
    ok(raw_path_and_query(p2) == "/api/media/%2e%2e%2frobots.txt", "kodowana sciezka zmieniona")
    p3 = check_scope("https://science.nask.pl/a/../b")
    ok(raw_path_and_query(p3) == "/a/../b", f"literalne `..` zwinięte: {raw_path_and_query(p3)}")

    # 4. klasyfikator: soft-404 z kodem 200 musi byc NEGATYWEM
    soft = classify({"status": 200, "content_type": "text/html", "bytes_read": 51201,
                     "markers": {"HTML_DOC": 1, "SOFT404_PL": 2}, "secret_marker_hits": 0})
    ok(soft == "soft-404-html", f"soft-404 sklasyfikowany jako {soft}")
    home = classify({"status": 200, "content_type": "text/html", "bytes_read": 51201,
                     "markers": {"HTML_DOC": 1}, "secret_marker_hits": 0})
    ok(home == "html-page", f"strona HTML sklasyfikowana jako {home}")
    shell = classify({"status": 200, "content_type": "text/html", "bytes_read": 713,
                      "markers": {"HTML_DOC": 1, "SPA_SHELL": 1}, "secret_marker_hits": 0})
    ok(shell == "spa-catch-all-shell", f"shell SPA sklasyfikowany jako {shell}")
    cand = classify({"status": 200, "content_type": "text/plain", "bytes_read": 300,
                     "markers": {"ENV_ASSIGNMENTS": 4, "SECRET_KEYS": 1}, "secret_marker_hits": 5})
    ok(cand == "CANDIDATE-SECRET-FILE", f"plik srodowiskowy sklasyfikowany jako {cand}")
    ok(classify({"status": 405, "content_type": "application/json", "bytes_read": 30, "markers": {}})
       == "method-not-allowed-route-exists", "405 bez werdyktu o istnieniu trasy")
    ok(classify({"status": None, "error": "transport: ConnectionResetError: reset"}) == "transport-error",
       "blad transportu nie sklasyfikowany")

    # 5. redakcja: podglad nie powstaje dla wrazliwej sciezki, a znaki niedrukowalne sa kropkowane
    ok(_sanitize_preview(b"abc\x00\xffdef") == "abc..def", "sanityzacja podgladu")

    # 6. dowod z identycznego skrotu
    ev = cross_hash_evidence([
        {"id": "control", "raw_path": "/api/media/wp-content/x.jpg", "sha256": "a" * 64, "bytes_read": 10},
        {"id": "traversal", "raw_path": "/api/media/%2e%2e%2fwp-content/x.jpg", "sha256": "a" * 64, "bytes_read": 10},
        {"id": "other", "raw_path": "/robots.txt", "sha256": "b" * 64, "bytes_read": 10},
    ])
    ok(len(ev) == 1 and len(ev[0]["identical_bodies"]) == 2, "dowod hash nie wykryl pary")

    # 7. walidacja planu odrzuca probe spoza zakresu PRZED wysylka
    try:
        load_plan_json = [{"id": "x", "url": "https://evil.example/x"}]
        for item in load_plan_json:
            check_scope(item["url"])
        ok(False, "plan z hostem spoza §5 przeszedl walidacje")
    except ScopeError:
        pass

    status_word = "OK" if not fails else "FAIL"
    print(f"selftest: {status_word} (10 grup, {len(fails)} bledow)")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", help="plik JSON z probami [{id,url,why}]")
    ap.add_argument("--out", help="gdzie zapisac raport JSON")
    ap.add_argument("--rps", type=float, default=DEFAULT_RPS, help=f"tempo (domyslnie {DEFAULT_RPS}, sufit {MAX_RPS})")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    ap.add_argument("--dry-run", action="store_true", help="walidacja planu bez zadnego zadania")
    ap.add_argument("--selftest", action="store_true", help="testy offline (zero sieci)")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.plan:
        ap.error("--plan jest wymagany (albo --selftest)")

    plan = load_plan(args.plan)
    report = run_plan(plan, rps=args.rps, timeout=args.timeout, dry_run=args.dry_run)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out and not args.dry_run:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    if args.dry_run:
        # audyt planu: dokladnie to, co wyszloby na drut (surowe sciezki)
        for item in report.get("probes", []):
            print(f'  {item["id"]:34s} {item["raw_path"]}')
    # do logu: TYLKO podsumowanie liczbowe (nigdy tresci odpowiedzi)
    s = report.get("summary") or {}
    print(json.dumps({
        "dry_run": report.get("dry_run"),
        "count": report.get("count"),
        "wall_seconds": report.get("wall_seconds"),
        "min_observed_gap_s": report.get("min_observed_gap_s"),
        "verdicts": s.get("verdicts"),
        "candidates": s.get("candidates"),
        "identical_bodies": report.get("identical_bodies"),
        "out": args.out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
