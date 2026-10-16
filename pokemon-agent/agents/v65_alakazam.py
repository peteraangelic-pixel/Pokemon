#!/usr/bin/env python3
"""v65: dedicated pilot for the YumeNeko (#1, 1352.9) Alakazam list.

The generic champion scorer cannot play this deck (0.012): it values
Powerful Hand at 0, has no Rare Candy plan and no draw-engine concept.
This pilot is explicit about the deck's actual game plan:

  - flood the bench with Abra/Dunsparce (Poffin finds them),
  - evolve to Alakazam fast (Rare Candy skips Kadabra),
  - keep the hand BIG (Powerful Hand = 20 dmg per card in hand):
    Dawn/Hilda draw, Dudunsparce Run-Away-Draw cycles,
  - Alakazam is a 1-prize non-ex attacker: Crustle walls don't block it,
    and it trades 1-for-2 against ex decks,
  - Boss cheap prizes off the bench; never discard the Abra line.

Written standalone (no champion code): own obs parsing + option scoring.
Returns indices into obs['select']['option'] only.
"""
from __future__ import annotations

import json
import os

# --- deck (YumeNeko list); FFI harness rebinds DECK/PLAN in tests -------
DECK = [
    19, 19, 19, 19, 741, 741, 741, 741, 742, 742, 742, 742,
    1079, 1079, 1079, 1079, 1086, 1086, 1086, 1086, 1152, 1152, 1152, 1152,
    66, 66, 66, 305, 305, 305, 743, 743, 743, 1225, 1225, 1225, 1231, 1231, 1231,
    5, 5, 1081, 1081, 1182, 1182, 1264, 1264, 1407, 1407, 1409, 1409,
    13, 140, 214, 959, 1097, 1129, 1161, 1184, 1413,
]

ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE = 305, 66
PIkipek, TOUCANNON = 1407, 1409
TOGEPI, TOGEKISS = 959, 214
FEZAN = 140
LINE = {ABRA: 0, KADABRA: 1, ALAKAZAM: 2}
PRE = {KADABRA: ABRA, ALAKAZAM: KADABRA}
ENERGY_IDS = {5, 13, 19}  # Basic P, Enriching, Telepath

_CI = None


def _index():
    global _CI
    if _CI is None:
        _CI = {"cards": {}, "attacks": {}}
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
        for d in (here, os.getcwd(), "tools", os.path.join(os.getcwd(), "tools"),
                  "/kaggle_simulations/agent"):
            p = os.path.join(d, "card_index.json")
            if d and os.path.exists(p):
                try:
                    _CI = json.load(open(p))
                    break
                except Exception:
                    pass
    return _CI


def _card(cid):
    return _index()["cards"].get(str(cid)) or {}


def _attack(aid):
    return _index()["attacks"].get(str(aid)) or {}


# --------------------------------------------------------------------------
# obs helpers (active may be dict or [dict]; be liberal)
# --------------------------------------------------------------------------

def _poke_list(player, zone):
    v = (player or {}).get(zone)
    if v is None:
        return []
    if isinstance(v, dict):
        return [v]
    return [p for p in v if p]


def _active(player):
    lst = _poke_list(player, "active")
    return lst[0] if lst else None


def _bench(player):
    return _poke_list(player, "bench")


def _board(player):
    a = _active(player)
    return ([a] if a else []) + _bench(player)


def _energies(poke):
    if not poke:
        return 0
    e = poke.get("energies")
    if isinstance(e, list):
        return len(e)
    ec = poke.get("energyCards")
    return len(ec) if isinstance(ec, list) else 0


def _hp(poke):
    return int((poke or {}).get("hp") or 0)


def _hand_ids(player):
    return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]


def _atk_damage(poke, aid, hand_n, opp_active):
    """Real damage estimate incl. variable attacks of this deck."""
    a = _attack(aid)
    d = int(a.get("d") or 0)
    if d > 0:
        return d
    name = a.get("n") or ""
    if name == "Powerful Hand":
        return 20 * hand_n
    if name == "Cruel Arrow":  # Fezandipiti: counters anywhere, approx
        return 30
    return 0


def _best_damage(poke, hand_n, opp_active):
    best, best_aid = 0, None
    for aid in (_card(poke.get("id")).get("atk") or []) if poke else []:
        d = _atk_damage(poke, aid, hand_n, opp_active)
        if d >= best:
            best, best_aid = d, aid
    return best, best_aid


# --------------------------------------------------------------------------
# option resolution
# --------------------------------------------------------------------------

