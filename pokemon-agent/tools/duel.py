#!/usr/bin/env python3
"""Duel two agents head-to-head on same deck, alternating seats."""
import argparse, ctypes, json, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G

def load(agent_path, deck, tag):
    m = G.load_module(agent_path, f"_duel_{tag}_{uuid.uuid4().hex[:8]}")
    G.rebind(m, deck)
    return m.agent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent-a", required=True)
    ap.add_argument("--agent-b", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--workers", type=int, default=1)
    args=ap.parse_args()

    deck=G.load_deck(args.deck)
    agent_a=load(args.agent_a, deck, "a")
    agent_b=load(args.agent_b, deck, "b")

    lib=G.get_lib()
    w=l=d=0
    for g in range(args.games):
        seat_a = g % 2  # which seat agent A sits
        # decks same, but seats matter for first player
        d0=deck
        d1=deck
        cards=(ctypes.c_int*120)(*d0,*d1)
        sd=lib.BattleStart(cards)
        bp=sd.battlePtr
        if not bp:
            d+=1
            continue
        res=-1
        try:
            step=0
            while True:
                step+=1
                if step>5000:
                    break
                data=lib.GetBattleData(bp)
                obs=json.loads(data.json)
                cur=obs.get("current") or {}
                r=cur.get("result")
                if r is not None and r>=0:
                    res=r
                    break
                sel=obs.get("select")
                if sel is None:
                    break
                me=int(cur.get("yourIndex",0))
                # me == seat_a => agent A to move, else B
                agent = agent_a if me==seat_a else agent_b
                dec=agent(obs)
                if not isinstance(dec, list):
                    dec=[0]
                arg=(ctypes.c_int*len(dec))(*dec)
                if lib.Select(bp, arg, len(dec))!=0:
                    break
        finally:
            lib.BattleFinish(bp)
        if res==2:
            d+=1
        elif res==seat_a:
            w+=1
        elif res>=0:
            l+=1
        else:
            d+=1
        if (g+1)%50==0:
            print(f"{g+1}/{args.games} W{w} L{l} D{d} rate={w/(w+l) if w+l>0 else 0:.3f}", flush=True)
    total=w+l
    rate=w/total if total>0 else 0
    print(f"FINAL A vs B: {w}-{l} D{d} rate={rate:.4f} ({args.agent_a} vs {args.agent_b})")

if __name__=="__main__":
    main()
