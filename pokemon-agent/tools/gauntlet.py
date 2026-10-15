"""Local gauntlet: our agent + our deck against a spread of archetypes.

Why this exists
---------------
The Kaggle ladder only tells us *that* we are losing, days later, averaged over
an unknown field.  This tells us *what* we lose to, today, with a known deck on
the other side of the table.

Both seats play the same policy (agents/main_heuristic.py), so the deck and the
matchup are the only variables -- which is exactly what we want to measure.
The opponent copy gets its plan rebuilt for its own list (tools/archetypes.py),
otherwise it would be playing a mill plan with a beatdown deck.

Every game is run from both seats.  That matters: we measured a 63.3% win rate
for whoever goes first, so a one-sided sample is mostly measuring turn order.

Usage
-----
    .venv/bin/python tools/gauntlet.py --games 60
    .venv/bin/python tools/gauntlet.py --games 100 --only crustle_wall,bronzong_lock
    .venv/bin/python tools/gauntlet.py --games 40 --bo 3

Output is our win rate per archetype, worst first -- that ordering *is* the
blacklist that tells us what Phase 2 has to fix.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from archetypes import ARCHETYPES, our_deck  # noqa: E402
from deck_rules import deck_problems, load_library  # noqa: E402

DEFAULT_AGENT = os.path.join(ROOT, "agents", "main_heuristic.py")


def load_agent(path: str, name: str):
    """Load an agent module under a unique name (we need many copies alive)."""
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if not hasattr(mod, "agent"):
        raise SystemExit(f"{path} does not define agent(obs)")
    return mod


def rebind_deck(mod, deck: list[int]) -> None:
    """Point a loaded heuristic at a different deck and rebuild its plan.

    The agent infers its win condition (primary attacker, evolution line, prize
    values) from its own 60 cards at import time.  Handing it a new deck without
    rebuilding that leaves it playing our mill plan with somebody else's cards.
    """
    mod.DECK = list(deck)
    mod.PLAN = mod._build_plan(mod.DECK)
    mod._PRIMARY_ATK_POWER = 0
    primary = mod.PLAN.get("primary")
    if primary is not None:
        for aid in mod.card(primary).get("atk") or []:
            mod._PRIMARY_ATK_POWER = max(
                mod._PRIMARY_ATK_POWER, int(mod.attack_data(aid).get("d") or 0)
            )


def make_deck_agent(inner, deck: list[int]):
    """Wrap an agent so the engine reads `deck` from its opening action.

    The wrapper takes EXACTLY one parameter.  kaggle_environments inspects the
    callable's arity and calls a 2-parameter callable the legacy way as
    (observation, configuration) -- an extra defaulted argument would silently
    hand the environment config in as the observation.
    """

    def wrapped(obs):
        if not obs or obs.get("select") is None:
            return list(deck)
        return inner(obs)

    return wrapped


def _z(wins: int, games: int) -> float:
    """z-score against the 50% null, with a continuity correction."""
    if games == 0:
        return 0.0
    return (wins - games / 2 - 0.5) / math.sqrt(games * 0.25)


def load_deck_file(path: str) -> list[int]:
    ids = []
    with open(path) as fh:
        for line in fh:
            for tok in line.replace(",", " ").split():
                if tok.strip():
                    ids.append(int(tok))
    return ids


def run(agent_path: str, games: int, bo: int, only: list[str] | None,
        seat_split: bool, deck_file: str | None = None) -> int:
    from kaggle_environments import make

    lib = load_library()
    our = load_deck_file(deck_file) if deck_file else our_deck()
    probs = deck_problems(our, lib)
    if probs:
        raise SystemExit(f"our own deck.csv is illegal: {probs}")

    base = load_agent(agent_path, "gauntlet_ours")
    us = make_deck_agent(base.agent, our)

    names = list(ARCHETYPES)
    if only:
        names = [n for n in names if n in only]
        unknown = set(only) - set(ARCHETYPES)
        if unknown:
            raise SystemExit(f"unknown archetype(s): {sorted(unknown)}")

    results = []
    print(f"gauntlet: {len(names)} archetypes x {games} games/seat, bo={bo}")
    print(f"agent: {os.path.basename(agent_path)}   our deck: {len(our)} cards"
          f"{'  (' + os.path.basename(deck_file) + ')' if deck_file else ' (deck.csv)'}")
    print()

    for name in names:
        spec = ARCHETYPES[name]
        deck = spec["deck"]()
        probs = deck_problems(deck, lib)
        if probs:
            print(f"  {name:<20} SKIPPED - illegal deck: {probs}")
            continue

        opp_mod = load_agent(agent_path, f"gauntlet_{name}")
        rebind_deck(opp_mod, deck)
        them = make_deck_agent(opp_mod.agent, deck)

        wins = losses = draws = errors = 0
        seats = [0, 1] if seat_split else [0]
        per_seat = max(1, games // len(seats))
        seat_wins = {s: 0 for s in seats}
        seat_games = {s: 0 for s in seats}
        t0 = time.perf_counter()

        for seat in seats:
            for g in range(per_seat):
                pair = [us, them] if seat == 0 else [them, us]
                env = make("cabt", configuration={"bo": bo}, debug=False)
                try:
                    env.run(pair)
                except Exception:  # noqa: BLE001 - engine-level failure
                    errors += 1
                    with open("/tmp/gauntlet_errors.log", "a") as fh:
                        fh.write(f"--- {name} seat{seat} game{g}\n{traceback.format_exc()}\n")
                    continue

                final = env.steps[-1]
                r0 = final[0].get("reward")
                r1 = final[1].get("reward")
                our_seat = 0 if seat == 0 else 1
                seat_games[seat] += 1
                if r0 == 1 and r1 != 1:
                    w = our_seat == 0
                elif r1 == 1 and r0 != 1:
                    w = our_seat == 1
                else:
                    draws += 1
                    continue
                if w:
                    wins += 1
                    seat_wins[seat] += 1
                else:
                    losses += 1

        total = wins + losses
        rate = wins / total if total else 0.0
        results.append(
            {
                "name": name,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "errors": errors,
                "rate": rate,
                "z": _z(wins, total),
                "seat0": (seat_wins[0] / seat_games[0]) if seat_games.get(0) else None,
                "seat1": (seat_wins[1] / seat_games[1]) if seat_games.get(1) else None,
                "secs": time.perf_counter() - t0,
                "note": spec["note"],
            }
        )
        s0 = f"{results[-1]['seat0']:.3f}" if results[-1]["seat0"] is not None else "  -  "
        s1 = f"{results[-1]['seat1']:.3f}" if results[-1]["seat1"] is not None else "  -  "
        print(
            f"  {name:<20} {rate:6.3f}  ({wins:>3}-{losses:<3}) "
            f"seat0={s0} seat1={s1} draw={draws} err={errors} "
            f"{results[-1]['secs']:5.1f}s"
        )

    # ---- report -----------------------------------------------------------
    print()
    print("=" * 104)
    print(f"{'archetype':<20} {'our win rate':>12} {'z':>7} {'W-L':>10}   note")
    print("-" * 104)
    results.sort(key=lambda r: r["rate"])
    for r in results:
        flag = ""
        if r["z"] <= -2:
            flag = "  <-- BAD"
        elif r["z"] >= 2:
            flag = "  <-- good"
        print(
            f"{r['name']:<20} {r['rate']:>12.3f} {r['z']:>7.2f} "
            f"{str(r['wins']) + '-' + str(r['losses']):>10}   {r['note']}{flag}"
        )
    print("-" * 104)
    tot_w = sum(r["wins"] for r in results)
    tot_l = sum(r["losses"] for r in results)
    tot_e = sum(r["errors"] for r in results)
    if tot_w + tot_l:
        print(
            f"overall {tot_w / (tot_w + tot_l):.3f}  "
            f"({tot_w}-{tot_l}, {tot_e} engine errors)   "
            f"worst: {results[0]['name'] if results else '-'}"
        )
    print()
    print("z <= -2 means we are losing that matchup for real, not noise.")
    print("Any engine error is written to /tmp/gauntlet_errors.log")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=DEFAULT_AGENT)
    ap.add_argument("--games", type=int, default=60,
                    help="games per archetype, split across seats")
    ap.add_argument("--bo", type=int, default=1)
    ap.add_argument("--only", default="",
                    help="comma-separated subset of archetypes")
    ap.add_argument("--deck-file", default=None,
                    help="test a deck variant instead of deck.csv")
    ap.add_argument("--one-seat", action="store_true",
                    help="play everything from seat 0 (faster, but turn order biases it)")
    args = ap.parse_args()
    only = [s for s in args.only.split(",") if s.strip()] or None
    return run(args.agent, args.games, args.bo, only, not args.one_seat,
               args.deck_file)


if __name__ == "__main__":
    raise SystemExit(main())
