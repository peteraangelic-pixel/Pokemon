import random, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
from deck_rules import load_library, deck_problems

TRAINERS = [1145,1227,1182,1152,1097,1205,1235,1414,1213,1158,1163,1121,1262,1092,1219]
POKEMON = [721,721,722,722,722,722,723,723,723,723]
ENERGY_ID = 3

def random_deck():
    energy = random.randint(30,35)
    remaining = 60 - 10 - energy
    deck = POKEMON.copy() + [ENERGY_ID]*energy
    for _ in range(remaining):
        deck.append(random.choice(TRAINERS))
    random.shuffle(deck)
    return deck, energy

def write_deck(deck, path):
    with open(path,"w") as f:
        for cid in deck:
            f.write(f"{cid}\n")

def eval_deck_rust(deck_path, agent_path, eval_dir, games):
    rust_bin = ROOT/"rust"/"bin"/"rust_gauntlet"
    cmd = [str(rust_bin), "--our-deck", str(deck_path), "--agent", agent_path, "--live-dir", eval_dir, "--games", str(games)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    out = result.stdout
    for line in out.splitlines():
        if "Overall:" in line:
            try:
                rate = float(line.split()[1])
                wl_part = line.split("(")[1].split(")")[0]
                w,l = map(int, wl_part.split("-")[:2])
                return rate, w, l
            except:
                pass
    return 0.0,0,0

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--agent", default="search_results/best_agent_gen5.py")
    args=ap.parse_args()

    lib=load_library()
    best_score=0
    best_deck=None

    for trial in range(args.trials):
        deck, energy = random_deck()
        if deck_problems(deck, lib):
            continue
        tmp_path=ROOT/f"decks/gen8/tmp_trial_{trial}.csv"
        write_deck(deck, tmp_path)
        rate_top, w_top, l_top = eval_deck_rust(tmp_path, args.agent, "decks/top7_live", args.games)
        rate_loss, w_loss, l_loss = eval_deck_rust(tmp_path, args.agent, "decks/losses_v8", args.games)
        # Weighted: 70% top7, 30% losses
        weighted = 0.7*rate_top + 0.3*rate_loss
        print(f"Trial {trial}: {energy}E top {rate_top:.3f} ({w_top}-{l_top}) loss {rate_loss:.3f} ({w_loss}-{l_loss}) weighted {weighted:.3f}")
        if weighted>best_score:
            best_score=weighted
            best_deck=deck
            best_out=ROOT/"decks/v9_best.csv"
            write_deck(deck, best_out)
            print(f"  NEW BEST weighted {weighted:.3f} -> {best_out}")

    print(f"Best weighted {best_score:.3f}")

if __name__=="__main__":
    main()
