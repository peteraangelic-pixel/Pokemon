#!/usr/bin/env python3
"""v83: Kyogre mirror tempo - per second branch correction

Second branch 2026-10-17 correction:
- Wipe 52.6% is END state, not cause. Cause is tempo of Abomasnow setup + Snover survivability
- 52% losses zero prizes, mirror loser avg 1.0 prize -> losing race early, bench empties at end of starvation
- Proof: no bench-discipline version beats baseline (v74 0.614 vs v70 0.618 new_losses noise, v76/v77 worse). Same as v64-guard.
- If bench discipline were cause, guard would help. It doesn't. Bottleneck is Abomasnow tempo.

Fixes for tempo (not bench guards):
- Early Snover bench T1-3 when have Water in hand, to start race
- Energy priority: attach to benched Snover/Abomasnow with 0E over active Kyogre with 1E+, to get first Aboma ready
- Search: Mega Signal 1145 boost when Snover board no Aboma hand, Ultra Ball 1121 boost when board empty to find Snover
- Protect Snover active: retreat if active Snover vs opp Aboma 723
- Attack: real damage estimate for Hammer-lanche (100 x Water discarded), avoid self-mill deckout when deckCount<=7
- Snipe: Boss 1182 / Waitress 1235 gust to KO benched Snover 722 with Kyogre Swirling 130 before evolve
- Promotion: Aboma ready (2E+) 150 > Kyogre 110 > Aboma not ready 100 > Snover 50, Snover -50 if opp Aboma can KO and Kyogre alt exists

Deck: c87_v44.csv (Kyogre 2, Snover 4, Aboma 4, 40 Water etc)
"""
from __future__ import annotations
import json, os, pathlib, re

_DECK_PATH = pathlib.Path(__file__).parent.parent / "decks" / "c87_v44.csv"
try:
    DECK = [int(x) for x in _DECK_PATH.read_text().split() if x.strip().isdigit()]
except:
    DECK = [3]*40 + [721,721,722,722,722,722,723,723,723,723,1227,1227,1227,1227,1145,1145,1145,1145,1235,1158,1152,1097,1121,1121,1152,1207,1121,1121,1262]

ABOMASNOW = 723
SNOVER = 722
KYOGRE = 721
MEGA_SIGNAL = 1145
BOSS = 1182
WAITRESS = 1235
ULTRA_BALL = 1121
POKE_PAD = 1152
NIGHT_STRETCHER = 1097

_CI = None
def _index():
    global _CI
    if _CI is None:
        _CI = {"cards": {}, "attacks": {}, "by_name": {}}
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
def _hp(poke): return int((poke or {}).get("hp") or 0)
def _energies(poke):
    if not poke: return 0
    e=poke.get("energies")
    if isinstance(e,list): return len(e)
    ec=poke.get("energyCards")
    return len(ec) if isinstance(ec,list) else 0
def _hand_ids(player): return [(h or {}).get("id") for h in ((player or {}).get("hand") or [])]
def _opt_hand_card(opt, player):
    idx=opt.get("index")
    if idx is None: return None
    hand=(player or {}).get("hand") or []
    if 0<=idx<len(hand):
        return (hand[idx] or {}).get("id")
    return None
def _is_basic(cid):
    c=_card(cid)
    return c.get("ct")==0 and c.get("b")
def _energy_id_of(cid):
    return _card(cid).get("en")
def _hand_water_count(player):
    try:
        cnt=0
        for h in (player.get("hand") or []):
            if not isinstance(h, dict): continue
            if _energy_id_of(h.get("id"))==3:
                cnt+=1
        return cnt
    except:
        return 0

# --- damage estimation for Hammer-lanche (copy from c87_v44) ---
_RE_PER_EACH = re.compile(r"does (\d+) damage for each", re.IGNORECASE)
_RE_MILL = re.compile(r"discard the top (\d+) cards? of your deck", re.IGNORECASE)

