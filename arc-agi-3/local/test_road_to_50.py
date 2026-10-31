"""Tests for local/road_to_50.py. Each one can fail."""
import glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import road_to_50 as R

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail else ""))
    if not cond: FAILS.append(name)

RR = "/tmp/smak/arc-agi-3/kaggle/ops/results"

def test_coverage_matches_a_real_run():
    """r085: 3.20 levels/game, recorded final_score 26.78."""
    import statistics as st
    try:
        d = json.load(open(f"{RR}/r085-kernel_output_pick/output-pick/benchmark.json"))
    except FileNotFoundError:
        print("  SKIP (brak logu r085 w tym sandboxie)"); return
    ns = [g["number_of_levels"] for g in d["game_runs"]]
    got = 100 * R.coverage(3.20, ns)
    want = st.mean([g["final_score"] for g in d["game_runs"]])
    check("model reproduces r085 within 4 points", abs(got - want) < 4.0,
          f"model {got:.1f} vs recorded {want:.1f}")

def test_reproduces_real_level_counts():
    check("level counts are 6..9 and mean 6.9",
          min(R.LEVEL_COUNTS) == 6 and max(R.LEVEL_COUNTS) == 9
          and abs(sum(R.LEVEL_COUNTS)/len(R.LEVEL_COUNTS) - 6.9) < 0.05,
          str(R.LEVEL_COUNTS))

def test_monotone():
    prev = -1
    for k in range(0, 10):
        c = R.coverage(k)
        check(f"coverage monotone at k={k}", c >= prev, f"{c:.3f}")
        prev = c

def test_fifty_needs_about_four_and_a_half_levels():
    k = R.levels_for_score(50)
    check("50 points needs 4.7-5.1 levels/game", 4.7 < k < 5.1, f"{k:.2f}")
    check("that is 43-47 actions per level",
          43 < R.actions_per_level_for(k) < 47,
          f"{R.actions_per_level_for(k):.1f}")

R085_LEVELS = [1, 4, 5, 3, 5, 3, 2, 3, 3, 3]
R121_LEVELS = [0, 5, 1, 2, 3, 5, 4, 2, 3, 0]

def test_the_chain_regression():
    r = R.ChainRegression()
    check("chain adds at least 30% actions per level", r.level_ratio > 1.30, r.line())
    c85 = R.score_from_levels(R085_LEVELS)
    c121 = R.score_from_levels(R121_LEVELS)
    check("calibrated model reproduces both recorded smoke scores within 2",
          abs(c85 - 26.78) < 2.0 and abs(c121 - 22.59) < 2.0,
          f"{c85:.1f} vs 26.78 | {c121:.1f} vs 22.59")
    check("the real smoke drop is smaller than the uniform model predicts",
          (c85 - c121) < (r.score_before - r.score_after),
          f"real {c85-c121:.1f} vs uniform {r.score_before-r.score_after:.1f}")

def test_submission_history():
    check("champion is v3 at 26.25", R.SUBMISSIONS["v3"] == 26.25)
    check("the patched chain scored below both earlier builds",
          R.SUBMISSIONS["v13.7"] < R.SUBMISSIONS["v11"] < R.SUBMISSIONS["v3"])

def test_concentration_uplift_is_large():
    u85 = R.concentration_uplift(R085_LEVELS)
    u121 = R.concentration_uplift(R121_LEVELS)
    check("uneven depth is worth >10% over uniform on the good run", u85 > 1.10, f"{u85:.2f}x")
    check("and >30% on the bad run (two games at zero)", u121 > 1.30, f"{u121:.2f}x")

def test_symbolic_coverage_needed():
    target = R.actions_per_level_for(R.levels_for_score(50))
    f = R.symbolic_coverage_needed(target)
    check("50 points needs about a third of the roster on the symbolic path",
          0.28 < f < 0.38, f"{f:.1%} at {target:.1f} actions/level")
    f35 = R.symbolic_coverage_needed(R.actions_per_level_for(R.levels_for_score(35)))
    check("35 points (public notebook ceiling) needs about a sixth",
          0.12 < f35 < 0.22, f"{f35:.1%}")
    check("with no symbolic coverage the target is unreachable via that route",
          R.symbolic_coverage_needed(R.ACTIONS_PER_LEVEL_C45) == 0.0)

if __name__ == "__main__":
    print("road_to_50 tests")
    for fn in (test_reproduces_real_level_counts, test_monotone,
               test_fifty_needs_about_four_and_a_half_levels,
               test_the_chain_regression, test_concentration_uplift_is_large,
               test_submission_history, test_symbolic_coverage_needed,
               test_coverage_matches_a_real_run):
        fn()
    print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)
