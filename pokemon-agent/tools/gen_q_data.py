#!/usr/bin/env python3
"""Epsilon-greedy exploration data for Q(state, option) — NOTES §19 step 2'.

Our v48 pilots 34W Kyo3. At every OUR MAIN single-choice decision we log
ml_features for ALL legal options + heuristic scores; the executed option is
the heuristic argmax with prob 1-EPS, else a uniform random legal option
(unconfounded action coverage). Label = game outcome. Split-by-game is done
at train time via gid.

Opponents: c87_v34 (60%) / c87_v42_4 (25%) on random pool decks, mirror (15%).
Run: .venv/bin/python tools/gen_q_data.py [--games 12000] [--eps 0.2]
Out: kaggle_results/q_data.npz  (X, starts, executed, won, gid)
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
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G

ROOT = Path(__file__).resolve().parents[1]
EPS = float(os.environ.get("Q_EPS", "0.2"))
_W = {}


def _init():
    _W["lib"] = G.get_lib()
    _W["our_deck"] = G.load_deck(str(ROOT / "decks/v41_34w_kyo3.csv"))
    _W["mod"] = G.load_module(str(ROOT / "agents/main_heuristic_v48.py"), f"_q_our_{os.getpid()}")
    G.rebind(_W["mod"], _W["our_deck"])
    _W["opp34"] = G.load_module(str(ROOT / "agents/c87_v34.py"), f"_q_o34_{os.getpid()}")
    _W["opp424"] = G.load_module(str(ROOT / "agents/c87_v42_4.py"), f"_q_o424_{os.getpid()}")
    _W["pool"] = [G.load_deck(p) for p in sorted(glob.glob(str(ROOT / "decks/top50_provisional/*.csv")))]
    _W["rng"] = random.Random(1000 + os.getpid())


def _play(spec):
    gid, kind, deck_idx, seat = spec
    lib, mod, rng = _W["lib"], _W["mod"], _W["rng"]
    our_deck = _W["our_deck"]
    if kind == 2:  # mirror
        odeck, opp_mod = our_deck, None
    else:
        odeck = _W["pool"][deck_idx % len(_W["pool"])]
        opp_mod = _W["opp34"] if kind == 0 else _W["opp424"]
        G.rebind(opp_mod, odeck)
    d0 = our_deck if seat == 0 else odeck
    d1 = odeck if seat == 0 else our_deck
    sd = lib.BattleStart((ctypes.c_int * 120)(*d0, *d1))
    bp = sd.battlePtr
    if not bp:
        return None
    scorer = mod._score_main_option
    pending = []  # (feats_list, executed_idx)
    res = 0
    step = 0
    try:
        while step < 5000:
            step += 1
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            r = cur.get("result")
            if r is not None and r >= 0:
                res = 0 if r == 2 else (1 if r == seat else -1)
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            if me == seat:
                opts = sel.get("option") or []
                is_main = sel.get("type") == 0 or sel.get("type") == getattr(mod, "SelectType", object) and False
                try:
                    is_main = sel.get("type") == 0 or int(sel.get("type")) == 0
                except Exception:
                    is_main = False
                if is_main and opts and int(sel.get("maxCount") or 1) == 1:
                    scored = [(scorer(o, obs, me, 1 - me), i) for i, o in enumerate(opts)]
                    best_i = max(scored)[1]
                    if rng.random() < EPS:
                        exec_i = rng.randrange(len(opts))
                    else:
                        exec_i = best_i
                    try:
                        feats = [mod.ml_features(obs, me, 1 - me, o) for o in opts]
                        pending.append((feats, exec_i))
                    except Exception:
                        pass
                    dec = [exec_i]
                else:
                    dec = mod.agent(obs)
            else:
                dec = (opp_mod.agent if opp_mod else mod.agent)(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*[int(x) for x in dec])
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    if res == 0:
        return None
    won = 1 if res == 1 else 0
    return pending, won, gid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=12000)
    ap.add_argument("--out", default="kaggle_results/q_data.npz")
    args = ap.parse_args()

    from multiprocessing import Pool
    rng = random.Random(42)
    specs = []
    for g in range(args.games):
        u = rng.random()
        kind = 0 if u < 0.60 else (1 if u < 0.85 else 2)
        specs.append((g, kind, rng.randrange(78), g % 2))

    X, starts, executed, won_l, gid_l = [], [], [], [], []
    off = 0
    done = 0
    t0 = time.time()
    with Pool(2, initializer=_init) as pool:
        for out in pool.imap_unordered(_play, specs, chunksize=25):
            done += 1
            if done % 1000 == 0:
                print(f"{done}/{args.games} games, {len(starts)} decisions, {time.time()-t0:.0f}s", flush=True)
            if not out:
                continue
            pending, won, gid = out
            for feats, exec_i in pending:
                starts.append(off)
                X.extend(feats)
                off += len(feats)
                executed.append(exec_i)
                won_l.append(won)
                gid_l.append(gid)
    Xa = np.asarray(X, dtype=np.float32)
    print("X:", Xa.shape, "decisions:", len(starts))
    np.savez_compressed(ROOT / args.out, X=Xa,
                        starts=np.asarray(starts, dtype=np.int64),
                        executed=np.asarray(executed, dtype=np.int32),
                        won=np.asarray(won_l, dtype=np.int8),
                        gid=np.asarray(gid_l, dtype=np.int32))
    print("saved", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
