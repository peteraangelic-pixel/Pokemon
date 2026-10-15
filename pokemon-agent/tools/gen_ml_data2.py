#!/usr/bin/env python3
"""v42.2 data gen: state-value samples per opponent archetype (multiprocessing).

Our v41 agent (deck 34W Kyo3) vs c87_v34 proxy on pool decks. At the first
MAIN select of each of our turns we log state_features + opp-deck archetype;
label = game outcome. Pool(2) workers, each with its own libcg handle.
"""
import ctypes, glob, json, os, sys, time
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import gauntlet_ffi as G
from state_feats import state_features, deck_archetype, ARCHES

ROOT = Path(__file__).resolve().parents[1]
GAMES_PER_DECK = int(os.environ.get("GPD", "120"))
OUT = os.environ.get("OUT", str(ROOT / "kaggle_results" / "ml_data2.npz"))
_W = {}

def init_worker():
    lib = G.get_lib()
    deck = G.load_deck(str(ROOT / "decks/v41_34w_kyo3.csv"))
    m1 = G.load_module(str(ROOT / "agents/main_heuristic_v41.py"), "_g2our")
    G.rebind(m1, deck)
    m2 = G.load_module(str(ROOT / "agents/c87_v34.py"), "_g2opp")
    _W.update(lib=lib, deck=deck, our=m1, opp=m2)

def play(task):
    opp_path, games, seed0 = task
    lib, our_deck, m1, m2 = _W["lib"], _W["deck"], _W["our"], _W["opp"]
    od = G.load_deck(opp_path)
    G.rebind(m2, od)
    arch = deck_archetype(od)
    rows = []
    for g in range(games):
        seat = (seed0 + g) % 2
        d0 = our_deck if seat == 0 else od
        d1 = od if seat == 0 else our_deck
        cards = (ctypes.c_int * 120)(*d0, *d1)
        sd = lib.BattleStart(cards); bp = sd.battlePtr
        if not bp: continue
        pending = []
        r = 0; step = 0; last_turn = -1
        try:
            while step < 5000:
                step += 1
                obs = json.loads(lib.GetBattleData(bp).json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res >= 0:
                    r = 0 if res == 2 else (1 if res == seat else -1); break
                sel = obs.get("select")
                if sel is None: break
                me = int(cur.get("yourIndex", 0))
                if me == seat and sel.get("type") == 0:
                    turn = int(cur.get("turn") or 0)
                    if turn != last_turn:
                        last_turn = turn
                        try: pending.append(state_features(obs, me, 1 - me, None))
                        except Exception: pass
                dec = (m1.agent if me == seat else m2.agent)(obs)
                if not isinstance(dec, list): dec = []
                arg = (ctypes.c_int * len(dec))(*dec)
                if lib.Select(bp, arg, len(dec)) != 0: break
        finally:
            lib.BattleFinish(bp)
        if r != 0:
            lab = 1.0 if r == 1 else 0.0
            for f in pending:
                rows.append((f, lab, arch, seed0 + g))
    return rows

def main():
    pool = sorted(glob.glob(str(ROOT / "decks/top50_provisional/*.csv")))
    pool += sorted(glob.glob(str(ROOT / "decks/live_oct13/*.csv")))
    hard = ["decks/top50_provisional/Ricardo_Paizinho__122908409.csv",
            "decks/live_oct13/live_ogerpon_hydrapple.csv",
            "decks/top7_live/Eugen_LNCanti.csv"]
    tasks = []
    seed = 0
    for p in pool:
        tasks.append((p, GAMES_PER_DECK, seed)); seed += GAMES_PER_DECK
    for p in hard:  # oversample nemesis decks x3
        for _ in range(2):
            tasks.append((str(ROOT / p), GAMES_PER_DECK, seed)); seed += GAMES_PER_DECK
    t0 = time.time()
    X, Y, A, GID = [], [], [], []
    with Pool(2, initializer=init_worker) as pool_:
        for rows in pool_.imap_unordered(play, tasks):
            for f, lab, arch, gid in rows:
                X.append(f); Y.append(lab); A.append(ARCHES.index(arch)); GID.append(gid)
            print(f"{len(X)} rows {time.time()-t0:.0f}s", flush=True)
    Xa = np.asarray(X, dtype=np.float32)
    np.savez_compressed(OUT, X=Xa, y=np.asarray(Y, np.float32),
                        arch=np.asarray(A, np.int32), gid=np.asarray(GID, np.int32))
    print(f"saved {OUT}: {Xa.shape}")

if __name__ == "__main__":
    main()
