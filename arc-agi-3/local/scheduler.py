"""Value-greedy action allocator for ARC-AGI-3 (krok 2 planu MEGA).

Why this exists
---------------
The competition score is the *mean over games* of a per-game score whose level
weights grow with the level index (1, 2, 3, ... L).  So completing level 1 of a
4-level game is worth 2/10 = 20% of that game, while completing level 1 of a
9-level game is worth 2/45 = 4.4%.  A 4.5x difference for the same work.

Our runs spread the wall-clock budget *equally* over games (all 30 games ended at
exactly 2880 s).  That is the opposite of optimal.  Measured on r018, reallocating
the same total action budget by marginal value is worth +7.4 points at 275
actions/game and +11.7 at 400 (see MEGA-DIAGNOSIS.md section 5).

What the scheduler can and cannot see
-------------------------------------
At evaluation time we know, from the first frame onward:

  * ``win_levels`` — the total number of levels L in the game. Always available.
  * how many levels we have already completed (k).
  * how many actions we have already spent on this game.

We do **not** know the human baseline ``h_l`` per level — that is only present in
our local benchmark artifacts.  So the cost estimate below is deliberately built
from observation only: a prior for the first level, then the observed mean cost
of the levels we did complete.  ``tests`` in ``local/test_scheduler.py`` pin this
behaviour.

API
---
    sched = ValueScheduler(games=[("tn36", 7), ("cn10", 4), ...], total_budget=2200)
    i = sched.next_game()          # -> index of the game to spend the next quantum on
    sched.record(i, actions=35, level_completed=True)

``next_game`` never returns a game that has no levels left.  Once the budget is
exhausted it returns ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_PRIOR_COST = 45.0
"""Prior on the action cost of a game's first level.

Observed median human cost per level across the 25 public games is ~40-60.  The
scheduler is insensitive to this choice over 20..45 (all give the same result on
r018, MEGA-DIAGNOSIS.md section 5); it only degrades when the prior is far too
large (>=90), because then every game looks equally expensive.
"""


def level_weight(level_index: int) -> int:
    """Weight of a 0-based level index: the formula uses 1-based indices."""
    return level_index + 1


def total_weight(levels: int) -> int:
    """Sum of level weights for a game with ``levels`` levels: 1+2+...+L."""
    return levels * (levels + 1) // 2


def marginal_value(completed: int, levels: int) -> float:
    """Score value of completing the *next* level, as a fraction of the whole game.

    ``completed`` is the number of levels already done, so the next level is the
    1-based index ``completed + 1`` and carries weight ``completed + 1``.
    """
    if levels <= 0 or completed >= levels:
        return 0.0
    return level_weight(completed) / total_weight(levels)


@dataclass
class GameState:
    name: str
    levels: int
    completed: int = 0
    spent: int = 0
    closed: bool = False

    @property
    def done(self) -> bool:
        return self.closed or self.completed >= self.levels

    @property
    def expected_cost(self) -> float:
        """Estimated actions needed for the next level, from observation only."""
        if self.completed <= 0:
            return DEFAULT_PRIOR_COST
        return max(self.spent / self.completed, 1.0)

    @property
    def priority(self) -> float:
        """Value per action. The scheduler always feeds the highest value."""
        if self.done:
            return 0.0
        return marginal_value(self.completed, self.levels) / self.expected_cost

    def coverage(self) -> float:
        """Achieved fraction of this game's maximum score, ignoring efficiency."""
        return sum(range(1, self.completed + 1)) / total_weight(self.levels)


