#!/usr/bin/env python3
"""Offline analyzer of public JS bundles for the NASK bug-bounty morning run (P0-lite).

ZERO network. Reads bundle files from disk, extracts:
  * API endpoint candidates (fetch/axios/axios-like/string literals with /api/ or /_next/),
  * query/path parameter names,
  * identifier-format classification per endpoint (sequential int / UUID / ULID / hash / other)
    -> sequential int in a per-object route = IDOR pre-rank candidate,
  * secret candidates with an entropy filter and an allow-list of known false positives.

Why offline: regulation caps live traffic at 5 req/s, so compute never helps the network
phase; it helps HERE, on the already-downloaded public assets. Multiprocessing is used
because the corpus is hundreds of MB of text (Rust+Rayon would do the same job; this is
the no-cargo fallback and it is unit-tested).

Usage:
  python3 bundle_scan.py --in DIR_OR_FILES... --out report.json [--workers N]
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import re
from collections import Counter
from pathlib import Path

ENDPOINT_RX = re.compile(
    r"""["'`](/(?:api|_next/data|rest|graphql|v[0-9]+)[A-Za-z0-9_\-./{}$]*?)["'`]""")
FETCH_RX = re.compile(r"""(?:fetch|axios\.(?:get|post|put|patch|delete)|\.(?:get|post|put|patch|delete))\(\s*["'``]([^"'`]+)["'``]""")
QUERY_RX = re.compile(r"""[?&]([A-Za-z_][A-Za-z0-9_]{1,30})=""")
# KOREKTA #44 (cz. 1): samo `generic_assignment` wymaga CUDZYSLOWU po `=`/`:`, wiec
# sekret w stylu URL (`...&access_token=EAAB...`) byl niewidoczny — a to wlasnie
# tak najczesciej wyglada token w klejonym linku. Stad osobny wzorzec na WARTOSC
# parametru o podejrzanej nazwie. Do raportu trafia wylacznie odcisk (korekta #33).
QUERY_VALUE_RX = re.compile(
    r"""[?&](access_token|token|api_?key|apikey|secret|sig|signature|auth|password|passwd|key)"""
    r"""=([A-Za-z0-9_.\-|]{16,120})""", re.I)
# placeholder-y szblonow i wartosci oczywiscie nieliterowe — nie sa sekretami
# KOREKTA #45: `generic_assignment` na zminifikowanym JS lapal SKLEJENIA, nie sekrety:
# `token="+encodeURIComponent(t)+"` -> "wartosc" `+encodeURIComponent(t)+` (23 znaki,
# entropia 3.73 > 3.5). To byl kandydat na falszywy raport. Filtr: wartosc
# kandydata na sekret nie moze zawierac skladni JS (nawiasy, `${}`, przecinki,
# spacje) ani zaczynac sie od operatora sklejenia.
CRED_VALUE_BAD_RX = re.compile(r"[(){}\[\]$\\\s,;<>!|&*=+\-]")


def looks_like_credential(value: str) -> bool:
    """Czy wartosc moze byc literalem sekretu (a nie fragmentem kodu).

    KOREKTA #48 (moja wlasna regresja z #45): obnizylem prog entropii z 3.5 do 3.0
    dla WSZYSTKICH kandydatow, przez co run 9 zglosil 8-znakowy kandydat o entropii
    3.0 w bundlu HIVE (szum). Przywrocony prog 3.5 — i wyzszy (4.0) dla wartosci
    krotszych niz 12 znakow, bo krotka + niska entropia = prawie zawsze literał UI."""
    if not value or value[0] in "+-" or len(value) < 8:
        return False
    if CRED_VALUE_BAD_RX.search(value):
        return False
    e = shannon(value)
    if len(value) < 12:
        return e >= 4.0
    return e >= 3.5


QUERY_VALUE_ALLOW_RX = re.compile(
    r"""(?:^\$\{|\$\{|%s|\{|\}|<[a-z]|^null$|^undefined$|^true$|^false$|^[0-9.]+$|\*\*\*|xxx|your_|example)""", re.I)
# KOREKTA #44 (cz. 2): literaly sciezek i hostow. Bez tego bundel HIVE
# (2,77 MB, lead L18) dal 0 endpointow i 0 tras, bo API jest klejone dynamicznie,
# a `ENDPOINT_RX` lapie tylko /api|/_next/data|/rest|/graphql|/vN.
PATH_RX = re.compile(r"""["'`](/[A-Za-z0-9_\-./{}$%?&=]{2,120})["'`]""")
HOST_RX = re.compile(r"""https?://([A-Za-z0-9][A-Za-z0-9.\-]{2,79})""")
MAX_PATHS = 300
MAX_HOSTS = 80
STATIC_PATH_RX = re.compile(
    r"^/(?:_next/static|static|assets|dist|media|icons|images|img|fonts|css|js)/", re.I)
PATH_PARAM_RX = re.compile(r"""[\{:]([A-Za-z_][A-Za-z0-9_]{1,30})[\}]""")
UUID_RX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ULID_RX = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
HASH_RX = re.compile(r"^[0-9a-fA-F]{32,64}$")
INT_RX = re.compile(r"^[0-9]{1,10}$")

SECRET_PATTERNS = {
    "aws_access_key_id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b"),
    "generic_assignment": re.compile(
        r"""["']?(?:api[_-]?key|apikey|secret|token|password|passwd|access[_-]?key)["']?\s*[:=]\s*["']([^"']{8,})["']""",
        re.I),
}
# Znane fałszywe pozytywy: klucze buildów, mapy, placeholder-y, zmienne publiczne Next.js.
ALLOW_RX = re.compile(
    r"^(?:undefined|null|true|false|process\.env|import\.meta|NEXT_PUBLIC_|YOUR_|XXXX|changeme|"
    r"<|\\u00|0x[0-9a-fA-F]+|[0-9]+\.?[0-9]*|\{|\[|function|require\()", re.I)


