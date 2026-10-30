"""The authoritative ARC-AGI-3 score, verified against 30 recorded runs.

Rule (source: `taaf/game.py::_compute_final_score`, which mirrors
`arc_agi.scorecard.EnvironmentScoreCalculator v0.9.8`; extracted by the
Gemma-konkurs branch `arena/c4eeb067`, file `ARC3/local-lab/PLAN-50.md` §1):

    for each level k = 1..n:
        w_k = k
        if k <= levels_completed and actions_k > 0:
            s_k = min(115, (baseline_k / actions_k)^2 * 100)
        else:
            s_k = 0
    raw   = sum(s_k * w_k) / sum(w_k)
    cap   = 100 * sum(w_k for k where s_k > 0) / sum(w_k)
    score = min(raw, cap)

Two things here that our own implementation got wrong for three days:

  * the per-level ceiling is **115**, not 100 and not 1.0 — the ratio cap is
    sqrt(1.15) ~ 1.072, so beating the human pays a little, but only a little;
  * there is a **completion cap**: `min(raw, cap)` — you cannot score above the
    fraction of the game you actually finished. This one is the reason depth
    dominates, and it was missing entirely from our model.

Verification: `local/test_metric.py` reproduces all 30 stored `final_score`
values from `local/benchmarks/*.json` to within 0.02.
"""
from __future__ import annotations

PER_LEVEL_CEILING = 115.0


def level_points(baseline: int, actions: int) -> float:
    """Points for one completed level, 0..115. Unfinished or free levels score 0."""
    if actions <= 0 or baseline <= 0:
        return 0.0
    return min(PER_LEVEL_CEILING, (baseline / actions) ** 2 * 100.0)


def game_score(baselines: list[int], actions: list[int], completed: int) -> float:
    """Score of one game, 0..100."""
    levels = len(baselines)
    if levels == 0:
        return 0.0
    denom = sum(range(1, levels + 1))
    weighted = 0.0
    done_weight = 0
    for i in range(levels):
        weight = i + 1
        if i >= completed:
            continue
        acts = actions[i] if i < len(actions) else 0
        if acts <= 0:
            continue
        weighted += level_points(baselines[i], acts) * weight
        done_weight += weight
    if denom == 0:
        return 0.0
    raw = weighted / denom
    completion_cap = 100.0 * done_weight / denom
    return min(raw, completion_cap)


def mean_score(games) -> float:
    """Total score: plain mean over games. `games` yields (baselines, actions, completed)."""
    games = list(games)
    if not games:
        return 0.0
    return sum(game_score(b, a, k) for b, a, k in games) / len(games)


def actions_needed_for(level_points_target: float, baseline: int) -> float:
    """Actions allowed on a level while still scoring `level_points_target`."""
    if level_points_target <= 0:
        return float("inf")
    return baseline / (level_points_target / 100.0) ** 0.5
