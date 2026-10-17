#!/usr/bin/env python3
"""v72: Alakazam ultra bench discipline - resistant to wipe losses.

Based on detailed loss analysis 2026-10-17:
- 71 losses: 21 empty (29.6%) +21 single (29.6%) +9 double (12.7%) = 59% bench wipe related
- Avg turn 14.28, many early T7-11
- Dominant vs KYOGRE 24, ? 20 (Crustle/Kangaskhan wall), MEOWTH+FEZ 11

Fixes vs v70:
- Bench guard threshold: board<=3 and prizes<=4 (was <=2 and <=3) — triggers earlier
- Poffin (1086) + Nest Ball (1152) boosted when board<=3 (search for basics)
- Recovery Night Stretcher (1097) + Sacred Ash (1129) boosted when board<=3 (was <=2)
- No Abra promotion when board<=3 (was <=2)
- Hand refill thresh 5 (was 4) vs Kyogre 350 HP needs 18 cards for 360 dmg (20*18)
- In main phase, if board<=3, prioritize benching basic over attacking, unless attack wins prize
- Boss KO margin increased to 20 when board small to avoid risky Boss
- Also add Buddy Buddy Poffin logic: if hand has Poffin and board<=3, always use Poffin first

Deck same simple 11E 4x Alakazam.
"""
from __future__ import annotations
import json, os

DECK_SIMPLE = [
    5,5,5,5,5,13,5,19,19,19,19,66,66,66,140,305,305,305,305,741,741,741,741,742,742,742,742,743,743,743,743,
    1079,1079,1079,1079,1081,1081,1086,1086,1086,1086,1097,1097,1129,1152,1152,1152,1152,1182,1182,1182,1184,1225,1225,1225,1231,1231,1231,1264,1264
]
DECK = DECK_SIMPLE

ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE = 305, 66
FEZAN = 140
ENERGY_IDS = {5, 13, 19}
POFFIN = 1086
NEST_BALL = 1152
NIGHT_STRETCHER = 1097
SACRED_ASH = 1129
BOSS = 1182
DAWN = 1231
HILDA = 1225
RARE_CANDY = 1079

_CI=None
def _index():
    global _CI
    if _CI is None:
        _CI={"cards":{}, "attacks":{}}
        here=os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
        for d in (here, os.getcwd(), "tools", os.path.join(os.getcwd(),"tools"), "/kaggle_simulations/agent", os.path.join(os.getcwd(),"assets"), "assets"):
            p=os.path.join(d,"card_index.json")
            if d and os.path.exists(p):
                try:
                    _CI=json.load(open(p))
                    break
                except:
                    pass
    return _CI
def _card(cid): return _index()["cards"].get(str(cid)) or {}
def _attack(aid): return _index()["attacks"].get(str(aid)) or {}
def _poke_list(player, zone):
    v=(player or {}).get(zone)
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
def _energies(poke):
    if not poke: return 0
    e=poke.get("energies")
    if isinstance(e,list): return len(e)
    ec=poke.get("energyCards")
    return len(ec) if isinstance(ec,list) else 0
def _hp(poke): return int((poke or {}).get("hp") or 0)
def _hand_ids(player): return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]
def _atk_damage(poke, aid, hand_n):
    a=_attack(aid)
    d=int(a.get("d") or 0)
    if d>0: return d
    name=a.get("n") or ""
    if name=="Powerful Hand": return 20*hand_n
    if name=="Cruel Arrow": return 30
    return 0
