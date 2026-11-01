"""What 50 points actually costs, measured on real harness data.

The question this answers
------------------------
Every strategic argument in this campaign has been about *tokens*: cap, arming,
tok/action, budget. The real submission history says that is the wrong axis:

    v3      26.25   (oldest, simplest config)
    v11     23.89   (PLAN_COMMIT=0)
    v13.7   13.28   (9 patches: hint, escalation, cap 2, self-pace, winpath)

and the two smoke runs that bracket it, same harness, same 10 games, same 48 min,
measured from `generated_tokens` and `actions_per_level` in the benchmark logs:

    r085 (c45 config)  actions/level 66.4   levels/game 3.20   smoke 26.78
    r121 (v13.7)       actions/level 91.0   levels/game 2.50   smoke 22.59

Token cost per action barely moved (667 -> 733, +10%). What moved is **actions per
level, +37%**. The chain did not make the model slower. It made it waste moves.

Since actions per game is pinned by the wall clock (about 220 at 48 min/game),
levels per game = actions_per_game / actions_per_level. That single ratio is the
whole competition.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- measured constants -----------------------------------------------------
# Three runs, same 10 public games, same harness, same 48 min budget.
#
# CORRECTION (01.11): an earlier version of this module used "total actions /
# levels completed" for r085 (66.4) and "actions on COMPLETED levels / levels
# completed" for v3 (47.8). Those are different quantities and the difference
# looked like a 37% efficiency collapse. Done consistently, efficiency is flat
# and the variable that moves is the share of actions spent on levels that are
# never finished.
ACTIONS_PER_GAME = 220
ACTIONS_PER_LEVEL_C45 = 51.8     # r085: actions on completed levels / completions
ACTIONS_PER_LEVEL_V137 = 50.4    # r121
ACTIONS_PER_LEVEL_V3 = 47.8      # fresh v3 control, 01.11

WASTE_C45 = 0.22
WASTE_V137 = 0.45
WASTE_V3 = 0.16

ACTIONS_PER_CALL = {"v3": 4.48, "r085": 4.51, "r121": 5.01}
TOKENS_PER_CALL = {"v3": 4066, "r085": 3009, "r121": 3675}

# The symbolic controller of the Codex package: 3 levels in 25 actions on ft09.
ACTIONS_PER_LEVEL_SYMBOLIC = 25 / 3

# Real `number_of_levels` from r085's ten games.
LEVEL_COUNTS = (7, 6, 6, 6, 7, 6, 8, 7, 9, 7)

# Recorded score / exact coverage on the two smoke runs: 26.78/29.8 = 0.899 and
# 22.59/23.5 = 0.961. We do not beat the human by enough on every closed level to
# collect the full 115, so the score is coverage times roughly this factor.
EFFICIENCY = 0.93

# Recorded Kaggle results (own-submissions, r122).
SUBMISSIONS = {"v3": 26.25, "v11": 23.89, "v13.7": 13.28}


def weight(k: int) -> int:
    """Level k weighs k, so a game's total weight is the triangular number."""
    return k * (k + 1) // 2


def coverage_from_levels(completed, level_counts=LEVEL_COUNTS) -> float:
    """Exact mean coverage from a per-game list of completed levels, 0..1.

    This is the honest function: real runs are *uneven* — some games finish five
    levels, some finish none — and because the weight is triangular, unevenness
    raises coverage at the same mean. `coverage()` below assumes a uniform depth
    and therefore *under*-predicts any real run; the gap is the concentration
    uplift, and it is large (see `concentration_uplift`).
    """
    done = list(completed)
    total = 0.0
    for i, n in enumerate(level_counts):
        k = min(float(done[i]) if i < len(done) else 0.0, float(n))
        whole = int(k)
        frac = k - whole
        # a fractional level credits that fraction of the next level's weight;
        # without this, rounding makes every lever saturate at the same value
        w = weight(whole) + (frac * (whole + 1) if whole + 1 <= n else 0.0)
        total += w / weight(n)
    return total / len(level_counts)


def scaled_shape(target_levels: float, completed, level_counts=LEVEL_COUNTS) -> list[float]:
    """Scale a recorded per-game depth profile to a new mean, without rounding.

    Rounding to whole levels saturates: past about 4.6 levels/game every game is
    pinned at its maximum and further levers stop registering, which would hide
    the very differences we are trying to measure.
    """
    done = list(completed)
    mean = sum(done) / len(level_counts)
    if mean <= 0:
        return [0.0] * len(level_counts)
    a = target_levels / mean
    return [min(k * a, float(n)) for k, n in zip(done, level_counts)]


