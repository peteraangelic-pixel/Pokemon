#!/usr/bin/env python3
"""v61 policy-hardened = c87 learned policy (0.477 local vs champion) +
behavioural guards against the failure modes seen in its Kaggle replays
(344.9 pts): famine (80% of games ended with <=1 Pokemon on board),
9 early collapses in turns 3-4, zero retreats, and the Crustle-wall wall.

Guards fire only in narrow, catastrophic states:
  G1 bench development: in the main phase, if our board has <=1 Pokemon
     and a PLAY option puts a Basic Pokemon on the bench, take it instead
     of ending the turn / attacking with the lone Pokemon.
  G2 wall answer: if the opposing Active is a 'pv' wall card (Crustle)
     and our Active is Mega Abomasnow ex (fully blocked), prefer a
     benched Kyogre: charge it, retreat into it, promote it after a KO.
  G3 promotion: after our Active is KO'd while facing a wall, promote
     Kyogre when available.

Everything else is the untouched learned policy.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_base():
    for cand in (os.path.join(_HERE, "c87_policy_v59_10k.py"),
                 os.path.join(os.getcwd(), "agents", "c87_policy_v59_10k.py")):
        if os.path.exists(cand):
            spec = importlib.util.spec_from_file_location("_v61p_base", cand)
            mod = importlib.util.module_from_spec(spec)
            sys.modules.setdefault("_v61p_base", mod)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError("policy base not found")


_P = _load_base()
_policy_agent = _P.agent
_FZ = getattr(_P, "_FZ", None) or getattr(_P, "_F", None)

KYOGRE = 721
ABOMASNOW_EX = 723


def _card(cid):
    try:
        return _FZ.card(cid) or {}
    except Exception:
        return {}


def _is_basic_poke(cid):
    c = _card(cid)
    return bool(c.get("b")) and c.get("ct") == 0


def _board(obs, me):
    cur = obs.get("current") or {}
    players = cur.get("players") or []
    if me >= len(players):
        return [], []
    p = players[me] or {}
    act = (p.get("active") or [None])
    bench = [b for b in (p.get("bench") or []) if b]
    return (act[0] if act else None), bench


def agent(obs: dict) -> list[int]:
    dec = _policy_agent(obs)
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
        players = cur.get("players") or []
        if len(players) < 2:
            return dec
        my_act, my_bench = _board(obs, me)
        opp_act, _ = _board(obs, opp)
        board_n = (1 if my_act else 0) + len(my_bench)

        # G3: promotion after KO, wall ahead -> Kyogre
        if int(sel.get("type") or -1) == 1 and int(sel.get("context") or -1) == 4 \
                and my_act is None and opp_act is not None and _card(opp_act.get("id")).get("pv"):
            bench = (players[me].get("bench") or [])
            for i, o in enumerate(opts):
                if o.get("type") == 3 and o.get("area") == 5:
                    slot = o.get("index")
                    if slot is not None and 0 <= slot < len(bench) \
                            and (bench[slot] or {}).get("id") == KYOGRE:
                        return [i]
            return dec

        if int(sel.get("type") or -1) != 0:
            return dec

        # G2: wall answer
        if opp_act is not None and my_act is not None \
                and my_act.get("id") == ABOMASNOW_EX and _card(opp_act.get("id")).get("pv"):
            # find benched Kyogre
            kyo_slot, kyo_e = None, 0
            for i, b in enumerate(my_bench):
                if b.get("id") == KYOGRE:
                    kyo_slot, kyo_e = i, len(b.get("energies") or [])
                    break
            if kyo_slot is not None and kyo_e < 3:
                for i, o in enumerate(opts):
                    if o.get("type") == 8 and o.get("inPlayArea") == 5 \
                            and o.get("inPlayIndex") == kyo_slot:
                        return [i]
            if kyo_slot is not None and kyo_e >= 3:
                for i, o in enumerate(opts):
                    if o.get("type") == 12:
                        return [i]
            if kyo_slot is None:
                # play Kyogre from hand
                hand = players[me].get("hand") or []
                for i, o in enumerate(opts):
                    if o.get("type") == 7:
                        idx = o.get("index")
                        if idx is not None and 0 <= idx < len(hand) \
                                and (hand[idx] or {}).get("id") == KYOGRE:
                            return [i]

        # G1: never idle on a starved board in the main phase
        if board_n <= 1 and int(sel.get("maxCount") or 1) == 1:
            hand = players[me].get("hand") or []
            has_end_or_attack = any(o.get("type") in (13, 14) for o in opts)
            if has_end_or_attack:
                for i, o in enumerate(opts):
                    if o.get("type") == 7 and o.get("area") is None:
                        idx = o.get("index")
                        if idx is not None and 0 <= idx < len(hand) \
                                and _is_basic_poke((hand[idx] or {}).get("id")):
                            return [i]
        return dec
    except Exception:
        return dec
