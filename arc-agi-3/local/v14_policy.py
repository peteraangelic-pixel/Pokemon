"""v14 policy: token budget, level abandonment, short-game priority.

Design thesis (see `V14-PLAN.md`):
    score = coverage x efficiency^2
    efficiency is already ~90%  -> the only lever left is COVERAGE
    coverage is limited by TOKENS, not time and not actions
    -> 853 tokens/action today; ~479 buys score 50

This module is the parts of that thesis that can be *measured offline*, today,
without a GPU or a submission slot:

  * `simulate()`  — replays the three recorded runs under different policies,
                    using only the actions the agent actually spent.
  * `LevelGovernor` — the runtime policy: cap a level, abandon a game, ask for
                    a plan instead of a single action.

Honesty rules baked in
----------------------
A level the agent never completed has an UNKNOWN cost. The simulator therefore
runs two bounds and never reports a single number:

  pessimistic  — a stalled level can never be finished, whatever we spend
  optimistic   — it finishes at OPTIMISM_FACTOR x what we already spent

The truth for any given game sits inside that bracket. Reporting only the
optimistic number is how the "+22 points" error happened in the first scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Measured in local/token_budget.py from the three recorded runs.
MS_PER_TOKEN = 15.8
TOKENS_PER_ACTION = 853.0
SECONDS_PER_GAME = 2945.0          # EVAL-BUDGET-MODEL.md section 2

# A stalled level is assumed to need this multiple of what we already spent on it,
# under the optimistic bound. 2.0 means "it was nearly done"; 1.0 would mean
# "one more action and it falls", which is too generous to be useful.
OPTIMISM_FACTOR = 2.0


def actions_per_game() -> float:
    """How many actions one game's slot buys at today's token rate."""
    return SECONDS_PER_GAME / (MS_PER_TOKEN * TOKENS_PER_ACTION / 1000.0)


def level_value(level_index: int) -> int:
    """Weight of a 0-based level index; the metric uses 1-based indices."""
    return level_index + 1


def total_weight(levels: int) -> int:
    return levels * (levels + 1) // 2


def marginal_value(completed: int, levels: int) -> float:
    """Score value of finishing the next level, as a fraction of that game."""
    if levels <= 0 or completed >= levels:
        return 0.0
    return level_value(completed) / total_weight(levels)


@dataclass
class LevelCost:
    """What one level actually cost in a recorded run."""
    actions: int
    completed: bool


@dataclass
class GameRun:
    """One game from benchmark.json, reduced to what the policy needs."""
    game_id: str
    levels: int
    per_level: list[LevelCost]

    @property
    def completed(self) -> int:
        return sum(1 for c in self.per_level if c.completed)


def load_run(benchmark: dict) -> list[GameRun]:
    out = []
    for g in benchmark["game_runs"]:
        k = int(g["levels_completed"])
        per = []
        for i, a in enumerate(g["actions_per_level"]):
            if not a:
                continue
            per.append(LevelCost(actions=int(a), completed=i < k))
        out.append(GameRun(g["game_id"][:4], int(g["number_of_levels"]), per))
    return out


def _cost_of(run: GameRun, level: int, generous: bool) -> float:
    """Actions needed to finish `level`, or inf if the bound forbids it."""
    if level < len(run.per_level):
        lc = run.per_level[level]
        if lc.completed:
            return float(lc.actions)
    # Stalled level: unknown. Only the optimistic bound allows finishing it.
    if not generous or level >= len(run.per_level):
        return float("inf")
    return run.per_level[level].actions * OPTIMISM_FACTOR


def _coverage(run: GameRun, spent_by_level: dict[int, float], generous: bool) -> float:
    """Fraction of the game's maximum score banked, given what we PAID for.

    Note: this asks "did our budget cover this level?", not "did the original run
    finish it?". The distinction matters — under the optimistic bound a counter-
    factual policy can finish levels the recorded run never reached, and the
    first version of this function silently reported the original outcome for
    every policy, making the whole simulation a no-op.
    """
    banked = 0
    for i in range(len(run.per_level)):
        cost = _cost_of(run, i, generous)
        if cost == float("inf"):
            break
        if spent_by_level.get(i, 0.0) >= cost - 1e-9:
            banked += level_value(i)
        else:
            break
    return banked / total_weight(run.levels) if run.levels else 0.0


def simulate(runs: list[GameRun], policy: str, generous: bool,
             cap: float | None = None, redistributable: float = 0.0) -> float:
    """Score (0-100) under a policy, on a fixed total action budget.

    policy="equal"  every game gets the same slice (what we do today)
    policy="cap"    a level is abandoned after `cap` actions without finishing;
                    the freed actions are handed to the games with the best
                    marginal value per action
    """
    n = len(runs)
    if n == 0:
        return 0.0
    budget = actions_per_game() * n
    per_game = budget / n

    spent = [dict() for _ in range(n)]
    left = [per_game] * n

    if policy == "equal":
        for i, run in enumerate(runs):
            for lvl in range(len(run.per_level)):
                cost = _cost_of(run, lvl, generous)
                if cost <= left[i]:
                    spent[i][lvl] = cost
                    left[i] -= cost
                else:
                    spent[i][lvl] = left[i]
                    left[i] = 0.0
                    break
        return 100.0 * sum(_coverage(r, s, generous) for r, s in zip(runs, spent)) / n

    if policy != "cap" or cap is None:
        raise ValueError(f"nieznana polityka: {policy}")

    # Phase 1: every game plays until a level exceeds the cap or it runs out.
    # The overspend above `cap` is what gets reclaimed for redistribution.
    reclaimed = 0.0
    for i, run in enumerate(runs):
        for lvl in range(len(run.per_level)):
            cost = _cost_of(run, lvl, generous)
            allowance = float(cap)
            if cost <= allowance and cost <= left[i]:
                spent[i][lvl] = cost
                left[i] -= cost
                continue
            # Level resists: burn at most `cap`, then walk away from the game.
            burn = min(allowance, left[i])
            spent[i][lvl] = burn
            left[i] -= burn
            reclaimed += left[i]
            left[i] = 0.0
            break

    # Phase 2: hand the reclaimed actions to the most valuable unfinished levels.
    pool = reclaimed + redistributable
    while pool > 1e-9:
        best = None
        for i, run in enumerate(runs):
            k = _coverage_levels(run, spent[i])
            if k >= len(run.per_level):
                continue
            cost = _cost_of(run, k, generous)
            if cost == float("inf"):
                continue
            value = marginal_value(k, run.levels)
            per_action = value / max(cost, 1.0)
            if best is None or per_action > best[0]:
                best = (per_action, i, k, cost, value)
        if best is None:
            break
        _, i, k, cost, value = best
        if cost <= pool:
            spent[i][k] = cost
            pool -= cost
        else:
            # Partial funding buys nothing: the level only scores when finished.
            break
    return 100.0 * sum(_coverage(r, s, generous) for r, s in zip(runs, spent)) / n


def _coverage_levels(run: GameRun, spent_by_level: dict[int, float]) -> int:
    k = 0
    for i, lc in enumerate(run.per_level):
        if lc.completed and spent_by_level.get(i, 0.0) >= lc.actions:
            k += 1
        else:
            break
    return k


@dataclass
class LevelGovernor:
    """Runtime policy: when to give up on a level, a game, or a turn.

    Everything here is derived from what the harness can see at eval time:
    `win_levels`, `levels_completed`, and the actions spent on this level.
    It never uses the human baseline, which is not available in the rerun.
    """

    level_cap: int = 120
    """Actions on one level before we stop funding it.

    Measured: in r018 the levels we *did* finish cost a median of 26 actions,
    while the one we stalled on ate 227 (ls20) and 124 (tn36). A cap near the
    95th percentile of completed levels sits between those populations.
    """

    min_plan_steps: int = 5
    """Below this many steps in one `commit()`, we ask for a longer plan.

    Rationale in V14-PLAN.md section 2: tokens per action is the binding
    constraint, and a 1-step commit pays a full generation for one action.
    """

    actions_on_level: int = 0
    plans_seen: int = 0
    short_plans: int = 0

    def on_action(self) -> None:
        self.actions_on_level += 1

    def on_level_change(self) -> None:
        self.actions_on_level = 0

    def on_plan(self, steps: int) -> None:
        self.plans_seen += 1
        if steps < self.min_plan_steps:
            self.short_plans += 1

    def should_abandon_level(self) -> bool:
        """True once this level has consumed its budget without progress."""
        return self.actions_on_level >= self.level_cap

    def should_nudge_for_plan(self) -> bool:
        """True when recent plans have been too short to pay for themselves."""
        if self.plans_seen < 3:
            return False
        return self.short_plans / self.plans_seen > 0.5

    def tokens_per_action(self, tokens: float, actions: int) -> float:
        """The one number that decides the score. Log it every game."""
        return tokens / actions if actions else float("inf")


def short_game_priority(runs: list[GameRun]) -> list[tuple[str, float]]:
    """Games ranked by how much score one finished level is worth.

    Level l of an L-level game is worth l / (1+..+L). Finishing level 1 of a
    4-level game is 20% of that game; of a 9-level game it is 4.4%. At equal
    risk, a short game is the better place to spend time.
    """
    ranked = [(r.game_id, marginal_value(r.completed, r.levels)) for r in runs]
    return sorted(ranked, key=lambda x: -x[1])
