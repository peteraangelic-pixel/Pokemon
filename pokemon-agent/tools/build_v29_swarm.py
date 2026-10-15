#!/usr/bin/env python3
"""Build agents/main_heuristic_v29_swarm.py from c87_v26_weakfix.py.

Swarm doctrine (branch a450b00f, Phase-2) - behavior-side levers only, deck
untouched (35W-noBoss confirmed optimal +-3 cards by F1+F2):

  S1  SWARM_BENCH      bench-as-resource: plant basics T1-4 in every matchup,
                       hottest when the bench is empty (root cause #1: 50% of
                       losses end with an empty board T3-11).
  S2  _swarm_fast_ex() auto-detected fast-ex set (ex/mex & hp>=200, or hp>=150
                       & retreat<=2) UNION the v28 seed ids (root cause #3).
                       Seen-based: fires on bench sightings too, not only when
                       the threat is the active. Our own mirror Mega Abomasnow
                       (mex) stays OUT of the auto part (mirror safety).
  S3  SWARM_ATK_EST    SelectType.ATTACK branch scored by
                       estimate_attack_damage + KO bonus + mill guard
                       (root cause #3b: Riptide AND Hammer carry d=0 in the
                       db, so raw-d scoring was a 0-tie -> engine order
                       decided Riptide-vs-Hammer effectively at random).

Uses regex subn with injection-count asserts (string-anchor patching failed
3x on this family; subn+assert is the proven method).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents/c87_v26_weakfix.py"
DST = ROOT / "agents/main_heuristic_v29_swarm.py"

src = SRC.read_text()
out = src
n_patches = 0


def patch(pattern: str, repl: str, count: int = 1, tag: str = "") -> None:
    global out, n_patches
    out, n = re.subn(pattern, repl, out, count=count, flags=re.DOTALL)
    if n != count:
        raise SystemExit(f"PATCH FAILED [{tag}]: expected {count} injection(s), got {n}")
    n_patches += n
    print(f"  ok [{tag}] x{n}")


# --- S1/S2 config + auto fast-ex ------------------------------------------
CONFIG_BLOCK = '''
# --- v29 SWARM doctrine (branch a450b00f, Phase-2) ------------------------
# Root causes (c87f7a48 forensics 249 episodes + our FFI verification):
#  #1 50% of losses = our board empty T3-11 -> the bench is a RESOURCE,
#     plant it before the first KO, in every matchup.
#  #2 Snover 90HP leads (forced when it is the only basic in hand - the
#     lead formula already prefers Kyogre 212>167 when both are available,
#     and the opponent's lead is NOT visible at choice time) die vs fast ex
#     -> retreat urgency gated on a seen-based, auto-detected threat set.
#  #3 new exotic ex (Zacian 336/299, Duraludon 169/839/992, Hydrapple 150,
#     Genesect 547, Zangoose 1002, Mega Starmie 1031) missing from a
#     hardcoded set -> auto-detect from the card db instead.
#  #3b Riptide 1042 AND Hammer-lanche 1046 both carry d=0 in the db (their
#     damage lives in the effect text) -> SelectType.ATTACK scored both 0,
#     a 0-tie kept ENGINE ORDER, so Riptide-vs-Hammer was a coin toss.
SWARM_AUTO_FAST_EX = os.environ.get("PTCG_SWARM_AUTO_FAST_EX", "1") != "0"
SWARM_ATK_EST = os.environ.get("PTCG_SWARM_ATK_EST", "1") != "0"
SWARM_BENCH = os.environ.get("PTCG_SWARM_BENCH", "1") != "0"
SWARM_BENCH_TARGET = int(os.environ.get("PTCG_SWARM_BENCH_TARGET", "3"))
SWARM_BENCH_HOT = 35    # bench <= 1: hot urgency
SWARM_BENCH_WARM = 15   # bench == 2: warm
SWARM_BENCH_THREAT = 35 # fast-ex seen anywhere: keep the bench coming

_FAST_EX_AUTO_CACHE = None

def _swarm_fast_ex() -> frozenset:
    """Explicit seed ids UNION auto-detected ex/mex fast threats.

    Auto rule: a pokemon flagged ex (or mega-ex - but NOT our own mirror
    Mega Abomasnow ex, which would only add mirror noise; Mega Starmie 1031
    stays in via the seed set) with hp >= 200, or hp >= 150 with retreat
    cost <= 2 (hit-and-run profile). Covers every exotic the forensics
    listed without hardcoding per-card ids.
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

patch(r"(_V21_SEEN = set\(\))", CONFIG_BLOCK + r"\1", 1, "S-config before _V21_SEEN")

