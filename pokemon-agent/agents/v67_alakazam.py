#!/usr/bin/env python3
"""v67: YumeNeko Alakazam — v65 + targeted fixes for fast aggro.

Fixes:
- Boss: calculate exact damage 20*hand +30 Fezandipiti, check bench HP
- Hand engine: Hilda/Dawn boost when hand<=4 -> 95, <=6 -> 80
- Switch attacks: Abra Teleportation + Dunsparce Trading Places as retreat alternative +40
- Prize race: when opp prizes <=3, Boss 100 and KO bonus 90
- Keep v65 bench guard (+60/+25) not +1000 to avoid over-benching
- Rare Candy 105 (was 95) to be more aggressive
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
        for d in (here, os.getcwd(), "tools", os.path.join(os.getcwd(), "tools"), "/kaggle_simulations/agent", os.path.join(os.getcwd(), "assets"), "assets", os.getcwd()+"/assets"):
            p = os.path.join(d, "card_index.json")
            if d and os.path.exists(p):
                try:
                    _CI = json.load(open(p))
                    break
                except:
                    pass
    return _CI
def _card(cid): return _index()["cards"].get(str(cid)) or {}
def _attack(aid): return _index()["attacks"].get(str(aid)) or {}

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
def _energies(poke):
    if not poke: return 0
    e=poke.get("energies")
    if isinstance(e,list): return len(e)
    ec=poke.get("energyCards")
    return len(ec) if isinstance(ec,list) else 0
def _hp(poke): return int((poke or {}).get("hp") or 0)
def _hand_ids(player): return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]

def _atk_damage(poke, aid, hand_n, opp_active):
    a=_attack(aid)
    d=int(a.get("d") or 0)
    if d>0: return d
    name=a.get("n") or ""
    if name=="Powerful Hand": return 20*hand_n
    if name=="Cruel Arrow": return 30
    if name=="Double Stab": return 40
    if name=="Feather Rondo": return 60
    return 0

def _best_damage(poke, hand_n, opp_active):
    best,best_aid=0,None
    for aid in (_card(poke.get("id")).get("atk") or []) if poke else []:
        d=_atk_damage(poke, aid, hand_n, opp_active)
        if d>=best:
            best,best_aid=d,aid
    return best,best_aid

def _opt_hand_card(opt, player):
    idx=opt.get("index")
    if idx is None: return None
    hand=(player or {}).get("hand") or []
    if 0<=idx<len(hand):
        return (hand[idx] or {}).get("id")
    return None

def _score_main(opt, me_p, opp_p, hand, opp_prizes=6):
    t=opt.get("type")
    hand_n=len(hand)
    opp_act=_active(opp_p)
    my_act=_active(me_p)
    my_board=_board(me_p)
    board_n=len(my_board)
    n_line=sum(1 for p in my_board if p.get("id") in LINE)

    # prize race
    prize_boost=0
    try:
        if isinstance(opp_p.get("prize"), list):
            opp_prizes=len(opp_p.get("prize"))
    except:
        pass
    if opp_prizes<=3:
        prize_boost=15
    if opp_prizes<=2:
        prize_boost=25

    if t==7: # PLAY
        cid=_opt_hand_card(opt, me_p)
        c=_card(cid)
        if c.get("ct")==0 and c.get("b"):
            if board_n>=6:
                return -50
            score=60
            if cid==ABRA:
                score=90 if n_line<3 else 70
            elif cid==DUNSPARCE:
                score=75
            elif cid==Pikipek:
                score=40
            if board_n<=1:
                score+=60
            elif board_n==2:
                score+=25
            return score+prize_boost
        if cid==1079: # Rare Candy
            if any(p.get("id")==ABRA for p in my_board) and ALAKAZAM in hand:
                return 105+prize_boost
            return -80
        if cid==1086: # Poffin
            if board_n<=4 and (hand.count(ABRA) or hand.count(DUNSPARCE)):
                return 60+prize_boost
            return 22
        if cid==1152: # Pad
            return 48
        if cid==1097: return 28
        if cid==1081: return 18
        if c.get("ct")==3:
            if cid==1231 or cid==1225: # Dawn/Hilda
                if hand_n<=3:
                    return 95+prize_boost
                if hand_n<=5:
                    return 80
                if hand_n<=6:
                    return 55
                return 40
            if cid==1182: # Boss
                bench=_bench(opp_p)
                dmg_est=20*hand_n + (30 if any(p.get("id")==FEZAN for p in my_board) else 0)
                # check bench KO
                for b in bench:
                    if _hp(b)>0 and _hp(b)<=dmg_est:
                        return 100+prize_boost
                # if opp low prizes, Boss is good even without guaranteed KO (disrupt)
                if opp_prizes<=3 and bench:
                    return 85+prize_boost
                return 12
            if cid==1184: return 22
            return 18
        if c.get("ct")==4: return 14
        if c.get("ct")==2: return 10
        return 6

    if t==9: # EVOLVE
        cid=_opt_hand_card(opt, me_p)
        if cid==ALAKAZAM: return 108+prize_boost
        if cid==KADABRA: return 88 if ALAKAZAM in hand else 65
        if cid==DUDUNSPARCE: return 75 if hand_n<=5 else 60
        if cid==TOUCANNON: return 38
        if cid==TOGEKISS: return 33
        return 52

    if t==8: # ATTACH
        area=opt.get("inPlayArea")
        idx=opt.get("inPlayIndex")
        tp=None
        if area==4:
            tp=my_act
        elif area==5 and idx is not None:
            b=_bench(me_p)
            tp=b[idx] if 0<=idx<len(b) else None
        if tp is None: return 0
        cid=tp.get("id")
        e=_energies(tp)
        if cid==ALAKAZAM:
            return 98+prize_boost if e==0 else 28
        if cid==KADABRA:
            return 62 if e==0 else 12
        if cid in (DUDUNSPARCE, TOUCANNON, TOGEKISS, FEZAN):
            return 46 if e<2 else 6
        if cid==ABRA:
            return 26 if e==0 else 0
        return 11

    if t==10: # ABILITY
        if hand_n<=3:
            return 80
        if hand_n<=5:
            return 65
        return 58

    if t==13: # ATTACK
        if not my_act: return -100
        aid=opt.get("attackId")
        if aid is not None and aid not in (_card(my_act.get("id")).get("atk") or []):
            return -100
        d_here=_atk_damage(my_act, aid, hand_n, opp_act) if aid else _best_damage(my_act, hand_n, opp_act)[0]
        score=52 + min(d_here, 220)/4.0
        # switch attacks boost when need to retreat
        atk_name=_attack(aid).get("n") if aid else ""
        if atk_name in ("Teleportation Attack","Trading Places"):
            ready=[p for p in _bench(me_p) if p.get("id") in (ALAKAZAM, DUDUNSPARCE, TOUCANNON, TOGEKISS) and _energies(p)>=1]
            if ready and (_hp(my_act)<=55 or _best_damage(my_act, hand_n, opp_act)[0]<45):
                score+=40
        if opp_act and d_here>=_hp(opp_act) and _hp(opp_act)>0:
            score+=85
            if (_card(opp_act.get("id")).get("ex") or _card(opp_act.get("id")).get("mex")):
                score+=32
            if opp_prizes<=2:
                score+=28
        if my_act.get("id")==ALAKAZAM and d_here<60 and board_n<=2:
            score-=15
        aid_here=my_act.get("id")
        evo={ABRA:KADABRA, KADABRA:ALAKAZAM}.get(aid_here)
        if evo is not None and evo in hand:
            if not (opp_act and d_here>=_hp(opp_act) and _hp(opp_act)>0):
                score-=45
        return score+prize_boost

    if t==12: # RETREAT
        # if active has switch attack, prefer attack over retreat
        if my_act:
            for aid in (_card(my_act.get("id")).get("atk") or []):
                if _attack(aid).get("n") in ("Teleportation Attack","Trading Places"):
                    return -25
        ready=[p for p in _bench(me_p) if p.get("id") in (ALAKAZAM, DUDUNSPARCE, TOUCANNON, TOGEKISS) and _energies(p)>=1]
        if my_act and my_act.get("id") not in (ALAKAZAM,) and ready:
            if _hp(my_act)<=55 or _best_damage(my_act, hand_n, opp_act)[0]==0:
                return 48+prize_boost
        return -30

    if t==14:
        return 0
    return 1

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
        opp_prizes=6
        try:
            if isinstance(opp_p.get("prize"), list):
                opp_prizes=len(opp_p.get("prize"))
        except:
            pass

        if stype==0:
            scored=[(_score_main(o, me_p, opp_p, hand, opp_prizes), i) for i,o in enumerate(opts)]
            scored.sort(reverse=True)
            return [scored[0][1]]

        def _opt_score(o):
            s=0
            if o.get("type")==3:
                cid=None
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        s={ALAKAZAM:105, KADABRA:65, DUDUNSPARCE:60, TOUCANNON:48, ABRA:35, DUNSPARCE:38}.get(p.get("id"),22)
                        s+=min(_energies(p),2)*8 + _hp(p)/20.0
                elif area==4:
                    p=_active(me_p)
                    if p:
                        s={ALAKAZAM:105, KADABRA:65, DUDUNSPARCE:60}.get(p.get("id"),32)
                elif area==2 and idx is not None:
                    cid=hand[idx] if 0<=idx<len(hand) else None
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                if cid is not None:
                    s={ALAKAZAM:105, KADABRA:85, ABRA:75, DUDUNSPARCE:60, DUNSPARCE:55, 1079:45}.get(cid,28)
                    if cid in ENERGY_IDS:
                        mine=_board(me_p)
                        loaded=sum(_energies(p) for p in mine)
                        s=68 if loaded<len(mine) else 18
            elif o.get("type")==1:
                s=12
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
