#!/usr/bin/env python3
"""Generate ML training data: self-play with score-noise exploration.

Our v42 agent (heuristic, ML weights empty) pilots our deck vs c87_v34 proxy
on pool decks. At every OUR MAIN decision we log ml_features(chosen option)
plus the heuristic score; label = game outcome from our perspective.
Exploration: gaussian noise added to option scores inside our module only.
"""
import ctypes, glob, json, os, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GAMES = int(os.environ.get("GAMES", "3000"))
NOISE = float(os.environ.get("ML_NOISE", "50"))
OUT = os.environ.get("OUT", str(ROOT / "kaggle_results" / "ml_data.npz"))
OUR_DECK = os.environ.get("DECK", "decks/v41_34w_kyo3.csv")

lib = G.get_lib()
our_deck = G.load_deck(str(ROOT / OUR_DECK))
mod = G.load_module(str(ROOT / "agents/main_heuristic_v42.py"), "_mlgen")
G.rebind(mod, our_deck)
orig_scorer = mod._score_main_option
rng = random.Random(1234)

def noisy_scorer(opt, obs, me_idx, opp_idx):
    base = orig_scorer(opt, obs, me_idx, opp_idx)
    return base + rng.gauss(0, NOISE)

pool = sorted(glob.glob(str(ROOT / "decks/top50_provisional/*.csv")))
pool += sorted(glob.glob(str(ROOT / "decks/live_oct13/*.csv")))
opp_cache = {}
def opp_agent_for(path):
    if path not in opp_cache:
        m = G.load_module(str(ROOT / "agents/c87_v34.py"), "_mlopp_" + str(abs(hash(path)) % 99999))
        G.rebind(m, G.load_deck(path))
        opp_cache[path] = m.agent
    return opp_cache[path]

X, Y, GID = [], [], []
t0 = time.time()
done = 0
for g in range(GAMES):
    if g % 8 == 7:
        opp_path = None; od = our_deck; opp_agent = None  # mirror
    else:
        opp_path = pool[g % len(pool)]; od = G.load_deck(opp_path); opp_agent = opp_agent_for(opp_path)
    seat = g % 2
    d0 = our_deck if seat == 0 else od
    d1 = od if seat == 0 else our_deck
    cards = (ctypes.c_int * 120)(*d0, *d1)
    sd = lib.BattleStart(cards); bp = sd.battlePtr
    if not bp:
        continue
    pending = []  # (features, hscore)
    r = 0; step = 0
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
            if me == seat:
                if sel.get("type") == 0 or sel.get("type") == mod.SelectType.MAIN:  # MAIN select
                    opts = sel.get("option") or []
                    maxc = int(sel.get("maxCount") or 1)
                    scored = []
                    for i, o in enumerate(opts):
                        hs = orig_scorer(o, obs, me, 1 - me)
                        scored.append((hs + rng.gauss(0, NOISE), hs, i))
                    scored.sort(key=lambda t: (-t[0], t[2]))
                    k = max(1, min(maxc, len(opts)))
                    chosen = [i for _, _, i in scored[:k]]
                    top_s, top_hs, top_i = scored[0]
                    try:
                        feats = mod.ml_features(obs, me, 1 - me, opts[top_i])
                        pending.append((feats, top_hs))
                    except Exception:
                        pass
                    dec = chosen
                else:
                    dec = mod.agent(obs)
            else:
                dec = (opp_agent if opp_agent else mod.agent)(obs)
            if not isinstance(dec, list): dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0: break
    finally:
        lib.BattleFinish(bp)
    if r != 0:
        label = 1.0 if r == 1 else 0.0
        for feats, hs in pending:
            X.append(feats); Y.append(label); GID.append(g)
    done += 1
    if done % 500 == 0:
        print(f"{done} games, {len(X)} rows, {time.time()-t0:.0f}s", flush=True)

Xa = np.asarray(X, dtype=np.float32); Ya = np.asarray(Y, dtype=np.float32)
np.savez_compressed(OUT, X=Xa, y=Ya, gid=np.asarray(GID, dtype=np.int32))
print(f"saved {OUT}: X={Xa.shape} winrate={Ya.mean():.3f}")