def _deck_energy_remaining(obs, me_idx, energy_type):
    try:
        total = sum(1 for cid in DECK if _energy_id_of(cid)==energy_type)
    except:
        return 0.0
    seen=0
    try:
        p = obs["current"]["players"][me_idx]
        for h in p.get("hand") or []:
            if _energy_id_of(h.get("id"))==energy_type:
                seen+=1
        for d in p.get("discard") or []:
            if isinstance(d, dict) and _energy_id_of(d.get("id"))==energy_type:
                seen+=1
        for slot in (p.get("active") or []) + (p.get("bench") or []):
            if not slot: continue
            for e in slot.get("energyCards") or []:
                if _energy_id_of(e.get("id"))==energy_type:
                    seen+=1
    except:
        pass
    return max(0.0, float(total-seen))

def _deck_energy_rate(obs, me_idx, energy_type):
    try:
        remaining = float(obs["current"]["players"][me_idx].get("deckCount") or 0)
        if remaining<=1: return 0.0
        return min(1.0, _deck_energy_remaining(obs, me_idx, energy_type)/remaining)
    except:
        return 0.0

def _estimate_damage_raw(aid, obs, me_idx, opp_idx):
    ad=_attack(aid)
    base=int(ad.get("d") or 0)
    if base>0:
        return base
    text=ad.get("t") or ""
    if not text:
        return 0
    m=_RE_PER_EACH.search(text)
    if m:
        per=int(m.group(1))
        if "in this way" in text.lower():
            mill=_RE_MILL.search(text)
            n_cards=int(mill.group(1)) if mill else 6
            low=text.lower()
            if "{w}" in low or "water" in low:
                rate=_deck_energy_rate(obs, me_idx, 3)
            else:
                rate=1.0
                return int(per*n_cards)
            return int(per*n_cards*min(rate,1.0))
        # fallback
        return 0
    return 0

