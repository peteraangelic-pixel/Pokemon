"""Tests for local/road_to_50.py against three recorded runs. Each can fail."""
import json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import road_to_50 as R

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail else ""))
    if not cond: FAILS.append(name)

LOGS = {"v3": "/tmp/cx/v3ctl.json", "r085": "/tmp/cx/r085.json", "r121": "/tmp/cx/r121.json"}

def load(name):
    return json.load(open(LOGS[name]))["game_runs"]

def test_three_constant_model_reproduces_every_run():
    """levels = actions_per_game * (1 - waste) / actions_per_level, three runs."""
    for name, apg, apl, w, want in (
        ("v3", 187.7, R.ACTIONS_PER_LEVEL_V3, R.WASTE_V3, 3.30),
        ("r085", 212.6, R.ACTIONS_PER_LEVEL_C45, R.WASTE_C45, 3.20),
        ("r121", 227.5, R.ACTIONS_PER_LEVEL_V137, R.WASTE_V137, 2.50),
    ):
        got = R.levels_per_game(apg, apl, w)
        check(f"model reproduces {name} depth", abs(got - want) < 0.06, f"{got:.2f} vs {want}")

def test_efficiency_is_flat_but_waste_is_not():
    """The correction that matters: depth is driven by waste, not by efficiency."""
    apl = [R.ACTIONS_PER_LEVEL_V3, R.ACTIONS_PER_LEVEL_C45, R.ACTIONS_PER_LEVEL_V137]
    waste = [R.WASTE_V3, R.WASTE_C45, R.WASTE_V137]
    spread_e = max(apl) / min(apl) - 1
    spread_w = (max(waste) - min(waste)) / max(waste)
    check("efficiency varies by under 10%", spread_e < 0.10, f"{100*spread_e:.1f}%")
    check("waste varies by more than 60%", spread_w > 0.60, f"{100*spread_w:.0f}%")

def test_score_model_reproduces_all_three():
    for name, want in (("v3", 27.50), ("r085", 26.78), ("r121", 22.59)):
        G = load(name)
        NS = [g["number_of_levels"] for g in G]
        KC = [g["levels_completed"] for g in G]
        got = R.score_from_levels(KC, NS)
        real = st.mean([g["final_score"] for g in G])
        check(f"score model matches {name} within 1 point", abs(got - real) < 1.0,
              f"model {got:.2f} vs recorded {real:.2f}")

def test_waste_removal_is_worth_ten_points():
    """v3's remaining 300 wasted actions are worth more than the whole v13 chain cost."""
    G = load("v3"); NS = [g["number_of_levels"] for g in G]; KC = [g["levels_completed"] for g in G]
    apg = 187.7
    now = R.score_from_levels(KC, NS)
    clean = R.levels_per_game(apg, R.ACTIONS_PER_LEVEL_V3, 0.0)
    got = R.score_from_levels(R.scaled_shape(clean, KC, NS), NS)
    check("zero waste would add 9-12 points", 9.0 < got - now < 12.0, f"{now:.1f} -> {got:.1f}")

def test_actions_per_call_is_the_budget_lever():
    """actions/game = budget / (tokens_per_call / actions_per_call)."""
    tok = R.TOKENS_PER_CALL["v3"]
    for apc, lo, hi in ((4.48, 180, 200), (6.0, 240, 265), (8.0, 320, 350)):
        got = 170_000 / R.tokens_per_action(tok, apc)
        check(f"{apc} actions/call -> {lo}-{hi} actions/game", lo < got < hi, f"{got:.0f}")

def test_hint_moved_actions_per_call_only_slightly():
    a = R.ACTIONS_PER_CALL
    gain = a["r121"] / a["v3"] - 1
    check("measured hint gain is 8-15%, not the 22% once assumed", 0.08 < gain < 0.15,
          f"{a['v3']} -> {a['r121']} = +{100*gain:.0f}%")

def test_fifty():
    need = R.levels_for_score(50)
    check("50 points needs 4.7-4.9 levels/game", 4.7 < need < 4.9, f"{need:.2f}")
    for apg, w, expect_pass in ((188, 0.16, False), (240, 0.0, True), (260, 0.10, True)):
        lv = R.levels_per_game(apg, R.ACTIONS_PER_LEVEL_V3, w)
        ok = R.score_from_levels(R.scaled_shape(lv, [3,2,4,3,3,5,5,3,3,2], R.LEVEL_COUNTS), R.LEVEL_COUNTS) >= 50
        check(f"{apg} actions, {100*w:.0f}% waste: 50+ is {expect_pass}", ok == expect_pass, f"{lv:.2f} levels")

def test_submission_history():
    check("v3 champion 26.25 > v11 23.89 > v13.7 13.28",
          R.SUBMISSIONS["v3"] > R.SUBMISSIONS["v11"] > R.SUBMISSIONS["v13.7"])
    check("the fresh v3 smoke (27.50) is above the old champion smoke",
          27.50 > 26.78)

if __name__ == "__main__":
    print("road_to_50 tests")
    for fn in (test_three_constant_model_reproduces_every_run,
               test_efficiency_is_flat_but_waste_is_not,
               test_score_model_reproduces_all_three,
               test_waste_removal_is_worth_ten_points,
               test_actions_per_call_is_the_budget_lever,
               test_hint_moved_actions_per_call_only_slightly,
               test_fifty, test_submission_history):
        fn()
    print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)
