#!/usr/bin/env python3
"""prizetest.py - measure zero-prize losses in mirror, per second branch fa4fe68

Second branch insight: 52% losses end with ZERO prizes, avg 1.17 prizes in losses.
This tool runs gauntlet in mirror (same deck both sides) and reports:
- winrate
- % losses with 0 prizes taken
- avg prizes taken in losses
- distribution of prizes in losses

Usage:
  python tools/prizetest.py --agent agents/v70_alakazam_endgame.py --deck decks/v66_alakazam_simple.csv --games 100
  python tools/prizetest.py --agent agents/v82_kyogre_mirror.py --deck decks/c87_v44.csv --games 100 --mirror
"""
import argparse, json, sys, os, pathlib, math, time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# Try to use gauntlet_ffi if available, else fallback to gauntlet_live
try:
    from gauntlet_ffi import load_deck, load_module, rebind, get_lib, _worker_init, _run_pair, _OUR
    HAS_FFI=True
except Exception as e:
    HAS_FFI=False
    print(f"gauntlet_ffi not available: {e}, need to run in Actions with kaggle-environments")

def run_mirror(agent_path, deck_path, games=100, workers=2):
    # Simplified: use gauntlet_ffi with same deck both sides, but we need prize counts
    # For prize metric, we need to parse logs or use engine's prize counts at end?
    # We'll use gauntlet_ffi's _run_pair which returns W-L-D but not prizes.
    # Instead, we will run a custom loop that captures final prize counts from BattleData.

    import ctypes, json as js
    from gauntlet_ffi import get_lib, load_deck, load_module, rebind

    deck = load_deck(deck_path)
    mod = load_module(agent_path, "_prize_our")
    rebind(mod, deck)
    agent_fn = mod.agent

    opp_mod = load_module(agent_path, "_prize_opp")
    rebind(opp_mod, deck)
    def opp_fn(obs):
        if obs.get("select") is None:
            return list(deck)
        return opp_mod.agent(obs)

    lib = get_lib()
    results=[]
    for g in range(games):
        seat = g % 2
        d0 = deck
        d1 = deck
        # same deck both sides
        cards = (ctypes.c_int * 120)(*d0, *d1)
        sd = lib.BattleStart(cards)
        bp = sd.battlePtr
        if not bp:
            results.append({"win": None, "our_prizes_taken": 0, "opp_prizes_taken": 0, "turn": 0})
            continue
        win=None
        our_prizes_taken=0
        turn=0
        try:
            while True:
                data = lib.GetBattleData(bp)
                obs = js.loads(data.json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res>=0:
                    if res==2:
                        win=None
                    else:
                        win = (res==seat)
                    # try to get prize counts
                    players = cur.get("players") or []
                    if len(players)>=2:
                        # prizes taken = 6 - remaining
                        try:
                            me_p = players[seat]
                            opp_p = players[1-seat]
                            our_rem = len(me_p.get("prize") or [])
                            opp_rem = len(opp_p.get("prize") or [])
                            our_prizes_taken = 6 - opp_rem
                            opp_prizes_taken = 6 - our_rem
                        except:
                            our_prizes_taken=0
                            opp_prizes_taken=0
                    else:
                        our_prizes_taken=0
                        opp_prizes_taken=0
                    turn = cur.get("turn") or 0
                    break
                sel = obs.get("select")
                if sel is None:
                    break
                me_idx = int((cur.get("yourIndex") or 0))
                dec = agent_fn(obs) if me_idx==seat else opp_fn(obs)
                if not isinstance(dec, list):
                    dec=[]
                arg = (ctypes.c_int * len(dec))(*dec)
                if lib.Select(bp, arg, len(dec))!=0:
                    break
        finally:
            lib.BattleFinish(bp)
        results.append({"win": win, "our_prizes_taken": our_prizes_taken, "turn": turn})

    # stats
    wins = sum(1 for r in results if r["win"]==True)
    losses = sum(1 for r in results if r["win"]==False)
    draws = len(results)-wins-losses
    zero_prize_losses = sum(1 for r in results if r["win"]==False and r["our_prizes_taken"]==0)
    avg_prizes_in_loss = sum(r["our_prizes_taken"] for r in results if r["win"]==False) / max(1,losses)
    print(f"Mirror {games} games: {wins}W-{losses}L-{draws}D = {wins/len(results):.3f}")
    print(f"Zero-prize losses: {zero_prize_losses}/{losses} = {zero_prize_losses/max(1,losses):.2%}  (target <30%)")
    print(f"Avg prizes taken in losses: {avg_prizes_in_loss:.2f} (target >2.0)")
    # distribution
    dist=Counter(r["our_prizes_taken"] for r in results if r["win"]==False)
    print(f"Prizes distribution in losses: {dict(sorted(dist.items()))}")
    return results

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--mirror", action="store_true", help="mirror same deck")
    args=ap.parse_args()
    if not HAS_FFI:
        print("Need gauntlet_ffi + libcg.so, run in Actions")
        sys.exit(1)
    run_mirror(args.agent, args.deck, args.games, args.workers)
