#!/usr/bin/env python3
"""Decision diagnostics: compare policy vs champion behaviour, focused on
bench development. Intercepts every decision of both players over N games."""
import argparse, ctypes, json, sys, uuid
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gauntlet_ffi as G  # noqa: E402

CI = json.loads((ROOT / "tools/card_index.json").read_text())
CARDS = CI["cards"]
OTYPE = {0: "NONE", 1: "YES", 2: "NO", 3: "CARD", 4: "ATTACK", 5: "MOVE",
         6: "COUNT", 7: "PLAY", 8: "ATTACH", 9: "EVOLVE", 10: "ABILITY",
         11: "DISCARD", 12: "RETREAT", 13: "ATTACK", 14: "END", 15: "SKILL"}


def is_basic_poke(cid):
    if cid is None:
        return False
    r = CARDS.get(str(cid)) or {}
    return bool(r.get("b")) and r.get("ct") == 0


def resolve_card(opt, obs, me):
    if opt.get("cardId") is not None and opt.get("area") is None:
        return opt.get("cardId")
    area, idx = opt.get("area"), opt.get("index")
    if idx is None:
        return None
    if area is None and opt.get("type") in (7, 8, 9, 11):
        cur0 = obs.get("current") or {}
        pl = cur0.get("players") or []
        if pl:
            hand = pl[me].get("hand") or []
            if 0 <= idx < len(hand):
                return (hand[idx] or {}).get("id")
        return None
    cur = obs.get("current") or {}
    players = cur.get("players") or []
    owner = opt.get("playerIndex", me)
    if area == 2 and owner == me and players:
        hand = players[me].get("hand") or []
        if 0 <= idx < len(hand):
            return (hand[idx] or {}).get("id")
    if area in (4, 5) and 0 <= owner < len(players):
        zone = players[owner].get("active" if area == 4 else "bench") or []
        if 0 <= idx < len(zone):
            return (zone[idx] or {}).get("id")
    return None


class Diag:
    def __init__(self):
        self.opp_total = Counter()
        self.opp_taken = Counter()
        self.opp_total0 = Counter()
        self.opp_taken0 = Counter()
        self.chosen_types = defaultdict(Counter)
        self.bench_by_turn = defaultdict(lambda: defaultdict(list))
        self.hand_basics_at_opp = defaultdict(list)
        self.examples = []

    def inspect(self, obs, dec, who, turn_no):
        cur = obs.get("current") or {}
        me = int(cur.get("yourIndex", 0))
        players = cur.get("players") or []
        if me >= len(players):
            return
        mp = players[me]
        bench_n = len([b for b in (mp.get("bench") or []) if b])
        sel = obs.get("select") or {}
        opts = sel.get("option") or []
        self.bench_by_turn[who][turn_no].append(bench_n + (1 if (mp.get("active") or [None])[0] else 0))
        bench_opts = []
        for i, o in enumerate(opts):
            if o.get("type") == 7 and is_basic_poke(resolve_card(o, obs, me)):
                bench_opts.append(i)
        chosen = dec[0] if dec else None
        if chosen is not None and 0 <= chosen < len(opts):
            self.chosen_types[who][OTYPE.get(opts[chosen].get("type"), "?")] += 1
        if bench_opts and bench_n < 5:
            self.opp_total[who] += 1
            hand_b = sum(1 for h in (mp.get("hand") or []) if is_basic_poke((h or {}).get("id")))
            self.hand_basics_at_opp[who].append(hand_b)
            if chosen in bench_opts:
                self.opp_taken[who] += 1
            if bench_n == 0:
                self.opp_total0[who] += 1
                if chosen in bench_opts:
                    self.opp_taken0[who] += 1
                elif who == "policy" and len(self.examples) < 6:
                    self.examples.append({
                        "turn_no": turn_no, "bench_n": bench_n,
                        "select": sel, "chosen": chosen,
                        "bench_opts": bench_opts,
                        "hand_ids": [(h or {}).get("id") for h in (mp.get("hand") or [])],
                    })


def play(lib, pol, champ, deck, seat_pol, diag):
    cards = (ctypes.c_int * 120)(*deck, *deck)
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        return None
    agents = {seat_pol: ("policy", pol), (1 - seat_pol): ("champ", champ)}
    turns = Counter()
    r = None
    try:
        for _ in range(5000):
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                r = res
                break
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            who, fn = agents[me]
            dec = fn(obs)
            if not isinstance(dec, list) or not dec:
                dec = [0]
            diag.inspect(obs, dec, who, turns[who])
            turns[who] += 1
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/main_policy_v60.py")
    ap.add_argument("--opp", default="agents/c87_v44.py")
    ap.add_argument("--deck", default="decks/v57_trolley34w.csv")
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--dump", default="/tmp/diag_examples.json")
    args = ap.parse_args()

    deck = G.load_deck(ROOT / args.deck)
    pol = G.load_module(str(ROOT / args.agent), f"_dg_p_{uuid.uuid4().hex[:8]}")
    G.rebind(pol, deck)
    champ = G.load_module(str(ROOT / args.opp), f"_dg_c_{uuid.uuid4().hex[:8]}")
    G.rebind(champ, deck)
    lib = G.get_lib()
    diag = Diag()
    W = L = 0
    for g in range(args.games):
        r = play(lib, pol.agent, champ.agent, deck, g % 2, diag)
        if r is None or r == 2:
            continue
        if r == g % 2:
            W += 1
        else:
            L += 1
    n = W + L
    print(f"games={args.games} policy W-L={W}-{L} WR={W/max(n,1):.3f}")
    for who in ("policy", "champ"):
        t, k = diag.opp_total[who], diag.opp_taken[who]
        t0, k0 = diag.opp_total0[who], diag.opp_taken0[who]
        print(f"[{who}] bench-play: taken {k}/{t} = {k/max(t,1):.3f} | at bench==0: {k0}/{t0} = {k0/max(t0,1):.3f}")
        hb = diag.hand_basics_at_opp[who]
        if hb:
            print(f"[{who}] hand basics at opportunity: mean={sum(hb)/len(hb):.2f}")
        print(f"[{who}] chosen option types: {dict(diag.chosen_types[who].most_common())}")
        bt = {tn: round(sum(v)/len(v), 2) for tn, v in sorted(diag.bench_by_turn[who].items()) if tn < 9}
        print(f"[{who}] board size by own decision no: {bt}")
    Path(args.dump).write_text(json.dumps(diag.examples, indent=1, default=str))
    print("examples ->", args.dump)


if __name__ == "__main__":
    main()
