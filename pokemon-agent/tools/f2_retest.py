#!/usr/bin/env python3
"""F2: honest re-test of F1 top-K decks on FULL pools with interleaved A/B vs
the control deck, same agent. Prints per-candidate delta + z vs control.
Acceptance (pre-registered): delta >= +2.0pp AND z >= 2.0 on BOTH independent
runs (this script run twice with different seeds)."""
from __future__ import annotations
import argparse, ctypes, glob, json, math, os, random, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G


def play(lib, agent, oagent, deck, od, seat):
    cards = (ctypes.c_int * 120)(*(deck if seat == 0 else od), *(od if seat == 0 else deck))
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
            dec = agent(obs) if me == seat else oagent(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
            if step > 4000:
                break
    finally:
        lib.BattleFinish(bp)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/c87_v26_weakfix.py")
    ap.add_argument("--candidates", default="search_results/f1_top10.json")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--meta", default="decks/meta1012,decks/exotic_gate")
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--out", default="search_results/f2_run.json")
    args = ap.parse_args()

    lib = G.get_lib()
    rng = random.Random(args.seed)
    m = G.load_module(args.agent, f"_f2_{uuid.uuid4().hex[:8]}")
    agent = m.agent
    opp_mod = G.load_module(args.agent, f"_f2opp_{uuid.uuid4().hex[:8]}")

    files = []
    for p in [x for x in args.meta.split(',') if x]:
        fs = [f for f in sorted(glob.glob(f"{p}/*.csv")) if not os.path.basename(f).startswith('_')]
        files += fs
    print(f"full pool: {len(files)} decks x {args.games} games x (1+candidates) arms", flush=True)

    cands = json.load(open(args.candidates))[:args.top]
    ctrl = [int(x) for x in (Path(__file__).resolve().parents[1] / 'decks/v22_35w_noBoss.csv').read_text().replace(',', ' ').split()]
    arms = [("CTRL", ctrl)] + [(f"cand{i}_{c['wr']:.3f}", c['deck']) for i, c in enumerate(cands)]

    stats = {name: [0, 0, 0] for name, _ in arms}
    for f in files:
        od = G.load_deck(f)
        G.rebind(opp_mod, od)
        oagent = opp_mod.agent
        for g in range(args.games):
            seat = g % 2
            for name, deck in arms:
                r = play(lib, agent, oagent, deck, od, seat)
                stats[name][0 if r == 1 else (1 if r == -1 else 2)] += 1

    cw = sum(stats["CTRL"])
    cx = stats["CTRL"][0] / max(1, cw)
    print(f"CTRL: {stats['CTRL'][0]}W-{stats['CTRL'][1]}L ({cx:.4f}, n={cw})")
    out = dict(seed=args.seed, ctrl=cx, ctrl_n=cw, cands=[])
    for name, _ in arms[1:]:
        t = stats[name]
        n = sum(t)
        x = t[0] / max(1, n)
        se = math.sqrt(x * (1 - x) / n + cx * (1 - cx) / cw)
        z = (x - cx) / se if se else 0
        verdict = "PASS" if (100 * (x - cx) >= 2.0 and z >= 2.0) else "fail"
        print(f"{name}: {x:.4f} (n={n}) delta={100 * (x - cx):+.2f}pp z={z:+.2f} -> {verdict}")
        out['cands'].append(dict(name=name, wr=x, n=n, delta_pp=round(100 * (x - cx), 2), z=round(z, 2), verdict=verdict))
    json.dump(out, open(args.out, 'w'), indent=1)

if __name__ == "__main__":
    main()
