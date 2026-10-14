#!/usr/bin/env python3
"""League data gen (NOTES §19 step 4): population of pilots x decks.

Each game: both sides drawn from a pilot population (v48, c87_v42_4, c87_v34,
v41, c87_v42_1) and deck population (our 34W Kyo3 + top50_provisional pool).
States are logged for BOTH players at their first MAIN select of each turn:
state_features(20D), arch = archetype of the OPPONENT's deck, label = that
player's outcome. Same schema as ml_data2.npz (X, y, arch, gid) so
tools/train_ml2.py can consume it via IN/OUT env (train_league.py).

Run: .venv/bin/python tools/gen_league_data.py [--games 24000]
Out: kaggle_results/league_data.npz
"""
from __future__ import annotations

import argparse
import ctypes
import glob
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
from state_feats import state_features, deck_archetype, ARCHES

ROOT = Path(__file__).resolve().parents[1]
OUR_DECK_P = str(ROOT / "decks/v41_34w_kyo3.csv")
PILOTS = [  # (file, weight)
    ("agents/main_heuristic_v48.py", 0.30),
    ("agents/c87_v42_4.py", 0.25),
    ("agents/c87_v34.py", 0.20),
    ("agents/main_heuristic_v41.py", 0.15),
    ("agents/c87_v42_1_perarch.py", 0.10),
]
_W = {}


def _pick(rng, weights):
    u = rng.random()
    s = 0.0
    for i, w in enumerate(weights):
        s += w
        if u <= s:
            return i
    return len(weights) - 1


def init_worker():
    lib = G.get_lib()
    _W["lib"] = lib
    _W["our_deck"] = G.load_deck(OUR_DECK_P)
    _W["pool"] = [G.load_deck(p) for p in sorted(glob.glob(str(ROOT / "decks/top50_provisional/*.csv")))]
    mods = {}
    for pi, (f, _) in enumerate(PILOTS):
        for side in ("a", "b"):
            mods[(pi, side)] = G.load_module(str(ROOT / f), f"_lg_{pi}_{side}_{os.getpid()}")
    _W["mods"] = mods
    _W["rng"] = random.Random(777 + os.getpid())


def play(spec):
    gid = spec
    lib, rng = _W["lib"], _W["rng"]
    weights = [w for _, w in PILOTS]
    pa, pb = _pick(rng, weights), _pick(rng, weights)
    da = _W["our_deck"] if rng.random() < 0.25 else rng.choice(_W["pool"])
    db = _W["our_deck"] if rng.random() < 0.25 else rng.choice(_W["pool"])
    ma, mb = _W["mods"][(pa, "a")], _W["mods"][(pb, "b")]
    G.rebind(ma, da)
    G.rebind(mb, db)
    arch_a = deck_archetype(db)  # arch of opponent's deck, for player A's states
    arch_b = deck_archetype(da)
    sd = lib.BattleStart((ctypes.c_int * 120)(*da, *db))
    bp = sd.battlePtr
    if not bp:
        return None
    pending = {0: [], 1: []}
    last_turn = {0: -1, 1: -1}
    res = None
    step = 0
    try:
        while step < 5000:
            step += 1
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            r = cur.get("result")
            if r is not None and r >= 0:
                res = r
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            mod = ma if me == 0 else mb
            if sel.get("type") == 0:
                turn = int(cur.get("turn") or 0)
                if turn != last_turn[me]:
                    last_turn[me] = turn
                    try:
                        pending[me].append(state_features(obs, me, 1 - me, None))
                    except Exception:
                        pass
            dec = mod.agent(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*[int(x) for x in dec])
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    if res is None or res == 2:
        return None
    rows = []
    for me in (0, 1):
        won = 1 if res == me else 0
        arch = arch_a if me == 0 else arch_b
        for feats in pending[me]:
            rows.append((feats, won, arch, gid))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=24000)
    ap.add_argument("--out", default="kaggle_results/league_data.npz")
    args = ap.parse_args()

    X, y, arch, gid = [], [], [], []
    done = 0
    t0 = time.time()
    with Pool(2, initializer=init_worker) as pool:
        for rows in pool.imap_unordered(play, range(args.games), chunksize=20):
            done += 1
            if done % 2000 == 0:
                print(f"{done}/{args.games} games, {len(y)} rows, {time.time()-t0:.0f}s", flush=True)
            if not rows:
                continue
            for feats, won, a, g in rows:
                X.append(feats)
                y.append(won)
                arch.append(a)
                gid.append(g)
    Xa = np.asarray(X, dtype=np.float32)
    print("X:", Xa.shape, "winrate:", float(np.mean(y)) if y else 0)
    def _arch_idx(a):
        return ARCHES.index(a) if a in ARCHES else ARCHES.index("DEFAULT")
    try:
        np.savez_compressed(ROOT / args.out, X=Xa, y=np.asarray(y, dtype=np.float32),
                            arch=np.asarray([_arch_idx(a) for a in arch], dtype=np.int32),
                            gid=np.asarray(gid, dtype=np.int32))
    except Exception:
        import pickle
        with open(str(ROOT / args.out) + ".pickle", "wb") as fh:
            pickle.dump({"X": Xa, "y": y, "arch": arch, "gid": gid}, fh)
        raise
    print("saved", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
