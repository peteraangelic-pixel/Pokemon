#!/usr/bin/env python3
"""parse_serve_log.py — wyciąga metryki nasycenia SGLang z `serve.log` runu ARC-AGI-3.

DLACZEGO TEN PLIK ISTNIEJE
--------------------------
Trzy sesje (c87, Gemma, 7911f950) zbiegły na wniosku, że 50+ jest funkcją PRZEPUSTOWOŚCI:
    akcje/grę = 2945 s × 1000 / (ms/token × tok/akcję)
Gemma zmierzyła, że TEN SAM model 8B miał 17,2 ms/token w r085 i 62,6 ms/token w r110 —
3,6× różnicy, która „nie pochodzi z modelu ani z promptu". Nikt nie ustalił mechanizmu,
bo **nikt nie sparsował `serve.log`**.

Hipoteza do rozstrzygnięcia (c87, `AUDYT-4-GALEZI-30-10.md` §3): pula KV = 1 011 264 tokenów,
kontekst harnessa 131 072, gier współbieżnych 10 ⇒ `10 × 131 072 = 1 310 720 > 1 011 264`,
czyli przy pełnym kontekście mieści się 7,7 gry. Pula nasyca się, gdy średni kontekst/grę
przekracza 101 126, a trim odpala dopiero przy 118 000 ⇒ nasycenie jest OCZEKIWANE.
Mechanizm niezależnie opisany przez rellik13 (25. miejsce): „kv pool sat 91-97% full and
requests queued for cache space".

CO TEN SKRYPT LICZY
-------------------
Z linii SGLang w formacie:
    Decode batch: #running-req: N, #token: T, token usage: U, gen throughput (token/s): G, #queue-req: Q
    Prefill batch: ... #token: T, token usage: U, cache hit rate: H ...
wyciąga szeregi czasowe i raportuje dla każdego runu:
  * `token usage`      — obłożenie puli KV (0..1). Kluczowe: frakcja próbek ≥ 0,91 (próg rellik13)
  * `#queue-req`       — ile żądań czeka. Kluczowe: frakcja próbek > 0 i maksimum
  * `#running-req`     — ile żądań faktycznie dekoduje (porównaj z concurrency=10)
  * `gen throughput`   — tok/s agregatowo; przeliczone na ms/token
  * `cache hit rate`   — trafialność prefix-cache (o ile jest w logu)
  * korelacja token usage ↔ gen throughput  — czy nasycenie DUSI przepustowość

UŻYCIE
------
    python3 parse_serve_log.py serve_r085.log serve_r093.log ...
    python3 parse_serve_log.py *.log --csv out.csv     # szeregi czasowe do CSV
    python3 parse_serve_log.py *.log --series          # percentyle w oknach po 100 próbek

BEZ GPU, BEZ SLOTA, BEZ SIECI. Czysty Python 3, biblioteka standardowa.
Na 5950X (16 rdzeni) plik 1 MB parsuje się w ułamku sekundy; skrypt jest jednowątkowy,
bo bottleneck to I/O, nie CPU.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from statistics import correlation, mean, median

# SGLang loguje m.in.:
#   "Decode batch: #running-req: 10, #token: 745000, token usage: 0.74, gen throughput (token/s): 946.2, #queue-req: 0"
#   "Prefill batch: #new-seq: 1, #new-token: 1234, #cached-token: 5678, token usage: 0.74, #running-req: 9, #queue-req: 0"
# Pola wyciągamy nazwą, nie pozycją — format różni się między wersjami Pennyroyal/vLLM.
FIELD_PATTERNS = {
    "token_usage": re.compile(r"token usage:\s*([0-9]*\.?[0-9]+)"),
    "running_req": re.compile(r"#running-req:\s*([0-9]+)"),
    "queue_req": re.compile(r"#queue-req:\s*([0-9]+)"),
    "gen_tput": re.compile(r"gen throughput \(token/s\):\s*([0-9]*\.?[0-9]+)"),
    "cache_hit": re.compile(r"cache hit rate:\s*([0-9]*\.?[0-9]+)"),
    "num_token": re.compile(r"#token:\s*([0-9]+)"),
    "new_token": re.compile(r"#new-token:\s*([0-9]+)"),
    "cached_token": re.compile(r"#cached-token:\s*([0-9]+)"),
}
BATCH_KIND = re.compile(r"(Decode|Prefill|Extend)\s+batch", re.IGNORECASE)
POOL_SIZE = re.compile(r"#tokens:\s*([0-9]+)")


def parse(path: str) -> dict:
    """Zwraca {'rows': [ {...}, ... ], 'pool': int|None, 'lines': int}."""
    rows: list[dict] = []
    pool = None
    n_lines = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            n_lines += 1
            if pool is None:
                m = POOL_SIZE.search(line)
                if m:
                    pool = int(m.group(1))
            if "batch" not in line and "token usage" not in line:
                continue
            rec: dict = {"line": n_lines}
            hit = False
            for key, rx in FIELD_PATTERNS.items():
                m = rx.search(line)
                if m:
                    rec[key] = float(m.group(1))
                    hit = True
            if not hit:
                continue
            kind = BATCH_KIND.search(line)
            rec["kind"] = kind.group(1).lower() if kind else "?"
            rows.append(rec)
    return {"rows": rows, "pool": pool, "lines": n_lines}


def col(rows: list[dict], key: str) -> list[float]:
    return [r[key] for r in rows if key in r]


def pct(vals: list[float], p: float) -> float:
    """Percentyl bez numpy (metoda najbliższej rangi)."""
    if not vals:
        return float("nan")
    s = sorted(vals)
    k = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
    return s[k]


def frac_ge(vals: list[float], thr: float) -> float:
    return (sum(1 for v in vals if v >= thr) / len(vals)) if vals else float("nan")


def frac_gt(vals: list[float], thr: float) -> float:
    return (sum(1 for v in vals if v > thr) / len(vals)) if vals else float("nan")


def summarize(path: str) -> dict:
    d = parse(path)
    rows, pool = d["rows"], d["pool"]
    dec = [r for r in rows if r["kind"] == "decode"]
    pre = [r for r in rows if r["kind"] == "prefill"]
    tu = col(rows, "token_usage")
    q = col(rows, "queue_req")
    run = col(rows, "running_req")
    gt = col(dec, "gen_tput")
    ch = col(rows, "cache_hit")

    out: dict = {
        "plik": path,
        "linie": d["lines"],
        "probek_batch": len(rows),
        "decode": len(dec),
        "prefill": len(pre),
        "pula_kv_tokenow": pool,
    }
    if tu:
        out.update({
            "TU_mean": round(mean(tu), 4),
            "TU_median": round(median(tu), 4),
            "TU_p90": round(pct(tu, 90), 4),
            "TU_p95": round(pct(tu, 95), 4),
            "TU_max": round(max(tu), 4),
            "TU_frac_ge_0.91": round(frac_ge(tu, 0.91), 4),   # próg rellik13 (91-97%)
            "TU_frac_ge_0.80": round(frac_ge(tu, 0.80), 4),
        })
    if q:
        out.update({
            "QUEUE_mean": round(mean(q), 2),
            "QUEUE_max": int(max(q)),
            "QUEUE_frac_gt_0": round(frac_gt(q, 0), 4),        # czy w ogóle kolejkowało
            "QUEUE_frac_ge_5": round(frac_ge(q, 5), 4),
        })
    if run:
        out.update({
            "RUNNING_mean": round(mean(run), 2),
            "RUNNING_max": int(max(run)),
        })
    if gt:
        pos = [v for v in gt if v > 0]
        if pos:
            out.update({
                "GEN_TPUT_mean": round(mean(pos), 1),
                "GEN_TPUT_median": round(median(pos), 1),
                "GEN_TPUT_min": round(min(pos), 1),
                # ms/token AGREGATOWO: 1000/throughput. To NIE jest latencja na żądanie,
                # tylko odwrotność przepustowości zbiorczej — porównywalne między runami.
                "ms_per_token_agg": round(1000.0 / mean(pos), 3),
            })
    if ch:
        out["CACHE_HIT_mean"] = round(mean(ch), 4)
    else:
        out["CACHE_HIT_mean"] = None  # SGLang nie zawsze to loguje

    # Kluczowe: czy nasycenie DUSI przepustowość?
    pairs = [(r["token_usage"], r["gen_tput"]) for r in dec
             if "token_usage" in r and r.get("gen_tput", 0) > 0]
    if len(pairs) > 10:
        xs, ys = zip(*pairs)
        try:
            out["korelacja_TU_vs_TPUT"] = round(correlation(xs, ys), 4)
        except Exception:
            out["korelacja_TU_vs_TPUT"] = None
        # przepustowość przy niskim vs wysokim obłożeniu
        lo = [y for x, y in pairs if x < 0.70]
        hi = [y for x, y in pairs if x >= 0.91]
        if lo:
            out["TPUT_przy_TU_lt_0.70"] = round(mean(lo), 1)
        if hi:
            out["TPUT_przy_TU_ge_0.91"] = round(mean(hi), 1)
        if lo and hi:
            out["STOSUNEK_duszenia"] = round(mean(lo) / mean(hi), 3)
    return out


def series(path: str, window: int = 100) -> list[tuple]:
    """Percentyle token usage w oknach — żeby zobaczyć, czy nasycenie ROSNIE w czasie."""
    d = parse(path)
    tu = col(d["rows"], "token_usage")
    q = col(d["rows"], "queue_req")
    out = []
    for i in range(0, len(tu), window):
        w = tu[i:i + window]
        wq = q[i:i + window] if q else []
        if not w:
            continue
        out.append((i // window, len(w), round(median(w), 3), round(pct(w, 95), 3),
                    round(max(w), 3), round(median(wq), 1) if wq else float("nan")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="pliki serve.log")
    ap.add_argument("--csv", metavar="PLIK", help="zapisz szeregi czasowe do CSV")
    ap.add_argument("--series", action="store_true",
                    help="drukuj token usage w oknach po 100 próbek (czy nasycenie rośnie)")
    ap.add_argument("--window", type=int, default=100)
    args = ap.parse_args()

    summaries = [summarize(p) for p in args.logs]

    keys: list[str] = []
    for s in summaries:
        for k in s:
            if k not in keys:
                keys.append(k)
    w = max(len(k) for k in keys) + 2
    header = "metryka".ljust(w) + "".join(str(s["plik"])[:22].rjust(24) for s in summaries)
    print(header)
    print("-" * len(header))
    for k in keys:
        row = k.ljust(w)
        for s in summaries:
            v = s.get(k)
            row += (("-" if v is None else str(v))).rjust(24)
        print(row)

    if len(summaries) >= 2 and "TU_mean" in summaries[0] and "TU_mean" in summaries[1]:
        a, b = summaries[0], summaries[1]
        print("\n=== PORÓWNANIE (hipoteza nasycenia KV) ===")
        print(f"  obłożenie puli   : {a['plik']} {a.get('TU_mean')} vs {b['plik']} {b.get('TU_mean')}")
        print(f"  frakcja ≥ 0.91   : {a.get('TU_frac_ge_0.91')} vs {b.get('TU_frac_ge_0.91')}"
              f"   (próg rellik13: 91-97%)")
        print(f"  kolejka > 0      : {a.get('QUEUE_frac_gt_0')} vs {b.get('QUEUE_frac_gt_0')}")
        print(f"  ms/token (agreg.) : {a.get('ms_per_token_agg')} vs {b.get('ms_per_token_agg')}")
        r1, r2 = a.get("STOSUNEK_duszenia"), b.get("STOSUNEK_duszenia")
        print(f"  duszenie (TU<0.70 / TU≥0.91): {r1} vs {r2}"
              f"   (>1 = nasycenie obniża przepustowość)")
        verdict = []
        for s in summaries:
            if s.get("TU_frac_ge_0.91", 0) and s["TU_frac_ge_0.91"] > 0.25:
                verdict.append(f"{s['plik']}: NASYCONE ({100*s['TU_frac_ge_0.91']:.0f}% próbek ≥0.91)")
            elif s.get("QUEUE_frac_gt_0", 0) and s["QUEUE_frac_gt_0"] > 0.25:
                verdict.append(f"{s['plik']}: KOLEJKUJE ({100*s['QUEUE_frac_gt_0']:.0f}% próbek z queue>0)")
            else:
                verdict.append(f"{s['plik']}: NIE nasycone (TU≥0.91 w {100*(s.get('TU_frac_ge_0.91') or 0):.0f}% próbek)")
        print("  WERDYKT:")
        for v in verdict:
            print("    -", v)

    if args.series:
        for p in args.logs:
            print(f"\n=== {p}: token usage w oknach po {args.window} próbek ===")
            print("  okno  n  mediana  p95   max   mediana_queue")
            for row in series(p, args.window):
                print("  %4d %4d  %6.3f %6.3f %6.3f  %6.1f" % row)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh)
            wr.writerow(["plik", "okno", "n", "TU_median", "TU_p95", "TU_max", "QUEUE_median"])
            for p in args.logs:
                for row in series(p, args.window):
                    wr.writerow([p, *row])
        print(f"\nCSV zapisany: {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
