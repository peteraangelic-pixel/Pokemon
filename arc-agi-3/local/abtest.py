"""Paired A/B testing and noise measurement for the local ARC-AGI-3 harness.

Why this exists
---------------
The `arc-agi` engine is deterministic for a given seed, and a submission can only
be spent once per day. That makes "did my change actually help?" the single most
expensive question in the project, and a raw mean over 6 rollouts cannot answer
it: with n=6 one episode that clears a level moves the mean by 0.17.

Two ideas, borrowed from a benchmark review on a sibling branch (Pokemon TCG
`benchmark_v2.4`, the "seat swap + control run + n>=600" fixes):

1. **Common random numbers.** Seat swap cancels first-player advantage in a
   two-player game. Here the analogous trick is to run both variants on the
   *same seeds*, so the only difference between the two runs is the change under
   test. This is stronger than seat swap: with a deterministic engine it removes
   seed noise entirely, leaving a paired difference.
2. **A measured noise floor.** Before trusting any delta, measure how much the
   *same* agent varies across two disjoint seed sets. Any A/B delta inside that
   band is not evidence.

Usage
-----
    # 1) how noisy is the harness at this sample size?
    python local/abtest.py noise --seeds 60 --workers 14

    # 2) does this parameter change help? (paired, same seeds)
    python local/abtest.py ab --seeds 120 --workers 14 \
        --params-a '{}' --params-b '{"epsilon": 0.4, "temp": 0.5}'

    # 3) how many seeds would I need to detect a delta of 0.10?
    python local/abtest.py power --delta 0.10
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

_W: dict = {}


def _init(games_dir: str) -> None:
    import engine

    _W["games"] = engine.discover_games(Path(games_dir))


def _one(task: dict) -> dict:
    import engine
    from policies import build_policy

    info = _W["games"].get(task["game"])
    if info is None:
        return {"game": task["game"], "seed": task["seed"], "variant": task["variant"],
                "levels": 0, "steps": 0, "error": "unknown game"}
    params = dict(task["params"] or {})
    if task["policy"] == "solution":
        params["paths"] = task.get("paths") or []
    policy = build_policy(task["policy"], params)
    res = engine.run_episode(info, task["game"], policy, seed=task["seed"],
                             max_steps=task["max_steps"])
    return {"game": task["game"], "seed": task["seed"], "variant": task["variant"],
            "levels": res.levels, "steps": res.steps,
            "solved": res.solved, "error": res.error}


def _run_tasks(tasks: list[dict], workers: int, games_dir=None) -> list[dict]:
    import engine

    out = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(str(games_dir or engine.GAMES_DIR),)) as ex:
        for r in ex.map(_one, tasks, chunksize=2):
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def bootstrap_ci(diffs: list[float], n_boot: int = 2000, alpha: float = 0.05,
                 seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of paired differences."""
    if not diffs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


def sign_test(diffs: list[float]) -> dict:
    """How often B beat A, tied, or lost — the paired analogue of a win rate."""
    wins = sum(1 for d in diffs if d > 0)
    losses = sum(1 for d in diffs if d < 0)
    ties = sum(1 for d in diffs if d == 0)
    n = wins + losses
    # two-sided binomial p-value under H0: p=0.5 (normal approximation, n large)
    if n == 0:
        p = 1.0
    else:
        z = abs(wins - n / 2) / math.sqrt(n / 4)
        p = math.erfc(z / math.sqrt(2))
    return {"b_better": wins, "b_worse": losses, "tied": ties, "p_value": round(p, 4)}


