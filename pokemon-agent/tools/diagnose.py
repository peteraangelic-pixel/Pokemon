"""Diagnostics: why do games end, and is our agent making obvious mistakes?

Runs N episodes between two agents and reports:

* the engine's end-of-game ``reason`` code histogram,
* game length distribution,
* how often our agent ended a turn without attacking although an attack was
  offered (wasted tempo), and how often it attacked.

Usage:
    python tools/diagnose.py --a agents/main_heuristic.py --b agents/main_random.py --games 20
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from run_match import load_agent  # noqa: E402


def instrument(agent_fn, stats: dict, tag: str):
    """Wrap an agent so we can watch what it chooses."""

    def wrapped(obs):
        out = agent_fn(obs)
        try:
            sel = obs.get("select")
            if sel is None:
                stats["deck_calls"] += 1
                return out
            cur = obs.get("current") or {}
            if int(cur.get("yourIndex", 0)) != stats["_me"]:
                return out
            opts = sel.get("option") or []
            types = [o.get("type") for o in opts]
            stats["decisions"] += 1
            stats["select_types"][sel.get("type")] += 1
            has_attack = 13 in types
            if 13 in [opts[i].get("type") for i in out if i < len(opts)]:
                stats["attacks"] += 1
            elif has_attack and types.count(14) and 14 in [opts[i].get("type") for i in out if i < len(opts)]:
                stats["ended_with_attack_available"] += 1
            if not out and opts:
                stats["empty_but_options"] += 1
        except Exception as exc:  # pragma: no cover - diagnostic only
            stats.setdefault("diag_errors", 0)
            stats["diag_errors"] += 1
            stats.setdefault("diag_error_msg", str(exc))
        return out

    return wrapped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=os.path.join(ROOT, "agents", "main_heuristic.py"))
    ap.add_argument("--b", default=os.path.join(ROOT, "agents", "main_random.py"))
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--bo", type=int, default=1)
    args = ap.parse_args()

    from kaggle_environments import make

    a = load_agent(args.a, "agent_a")
    b = load_agent(args.b, "agent_b")

    reasons = collections.Counter()
    turns = []
    wins = [0, 0]
    stats: dict = {"select_types": collections.Counter()}

    for g in range(args.games):
        sa = collections.Counter({"select_types": collections.Counter(), "_me": 0})
        if g % 2 == 0:
            agents = [instrument(a, sa, "A"), b]
            a_side = 0
        else:
            agents = [b, instrument(a, sa, "A")]
            a_side = 1
        sa["_me"] = a_side

        env = make("cabt", configuration={"bo": args.bo}, debug=False)
        env.run(agents)
        final = env.steps[-1]
        r = [final[0].get("reward"), final[1].get("reward")]
        if r[a_side] == 1:
            wins[0] += 1
        elif r[1 - a_side] == 1:
            wins[1] += 1

        last_obs = final[a_side].get("observation") or {}
        cur = last_obs.get("current") or {}
        turns.append(cur.get("turn"))
        for entry in reversed(last_obs.get("logs") or []):
            if isinstance(entry, dict) and entry.get("type") == 23:
                reasons[entry.get("reason")] += 1
                break
        for k, v in sa.items():
            if k == "select_types":
                stats["select_types"].update(v)
            elif k != "_me":
                stats[k] = stats.get(k, 0) + v

    print(f"A wins={wins[0]}  B wins={wins[1]}  games={args.games}")
    print(f"A win rate = {wins[0] / args.games:.3f}")
    print(f"\nend-of-game reason histogram: {dict(reasons)}")
    tt = [t for t in turns if t is not None]
    if tt:
        print(f"final turn: min={min(tt)} max={max(tt)} mean={sum(tt)/len(tt):.1f}")
    print("\nA-side decision stats:")
    for k in sorted(stats):
        if k.startswith("diag") or k == "select_types":
            continue
        print(f"  {k} = {stats[k]}")
    print(f"  select_types = {dict(stats['select_types'])}")
    for k in ("diag_errors", "diag_error_msg"):
        if k in stats:
            print(f"  {k} = {stats[k]}")
    print(f"  attacks made = {stats.get('attacks', 0)}")
    print(f"  ended turn with attack available = {stats.get('ended_with_attack_available', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
