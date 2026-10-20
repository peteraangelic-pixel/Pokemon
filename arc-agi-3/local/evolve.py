"""CEM / evolutionary search over heuristic parameters, on the real engine.

This replaces the `mock_evaluator` placeholder in `llm-agent/evolve_parameters.py`
with an actual fitness signal: the local game engine. Because a step costs
~0.1 ms, a generation of 64 individuals x 25 games x 4 rollouts x ~200 steps is
a few hundred thousand steps -> tens of seconds on a 16-core desktop.

Usage:
    python local/evolve.py --generations 20 --population 64 --workers 16
    python local/evolve.py --games m0r0,r11l,sp80 --generations 30 --epochs-quick
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402
from policies import DEFAULT_PARAMS  # noqa: E402

# Search bounds: (low, high, is_int)
BOUNDS: dict[str, tuple[float, float, bool]] = {
    "temp": (0.05, 4.0, False),
    "novelty_weight": (0.0, 5.0, False),
    "noop_penalty": (0.0, 6.0, False),
    "reverse_penalty": (0.0, 4.0, False),
    "epsilon": (0.0, 0.6, False),
    "click_rate": (0.0, 0.8, False),
    "memory_decay": (0.3, 1.0, False),
    "progress_bonus": (0.0, 10.0, False),
}

_WORKER: dict = {}


def _worker_init(games_dir: str) -> None:
    _WORKER["games"] = engine.discover_games(Path(games_dir))


def _eval_task(task: dict) -> dict:
    import engine as eng
    from policies import build_policy

    info = _WORKER["games"].get(task["game"])
    if info is None:
        return {"ind": task["ind"], "levels": 0, "best": 0, "steps": 0, "error": True}
    pol = build_policy("heuristic", task["params"])
    res = eng.run_episode(info, task["game"], pol, seed=task["seed"],
                          max_steps=task["max_steps"])
    return {"ind": task["ind"], "levels": res.levels, "best": res.levels,
            "steps": res.steps, "error": res.error is not None}


def evaluate_population(pop, games, seeds, workers, max_steps, games_dir):
    tasks = [
        {"ind": i, "params": p, "game": g, "seed": s, "max_steps": max_steps}
        for i, p in enumerate(pop)
        for g in games
        for s in seeds
    ]
    agg = {i: {"levels": 0, "best": 0, "steps": 0, "n": 0, "err": 0} for i in range(len(pop))}
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init,
                             initargs=(str(games_dir),)) as ex:
        for r in ex.map(_eval_task, tasks, chunksize=4):
            a = agg[r["ind"]]
            a["levels"] += r["levels"]
            a["best"] += r["best"]
            a["steps"] += r["steps"]
            a["n"] += 1
            a["err"] += int(bool(r.get("error")))

    fitness = []
    for i in range(len(pop)):
        a = agg[i]
        n = max(1, a["n"])
        mean_levels = a["levels"] / n
        # primary: mean levels; secondary: consistency (best-level rate);
        # tertiary: do not waste steps
        fit = mean_levels + 0.01 * (a["best"] / n) - 1e-6 * (a["steps"] / n)
        fitness.append(fit)
    return fitness, agg


def sample_population(mean, std, size, rng):
    pop = []
    for _ in range(size):
        p = {}
        for k, (lo, hi, is_int) in BOUNDS.items():
            v = rng.gauss(mean.get(k, DEFAULT_PARAMS[k]), std.get(k, 0.5))
            v = min(hi, max(lo, v))
            p[k] = int(round(v)) if is_int else round(v, 4)
        pop.append(p)
    return pop


def main() -> None:
    ap = argparse.ArgumentParser(description="CEM over local ARC-AGI-3 heuristics")
    ap.add_argument("--games", default="all")
    ap.add_argument("--population", type=int, default=32)
    ap.add_argument("--elite-frac", type=float, default=0.25)
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--max-steps", type=int, default=400)
    ap.add_argument("--out", default="local/evolved_params.json")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    games = (sorted(engine.discover_games().keys())
             if args.games == "all" else [g.strip() for g in args.games.split(",")])
    seeds = list(range(args.seeds))

    mean = dict(DEFAULT_PARAMS)
    std = {k: (hi - lo) * 0.25 for k, (lo, hi, _) in BOUNDS.items()}
    best_params, best_fit = dict(mean), -1e9

    print(f"games={len(games)} pop={args.population} gen={args.generations} "
          f"workers={args.workers} -> {len(games) * args.seeds} episodes/individual")

    for gen in range(args.generations):
        t0 = time.perf_counter()
        pop = sample_population(mean, std, args.population, rng)
        pop[0] = dict(best_params) if best_fit > -1e8 else dict(mean)
        fitness, agg = evaluate_population(pop, games, seeds, args.workers,
                                           args.max_steps, engine.GAMES_DIR)
        order = sorted(range(len(pop)), key=lambda i: fitness[i], reverse=True)
        elite_n = max(2, int(len(pop) * args.elite_frac))
        elites = [pop[i] for i in order[:elite_n]]
        if fitness[order[0]] > best_fit:
            best_fit = fitness[order[0]]
            best_params = dict(pop[order[0]])

        for k in BOUNDS:
            vals = [e[k] for e in elites]
            mu = sum(vals) / len(vals)
            var = sum((v - mu) ** 2 for v in vals) / max(1, len(vals) - 1)
            mean[k] = mu
            std[k] = max(1e-3, math.sqrt(var))
        wall = time.perf_counter() - t0
        ep = sum(a["n"] for a in agg.values())
        print(f"gen {gen+1:2d}  best={fitness[order[0]]:.4f}  elite_mean="
              f"{sum(fitness[i] for i in order[:elite_n]) / elite_n:.4f}  "
              f"episodes={ep}  {wall:.1f}s ({ep / wall:.0f} ep/s)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"fitness": best_fit, "params": best_params,
                               "games": games, "seeds": args.seeds,
                               "max_steps": args.max_steps}, indent=2) + "\n")
    print(f"\nbest fitness {best_fit:.4f}")
    print(json.dumps(best_params, indent=2))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
