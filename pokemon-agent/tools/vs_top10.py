#!/usr/bin/env python3
"""Simulate our agent vs top10 decks extracted from official replays.

This answers user's question: is it worth competing bare vs top10?

We have 26 decks from top10 dataset, including:
- Revue Crustle wall (hard counter)
- YumeNeko Metal (if present)
- etc.

We test both our mill (deck.csv) and metal (yumeneko_metal.csv) vs each top deck.
"""

import sys, pathlib, json, collections, time, math
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))

from deck_rules import load_library

def load_deck_file(path):
    return [int(l.strip()) for l in open(path) if l.strip()]

def load_agent(path, name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name, pathlib.Path(path).resolve().as_posix())
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def rebind_deck(mod, deck):
    mod.DECK=list(deck)
    mod.PLAN=mod._build_plan(mod.DECK)
    mod._PRIMARY_ATK_POWER=0
    primary=mod.PLAN.get("primary")
    if primary:
        for aid in mod.card(primary).get("atk") or []:
            mod._PRIMARY_ATK_POWER=max(mod._PRIMARY_ATK_POWER, int(mod.attack_data(aid).get("d") or 0))

def make_deck_agent(inner, deck):
    def wrapped(obs):
        if not obs or obs.get("select") is None:
            return list(deck)
        return inner(obs)
    return wrapped

def run_match(our_deck, opp_deck, agent_path, games=20, bo=1):
    from kaggle_environments import make
    base=load_agent(agent_path, f"agent_{hash(str(our_deck))%10000}")
    rebind_deck(base, our_deck)
    us=make_deck_agent(base.agent, our_deck)

    opp_mod=load_agent(agent_path, f"opp_{hash(str(opp_deck))%10000}")
    rebind_deck(opp_mod, opp_deck)
    them=make_deck_agent(opp_mod.agent, opp_deck)

    wins=losses=draws=0
    for g in range(games):
        pair=[us,them] if g%2==0 else [them,us]
        env=make("cabt", configuration={"bo":bo}, debug=False)
        try:
            env.run(pair)
        except Exception:
            continue
        final=env.steps[-1]
        r0=final[0].get("reward")
        r1=final[1].get("reward")
        our_seat=0 if g%2==0 else 1
        if r0==1 and r1!=1:
            if our_seat==0:
                wins+=1
            else:
                losses+=1
        elif r1==1 and r0!=1:
            if our_seat==1:
                wins+=1
            else:
                losses+=1
        else:
            draws+=1
    total=wins+losses
    return wins/total if total else 0, wins, losses, draws

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--top10-dir", default="decks/top10")
    ap.add_argument("--our-deck", default="deck.csv")
    ap.add_argument("--agent", default="agents/main_heuristic.py")
    args=ap.parse_args()

    our_deck=load_deck_file(args.our_deck)
    print(f"Our deck: {args.our_deck} {len(our_deck)} cards")

    top_dir=pathlib.Path(args.top10_dir)
    decks=list(top_dir.glob("*.csv"))
    print(f"Found {len(decks)} top10 decks in {top_dir}")

    results=[]
    for deck_path in sorted(decks)[:15]:
        opp_deck=load_deck_file(deck_path)
        # Quick legality check
        if len(opp_deck)!=60:
            continue
        rate,w,l,d=run_match(our_deck, opp_deck, args.agent, games=args.games, bo=1)
        results.append((deck_path.stem, rate, w, l, d))
        print(f"  {deck_path.stem:<30} {rate:.3f} ({w}-{l} draw {d})")

    print("\n=== Sorted worst first ===")
    results.sort(key=lambda x: x[1])
    for name,rate,w,l,d in results:
        print(f"{name:<30} {rate:.3f} ({w}-{l})")

    overall_w=sum(r[2] for r in results)
    overall_l=sum(r[3] for r in results)
    if overall_w+overall_l>0:
        print(f"\nOverall vs top10: {overall_w/(overall_w+overall_l):.3f} ({overall_w}-{overall_l})")

if __name__=="__main__":
    main()
