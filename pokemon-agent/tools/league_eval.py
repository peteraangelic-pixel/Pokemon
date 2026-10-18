"""League round-robin: pilots (agent+deck) graja kazdy z kazdym + rating BT.
Fundament Fazy 2: wspolny metr dla pilotow regulowych / uczonych / search.
Uzycie: .venv/bin/python tools/league_eval.py --games 300 --out league.json
"""
import argparse, ctypes, itertools, json, math, sys, uuid
sys.path.insert(0, 'tools')
import gauntlet_ffi as G


def run_game(lib, agent, opp, our_deck, opp_deck, seat):
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck),
                                  *(opp_deck if seat == 0 else our_deck))
    bp = lib.BattleStart(cards).battlePtr
    if not bp:
        return 2
    r = 2
    try:
        while True:
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1)
                break
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            dec = agent(obs) if me == seat else opp(obs)
            if not isinstance(dec, list):
                dec = []
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    return r


PILOTS = [
    ("champion_v44", "agents/c87_v44.py", "decks/v57_trolley34w.csv"),
    ("v63_live", "agents/v63_super_sub.py", "decks/v57_trolley34w.csv"),
    ("v67_live", "agents/v67_wall_tempo_noimit.py", "decks/v57_trolley34w.csv"),
    ("v70_meta_judge", "agents/v70_judge.py", "decks/v70_judge.csv"),
    ("v70_horizon_c87", "agents/c87_v70h_main.py", "decks/v57_trolley34w.csv"),
    ("v69r_c87", "agents/c87_v69r_main.py", "decks/c87_v69r_deck.csv"),
    ("alakazam_hybrid_v65", "agents/v65_alakazam.py", "decks/v66_alakazam_simple.csv"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=300)
    ap.add_argument('--out', default='kaggle_results/league_table.json')
    a = ap.parse_args()
    lib = G.get_lib()
    mods = {}
    for name, ag, dk in PILOTS:
        deck = G.load_deck(dk)
        m = G.load_module(ag, f"_lg_{name}_{uuid.uuid4().hex[:6]}")
        G.rebind(m, deck)
        mods[name] = (m.agent, deck)
    wins = {n: {} for n, _, _ in PILOTS}
    names = [n for n, _, _ in PILOTS]
    for x, y in itertools.combinations(names, 2):
        W = L = 0
        ax, dx = mods[x]; ay, dy = mods[y]
        for g in range(a.games):
            r = run_game(lib, ax, ay, dx, dy, g % 2)
            if r == 1: W += 1
            elif r == -1: L += 1
        wins[x][y] = (W, L); wins[y][x] = (L, W)
        print(f"{x} vs {y}: {W}-{L}", flush=True)
    # Bradley-Terry (skala jak Kaggle: pole ~1000)
    R = {n: 1000.0 for n in names}
    for _ in range(200):
        for n in names:
            num = den = 0.0
            for o in names:
                if o == n: continue
                w, l = wins[n][o]
                num += w
                den += (w + l) / (1 + 10 ** ((R[o] - R[n]) / 400))
            if den > 0:
                R[n] = 400 * math.log10(max(num, 0.01) / den) if num > 0 else R[n] - 50
        mean = sum(R.values()) / len(R)
        for n in names: R[n] += 1000 - mean
    table = sorted(R.items(), key=lambda kv: -kv[1])
    print("\n=== LIGA (Bradley-Terry, srednia=1000) ===")
    for n, r in table:
        tot_w = sum(wins[n][o][0] for o in names if o != n)
        tot_l = sum(wins[n][o][1] for o in names if o != n)
        print(f"{n:22s} BT={r:7.1f}  bilans {tot_w}W-{tot_l}L")
    json.dump({"ratings": dict(table), "wins": {x: {y: list(wins[x][y]) for y in wins[x]} for x in wins}},
              open(a.out, 'w'), indent=1)
    print("zapisano", a.out)


if __name__ == '__main__':
    main()
