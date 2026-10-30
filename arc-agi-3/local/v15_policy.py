"""v15: baseline-aware governor — turn "abandon" from a bet into arithmetic.

Why this exists
---------------
The authoritative score (see `local/metric.py`, verified 30/30 against recorded
runs) is:

    s_k  = min(115, (baseline_k / actions_k)^2 * 100)   for a completed level
    raw  = sum(s_k * w_k) / sum(w_k)          with w_k = k
    cap  = 100 * (finished weight) / (total weight)
    score = min(raw, cap)                     => score <= 100 * coverage

So *every* decision reduces to one question: **does the next level finish within
the actions it costs?** If we know `baseline_k`, we know exactly how many actions
buy 100 points on that level (`baseline_k`) and how many buy the 115 ceiling
(`baseline_k / 1.0724`). That turns abandonment from a guess into arithmetic:

    keep going  iff  expected points gained  >  points lost by spending
                     those actions on the best alternative level

Our previous simulator could only bracket this between
"never completes" (-19.5) and "completes at 2x cost" (+2.9). That bracket exists
**because we did not use the baseline**, which we do have in every recorded
`game_run`. Gemma-konkurs asked the open question: "nie wiem, jak ToolAgent się do
baseline'u dostaje". Answer: `self.game_run.base_actions_per_level` — present on
all 30 recorded game_runs. Whether it is *populated* in the scoring rerun is a
probe, not a guess: `baseline_available()` below, and `PROBE` output in v15.

Design rule
-----------
Everything degrades safely. With no baseline this module reproduces the v13.2
behaviour plus a fixed cap; with a baseline it makes exact decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from metric import PER_LEVEL_CEILING, actions_needed_for, game_score, level_points

# sqrt(1.15): the ratio at which a level stops paying more.
RATIO_AT_CEILING = (PER_LEVEL_CEILING / 100.0) ** 0.5

# Points a level must still be worth for us to keep funding it. Below this the
# action is worth more elsewhere.
DEFAULT_MIN_MARGINAL = 5.0


def baseline_available(base_actions_per_level) -> bool:
    """True when the harness actually populated the human baseline.

    This is the single fact that decides whether v15 can be exact. It is
    unknown for the 110 private games, so it is measured, not assumed.
    """
    if not base_actions_per_level:
        return False
    try:
        return any(int(b) > 0 for b in base_actions_per_level)
    except (TypeError, ValueError):
        return False


def escalate_at(base_actions: list[int] | None, level_index: int,
                floor: int = 20, rate: float = 1.2) -> int:
    """Actions on a level before the escalation directive fires.

    With a baseline: `max(floor, rate * baseline)` — so the nudge only lands when
    we are genuinely behind the human on THIS level, not on every level.

    Gemma-konkurs measured the absolute threshold on 32 completed levels of r085:
    at 10 the directive fired 154 times (15.3% of the game's token pool) and on
    **31/32** levels told the model to stop trying while it was at or better than
    human pace. At 20: 60 times (6.0%). Relative: 8 times, 0/32 premature.
    """
    if not base_actions or level_index >= len(base_actions):
        return floor
    b = int(base_actions[level_index])
    if b <= 0:
        return floor
    return max(floor, int(round(rate * b)))


@dataclass
class LevelState:
    index: int
    actions_spent: int = 0
    completed: bool = False


@dataclass
class GameGovernor:
    """Per-game decisions. Feed it the real observed numbers; it makes calls."""

    level_count: int
    baselines: list[int] | None = None
    level_cap_floor: int = 120
    min_marginal: float = DEFAULT_MIN_MARGINAL
    levels: list[LevelState] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.levels:
            self.levels = [LevelState(i) for i in range(self.level_count)]

    # -- reporting -------------------------------------------------------
    @property
    def completed(self) -> int:
        n = 0
        for lv in self.levels:
            if lv.completed:
                n += 1
            else:
                break
        return n

    def current(self) -> LevelState | None:
        k = self.completed
        return self.levels[k] if k < len(self.levels) else None

    def coverage(self) -> float:
        """Fraction of the game's weighted levels finished — the hard score cap."""
        total = sum(range(1, self.level_count + 1))
        done = sum(range(1, self.completed + 1))
        return done / total if total else 0.0

    def current_score(self) -> float:
        """Score banked so far, using baselines when we have them."""
        if not self.baselines:
            return 0.0
        actions = [lv.actions_spent for lv in self.levels]
        return game_score(self.baselines, actions, self.completed)

    # -- observation -----------------------------------------------------
    def on_action(self) -> None:
        lv = self.current()
        if lv is not None:
            lv.actions_spent += 1

    def on_level_complete(self) -> None:
        lv = self.current()
        if lv is not None:
            lv.completed = True

    # -- decisions -------------------------------------------------------
    def level_budget(self) -> int:
        """Actions we are willing to spend on the current level.

        With a baseline, the honest answer is "as many as still pay": a level is
        worth funding up to the point where its points per action drop below what
        the next level would pay. That point depends on `min_marginal`.
        """
        lv = self.current()
        if lv is None:
            return 0
        if not self.baselines or lv.index >= len(self.baselines):
            return self.level_cap_floor
        base = self.baselines[lv.index]
        # Actions at which this level still scores `min_marginal` points.
        return max(self.level_cap_floor, int(actions_needed_for(self.min_marginal, base)))

    def should_abandon_level(self) -> bool:
        lv = self.current()
        if lv is None:
            return False
        return lv.actions_spent >= self.level_budget()

    def escalate_threshold(self) -> int:
        lv = self.current()
        if lv is None:
            return 20
        return escalate_at(self.baselines, lv.index, floor=20)

    def should_escalate(self) -> bool:
        lv = self.current()
        return lv is not None and lv.actions_spent >= self.escalate_threshold()

    # -- the number that decides the run ---------------------------------
    def tokens_per_action(self, tokens: int) -> float:
        spent = sum(lv.actions_spent for lv in self.levels)
        return tokens / spent if spent else float("inf")

    def probe_line(self, game_id: str) -> str:
        """One log line per game. This is the measurement v15 exists to produce."""
        return (
            f"v15 probe: game={game_id} levels={self.level_count} "
            f"completed={self.completed} coverage={self.coverage():.3f} "
            f"baseline={'yes' if self.baselines else 'no'} "
            f"budget={self.level_budget()} escalate_at={self.escalate_threshold()} "
            f"score={self.current_score():.2f}"
        )


def best_next_level(runs, budget_left: float):
    """Across games: which unfinished level gives the most points per action.

    `runs` is a list of GameGovernor. Returns (index, level, points_per_action)
    for the best candidate, or None when nothing can be finished.
    """
    best = None
    for i, gov in enumerate(runs):
        lv = gov.current()
        if lv is None or not gov.baselines or lv.index >= len(gov.baselines):
            continue
        base = gov.baselines[lv.index]
        weight = lv.index + 1
        total = sum(range(1, gov.level_count + 1))
        points = level_points(base, base) * weight / total   # best case: match human
        cost = float(base)
        score = points / max(cost, 1.0)
        if best is None or score > best[2]:
            best = (i, lv.index, score)
    return best


def required_coverage(target_score: float, efficiency: float = 0.9) -> float:
    """Coverage needed to reach `target_score`.

    Because `score <= 100 * coverage`, 50 points needs at least 50% coverage.
    With efficiency e < 1 the raw term scales by e^2, so we need
    coverage >= target / (100 * e^2) — unless the per-level 115 ceiling rescues
    us, which it only does on levels we beat the human on.
    """
    if efficiency <= 0:
        return 1.0
    return min(1.0, target_score / (100.0 * efficiency * efficiency))
