import argparse, ctypes, json, sys, uuid
from pathlib import Path
sys.path.insert(0, 'tools')
import gauntlet_ffi as G

def alive(cur, idx):
    p = cur["players"][idx]
    n = 0
    act = p.get("active")
    if isinstance(act, list): n += sum(1 for q in act if isinstance(q, dict) and int(q.get("hp") or 0) > 0)
    elif isinstance(act, dict) and int(act.get("hp") or 0) > 0: n += 1
    n += sum(1 for b in p.get("bench") or [] if isinstance(b, dict) and int(b.get("hp") or 0) > 0)
    return n

def run(lib, agent, opp, our_deck, opp_deck, seat):
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck), *(opp_deck if seat == 0 else our_deck))
    bp = lib.BattleStart(cards).battlePtr
    if not bp: return 2, None
    r, last = 2, None
    try:
        while True:
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            if int(cur.get("yourIndex", 0)) == seat: last = cur
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1); break
            if obs.get("select") is None: break
            me = int(cur.get("yourIndex", 0))
            dec = agent(obs) if me == seat else opp(obs)
            if not isinstance(dec, list): dec = []
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0: break
    finally:
        lib.BattleFinish(bp)
    return r, last

ap = argparse.ArgumentParser()
ap.add_argument('--agent', required=True); ap.add_argument('--opp', required=True)
ap.add_argument('--our-deck', required=True); ap.add_argument('--opp-deck', required=True)
ap.add_argument('--games', type=int, default=400)
a = ap.parse_args()
our, opp_d = G.load_deck(a.our_deck), G.load_deck(a.opp_deck)
m = G.load_module(a.agent, f"_pt_a_{uuid.uuid4().hex[:8]}"); G.rebind(m, our)
mo = G.load_module(a.opp, f"_pt_o_{uuid.uuid4().hex[:8]}"); G.rebind(mo, opp_d)
lib = G.get_lib()
W = L = 0; loss_taken = []; loss_board = []
for g in range(a.games):
    r, last = run(lib, m.agent, mo.agent, our, opp_d, g % 2)
    if r == 1: W += 1
    elif r == -1:
        L += 1
        if last:
            me = last["players"][g % 2]
            loss_taken.append(6 - len(me.get("prize") or []))
            loss_board.append(alive(last, g % 2))
n = W + L
fam = sum(1 for t in loss_taken if t == 0)
print(f"W={W} L={L} WR={W/max(n,1):.3f} | porazki: 0 nagrod={fam} ({100*fam/max(L,1):.0f}%), sr. nagrod w porazkach={sum(loss_taken)/max(len(loss_taken),1):.2f}, plansza<=1 w porazkach={sum(1 for b in loss_board if b<=1)}/{L}")
