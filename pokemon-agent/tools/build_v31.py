#!/usr/bin/env python3
"""Build agents/main_heuristic_v31.py from c87_v30.py (c87f7a48 e2443df).

v31 = v30 + MY (a450) S1/S2 actually WIRED.
v30 already carries: my S3 attack-est fix (LIVE), v28 bands (bench 400/60/40,
KO 60/30, mirror guard), FAST_EX 13 hardcoded ids, and - DEAD - copies of my
S1 constants (SWARM_BENCH_*) and 8560's mirror-specialist constants (defined,
never used; specialist stays OUT of v31 - no spec, no owner, mirror duel
already won by v30 bands alone).

Wiring:
  S1 bench-as-resource  : PLAY basic -> +35 (bench<=1) / +15 (bench==2),
                          target 3, in EVERY matchup (root cause #1).
  S2 auto fast-ex       : _swarm_fast_ex() = seed13 UNION auto-detected
                          (ex/mex & hp>=200 or hp>=150&rc<=2; own Mega
                          Abomasnow excluded) = 136 ids; seen-based threat
                          (bench sightings count), Snover retreat urgency
                          only vs fast-ex ACTIVE (root cause #3, incl.
                          UNKNOWN future ex cards - hardcode can't do that).

Regex subn with injection-count asserts (proven method on this family).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents/c87_v30.py"
DST = ROOT / "agents/main_heuristic_v31.py"

out = SRC.read_text()
n_patches = 0


def patch(pattern: str, repl: str, count: int = 1, tag: str = "") -> None:
    global out, n_patches
    out, n = re.subn(pattern, repl, out, count=count, flags=re.DOTALL)
    if n != count:
        raise SystemExit(f"PATCH FAILED [{tag}]: expected {count}, got {n}")
    n_patches += n
    print(f"  ok [{tag}] x{n}")


# --- S2 engine: config + auto fast-ex set (before the dead constants) ------
CONFIG = '''# --- v31 (a450): S1/S2 WIRED. In v30 the constants below existed but were
# DEAD (defined, never referenced). v31 makes them live. S3 (attack-est) was
# already live in v30 (copied from a450 v29_swarm) and stays untouched.
SWARM_AUTO_FAST_EX = True
SWARM_BENCH = True

_FAST_EX_AUTO_CACHE = None

def _swarm_fast_ex() -> frozenset:
    """Seed 13 ids UNION auto-detected fast-ex threats (a450 v29_swarm S2).

    Auto rule: pokemon flagged ex (or mega-ex - but NOT our own mirror Mega
    Abomasnow ex, which would only add mirror noise; Mega Starmie 1031 stays
    in via the seed set) with hp >= 200, or hp >= 150 with retreat cost <= 2.
    Covers future/unknown ex cards that a hardcoded set will always miss.
    """
    global _FAST_EX_AUTO_CACHE
    if _FAST_EX_AUTO_CACHE is not None:
        return _FAST_EX_AUTO_CACHE
    ids = {63, 547, 1031, 861, 24, 171, 361, 336, 299, 169, 839, 992, 1002}
    if SWARM_AUTO_FAST_EX:
        try:
            for _cid_s, _c in CARDS.items():
                try:
                    if _c.get("ct") != CardType.POKEMON:
                        continue
                    is_ex = _c.get("ex") == 1
                    is_mex = _c.get("mex") == 1
                    if not is_ex and not is_mex:
                        continue
                    if is_mex and not is_ex:
                        continue  # mirror safety: our own Mega Abomasnow stays out
                    hp = int(_c.get("hp") or 0)
                    rc = int(_c.get("rc") or 9)
                    if hp >= 200 or (hp >= 150 and rc <= 2):
                        try:
                            ids.add(int(_cid_s))
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass
    _FAST_EX_AUTO_CACHE = frozenset(ids)
    return _FAST_EX_AUTO_CACHE

'''

patch(r"(SWARM_BENCH_TARGET = 3)", CONFIG + r"\1", 1, "S2 config+auto before SWARM constants")

# --- S1+S2 wiring: replace the FAST_EX block --------------------------------
OLD_FAST = (
    r'''        # --- FAST_EX mode \(v26\): Genesect ex, Raging Bolt ex, Mega Starmie ex etc\.\n'''
    r'''        FAST_EX_IDS_V30 = \{63, 547, 1031, 861, 24, 171, 361, 336, 299, 169, 839, 992, 1002\}\n'''
    r'''        try:\n'''
    r'''            opp_id = opp_active\.get\("id"\) if opp_active else None\n'''
    r'''            if opp_id in FAST_EX_IDS_V30:\n'''
    r'''                # vs fast ex, bench aggressively and protect Snover\n'''
    r'''                if len\(my_bench\) < 3 and otype == OptionType\.PLAY:\n'''
    r'''                    score \+= 25\n'''
    r'''                # if our active is Snover \(90 HP\) vs fast ex, retreat urgently\n'''
    r'''                if my_active and my_active\.get\("id"\) == 722 and my_active\.get\("hp", 0\) <= 90:\n'''
    r'''                    if otype in \(OptionType\.RETREAT, OptionType\.SWITCH\):\n'''
    r'''                        score \+= 100\n'''
    r'''        except Exception:\n'''
    r'''            pass\n'''
)
NEW_FAST = '''        # --- v31 FAST_EX (S2 WIRED): auto-detected set, seen-based threat.
        try:
            _fast = _swarm_fast_ex()
            opp_id = opp_active.get("id") if opp_active else None
            threat_seen = bool(seen & _fast)
            if opp_id in _fast or threat_seen:
                # S1 WIRED: warm the bench BEFORE the first KO (root cause #1)
                if otype == OptionType.PLAY and len(my_bench) < SWARM_BENCH_TARGET:
                    score += SWARM_BENCH_THREAT
                # Snover (90 HP) retreats urgently only vs fast-ex ACTIVE
                if opp_id in _fast and my_active and my_active.get("id") == 722 \\
                        and my_active.get("hp", 0) <= 90:
                    if otype in (OptionType.RETREAT, OptionType.SWITCH):
                        score += 100
        except Exception:
            pass

        # --- v31 S1 WIRED: bench-as-resource in EVERY matchup.
        # Root cause #1 (c87f forensics + our FFI): 50% of losses end with an
        # empty board T3-11. Plant basics while they are still in hand.
        if SWARM_BENCH and otype == OptionType.PLAY:
            try:
                _bid = _hand_id(obs, me_idx, opt.get("index"))
                if _bid and is_basic_pokemon(_bid) and len(my_bench) < SWARM_BENCH_TARGET:
                    score += SWARM_BENCH_HOT if len(my_bench) <= 1 else SWARM_BENCH_WARM
            except Exception:
                pass
'''
patch(OLD_FAST, NEW_FAST.replace("\\", "\\\\"), 1, "S1+S2 wiring (FAST_EX block)")

DST.write_text(out)
print(f"\nwrote {DST} ({len(out)} bytes, {n_patches} injections)")

# --- import + liveness + sanity --------------------------------------------
import importlib.util
spec = importlib.util.spec_from_file_location("_v31_check", str(DST))
mod = importlib.util.module_from_spec(spec)
sys.modules["_v31_check"] = mod
spec.loader.exec_module(mod)

fe = mod._swarm_fast_ex()
print(f"_swarm_fast_ex(): {len(fe)} ids (expect 136)")
assert len(fe) == 136, "auto set size drifted!"
for pid in (336, 299, 169, 150, 547, 1002, 1031):
    assert pid in fe, pid
assert 723 not in fe, "own Mega Abomasnow must stay OUT"
assert 721 not in fe and 722 not in fe
print("auto-set probes OK (723 out, basics out)")
assert mod.SWARM_BENCH is True and mod.SWARM_AUTO_FAST_EX is True
assert mod.SWARM_BENCH_TARGET == 3 and mod.SWARM_BENCH_HOT == 35
assert mod.RETREAT_WALL == 350 and mod.GUST_BONUS == 70
dec = mod.agent({"select": None})
assert dec == list(mod.DECK), "select=None must return DECK"
print("liveness OK; knobs 350/70; SWARM flags ON")
print("ALL PATCHES VERIFIED")
