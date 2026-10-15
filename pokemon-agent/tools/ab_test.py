"""Head-to-head A/B test between two builds of the same agent.

This is the tool that decides whether a change earns one of the 5 daily
submission slots: identical deck, identical matchmaking, only the knob differs.
Sides alternate every game so turn-order effects cancel out.

Usage
-----
    python tools/ab_test.py --agent agents/main_heuristic.py \\
        --env-a PTCG_VAR_DMG=1 --env-b PTCG_VAR_DMG=0 --games 200

Reports win rate plus a two-sided z-score so a "win" can be told apart from
noise (see NOTES_STRATEGY.md for the sample-size reasoning).
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_with_env(path: str, name: str, env: dict):
    """Import a module with a temporary environment (knobs read at import time)."""
    saved = dict(os.environ)
    os.environ.update(env)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=os.path.join(ROOT, "agents", "main_heuristic.py"))
    ap.add_argument("--env-a", default="", help="e.g. PTCG_VAR_DMG=1")
    ap.add_argument("--env-b", default="", help="e.g. PTCG_VAR_DMG=0")
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--bo", type=int, default=1)
    args = ap.parse_args()

    def parse_env(s: str) -> dict:
        out = {}
        for part in s.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    from kaggle_environments import make

    mod_a = load_with_env(args.agent, "ab_a", parse_env(args.env_a))
    mod_b = load_with_env(args.agent, "ab_b", parse_env(args.env_b))

    wins = [0, 0]
    draws = 0
    for g in range(args.games):
        a_first = g % 2 == 0
        agents = [mod_a.agent, mod_b.agent] if a_first else [mod_b.agent, mod_a.agent]
        env = make("cabt", configuration={"bo": args.bo}, debug=False)
        env.run(agents)
        final = env.steps[-1]
        r = [final[0].get("reward"), final[1].get("reward")]
        a_side = 0 if a_first else 1
        if r[a_side] == 1:
            wins[0] += 1
        elif r[1 - a_side] == 1:
            wins[1] += 1
        else:
            draws += 1
        if (g + 1) % 25 == 0:
            print(f"  ...{g+1}/{args.games}  A={wins[0]} B={wins[1]}", flush=True)

    n = wins[0] + wins[1]
    print("=" * 62)
    print(f"A (env: {args.env_a or 'defaults'}) wins = {wins[0]}")
    print(f"B (env: {args.env_b or 'defaults'}) wins = {wins[1]}")
    print(f"draws={draws}  decisive games={n}")
    if n:
        wr = wins[0] / n
        z = (wins[0] - n / 2) / math.sqrt(n / 4) if n else 0.0
        print(f"A win rate = {wr:.4f}   z = {z:+.2f}")
        if abs(z) < 2:
            print("=> NOT significant at p<0.05 (95% CI includes 50%)")
        else:
            print(f"=> SIGNIFICANT at p<0.05, favouring {'A' if z > 0 else 'B'}")
        # How many games to detect this effect size reliably?
        delta = abs(wr - 0.5)
        if delta > 1e-9:
            # 80% power, two-sided alpha=0.05, p=0.5 -> n ~= 7.85 * 0.25 / delta^2
            need = int(math.ceil(7.85 * 0.25 / (delta ** 2)))
            print(f"   ~{need} decisive games needed for a stable read at this effect size")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
