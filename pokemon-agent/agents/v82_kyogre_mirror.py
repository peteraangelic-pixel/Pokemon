#!/usr/bin/env python3
"""v82: Kyogre mirror resistant - per second branch fa4fe68 insight

Second branch 2026-10-17 08:00:
- v63 31W-44L (0.413) rating 399.7, 52% losses end with ZERO prizes, avg 1.17 prizes in losses
- Mirror Abomasnow 15 losses, 9x wipe, avg 1.0 prizes - race to first Mega Abomasnow
- Problem not bench wipe itself but losing Snover before evolution
- Local WR 0.512 reproduces live 1:1, can work without Kaggle via prizetest.py metric "zero prize losses"

Fixes:
- Protect Snover on bench: never promote Snover active if opp has Abomasnow that can KO 90 HP, prefer Kyogre active as tank
- Early Kyogre snipe: if opp has benched Snover <=90 HP and we have Kyogre with Swirling Waves 130 + Boss, gust and KO before they evolve
- Search: boost Mega Signal (1145) when we have Snover on board and no Abomasnow in hand
- Bench: always bench Snover early (turn<=6) even if board<=2, to setup race
- Promotion: Abomasnow 130 > Kyogre 100 > Snover 50 when board<=2, but if opp can KO Snover, prefer Kyogre even more

Deck: c87_v44.csv Kyogre 2, Snover 4, Abomasnow 4, 40 Water Energy? Actually 3 is Basic Water
"""
from __future__ import annotations
import json, os, pathlib

# Load deck from c87_v44.csv
_DECK_PATH = pathlib.Path(__file__).parent.parent / "decks" / "c87_v44.csv"
try:
    DECK = [int(x) for x in _DECK_PATH.read_text().split() if x.strip().isdigit()]
except:
    DECK = [3]*40 + [721,721,722,722,722,722,723,723,723,723,1227,1227,1227,1227,1145,1145,1145,1145,1235,1158,1152,1097,1121,1121,1152,1207,1121,1121,1262]

ABOMASNOW = 723
SNOVER = 722
KYOGRE = 721
MEGA_SIGNAL = 1145
BOSS = 1182  # might be different id for Boss in Kyogre deck? Actually 1182 is Boss's Orders, but Kyogre deck uses 1235 Waitress? Let's use both
WAITRESS = 1235
LILLIE = 1227

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
def _has_energy(poke, need=1):
    if not poke: return False
    e=poke.get("energies")
    if isinstance(e,list): return len(e)>=need
    ec=poke.get("energyCards")
    if isinstance(ec,list): return len(ec)>=need
    return False

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
        act=_active(me_p)
        opp_bench=_bench(opp_p)

        # Is opponent Abomasnow that can KO our Snover (90 HP)?
        opp_can_ko_snover = opp_active_id==ABOMASNOW  # Abomasnow does 200 or 100 per Water, can KO Snover

        if stype==0:
            # 1) Protect Snover: if active is Snover and opp can KO, try to retreat or switch
            if act and int(act.get("id") or 0)==SNOVER and opp_can_ko_snover:
                # look for switch / retreat
                for i,o in enumerate(opts):
                    if o.get("type")==8:  # retreat / switch
                        return [i]
                # if no retreat, try to evolve Snover to Abomasnow now
                for i,o in enumerate(opts):
                    if o.get("type")==9 and _opt_hand_card(o, me_p)==ABOMASNOW:
                        return [i]

            # 2) Early Kyogre snipe: opp has benched Snover <=90 HP, we have Kyogre active with energy, and Boss/Waitress
            # Check if we have Kyogre active with 3 energy for Swirling Waves 130
            if act and int(act.get("id") or 0)==KYOGRE and _has_energy(act,3):
                for b in opp_bench:
                    if int(b.get("id") or 0)==SNOVER and _hp(b)<=130 and _hp(b)>0:
                        # need Boss or Waitress to gust
                        for i,o in enumerate(opts):
                            cid=_opt_hand_card(o, me_p)
                            if cid in (1182, 1235, 1227):  # Boss, Waitress, Lillie? Actually Boss is 1182, Waitress 1235
                                # Check if this supporter is Boss/Waitress that can gust
                                # For simplicity, if we have any gust supporter, use it
                                if cid in (1182, 1235):
                                    return [i]

            # 3) Search: boost Mega Signal when we have Snover on board and no Abomasnow in hand
            has_snover_board = any(int(p.get("id") or 0)==SNOVER for p in board)
            has_aboma_hand = ABOMASNOW in hand
            if has_snover_board and not has_aboma_hand:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==MEGA_SIGNAL:
                        return [i]

            # 4) Bench Snover early even if board small
            if turn<=6 and board_n<=3:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==SNOVER:
                        return [i]

            # 5) Always evolve Snover to Abomasnow
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ABOMASNOW:
                    return [i]

            # 6) bench discipline for Kyogre: board<=1 always
            if board_n<=1:
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        c=_card(cid)
                        if c.get("ct")==0 and c.get("b"):
                            return [i]

            return [0]

        # non-main: promotion / search
        def _score(o):
            s=0
            if o.get("type")==3:
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:  # bench promotion
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=int(p.get("id") or 0)
                        # Protect Snover: never promote Snover if opp can KO and we have Kyogre alternative
                        if pid==SNOVER and opp_can_ko_snover and any(int(q.get("id") or 0)==KYOGRE for q in b):
                            s=-50
                        elif pid==ABOMASNOW:
                            s=130
                        elif pid==KYOGRE:
                            s=110
                        elif pid==SNOVER:
                            s=50
                        else:
                            s=20
                        s+=_hp(p)/10
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                    # search priority
                    if has_snover_board and not has_aboma_hand and cid==MEGA_SIGNAL:
                        s=100
                    elif cid==ABOMASNOW:
                        s=95
                    elif cid==SNOVER and turn<=6:
                        s=90
                    elif cid==KYOGRE:
                        s=70
                    else:
                        s=20
            elif o.get("type")==1:
                s=5
            return s

        ranked=sorted(range(len(opts)), key=lambda i: -_score(opts[i]))
        k=int(sel.get("minCount") or 1)
        return sorted(ranked[:max(1,k)])
    except Exception as e:
        try:
            n=len((obs.get("select") or {}).get("option") or [])
            return [0] if n else []
        except:
            return []