def _best_damage(poke, hand_n):
    best=0
    for aid in (_card(poke.get("id")).get("atk") or []) if poke else []:
        d=_atk_damage(poke, aid, hand_n)
        if d>=best:
            best=d
    return best
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
        _st=sel.get("type")
        stype=int(_st) if _st is not None else -1
        hand=_hand_ids(me_p)

        # prize counts
        our_prizes=6
        opp_prizes=6
        try:
            if isinstance(me_p.get("prize"), list):
                our_prizes=len(me_p.get("prize"))
            if isinstance(opp_p.get("prize"), list):
                opp_prizes=len(opp_p.get("prize"))
        except:
            pass
        board=_board(me_p)
        board_n=len(board)
        hand_n=len([h for h in hand if h is not None])

        # ultra bench guard thresholds
        BENCH_GUARD_BOARD=3
        BENCH_GUARD_PRIZE=4
        in_endgame = board_n<=BENCH_GUARD_BOARD and (our_prizes<=BENCH_GUARD_PRIZE or opp_prizes<=BENCH_GUARD_PRIZE)
        in_risk = board_n<=3

        if stype==0:
            # 1) always evo to Alakazam
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ALAKAZAM:
                    return [i]
            # 2) Rare Candy
            if ALAKAZAM in hand and any(p.get("id")==ABRA for p in board):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==RARE_CANDY:
                        return [i]
            # 3) ULTRA BENCH DISCIPLINE: board<=3 prizes<=4 -> must bench basic
            if in_endgame or in_risk:
                # Poffin first to search
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==POFFIN:
                        return [i]
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==NEST_BALL:
                        return [i]
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            return [i]
                # if no basic, try recovery to get basic back
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (NIGHT_STRETCHER, SACRED_ASH):
                        return [i]
            # 4) hand refill when <=5 (was 4) vs Kyogre 350 needs 18 cards
            if hand_n<=5:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (DAWN, HILDA):
                        return [i]
            # 5) Boss KO with larger margin when small board
            act=_active(me_p)
            if act is not None:
                dmg=_best_damage(act, hand_n)
                if dmg>0:
                    margin = 20 if in_risk else 10
                    for b in _bench(opp_p):
                        if 0<_hp(b)<=dmg+margin:
                            for i,o in enumerate(opts):
                                if o.get("type")==7 and _opt_hand_card(o, me_p)==BOSS:
                                    # avoid Boss if it would leave us with 1 bench and opp has 5
                                    if not (in_endgame and board_n<=2):
                                        return [i]
            # 6) recovery when board <=3 (was <=2)
            if board_n<=3:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (NIGHT_STRETCHER, SACRED_ASH):
                        return [i]
            # 7) don't attack before setup
            if opts[0].get("type")==13:
                for i,o in enumerate(opts):
                    if o.get("type")==9:
                        return [i]
                if act and _energies(act)==0:
                    for i,o in enumerate(opts):
                        if o.get("type")==8 and o.get("inPlayArea")==4:
                            return [i]
            return [0]

        # non-main: promotion / search
        def _opt_score(o):
            s=0
            if o.get("type")==3:
                cid=None
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=p.get("id")
                        if board_n<=3 and (our_prizes<=4 or opp_prizes<=4):
                            if pid==ABRA:
                                s=-100
                            elif pid==ALAKAZAM:
                                s=130
                            elif pid==DUDUNSPARCE:
                                s=120
                            elif pid==DUNSPARCE:
                                s=70
                            else:
                                s=40
                        else:
                            s={ALAKAZAM:100, KADABRA:60, DUDUNSPARCE:55, ABRA:30, DUNSPARCE:35}.get(pid,20)
                        s+=min(_energies(p),2)*8 + _hp(p)/20.0
                elif area==4:
                    p=_active(me_p)
                    if p:
                        s={ALAKAZAM:100, KADABRA:60, DUDUNSPARCE:55}.get(p.get("id"),30)
                elif area==2 and idx is not None:
                    cid=hand[idx] if 0<=idx<len(hand) else None
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                if cid is not None:
                    if board_n<=3 and (our_prizes<=4 or opp_prizes<=4):
                        if cid in (NIGHT_STRETCHER, SACRED_ASH):
                            s=100
                        elif cid==ALAKAZAM:
                            s=110
                        elif cid==POFFIN:
                            s=105
                        elif cid==NEST_BALL:
                            s=100
                        elif cid==ABRA:
                            s=80
                        elif cid==DUNSPARCE:
                            s=75
                        else:
                            s=35
                    else:
                        s={ALAKAZAM:100, KADABRA:80, ABRA:70, DUDUNSPARCE:55, DUNSPARCE:50, RARE_CANDY:40, POFFIN:45, NEST_BALL:40}.get(cid,25)
                    if cid in ENERGY_IDS:
                        mine=_board(me_p)
                        loaded=sum(_energies(p) for p in mine)
                        s=70 if loaded<len(mine) else 15
            elif o.get("type")==1:
                s=10
            return s

        ranked=sorted(range(len(opts)), key=lambda i: -_opt_score(opts[i]))
        k=int(sel.get("minCount") or 1)
        k=max(1, min(k, len(opts)))
        return sorted(ranked[:k])
    except Exception:
        try:
            n=len((obs.get("select") or {}).get("option") or [])
            return [0] if n else []
        except:
            return []