def required_n(effect: float, sd: float, power: float = 0.8,
               alpha: float = 0.05) -> int:
    """Rough paired-sample size for a two-sided test at `alpha` with `power`.

    Uses n = ((z_{1-alpha/2} + z_power) * sd / effect)^2.
    """
    if effect <= 0:
        return -1
    z_alpha = 1.959963985 if abs(alpha - 0.05) < 1e-9 else 2.575829303
    z_power = {0.8: 0.841621234, 0.9: 1.281551566, 0.95: 1.644853627}.get(power, 0.841621234)
    return int(math.ceil(((z_alpha + z_power) * sd / effect) ** 2))


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
def mode_noise(args, games: list[str]) -> dict:
    """Same agent, two disjoint seed sets: the noise floor of the harness."""
    pol = "heuristic" if args.policy in ("heuristic", "solution") else args.policy
    params = json.loads(args.params_a) if args.params_a else {}
    seeds_a = list(range(0, args.seeds))
    seeds_b = list(range(args.seeds, 2 * args.seeds))

    tasks = []
    for g in games:
        for s in seeds_a:
            tasks.append({"game": g, "seed": s, "policy": pol, "params": params,
                          "variant": "A", "max_steps": args.max_steps})
        for s in seeds_b:
            tasks.append({"game": g, "seed": s, "policy": pol, "params": params,
                          "variant": "B", "max_steps": args.max_steps})
    res = _run_tasks(tasks, args.workers)

    agg: dict[tuple[str, str], list[float]] = {}
    for r in res:
        agg.setdefault((r["game"], r["variant"]), []).append(r["levels"])

    per_game = {}
    tot_a = tot_b = 0.0
    for g in games:
        a = agg.get((g, "A"), [0.0])
        b = agg.get((g, "B"), [0.0])
        ma, mb = statistics.mean(a), statistics.mean(b)
        tot_a += ma
        tot_b += mb
        per_game[g] = {"A": round(ma, 4), "B": round(mb, 4),
                       "abs_delta": round(abs(mb - ma), 4),
                       "n": len(a)}
    deltas = [per_game[g]["abs_delta"] for g in per_game]
    return {
        "mode": "noise",
        "policy": pol,
        "seeds_per_side": args.seeds,
        "total_levels_A": round(tot_a, 3),
        "total_levels_B": round(tot_b, 3),
        "noise_total_levels": round(abs(tot_b - tot_a), 3),
        "mean_abs_delta_per_game": round(statistics.mean(deltas), 4) if deltas else 0.0,
        "max_delta_per_game": round(max(deltas), 4) if deltas else 0.0,
        "games_that_differed": sum(1 for d in deltas if d > 0),
        "games": len(per_game),
        "per_game": per_game,
        "interpretation": (
            "Two runs of the SAME policy differ by this much on total levels. "
            "Any A/B result smaller than this is not evidence."),
    }


def mode_ab(args, games: list[str]) -> dict:
    """Paired A/B on identical seeds (common random numbers)."""
    seeds = list(range(0, args.seeds))
    params_a = json.loads(args.params_a) if args.params_a else {}
    params_b = json.loads(args.params_b) if args.params_b else {}

    tasks = []
    for g in games:
        for s in seeds:
            tasks.append({"game": g, "seed": s, "policy": args.policy,
                          "params": params_a, "variant": "A",
                          "max_steps": args.max_steps})
            tasks.append({"game": g, "seed": s, "policy": args.policy_b or args.policy,
                          "params": params_b, "variant": "B",
                          "max_steps": args.max_steps})
    res = _run_tasks(tasks, args.workers)

    key = {(r["game"], r["variant"], r["seed"]): r["levels"] for r in res}
    diffs: list[float] = []
    per_game: dict[str, dict] = {}
    for g in games:
        gd = []
        for s in seeds:
            a = key.get((g, "A", s), 0.0)
            b = key.get((g, "B", s), 0.0)
            gd.append(b - a)
        diffs.extend(gd)
        per_game[g] = {
            "delta_mean": round(statistics.mean(gd), 4),
            "A_mean": round(statistics.mean(key.get((g, "A", s), 0.0) for s in seeds), 4),
            "B_mean": round(statistics.mean(key.get((g, "B", s), 0.0) for s in seeds), 4),
            "B_better": sum(1 for d in gd if d > 0),
            "B_worse": sum(1 for d in gd if d < 0),
        }

    mean_d = statistics.mean(diffs) if diffs else 0.0
    sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    lo, hi = bootstrap_ci(diffs)
    st = sign_test(diffs)
    # total levels scale: sum of per-game means, comparable to a leaderboard delta
    total_a = sum(per_game[g]["A_mean"] for g in per_game)
    total_b = sum(per_game[g]["B_mean"] for g in per_game)
    return {
        "mode": "ab",
        "policy_a": args.policy, "params_a": params_a,
        "policy_b": args.policy_b or args.policy, "params_b": params_b,
        "seeds": len(seeds),
        "episodes": len(diffs),
        "total_levels_A": round(total_a, 3),
        "total_levels_B": round(total_b, 3),
        "total_delta": round(total_b - total_a, 3),
        "per_episode_delta_mean": round(mean_d, 5),
        "per_episode_delta_sd": round(sd, 5),
        "ci95_per_episode": [round(lo, 5), round(hi, 5)],
        "significant": bool(lo > 0 or hi < 0),
        "sign_test": st,
        "n_for_0.10_total": required_n(0.10 / max(1, len(games)), sd) if sd else None,
        "per_game": per_game,
        "interpretation": (
            "Paired on identical seeds, so the engine's determinism cancels seed "
            "noise. 'significant' means the 95% bootstrap CI of the paired "
            "difference excludes zero."),
    }


