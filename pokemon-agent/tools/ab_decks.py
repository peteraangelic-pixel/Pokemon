#!/usr/bin/env python3
"""Interleaved in-process DECK A/B: same agent file, two of OUR decks.

Arm A plays the agent with --deck-a, arm B with --deck-b (separate module
instances, rebound per instance).  Opponent is the reference policy (same
agent file) playing the OPPONENT's deck, so the measurement is the deck-only
delta against a fixed meta.  Blocks alternate so libcg.so per-process RNG
drift cancels (same rationale as ab_interleaved.py).

Usage:
  .venv/bin/python tools/ab_decks.py --agent agents/main_heuristic_v22b.py \
      --deck-a decks/v12_30_boss4.csv --deck-b decks/v22_35w.csv \
      --pools decks/meta1012 --blocks 2 --block-games 50
"""
from __future__ import annotations
import argparse, ctypes, glob, json, math, os, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G


def load(agent_path, deck, tag):
    m = G.load_module(agent_path, f"_abd_{tag}_{uuid.uuid4().hex[:8]}")
    G.rebind(m, deck)
    return m.agent


def run_block(agent, opp_agent, our_deck, opp_deck, games):
    w = l = d = 0
    lib = G.get_lib()
    for g in range(games):
        seat = g % 2
        d0 = our_deck if seat == 0 else opp_deck
        d1 = opp_deck if seat == 0 else our_deck
        cards = (ctypes.c_int * 120)(*d0, *d1)
        sd = lib.BattleStart(cards)
        bp = sd.battlePtr
        if not bp:
            d += 1
            continue
        r = 0
        step = 0
        try:
            while True:
                step += 1
                data = lib.GetBattleData(bp)
                obs = json.loads(data.json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res >= 0:
                    r = 0 if res == 2 else (1 if res == seat else -1)
                    break
                sel = obs.get("select")
                if sel is None:
                    break
                me = int(cur.get("yourIndex", 0))
                dec = agent(obs) if me == seat else opp_agent(obs)
                if not isinstance(dec, list):
                    dec = []
                arg = (ctypes.c_int * len(dec))(*dec)
                if lib.Select(bp, arg, len(dec)) != 0:
                    break
                if step > 5000:
                    break
        finally:
            lib.BattleFinish(bp)
        if r == 1:
            w += 1
        elif r == -1:
            l += 1
        else:
            d += 1
    return w, l, d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--deck-a", required=True)
    ap.add_argument("--deck-b", required=True)
    ap.add_argument("--pools", required=True, help="comma list; each item is a deck .csv or a dir of .csv")
    ap.add_argument("--blocks", type=int, default=2)
    ap.add_argument("--block-games", type=int, default=50)
    args = ap.parse_args()

    deck_a = G.load_deck(args.deck_a)
    deck_b = G.load_deck(args.deck_b)
    a = load(args.agent, deck_a, "a")
    b = load(args.agent, deck_b, "b")

    totals = {"A": [0, 0, 0], "B": [0, 0, 0]}
    for pool in [p for p in args.pools.split(",") if p.strip()]:
        pool = pool.strip()
        if os.path.isdir(pool):
            decks = sorted(p for p in glob.glob(os.path.join(pool, "*.csv"))
                           if not os.path.basename(p).startswith("_"))
        else:
            decks = [pool]
        if not decks:
            continue
        pa = [0, 0, 0]
        pb = [0, 0, 0]
        print(f"pool {pool} ({len(decks)} decks)")
        for f in decks:
            od = G.load_deck(f)
            opp_agent = load(args.agent, od, "opp")
            for _ in range(args.blocks):
                ra = run_block(a, opp_agent, deck_a, od, args.block_games)
                rb = run_block(b, opp_agent, deck_b, od, args.block_games)
                for k in range(3):
                    pa[k] += ra[k]
                    pb[k] += rb[k]
        ta, tb = sum(pa), sum(pb)
        x, y = pa[0] / ta, pb[0] / tb
        se = math.sqrt(x * (1 - x) / ta + y * (1 - y) / tb)
        print(f"  A {pa[0]}W-{pa[1]}L-{pa[2]}D ({x:.3f}) | "
              f"B {pb[0]}W-{pb[1]}L-{pb[2]}D ({y:.3f}) | "
              f"B-A {100*(y-x):+.2f}pp (z={(y-x)/se:+.2f})")
        for k in range(3):
            totals["A"][k] += pa[k]
            totals["B"][k] += pb[k]
    ta, tb = sum(totals["A"]), sum(totals["B"])
    x, y = totals["A"][0] / ta, totals["B"][0] / tb
    se = math.sqrt(x * (1 - x) / ta + y * (1 - y) / tb)
    print(f"TOTAL A {totals['A'][0]}W-{totals['A'][1]}L-{totals['A'][2]}D ({x:.4f}) | "
          f"B {totals['B'][0]}W-{totals['B'][1]}L-{totals['B'][2]}D ({y:.4f}) | "
          f"B-A {100*(y-x):+.2f}pp (z={(y-x)/se:+.2f})")


if __name__ == "__main__":
    main()