def _opt_card_in_play(opt, players, me):
    """Pokemon dict targeted by an in-play option (evolve/attach...)."""
    area = opt.get("inPlayArea", opt.get("area"))
    idx = opt.get("inPlayIndex", opt.get("index"))
    if idx is None:
        return None
    owner = me if opt.get("playerIndex") in (None, me) else opt.get("playerIndex")
    try:
        pl = players[owner]
        if area == 4:
            return _active(pl)
        if area == 5:
            b = _bench(pl)
            return b[idx] if 0 <= idx < len(b) else None
    except Exception:
        return None
    return None


def _opt_hand_card(opt, player):
    idx = opt.get("index")
    if idx is None:
        return None
    hand = (player or {}).get("hand") or []
    if 0 <= idx < len(hand):
        return (hand[idx] or {}).get("id")
    return None


# --------------------------------------------------------------------------
# main-phase scoring
# --------------------------------------------------------------------------

def _score_main(opt, me_p, opp_p, hand):
    t = opt.get("type")
    hand_n = len(hand)
    opp_act = _active(opp_p)
    my_act = _active(me_p)
    my_board = _board(me_p)
    board_n = len(my_board)
    n_alak = sum(1 for p in my_board if p.get("id") == ALAKAZAM)
    n_line = sum(1 for p in my_board if p.get("id") in LINE)

    if t == 7:  # PLAY
        cid = _opt_hand_card(opt, me_p)
        c = _card(cid)
        if c.get("ct") == 0 and c.get("b"):  # basic Pokemon -> bench it
            if board_n >= 6:
                return -50
            score = 60
            if cid == ABRA:
                score = 90 if n_line < 3 else 70
            elif cid == DUNSPARCE:
                score = 75
            elif cid == PIkipek:
                score = 40
            if board_n <= 1:
                score += 60  # never starve
            elif board_n == 2:
                score += 25
            return score
        if cid == 1079:  # Rare Candy: only with Abra on board + Alakazam in hand
            if any(p.get("id") == ABRA for p in my_board) and ALAKAZAM in hand:
                return 95
            return -80
        if cid == 1086:  # Buddy-Buddy Poffin (2 basics <=70hp to bench)
            if board_n <= 4 and (hand.count(ABRA) or hand.count(DUNSPARCE)):
                return 55
            return 20
        if cid == 1152:  # Poke Pad: search a Pokemon
            return 45
        if cid == 1097:  # Night Stretcher
            return 25
        if cid == 1081:  # Enhanced Hammer: only if opp has special energy
            return 15
        if c.get("ct") == 3:  # Supporter
            if cid == 1231 or cid == 1225:  # Dawn / Hilda: draw/search
                return 70 if hand_n <= 5 else 40
            if cid == 1182:  # Boss's Orders
                bench = _bench(opp_p)
                if any(_hp(b) <= (20 * hand_n if my_act and my_act.get("id") == ALAKAZAM else 90)
                       for b in bench):
                    return 78
                return 10
            if cid == 1184:  # Lana's Aid
                return 20
            return 15
        if c.get("ct") == 4:  # Stadium Battle Cage
            return 12
        if c.get("ct") == 2:  # Tool Handheld Fan
            return 8
        return 5

    if t == 9:  # EVOLVE
        # result is the evolution card in hand
        cid = _opt_hand_card(opt, me_p)
        if cid == ALAKAZAM:
            return 100
        if cid == KADABRA:
            return 88 if ALAKAZAM in hand else 65
        if cid == DUDUNSPARCE:
            return 72  # draw engine
        if cid == TOUCANNON:
            return 35
        if cid == TOGEKISS:
            return 30
        return 50

    if t == 8:  # ATTACH energy
        tgt = _opt_card_in_play(opt, [me_p, opp_p], 0)
        # inPlayArea/Index describe the target
        area = opt.get("inPlayArea")
        idx = opt.get("inPlayIndex")
        tp = None
        if area == 4:
            tp = my_act
        elif area == 5 and idx is not None:
            b = _bench(me_p)
            tp = b[idx] if 0 <= idx < len(b) else None
        if tp is None:
            return 0
        cid = tp.get("id")
        e = _energies(tp)
        if cid == ALAKAZAM:
            return 96 if e == 0 else 30  # one energy is enough
        if cid == KADABRA:
            return 60 if e == 0 else 10
        if cid in (DUDUNSPARCE, TOUCANNON, TOGEKISS, FEZAN):
            return 45 if e < 2 else 5
        if cid == ABRA:
            return 25 if e == 0 else 0
        return 10

    if t == 10:  # ABILITY
        return 58  # Dudunsparce draw etc: good, but board first

    if t == 13:  # ATTACK
        if not my_act:
            return -100
        dmg, _ = _best_damage(my_act, hand_n, opp_act)
        aid = opt.get("attackId")
        # restrict to attacks of active pokemon
        if aid is not None and aid not in (_card(my_act.get("id")).get("atk") or []):
            return -100
        d_here = _atk_damage(my_act, aid, hand_n, opp_act) if aid else dmg
        score = 50 + min(d_here, 200) / 4.0
        if opp_act and d_here >= _hp(opp_act) and _hp(opp_act) > 0:
            score += 55  # KO -> prize
            if (_card(opp_act.get("id")).get("ex") or _card(opp_act.get("id")).get("mex")):
                score += 25  # 2 prizes
        # tempo: don't throw away a charged Alakazam for chip damage
        if my_act.get("id") == ALAKAZAM and d_here < 60 and board_n <= 2:
            score -= 15
        # never end the turn attacking with a pre-evolution that could
        # evolve right now (unless it takes the KO)
        aid_here = my_act.get("id")
        evo = {ABRA: KADABRA, KADABRA: ALAKAZAM}.get(aid_here)
        if evo is not None and evo in hand:
            if not (opp_act and d_here >= _hp(opp_act) and _hp(opp_act) > 0):
                score -= 45
        return score

    if t == 12:  # RETREAT
        # rotate a spent/weak active to a ready bench attacker
        ready = [p for p in _bench(me_p)
                 if p.get("id") in (ALAKAZAM, DUDUNSPARCE, TOUCANNON, TOGEKISS)
                 and _energies(p) >= 1]
        if my_act and my_act.get("id") not in (ALAKAZAM,) and ready:
            if _hp(my_act) <= 50 or _best_damage(my_act, hand_n, opp_act)[0] == 0:
                return 42
        return -30

    if t == 14:  # END
        return 0
    return 1


