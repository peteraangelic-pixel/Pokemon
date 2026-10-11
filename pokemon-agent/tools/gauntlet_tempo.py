#!/usr/bin/env python3
"""Gauntlet with tempo metrics: winrate + first prize turn + prize by T9"""
import argparse, ctypes, importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"
if not LIB.exists():
    LIB = Path("/home/user/Pokemon/pokemon-agent/.venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")

class StartData(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

_lib=None
def get_lib():
    global _lib
    if _lib is None:
        lib = ctypes.cdll.LoadLibrary(str(LIB))
        lib.GameInitialize()
        lib.BattleStart.restype = StartData
        lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.BattleFinish.argtypes = [ctypes.c_void_p]
        lib.GetBattleData.restype = SerialData
        lib.GetBattleData.argtypes = [ctypes.c_void_p]
        lib.Select.restype = ctypes.c_int
        lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        _lib=lib
    return _lib

def load_deck(path):
    return [int(t) for line in open(path) for t in line.replace(",", " ").split() if t]

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def run_game(our_deck, opp_deck, our_agent_fn, opp_agent_fn, our_seat, lib):
    d0 = our_deck if our_seat==0 else opp_deck
    d1 = opp_deck if our_seat==0 else our_deck
    cards = (ctypes.c_int * 120)(*d0, *d1)
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        return {"result":0, "first_prize_turn":99, "prize_by_T9":0, "turns":0, "steps":0, "winner":-1, "first_prize_turn_opp":99, "prize_by_T9_opp":0}

    first_prize_turn=None
    first_prize_turn_opp=None
    prize_by_T9=0
    prize_by_T9_opp=0
    max_turn=0
    steps=0
    winner=-1
    # track prize len
    try:
        while True:
            steps+=1
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            turn = cur.get("turn", 0)
            max_turn=max(max_turn, turn)
            players=cur.get("players") or []
            if players and len(players)>=2:
                # our prize remaining = len(players[our_seat].prize)
                # taken = 6 - len
                if our_seat < len(players):
                    our_prize_len=len(players[our_seat].get("prize") or [])
                    # at start prize len 0 before setup, then 6, then decreases
                    if our_prize_len>0 and our_prize_len<6:
                        if first_prize_turn is None:
                            first_prize_turn=turn
                    # prize by T9
                    if turn<=9:
                        # taken by T9 = 6 - len, but if len 0 before setup, ignore
                        if our_prize_len<=6 and our_prize_len>0:
                            prize_by_T9=6-our_prize_len
                        elif our_prize_len==0 and turn>0:
                            # game ended, all taken
                            prize_by_T9=6
                opp_seat=1-our_seat
                if opp_seat < len(players):
                    opp_prize_len=len(players[opp_seat].get("prize") or [])
                    if opp_prize_len>0 and opp_prize_len<6:
                        if first_prize_turn_opp is None:
                            first_prize_turn_opp=turn
                    if turn<=9:
                        if opp_prize_len<=6 and opp_prize_len>0:
                            prize_by_T9_opp=6-opp_prize_len
            res=cur.get("result")
            if res is not None and res>=0:
                winner=res
                break
            sel=obs.get("select")
            if sel is None:
                break
            me=int(cur.get("yourIndex",0))
            dec = our_agent_fn(obs) if me==our_seat else opp_agent_fn(obs)
            if not isinstance(dec, list):
                dec=[]
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec))!=0:
                break
            if steps>5000:
                break
    finally:
        lib.BattleFinish(bp)
    if first_prize_turn is None:
        first_prize_turn=99
    if first_prize_turn_opp is None:
        first_prize_turn_opp=99
    our_win = 1 if winner==our_seat else (-1 if winner>=0 and winner!=2 else 0)
    return {"result":our_win, "first_prize_turn":first_prize_turn, "prize_by_T9":prize_by_T9, "turns":max_turn, "steps":steps, "winner":winner, "first_prize_turn_opp":first_prize_turn_opp, "prize_by_T9_opp":prize_by_T9_opp}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/main_heuristic_v11.py")
    ap.add_argument("--our-deck", default="decks/v12_30_boss4.csv")
    ap.add_argument("--opp-dir", default="decks/v14_opp_test")
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--only", default="")
    args=ap.parse_args()

    agent_path = str((ROOT / args.agent) if not os.path.isabs(args.agent) else args.agent)
    our_deck_path = (ROOT / args.our_deck) if not os.path.isabs(args.our_deck) else Path(args.our_deck)
    opp_dir = (ROOT / args.opp_dir) if not os.path.isabs(args.opp_dir) else Path(args.opp_dir)

    our_deck=load_deck(str(our_deck_path))
    mod = load_module(agent_path, "_our")
    mod.DECK=list(our_deck)
    if hasattr(mod, "_build_plan"):
        mod.PLAN=mod._build_plan(mod.DECK)
    def fn_our(obs):
        if obs.get("select") is None:
            return list(our_deck)
        return mod.agent(obs)

    opp_files=[]
    for p in Path(opp_dir).glob("*.csv"):
        if args.only and args.only not in p.stem:
            continue
        opp_files.append(p)
    opp_files=sorted(opp_files)
    print(f"Our deck: {our_deck_path} {len(our_deck)} cards")
    print(f"Opp dir: {opp_dir} {len(opp_files)} decks, {args.games} games each")
    lib=get_lib()

    total_w=0
    total_l=0
    total_d=0
    sum_first=0
    sum_prize_T9=0
    sum_turns=0
    sum_first_opp=0
    sum_prize_T9_opp=0
    count=0

    for opp_path in opp_files:
        opp_deck=load_deck(str(opp_path))
        mod_opp = load_module(agent_path, f"_opp_{opp_path.stem}")
        mod_opp.DECK=list(opp_deck)
        if hasattr(mod_opp, "_build_plan"):
            mod_opp.PLAN=mod_opp._build_plan(mod_opp.DECK)
        def make_fn(deck, m):
            def fn(obs):
                if obs.get("select") is None:
                    return list(deck)
                return m.agent(obs)
            return fn
        fn_opp=make_fn(opp_deck, mod_opp)

        w=l=d=0
        firsts=[]
        prizes=[]
        turns=[]
        firsts_opp=[]
        prizes_opp=[]
        for g in range(args.games):
            seat=g%2
            res=run_game(our_deck, opp_deck, fn_our, fn_opp, seat, lib)
            if res["result"]==1:
                w+=1
            elif res["result"]==-1:
                l+=1
            else:
                d+=1
            firsts.append(res["first_prize_turn"])
            prizes.append(res["prize_by_T9"])
            turns.append(res["turns"])
            firsts_opp.append(res["first_prize_turn_opp"])
            prizes_opp.append(res["prize_by_T9_opp"])
        avg_first=sum(firsts)/len(firsts) if firsts else 99
        avg_prize=sum(prizes)/len(prizes) if prizes else 0
        avg_turn=sum(turns)/len(turns) if turns else 0
        avg_first_opp=sum(firsts_opp)/len(firsts_opp) if firsts_opp else 99
        avg_prize_opp=sum(prizes_opp)/len(prizes_opp) if prizes_opp else 0
        total_w+=w
        total_l+=l
        total_d+=d
        sum_first+=avg_first
        sum_prize_T9+=avg_prize
        sum_turns+=avg_turn
        sum_first_opp+=avg_first_opp
        sum_prize_T9_opp+=avg_prize_opp
        count+=1
        print(f"{opp_path.stem:40s} {w}W-{l}L-{d}D  first={avg_first:.1f} prize_T9={avg_prize:.1f} opp_first={avg_first_opp:.1f} opp_prize_T9={avg_prize_opp:.1f} turns={avg_turn:.1f}")

    if count>0:
        overall_first=sum_first/count
        overall_prize=sum_prize_T9/count
        overall_turn=sum_turns/count
        overall_first_opp=sum_first_opp/count
        overall_prize_opp=sum_prize_T9_opp/count
        total=total_w+total_l+total_d
        winrate=total_w/total if total else 0
        prize_score=min(overall_prize/2.2, 1.0)
        first_score=min(7.0/max(overall_first,1), 1.0)
        fitness=winrate*0.7 + prize_score*0.2 + first_score*0.1
        print(f"\nTOTAL {total_w}W-{total_l}L-{total_d}D winrate={winrate:.3f} first={overall_first:.1f} (opp {overall_first_opp:.1f}) prize_T9={overall_prize:.2f} (opp {overall_prize_opp:.2f}) turns={overall_turn:.1f} fitness={fitness:.3f}")
        result={"winrate":winrate, "first_prize_turn":overall_first, "prize_by_T9":overall_prize, "turns":overall_turn, "fitness":fitness, "w":total_w, "l":total_l, "d":total_d, "first_opp":overall_first_opp, "prize_T9_opp":overall_prize_opp}
        Path("kaggle_results/tempo_latest.json").write_text(json.dumps(result, indent=2))
    else:
        print("no decks")

if __name__=="__main__":
    main()
