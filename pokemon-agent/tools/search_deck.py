#!/usr/bin/env python3
"""Search for best deck composition vs combined losses + top7_live.

We have base Pokemon: Snover x4, Abomasnow x4, Kyogre x2 = 10 cards
Energy: 26-33 Water
Trainers: choose from Lillie x4, Mega Signal x4, Boss x2-3, Cyrano 1-2, Night 1-2, Poke Pad 1-3, Ultra 1-2, Waitress 1-4, etc.
We need 60 cards total.

We evaluate vs all_eval (39 decks) with 2 games each, using best_agent_gen5.
"""

import argparse, itertools, random, pathlib, sys, os, json, subprocess, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))

from deck_rules import load_library, deck_problems

# Base
Snover=722
Aboma=723
Kyogre=721
WATER=3

LILLIE=1227
MEGA=1145
BOSS=1182
CYRANO=1205
NIGHT=1097
POKE_PAD=1152
ULTRA=1121
WAITRESS=1235
BELT=1158
JUDGE=1213
HAUL=1414
POWERGLASS=1163
SWITCH=1123

def make_deck(energy, trainers):
    deck=[Snover]*4+[Aboma]*4+[Kyogre]*2+[WATER]*energy
    for cid,cnt in trainers:
        deck+=[cid]*cnt
    return deck

def check(deck):
    lib=load_library()
    probs=deck_problems(deck, lib)
    return probs

def evaluate(deck_path, agent_path, eval_dir, games):
    # Use gauntlet_live.py
    cmd=[sys.executable, str(ROOT/"tools"/"gauntlet_live.py"),
         "--games", str(games),
         "--our-deck", str(deck_path),
         "--agent", str(agent_path),
         "--live-dir", str(eval_dir)]
    env=os.environ.copy()
    # Use best_agent_gen5 env? No, just default
    result=subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    out=result.stdout+result.stderr
    m=re.search(r"Overall:\s+([0-9.]+)", out)
    if m:
        return float(m.group(1)), out
    return 0.0, out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--eval-dir", default="decks/all_eval")
    ap.add_argument("--agent", default="search_results/best_agent_gen5.py")
    ap.add_argument("--trials", type=int, default=20)
    args=ap.parse_args()

    lib=load_library()
    best_rate=0
    best_deck=None
    best_desc=None

    for trial in range(args.trials):
        # Random energy 26-33
        energy=random.randint(26,33)
        # Trainers: we need 50-energy cards = 60 -10 -energy = 50-energy
        # For energy 30, need 20 trainers; for 26, need 24 trainers
        needed=50-energy
        # Randomly choose trainer counts
        # We have mandatory Lillie x4, Mega x4? Let's make them variable but at least 3 each
        # For simplicity, generate random counts for each trainer type, then trim to needed
        pool=[
            (LILLIE, 4),
            (MEGA, 4),
            (BOSS, random.choice([2,3])),
            (CYRANO, random.randint(1,2)),
            (NIGHT, random.randint(1,2)),
            (POKE_PAD, random.randint(1,3)),
            (ULTRA, random.randint(1,2)),
            (WAITRESS, random.randint(1,4)),
            (BELT, random.choice([0,1])),
            (JUDGE, random.choice([0,1])),
            (HAUL, random.choice([0,1,2])),
            (POWERGLASS, random.choice([0,1,2])),
            (SWITCH, random.choice([0,1,2])),
        ]
        # Flatten to list of cids with counts
        trainers=[]
        total=0
        for cid,maxcnt in pool:
            if isinstance(maxcnt, tuple):
                cnt=maxcnt[1]
            else:
                cnt=maxcnt
            # For some, maxcnt is already count, for others random
            # Actually pool already has counts, so use them
            # But we need to ensure total == needed
            # We'll add one by one until needed
            pass

        # Better: build trainers list with random counts, then adjust
        trainers=[]
        # Start with base: Lillie 4, Mega 4, Boss 2-3
        trainers.append((LILLIE, 4))
        trainers.append((MEGA, 4))
        trainers.append((BOSS, random.choice([2,3])))
        # Add others randomly until we reach needed
        options=[(CYRANO,2),(NIGHT,2),(POKE_PAD,3),(ULTRA,2),(WAITRESS,4),(BELT,1),(JUDGE,1),(HAUL,2),(POWERGLASS,2),(SWITCH,2)]
        # Shuffle options
        random.shuffle(options)
        total=sum(c for _,c in trainers)
        for cid,maxc in options:
            if total>=needed:
                break
            cnt=random.randint(1, maxc) if maxc>1 else 1
            if total+cnt>needed:
                cnt=needed-total
            trainers.append((cid,cnt))
            total+=cnt

        # If still not enough, fill with random from options
        while total<needed:
            cid,maxc=random.choice(options)
            cnt=1
            if total+cnt>needed:
                cnt=needed-total
            trainers.append((cid,cnt))
            total+=cnt

        # If too many, trim
        # For simplicity, if total != needed, skip
        if total!=needed:
            continue

        deck=make_deck(energy, trainers)
        if len(deck)!=60:
            continue
        probs=check(deck)
        if probs:
            continue

        # Write temp deck
        tmp_path=ROOT/f"decks/gen8/tmp_trial_{trial}.csv"
        tmp_path.write_text("\n".join(str(x) for x in deck))

        rate,out=evaluate(tmp_path, args.agent, args.eval_dir, args.games)
        print(f"Trial {trial}: energy {energy} trainers {trainers} -> {rate:.3f}")
        if rate>best_rate:
            best_rate=rate
            best_deck=deck
            best_desc=(energy, trainers, rate, out)
            # Save best
            best_path=ROOT/"decks/gen8/best_from_deck_search.csv"
            best_path.write_text("\n".join(str(x) for x in deck))
            print(f"  NEW BEST {rate:.3f} saved to {best_path}")

    print(f"\nBest overall: {best_rate:.3f}")
    if best_desc:
        print(best_desc)

if __name__=="__main__":
    main()
