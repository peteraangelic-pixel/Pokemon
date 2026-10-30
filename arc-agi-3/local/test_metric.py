"""Verifies the score rule against all 30 recorded runs. Run: python3 local/test_metric.py"""
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from metric import actions_needed_for, game_score, level_points, mean_score  # noqa: E402


def _runs():
    for path in sorted(glob.glob(str(pathlib.Path(__file__).parent / "benchmarks" / "*.json"))):
        data = json.loads(pathlib.Path(path).read_text())
        for g in data["game_runs"]:
            yield (g["game_id"], g["base_actions_per_level"], g["actions_per_level"],
                   g["levels_completed"], g["final_score"])


def test_reproduces_all_30_recorded_scores():
    bad = []
    n = 0
    for gid, base, acts, k, want in _runs():
        n += 1
        got = game_score(base, acts, k)
        if abs(got - want) > 0.02:
            bad.append((gid, want, round(got, 2)))
    assert n == 30, n
    assert not bad, bad


def test_perfect_match_scores_100():
    # Matching the human exactly on every level: s_k = 100, completion cap = 100.
    assert abs(game_score([50, 50, 50], [50, 50, 50], 3) - 100.0) < 1e-9


def test_beating_human_is_capped_at_115_not_unlimited():
    # 10x faster still scores 115 per level, and the completion cap holds it at 100.
    assert level_points(100, 10) == 115.0
    assert abs(game_score([100] * 4, [10] * 4, 4) - 100.0) < 1e-9


def test_completion_cap_is_the_reason_depth_dominates():
    # Weights are 1,2,3,4 out of 10, so covering the first k levels caps you at
    # (1+..+k)/10 of the game. This is the whole reason depth beats speed.
    assert abs(game_score([50] * 4, [100] * 4, 4) - 25.0) < 1e-9     # all done, 2x cost
    assert abs(game_score([50] * 4, [50, 50, 50, 0], 3) - 60.0) < 1e-9  # 3 of 4 -> 6/10
    assert abs(game_score([50] * 4, [50, 50, 0, 0], 2) - 30.0) < 1e-9   # 2 of 4 -> 3/10
    assert abs(game_score([50] * 4, [50, 0, 0, 0], 1) - 10.0) < 1e-9    # 1 of 4 -> 1/10


def test_unfinished_levels_contribute_nothing():
    # A level in progress (actions spent, not completed) must score zero.
    one = game_score([50] * 4, [50, 999, 0, 0], 1)
    assert abs(one - 10.0) < 1e-9


def test_old_wrong_formula_disagrees():
    """Guard against reverting to our old rule (ratio cap 1.15, no completion cap)."""
    def old(baselines, actions, completed, ratio_cap=1.15):
        n = len(baselines)
        denom = sum(range(1, n + 1))
        return 100.0 * sum(
            (i + 1) * min(baselines[i] / actions[i], ratio_cap) ** 2
            for i in range(completed) if i < len(actions) and actions[i]
        ) / denom

    # 3 of 4 levels, three times faster than human: the old rule pays 79.35,
    # the real rule is held at the completion cap of 60.
    args = ([50] * 4, [10, 10, 10, 0], 3)
    assert abs(old(*args) - 79.35) < 0.01, old(*args)
    assert abs(game_score(*args) - 60.0) < 1e-9


def test_actions_needed_for():
    assert abs(actions_needed_for(100.0, 50) - 50.0) < 1e-9
    assert abs(actions_needed_for(25.0, 50) - 100.0) < 1e-9
    assert actions_needed_for(0.0, 50) == float("inf")


def test_mean_over_games():
    games = [([50] * 4, [50] * 4, 4), ([50] * 4, [50, 0, 0, 0], 1)]
    assert abs(mean_score(games) - (100.0 + 10.0) / 2) < 1e-9


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
