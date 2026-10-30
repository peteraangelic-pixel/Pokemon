"""Tests for the v14 policy and simulator. Run: python3 local/test_v14.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from v14_policy import (
    LevelGovernor,
    LevelCost,
    GameRun,
    actions_per_game,
    load_run,
    marginal_value,
    simulate,
    short_game_priority,
    total_weight,
)


def test_budget_is_tokens_not_turns():
    # 2945 s / (15.8 ms/token * 853 tok/action) = 219 actions, not 205 decisions
    a = actions_per_game()
    assert 215 < a < 223, a


def test_level_weights_are_back_loaded():
    assert total_weight(7) == 28
    assert abs(marginal_value(0, 7) - 1 / 28) < 1e-12
    assert abs(marginal_value(6, 7) - 7 / 28) < 1e-12
    assert marginal_value(7, 7) == 0.0


def test_short_game_pays_more_for_first_level():
    # Level 1 (weight 1) of a 4-level game is 1/10; of a 9-level game 1/45.
    assert abs(marginal_value(0, 4) - 1 / 10) < 1e-12
    assert abs(marginal_value(0, 9) - 1 / 45) < 1e-12
    # The NEXT level of a 4-level game (k=1) is worth 2/10 = 20%.
    assert abs(marginal_value(1, 4) - 2 / 10) < 1e-12


def _run(game_id, levels, costs):
    per = [LevelCost(a, done) for a, done in costs]
    return GameRun(game_id, levels, per)


def test_equal_policy_reproduces_observed_coverage():
    # Two 4-level games, both finish 2 levels at 10 actions each; budget 219.
    runs = [_run("aaaa", 4, [(10, True), (10, True), (50, False), (50, False)]),
            _run("bbbb", 4, [(10, True), (10, True), (50, False), (50, False)])]
    # Each game has 219 actions; 20 spent, then it stalls on level 3.
    # Coverage = (1+2)/10 = 30% each.
    score = simulate(runs, "equal", generous=False)
    assert abs(score - 30.0) < 0.01, score


def test_pessimistic_and_optimistic_disagree_on_stalled_levels():
    runs = [_run("aaaa", 4, [(10, True), (60, False), (60, False), (60, False)])]
    pes = simulate(runs, "equal", generous=False)
    opt = simulate(runs, "equal", generous=True)
    # Pessimistic: level 2 never falls, coverage = 1/10.
    assert abs(pes - 10.0) < 0.01, pes
    # Optimistic: level 2 needs 120 and the budget is 219, so it falls too.
    assert opt > pes, (opt, pes)


def test_cap_reclaims_and_redistributes():
    # One hopeless game that would burn its whole budget, one productive game.
    runs = [
        _run("dead", 4, [(1, True), (400, False), (400, False), (400, False)]),
        _run("good", 4, [(20, True), (30, True), (40, True), (500, False)]),
    ]
    equal = simulate(runs, "equal", generous=False)
    capped = simulate(runs, "cap", generous=False, cap=60)
    # Freeing the dead game's budget must not make the result worse
    # under the pessimistic bound, and it funds `good`'s level 3..4 attempt.
    assert capped >= equal, (capped, equal)


def test_cap_can_hurt_under_optimism():
    """The whole point of the two bounds: capping is a bet, not a free win."""
    runs = [_run("late", 4, [(10, True), (150, False), (200, False), (200, False)])]
    equal = simulate(runs, "equal", generous=True)
    capped = simulate(runs, "cap", generous=True, cap=40)
    assert capped <= equal, (capped, equal)


def test_governor_abandons_at_cap():
    g = LevelGovernor(level_cap=100)
    for _ in range(99):
        g.on_action()
    assert not g.should_abandon_level()
    g.on_action()
    assert g.should_abandon_level()
    g.on_level_change()
    assert not g.should_abandon_level()


def test_governor_nudges_only_after_evidence():
    g = LevelGovernor(min_plan_steps=5)
    g.on_plan(2)
    assert not g.should_nudge_for_plan(), "za wcześnie na wniosek z jednego planu"
    g.on_plan(2)
    g.on_plan(2)
    assert g.should_nudge_for_plan()


def test_governor_long_plans_never_nudge():
    g = LevelGovernor(min_plan_steps=5)
    for _ in range(6):
        g.on_plan(12)
    assert not g.should_nudge_for_plan()
    assert g.short_plans == 0


def test_tokens_per_action_is_the_metric():
    g = LevelGovernor()
    assert abs(g.tokens_per_action(8530.0, 10) - 853.0) < 1e-9
    assert g.tokens_per_action(0.0, 0) == float("inf")


def test_short_game_priority_ranks_by_marginal_value():
    runs = [_run("long", 9, [(10, True)] * 3), _run("short", 4, [(10, True)])]
    ranked = short_game_priority(runs)
    assert ranked[0][0] == "short", ranked


def test_real_benchmarks_load():
    for name in ("r013", "r015", "r018"):
        path = pathlib.Path(__file__).parent / "benchmarks" / f"{name}.json"
        runs = load_run(json.loads(path.read_text()))
        assert len(runs) == 10, (name, len(runs))
        assert all(r.levels > 0 for r in runs)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL {name}: {exc}")
    print("OK" if failures == 0 else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
