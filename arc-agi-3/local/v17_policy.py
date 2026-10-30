"""v17 policy: the parts that decide which of the two diverged v15s to ship.

Why this module exists
----------------------
There are two packages both called ``duck-v15`` and they are NOT the same build:

  * ``Pokemon@a450b00f``  ``8d96c68`` — duck-v14 + patch 0007 = escalate-relative
  * ``Gemma-konkurs@c4eeb067`` ``07bf05e`` — duck-v13.3-arena + v14's env-only parts

Both carry a patch numbered 0007 and both say "7 patches", so a naive reader
concludes they are updates of each other. They are divergent. This module holds
the arithmetic needed to choose, so the choice is not an opinion.

Everything here is derived from numbers already in the repository:
  local/benchmarks/r0{13,15,18}.json  (actions per generation, 30 games)
  local/metric.py                     (the authoritative score, verified 30/30)
"""

from __future__ import annotations

from dataclasses import dataclass

# --- budget model (EVAL-BUDGET-MODEL.md) ------------------------------------
TOKENS_PER_GAME = 186_200     # 2 945 s / 15,8 ms per token
TOK_PER_ACTION_BASELINE = 853
ACTIONS_PER_GEN_BASELINE = 4.61   # our measurement; c87 independently 4,357
ESCALATE_DIRECTIVE_TOKENS = 146   # 540 chars, quoted by Gemma's v14/v15 README

# --- the target (V16-PLAN.md §0) -------------------------------------------
ACTIONS_NEEDED_FOR_50 = 253       # 50% coverage at 42 actions per level

# Every recorded run's mean actions/generation. The gate must fail all of them.
RECORDED_ACTIONS_PER_GEN = {"r013": 5.38, "r015": 4.57, "r018": 5.20}

# r018, 32 completed levels: injections of the escalation directive.
RECORDED_INJECTIONS = {"thr10": 121, "thr20": 52, "thr20_cap2": 39, "relative": 4}
RECORDED_GAMES = 10


def actions_per_generation_needed(actions_per_game: float) -> float:
    """Actions/generation implied by hitting ``actions_per_game`` on this budget.

    Tokens per action scales inversely with actions per generation, because a
    generation costs a roughly fixed number of tokens.
    """
    return ACTIONS_PER_GEN_BASELINE * TOKENS_PER_GAME / (
        TOK_PER_ACTION_BASELINE * actions_per_game
    )


def actions_per_game(apg: float) -> float:
    """Actions per game available at a given actions-per-generation rate."""
    return TOKENS_PER_GAME / (TOK_PER_ACTION_BASELINE * ACTIONS_PER_GEN_BASELINE / apg)


def escalation_cost_actions(injections: int, games: int = RECORDED_GAMES) -> float:
    """Direct token cost of the escalation directive, expressed in actions.

    This is the *direct prompt* cost only. The directive also changes behaviour,
    which is unmeasured — see ``escalation_robustness``.
    """
    return (injections / games) * ESCALATE_DIRECTIVE_TOKENS / TOK_PER_ACTION_BASELINE


def escalation_robustness(factor: float = 10.0) -> float:
    """Worst case: if the directive really costs ``factor``x its prompt length
    (a whole generation spent building a model instead of acting), the swing
    between the best and worst escalation policy is still this many actions."""
    best = escalation_cost_actions(RECORDED_INJECTIONS["relative"])
    worst = escalation_cost_actions(RECORDED_INJECTIONS["thr10"])
    return (worst - best) * factor


# --- the gate ---------------------------------------------------------------

GATE_THRESHOLD = 6.0


@dataclass(frozen=True)
class GateResult:
    threshold: float
    observed: float
    passed: bool
    implied_actions_per_game: float

    def line(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"v17 gate: actions_per_call={self.observed:.2f} "
            f"threshold={self.threshold:.2f} {verdict} "
            f"implied_actions_per_game={self.implied_actions_per_game:.0f}"
        )


def opener_gate(observed_actions_per_call: float, threshold: float = GATE_THRESHOLD) -> GateResult:
    """The GO/NO-GO test for the opener-batching hint.

    A test that cannot fail is not a test. Gemma's v15 gate is
    ``actions_per_call >= 1,8``; every recorded run already clears it (means
    4,57 / 5,20 / 5,38), so it certifies the hint whether or not the hint works.
    This gate is set above the highest observed run mean, so a passing result is
    evidence and a failing result is information.
    """
    return GateResult(
        threshold=threshold,
        observed=observed_actions_per_call,
        passed=observed_actions_per_call >= threshold,
        implied_actions_per_game=actions_per_game(observed_actions_per_call),
    )


def gate_is_reachable(threshold: float = GATE_THRESHOLD) -> bool:
    """A gate above the 50-point budget is pointless: nothing below it is worth
    shipping, nothing above it is needed. This checks the gate sits at the point
    where the extra actions start to matter."""
    return actions_per_game(threshold) >= ACTIONS_NEEDED_FOR_50 * 0.95


# --- patch composition ------------------------------------------------------

def patch_collisions(a: dict[str, list[str]], b: dict[str, list[str]]) -> list[str]:
    """Filenames touched by both patch sets.

    Two packages numbering a patch ``0007`` is harmless if they touch different
    files; it is a hard conflict if they touch the same one. The *numbers* are
    labels, so they are deliberately ignored here — comparing numbers instead of
    files would report a clash between every pair of sets that happens to use
    the same numbering, which is the opposite of the useful answer.
    """
    files_a = {f for files in a.values() for f in files}
    files_b = {f for files in b.values() for f in files}
    return sorted(files_a & files_b)


def compose(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    """Merge two patch sets, renaming ``b``'s numbers above ``a``'s maximum.

    Assumes ``patch_collisions`` returned empty. Renaming is by number only:
    patch content is untouched, which is what lets each side keep its own
    verification.
    """
    clash = patch_collisions(a, b)
    if clash:
        raise ValueError(f"patch sets touch the same files: {clash}")
    out = dict(a)
    top = max((int(k) for k in a), default=0)
    for i, (name, files) in enumerate(sorted(b.items()), start=1):
        out[f"{top + i:04d}"] = files
    return out
