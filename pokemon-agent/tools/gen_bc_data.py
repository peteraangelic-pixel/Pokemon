#!/usr/bin/env python3
"""Behavior-cloning data: champion pilot plays both seats on a deck mix;
log (state_feats, option_feats, chosen_idx, outcome) for every select.

Run: .venv/bin/python tools/gen_bc_data.py --games 2400 --out kaggle_results/bc_data.npz
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G
import policy_feats as PF

ROOT = Path(__file__).resolve().parents[1]
CHAMP = ROOT / "agents/c87_v44.py"
FZ = None
MOD = None


def init_worker():
    global FZ, MOD
    import tarfile
    with tarfile.open(ROOT / "bundles/ptcg_v55_mirror_a450.tar.gz") as tf:
        ci = json.loads(tf.extractfile("card_index.json").read())
    FZ = PF.Featurizer(ci)
    MOD = G.load_module(str(CHAMP), f"_bc_champ_{os.getpid()}")


def play_game(task):
    deck_a, deck_b = task
    lib = G.get_lib()
    decks = [deck_a, deck_b]
    recs = [[], []]
    cards = (ctypes.c_int * 120)(*deck_a, *deck_b)
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        return None
    result = -1
    try:
        step = 0
        while True:
            step += 1
            if step > 5000:
                break
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                result = res
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            G.rebind(MOD, decks[me])
            dec = MOD.agent(obs)
            if not isinstance(dec, list) or not dec:
                dec = [0]
            opts = sel.get("option") or []
            if opts:
                try:
                    s = FZ.state_feats(obs, me)
                    ofeats = [FZ.option_feats(o, obs, me) for o in opts[: PF.MAX_OPT]]
                    recs[me].append((s, ofeats, int(dec[0])))
                except Exception:
                    pass
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    if result not in (0, 1):
        return None
    S, O, M, Y, R = [], [], [], [], []
    for seat in (0, 1):
        y = 1.0 if result == seat else -1.0
        for s, ofeats, ch in recs[seat]:
            n = len(ofeats)
            om = np.zeros((PF.MAX_OPT, PF.DO), dtype=np.float16)
            om[:n] = np.array(ofeats, dtype=np.float16)
            mask = np.zeros(PF.MAX_OPT, dtype=np.float32)
            mask[:n] = 1.0
            S.append(s)
            O.append(om)
            M.append(mask)
            Y.append(ch)
            R.append(y)
    if not S:
        return None
    return (np.array(S, dtype=np.float32), np.stack(O), np.array(M, dtype=np.float32),
            np.array(Y, dtype=np.int32), np.array(R, dtype=np.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2400)
    ap.add_argument("--out", default="kaggle_results/bc_data.npz")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    pool = []
    for pat in ("decks/v57_trolley34w.csv", "decks/c87_v60.csv", "decks/c87_v61.csv",
                "decks/top50_fresh22/*.csv", "decks/live_killers/*.csv",
                "decks/top50_provisional/*.csv"):
        pool += [str(p) for p in ROOT.glob(pat)]
    cache = {}

    def load(p):
        if p not in cache:
            cache[p] = G.load_deck(p)
        return cache[p]

    tasks = [(load(rng.choice(pool)), load(rng.choice(pool))) for _ in range(a.games)]
    t0 = time.time()
    parts, done, ndec = [], 0, 0
    with Pool(a.workers, initializer=init_worker) as pool_:
        for out in pool_.imap_unordered(play_game, tasks, chunksize=8):
            done += 1
            if out is None:
                continue
            parts.append(out)
            ndec += len(out[0])
            if done % 400 == 0:
                print(f"{done}/{a.games} games, {ndec} decisions, {time.time()-t0:.0f}s", flush=True)
    S = np.concatenate([p[0] for p in parts])
    O = np.concatenate([p[1] for p in parts])
    M = np.concatenate([p[2] for p in parts])
    Y = np.concatenate([p[3] for p in parts])
    R = np.concatenate([p[4] for p in parts])
    np.savez_compressed(a.out, S=S, O=O, M=M, Y=Y, R=R)
    print(f"saved {len(S)} decisions -> {a.out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
