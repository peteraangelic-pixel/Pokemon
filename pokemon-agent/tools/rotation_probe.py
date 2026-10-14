#!/usr/bin/env python3
"""Rotation probe: in mirror games, when our Active is Kyogre (721) and a
Mega Abomasnow ex (723) sits on our bench, how energized is that Abomasnow?
Tells whether the mirror stall is a retreat problem or an energy-allocation
problem. Usage: rotation_probe.py agent.py deck.csv oppagent.py games
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
    deck = load_deck(sys.argv[2])
    games = int(sys.argv[4])
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
        sd = lib.BattleStart((ctypes.c_int * 120)(*(deck + deck)))
        bp = sd.battlePtr
        if not bp:
            continue
        seen_turn = -1
        stall_turns = 0
        try:
            while True:
                obs = json.loads(lib.GetBattleData(bp).json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res >= 0:
                    agg["games"] += 1
                    agg["wins" if res == seat else "losses"] += 1
                    if stall_turns >= 4:
                        agg["stall_games"] += 1
                        agg["stall_wins" if res == seat else "stall_losses"] += 1
                    break
                if obs.get("select") is None:
                    break
                me = int(cur.get("yourIndex", 0))
                fn = agent if me == seat else opp
                if me == seat:
                    t = int(cur.get("turn") or 0)
                    if t != seen_turn:
                        seen_turn = t
                        p = cur["players"][seat]
                        act = (p.get("active") or [None])[0]
                        bench723 = [x for x in (p.get("bench") or [])
                                    if isinstance(x, dict) and x.get("id") == 723]
                        if isinstance(act, dict) and act.get("id") == 721 and bench723:
                            en = len(bench723[0].get("energies") or [])
                            agg[f"kyo_active_aboma_en{min(en, 3)}"] += 1
                            if en >= 2:
                                stall_turns += 1
                        elif isinstance(act, dict) and act.get("id") == 723:
                            agg["aboma_active_turns"] += 1
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