def fingerprint(value: str) -> str:
    """Odcisk kandydata na sekret: sha256[:12]. Bez fragmentow wartosci w raporcie."""
    import hashlib
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:12]


def shannon(s: str) -> float:
    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    return -sum((k / n) * math.log2(k / n) for k in c.values())


def classify_id(value: str) -> str:
    v = value.strip()
    if UUID_RX.match(v):
        return "uuid"
    if ULID_RX.match(v):
        return "ulid"
    if HASH_RX.match(v):
        return "hash"
    if INT_RX.match(v):
        return "sequential-int-candidate"
    return "other"


# KOREKTA #39: surowe QUERY_RX/PATH_PARAM_RX na zminifikowanym JS daja 662 "parametry",
# z czego wiekszosc to slowa kluczowe i dwuliterowe zmienne (null/return/this/et/dpl/NaN...).
# Filtr: dlugosc >= 3, brak slow kluczowych JS/TS, brak jednoliterowych + camelCase-zmiennych
# typowych dla minifikatora (2 znaki, wielka litera na poczatku).
JS_KEYWORDS = {
    "null", "return", "this", "true", "false", "undefined", "function", "object", "string",
    "number", "boolean", "break", "case", "catch", "class", "const", "continue", "default",
    "delete", "else", "export", "extends", "finally", "for", "from", "get", "if", "import",
    "instanceof", "let", "new", "set", "super", "switch", "throw", "try", "typeof", "var",
    "void", "while", "with", "yield", "async", "await", "static", "public", "private",
    "prototype", "length", "concat", "slice", "index", "value", "target", "window",
    "document", "global", "module", "exports", "require", "define", "apply", "call",
}
JSX_INPUT_TYPES = {
    "password", "range", "search", "tel", "text", "time", "url", "week", "month", "date",
    "color", "email", "file", "hidden", "image", "number", "radio", "reset", "submit",
    "checkbox", "button", "datetime", "locale",
}


def is_real_param(name: str) -> bool:
    """Odsiewa szum minifikatora; zostawia nazwy, ktore moga byc parametrem API."""
    if not name or len(name) < 3:
        return False
    low = name.lower()
    if low in JS_KEYWORDS or low in JSX_INPUT_TYPES:
        return False
    if name[:1].isupper() and len(name) <= 3:      # `Ba`, `Ii`, `Lr` — zmienne minifikatora
        return False
    if not re.search(r"[a-z]", name):               # `NaN`, `UT`, `IO`
        return False
    if re.fullmatch(r"[A-Za-z]{1,2}\d*", name):     # `u1`, `q7`, `e`
        return False
    return True


def extract_paths(text: str, limit: int = MAX_PATHS) -> list:
    """Literaly sciezek z bundla. Priorytet: nie-statyczne (API/trasy), bo assety
    (`/_next/static/chunks/...`) zalewaja liste i niczego nie rozstrzygaja."""
    raw = {p for p in PATH_RX.findall(text) if not p.startswith("//")}
    interesting = sorted(p for p in raw if not STATIC_PATH_RX.match(p))
    static = sorted(p for p in raw if STATIC_PATH_RX.match(p))
    return (interesting + static)[:limit]


