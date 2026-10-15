"""Robustness fuzzing: run our agent against many *different* opponent decks.

On the ladder we meet arbitrary archetypes, so the agent must survive card ids,
board shapes and selection prompts it has never seen.  A crash is not a lost game,
it is a lost submission slot (status ``Error``).

This tool builds random legal-ish decks from the full card pool and plays our agent
against a random-move pilot using them, checking that:

* our agent never raises,
* the episode always terminates with status DONE/INACTIVE (never ERROR),
* our decisions are always within ``maxCount`` and in range.

Usage:
    python tools/fuzz_robustness.py --agent agents/main_heuristic.py --games 40
"""
from __future__ import annotations

import argparse
import collections
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from deck_rules import deck_is_legal  # noqa: E402
from run_match import load_agent  # noqa: E402


def make_random_deck(rng: random.Random, pool: list[int], library: dict) -> list[int]:
    """A *rules-legal* random deck.

    The engine validates deck construction and rejects violations with
    ``errorType 4`` (confirmed experimentally): at most 4 copies of any card,
    at most 1 ACE SPEC, and basic Energy is unlimited.  Getting this wrong makes
    the engine mark the opponent INVALID and the episode never exercises our
    agent at all -- which is how we found the rule in the first place.
    """
    basics = [c for c in pool if library[c].get("basic") and library[c].get("cardType") == 0]
    evos = [c for c in pool if library[c].get("cardType") == 0 and not library[c].get("basic")]
    trainers = [
        c for c in pool
        if library[c].get("cardType") in (1, 2, 3, 4) and not library[c].get("aceSpec")
    ]
    basic_energy = [c for c in pool if library[c].get("cardType") == 5]
    # ACE SPEC cards (including ACE SPEC *special energies* such as Legacy
    # Energy) are limited to ONE per deck, so we keep them out entirely.
    special_energy = [
        c for c in pool if library[c].get("cardType") == 6 and not library[c].get("aceSpec")
    ]
    if not basics or not basic_energy:
        raise SystemExit("card pool missing basics or basic energy")

    deck: list[int] = []
    used: dict[int, int] = {}

    def add(cid: int, limit: int = 4) -> bool:
        if used.get(cid, 0) >= limit:
            return False
        deck.append(cid)
        used[cid] = used.get(cid, 0) + 1
        return True

    # A main line: 3 copies of a random evolution and 4 of a random Basic.
    main_evo = rng.choice(evos) if evos else None
    main_basic = rng.choice(basics)
    if main_evo is not None:
        for _ in range(3):
            add(main_evo)
    for _ in range(4):
        add(main_basic)

    # ~12 more Pokemon, ~15 trainers, specialised energies, rest basic energy.
    for _ in range(200):
        if len(deck) >= 16:
            break
        add(rng.choice(basics))
    for _ in range(200):
        if len(deck) >= 31:
            break
        add(rng.choice(trainers))
    for _ in range(4):
        add(rng.choice(special_energy))
    energy_pick = rng.choice(basic_energy)
    while len(deck) < 60:
        add(energy_pick, limit=99)
    rng.shuffle(deck)
    deck = deck[:60]
    if not deck_is_legal(deck, library):
        raise ValueError("generator produced an illegal deck")
    return deck


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=os.path.join(ROOT, "agents", "main_heuristic.py"))
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from kaggle_environments import make

    rng = random.Random(args.seed)
    agent = load_agent(args.agent, "fuzz_agent")

    # Build the card pool from the engine itself (same source the agent uses).
    import ctypes
    from kaggle_environments.envs.cabt.cg.sim import lib

    lib.AllCard.restype = ctypes.c_char_p
    lib.AllCard.argtypes = []
    import json

    all_cards = json.loads(lib.AllCard().decode("utf-8"))
    library = {c["cardId"]: c for c in all_cards}
    pool = list(library)

    TRACEBACKS: list[str] = []
    statuses = collections.Counter()
    violations = []
    raises = []

    for g in range(args.games):
        deck = None
        for _attempt in range(200):
            try:
                deck = make_random_deck(rng, pool, library)
                break
            except ValueError:
                continue
        if deck is None:
            raise SystemExit("could not generate a legal deck in 200 attempts")

        def opponent(obs):
            select = obs.get("select")
            if select is None:
                return list(deck)
            opts = select.get("option") or []
            if not opts:
                return []
            k = min(int(select.get("maxCount") or 1), len(opts))
            return random.sample(range(len(opts)), k)

        # NOTE: an agent callable must accept EXACTLY ONE argument.  The
        # harness inspects arity and, if the callable accepts two parameters,
        # calls it the legacy way as (observation, configuration) -- which
        # silently feeds the env configuration in as the observation.  So no
        # default-argument tricks here; bind via a factory instead.
        def make_wrapper(inner):
            def wrapped(obs):
                try:
                    out = inner(obs)
                except Exception as exc:
                    import traceback as _tb
                    raises.append(f"AGENT {type(exc).__name__}: {exc}")
                    TRACEBACKS.append(_tb.format_exc())
                    return []
                select = obs.get("select")
                if select is not None:
                    opts = select.get("option") or []
                    mx = int(select.get("maxCount") or 0)
                    mn = int(select.get("minCount") or 0)
                    if len(out) > mx:
                        violations.append(f"returned {len(out)} > maxCount {mx}")
                    if opts and len(out) < min(mn, len(opts)):
                        violations.append(f"returned {len(out)} < minCount {mn}")
                    if any((not isinstance(i, int)) or i < 0 or i >= len(opts) for i in out):
                        violations.append(f"out-of-range index in {out} (n_opts={len(opts)})")
                    if len(set(out)) != len(out):
                        violations.append(f"duplicate indices {out}")
                return out

            return wrapped

        wrapped = make_wrapper(agent)
        env = make("cabt", configuration={"bo": 1}, debug=False)
        agents = [wrapped, opponent] if g % 2 == 0 else [opponent, wrapped]
        try:
            env.run(agents)
        except Exception as exc:
            import traceback as _tb
            raises.append(f"ENV {type(exc).__name__}: {exc}")
            TRACEBACKS.append(_tb.format_exc())
            continue
        for seat in env.steps[-1]:
            statuses[seat.get("status")] += 1
        if any(seat.get("status") == "INVALID" for seat in env.steps[-1]):
            import collections as _c
            comp = _c.Counter(deck)
            detail = []
            for cid, n in sorted(comp.items()):
                c = library[cid]
                detail.append(
                    f"{n}x {cid}:{c.get('name','?')[:26]} "
                    f"(ct={c.get('cardType')}, basic={bool(c.get('basic'))}, "
                    f"evo={c.get('evolutionType')}, ace={bool(c.get('aceSpec'))}, "
                    f"ef={c.get('evolvesFrom')})"
                )
            print(f"--- INVALID deck (game {g}) error={env.steps[0][0].get('error')} ---")
            for d in detail:
                print("   ", d)

    print(f"seat statuses: {dict(statuses)}")
    print(f"contract violations: {len(violations)}")
    for v in violations[:10]:
        print("   !", v)
    print(f"exceptions: {len(raises)}")
    for r in raises[:10]:
        print("   !", r)
    if TRACEBACKS:
        print("--- first traceback ---")
        print(TRACEBACKS[0])
    bad = statuses.get("ERROR", 0) + statuses.get("INVALID", 0) + statuses.get("TIMEOUT", 0)
    if violations or raises or bad:
        print("FUZZ FAILED")
        return 1
    print("FUZZ PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
