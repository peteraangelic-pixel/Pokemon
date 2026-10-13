#!/usr/bin/env python3
"""Rebuild agents/main_heuristic_v37.py (= v37a as benchmarked, 2026-10-13).

EXACT reproduction of the paired-tested winner: c87_v36 + CFG block + P2 gate
`if mode == "WALL" and _v37_wall_live(...)`. NOTE: in the benchmarked v37a the
_v37_observe() call was NOT wired, so _V37 stayed empty and _v37_wall_live()
always returned False -> empirically "v36 minus WALL mode". That variant beat
their v36 on exotic (+4.8pp) and live toolboxes (+2.7pp), paritet elsewhere.
Rebuilt byte-logically identical to what was measured (no blind "fixes");
a separately WIRED gate variant (v37b) is a candidate for tomorrow, gated on
its own paired runs.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents/c87_v36.py"
DST = ROOT / "agents/main_heuristic_v37.py"

out = SRC.read_text()
n = 0


def patch(pattern: str, repl: str, count: int = 1, tag: str = "") -> None:
    global out, n
    out, k = re.subn(pattern, repl, out, count=count, flags=re.DOTALL)
    if k != count:
        raise SystemExit(f"PATCH FAILED [{tag}]: expected {count}, got {k}")
    n += k
    print(f"  ok [{tag}] x{k}")


CFG = '''# --- v37 (a450): slow-evidence WALL gate + deckCount mirror radar -----------
_V37 = {"dc": [], "obench": -1, "turn": -1}

def _v37_observe(obs, me_idx, opp_idx):
    try:
        cur = obs.get("current") or {}
        turn = int(cur.get("turn") or 0)
        if turn <= 1 and _V37["turn"] > 1:
            _V37["dc"] = []
        _V37["turn"] = turn
        p = (cur.get("players") or [])[opp_idx]
        _V37["obench"] = len(p.get("bench") or [])
        dc = int(p.get("deckCount") or 60)
        if not _V37["dc"] or dc < _V37["dc"][-1]:
            _V37["dc"].append(dc)
    except Exception:
        pass

def _v37_dc_drop() -> int:
    dc = _V37.get("dc") or []
    return (60 - min(dc)) if dc else 0

def _v37_wall_live(wall_cnt, opp_ahp) -> bool:
    """P2: heavy WALL scoring only with slow evidence (2 of 3)."""
    ev = 0
    if wall_cnt >= 2:
        ev += 1
    if _V37.get("turn", 0) >= 6:
        ev += 1
    if _V37.get("obench", 9) <= 1:
        ev += 1
    return ev >= 2

def _v37_mirror_radar(mirror_cnt) -> bool:
    """P3: MIRROR confirmed by self-mill signature even with 0 Kyogre seen."""
    return mirror_cnt >= ADAPT_MIRROR_THRESHOLD or _v37_dc_drop() >= 8

'''

patch(r"(ADAPT_MIRROR_THRESHOLD = 2)", CFG + r"\1", 1, "P-config")
patch(r'if mode == "WALL":',
      r'if mode == "WALL" and _v37_wall_live(wall_cnt, opp_ahp):', 1, "P2 WALL gate")

DST.write_text(out)
print(f"\nwrote {DST} ({len(out)} bytes, {n} injections)")

import importlib.util
spec = importlib.util.spec_from_file_location("_v37_check", str(DST))
mod = importlib.util.module_from_spec(spec)
sys.modules["_v37_check"] = mod
spec.loader.exec_module(mod)
# benchmark semantics: defaults obench=-1 -> gate == v36's wall_cnt>=2 PLUS
# extension: turn>=6 with a single wall id also opens WALL (ev: obench(-1<=1)
# + turn>=6). Exactly what the paired batteries measured.
assert mod._v37_wall_live(5, 330) is True    # wall_cnt>=2 (+always-obench)
assert mod._v37_wall_live(1, 330) is False   # turn=-1: no slow evidence yet
mod._V37.update({"turn": 7, "obench": -1})
assert mod._v37_wall_live(1, 330) is True    # late single-wall -> WALL
mod._V37.update({"dc": [60, 50], "obench": 1, "turn": 3})
assert mod._v37_mirror_radar(0) is True      # radar helper (dormant here)
dec = mod.agent({"select": None})
assert dec == list(mod.DECK)
print("semantics == benchmarked v37a; liveness OK")
print("ALL PATCHES VERIFIED")
