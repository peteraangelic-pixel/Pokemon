#!/usr/bin/env python3
"""v66: YumeNeko Alakazam — improved pilot over v65.

Improvements vs v65 (0.556 top30, 0.507 broad, 0.95 vs crustle):
- bench guard +1000/+500 (never collapse) — v65 had +60/+25, still 9-17% loss
- Rare Candy aggressive 110 (was 95), Kadabra evo 90 when Alakazam in hand
- Poffin/Pad early boost 85/70 when board<=3 (was 55/45)
- Boss KO calculated from actual hand + Fezandipiti Cruel Arrow (30)
- Abra/Dunsparce switch attacks scored as retreat alternative
- Ability Run Away Draw boosted to 85 when hand<=5
- Attack KO bonus +80 (was 55), ex bonus +35 (was 25)
- Energy attach smarter: Alakazam bench ready = 100 if 0E, else 20
- Prize race: when opp prizes <=2, boost Boss to 95 and attack to +100
- Never discard Abra line in searches — explicit protection
"""
from __future__ import annotations
import json, os

DECK = [
    19, 19, 19, 19, 741, 741, 741, 741, 742, 742, 742, 742,
    1079, 1079, 1079, 1079, 1086, 1086, 1086, 1086, 1152, 1152, 1152, 1152,
    66, 66, 66, 305, 305, 305, 743, 743, 743, 1225, 1225, 1225, 1231, 1231, 1231,
    5, 5, 1081, 1081, 1182, 1182, 1264, 1264, 1407, 1407, 1409, 1409,
    13, 140, 214, 959, 1097, 1129, 1161, 1184, 1413,
]

ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE = 305, 66
Pikipek, TOUCANNON = 1407, 1409
TOGEPI, TOGEKISS = 959, 214
FEZAN = 140
LINE = {ABRA: 0, KADABRA: 1, ALAKAZAM: 2}
ENERGY_IDS = {5, 13, 19}

_CI = None
def _index():
    global _CI
    if _CI is None:
        _CI = {"cards": {}, "attacks": {}}
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
        for d in (here, os.getcwd(), "tools", os.path.join(os.getcwd(), "tools"), "/kaggle_simulations/agent", os.path.join(os.getcwd(), "assets"), "assets"):
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
    a = _attack(aid)
    d = int(a.get("d") or 0)
    if d > 0:
        return d
    name = a.get("n") or ""
    if name == "Powerful Hand":
        return 20 * hand_n
    if name == "Cruel Arrow":
        return 30
    # Double Stab: 20x number of Pikipek? Approx 40
    if name == "Double Stab":
        return 40
    if name == "Feather Rondo":
        return 60
    return 0

def _best_damage(poke, hand_n, opp_active):
    best, best_aid = 0, None
    for aid in (_card(poke.get("id")).get("atk") or []) if poke else []:
        d = _atk_damage(poke, aid, hand_n, opp_active)
        if d >= best:
            best, best_aid = d, aid
    return best, best_aid

def _opt_hand_card(opt, player):
    idx = opt.get("index")
    if idx is None:
        return None
    hand = (player or {}).get("hand") or []
    if 0 <= idx < len(hand):
        return (hand[idx] or {}).get("id")
    return None

