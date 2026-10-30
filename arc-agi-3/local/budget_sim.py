"""A faithful re-implementation of the level-budget policy in rev2
(`Smak-Domu-Konkurs@arena/5ed750ef`, `duck-v13-7-final`, patch 0010).

Why re-implement instead of quoting
-----------------------------------
rev2 changes one number (`ARC3_LEVEL_TOKEN_CAP` 60000 -> 20000) and calls it a
correction. Whether that is a correction or a regression is a question about
coverage, and coverage can be computed from the three recorded runs — but only
if the decision ladder is reproduced exactly, including the free reset and its
x1.5 ladder, because those two together decide the real per-level budget.

The ladder, read off `arc3_level_budget_v13_2.py`:

    cap(r)   = clamp(base, CAP_MIN, CAP_MAX) * LADDER**r,  r = resets used
    base     = static_cap                       if fewer than two costs recorded
    base     = max(static_cap, 4 * median)      otherwise
    spent >= cap(r) and r < RESETS_MAX  ->  RESET   (spent resets to 0, r += 1)
    spent >= cap(r) * ABANDON_MULT      ->  ABANDON (the game ends, `gave_up`)

With the shipped defaults (RESETS_MAX=1, LADDER=1.5, ABANDON_MULT=1.5) a level
in a game with fewer than two completed levels therefore gets

    static_cap  +  1.5 * static_cap * 1.5  =  3.25 * static_cap

tokens before the game is abandoned — 65 000 at rev2's arming of 20 000, and
195 000 at the 60 000 rev2 replaced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

CAP_MIN = 45_000
CAP_MAX = 150_000
RESETS_MAX = 1
LADDER = 1.5
ABANDON_MULT = 1.5


@dataclass
class LevelBudget:
    """rev2's policy, reduced to the parts that decide a level's fate."""

    static_cap: int
    # rev2: `cap_min = max(1, env("ARC3_DYN_CAP_MIN", static_cap or 45000))`
    # — i.e. the floor IS the arming value unless overridden. Leaving it at
    # 45000 regardless would silently clamp a 20000 arming back up to 45000 and
    # make the policy look harmless, which is the opposite of what it does.
    cap_min: int | None = None
    cap_max: int = CAP_MAX
    resets_max: int = RESETS_MAX
    ladder: float = LADDER
    abandon_mult: float = ABANDON_MULT
    costs: list[float] = field(default_factory=list)

    def cap(self, resets_used: int = 0) -> float:
        base = float(self.static_cap)
        if len(self.costs) >= 2:
            base = max(base, median(self.costs) * 4.0)
        floor = self.static_cap if self.cap_min is None else self.cap_min
        base = min(max(base, floor), self.cap_max)
        return base * (self.ladder ** resets_used)

    def budget_for_level(self) -> float:
        """Tokens a level may consume before ABANDON, with the one free reset."""
        return self.cap(0) + self.cap(1) * self.abandon_mult

    def run_level(self, cost: float) -> bool:
        """Spend ``cost`` on one level; return True if it completes.

        On completion the cost joins the history, which is what lets later
        levels use the 4x-median rule.
        """
        if cost <= self.budget_for_level():
            self.costs.append(cost)
            return True
        return False


def simulate(costs: list[float], static_cap: int, protect_level_one: bool = False) -> tuple[int, float]:
    """Simulate a whole game. Returns (levels completed, tokens spent).

    ``protect_level_one`` models ``ARC3_LEVEL_MIN_DONE=1``: while nothing has
    been completed, ABANDON is suppressed, so the first level gets the ladder
    ceiling instead of the ladder budget.
    """
    b = LevelBudget(static_cap=static_cap)
    spent = 0.0
    for i, cost in enumerate(costs):
        if protect_level_one and not b.costs:
            limit = float("inf")
        else:
            limit = b.budget_for_level()
        if cost <= limit:
            b.costs.append(cost)
            spent += cost
        else:
            spent += limit if limit != float("inf") else cost
            break
        if i + 1 == len(costs):
            break
    return len(b.costs), spent


def waste_tokens(costs: list[float], last_level_tokens: float, static_cap: int) -> float:
    """Tokens rev2 would refuse to spend on the unfinished last level."""
    b = LevelBudget(static_cap=static_cap, costs=list(costs))
    budget = b.budget_for_level()
    return max(0.0, last_level_tokens - budget)
