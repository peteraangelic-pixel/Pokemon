#!/usr/bin/env python3
"""BC data for the Alakazam deck: v65 pilot plays both seats (mirror).
Featurizer gets an EMPTY card index on purpose: the zero-card-feature
regime measured better for learned policies (0.477 vs 0.365) and makes
train/runtime identical by construction.

Run: .venv/bin/python tools/gen_bc_alakazam.py --games 1600
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G
import policy_feats as PF

ROOT = Path(__file__).resolve().parents[1]
TEACHER = ROOT / "agents/v65_alakazam.py"
DECK_PATH = ROOT / "decks/top30_live/YumeNeko.csv"
FZ = None
MOD = None
DECK = None


def init_worker():
    global FZ, MOD, DECK
    FZ = PF.Featurizer({"cards": {}, "attacks": {}})
    MOD = G.load_module(str(TEACHER), f"_bca_{os.getpid()}")
    DECK = G.load_deck(DECK_PATH)
    G.rebind(MOD, DECK)


def play_game(_):
    lib = G.get_lib()
    recs = [[], []]
    cards = (ctypes.c_int * 120)(*DECK, *DECK)
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        return None
    result = -1
    try:
        for _step in range(5000):
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                result = res
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
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
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
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
            S.append(s); O.append(om); M.append(mask); Y.append(ch); R.append(y)
    if not S:
        return None
    return (np.array(S, dtype=np.float32), np.stack(O), np.array(M, dtype=np.float32),
            np.array(Y, dtype=np.int32), np.array(R, dtype=np.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1600)
    ap.add_argument("--out", default="kaggle_results/bc_alakazam.npz")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    parts, ndec, done = [], 0, 0
    with Pool(a.workers, initializer=init_worker) as pool_:
        for out in pool_.imap_unordered(play_game, range(a.games), chunksize=8):
            done += 1
            if out is None:
                continue
            parts.append(out)
            ndec += len(out[0])
            if done % 400 == 0:
                print(f"{done}/{a.games} games, {ndec} decisions, {time.time()-t0:.0f}s", flush=True)
    S = np.concatenate([p[0] for p in parts]); O = np.concatenate([p[1] for p in parts])
    M = np.concatenate([p[2] for p in parts]); Y = np.concatenate([p[3] for p in parts])
    R = np.concatenate([p[4] for p in parts])
    np.savez_compressed(a.out, S=S, O=O, M=M, Y=Y, R=R)
    print(f"saved {len(S)} decisions -> {a.out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