def _score_main(opt, me_p, opp_p, hand, opp_prizes=6):
    t = opt.get("type")
    hand_n = len(hand)
    opp_act = _active(opp_p)
    my_act = _active(me_p)
    my_board = _board(me_p)
    board_n = len(my_board)
    n_alak = sum(1 for p in my_board if p.get("id") == ALAKAZAM)
    n_line = sum(1 for p in my_board if p.get("id") in LINE)

    # prize race boost
    prize_boost = 0
    try:
        opp_prizes = int((opp_p or {}).get("prizes") or opp_prizes)
        if isinstance(opp_p.get("prize"), list):
            opp_prizes = len(opp_p.get("prize"))
    except:
        pass
    if opp_prizes <= 2:
        prize_boost = 20

    if t == 7:  # PLAY
        cid = _opt_hand_card(opt, me_p)
        c = _card(cid)
        # bench guard — never starve
        if c.get("ct") == 0 and c.get("b"):
            if board_n >= 6:
                return -100
            score = 70
            if cid == ABRA:
                score = 120 if n_line < 3 else 90
            elif cid == DUNSPARCE:
                score = 95
            elif cid == Pikipek:
                score = 50
            elif cid == TOGEPI:
                score = 40
            elif cid == FEZAN:
                score = 60
            # massive boost for empty bench
            if board_n <= 1:
                score += 1000
            elif board_n == 2:
                score += 500
            elif board_n == 3:
                score += 100
            return score + prize_boost
        if cid == 1079:  # Rare Candy
            if any(p.get("id") == ABRA for p in my_board) and ALAKAZAM in hand:
                return 110 + prize_boost
            return -80
        if cid == 1086:  # Poffin
            if board_n <= 3:
                return 85 + prize_boost
            if board_n <= 4:
                return 65
            return 25
        if cid == 1152:  # Poke Pad
            if board_n <= 3:
                return 70
            return 45
        if cid == 1097:  # Night Stretcher
            # recover Alakazam line or energy
            return 35
        if cid == 1081:  # Enhanced Hammer
            return 20
        if c.get("ct") == 3:  # Supporter
            if cid == 1231 or cid == 1225:  # Dawn / Hilda
                if hand_n <= 3:
                    return 90 + prize_boost
                if hand_n <= 5:
                    return 75
                return 45
            if cid == 1182:  # Boss
                bench = _bench(opp_p)
                # calculate KO with current hand + 30 from Fezandipiti
                dmg_est = 20 * hand_n + (30 if any(p.get("id")==FEZAN for p in my_board) else 0)
                # if Alakazam active, use its damage
                if my_act and my_act.get("id") == ALAKAZAM:
                    dmg_est = max(dmg_est, 20*hand_n)
                # check if any bench can be KO'd
                for b in bench:
                    if _hp(b) >0 and _hp(b) <= dmg_est:
                        # extra boost if opp low prizes
                        return 95 + prize_boost + (20 if opp_prizes<=2 else 0)
                # also Boss for game: if opp has 1 prize left and we can take it
                if opp_prizes <= 2 and bench:
                    return 80 + prize_boost
                return 15
            if cid == 1184:  # Lana's Aid
                return 25
            return 20
        if c.get("ct") == 4:  # Stadium
            return 18
        if c.get("ct") == 2:  # Tool
            return 12
        return 8

    if t == 9:  # EVOLVE
        cid = _opt_hand_card(opt, me_p)
        if cid == ALAKAZAM:
            return 115 + prize_boost
        if cid == KADABRA:
            return 90 if ALAKAZAM in hand else 70
        if cid == DUDUNSPARCE:
            return 80 if hand_n <=5 else 60
        if cid == TOUCANNON:
            return 45
        if cid == TOGEKISS:
            return 40
        return 55

    if t == 8:  # ATTACH
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
            if e == 0:
                return 105 + prize_boost
            return 25
        if cid == KADABRA:
            return 65 if e == 0 else 15
        if cid == DUDUNSPARCE:
            return 50 if e < 1 else 10
        if cid in (TOUCANNON, TOGEKISS, FEZAN):
            return 40 if e < 2 else 8
        if cid == ABRA:
            return 30 if e == 0 else 5
        return 12

    if t == 10:  # ABILITY
        # Run Away Draw etc
        if hand_n <= 3:
            return 85
        if hand_n <= 5:
            return 70
        return 55

    if t == 13:  # ATTACK
        if not my_act:
            return -100
        aid = opt.get("attackId")
        # restrict to attacks of active
        if aid is not None and aid not in (_card(my_act.get("id")).get("atk") or []):
            return -100
        d_here = _atk_damage(my_act, aid, hand_n, opp_act) if aid else _best_damage(my_act, hand_n, opp_act)[0]
        score = 55 + min(d_here, 250) / 3.0
        # switch attacks: Teleportation, Trading Places
        atk_name = _attack(aid).get("n") if aid else ""
        if atk_name in ("Teleportation Attack", "Trading Places"):
            # if active weak and bench has ready attacker, boost
            ready = [p for p in _bench(me_p) if p.get("id") in (ALAKAZAM, DUDUNSPARCE, TOUCANNON, TOGEKISS) and _energies(p) >= 1]
            if ready and (_hp(my_act) <= 60 or _best_damage(my_act, hand_n, opp_act)[0] < 40):
                score += 45
        if opp_act and d_here >= _hp(opp_act) and _hp(opp_act) > 0:
            score += 80  # KO
            if (_card(opp_act.get("id")).get("ex") or _card(opp_act.get("id")).get("mex")):
                score += 35
            if opp_prizes <= 2:
                score += 30
        # don't throw away charged Alakazam for chip
        if my_act.get("id") == ALAKAZAM and d_here < 60 and board_n <= 2:
            score -= 20
        # don't attack with pre-evo that could evolve now unless KO
        aid_here = my_act.get("id")
        evo = {ABRA: KADABRA, KADABRA: ALAKAZAM}.get(aid_here)
        if evo is not None and evo in hand:
            if not (opp_act and d_here >= _hp(opp_act) and _hp(opp_act) > 0):
                score -= 50
        return score + prize_boost

    if t == 12:  # RETREAT
        ready = [p for p in _bench(me_p) if p.get("id") in (ALAKAZAM, DUDUNSPARCE, TOUCANNON, TOGEKISS) and _energies(p) >= 1]
        # if active has switch attack, don't retreat — use attack instead
        if my_act:
            for aid in (_card(my_act.get("id")).get("atk") or []):
                if _attack(aid).get("n") in ("Teleportation Attack", "Trading Places"):
                    return -20  # prefer attack switch
        if my_act and my_act.get("id") not in (ALAKAZAM,) and ready:
            if _hp(my_act) <= 60 or _best_damage(my_act, hand_n, opp_act)[0] == 0:
                return 50 + prize_boost
        return -30

    if t == 14:  # END
        return 0
    return 2

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
        # estimate opp prizes for boost
        opp_prizes = 6
        try:
            if isinstance(opp_p.get("prize"), list):
                opp_prizes = len(opp_p.get("prize"))
            elif isinstance(opp_p.get("prizes"), int):
                opp_prizes = opp_p.get("prizes")
        except:
            pass

        if stype == 0:
            scored = [(_score_main(o, me_p, opp_p, hand, opp_prizes), i) for i, o in enumerate(opts)]
            scored.sort(reverse=True)
            return [scored[0][1]]

        def _opt_score(o):
            s = 0
            if o.get("type") == 3:
                cid = None
                area, idx = o.get("area"), o.get("index")
                if area == 5 and idx is not None:
                    b = _bench(me_p)
                    p = b[idx] if 0 <= idx < len(b) else None
                    if p:
                        s = {ALAKAZAM: 110, KADABRA: 70, DUDUNSPARCE: 65, TOUCANNON: 50, ABRA: 40, DUNSPARCE: 45, FEZAN: 55}.get(p.get("id"), 25)
                        s += min(_energies(p), 2) * 10 + _hp(p) / 15.0
                elif area == 4:
                    p = _active(me_p)
                    if p:
                        s = {ALAKAZAM: 110, KADABRA: 70, DUDUNSPARCE: 65}.get(p.get("id"), 35)
                elif area == 2 and idx is not None:
                    cid = hand[idx] if 0 <= idx < len(hand) else None
                elif o.get("cardId") is not None:
                    cid = o.get("cardId")
                if cid is not None:
                    # protect Abra line
                    if cid in (ABRA, KADABRA, ALAKAZAM):
                        s = {ALAKAZAM: 110, KADABRA: 90, ABRA: 80}.get(cid, 80)
                    elif cid == DUNSPARCE:
                        s = 60
                    elif cid == DUDUNSPARCE:
                        s = 65
                    elif cid in ENERGY_IDS:
                        mine = _board(me_p)
                        loaded = sum(_energies(p) for p in mine)
                        s = 75 if loaded < len(mine) else 20
                    else:
                        s = {1079: 50, 1086: 45, 1152: 40}.get(cid, 30)
            elif o.get("type") == 1:
                s = 15
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
