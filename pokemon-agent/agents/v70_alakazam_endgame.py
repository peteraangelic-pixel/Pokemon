#!/usr/bin/env python3
"""v70: Alakazam — fix wipe loss mode per second branch forensics.

Loss mode: leading 4-1 in prizes and lose because last Pokemon dies with board 1 vs 5.
Fixes per second branch:
- endgame bench discipline: always >=2 behind active when prizes <=3
- timing recovery: Night Stretcher/Sacred Ash boosted when board<=2
- not promoting last Abra in KO: prefer Dudunsparce 140/Alakazam over Abra 50 when board<=2

Base: latest v65 hybrid (0.611 grid) + simple deck 4x Alakazam 11E.
Env knobs kept for CEM but defaults fixed to best known.
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

        # prize counts for endgame discipline
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

        if stype==0:
            # 1) always evo to Alakazam
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ALAKAZAM:
                    return [i]
            # 2) Rare Candy when Abra line present
            if ALAKAZAM in hand and any(p.get("id")==ABRA for p in board):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==1079:
                        return [i]
            # 3) ENDGAME BENCH DISCIPLINE: if board <=2 and prizes <=3, never end turn without benching
            if board_n<=2 and (our_prizes<=3 or opp_prizes<=3):
                # look for basic bench
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            # massive boost for endgame
                            return [i]
                # if no basic in hand, try Poffin/Pad to find one
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1086,1152):
                        return [i]
            # 4) hand refill when <=4 (damage = hand)
            if len(hand)<=4:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1231,1225):
                        return [i]
            # 5) Boss KO when it gives KO now
            act=_active(me_p)
            if act is not None:
                dmg=_best_damage(act, len(hand), _active(opp_p))
                if dmg>0:
                    for b in _bench(opp_p):
                        if 0<_hp(b)<=dmg+10:  # margin 10
                            for i,o in enumerate(opts):
                                if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                    return [i]
            # 6) recovery when board small
            if board_n<=2:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1097,1129):
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

        # non-main: promotion / search — fix last Abra promotion
        def _opt_score(o):
            s=0
            if o.get("type")==3:
                cid=None
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:  # bench promotion after KO
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=p.get("id")
                        # ENDGAME: never promote last Abra 50 HP if alternative exists
                        if board_n<=2 and our_prizes<=3:
                            if pid==ABRA:
                                s=-50  # penalize Abra promotion in endgame
                            elif pid==ALAKAZAM:
                                s=120
                            elif pid==DUDUNSPARCE:
                                s=110
                            elif pid==DUNSPARCE:
                                s=60
                            else:
                                s=30
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
                    # protect Abra line, but in endgame prefer recovery
                    if board_n<=2 and (our_prizes<=3 or opp_prizes<=3):
                        if cid in (1097,1129):  # Night Stretcher, Sacred Ash
                            s=90
                        elif cid==ALAKAZAM:
                            s=100
                        elif cid==ABRA:
                            s=70
                        elif cid==DUNSPARCE:
                            s=65
                        else:
                            s=30
                    else:
                        s={ALAKAZAM:100, KADABRA:80, ABRA:70, DUDUNSPARCE:55, DUNSPARCE:50, 1079:40}.get(cid,25)
                    if cid in ENERGY_IDS:
                        mine=_board(me_p)
                        loaded=sum(_energies(p) for p in mine)
                        s=65 if loaded<len(mine) else 15
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
