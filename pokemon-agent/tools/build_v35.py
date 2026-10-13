#!/usr/bin/env python3
"""Build agents/main_heuristic_v35.py (a450 Phase-3) from c87_v34.py.

Design contract (lessons: basic-engine v1 REJECTED -3pp because draws were
cut AND the agent had no wiring; their v35 wiring is +50/+30 only):
  35W Hammer math INTACT, draw engine INTACT (Signal4+Waitress3 stay).
  Decks (separate files): v35_beng2 (Poffin2 for Pad+Cyrano),
  v35_beng2_k3 (+1 Kyogre for Belt), v35_beng1 (Poffin1 for Pad).

Wiring (3 patches):
  W1 Poffin/Ultra timing (live ITEM band): whiff-guard when no basics left
     (score 40), 285 when bench full, Poffin 372/352 and Ultra 344/312 by
     bench<=1/bench==2 - convert cards into bench presence ABOVE the
     supporter band exactly when famine risk is live.
  W2 search->bench target: want Kyogre down when lead is Snover (150HP body
     survives a fast-ex hit), Snover as sacrifice node under Kyogre,
     Kyogre preferred vs seen fast-ex.
  W3 famine gauge on S1: extra +10 urgency when <=3 basics unaccounted;
     S1 silent when 0 (nothing left to plant).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents/c87_v34.py"
DST = ROOT / "agents/main_heuristic_v35.py"

out = SRC.read_text()
n = 0


def patch(pattern: str, repl: str, count: int = 1, tag: str = "") -> None:
    global out, n
    out, k = re.subn(pattern, repl, out, count=count, flags=re.DOTALL)
    if k != count:
        raise SystemExit(f"PATCH FAILED [{tag}]: expected {count}, got {k}")
    n += k
    print(f"  ok [{tag}] x{k}")


# --- W-config + famine gauge helper ----------------------------------------
CFG = '''# --- v35 (a450): Phase-3 basic-engine wiring --------------------------------
SWARM_POFFIN_WIRING = True
POFFIN_ID_V35 = 1086   # Buddy-Buddy Poffin (search basics)
ULTRA_ID_V35 = 1121    # Ultra Ball (discard 1, fetch any pokemon)

def _v35_basics_left(obs, me_idx) -> int:
    """Basics still unaccounted for (deck total minus visible). Drives both
    search-timing (whiff guard) and bench urgency (famine gauge)."""
    try:
        total = sum(1 for c in DECK if is_basic_pokemon(c))
    except Exception:
        return 9
    try:
        p = obs["current"]["players"][me_idx]
        vis = 0
        act = (p.get("active") or [None])[0]
        if isinstance(act, dict) and is_basic_pokemon(act.get("id")):
            vis += 1
        vis += len(p.get("bench") or [])
        for key in ("hand", "discard"):
            for h in (p.get(key) or []):
                if isinstance(h, dict) and is_basic_pokemon(h.get("id")):
                    vis += 1
        for pr in (p.get("prize") or []):
            if isinstance(pr, dict) and is_basic_pokemon(pr.get("id")):
                vis += 1
        return max(0, total - vis)
    except Exception:
        return 9

'''
patch(r"(SWARM_BENCH_TARGET = 3)", CFG + r"\1", 1, "W-config+gauge helper")

# --- W1: Poffin/Ultra timing in the LIVE item band --------------------------
OLD_ITEM = (
    r'''        if ct == CardType\.ITEM:\n'''
    r'''            return ITEM_SCORE \+ _wall_gust_bonus\(cid, obs, me_idx, opp_idx\)\n'''
)
NEW_ITEM = '''        if ct == CardType.ITEM:
            # v35 (a450): basic-engine wiring - search timing by bench need
            # and remaining basics (58% of v33 losses were basic famine).
            if SWARM_POFFIN_WIRING and cid in (POFFIN_ID_V35, ULTRA_ID_V35):
                try:
                    _bl = _v35_basics_left(obs, me_idx)
                    _b = len(my_bench)
                    if _bl <= 0:
                        return 40   # would whiff: no basics left to find
                    if _b >= SWARM_BENCH_TARGET:
                        return 285  # bench already developed
                    if cid == POFFIN_ID_V35:
                        return 372 if _b <= 1 else 352
                    return 344 if _b <= 1 else 312  # Ultra costs a discard
                except Exception:
                    pass
            return ITEM_SCORE + _wall_gust_bonus(cid, obs, me_idx, opp_idx)
'''
patch(OLD_ITEM, NEW_ITEM.replace("\\", "\\\\"), 1, "W1 Poffin/Ultra timing")

# --- W2: search->bench target preferences -----------------------------------
OLD_TB = (
    r'''    if ctx in \(Ctx\.TO_BENCH, Ctx\.TO_FIELD\):\n'''
    r'''        return 100 \+ plan_power\(cid\) // 2\n'''
)
NEW_TB = '''    if ctx in (Ctx.TO_BENCH, Ctx.TO_FIELD):
        if SWARM_POFFIN_WIRING:
            try:
                _act = _active(obs, me_idx)
                _aid = (_act or {}).get("id")
                if cid == 721 and _aid == 722:
                    return 200 + plan_power(cid) // 2  # fragile lead -> want the 150HP body
                if cid == 722 and _aid == 721:
                    return 150 + plan_power(cid) // 2  # sacrifice node under Kyogre
                if cid == 721 and (_V21_SEEN & _swarm_fast_ex()):
                    return 190 + plan_power(cid) // 2  # vs seen fast-ex: tankier basic
            except Exception:
                pass
        return 100 + plan_power(cid) // 2
'''
patch(OLD_TB, NEW_TB.replace("\\", "\\\\"), 1, "W2 bench-target preference")

# --- W3: famine gauge on S1 --------------------------------------------------
OLD_S1 = r'''score \+= SWARM_BENCH_HOT if len\(my_bench\) <= 1 else SWARM_BENCH_WARM'''
NEW_S1 = '''_bl = _v35_basics_left(obs, me_idx)
                    if _bl > 0:
                        score += (SWARM_BENCH_HOT if len(my_bench) <= 1 else SWARM_BENCH_WARM) \\
                            + (10 if _bl <= 3 else 0)'''
patch(OLD_S1, NEW_S1.replace("\\", "\\\\"), 1, "W3 famine gauge")

DST.write_text(out)
print(f"\nwrote {DST} ({len(out)} bytes, {n} injections)")

# --- import + sanity ----------------------------------------------------------
import importlib.util
spec = importlib.util.spec_from_file_location("_v35_check", str(DST))
mod = importlib.util.module_from_spec(spec)
sys.modules["_v35_check"] = mod
spec.loader.exec_module(mod)
assert mod.SWARM_POFFIN_WIRING is True
assert mod.SWARM_BENCH_WARM == 15 and mod.SWARM_BENCH_HOT == 35
c1086 = mod.card(1086)
print("card 1086 known in index:", bool(c1086), "| ct:", c1086.get("ct"))
assert mod._v35_basics_left({"current": {"players": [{}]}}, 0) >= 0
dec = mod.agent({"select": None})
assert dec == list(mod.DECK)
print("liveness OK; wiring flags ON")
print("ALL PATCHES VERIFIED")
