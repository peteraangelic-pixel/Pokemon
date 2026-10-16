#!/usr/bin/env python3
"""DAgger data: the learned policy plays one seat vs the champion; every
policy decision is labelled with the champion's choice on the same obs.
Champion labels are queried with the champion rebound to the policy's deck.

Run: .venv/bin/python tools/gen_dagger_data.py --agent agents/main_policy_v59.py --games 2400
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
AGENT_PATH = os.environ.get("DAGGER_AGENT", str(ROOT / "agents/main_policy_v59.py"))
FZ = None
CHAMP_MOD = None
POL_MOD = None


def init_worker():
    global FZ, CHAMP_MOD, POL_MOD
    import tarfile
    with tarfile.open(ROOT / "bundles/ptcg_v55_mirror_a450.tar.gz") as tf:
        ci = json.loads(tf.extractfile("card_index.json").read())
    FZ = PF.Featurizer(ci)
    CHAMP_MOD = G.load_module(str(CHAMP), f"_dg_champ_{os.getpid()}")
    POL_MOD = G.load_module(AGENT_PATH, f"_dg_pol_{os.getpid()}")


def play_game(task):
    deck_pol, deck_opp, pol_seat = task
    lib = G.get_lib()
    decks = [deck_opp, deck_opp]
    decks[pol_seat] = deck_pol
    decks[1 - pol_seat] = deck_opp
    recs = []
    cards = (ctypes.c_int * 120)(*decks[0], *decks[1])
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
            if me == pol_seat:
                G.rebind(POL_MOD, deck_pol)
                dec = POL_MOD.agent(obs)
                if not isinstance(dec, list) or not dec:
                    dec = [0]
                G.rebind(CHAMP_MOD, deck_pol)
                lab = CHAMP_MOD.agent(obs)
                if not isinstance(lab, list) or not lab:
                    lab = [0]
                opts = sel.get("option") or []
                if opts:
                    try:
                        s = FZ.state_feats(obs, me)
                        ofeats = [FZ.option_feats(o, obs, me) for o in opts[: PF.MAX_OPT]]
                        recs.append((s, ofeats, int(lab[0])))
                    except Exception:
                        pass
            else:
                G.rebind(CHAMP_MOD, deck_opp)
                dec = CHAMP_MOD.agent(obs)
                if not isinstance(dec, list) or not dec:
                    dec = [0]
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    if result not in (0, 1) or not recs:
        return None
    y = 1.0 if result == pol_seat else -1.0
    S, O, M, Y, R = [], [], [], [], []
    for s, ofeats, ch in recs:
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
    return (np.array(S, dtype=np.float32), np.stack(O), np.array(M, dtype=np.float32),
            np.array(Y, dtype=np.int32), np.array(R, dtype=np.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/main_policy_v59.py")
    ap.add_argument("--games", type=int, default=2400)
    ap.add_argument("--out", default="kaggle_results/dagger_data.npz")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    global AGENT_PATH
    AGENT_PATH = str(ROOT / a.agent) if not a.agent.startswith("/") else a.agent
    rng = random.Random(a.seed)
    pol_deck = G.load_deck(ROOT / "decks/v57_trolley34w.csv")
    pool_paths = []
    for pat in ("decks/v57_trolley34w.csv", "decks/shaun2024_wall.csv",
                "decks/top50_fresh22/*.csv", "decks/live_v56t/*.csv"):
        pool_paths += [str(p) for p in ROOT.glob(pat)]
    cache = {}

    def load(p):
        if p not in cache:
            cache[p] = G.load_deck(p)
        return cache[p]

    tasks = [(pol_deck, load(rng.choice(pool_paths)), g % 2) for g in range(a.games)]
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
    print(f"saved {len(S)} decisions -> {a.out} in {time.time()-t0:.0f}s (policy winrate in data: {(R > 0).mean():.3f})")


if __name__ == "__main__":
    main()
