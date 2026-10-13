#!/usr/bin/env python3
"""MEGA-TEST (a450): our agent+deck vs the TOP50 field's actual decks.

Input:  kaggle_results/top50_live/episode-*.json  (fetched by kaggle-top30 run)
        decks/top50/<team>__<ep>.csv              (extracted opponent decks)
Run:    our ARM vs every distinct top50 deck, N games (seats alternate),
        aggregate WR by leaderboard bucket (1-10 / 11-25 / 26-50) and list the
        decks that beat us most (counter census).

NOTE: this measures deck matchups (what we meet on the ladder), not their
policies (we don't have their code) - the ladder signal that matters.

Usage:
  .venv/bin/python tools/mega50_test.py --agent agents/main_heuristic_v37_gate.py \
      --our-deck decks/v22_35w_noBoss.csv --games 8 [--arm2 agents/c87_v34.py]
"""
from __future__ import annotations
import argparse, ctypes, importlib.util, json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"

class StartData(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

_lib = None
def get_lib():
    global _lib
    if _lib is None:
        lib = ctypes.cdll.LoadLibrary(str(LIB)); lib.GameInitialize()
        lib.BattleStart.restype = StartData; lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.BattleFinish.argtypes = [ctypes.c_void_p]
        lib.GetBattleData.restype = SerialData; lib.GetBattleData.argtypes = [ctypes.c_void_p]
        lib.Select.restype = ctypes.c_int; lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        _lib = lib
    return _lib

def load_deck(p): return [int(t) for line in open(p) for t in line.replace(",", " ").split() if t]
def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
def rebind(m, deck):
    m.DECK = list(deck)
    if hasattr(m, "_build_plan"): m.PLAN = m._build_plan(list(deck))

def play(lib, ag_a, dk_a, ag_b, dk_b, seat):
    d0 = dk_a if seat == 0 else dk_b
    d1 = dk_b if seat == 0 else dk_a
    cards = (ctypes.c_int * 120)(*d0, *d1)
    sd = lib.BattleStart(cards); bp = sd.battlePtr
    if not bp: return 2
    r = 2; step = 0
    try:
        while True:
            step += 1
            data = lib.GetBattleData(bp); obs = json.loads(data.json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1); break
            sel = obs.get("select")
            if sel is None: break
            me = int(cur.get("yourIndex", 0))
            ag = ag_a if me == seat else ag_b
            dec = ag(obs)
            if not isinstance(dec, list): dec = []
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0: break
            if step > 5000: break
    finally:
        lib.BattleFinish(bp)
    return {1: 1, -1: -1, 0: 0, 2: 2}.get(r, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--our-deck", default="decks/v22_35w_noBoss.csv")
    ap.add_argument("--arm2", default=None, help="optional second arm (same deck)")
    ap.add_argument("--games", type=int, default=8, help="per opponent deck (seats alternate)")
    ap.add_argument("--pool", default="decks/top50")
    args = ap.parse_args()

    lib = get_lib()
    our_deck = load_deck(str(ROOT / args.our_deck)); assert len(our_deck) == 60
    A = load_mod(str(ROOT / args.agent), "_mega_a"); rebind(A, our_deck)
    B = load_mod(str(ROOT / args.arm2), "_mega_b"); rebind(B, our_deck) if args.arm2 else None

    # meta: rank bucket from top50_extract.csv (team -> which episode row)
    meta = {}
    ex = ROOT / "kaggle_results/top50_live/top50_extract.csv"
    team_score = {}
    if ex.exists():
        import csv
        lb = ROOT / "kaggle_results/leaderboard.csv"
        if lb.exists():
            for r in csv.DictReader(open(lb, encoding="utf-8-sig")):
                team_score[r["TeamName"]] = float(r["Score"])
    pool = sorted((ROOT / args.pool).glob("*.csv"))
    print(f"arm={args.agent}" + (f" + {args.arm2}" if args.arm2 else "") + f" | decks={len(pool)} | games/deck={args.games}")

    buckets = {"1-10": [0, 0], "11-25": [0, 0], "26-50": [0, 0], "?": [0, 0]}
    counters = []
    t0 = time.time()
    for i, p in enumerate(pool, 1):
        od = load_deck(str(p))
        if len(od) != 60: continue
        team = p.stem.split("__")[0].replace("_", " ")
        sc = team_score.get(team)
        bkey = "1-10" if (sc or 0) >= float(team_score and sorted(team_score.values())[-10] or 0) else "?"
        wl = [0, 0, 0]  # our W/L/D
        for g in range(args.games):
            seat = g % 2
            r = play(lib, A.agent, our_deck, None, od, seat)
            wl[{1: 0, -1: 1, 0: 2, 2: 2}[r]] += 1
            if B is not None:
                r2 = play(lib, B.agent, our_deck, None, od, seat)
                wl2 = None  # aggregate arm2 separately below
        if args.arm2 is None:
            pass
        counters.append((wl[1], p.stem))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
