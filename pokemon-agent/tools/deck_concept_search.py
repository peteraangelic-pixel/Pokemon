#!/usr/bin/env python3
"""Deck-CONCEPT search v2 — HYBRID mutate (config genetics, not random fill).

Population: (a) 35W-noBoss control mutations (energy +-2, one-trainer swaps,
Lillie/Signal counts) and (b) Lucario-concept variants anchored on the live
meta deck (4 Riolu/4 Solrock/4 Mega Lucario + Fighting energy), mutating
trainer counts & energy. Scoring: our agent (weakfix) in-process interleaved
vs meta1012-subsample + exotic_gate. Baseline = the control deck itself.
"""
from __future__ import annotations
import argparse, ctypes, glob, json, math, os, random, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G

CTRL = [int(x) for x in (Path(__file__).resolve().parents[1] / 'decks/v22_35w_noBoss.csv').read_text().replace(',', ' ').split()]
ANCHOR_LUC = [int(x) for x in (Path(__file__).resolve().parents[1] / 'decks/newconcept_pool/meta_lucario.csv').read_text().replace(',', ' ').split()]

TR_POOL = [1227, 1145, 1152, 1205, 1097, 1235, 1182, 1123, 1213, 1231, 1121, 1094]


def mutate_control(rng, deck):
    d = list(deck)
    for _ in range(rng.randint(1, 3)):
        kind = rng.random()
        if kind < 0.5:  # energy <-> trainer swap
            if 3 in d:
                d[d.index(3)] = rng.choice(TR_POOL)
            else:
                swappable = [i for i, c in enumerate(d) if c in TR_POOL and d.count(c) > 1]
                if swappable:
                    d[rng.choice(swappable)] = 3
        else:  # trainer count rebalance
            frm = rng.choice([1145, 1227, 1235, 1152, 1205])
            to = rng.choice(TR_POOL)
            if frm in d and d.count(to) < 4:
                d[d.index(frm)] = to
    return sorted(d)


LUC_TR = [1102, 1141, 1142, 1192, 1227, 1182, 1152, 1121, 1213]  # DuskBall, PPP, Gong, Carmine, Lillie, Boss, Pad, Ultra, Judge


def mutate_luc(rng, deck):
    """Swap F energy <-> Lucario-family trainers; keep pokemon lines intact."""
    d = list(deck)
    f_idx = [i for i, c in enumerate(d) if c == 6]
    tr_idx = [i for i, c in enumerate(d) if c in LUC_TR and d.count(c) > 1]
    for _ in range(rng.randint(1, 4)):
        if f_idx and (rng.random() < 0.7 or not tr_idx):
            i = rng.choice(f_idx)
            to = rng.choice(LUC_TR)
            if d.count(to) < 4:
                d[i] = to
                f_idx.remove(i)
        elif tr_idx:
            i = rng.choice(tr_idx)
            if d.count(6) + 1 <= 16:
                d[i] = 6
    return sorted(d)


def main():
    global lib
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/c87_v26_weakfix.py")
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--seed-seed", type=int, default=7)
    ap.add_argument("--meta", default="decks/meta1012,decks/exotic_gate")
    ap.add_argument("--meta-sub", type=int, default=24)
    ap.add_argument("--out", default="search_results/concept_f1.json")
    args = ap.parse_args()

    lib = G.get_lib()
    rng = random.Random(args.seed_seed)
    m = G.load_module(args.agent, f"_dcsv2_{uuid.uuid4().hex[:8]}")
    agent = m.agent
    opp_mod = G.load_module(args.agent, f"_dcsv2opp_{uuid.uuid4().hex[:8]}")

    pools = []
    for p in [x for x in args.meta.split(',') if x]:
        files = [f for f in sorted(glob.glob(f"{p}/*.csv")) if not os.path.basename(f).startswith('_')]
        if 'meta1012' in p:
            files = rng.sample(files, args.meta_sub)
        pools.append(dict(name=p, files=files))
    print(f"pools: {[(p['name'], len(p['files'])) for p in pools]}", flush=True)

    def score(deck):
        G.rebind(agent, deck)
        tw = tl = td = 0
        for pool in pools:
            for f in pool['files']:
                od = G.load_deck(f)
                G.rebind(opp_mod, od)
                oagent = opp_mod.agent
                for g in range(args.games):
                    seat = g % 2
                    cards = (ctypes.c_int * 120)(*(deck if seat == 0 else od), *(od if seat == 0 else deck))
                    sd = lib.BattleStart(cards)
                    bp = sd.battlePtr
                    if not bp:
                        td += 1
                        continue
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
                    if r == 1:
                        tw += 1
                    elif r == -1:
                        tl += 1
                    else:
                        td += 1
        n = tw + tl + td
        return tw / max(1, n), tw, tl, td

    base_wr, *_ = score(CTRL)
    print(f"BASELINE control (v22b_35w): {base_wr:.4f}", flush=True)

    results = []
    from deck_rules import load_library, deck_problems
    lib_rules = load_library()
    for t in range(args.trials):
        if t % 3 == 2:
            cand = mutate_luc(rng, ANCHOR_LUC)
            tag = "luc_mut"
        else:
            cand = mutate_control(rng, CTRL)
            tag = "ctrl_mut"
        if deck_problems(cand, lib_rules):
            continue
        wr, w, l, d = score(cand)
        results.append(dict(tag=tag, deck=cand, wr=round(wr, 4), w=w, l=l, d=d))
        results.sort(key=lambda r: -r['wr'])
        print(f"[{t+1}/{args.trials}] {tag} WR={wr:.3f} ({w}W-{l}L-{d}D) | best={results[0]['wr']:.3f}", flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(dict(baseline=base_wr, results=results), open(args.out, 'w'), indent=1)
    print("\nTOP-6:")
    for r in results[:6]:
        print(f"  {r['wr']:.4f} {r['tag']} ({r['w']}W-{r['l']}L-{r['d']}D)")

if __name__ == "__main__":
    main()