def concentration_uplift(completed, level_counts=LEVEL_COUNTS) -> float:
    """How much more coverage the real, uneven depth gives than a uniform depth.

    Returns 1.0 when the run is uniform. Measured: r085 = 1.15, r121 = 1.44.
    """
    done = list(completed)
    mean_levels = sum(done) / len(level_counts)
    return coverage_from_levels(done, level_counts) / coverage(mean_levels, level_counts)


def coverage(levels_per_game: float, level_counts=LEVEL_COUNTS) -> float:
    """Mean per-game coverage at a uniform depth, 0..1.

    `score = min(raw, 100 * coverage)` and we clear the per-level 115 ceiling on
    levels we do close, so coverage is the score, in percent.
    """
    total = 0.0
    for n in level_counts:
        k = min(levels_per_game, n)
        whole = int(k)
        frac = k - whole
        # fractional level: credit `frac` of the next level's weight
        w = weight(whole) + frac * (whole + 1 if whole + 1 <= n else 0)
        total += w / weight(n)
    return total / len(level_counts)


def score_from_levels(completed, level_counts=LEVEL_COUNTS) -> float:
    """Predicted score for a per-game list of completed levels."""
    return 100 * EFFICIENCY * coverage_from_levels(completed, level_counts)


def levels_for_score(target: float, level_counts=LEVEL_COUNTS) -> float:
    """Levels per game needed to reach `target` points (bisection, monotone)."""
    lo, hi = 0.0, float(max(level_counts))
    for _ in range(80):
        mid = (lo + hi) / 2
        if 100 * EFFICIENCY * coverage(mid, level_counts) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def levels_per_game(actions_per_game: float, actions_per_level: float,
                    waste_share: float) -> float:
    """Depth from budget, efficiency and waste — the three-constant model.

        completed_actions = actions_per_game * (1 - waste_share)
        levels            = completed_actions / actions_per_level
    """
    return actions_per_game * (1.0 - waste_share) / actions_per_level


def actions_for_depth(levels: float, actions_per_level: float,
                      waste_share: float) -> float:
    """Actions per game needed to reach a depth, inverting the model above."""
    return levels * actions_per_level / (1.0 - waste_share)


def tokens_per_action(tokens_per_call: float, actions_per_call: float) -> float:
    """Cost of one action; the budget buys `tokens_per_game / this` actions."""
    return tokens_per_call / actions_per_call


def actions_per_level_for(levels: float, actions_per_game: float = ACTIONS_PER_GAME) -> float:
    """Actions per level implied by hitting `levels` within the time budget."""
    return actions_per_game / levels


def symbolic_coverage_needed(
    target_actions_per_level: float,
    baseline: float = ACTIONS_PER_LEVEL_C45,
    symbolic: float = ACTIONS_PER_LEVEL_SYMBOLIC,
) -> float:
    """Share of games a symbolic solver must cover to hit a target average.

    The symbolic path costs no tokens, so on the games it fires it replaces the
    LLM's cost per level with its own.
    """
    if not (symbolic < target_actions_per_level < baseline):
        return 0.0 if target_actions_per_level >= baseline else 1.0
    return (baseline - target_actions_per_level) / (baseline - symbolic)


@dataclass(frozen=True)
class ChainRegression:
    """The measured cost of the v13 chain, in the two currencies that matter."""

    actions_per_level_before: float = ACTIONS_PER_LEVEL_C45
    actions_per_level_after: float = ACTIONS_PER_LEVEL_V137

    @property
    def level_ratio(self) -> float:
        return self.actions_per_level_after / self.actions_per_level_before

    @property
    def levels_before(self) -> float:
        return ACTIONS_PER_GAME / self.actions_per_level_before

    @property
    def levels_after(self) -> float:
        return ACTIONS_PER_GAME / self.actions_per_level_after

    @property
    def score_before(self) -> float:
        return 100 * coverage(self.levels_before)

    @property
    def score_after(self) -> float:
        return 100 * coverage(self.levels_after)

    def line(self) -> str:
        return (
            f"v13 chain: {self.actions_per_level_before:.1f} -> "
            f"{self.actions_per_level_after:.1f} actions/level "
            f"(+{100 * (self.level_ratio - 1):.0f}%), "
            f"{self.levels_before:.2f} -> {self.levels_after:.2f} levels/game, "
            f"smoke {self.score_before:.1f} -> {self.score_after:.1f}"
        )
