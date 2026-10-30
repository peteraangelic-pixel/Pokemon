"""Tests for the v15 baseline-aware governor. Run: python3 local/test_v15.py"""
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from metric import game_score  # noqa: E402
from v15_policy import (  # noqa: E402
    GameGovernor,
    baseline_available,
    best_next_level,
    escalate_at,
    required_coverage,
)


def test_baseline_available_detects_populated_and_empty():
    assert baseline_available([32, 72, 26])
    assert not baseline_available([])
    assert not baseline_available(None)
    assert not baseline_available([0, 0, 0]), "same slownik z zerami = brak baseline"


def test_escalate_relative_beats_absolute():
    # Human needs 300 on this level: v13.2 fired at 10, i.e. 30x too early.
    assert escalate_at([300, 208], 0) == 360
    assert escalate_at([300, 208], 0) > 10
    # Floor protects a level the human solved in a handful of actions.
    assert escalate_at([5], 0, floor=20) == 20


def test_escalate_falls_back_without_baseline():
    assert escalate_at(None, 0, floor=20) == 20
    assert escalate_at([], 3, floor=20) == 20
    assert escalate_at([0], 0, floor=20) == 20


def test_escalate_matches_gemma_measurement():
    """On r085 32 completed levels, relative fired 8x and 0/32 premature."""
    d = json.loads((pathlib.Path(__file__).parent / "benchmarks" / "r018.json").read_text())
    fires = 0
    premature = 0
    checked = 0
    for g in d["game_runs"]:
        base = g["base_actions_per_level"]
        k = g["levels_completed"]
        for i in range(k):
            if i >= len(base) or i >= len(g["actions_per_level"]):
                continue
            acts = g["actions_per_level"][i]
            checked += 1
            thr = escalate_at(base, i)
            if acts >= thr:
                fires += 1
                # premature = we were at or better than human pace when nudged
                if acts <= base[i]:
                    premature += 1
    assert checked >= 20, checked
    assert premature == 0, f"{premature}/{checked} przedwczesnych"
    assert fires <= checked // 3, fires


def test_no_baseline_reproduces_floor_behaviour():
    g = GameGovernor(level_count=5, baselines=None)
    assert g.level_budget() == g.level_cap_floor
    assert g.escalate_threshold() == 20
    for _ in range(g.level_cap_floor):
        g.on_action()
    assert g.should_abandon_level()


def test_baseline_extends_budget_on_expensive_levels():
    # Human needed 300: we should be allowed far more than the 120 floor.
    g = GameGovernor(level_count=3, baselines=[300, 100, 50])
    assert g.level_budget() > 300, g.level_budget()


def test_cheap_level_gets_short_budget():
    # Human solved it in 8 actions; we should not grind it for 120.
    g = GameGovernor(level_count=3, baselines=[8, 100, 50])
    assert g.level_budget() == g.level_cap_floor  # floor still applies


def test_governor_tracks_coverage_and_score():
    g = GameGovernor(level_count=4, baselines=[10, 20, 30, 40])
    for _ in range(10):
        g.on_action()
    g.on_level_complete()
    for _ in range(20):
        g.on_action()
    g.on_level_complete()
    assert g.completed == 2
    assert abs(g.coverage() - 3 / 10) < 1e-12   # (1+2)/(1+2+3+4)
    # Both levels at exactly human cost -> 100 points each, held by the cap at 30.
    assert abs(g.current_score() - 30.0) < 1e-9, g.current_score()


def test_probe_line_reports_the_decisive_fields():
    g = GameGovernor(level_count=9, baselines=[22, 42, 26, 115, 36, 31, 8, 40, 41])
    line = g.probe_line("su15-1944f8ab")
    for token in ("game=su15", "levels=9", "baseline=yes", "escalate_at=", "score="):
        assert token in line, line


def test_best_next_level_prefers_short_games():
    long_g = GameGovernor(level_count=9, baselines=[50] * 9)
    short_g = GameGovernor(level_count=4, baselines=[50] * 4)
    pick = best_next_level([long_g, short_g], budget_left=1000)
    assert pick is not None
    assert pick[0] == 1, "krotka gra placi wiecej za ten sam poziom"


def test_required_coverage_matches_the_hard_cap():
    # score <= 100 * coverage, so 50 points needs at least 50% coverage.
    assert abs(required_coverage(50.0, 1.0) - 0.5) < 1e-12
    assert required_coverage(50.0, 0.9) > 0.5, "przy eff 0.9 trzeba wiecej niz 50%"
    assert required_coverage(100.0, 1.0) == 1.0


def test_all_real_games_supported():
    for run in ("r013", "r015", "r018"):
        d = json.loads((pathlib.Path(__file__).parent / "benchmarks" / f"{run}.json").read_text())
        for g in d["game_runs"]:
            gov = GameGovernor(level_count=g["number_of_levels"],
                               baselines=g["base_actions_per_level"])
            assert baseline_available(g["base_actions_per_level"])
            assert gov.level_budget() > 0
            assert gov.escalate_threshold() >= 20


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
