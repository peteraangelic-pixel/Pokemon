#!/usr/bin/env python3
"""Interleaved in-process A/B between two agent files on fixed opponent pools.

WHY THIS EXISTS (root cause, 2026-10-11): libcg.so keeps per-process RNG
state that is consumed by every BattleStart.  Two separate gauntlet_ffi.py
invocations (each spawning fresh worker processes) therefore sample DIFFERENT
RNG stream blocks, and 200-game runs of an IDENTICAL policy can differ by
4-10pp (observed: v21-vs-v22b "regression" on Kanga_Crustle that was later
proven to be 0/3279 score diffs via tools/diff test).  gauntlet_ffi.py numbers
are only comparable ACROSS agents when they come from the SAME invocation
(which they do, but per-run noise is then unresolvable at 200g).

Fix: run both agents in ONE process, in alternating blocks, and pool.
Adjacent blocks share the RNG stream neighborhood, so block noise cancels in
the pooled comparison.

Usage:
  .venv/bin/python tools/ab_interleaved.py \
      --agent-a agents/main_heuristic_v21.py \
      --agent-b agents/main_heuristic_v22b.py \
      --our-deck decks/v12_30_boss4.csv \
      --pools decks/top30_live/やる気元気ミワハルキ_2nd_ver_.csv,decks/mirror10 \
      --blocks 7 --block-games 100
"""
from __future__ import annotations
import argparse, ctypes, glob, json, math, os, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G


def load(agent_path, deck, tag):
    m = G.load_module(agent_path, f"_ab_{tag}_{uuid.uuid4().hex[:8]}")
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
                me = int((obs.get("current") or {}).get("yourIndex", 0))
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
    ap.add_argument("--agent-a", required=True)
    ap.add_argument("--agent-b", required=True)
    ap.add_argument("--our-deck", required=True)
    ap.add_argument("--pools", required=True, help="comma list; each item is a deck .csv or a dir of .csv")
    ap.add_argument("--blocks", type=int, default=7, help="blocks per pool per agent")
    ap.add_argument("--block-games", type=int, default=100)
    args = ap.parse_args()

    our_deck = G.load_deck(args.our_deck)
    a = load(args.agent_a, our_deck, "a")
    b = load(args.agent_b, our_deck, "b")
    # NOTE: opponent side always uses agent A's policy for BOTH pools' opponents.
    # (Policy-delta measurement: opponent is a fixed reference policy; if you
    # want the strict "same policy, deck-only delta" semantics, pass the same
    # file for --agent-a and --agent-b and vary --our-deck instead.)

    totals = {"A": [0, 0, 0], "B": [0, 0, 0]}
    for pool in [p for p in args.pools.split(",") if p.strip()]:
        pool = pool.strip()
        if os.path.isdir(pool):
            decks = sorted(glob.glob(os.path.join(pool, "*.csv")))
        else:
            decks = [pool]
        if not decks:
            continue
        pa = [0, 0, 0]
        pb = [0, 0, 0]
        print(f"pool {pool} ({len(decks)} decks)")
        for f in decks:
            opp_agent = load(args.agent_a, G.load_deck(f), "opp")
            for i in range(args.blocks):
                ra = run_block(a, opp_agent, our_deck, G.load_deck(f), args.block_games)
                rb = run_block(b, opp_agent, our_deck, G.load_deck(f), args.block_games)
                for k in range(3):
                    pa[k] += ra[k]
                    pb[k] += rb[k]
        ta, tb = sum(pa), sum(pb)
        x, y = pa[0] / ta, pb[0] / tb
        se = math.sqrt(x * (1 - x) / ta + y * (1 - y) / tb)
        print(f"  A {pa[0]}W-{pa[1]}L-{pa[2]}D ({x:.3f}, draws {pa[2]/ta:.1%}) | "
              f"B {pb[0]}W-{pb[1]}L-{pb[2]}D ({y:.3f}, draws {pb[2]/tb:.1%}) | "
              f"B-A {100*(y-x):+.2f}pp (z={(y-x)/se:+.2f})")
        for k in range(3):
            totals["A"][k] += pa[k]
            totals["B"][k] += pb[k]

    ta, tb = sum(totals["A"]), sum(totals["B"])
    x, y = totals["A"][0] / ta, totals["B"][0] / tb
    se = math.sqrt(x * (1 - x) / ta + y * (1 - y) / tb)
    print(f"TOTAL A {totals['A'][0]}W-{totals['A'][1]}L-{totals['A'][2]}D ({x:.3f}) | "
          f"B {totals['B'][0]}W-{totals['B'][1]}L-{totals['B'][2]}D ({y:.3f}) | "
          f"B-A {100*(y-x):+.2f}pp (z={(y-x)/se:+.2f})")


if __name__ == "__main__":
    main()
