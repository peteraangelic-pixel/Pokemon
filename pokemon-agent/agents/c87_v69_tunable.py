#!/usr/bin/env python3
"""v69 tunable: YumeNeko Alakazam hybrid (latest v65) + env var knobs for CEM.

Knobs (via env, defaults = v65 latest best):
- PTCG_RARE_CANDY 1/0 enable Rare Candy override
- PTCG_HAND_THRESH int 4 = hand <= thresh triggers Dawn/Hilda refill
- PTCG_HAND_BONUS int 1 = enable hand refill override
- PTCG_BOSS_KO 1/0 enable Boss KO override
- PTCG_BOSS_MARGIN int 0 = extra dmg margin for Boss KO (dmg >= hp - margin)
- PTCG_EVO_ALAK 1/0 always evolve to Alakazam when offered
- PTCG_NO_ATK_BEFORE_SETUP 1/0 don't attack before evolve/attach
- PTCG_ABRA_TP_THRESH int 50 = Abra Teleport when HP <= thresh and ready Alakazam bench
- PTCG_SIMPLE_DECK 0/1 use simplified list (4x Alakazam, 11E) vs YumeNeko list

Decks:
- YumeNeko (default): 19x4,741x4,742x4,1079x4,1086x4,1152x4,66x3,305x3,743x3,1225x3,1231x3,5x2,1081x2,1182x2,1264x2,1407x2,1409x2,13,140,214,959,1097,1129,1161,1184,1413
- Simple (v66): 5x6,13,19x4,66x3,140,305x4,741x4,742x4,743x4,1079x4,1081x2,1086x4,1097x2,1129,1152x4,1182x3,1184,1225x3,1231x3,1264x2
"""
from __future__ import annotations
import json, os

# --- env knobs ---
def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except:
        return default

RARE_CANDY_EN = _env_int("PTCG_RARE_CANDY", 1)
HAND_THRESH = _env_int("PTCG_HAND_THRESH", 4)
HAND_BONUS_EN = _env_int("PTCG_HAND_BONUS", 1)
BOSS_KO_EN = _env_int("PTCG_BOSS_KO", 1)
BOSS_MARGIN = _env_int("PTCG_BOSS_MARGIN", 0)
EVO_ALAK_EN = _env_int("PTCG_EVO_ALAK", 1)
NO_ATK_BEFORE_SETUP = _env_int("PTCG_NO_ATK_BEFORE_SETUP", 1)
ABRA_TP_THRESH = _env_int("PTCG_ABRA_TP_THRESH", 50)
USE_SIMPLE = _env_int("PTCG_SIMPLE_DECK", 1)

# --- decks ---
DECK_YUME = [
    19, 19, 19, 19, 741, 741, 741, 741, 742, 742, 742, 742,
    1079, 1079, 1079, 1079, 1086, 1086, 1086, 1086, 1152, 1152, 1152, 1152,
    66, 66, 66, 305, 305, 305, 743, 743, 743, 1225, 1225, 1225, 1231, 1231, 1231,
    5, 5, 1081, 1081, 1182, 1182, 1264, 1264, 1407, 1407, 1409, 1409,
    13, 140, 214, 959, 1097, 1129, 1161, 1184, 1413,
]
DECK_SIMPLE = [
    5,5,5,5,5,13,5,19,19,19,19,66,66,66,140,305,305,305,305,741,741,741,741,742,742,742,742,743,743,743,743,
    1079,1079,1079,1079,1081,1081,1086,1086,1086,1086,1097,1097,1129,1152,1152,1152,1152,1182,1182,1182,1184,1225,1225,1225,1231,1231,1231,1264,1264
]
DECK = DECK_SIMPLE if USE_SIMPLE else DECK_YUME

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

        if stype==0:
            # hybrid: trust engine order + surgical overrides
            if EVO_ALAK_EN:
                for i,o in enumerate(opts):
                    if o.get("type")==9 and _opt_hand_card(o, me_p)==ALAKAZAM:
                        return [i]
            if RARE_CANDY_EN and ALAKAZAM in hand and any(p.get("id")==ABRA for p in _board(me_p)):
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==1079:
                        return [i]
            if HAND_BONUS_EN and len(hand)<=HAND_THRESH:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (1231,1225):
                        return [i]
            if BOSS_KO_EN:
                act=_active(me_p)
                if act is not None:
                    dmg=_best_damage(act, len(hand), _active(opp_p))
                    if dmg>0:
                        for b in _bench(opp_p):
                            if 0<_hp(b)<=dmg+BOSS_MARGIN:
                                for i,o in enumerate(opts):
                                    if o.get("type")==7 and _opt_hand_card(o, me_p)==1182:
                                        return [i]
            if NO_ATK_BEFORE_SETUP and opts[0].get("type")==13:
                for i,o in enumerate(opts):
                    if o.get("type")==9:
                        return [i]
                act=_active(me_p)
                if act and _energies(act)==0:
                    for i,o in enumerate(opts):
                        if o.get("type")==8 and o.get("inPlayArea")==4:
                            return [i]
            return [0]

        # non-main: keep v65 scoring
        def _opt_score(o):
            s=0
            if o.get("type")==3:
                cid=None
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        s={ALAKAZAM:100, KADABRA:60, DUDUNSPARCE:55, TOUCANNON:45, ABRA:30, DUNSPARCE:35}.get(p.get("id"),20)
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
