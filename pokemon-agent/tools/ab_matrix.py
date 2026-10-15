#!/usr/bin/env python3
"""Factorial in-process multi-arm comparison: (agent, deck) pairs.

Measures several (policy, deck) arms against ONE fixed opponent policy
(default: the first arm's agent) playing each opponent deck in the pools.
Blocks rotate the arm starting order so libcg.so per-process RNG block
effects cancel (same rationale as ab_interleaved.py / ab_decks.py).

Usage:
  .venv/bin/python tools/ab_matrix.py \
      --pairs "A=agents/main_heuristic_v22b.py:decks/v12_30_boss4.csv,B=agents/main_heuristic_v22b.py:decks/v22_35w_noBoss.csv,C=agents/main_heuristic_v24.py:decks/v12_30_boss4.csv,D=agents/main_heuristic_v24.py:decks/v22_35w_noBoss.csv" \
      --pools decks/meta1012 --blocks 1 --block-games 10
"""
from __future__ import annotations
import argparse, ctypes, glob, json, math, os, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G


def parse_pairs(spec):
    arms = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        label, rest = part.split("=", 1)
        agent_file, deck_file = rest.split(":", 1)
        arms.append((label.strip(), agent_file.strip(), deck_file.strip()))
    return arms


def run_game(lib, arm_agent, opp_agent, our_deck, opp_deck, seat):
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck),
                                 *(opp_deck if seat == 0 else our_deck))
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        return 2
    r = 2
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
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            dec = arm_agent(obs) if me == seat else opp_agent(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
            if step > 5000:
                break
    finally:
        lib.BattleFinish(bp)
    return {1: 0, -1: 1, 2: 2}.get(r, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--pools", required=True)
    ap.add_argument("--blocks", type=int, default=1)
    ap.add_argument("--block-games", type=int, default=50)
    ap.add_argument("--opp-agent", default=None,
                    help="fixed opponent policy (default: first arm's agent)")
    args = ap.parse_args()

    arms = parse_pairs(args.pairs)
    loaded = []
    for label, af, df in arms:
        deck = G.load_deck(df)
        m = G.load_module(af, f"_abm_{label}_{uuid.uuid4().hex[:8]}")
        G.rebind(m, deck)
        loaded.append((label, m.agent, deck))
    opp_file = args.opp_agent or arms[0][1]
    opp_m = G.load_module(opp_file, f"_abm_opp_{uuid.uuid4().hex[:8]}")
    print(f"arms: {[l for l, _, _ in loaded]} | opp policy: {opp_file}")

    totals = {l: [0, 0, 0] for l, _, _ in loaded}
    narms = len(loaded)
    for pool in [p for p in args.pools.split(",") if p.strip()]:
        pool = pool.strip()
        if os.path.isdir(pool):
            decks = sorted(p for p in glob.glob(os.path.join(pool, "*.csv"))
                           if not os.path.basename(p).startswith("_"))
        else:
            decks = [pool]
        if not decks:
            continue
        acc = {l: [0, 0, 0] for l, _, _ in loaded}
        print(f"pool {pool} ({len(decks)} decks)")
        for blk in range(args.blocks):
            order = [loaded[(i + blk) % narms] for i in range(narms)]
            for f in decks:
                od = G.load_deck(f)
                G.rebind(opp_m, od)
                opp_agent = opp_m.agent
                for g in range(args.block_games):
                    seat = g % 2
                    for label, ag, deck in order:
                        r = run_game(G.get_lib(), ag, opp_agent, deck, od, seat)
                        acc[label][r] += 1
        line = " | ".join(f"{l} {acc[l][0]}-{acc[l][1]}-{acc[l][2]}"
                          f" ({acc[l][0] / max(1, sum(acc[l])):.3f})" for l in acc)
        print(f"  {line}")
        for l in acc:
            for k in range(3):
                totals[l][k] += acc[l][k]
    print("TOTAL:")
    base = None
    for l, _, _ in loaded:
        t = totals[l]
        n = sum(t)
        x = t[0] / max(1, n)
        line = f"  {l}: {t[0]}W-{t[1]}L-{t[2]}D ({x:.4f}, n={n})"
        if base is None:
            base = (x, n)
            line += "  <- control"
        else:
            xb, nb = base
            se = math.sqrt(x * (1 - x) / n + xb * (1 - xb) / nb)
            line += f"  vs ctrl {100 * (x - xb):+.2f}pp (z={(x - xb) / se:+.2f})"
        print(line)


if __name__ == "__main__":
    main()
