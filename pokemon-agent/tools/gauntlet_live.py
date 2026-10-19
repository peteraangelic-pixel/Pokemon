#!/usr/bin/env python3
"""Gauntlet vs live top10 + archetypes — combined fitness for Gen8.

Usage:
  python tools/gauntlet_live.py --games 20 --our-deck decks/v3_boss33.csv --agent agents/best_from_search.py
  python tools/gauntlet_live.py --games 20 --our-deck decks/v3_boss33.csv --agent search_results/best_agent_gen5.py
"""

import argparse, sys, pathlib, collections, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))

from deck_rules import load_library, deck_problems
from archetypes import ARCHETYPES, our_deck as archetype_our_deck

def load_deck_file(path):
    ids=[]
    with open(path) as fh:
        for line in fh:
            for tok in line.replace(","," ").split():
                if tok.strip():
                    try:
                        ids.append(int(tok))
                    except:
                        pass
    return ids

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

def run_matches(our_deck, opp_deck, agent_path, games, bo=1):
    from kaggle_environments import make
    # Load fresh each time to avoid state leakage
    base=load_agent(agent_path, f"agent_{abs(hash(str(our_deck)))%100000}_our")
    rebind_deck(base, our_deck)
    us=make_deck_agent(base.agent, our_deck)

    opp_mod=load_agent(agent_path, f"agent_{abs(hash(str(opp_deck)))%100000}_opp")
    rebind_deck(opp_mod, opp_deck)
    them=make_deck_agent(opp_mod.agent, opp_deck)

    wins=losses=draws=0
    for g in range(games):
        pair=[us,them] if g%2==0 else [them,us]
        env=make("cabt", configuration={"bo": bo}, debug=False)
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
    ap=argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--bo", type=int, default=1)
    ap.add_argument("--our-deck", default="decks/v3_boss33.csv")
    ap.add_argument("--agent", default="agents/main_heuristic.py")
    ap.add_argument("--live-dir", default="decks/top7_live")
    ap.add_argument("--include-archetypes", action="store_true", help="include 11 archetypes gauntlet")
    ap.add_argument("--only", default=None, help="comma separated filter")
    args=ap.parse_args()

    our_deck=load_deck_file(args.our_deck)
    lib=load_library()
    probs=deck_problems(our_deck, lib)
    if probs:
        print(f"Our deck illegal: {probs}")
        return 1

    print(f"Our deck: {args.our_deck} {len(our_deck)} cards")
    print(f"Agent: {args.agent}")
    print(f"Games per matchup: {args.games} (alternating seats)")

    results=[]

    # Live decks
    live_dir=pathlib.Path(args.live_dir)
    if live_dir.exists():
        live_decks=list(live_dir.glob("*.csv"))
        live_decks=[p for p in live_decks if not p.name.startswith("_")]
        print(f"\nLive decks: {len(live_decks)} in {live_dir}")
        for dp in sorted(live_decks):
            if args.only and dp.stem not in args.only.split(","):
                continue
            opp=load_deck_file(dp)
            if len(opp)!=60:
                continue
            # legality check
            if deck_problems(opp, lib):
                print(f"  {dp.stem} SKIPPED illegal")
                continue
            rate,w,l,d=run_matches(our_deck, opp, args.agent, games=args.games, bo=args.bo)
            results.append((f"live:{dp.stem}", rate, w, l, d))
            print(f"  {dp.stem:<35} {rate:.3f} ({w}-{l} d{d})")

    # Archetypes
    if args.include_archetypes:
        print(f"\nArchetypes: {len(ARCHETYPES)}")
        for name,spec in ARCHETYPES.items():
            if name=="ours":
                continue
            if args.only and name not in args.only.split(","):
                continue
            deck=spec["deck"]()
            if deck_problems(deck, lib):
                print(f"  {name} SKIPPED illegal")
                continue
            rate,w,l,d=run_matches(our_deck, deck, args.agent, games=args.games, bo=args.bo)
            results.append((f"arch:{name}", rate, w, l, d))
            print(f"  {name:<35} {rate:.3f} ({w}-{l} d{d})  {spec['note']}")

    # Summary
    results.sort(key=lambda x: x[1])
    print("\n=== Sorted worst first ===")
    for name,rate,w,l,d in results:
        print(f"{name:<40} {rate:.3f} ({w}-{l})")

    overall_w=sum(r[2] for r in results)
    overall_l=sum(r[3] for r in results)
    if overall_w+overall_l>0:
        print(f"\nOverall: {overall_w/(overall_w+overall_l):.3f} ({overall_w}-{overall_l}) over {len(results)} matchups x {args.games} games")

if __name__=="__main__":
    main()