def _first_legal(opts, dec):
    if isinstance(dec, list) and dec and all(isinstance(i, int) and 0 <= i < len(opts) for i in dec):
        return dec
    return [0]


def agent(obs: dict) -> list[int]:
    try:
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return list(DECK)
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        me = int(cur.get("yourIndex", 0))
        if len(players) < 2 or me >= len(players):
            return [0]
        me_p, opp_p = players[me], players[1 - me]
        opts = sel.get("option") or []
        if not opts:
            return []
        stype = int(sel.get("type") or -1)
        hand = _hand_ids(me_p)

        if stype == 0:  # main phase
            scored = [(_score_main(o, me_p, opp_p, hand), i) for i, o in enumerate(opts)]
            scored.sort(reverse=True)
            return [scored[0][1]]

        # all non-main selects: score every option, return exactly
        # minCount best (prize takes and searches demand exact counts;
        # returning fewer is an illegal move and kills the game)
        def _opt_score(o):
            s = 0
            if o.get("type") == 3:
                cid = None
                area, idx = o.get("area"), o.get("index")
                if area == 5 and idx is not None:  # bench slot (promotion)
                    b = _bench(me_p)
                    p = b[idx] if 0 <= idx < len(b) else None
                    if p:
                        s = {ALAKAZAM: 100, KADABRA: 60, DUDUNSPARCE: 55,
                             TOUCANNON: 45, ABRA: 30, DUNSPARCE: 35}.get(p.get("id"), 20)
                        s += min(_energies(p), 2) * 8 + _hp(p) / 20.0
                elif area == 4:  # active slot
                    p = _active(me_p)
                    if p:
                        s = {ALAKAZAM: 100, KADABRA: 60, DUDUNSPARCE: 55}.get(p.get("id"), 30)
                elif area == 2 and idx is not None:  # hand card
                    cid = hand[idx] if 0 <= idx < len(hand) else None
                elif o.get("cardId") is not None:
                    cid = o.get("cardId")
                if cid is not None:
                    s = {ALAKAZAM: 100, KADABRA: 80, ABRA: 70, DUDUNSPARCE: 55,
                         DUNSPARCE: 50, 1079: 40}.get(cid, 25)
                    if cid in ENERGY_IDS:
                        mine = _board(me_p)
                        loaded = sum(_energies(p) for p in mine)
                        s = 65 if loaded < len(mine) else 15
            elif o.get("type") == 1:  # YES
                s = 10
            return s

        ranked = sorted(range(len(opts)), key=lambda i: -_opt_score(opts[i]))
        k = int(sel.get("minCount") or 1)
        k = max(1, min(k, len(opts)))
        return sorted(ranked[:k])
    except Exception:
        try:
            n = len((obs.get("select") or {}).get("option") or [])
            return [0] if n else []
        except Exception:
            return []
