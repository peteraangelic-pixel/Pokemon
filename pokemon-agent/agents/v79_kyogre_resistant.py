#!/usr/bin/env python3
"""v79: Kyogre resistant - take Kyogre deck c87_v44 with bench guard from v70

Kyogre deck: 4x Abomasnow 723, 4x Snover 722, 2x Kyogre 721, plus supporters
Loss analysis for Kyogre v63: 76 ep 31W-45L, vs KYOGRE 12W-16L, vs ? 6W-18L
Same wipe problem: early T5-T9 losses with board 1

Apply v70 bench logic to Kyogre:
- board<=1 always bench
- board<=2 turn<=8 or prizes<=4 bench
- promotion: prefer Abomasnow 723 (350 HP) > Kyogre 721 (150) > Snover 722 (90)
- recovery: Night Stretcher/Sacred Ash when board<=2
"""
from __future__ import annotations
import json, os

DECK_KYOGRE = [
    3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,  # 40 Water Energy? Actually 3 is Basic Water
    721,721,  # Kyogre 2
    722,722,722,722,  # Snover 4
    723,723,723,723,  # Abomasnow 4
    1227,1227,1227,1227,  # Lillie Determination 4
    1145,1145,1145,1145,  # Mega Signal 4
    1235,  # Waitress 1
    1158,  # Maximum Belt 1
    1152,  # Poke Pad 1
    1097,  # Night Stretcher 1
    1121,1121,  # Ultra Ball 2
    1152,  # Pad extra
    1207,  # Amarys 1
    1121,1121,  # Ultra Ball 2 more
    1262,  # Surfing Beach 1
]
# Actually need exactly 60, let's use known good Kyogre deck c87_v44.csv
# Load from file if exists
import pathlib
_p = pathlib.Path(__file__).parent.parent / "decks" / "c87_v44.csv"
if _p.exists():
    try:
        DECK_KYOGRE = [int(x) for x in _p.read_text().split() if x.strip().isdigit()]
    except:
        pass
DECK = DECK_KYOGRE

ABOMASNOW = 723
SNOVER = 722
KYOGRE = 721

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
                except:
                    pass
    return _CI
def _card(cid): return _index()["cards"].get(str(cid)) or {}
def _poke_list(player, zone):
    v = (player or {}).get(zone)
    if v is None: return []
    if isinstance(v, dict): return [v]
    return [p for p in v if p]
def _active(player):
    lst=_poke_list(player,"active")
    return lst[0] if lst else None
def _bench(player): return _poke_list(player,"bench")
def _board(player):
    a=_active(player)
    return ([a] if a else [])+_bench(player)
def _hp(poke): return int((poke or {}).get("hp") or 0)
def _hand_ids(player): return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]
def _opt_hand_card(opt, player):
    idx=opt.get("index")
    if idx is None: return None
    hand=(player or {}).get("hand") or []
    if 0<=idx<len(hand):
        return (hand[idx] or {}).get("id")
    return None

def agent(obs: dict) -> list[int]:
    try:
        sel=obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return list(DECK)
        cur=obs.get("current") or {}
        players=cur.get("players") or []
        me=int(cur.get("yourIndex",0))
        if len(players)<2 or me>=len(players):
            return [0]
        me_p,opp_p=players[me],players[1-me]
        opts=sel.get("option") or []
        if not opts:
            return []
        stype=int(sel.get("type") or -1)
        hand=_hand_ids(me_p)
        turn=int(cur.get("turn") or 0)
        our_prizes=6
        try:
            if isinstance(me_p.get("prize"), list):
                our_prizes=len(me_p.get("prize"))
        except:
            pass
        board=_board(me_p)
        board_n=len(board)

        if stype==0:
            # bench discipline for Kyogre
            need=False
            if board_n<=1:
                need=True
            elif board_n<=2 and (turn<=8 or our_prizes<=4):
                need=True
            if need:
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            return [i]
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1086,1152,1121):
                        return [i]
            # recovery
            if board_n<=2:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1097,1129):
                        return [i]
            return [0]

        def _score(o):
            s=0
            if o.get("type")==3:
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=p.get("id")
                        if board_n<=2:
                            if pid==ABOMASNOW:
                                s=130
                            elif pid==KYOGRE:
                                s=100
                            elif pid==SNOVER:
                                s=60
                            else:
                                s=20
                        else:
                            s={ABOMASNOW:100, KYOGRE:80, SNOVER:50}.get(pid,20)
                        s+=_hp(p)/10
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                    s={ABOMASNOW:100, KYOGRE:80, SNOVER:60}.get(cid,20)
            return s
        ranked=sorted(range(len(opts)), key=lambda i: -_score(opts[i]))
        k=int(sel.get("minCount") or 1)
        return sorted(ranked[:max(1,k)])
    except Exception:
        try:
            n=len((obs.get("select") or {}).get("option") or [])
            return [0] if n else []
        except:
            return []
