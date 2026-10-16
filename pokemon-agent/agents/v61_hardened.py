#!/usr/bin/env python3
"""v61 hardened = champion v44 + anti-wall wrapper (live forensics 2026-10-16).

Why: learned policy v59_10k scored 344.9 on Kaggle while v56 TUNED (this
same v44 heuristic) holds ~402-428. Forensics on the 46 fetched v59 replays
(16W-29L) and a local 24-deck live matchup grid showed the killers:
  1. Crustle-wall decks (pv=['ex'] blocks Mega Abomasnow ex entirely;
     Kyogre is the only attacker that gets through, 130 dmg).
  2. Mirror Abomasnow decks piloted by tuned heuristics (bench race).
  3. Empty-bench collapses = >55% of losses for BOTH the policy and v44.

v44 preates Crustle only via Boss-gust, but the trolley34w deck carries
NO gust card, so that mechanism is dead. This wrapper adds the missing
plan: when walled, bring Kyogre forward (play it, charge it to 3 energy
on the Bench, retreat into it, promote it after a KO).

The wrapper only fires when damage_prevented(active, opp_active) is true,
so all other matchups run the untouched champion logic.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_base():
    for cand in (os.path.join(_HERE, "c87_v44.py"), os.path.join(_HERE, "main.py"),
                 os.path.join(os.getcwd(), "agents", "c87_v44.py")):
        if os.path.exists(cand):
            spec = importlib.util.spec_from_file_location("_v61_base", cand)
            mod = importlib.util.module_from_spec(spec)
            sys.modules.setdefault("_v61_base", mod)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError("base agent not found")


_B = _load_base()
_base_agent = _B.agent

KYOGRE = 721
SWIRLING_WAVES = 1043

DECK = getattr(_B, "DECK", [])


def _build_plan(deck):
    plan = _B._build_plan(deck)
    _B.PLAN = plan
    _B.DECK = list(deck)
    return plan


PLAN = getattr(_B, "PLAN", None)


def _walled(obs, me, opp):
    try:
        a = _B._active(obs, me)
        o = _B._active(obs, opp)
        if not a or not o:
            return False
        return bool(_B.damage_prevented(a.get("id"), o.get("id"), 10 ** 6))
    except Exception:
        return False


def _kyogre_bench_slot(obs, me):
    """(slot, energies) of our benched Kyogre or (None, 0)."""
    try:
        bench = _B._bench(obs, me) or []
        for i, p in enumerate(bench):
            if p and p.get("id") == KYOGRE:
                return i, len(p.get("energies") or [])
    except Exception:
        pass
    return None, 0


def _board_has_kyogre(obs, me):
    try:
        a = _B._active(obs, me)
        if a and a.get("id") == KYOGRE:
            return True
        slot, _ = _kyogre_bench_slot(obs, me)
        return slot is not None
    except Exception:
        return False


def agent(obs: dict) -> list[int]:
    dec = _base_agent(obs)
    try:
        cur = obs.get("current") or {}
        if cur.get("result") is not None:
            return dec
        me = int(cur.get("yourIndex", 0))
        opp = 1 - me
        sel = obs.get("select") or {}
        opts = sel.get("option") or []
        if not opts:
            return dec

        # --- promotion after a KO: bring Kyogre up when walled ---------
        if int(sel.get("type") or -1) == 1 and int(sel.get("context") or -1) == 4:
            try:
                act = _B._active(obs, me)
                opp_act = _B._active(obs, opp)
                if act is None and opp_act is not None and _walled_obs_card(obs, opp_act):
                    for i, o in enumerate(opts):
                        if o.get("type") == 3 and o.get("area") == 5:
                            slot = o.get("index")
                            bench = _B._bench(obs, me) or []
                            if slot is not None and 0 <= slot < len(bench) \
                                    and bench[slot] and bench[slot].get("id") == KYOGRE:
                                return [i]
            except Exception:
                pass
            return dec

        if int(sel.get("type") or -1) != 0:
            return dec
        if not _walled(obs, me, opp):
            return dec

        # --- walled: execute the Kyogre plan ----------------------------
        slot, kyo_e = _kyogre_bench_slot(obs, me)
        if slot is None and not _board_has_kyogre(obs, me):
            # play Kyogre from hand
            players = cur.get("players") or []
            hand = (players[me].get("hand") or []) if me < len(players) else []
            for i, o in enumerate(opts):
                if o.get("type") == 7:
                    idx = o.get("index")
                    if idx is not None and 0 <= idx < len(hand) \
                            and (hand[idx] or {}).get("id") == KYOGRE:
                        return [i]
            return dec
        if slot is not None and kyo_e < 3:
            for i, o in enumerate(opts):
                if o.get("type") == 8 and o.get("inPlayArea") == 5 \
                        and o.get("inPlayIndex") == slot:
                    return [i]
            return dec
        if slot is not None and kyo_e >= 3:
            act = _B._active(obs, me)
            if not (act and act.get("id") == KYOGRE):
                for i, o in enumerate(opts):
                    if o.get("type") == 12:  # RETREAT
                        return [i]
            return dec
        # Kyogre already active: prefer Swirling Waves
        for i, o in enumerate(opts):
            if o.get("type") == 13 and o.get("attackId") == SWIRLING_WAVES:
                return [i]
        return dec
    except Exception:
        return dec


def _walled_obs_card(obs, opp_act) -> bool:
    """True when the opposing active is a known wall card class."""
    try:
        return bool((_B.card(opp_act.get("id")) or {}).get("pv"))
    except Exception:
        return False
