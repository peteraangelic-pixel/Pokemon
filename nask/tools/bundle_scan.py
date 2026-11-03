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


def scan_text(name: str, text: str) -> dict:
    endpoints = set(ENDPOINT_RX.findall(text)) | set(FETCH_RX.findall(text))
    endpoints = {e for e in endpoints if e.startswith("/") and not e.startswith("//")}
    params = set(QUERY_RX.findall(text)) | set(PATH_PARAM_RX.findall(text))
    secrets = []
    for kind, rx in SECRET_PATTERNS.items():
        for m in rx.findall(text):
            val = m if isinstance(m, str) else m[0]
            if ALLOW_RX.match(val):
                continue
            if kind == "generic_assignment" and shannon(val) < 3.5:
                continue  # niskia entropia = raczej hasło-hasło z dokumentacji, nie sekret
            secrets.append({"kind": kind, "entropy": round(shannon(val), 2),
                            "preview": val[:4] + "…" + val[-2:] if len(val) > 8 else val})
    id_samples = re.findall(r"""["']([0-9a-fA-F\-]{6,64})["']""", text)
    formats = Counter(classify_id(v) for v in id_samples[:2000])
    return {"file": name, "endpoints": sorted(endpoints), "params": sorted(params),
            "secrets": secrets, "id_formats": dict(formats)}


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
          f"sekret-kandydaty: {sum(len(r.get('secrets', [])) for r in results)}; "
          f"idor_prerank: {len(ranked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