# --- S2: FAST_EX section -> seen-based auto set ----------------------------
OLD_FAST = (
    r'''        # --- FAST_EX mode \(v26\): Genesect ex, Raging Bolt ex, Mega Starmie ex etc\.\n'''
    r'''        FAST_EX_IDS_V26 = \{63, 547, 1031, 861, 24, 171, 361\}\n'''
    r'''        try:\n'''
    r'''            opp_id = opp_active\.get\("id"\) if opp_active else None\n'''
    r'''            if opp_id in FAST_EX_IDS_V26:\n'''
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
NEW_FAST = '''        # --- FAST_EX mode (v29 swarm): auto-detected + seed ids, seen-based.
        try:
            _fast = _swarm_fast_ex()
            opp_id = opp_active.get("id") if opp_active else None
            threat_seen = bool(seen & _fast)
            if opp_id in _fast or threat_seen:
                # SWARM bench-as-resource: warm the bench BEFORE the first KO
                if otype == OptionType.PLAY and len(my_bench) < SWARM_BENCH_TARGET:
                    score += SWARM_BENCH_THREAT
                # our active is Snover (90 HP) vs a KNOWN fast ex: retreat urgently
                if opp_id in _fast and my_active and my_active.get("id") == 722 \\
                        and my_active.get("hp", 0) <= 90:
                    if otype in (OptionType.RETREAT, OptionType.SWITCH):
                        score += 100
        except Exception:
            pass

        # --- SWARM bench-as-resource (root cause #1: 50% of losses = empty
        # board). Plant basics T1-4 in EVERY matchup, hottest when empty.
        if SWARM_BENCH and otype == OptionType.PLAY:
            try:
                _bid = _hand_id(obs, me_idx, opt.get("index"))
                if _bid and is_basic_pokemon(_bid) and len(my_bench) < SWARM_BENCH_TARGET:
                    score += SWARM_BENCH_HOT if len(my_bench) <= 1 else SWARM_BENCH_WARM
            except Exception:
                pass
'''
patch(OLD_FAST, NEW_FAST.replace("\\", "\\\\"), 1, "S2 fast-ex rewrite")

# --- S3: ATTACK select branch -> estimate + KO + mill guard ----------------
OLD_ATK = (
    r'''    elif stype == SelectType\.ATTACK:\n'''
    r'''        for i, o in enumerate\(opts\):\n'''
    r'''            ad = attack_data\(o\.get\("attackId"\)\)\n'''
    r'''            scores\.append\(\(int\(ad\.get\("d"\) or 0\), i\)\)\n'''
)
NEW_ATK = '''    elif stype == SelectType.ATTACK:
        # v29 SWARM (root cause #3b): Riptide AND Hammer carry d=0 in the db
        # (damage lives in the effect text) - raw-d scoring made this select a
        # 0-tie decided by engine order. Score by real estimate + KO bonus,
        # and never self-mill into a deckout.
        _my_act = _active(obs, me_idx)
        _opp_act = _active(obs, opp_idx)
        _opp_hp = int((_opp_act or {}).get("hp") or 0) if _opp_act else 0
        _at_t = card((_my_act or {}).get("id")).get("pt") if _my_act else None
        _dfn_c = card((_opp_act or {}).get("id")) if _opp_act else {}
        for i, o in enumerate(opts):
            _aid = o.get("attackId")
            _ad = attack_data(_aid)
            if not SWARM_ATK_EST:
                scores.append((int(_ad.get("d") or 0), i))
                continue
            _est = estimate_attack_damage(_aid, obs, me_idx, opp_idx)
            if _est > 0:
                try:
                    if _at_t is not None and _dfn_c.get("w") is not None and _at_t == _dfn_c.get("w"):
                        _est += 30
                    if _at_t is not None and _dfn_c.get("res") is not None and _at_t == _dfn_c.get("res"):
                        _est = max(0, _est - 30)
                except Exception:
                    pass
            _sc = max(_est, int(_ad.get("d") or 0)) * 4
            if _est > 0 and _opp_hp and _est >= _opp_hp:
                _sc += 300  # this line wins the duel now
            if _mill_would_deck_us_out(_aid, obs, me_idx):
                _sc = -500  # never deck ourselves
            scores.append((_sc, i))
'''
patch(OLD_ATK, NEW_ATK.replace("\\", "\\\\"), 1, "S3 attack-est branch")

DST.write_text(out)
print(f"\nwrote {DST} ({len(out)} bytes, {n_patches} injections)")

# --- import + liveness + sanity --------------------------------------------
import importlib.util
import json
spec = importlib.util.spec_from_file_location("_v29_check", str(DST))
mod = importlib.util.module_from_spec(spec)
sys.modules["_v29_check"] = mod
spec.loader.exec_module(mod)

fe = mod._swarm_fast_ex()
print(f"_swarm_fast_ex(): {len(fe)} ids")
for probe_id, label in ((336, "Zacian ex"), (299, "Hop's Zacian"), (169, "Duraludon"),
                        (150, "Hydrapple ex"), (547, "Genesect"), (1002, "Zangoose"),
                        (1031, "Mega Starmie"), (150 if False else 0, "-")):
    if probe_id:
        print(f"  {label} {probe_id}: {'IN' if probe_id in fe else 'out'}")
own = {721: "Kyogre", 722: "Snover"}
mega_aboma = [int(k) for k, v in mod.CARDS.items() if v.get("n") == "Mega Abomasnow ex"]
for k in mega_aboma:
    print(f"  Mega Abomasnow ex {k}: {'IN' if int(k) in fe else 'OUT'} (expect OUT)")
for k, lab in own.items():
    print(f"  {lab} {k}: {'IN' if k in fe else 'OUT'} (expect OUT)")

dec = mod.agent({"select": None})
assert dec == list(mod.DECK), "select=None must return DECK"
print("liveness OK, select=None -> DECK OK")
print("ALL PATCHES VERIFIED")
