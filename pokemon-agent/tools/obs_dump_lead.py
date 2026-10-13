#!/usr/bin/env python3
"""Dump the OPENING select prompts (lead choice) from the real engine.

Runs a few games vs mirror deck and prints, for our seat, every select until
our active exists (the opening sequence). This tells us exactly what the
"choose your starting basic" prompt looks like so the swarm lead logic can be
built on facts, not guesses.
"""
from __future__ import annotations
import ctypes, importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"

class StartData(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

lib = ctypes.cdll.LoadLibrary(str(LIB))
lib.GameInitialize()
lib.BattleStart.restype = StartData
lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
lib.BattleFinish.argtypes = [ctypes.c_void_p]
lib.GetBattleData.restype = SerialData
lib.GetBattleData.argtypes = [ctypes.c_void_p]
lib.Select.restype = ctypes.c_int
lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]

def load_deck(p):
    return [int(t) for line in open(p) for t in line.replace(",", " ").split() if t]

DECK = load_deck(str(ROOT / "decks/v22_35w_noBoss.csv"))
assert len(DECK) == 60, len(DECK)

AGENTS = ROOT / "agents"
spec = importlib.util.spec_from_file_location("_probe_agent", str(AGENTS / "c87_v26_weakfix.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules["_probe_agent"] = mod
spec.loader.exec_module(mod)
mod.DECK = list(DECK)
if hasattr(mod, "_build_plan"):
    mod.PLAN = mod._build_plan(list(DECK))

dumped = 0
for g in range(4):
    seat = g % 2
    cards = (ctypes.c_int * 120)(*DECK, *DECK)
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        continue
    step = 0
    try:
        while True:
            step += 1
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            if cur.get("result") is not None and cur["result"] >= 0:
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            if me == seat and dumped < 6:
                sel2 = {k: v for k, v in sel.items() if k != "option"}
                print(f"=== game {g} step {step} seat {seat} select-meta: {json.dumps(sel2)}")
                for i, o in enumerate((sel.get("option") or [])[:12]):
                    print(f"  opt[{i}] = {json.dumps(o, ensure_ascii=False)[:300]}")
                dumped += 1
            dec = mod.agent(obs) if me == seat else [0]
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
            if step > 300:
                break
    finally:
        lib.BattleFinish(bp)
print(f"dumps={dumped}")
