"""Tests for local/budget_sim.py — the rev2 level-budget policy on recorded data."""
import glob, json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import budget_sim as B

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail else ""))
    if not cond: FAILS.append(name)

def load():
    games = []
    for f in sorted(glob.glob("local/benchmarks/r0*.json")):
        for g in json.load(open(f)).get("game_runs", []):
            h = g.get("history") or []; apl = g.get("actions_per_level") or []
            done = g.get("levels_completed", 0)
            if not h or not apl: continue
            s = 0; cum = []
            for e in h: s += (e.get("generated_tokens") or 0); cum.append(s)
            idx = 0; prev = 0; costs = []; parts = []
            for k in range(min(done, len(apl))):
                idx += apl[k]
                if idx <= len(cum):
                    costs.append(cum[idx-1] - prev); parts.append(cum[idx-1] - prev); prev = cum[idx-1]
            waste = cum[-1] - cum[idx-1] if idx and idx <= len(cum) else 0.0
            games.append(dict(run=f.split('/')[-1][:4], gid=g["game_id"][:6],
                              costs=parts, waste=waste))
    return games

def test_ladder_arithmetic():
    b = B.LevelBudget(static_cap=20000)
    check("no history -> cap is the static arming", b.cap(0) == 20000, f"{b.cap(0)}")
    check("after one reset the cap is x1.5", b.cap(1) == 30000, f"{b.cap(1)}")
    check("effective per-level budget is 3,25x arming",
          b.budget_for_level() == 65000, f"{b.budget_for_level()}")
    b60 = B.LevelBudget(static_cap=60000)
    check("arming 60000 gives 195000", b60.budget_for_level() == 195000, f"{b60.budget_for_level()}")

def test_median_rule_needs_two_levels():
    b = B.LevelBudget(static_cap=20000, costs=[80000.0])
    check("one recorded cost does NOT raise the cap", b.cap(0) == 20000, f"{b.cap(0)}")
    b2 = B.LevelBudget(static_cap=20000, costs=[80000.0, 80000.0])
    check("two recorded costs switch on 4x median (clamped)",
          b2.cap(0) == 150000, f"{b2.cap(0)}  (4*80000=320000 clamped to 150000)")

def test_rev2_arming_costs_levels():
    g = load(); total = sum(len(x["costs"]) for x in g)
    for cap in (20000, 60000):
        kept = sum(B.simulate(x["costs"], cap)[0] for x in g)
        print(f"    arming {cap}: {kept}/{total} levels kept ({100*kept/total:.0f}%)")
    k20 = sum(B.simulate(x["costs"], 20000)[0] for x in g)
    k60 = sum(B.simulate(x["costs"], 60000)[0] for x in g)
    check("arming 20000 keeps at most 80% of levels", k20 <= 0.80 * total, f"{k20}/{total}")
    check("arming 60000 keeps every level", k60 == total, f"{k60}/{total}")
    check("the difference is at least 15 levels", k60 - k20 >= 15, f"{k60-k20} levels")

def test_cap_is_inert_where_the_waste_is():
    g = load(); wastes = [x["waste"] for x in g if x["waste"] > 0]
    binding = 0
    for x in g:
        b = B.LevelBudget(static_cap=60000, costs=list(x["costs"]))
        if x["waste"] > b.budget_for_level(): binding += 1
    check("median waste is far below the 60000 budget",
          st.median(wastes) < 0.5 * 195000, f"median waste {st.median(wastes):.0f} vs budget 195000")
    check("at 60000 the cap binds in a minority of games", binding < len(g) * 0.5, f"{binding}/{len(g)}")

def test_protecting_level_one_is_free_at_60000():
    g = load(); total = sum(len(x["costs"]) for x in g)
    plain = sum(B.simulate(x["costs"], 60000)[0] for x in g)
    prot = sum(B.simulate(x["costs"], 60000, protect_level_one=True)[0] for x in g)
    check("min_done=1 changes nothing at 60000 (cap already generous)",
          prot == plain == total, f"plain={plain} protected={prot} total={total}")

if __name__ == "__main__":
    print("budget_sim tests (rev2 policy on recorded runs)")
    test_ladder_arithmetic(); test_median_rule_needs_two_levels()
    test_rev2_arming_costs_levels(); test_cap_is_inert_where_the_waste_is()
    test_protecting_level_one_is_free_at_60000()
    print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)
