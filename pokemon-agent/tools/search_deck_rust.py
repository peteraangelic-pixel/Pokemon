#!/usr/bin/env python3
"""Random deck search using Rust gauntlet for speed"""
import random, pathlib, subprocess, sys, json, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
from deck_rules import load_library, deck_problems

# Trainer pool
TRAINERS = [
    1145, # Mega Signal
    1227, # Lillie
    1182, # Boss
    1152, # Pad
    1097, # Night Stretcher
    1205, # Cyrano
    1235, # Waitress
    1414, # Haul
    1213, # Judge
    1158, # Belt
    1163, # Powerglass
    1121, # Ultra Ball
    1262, # Beach
    1092, # Secret Box
    1219, # Petrel
]

POKEMON = [721,721,722,722,722,722,723,723,723,723] # 2+4+4=10
ENERGY_ID = 3

def random_deck():
    energy = random.randint(26,35)
    remaining = 60 - 10 - energy
    # Random trainers
    deck = POKEMON.copy()
    deck += [ENERGY_ID]*energy
    # Fill remaining with random trainers
    for _ in range(remaining):
        deck.append(random.choice(TRAINERS))
    random.shuffle(deck)
    return deck, energy

def write_deck(deck, path):
    with open(path,"w") as f:
        for cid in deck:
            f.write(f"{cid}\n")

def eval_deck(deck_path, agent_path, eval_dir, games):
    # Use rust_gauntlet if available
    rust_bin = ROOT/"rust"/"bin"/"rust_gauntlet"
    if rust_bin.exists():
        cmd = [str(rust_bin), "--our-deck", str(deck_path), "--agent", agent_path, "--live-dir", eval_dir, "--games", str(games)]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        out = result.stdout
        # Parse Overall line
        for line in out.splitlines():
            if "Overall:" in line:
                # Overall: 0.705 (31-13) over 22 matchups x 2 games in 17.6s
                try:
                    rate = float(line.split()[1])
                    # Parse wins-losses
                    wl_part = line.split("(")[1].split(")")[0]
                    w,l = map(int, wl_part.split("-")[:2])
                    return rate, w, l
                except:
                    pass
        return 0.0, 0, 0
    else:
        # Fallback to python
        cmd = [str(ROOT/".venv"/"bin"/"python"), "tools/gauntlet_live.py", "--our-deck", str(deck_path), "--agent", agent_path, "--live-dir", eval_dir, "--games", str(games)]
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
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--eval-dir", default="decks/all_eval")
    ap.add_argument("--agent", default="search_results/best_agent_gen5.py")
    args=ap.parse_args()

    lib=load_library()
    best_rate=0
    best_deck=None
    best_path=None

    for trial in range(args.trials):
        deck, energy = random_deck()
        probs=deck_problems(deck, lib)
        if probs:
            # retry
            continue
        tmp_path=ROOT/f"decks/gen8/tmp_trial_{trial}.csv"
        write_deck(deck, tmp_path)
        rate,w,l = eval_deck(tmp_path, args.agent, args.eval_dir, args.games)
        print(f"Trial {trial}: {energy}E rate {rate:.3f} ({w}-{l})")
        if rate>best_rate:
            best_rate=rate
            best_deck=deck
            best_path=tmp_path
            # Save best
            best_out=ROOT/"decks/gen8/best_from_deck_search.csv"
            write_deck(deck, best_out)
            print(f"  NEW BEST {rate:.3f} saved to {best_out}")

    print(f"Best rate {best_rate:.3f}")

if __name__=="__main__":
    main()
