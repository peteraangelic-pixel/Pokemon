#!/usr/bin/env python3
"""Build agents/main_heuristic_v34.py from c87_v33.py (1bc665f).

Evidence base (a450 autopsy of 114 v33 losses, mirror vs weakfix, 240g):
  FAMINE 58% (0 basics in hand -> structural, needs deck+agent co-design,
              OUT of scope today)
  PRIZE-RACE 26% (behind on prizes at death, mean T15)  -> lever P
  BENCH-ROT 12% (basics rot in hand, mean 1.07 @ T8)    -> lever B
  DECKOUT 4% -> skip

P  prize-deficit module: when OUR prize progress trails by >=2, KO options get
   +30*deficit (convert now), retreat/switch of a DAMAGED active gets
   +20*deficit (stop feeding KOs), PLAY gets +10*deficit (keep developing).
B  SWARM_BENCH_WARM 15 -> 30: at bench==1 a basic now scores 350 > supporter
   340, so planting actually reaches SWARM_BENCH_TARGET 3 (root cause #1).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents/c87_v33.py"
DST = ROOT / "agents/main_heuristic_v34.py"

out = SRC.read_text()
n = 0


def patch(pattern: str, repl: str, count: int = 1, tag: str = "") -> None:
    global out, n
    out, k = re.subn(pattern, repl, out, count=count, flags=re.DOTALL)
    if k != count:
        raise SystemExit(f"PATCH FAILED [{tag}]: expected {count}, got {k}")
    n += k
    print(f"  ok [{tag}] x{k}")


# --- B: warm band -----------------------------------------------------------
patch(r"SWARM_BENCH_WARM = 15",
      "SWARM_BENCH_WARM = 30  # v34: 350 > supporter 340 -> planting reaches target 3 (a450 bench-rot 12%)",
      1, "B warm 15->30")

# --- P: prize-deficit wrapper (replaces the final chain assignment) ---------
PRIZE_MOD = '''
# --- v34 (a450): prize-deficit module ---------------------------------------
# Autopsy: 26% of v33 losses = behind on prizes at death (mean T15). When we
# trail by >=2 prizes the game is a conversion race: KOs must be taken NOW,
# our damaged actives must not be fed to their attacks, and development
# options keep their value.
def _score_main_option_v34(opt, obs, me_idx, opp_idx):
    score = _score_main_option_v22b(opt, obs, me_idx, opp_idx)
    try:
        players = obs["current"]["players"]
        their_t = sum(1 for p in (players[me_idx].get("prize") or []) if p is None)
        our_t = sum(1 for p in (players[opp_idx].get("prize") or []) if p is None)
        deficit = their_t - our_t
        if deficit >= 2:
            dcap = min(deficit, 3)
            otype = opt.get("type")
            if otype == OptionType.ATTACK:
                aid = opt.get("attackId")
                if aid:
                    est = estimate_attack_damage(aid, obs, me_idx, opp_idx)
                    opp_act = _active(obs, opp_idx)
                    opp_hp = int((opp_act or {}).get("hp") or 0) if opp_act else 0
                    if est > 0 and opp_hp and est >= opp_hp:
                        score += 30 * dcap   # convert the KO while we still can
            elif otype in (OptionType.RETREAT, OptionType.SWITCH, OptionType.TO_ACTIVE):
                my_act = _active(obs, me_idx)
                if my_act:
                    my_hp = int(my_act.get("hp") or 0)
                    mx = int(my_act.get("maxHp") or 0)
                    if my_hp < mx:
                        score += 20 * dcap   # don't feed a KO from behind
            elif otype == OptionType.PLAY:
                score += 10 * dcap           # keep developing assets
    except Exception:
        pass
    return score

_score_main_option = _score_main_option_v34
'''
patch(r"_score_main_option = _score_main_option_v22b",
      PRIZE_MOD.replace("\\", "\\\\"),
      1, "P prize-deficit wrapper")

DST.write_text(out)
print(f"\nwrote {DST} ({len(out)} bytes, {n} injections)")

# --- import + sanity ----------------------------------------------------------
import importlib.util
spec = importlib.util.spec_from_file_location("_v34_check", str(DST))
mod = importlib.util.module_from_spec(spec)
sys.modules["_v34_check"] = mod
spec.loader.exec_module(mod)
assert mod.SWARM_BENCH_WARM == 30 and mod.SWARM_BENCH_HOT == 35
assert mod.SWARM_BENCH_TARGET == 3
fe = mod._swarm_fast_ex()
assert len(fe) == 144, len(fe)
assert hasattr(mod, "_score_main_option_v34")
assert mod._score_main_option.__name__ == "_score_main_option_v34"
dec = mod.agent({"select": None})
assert dec == list(mod.DECK)
print("liveness OK: WARM=30, prize module active, fast_ex=144")
print("ALL PATCHES VERIFIED")
