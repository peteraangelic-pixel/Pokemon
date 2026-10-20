"""Parallel local gauntlet: many episodes, many cores, no LLM, no GPU.

This is the piece that makes a 16-core desktop useful for the competition: a
full 25-game x N-rollouts sweep of the *real* game engine runs in seconds, so
changes can be validated locally instead of spending the 1-per-day Kaggle
submission on a guess.

Usage:
    python local/gauntlet.py --games all --rollouts 16 --workers 16
    python local/gauntlet.py --games ls20,vc33,ar25 --rollouts 64 --policy heuristic
    python local/gauntlet.py --games all --rollouts 8 --max-steps 400 --out report.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Global per-process cache so workers do not rescan the games on every task.
_WORKER: dict = {}


def _worker_init(games_dir: str) -> None:
    import engine

    _WORKER["games"] = engine.discover_games(Path(games_dir))


def _run_task(task: dict) -> dict:
    import engine
    from policies import build_policy

    info = _WORKER["games"].get(task["game"])
    if info is None:
        return {"game": task["game"], "seed": task["seed"], "levels": 0,
                "win_levels": 0, "steps": 0, "wall_ms": 0.0, "solved": False,
                "error": "unknown game"}
    params = dict(task["params"] or {})
    if task["policy"] == "solution":
        params["paths"] = task.get("paths") or []
    policy = build_policy(task["policy"], params)
    res = engine.run_episode(
        info, task["game"], policy,
        seed=task["seed"], max_steps=task["max_steps"],
    )
    return {
        "game": res.game, "seed": res.seed, "levels": res.levels,
        "win_levels": res.win_levels, "steps": res.steps,
        "wall_ms": round(res.wall_ms, 2), "solved": res.solved,
        "error": res.error,
    }


def run_gauntlet(
    games: list[str],
    rollouts: int,
    workers: int,
    policy: str = "heuristic",
    params: dict | None = None,
    max_steps: int = 1200,
    games_dir: Path | None = None,
) -> dict:
    import engine

    games_dir = games_dir or engine.GAMES_DIR
    # A `solution` run replays stored paths per game, then falls back to the heuristic.
    solutions: dict[str, list] = {}
    if policy == "solution":
        sol_path = Path(params.pop("solutions_file")) if params and params.get("solutions_file") else None
        if sol_path and sol_path.is_file():
            solutions = json.loads(sol_path.read_text()).get("solutions", {})

    tasks = [
        {"game": g, "seed": s,
         "policy": "solution" if policy == "solution" else policy,
         "params": params, "paths": solutions.get(g, []),
         "max_steps": max_steps}
        for g in games for s in range(rollouts)
    ]

    t0 = time.perf_counter()
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init,
                             initargs=(str(games_dir),)) as ex:
        for res in ex.map(_run_task, tasks, chunksize=1):
            results.append(res)
    wall = time.perf_counter() - t0

    # ---- aggregate per game -------------------------------------------
    per_game: dict[str, dict] = {}
    for r in results:
        g = per_game.setdefault(r["game"], {
            "rollouts": 0, "sum_levels": 0, "best_levels": 0,
            "win_levels": r["win_levels"], "levels_hist": {}, "errors": 0,
            "sum_steps": 0,
        })
        g["rollouts"] += 1
        g["sum_levels"] += r["levels"]
        g["best_levels"] = max(g["best_levels"], r["levels"])
        g["sum_steps"] += r["steps"]
        g["levels_hist"][r["levels"]] = g["levels_hist"].get(r["levels"], 0) + 1
        if r["error"]:
            g["errors"] += 1

    total_levels = sum(r["levels"] for r in results)
    max_levels = sum(r["win_levels"] for r in results)
    summary = {
        "policy": policy,
        "params": params,
        "rollouts_per_game": rollouts,
        "max_steps": max_steps,
        "workers": workers,
        "episodes": len(results),
        "wall_s": round(wall, 2),
        "episodes_per_s": round(len(results) / wall, 2) if wall else 0.0,
        "mean_levels": round(total_levels / len(results), 3) if results else 0.0,
        "level_completion_rate": round(total_levels / max_levels, 4) if max_levels else 0.0,
        # Fraction of games where at least one rollout cleared >= 1 level.
        "games_with_progress": sum(
            1 for g in per_game.values() if g["best_levels"] > 0),
        "games_total": len(per_game),
        "games_fully_solved": sum(
            1 for g in per_game.values()
            if g["win_levels"] and g["best_levels"] >= g["win_levels"]),
        "per_game": {
            k: {
                "mean_levels": round(v["sum_levels"] / v["rollouts"], 3),
                "best_levels": v["best_levels"],
                "win_levels": v["win_levels"],
                "mean_steps": round(v["sum_steps"] / v["rollouts"], 1),
                "errors": v["errors"],
                "levels_hist": dict(sorted(v["levels_hist"].items())),
            }
            for k, v in sorted(per_game.items())
        },
    }
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Local parallel ARC-AGI-3 gauntlet")
    ap.add_argument("--games", default="all", help="'all' or comma-separated ids")
    ap.add_argument("--rollouts", type=int, default=16, help="episodes per game")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--policy", default="heuristic",
                    choices=["random", "anti-reverse", "heuristic", "solution"])
    ap.add_argument("--solutions", default="local/solutions.json",
                    help="solution library for --policy solution")
    ap.add_argument("--max-steps", type=int, default=1200)
    ap.add_argument("--params", default=None,
                    help="JSON dict overriding heuristic params")
    ap.add_argument("--out", default=None, help="write JSON report here")
    args = ap.parse_args()

    import engine

    if args.games == "all":
        games = sorted(engine.discover_games().keys())
    else:
        games = [g.strip() for g in args.games.split(",") if g.strip()]

    params = json.loads(args.params) if args.params else None
    if args.policy == "solution":
        params = dict(params or {})
        params["solutions_file"] = args.solutions

    summary = run_gauntlet(
        games=games, rollouts=args.rollouts, workers=args.workers,
        policy=args.policy, params=params, max_steps=args.max_steps,
    )

    print(f"\n{'game':6} {'mean':>6} {'best':>5} {'of':>3} {'steps':>7}  histogram")
    print("-" * 62)
    for g, v in summary["per_game"].items():
        print(f"{g:6} {v['mean_levels']:6.2f} {v['best_levels']:5d} "
              f"{v['win_levels']:3d} {v['mean_steps']:7.0f}  {v['levels_hist']}")
    print("-" * 62)
    print(f"episodes {summary['episodes']} in {summary['wall_s']}s "
          f"({summary['episodes_per_s']} ep/s) on {summary['workers']} workers")
    print(f"level completion rate: {summary['level_completion_rate']:.2%}")
    print(f"games with progress: {summary['games_with_progress']}/"
          f"{summary['games_total']}   fully solved: {summary['games_fully_solved']}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")
        print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