def _mill_would_deck_out(aid, obs, me_idx):
    ad=_attack(aid)
    m=_RE_MILL.search(ad.get("t") or "")
    if not m: return False
    try:
        remaining=int(obs["current"]["players"][me_idx].get("deckCount") or 0)
    except:
        return False
    return remaining <= int(m.group(1))+1

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
        board=_board(me_p)
        board_n=len(board)
        opp_active=_active(opp_p)
        opp_active_id=int(opp_active.get("id")) if opp_active and opp_active.get("id") is not None else 0
        act=_active(me_p)
        opp_bench=_bench(opp_p)
        has_snover_board = any(int(p.get("id") or 0)==SNOVER for p in board)
        has_aboma_hand = ABOMASNOW in hand
        has_snover_hand = SNOVER in hand
        opp_can_ko_snover = opp_active_id==ABOMASNOW
        water_in_hand = _hand_water_count(me_p)

        if stype==0:
            # 1) Always evolve Snover to Abomasnow
            for i,o in enumerate(opts):
                if o.get("type")==9 and _opt_hand_card(o, me_p)==ABOMASNOW:
                    return [i]

            # 2) Protect Snover active: retreat if vs Aboma
            if act and int(act.get("id") or 0)==SNOVER and opp_can_ko_snover:
                for i,o in enumerate(opts):
                    if o.get("type")==12:  # retreat
                        return [i]
                # if no retreat, try switch via ability? (Beach)
                for i,o in enumerate(opts):
                    if o.get("type")==10:
                        return [i]

            # 3) Tempo search: Mega Signal when Snover board no Aboma hand
            if has_snover_board and not has_aboma_hand:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==MEGA_SIGNAL:
                        return [i]

            # 4) Early Snover bench T<=4 when have Water, to start race
            if turn<=4 and has_snover_hand and water_in_hand>=1 and board_n<=4:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p)==SNOVER:
                        return [i]

            # 5) Ultra Ball / Poke Pad when board empty to find Snover
            if board_n<=1:
                for i,o in enumerate(opts):
                    if o.get("type")==7 and _opt_hand_card(o, me_p) in (ULTRA_BALL, POKE_PAD):
                        return [i]

            # 6) Early Kyogre snipe: opp benched Snover <=130 HP, we have Kyogre active 3E, Boss in hand
            if act and int(act.get("id") or 0)==KYOGRE and _energies(act)>=3:
                for b in opp_bench:
                    if int(b.get("id") or 0)==SNOVER and _hp(b)<=130 and _hp(b)>0:
                        for i,o in enumerate(opts):
                            cid=_opt_hand_card(o, me_p)
                            if cid in (BOSS, WAITRESS):
                                return [i]

            # 7) Energy priority: attach to bench Snover/Aboma with 0E if active already has 1E+
            # This is handled in ATTACH scoring below, but for MAIN we need to pick attach option
            # Look for attach options that target bench Snover 0E
            active_e = _energies(act) if act else 0
            if active_e>=1:
                for i,o in enumerate(opts):
                    if o.get("type")==8:
                        area=o.get("inPlayArea")
                        idx=o.get("inPlayIndex")
                        if area==5 and idx is not None:
                            b=_bench(me_p)
                            if 0<=idx<len(b):
                                p=b[idx]
                                if int(p.get("id") or 0) in (SNOVER, ABOMASNOW) and _energies(p)==0:
                                    return [i]

            # 8) Basic bench discipline minimal: only when board<=1 (not guard heavy)
            if board_n<=1:
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        cid=_opt_hand_card(o, me_p)
                        if _is_basic(cid):
                            return [i]

            return [0]

        # non-main: promotion / search / energy / attack
        def _score(o):
            s=0
            otype=o.get("type")
            if otype==3:  # CARD select
                area,idx=o.get("area"),o.get("index")
                if area==5 and idx is not None:  # bench promotion
                    b=_bench(me_p)
                    p=b[idx] if 0<=idx<len(b) else None
                    if p:
                        pid=int(p.get("id") or 0)
                        e=_energies(p)
                        ready = e>=2
                        if pid==SNOVER and opp_can_ko_snover and any(int(q.get("id") or 0)==KYOGRE for q in b):
                            s=-50
                        elif pid==ABOMASNOW and ready:
                            s=150
                        elif pid==KYOGRE:
                            s=110
                        elif pid==ABOMASNOW:
                            s=100
                        elif pid==SNOVER:
                            s=50
                        else:
                            s=20
                        s+=_hp(p)/10 + e*5
                elif o.get("cardId") is not None:
                    cid=o.get("cardId")
                    if has_snover_board and not has_aboma_hand and cid==MEGA_SIGNAL:
                        s=100
                    elif cid==ABOMASNOW:
                        s=95
                    elif cid==SNOVER and turn<=4:
                        s=90
                    elif cid==KYOGRE:
                        s=70
                    else:
                        s=20
                elif area==2 and idx is not None:  # hand card for discard/search
                    cid=hand[idx] if 0<=idx<len(hand) else None
                    if cid==ABOMASNOW:
                        s=95
                    elif cid==SNOVER and turn<=4:
                        s=85
                    else:
                        s=10
            elif otype==8:  # ATTACH
                area=o.get("inPlayArea")
                idx=o.get("inPlayIndex")
                target=None
                if area==4:
                    target=act
                elif area==5 and idx is not None:
                    b=_bench(me_p)
                    if 0<=idx<len(b):
                        target=b[idx]
                if target:
                    pid=int(target.get("id") or 0)
                    e=_energies(target)
                    # Tempo: bench Snover/Aboma 0E gets highest
                    if pid in (SNOVER, ABOMASNOW) and e==0 and area==5:
                        s=120
                    elif pid==ABOMASNOW and e<2:
                        s=110
                    elif pid==KYOGRE and e<3 and area==4:
                        s=90
                    elif pid==SNOVER and e<2:
                        s=80
                    else:
                        s=20
            elif otype==13:  # ATTACK
                aid=o.get("attackId")
                est=_estimate_damage_raw(aid, obs, me, 1-me)
                # avoid self-mill
                if _mill_would_deck_out(aid, obs, me):
                    s=-500
                else:
                    s=est//2
                    # prize hunger: boost KO
                    if opp_active and _hp(opp_active)>0 and est>=_hp(opp_active):
                        s+=100
                    # Hammer-lanche vs thick wall
                    if opp_active and _hp(opp_active)>=300 and est>=200:
                        s+=60
            elif otype==1:
                s=10
            elif otype==12:  # RETREAT
                s=50
                if act and int(act.get("id") or 0)==SNOVER and opp_can_ko_snover:
                    s=200
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
