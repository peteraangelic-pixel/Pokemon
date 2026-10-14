#!/usr/bin/env python3
"""Trace our turns in a local game: hand, board, prizes per our turn."""
from __future__ import annotations

import ctypes
import importlib.util
import json
import sys
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


def main():
    agent_p, deck_p = sys.argv[1], sys.argv[2]
    opp_p, odeck_p = sys.argv[3], sys.argv[4]
    seat = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    agent, opp = load_agent(agent_p, "a"), load_agent(opp_p, "o")
    our_deck, opp_deck = load_deck(deck_p), load_deck(odeck_p)
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
    decks = our_deck + opp_deck if seat == 0 else opp_deck + our_deck
    sd = lib.BattleStart((ctypes.c_int * 120)(*decks))
    bp = sd.battlePtr
    assert bp
    seen_turn = -1
    try:
        while True:
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                print("RESULT:", res, "(we win)" if res == seat else "(we lose)" if res != 2 else "draw")
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
                    o = cur["players"][1 - seat]
                    def b(pp):
                        return [(x.get("id"), x.get("hp")) for z in ("active", "bench")
                                for x in (pp.get(z) or []) if isinstance(x, dict)]
                    hand = [c.get("id") for c in (p.get("hand") or []) if isinstance(c, dict)]
                    print(f"T{t} hand={hand} board={b(p)} prizesLeft me={len(p.get('prize') or [])} opp={len(o.get('prize') or [])} deck={p.get('deckCount')}")
            dec = fn(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                print("SELECT error"); break
    finally:
        lib.BattleFinish(bp)


if __name__ == "__main__":
    main()