def mode_power(args) -> dict:
    """Sample size needed for a target delta, given a measured sd."""
    sd = args.sd
    n = required_n(args.delta, sd, power=args.power)
    return {
        "mode": "power",
        "target_delta_per_episode": args.delta,
        "assumed_sd": sd,
        "power": args.power,
        "required_episodes": n,
        "note": ("Pass --sd from a real `ab` run (per_episode_delta_sd). With a "
                 "deterministic engine and paired seeds the sd is usually small, "
                 "which is why pairing matters more than raw sample size."),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Paired A/B + noise floor for ARC-AGI-3")
    sub = ap.add_subparsers(dest="mode", required=True)

    for name in ("noise", "ab"):
        p = sub.add_parser(name)
        p.add_argument("--games", default="all")
        p.add_argument("--seeds", type=int, default=60,
                       help="seeds per side (noise) or shared seeds (ab)")
        p.add_argument("--workers", type=int, default=os.cpu_count() or 4)
        p.add_argument("--max-steps", type=int, default=400)
        p.add_argument("--policy", default="heuristic")
        p.add_argument("--policy-b", default=None)
        p.add_argument("--params-a", default=None, help="JSON dict")
        p.add_argument("--params-b", default=None, help="JSON dict")
        p.add_argument("--out", default=None)

    pw = sub.add_parser("power")
    pw.add_argument("--delta", type=float, default=0.10)
    pw.add_argument("--sd", type=float, default=0.5)
    pw.add_argument("--power", type=float, default=0.8)

    args = ap.parse_args()

    if args.mode == "power":
        result = mode_power(args)
    else:
        import engine

        games = (sorted(engine.discover_games().keys())
                 if args.games == "all" else [g.strip() for g in args.games.split(",")])
        result = (mode_noise(args, games) if args.mode == "noise"
                  else mode_ab(args, games))

    print(json.dumps({k: v for k, v in result.items() if k != "per_game"}, indent=2))
    if "per_game" in result:
        print("\nper game (sorted by |effect|):")
        items = sorted(result["per_game"].items(),
                       key=lambda kv: -abs(kv[1].get("abs_delta", kv[1].get("delta_mean", 0))))
        for g, v in items:
            if result["mode"] == "noise":
                print(f"  {g:6} A={v['A']:.3f} B={v['B']:.3f} |d|={v['abs_delta']:.3f}")
            else:
                print(f"  {g:6} A={v['A_mean']:.3f} B={v['B_mean']:.3f} "
                      f"d={v['delta_mean']:+.3f}  B better/worse={v['B_better']}/{v['B_worse']}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
