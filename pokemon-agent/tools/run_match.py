"""Local arena: play N episodes between two agents on the real cabt engine.

Usage
-----
    python tools/run_match.py --a agents/main_heuristic.py --b agents/main_random.py --games 20
    python tools/run_match.py --a agents/main_heuristic.py --b agents/main_random.py --bo 3

Agents are plain ``agent(obs) -> list[int]`` callables loaded from a .py file,
exactly like a Kaggle submission.  Each agent brings its own deck (the engine
reads it from the agent's first action when ``select is None``).

Reports win rate, draws, crashes and per-game wall time.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_agent(path: str, name: str):
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if not hasattr(mod, "agent"):
        raise SystemExit(f"{path} does not define agent(obs)")
    return mod.agent


def run(a_path: str, b_path: str, games: int, bo: int, verbose: bool) -> int:
    from kaggle_environments import make

    a = load_agent(a_path, "agent_a")
    b = load_agent(b_path, "agent_b")

    wins = [0, 0]
    draws = 0
    errors = 0
    times: list[float] = []

    for g in range(games):
        # Alternate sides so turn-order effects cancel out.
        first, second = (a, b) if g % 2 == 0 else (b, a)
        env = make("cabt", configuration={"bo": bo}, debug=False)
        t0 = time.perf_counter()
        try:
            env.run([first, second])
        except Exception as exc:  # engine-level failure
            errors += 1
            print(f"game {g}: ENGINE ERROR {type(exc).__name__}: {exc}")
            continue
        dt = time.perf_counter() - t0
        times.append(dt)

        final = env.steps[-1]
        r0 = final[0].get("reward")
        r1 = final[1].get("reward")
        if r0 == 1:
            wins[0 if g % 2 == 0 else 1] += 1
            outcome = "A wins"
        elif r1 == 1:
            wins[1 if g % 2 == 0 else 0] += 1
            outcome = "B wins"
        else:
            draws += 1
            outcome = "draw"

        if verbose:
            st0 = final[0].get("status")
            st1 = final[1].get("status")
            rounds = env.steps[-1][0].get("observation", {}).get("current", {}) or {}
            print(
                f"game {g:>3} (A={'P1' if g % 2 == 0 else 'P2'}): {outcome:8s} "
                f"bo_result={env.result} status={st0}/{st1} {dt:.2f}s"
            )
        else:
            print(f"game {g:>3}: {outcome}", end="\r", flush=True)

    total = games if not errors else games - errors
    print()
    print("=" * 58)
    print(f"A  {os.path.basename(a_path):<28} wins={wins[0]}")
    print(f"B  {os.path.basename(b_path):<28} wins={wins[1]}")
    print(f"draws={draws}  engine_errors={errors}  games={total}  bo={bo}")
    if total > 0:
        print(f"A win rate = {wins[0] / total:.3f}")
    if times:
        print(
            f"time/game: mean={statistics.mean(times):.2f}s "
            f"median={statistics.median(times):.2f}s max={max(times):.2f}s"
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=os.path.join(ROOT, "agents", "main_heuristic.py"))
    ap.add_argument("--b", default=os.path.join(ROOT, "agents", "main_random.py"))
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--bo", type=int, default=1, help="1 = single game, 3 = best of three")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    return run(args.a, args.b, args.games, args.bo, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