@dataclass
class ValueScheduler:
    games: list[tuple[str, int]]
    total_budget: int | None = None
    _state: list[GameState] = field(default_factory=list, repr=False)
    _allocated: int = 0

    def __post_init__(self) -> None:
        self._state = [GameState(name=n, levels=L) for n, L in self.games]

    # -- introspection ---------------------------------------------------
    @property
    def states(self) -> list[GameState]:
        return self._state

    @property
    def remaining(self) -> float:
        if self.total_budget is None:
            return float("inf")
        return self.total_budget - self._allocated

    def exhausted(self) -> bool:
        return self.total_budget is not None and self._allocated >= self.total_budget

    # -- decisions -------------------------------------------------------
    def next_game(self) -> int | None:
        """Index of the game that should receive the next quantum of actions."""
        if self.exhausted():
            return None
        best_idx, best_pri = None, 0.0
        for i, g in enumerate(self._state):
            if g.done:
                continue
            p = g.priority
            # Strict > with a tiny epsilon keeps ties stable at the lowest index.
            if p > best_pri + 1e-12:
                best_idx, best_pri = i, p
        return best_idx

    def record(self, index: int, actions: int, level_completed: bool = False) -> None:
        """Account for ``actions`` spent on game ``index``.

        Call this once per batch of real game actions.  ``level_completed`` says
        whether that batch finished the level.
        """
        g = self._state[index]
        g.spent += actions
        self._allocated += actions
        if level_completed:
            g.completed += 1

    def close(self, index: int) -> None:
        """Give up on a game (e.g. the harness reported GAME_OVER for good)."""
        self._state[index].closed = True

    # -- reporting -------------------------------------------------------
    def projected_score(self, efficiency: float = 0.9) -> float:
        """Expected score (0-100) if every game finishes at its current coverage.

        ``efficiency`` is the squared-RHAE factor on completed levels; 0.9 matches
        what our runs actually achieve on levels they finish.
        """
        if not self._state:
            return 0.0
        return 100.0 * sum(g.coverage() for g in self._state) / len(self._state) * efficiency


def plan(games: list[tuple[str, int]], budget_per_game: float,
         costs: dict[str, list[int]] | None = None, efficiency: float = 0.9,
         prior_cost: float = 30.0, quantum: int = 10) -> float:
    """Offline replay of the value-greedy policy against known level costs.

    Mirrors the reference simulator used for the tables in MEGA-DIAGNOSIS.md
    section 5; ``local/test_scheduler.py`` pins the reproduced numbers.

    ``prior_cost`` is the guess for a game's first level. The observed median
    first-level human cost in r018 is 30, which is the default. The result is
    genuinely sensitive to this value (30 -> 40.3, 45 -> 36.3, 90 -> 24.8 at a
    275 action/game budget), so it is a parameter rather than a constant.
    """
    table = _R018_COSTS if costs is None else costs
    n = len(games)
    if n == 0:
        return 0.0
    spent = {name: 0.0 for name, _ in games}
    done = {name: 0 for name, _ in games}
    left = float(budget_per_game * n)

    while left > 1e-9:
        best: tuple[float, str] | None = None
        for name, levels in games:
            if done[name] >= levels:
                continue
            value = marginal_value(done[name], levels)
            cost = prior_cost if done[name] == 0 else max(spent[name] / done[name], 1.0)
            priority = value / cost
            if best is None or priority > best[0]:
                best = (priority, name)
        if best is None:
            break
        name = best[1]
        level = done[name]
        need = table[name][level] / efficiency
        paid = sum(table[name][:level]) / efficiency
        on_level = spent[name] - paid
        step = min(quantum, need - on_level, left)
        step = max(1.0, float(round(step)))
        step = min(step, left)
        spent[name] += step
        left -= step
        if spent[name] >= sum(table[name][:level + 1]) / efficiency - 1e-9:
            done[name] += 1

    total = 0.0
    for name, levels in games:
        used = 0.0
        k = 0
        for c in table[name]:
            c = c / efficiency
            if used + c <= spent[name] + 1e-9:
                used += c
                k += 1
            else:
                break
        total += sum(range(1, min(k, levels) + 1)) / total_weight(levels)
    return 100.0 * total / n


_R018_COSTS: dict[str, list[int]] = {
    # Human baselines verbatim from r018 `base_actions_per_level` (benchmark.json,
    # branch arena/98ddb59f-pokemon). Not estimates.
    "tn36": [32, 72, 26, 40, 30, 55, 62],
    "m0r0": [30, 111, 203, 26, 500, 237],
    "cn04": [29, 54, 85, 300, 208, 113],
    "dc22": [59, 102, 67, 98, 324, 578],
    "ka59": [28, 109, 51, 51, 33, 132, 326],
    "sc25": [36, 6, 32, 83, 143, 50],
    "s5i5": [20, 89, 106, 54, 162, 38, 86, 83],
    "ls20": [22, 123, 73, 84, 96, 192, 186],
    "su15": [22, 42, 26, 115, 36, 31, 8, 40, 41],
    "g50t": [78, 175, 179, 230, 96, 54, 67],
}

R018_GAMES: list[tuple[str, int]] = [(n, len(c)) for n, c in _R018_COSTS.items()]
