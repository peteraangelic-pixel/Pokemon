"""Pins the numbers published in MEGA-DIAGNOSIS.md section 5.

If someone changes the scheduler, these tests fail loudly rather than silently
drifting the analysis. Run with:  python3 -m pytest local/test_scheduler.py -q
or plain:  python3 local/test_scheduler.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scheduler import (  # noqa: E402
    R018_GAMES,
    ValueScheduler,
    marginal_value,
    plan,
    total_weight,
)


def test_total_weight():
    assert total_weight(7) == 28
    assert total_weight(9) == 45
    assert total_weight(4) == 10


def test_marginal_value_is_back_loaded():
    # Level 1 of a 7-level game carries weight 1 of 28; the last level 7 of 28.
    assert abs(marginal_value(0, 7) - 1 / 28) < 1e-12
    assert abs(marginal_value(6, 7) - 7 / 28) < 1e-12
    # And a short game pays far more for the same first level.
    assert marginal_value(0, 4) > 4 * marginal_value(0, 9)
    assert marginal_value(7, 7) == 0.0


def test_r018_shape():
    assert len(R018_GAMES) == 10
    by_name = dict(R018_GAMES)
    assert by_name["tn36"] == 7
    assert by_name["su15"] == 9


def test_greedy_reproduces_published_table():
    # Column "greedy (C0=45)" of MEGA-DIAGNOSIS.md section 5.
    expected = {206: 24.2, 275: 36.3, 300: 36.3, 400: 46.1, 600: 72.4, 900: 100.0}
    for budget, want in expected.items():
        got = plan(R018_GAMES, budget, prior_cost=45.0)
        assert abs(got - want) < 0.05, f"{budget}: {got} != {want}"


def test_greedy_reproduces_c0_30_column():
    expected = {275: 40.3, 400: 52.8}
    for budget, want in expected.items():
        got = plan(R018_GAMES, budget, prior_cost=30.0)
        assert abs(got - want) < 0.05, f"{budget}: {got} != {want}"


def test_equal_split_reproduces_ceiling():
    # With a per-game budget and no reallocation this is just the ceiling table.
    from scheduler import _R018_COSTS

    eff = 0.9

    def coverage(spent, human):
        used = k = 0
        for c in human:
            c /= eff
            if used + c <= spent + 1e-9:
                used += c
                k += 1
            else:
                break
        return sum(range(1, k + 1)) / total_weight(len(human))

    for budget, want in {206: 18.7, 275: 28.3, 400: 51.3}.items():
        got = 100 * sum(coverage(budget, h) for h in _R018_COSTS.values()) / len(_R018_COSTS)
        assert abs(got - want) < 0.05, f"{budget}: {got} != {want}"


def test_live_scheduler_prefers_short_games():
    # Same level count difference: the 4-level game must win the first quantum.
    sched = ValueScheduler(games=[("long", 9), ("short", 4)])
    assert sched.next_game() == 1


def test_live_scheduler_tracks_budget():
    sched = ValueScheduler(games=[("a", 3)], total_budget=100)
    assert sched.next_game() == 0
    sched.record(0, 60)
    assert sched.remaining == 40
    sched.record(0, 40)
    assert sched.exhausted()
    assert sched.next_game() is None


def test_live_scheduler_closes_finished_games():
    sched = ValueScheduler(games=[("a", 1)], total_budget=1000)
    sched.record(0, 10, level_completed=True)
    assert sched.next_game() is None
    # closing an unfinished game also removes it from play
    sched2 = ValueScheduler(games=[("b", 5)], total_budget=1000)
    sched2.close(0)
    assert sched2.next_game() is None


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
