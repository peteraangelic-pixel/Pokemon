"""Tests for local/v17_policy.py. Every one of these can fail."""
import json
import glob
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import v17_policy as P

FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# --- 1. the recorded data still says what the policy assumes -----------------
def test_recorded_rates_unchanged():
    """If the benchmarks move, the gate threshold must be re-derived, not kept."""
    obs = {}
    for f in sorted(glob.glob("local/benchmarks/r0*.json")):
        d = json.load(open(f))
        per = []
        for g in d.get("game_runs", []):
            c = sum(1 for e in (g.get("history") or [])
                    if isinstance(e, dict) and (e.get("generated_tokens") or 0) > 0)
            if c:
                per.append(sum(g.get("actions_per_level") or []) / c)
        if per:
            obs[Path(f).stem] = round(st.mean(per), 2)
    for k, v in P.RECORDED_ACTIONS_PER_GEN.items():
        check(f"rate {k} still {v}", abs(obs.get(k, 0) - v) <= 0.02,
              f"file says {obs.get(k)}")
    return obs


# --- 2. the old gate cannot fail -------------------------------------------
def test_old_gate_cannot_fail():
    """Gemma's v15 gate is 1,8. Every recorded run already passes it."""
    lowest = min(P.RECORDED_ACTIONS_PER_GEN.values())
    check("old gate 1,8 is below the worst recorded mean", 1.8 < lowest,
          f"worst mean = {lowest}")
    check("old gate therefore certifies a dead lever", P.opener_gate(lowest, 1.8).passed)


# --- 3. the new gate can fail, on real runs --------------------------------
def test_new_gate_rejects_every_recorded_run():
    for k, v in P.RECORDED_ACTIONS_PER_GEN.items():
        r = P.opener_gate(v)
        check(f"new gate rejects {k} ({v})", not r.passed, r.line())


def test_new_gate_is_reachable_and_meaningful():
    check("gate sits at the 50-point budget", P.gate_is_reachable(),
          f"gate {P.GATE_THRESHOLD} -> {P.actions_per_game(P.GATE_THRESHOLD):.0f} actions/game")
    r = P.opener_gate(6.5)
    check("a good result passes", r.passed, r.line())
    check("passing gives enough actions for 50",
          r.implied_actions_per_game >= P.ACTIONS_NEEDED_FOR_50,
          f"{r.implied_actions_per_game:.0f} >= {P.ACTIONS_NEEDED_FOR_50}")


# --- 4. half the hint effect is already enough -----------------------------
def test_half_effect_reaches_the_target():
    half = (P.ACTIONS_PER_GEN_BASELINE + 6.73) / 2     # opener 4,61 -> resumption 6,73
    got = P.actions_per_game(half)
    check("half the measured hint effect clears 253 actions",
          got >= P.ACTIONS_NEEDED_FOR_50, f"{half:.2f} actions/gen -> {got:.0f}/game")
    check("today does not clear it",
          P.actions_per_game(P.ACTIONS_PER_GEN_BASELINE) < P.ACTIONS_NEEDED_FOR_50,
          f"{P.actions_per_game(P.ACTIONS_PER_GEN_BASELINE):.0f}/game")


# --- 5. escalation is a rounding error against the hint --------------------
def test_escalation_is_rounding_error():
    span = P.escalation_robustness(factor=1.0)
    check("best-vs-worst escalation policy is under 3 actions/game",
          span < 3.0, f"{span:.2f} actions")
    even_10x = P.escalation_robustness(factor=10.0)
    hint_gain = P.actions_per_game((P.ACTIONS_PER_GEN_BASELINE + 6.73) / 2) - \
        P.actions_per_game(P.ACTIONS_PER_GEN_BASELINE)
    check("even at 10x behavioural cost the hint dominates",
          hint_gain > even_10x, f"hint +{hint_gain:.0f} vs escalation {even_10x:.1f}")
    check("cap 2 halves the injection count",
          P.RECORDED_INJECTIONS["thr20_cap2"] < P.RECORDED_INJECTIONS["thr20"] * 0.8,
          f"{P.RECORDED_INJECTIONS['thr20']} -> {P.RECORDED_INJECTIONS['thr20_cap2']}")


# --- 6. the two v15 patch sets compose ------------------------------------
def test_patch_sets_compose():
    a450_0007 = ["ARC3-Inference/inference/agent/tool_agent.py",
                 "ARC3-Inference/inference/framework/solver.py",
                 "ARC3-Inference/inference/utils/plan_commit.py"]
    gemma_0007 = ["ARC3-Inference/inference/framework/arc3_winpath.py"]
    check("the two patches numbered 0007 touch different files",
          P.patch_collisions({"0007": a450_0007}, {"0007": gemma_0007}) == [])
    merged = P.compose({"0001": ["x"], "0007": gemma_0007}, {"0007": a450_0007})
    check("composition renumbers instead of overwriting",
          len(merged) == 3 and "0008" in merged, str(sorted(merged)))


def test_compose_refuses_a_real_clash():
    try:
        P.compose({"0007": ["same.py"]}, {"0007": ["same.py"]})
        check("compose refuses identical file sets", False, "no exception")
    except ValueError:
        check("compose refuses identical file sets", True)


if __name__ == "__main__":
    print("v17 policy tests")
    test_recorded_rates_unchanged()
    test_old_gate_cannot_fail()
    test_new_gate_rejects_every_recorded_run()
    test_new_gate_is_reachable_and_meaningful()
    test_half_effect_reaches_the_target()
    test_escalation_is_rounding_error()
    test_patch_sets_compose()
    test_compose_refuses_a_real_clash()
    print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)
