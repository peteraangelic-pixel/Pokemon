#!/usr/bin/env python3
"""Token budget model: the real constraint on ARC-AGI-3 throughput.

Replaces the earlier "actions per decision" metric, which was measured wrongly.
`wallclock_seconds` in `history[]` is CUMULATIVE execution time and increases on
every action, so "rising wallclock == new decision" is tautological and always
yields 1.00. The correct proxy for an LLM generation is `generated_tokens > 0`.

Findings this reproduces (MEGA-DIAGNOSIS.md section 4):

  * ~4.61 game actions per LLM generation  (we already batch)
  * ~853 generated tokens per action
  * the per-game budget is therefore in TOKENS: ~186 400 at 15.8 ms/token
  * to reach 389 actions/game (score ceiling ~51) we need ~479 tokens/action,
    i.e. a 34% cut from today's 728

Usage:
    python3 local/token_budget.py            # uses local/benchmarks/*.json
    python3 local/token_budget.py --seconds 2945 --ms-per-token 15.8
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import statistics as st
import sys


def scan(paths: list[str]) -> dict:
    """Aggregate actions, generations and tokens across benchmark.json files."""
    rows, totals = [], {"actions": 0, "gens": 0, "tokens": 0, "ratios": [], "gen_tokens": []}
    for path in paths:
        data = json.loads(pathlib.Path(path).read_text())
        a = g = t = 0
        for game in data["game_runs"]:
            prev = 0.0
            for rec in game["history"]:
                wall = float(rec["wallclock_seconds"])
                dt = wall - prev
                prev = wall
                gen = int(rec["generated_tokens"])
                a += 1
                t += gen
                if gen > 0:
                    g += 1
                    totals["gen_tokens"].append(gen)
                    if dt > 0.05:
                        totals["ratios"].append(dt * 1000.0 / gen)
        rows.append((os.path.basename(path).replace(".json", ""), a, g, t))
        totals["actions"] += a
        totals["gens"] += g
        totals["tokens"] += t
    return {"rows": rows, "totals": totals}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="local/benchmarks/*.json")
    ap.add_argument("--seconds", type=float, default=2945.0,
                    help="effective seconds per game (EVAL-BUDGET-MODEL.md §2)")
    ap.add_argument("--ms-per-token", type=float, default=None,
                    help="override; default = measured median")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.glob))
    if not paths:
        print(f"brak plików: {args.glob}", file=sys.stderr)
        return 2
    data = scan(paths)
    tot = data["totals"]

    print(f"{'run':8} {'akcji':>6} {'generacji':>10} {'akc/gen':>8} {'tok/akcje':>10}")
    for name, a, g, t in data["rows"]:
        print(f"{name:8} {a:6} {g:10} {a / g:8.2f} {t / a:10.0f}")
    a, g, t = tot["actions"], tot["gens"], tot["tokens"]
    print(f"{'RAZEM':8} {a:6} {g:10} {a / g:8.2f} {t / a:10.0f}")

    ms = args.ms_per_token or st.median(tot["ratios"])
    budget = args.seconds * 1000.0 / ms
    print()
    print(f"tempo silnika (mediana, z history[]): {ms:.1f} ms/token")
    print(f"budżet: {args.seconds:.0f} s / {ms:.1f} ms/token = {budget:,.0f} tokenów na grę")
    print(f"dziś: {t / a:.0f} tok/akcję -> {budget / (t / a):.0f} akcji na grę")
    print()
    print(f"{'akcji/grę':>10} {'wymagane tok/akcję':>20} {'vs dziś':>10}")
    today = t / a
    for acts in (205, 389, 600, 736):
        need = budget / acts
        print(f"{acts:10} {need:20.0f} {need / today:9.2f}x")

    ok = abs(a / g - 4.61) < 0.05 and abs(today - 853) < 2
    print()
    print("OK" if ok else "NIEZGODNE z MEGA-DIAGNOSIS §4.1 — zaktualizuj dokument")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