def extract_hosts(text: str, limit: int = MAX_HOSTS) -> list:
    """Hosty absolutnych URL-i w bundlu — tak znaleziono embed PowerBI (L13)."""
    c = Counter(h.rstrip(".").lower() for h in HOST_RX.findall(text))
    return [h for h, _ in c.most_common(limit)]


def query_value_secrets(text: str) -> list:
    """Sekrety w stylu `?access_token=WARTOSC` — TYLKO odcisk, nazwa i metryki."""
    out = []
    seen = set()
    for pname, value in QUERY_VALUE_RX.findall(text):
        if QUERY_VALUE_ALLOW_RX.search(value) or not looks_like_credential(value):
            continue
        fp = fingerprint(value)
        if fp in seen:
            continue
        seen.add(fp)
        out.append({"kind": "query_value_" + pname.lower(), "param": pname.lower(),
                    "length": len(value), "entropy": round(shannon(value), 2),
                    "fingerprint": fp})
    return out[:20]


def scan_text(name: str, text: str) -> dict:
    endpoints = set(ENDPOINT_RX.findall(text)) | set(FETCH_RX.findall(text))
    endpoints = {e for e in endpoints if e.startswith("/") and not e.startswith("//")}
    params = {p for p in (set(QUERY_RX.findall(text)) | set(PATH_PARAM_RX.findall(text)))
              if is_real_param(p)}
    secrets = query_value_secrets(text)
    for kind, rx in SECRET_PATTERNS.items():
        for m in rx.findall(text):
            val = m if isinstance(m, str) else m[0]
            if ALLOW_RX.match(val):
                continue
            # KOREKTA #45: wspolny filtr ksztaltu wartosci (nawiasy/sklejenia = kod,
            # nie sekret) + entropia. Wczesniejszy prog 3.5 przepuszczal
            # `+encodeURIComponent(t)+` (3.73).
            if not looks_like_credential(val):
                continue
            # KOREKTA #33: nawet 6 znakow sekretu nie powinno trafic do publicznego
            # repo. Zostaje odcisk (sha256[:12]) + dlugosc + entropia — wystarcza do
            # deduplikacji i do potwierdzenia znaleziska bez ujawniania wartosci.
            secrets.append({"kind": kind, "entropy": round(shannon(val), 2),
                            "length": len(val), "fingerprint": fingerprint(val)})
    id_samples = re.findall(r"""["']([0-9a-fA-F\-]{6,64})["']""", text)
    formats = Counter(classify_id(v) for v in id_samples[:2000])
    return {"file": name, "endpoints": sorted(endpoints), "params": sorted(params),
            "secrets": secrets, "id_formats": dict(formats),
            "paths": extract_paths(text), "hosts": extract_hosts(text)}


def _work(item):
    p = Path(item)
    try:
        return scan_text(str(p), p.read_text(encoding="utf-8", errors="replace"))
    except OSError as e:
        return {"file": str(p), "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", nargs="+", required=True, dest="inputs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count()))
    a = ap.parse_args()
    files = []
    for it in a.inputs:
        p = Path(it)
        if p.is_dir():
            files += [q for q in p.rglob("*") if q.is_file() and q.suffix in (".js", ".mjs", ".map", ".json", ".html")]
        elif p.is_file():
            files.append(p)
    with mp.Pool(a.workers) as pool:
        results = pool.map(_work, [str(f) for f in files])
    # pre-ranking IDOR: endpoint z path-param klasy sequential-int-candidate
    ranked = []
    for r in results:
        for e in r.get("endpoints", []):
            for prm in PATH_PARAM_RX.findall(e):
                ranked.append({"endpoint": e, "param": prm,
                               "note": "sprawdz format identyfikatora na zywo (rano)"})
    out = {"files": len(files), "results": results, "idor_prerank": ranked}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"przeskanowano {len(files)} plikow; endpointy: "
          f"{sum(len(r.get('endpoints', [])) for r in results)}; "
          f"sciezki: {sum(len(r.get('paths', [])) for r in results)}; "
          f"hosty: {len({h for r in results for h in (r.get('hosts') or [])})}; "
          f"sekret-kandydaty: {sum(len(r.get('secrets', [])) for r in results)}; "
          f"idor_prerank: {len(ranked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
