#!/usr/bin/env python3
"""Basic-flow audit: over N games, track basics we SEE (hand), PLAY to board,
and how our board size evolves at each of our turns. Distinguishes
'deck never deals basics' from 'pilot fails to bench them'.
Usage: .venv/bin/python tools/basic_flow.py agent.py ourdeck.csv oppagent.py oppdeck.csv games
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"
BASICS = {721, 722, 35}


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.agent


def load_deck(p):
    return [int(x) for x in Path(p).read_text().replace(",", " ").split() if x.strip()]


def main() -> int:
    agent = load_agent(sys.argv[1], "a")
    opp = load_agent(sys.argv[3], "o")
    our_deck, opp_deck = load_deck(sys.argv[2]), load_deck(sys.argv[4])
    games = int(sys.argv[5])
    lib = ctypes.cdll.LoadLibrary(str(LIB))
    lib.GameInitialize()

    class SD(ctypes.Structure):
        _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]

    class SER(ctypes.Structure):
        _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

    lib.BattleStart.restype = SD
    lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
    lib.GetBattleData.restype = SER
    lib.GetBattleData.argtypes = [ctypes.c_void_p]
    lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    agg = Counter()
    for g in range(games):
        seat = g % 2
        decks = our_deck + opp_deck if seat == 0 else opp_deck + our_deck
        sd = lib.BattleStart((ctypes.c_int * 120)(*decks))
        bp = sd.battlePtr
        if not bp:
            continue
        seen_turn = -1
        max_board = 0
        basics_in_hand_turns = 0
        turns = 0
        try:
            while True:
                obs = json.loads(lib.GetBattleData(bp).json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res >= 0:
                    agg["games"] += 1
                    if res == seat:
                        agg["wins"] += 1
                    else:
                        agg["losses"] += 1
                        if max_board <= 2:
                            agg["loss_maxboard<=2"] += 1
                    break
                if obs.get("select") is None:
                    break
                me = int(cur.get("yourIndex", 0))
                fn = agent if me == seat else opp
                if me == seat:
                    t = int(cur.get("turn") or 0)
                    if t != seen_turn:
                        seen_turn = t
                        turns += 1
                        p = cur["players"][seat]
                        board_n = sum(1 for z in ("active", "bench") for x in (p.get(z) or []) if isinstance(x, dict))
                        max_board = max(max_board, board_n)
                        hand_basics = sum(1 for c in (p.get("hand") or []) if isinstance(c, dict) and int(c.get("id") or 0) in BASICS)
                        if hand_basics > 0:
                            basics_in_hand_turns += 1
                        if board_n <= 1:
                            agg["turns_board<=1"] += 1
                        agg["turns_total"] += 1
                dec = fn(obs)
                if not isinstance(dec, list):
                    dec = []
                if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
                    break
        finally:
            lib.BattleFinish(bp)
    print(dict(agg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
