"""Wasted-action report for a local ARC-AGI-3 run report.

RHAE compares an agent's action count against the human median, so an action
that returns to an already-visited state is pure loss. This script measures
that loss per game.

Usage:
    python scripts/wasted.py runs/report-<id>.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _sum(evidence: dict, key: str) -> int:
    return sum(v.get(key, 0) for v in evidence.values() if isinstance(v, dict))


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: wasted.py <report.json>", file=sys.stderr)
        return 2

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = payload.get("results", [])
    if not results:
        print("no results")
        return 1

    rows = []
    total_actions = total_revisits = total_game_overs = 0

    for run in results:
        ev = run.get("policy_evidence") or {}
        attempts = _sum(ev, "attempts")
        revisits = _sum(ev, "revisits")
        changed = _sum(ev, "changed")
        overs = _sum(ev, "game_overs")
        decisions = run.get("policy_decisions") or {}
        mode = max(decisions.items(), key=lambda kv: kv[1])[0] if decisions else "-"
        rows.append(
            (
                run.get("game_id", "?"),
                run.get("levels_completed", 0),
                attempts,
                revisits,
                changed,
                overs,
                mode,
            )
        )
        total_actions += attempts
        total_revisits += revisits
        total_game_overs += overs

    print(f"{'game':<6}{'lvl':>4}{'acts':>7}{'revisit':>9}{'%re':>7}{'changed':>9}{'deaths':>7}  mode")
    print("-" * 78)
    for g, lvl, a, rv, ch, go, mode in sorted(rows, key=lambda r: -(r[3] / max(r[2], 1))):
        print(f"{g:<6}{lvl:>4}{a:>7}{rv:>9}{100*rv/max(a,1):>6.1f}%{ch:>9}{go:>7}  {mode}")
    print("-" * 78)
    print(f"{'TOTAL':<6}{sum(r[1] for r in rows):>4}{total_actions:>7}{total_revisits:>9}"
          f"{100*total_revisits/max(total_actions,1):>6.1f}%")
    print()
    print(f"games={len(rows)}  levels_completed={sum(r[1] for r in rows)}  "
          f"game_overs={total_game_overs}")
    print(f"mean revisit rate: {100*total_revisits/max(total_actions,1):.1f}%")

    # Czy niski odsetek powtórzeń idzie w parze z ukończonymi poziomami?
    moved = [r for r in rows if r[1] > 0]
    stuck = [r for r in rows if r[1] == 0]
    if moved and stuck:
        m = sum(r[3] for r in moved) / max(sum(r[2] for r in moved), 1)
        s = sum(r[3] for r in stuck) / max(sum(r[2] for r in stuck), 1)
        print()
        print(f"revisits: gry z >=1 poziomem {100*m:.1f}%  vs  gry na 0 poziomie {100*s:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
