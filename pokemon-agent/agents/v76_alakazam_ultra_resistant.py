#!/usr/bin/env python3
"""v76: ultra resistant - fixes 78 losses 52.6% wipe + 35% vs ? + 34% vs KYOGRE

Loss analysis 2026-10-17 07:xx UTC: 68 ep v70g 35W-33L, 76 ep v63 31W-45L, total 78 wipe losses:
- WIPE_1_SINGLE 30 (38.5%) board 1
- WIPE_0_EMPTY 11 (14.1%) board 0
- vs ? 28 (Hydrapple, Archaludon, Ogerpon, Kangaskhan, Crustle) - high HP walls 210-400
- vs KYOGRE 27 (Kyogre 350 HP, our max 20*15=300 can't OHKO)
- early T4-T9 14 losses (17.9%), T10-T14 33 (42%)

Fixes over v70/v74:
1. Early bench: board<=1 ALWAYS bench basic, board<=2 when turn<=10 or prizes<=5, board<=3 when prizes<=4
   (v70 only board<=2 prizes<=3, missed early 6-6)
2. Poffin/Pad boost when board<=2 ANY time, not just endgame
3. Hand refill thresh 6 (was 4) + extra boost when vs high HP (opp HP > our dmg) -> need 18 hand for 360 vs 350
4. Boss: not only KO now, but also cheap prize race vs walls: if opp bench <=90 HP and we have Boss, use it to gust weak mon even if not immediate KO, to avoid 2HKO race vs 350 HP wall
5. Recovery: Night Stretcher/Sacred Ash boosted when board<=2 OR discard has Abra line (741/742/743) and board<=3
6. Promotion: NEVER Abra when board<=2, regardless prizes; board<=3 prizes<=4 penalize Abra -50, prefer Alakazam 120 > Dudun 110 > Duns 60 > Kadabra 50 > Abra -50
7. Energy attach: if active 0 energy, attach before attack setup (was only when opts[0] type 13)
8. Vs KYOGRE: if opp active is Kyogre (721) or Mega Abomasnow (723) and our hand <=8, prioritize Hilda/Dawn to grow hand for 300 dmg

Second branch opinion: champion heuristic 0.012-0.39 invalid on Alakazam, need Rust port, but for Python we can still improve bench discipline and hand management.

Deck same as v66 simple 11E.
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
KYOGRE_IDS = {721, 723}  # Kyogre, Mega Abomasnow
HIGH_HP_WALLS = {96, 150, 190, 121, 756, 345, 240, 93, 90}  # Ogerpon, Hydrapple, Archaludon, Dragapult, Kangaskhan, Crustle etc

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
def _maxhp(poke): return int((poke or {}).get("maxHp") or _hp(poke))
def _hand_ids(player): return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]
def _discard_ids(player): return [(c or {}).get("id") for c in ((player or {}).get("discard") or [])]
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

        # helper: is opponent high HP wall?
        is_high_wall = opp_active_id in KYOGRE_IDS or opp_active_id in HIGH_HP_WALLS or opp_active_hp>=300

        if stype==0:
            # 1) always evo to Alakazam
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ALAKAZAM:
                    return [i]
            # 2) Rare Candy
            if ALAKAZAM in hand and any(p.get("id")==ABRA for p in board):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==1079:
                        return [i]
            # 3) ULTRA BENCH DISCIPLINE
            # board<=1 always, board<=2 when turn<=10 or prizes<=5, board<=3 when prizes<=4 or opp can KO
            need_bench = False
            if board_n<=1:
                need_bench=True
            elif board_n<=2 and (turn<=10 or our_prizes<=5 or opp_prizes<=5):
                need_bench=True
            elif board_n<=3 and (our_prizes<=4 or opp_prizes<=4 or is_high_wall):
                need_bench=True
            if need_bench:
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            return [i]
                # Poffin / Pad to find basic
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1086,1152):
                        return [i]
            # 4) hand refill thresh 6 + vs high wall
            if hand_n<=6 or (is_high_wall and hand_n<=8 and best_dmg < opp_active_hp):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1231,1225,1184):
                        return [i]
            # 5) Boss KO now
            if act is not None and best_dmg>0:
                for b in _bench(opp_p):
                    if 0<_hp(b)<=best_dmg+15:
                        for i,o in enumerate(opts):
                            if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                return [i]
                # cheap prize race vs walls: gust weak bench <=90 even if not KO now, if we have prize lead or equal and board healthy
                if is_high_wall and board_n>=3:
                    for b in _bench(opp_p):
                        if 0<_hp(b)<=90:
                            for i,o in enumerate(opts):
                                if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                    return [i]
            # 6) recovery when board small or discard has line
            discard=_discard_ids(me_p)
            has_line_in_discard = any(cid in (741,742,743,305,66) for cid in discard)
            if board_n<=2 or (board_n<=3 and has_line_in_discard):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1097,1129):
                        return [i]
            # 7) don't attack before setup - also attach energy if active 0
            if act and _energies(act)==0:
                for i,o in enumerate(opts):
                    if o.get("type")==8 and o.get("inPlayArea")==4:
                        return [i]
            if opts[0].get("type")==13:
                for i,o in enumerate(opts):
                    if o.get("type")==9:
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
                        if board_n<=2:
                            # NEVER Abra
                            if pid==ABRA:
                                s=-100
                            elif pid==ALAKAZAM:
                                s=130
                            elif pid==DUDUNSPARCE:
                                s=115
                            elif pid==DUNSPARCE:
                                s=70
                            elif pid==KADABRA:
                                s=50
                            else:
                                s=20
                        elif board_n<=3 and our_prizes<=4:
                            if pid==ABRA:
                                s=-50
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
                    if board_n<=2:
                        if cid in (1097,1129):
                            s=95
                        elif cid==ALAKAZAM:
                            s=105
                        elif cid in (1086,1152):
                            s=90
                        elif cid==ABRA:
                            s=75
                        elif cid==DUNSPARCE:
                            s=70
                        else:
                            s=25
                    elif board_n<=3 and (our_prizes<=4 or is_high_wall):
                        if cid in (1097,1129):
                            s=90
                        elif cid==ALAKAZAM:
                            s=100
                        elif cid in (1086,1152):
                            s=85
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
                        s=70 if loaded<len(mine) else 10
                    # hand refill boost vs high wall
                    if is_high_wall and cid in (1231,1225,1184) and hand_n<=8:
                        s=95
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
