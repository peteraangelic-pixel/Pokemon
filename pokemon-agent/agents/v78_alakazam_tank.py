#!/usr/bin/env python3
"""v78: tanky deck + balanced logic - more high HP to survive Kyogre chain KO

Deck change vs v66 simple:
- Dudunsparce 3->4 (140 HP tank)
- Fezandipiti ex 1->2 (210 HP)
- Dunsparce 4->3 (70 HP)
- Abra 4->3 (50 HP)
- Kadabra 4->3 (80 HP)
- Alakazam 4 stays
Total basics: Dunsparce 3 + Abra 3 + Fez 2 = 8 (same as before 8, but more high HP)
High HP count: Dudun 4 + Fez 2 + Alakazam 4 = 10 high HP (was 3+1+4=8)

Logic: v77 balanced (board<=1 always, board<=2 turn<=8 or prizes<=4, hand 5, Boss 100, no Abra promo board<=2)
Plus: always prefer Dudun 140 > Fez 210? Actually Fez 210 > Dudun 140 for tank, but Alakazam 140 with attack is best if can attack.
Promotion: Alakazam 130 > Fez 120 > Dudun 115 > Duns 65 > Kadabra 50 > Abra -100 when board<=2
"""
from __future__ import annotations
import json, os

DECK_TANK = [
    5,5,5,5,5,13,5,19,19,19,19,  # 11E
    66,66,66,66,  # Dudun 4
    140,140,  # Fez 2
    305,305,305,  # Duns 3
    741,741,741,  # Abra 3
    742,742,742,  # Kadabra 3
    743,743,743,743,  # Alakazam 4
    1079,1079,1079,1079,  # Candy 4
    1081,1081,  # Hammer 2
    1086,1086,1086,1086,  # Poffin 4
    1097,1097,  # Stretcher 2
    1129,  # Ash 1
    1152,1152,1152,1152,  # Pad 4
    1182,1182,1182,  # Boss 3
    1184,  # Lana 1
    1225,1225,1225,  # Hilda 3
    1231,1231,1231,  # Dawn 3
    1264,1264  # Cage 2
]
DECK = DECK_TANK

ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE = 305, 66
FEZAN = 140
ENERGY_IDS = {5, 13, 19}
KYOGRE_IDS = {721, 723}
HIGH_HP_WALLS = {96, 150, 190, 121, 756, 345}

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
    return 0
def _best_damage(poke, hand_n, opp_active):
    best=0
    for aid in (_card(poke.get("id")).get("atk") or []) if poke else []:
        d=_atk_damage(poke, aid, hand_n, opp_active)
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
        hand_n=len(hand)
        turn=int(cur.get("turn") or 0)
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
        opp_active=_active(opp_p)
        opp_active_id=int(opp_active.get("id")) if opp_active and opp_active.get("id") is not None else 0
        opp_active_hp=_hp(opp_active)
        act=_active(me_p)
        best_dmg=_best_damage(act, hand_n, opp_active) if act else 0
        is_high_wall = opp_active_id in KYOGRE_IDS or opp_active_id in HIGH_HP_WALLS or opp_active_hp>=300

        if stype==0:
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ALAKAZAM:
                    return [i]
            if ALAKAZAM in hand and any(p.get("id")==ABRA for p in board):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==1079:
                        return [i]
            need_bench=False
            if board_n<=1:
                need_bench=True
            elif board_n<=2 and (turn<=8 or our_prizes<=4):
                need_bench=True
            elif board_n<=3 and our_prizes<=4:
                need_bench=True
            if need_bench:
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            return [i]
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1086,1152):
                        return [i]
            if hand_n<=5 or (is_high_wall and hand_n<=7 and best_dmg < opp_active_hp):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1231,1225):
                        return [i]
            if act is not None and best_dmg>0:
                for b in _bench(opp_p):
                    if 0<_hp(b)<=best_dmg+15:
                        for i,o in enumerate(opts):
                            if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                return [i]
                if is_high_wall and board_n>=2:
                    for b in _bench(opp_p):
                        if 0<_hp(b)<=100:
                            for i,o in enumerate(opts):
                                if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                    return [i]
            if board_n<=2:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1097,1129):
                        return [i]
            if act and _energies(act)==0:
                for i,o in enumerate(opts):
                    if o.get("type")==8 and o.get("inPlayArea")==4:
                        return [i]
            if opts[0].get("type")==13:
                for i,o in enumerate(opts):
                    if o.get("type")==9:
                        return [i]
            return [0]

        def _opt_score(o):
            s=0
            if o.get("type")==3:
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=p.get("id")
                        if board_n<=2:
                            if pid==ABRA:
                                s=-100
                            elif pid==ALAKAZAM:
                                s=130
                            elif pid==FEZAN:
                                s=122
                            elif pid==DUDUNSPARCE:
                                s=115
                            elif pid==DUNSPARCE:
                                s=65
                            else:
                                s=25
                        elif board_n<=3 and our_prizes<=4:
                            if pid==ABRA:
                                s=-50
                            elif pid==ALAKAZAM:
                                s=120
                            elif pid==FEZAN:
                                s=118
                            elif pid==DUDUNSPARCE:
                                s=110
                            else:
                                s=30
                        else:
                            s={ALAKAZAM:100, FEZAN:95, DUDUNSPARCE:55, ABRA:30, DUNSPARCE:35}.get(pid,20)
                        s+=min(_energies(p),2)*8 + _hp(p)/20.0
                elif area==4:
                    p=_active(me_p)
                    if p:
                        s={ALAKAZAM:100, FEZAN:90, DUDUNSPARCE:55}.get(p.get("id"),30)
                elif area==2 and idx is not None:
                    cid=hand[idx] if 0<=idx<len(hand) else None
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                if cid is not None:
                    if board_n<=2:
                        if cid in (1097,1129):
                            s=92
                        elif cid==ALAKAZAM:
                            s=102
                        elif cid in (1086,1152):
                            s=88
                        elif cid==ABRA:
                            s=72
                        elif cid==DUNSPARCE:
                            s=68
                        else:
                            s=28
                    elif board_n<=3 and our_prizes<=4:
                        if cid in (1097,1129):
                            s=90
                        elif cid==ALAKAZAM:
                            s=100
                        elif cid in (1086,1152):
                            s=85
                        else:
                            s=32
                    else:
                        s={ALAKAZAM:100, KADABRA:80, ABRA:70, DUDUNSPARCE:55, DUNSPARCE:50, 1079:40}.get(cid,25)
                    if cid in ENERGY_IDS:
                        mine=_board(me_p)
                        loaded=sum(_energies(p) for p in mine)
                        s=68 if loaded<len(mine) else 12
                    if is_high_wall and cid in (1231,1225) and hand_n<=7:
                        s=93
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
