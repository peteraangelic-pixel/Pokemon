"""Verify the duck-v8 replay premise against the real ARC-AGI-3 engine — locally.

The v8 package (branch `arena/a450b00f-pokemon`, commit 5f397df, `arc-agi-3/duck-v8/`)
ships a record/replay layer whose whole value rests on one assumption:

    after a death, the level is auto-reset to its initial state, and replaying the
    recorded action sequence re-clears it without any model calls.

That assumption has never been smoke-tested. This script tests it on the real
engine, at zero GPU cost, by answering four questions:

  Q1  Does `GameAction.RESET` (what the harness issues on death) restore the
      level to its initial frame?
  Q2  Does it restore the level counter to the state before the solve, or keep
      completed levels?
  Q3  Does replaying the recorded actions re-clear the level?
  Q4  How many model decisions does replay save on that re-clear?

The last one is the point: decisions per minute (~1.2) is the bottleneck, and a
replayed level costs zero decisions.

Usage:
    python local/test_replay_premise.py
    python local/test_replay_premise.py --solutions local/solutions.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402


def grid_hash(grid) -> str:
    return hashlib.sha1(grid.tobytes()).hexdigest()[:16]


def decode(enc):
    """`[id]` or `[6, x, y]` -> (action_id, data)."""
    a = int(enc[0])
    data = {"x": int(enc[1]), "y": int(enc[2])} if a == 6 and len(enc) > 2 else None
    return a, data


def verify_one(info, game: str, paths: list[list[list[int]]]) -> dict:
    """Solve -> RESET -> replay, recording hashes at each stage."""
    from arcengine import GameAction

    flat = [enc for p in paths for enc in p]

    # --- 1. fresh game, record the initial frame -------------------------
    w = engine.make_wrapper(info, seed=0)
    obs = engine.to_obs(w.reset())
    start_hash = grid_hash(obs.grid)
    start_levels = obs.levels

    # --- 2. play the known solution, recording step hashes ---------------
    step_hashes, levels_after = [], []
    for enc in flat:
        a, data = decode(enc)
        nf = w.step(engine.action_for(a), data=data)
        if nf is None:
            return {"game": game, "ok": False, "stage": "solve", "error": "step returned None"}
        obs = engine.to_obs(nf, obs.grid)
        step_hashes.append(grid_hash(obs.grid))
        levels_after.append(obs.levels)
    solved_levels = obs.levels
    solved_hash = grid_hash(obs.grid)
    solved_ok = solved_levels > start_levels

    # --- 3. Q1/Q2: issue RESET exactly like the harness does on death ----
    nf = w.step(GameAction.RESET)
    if nf is None:
        return {"game": game, "ok": False, "stage": "reset", "error": "RESET returned None"}
    after_reset = engine.to_obs(nf, obs.grid)
    reset_hash = grid_hash(after_reset.grid)
    q1_restores_frame = reset_hash == start_hash
    q2_keeps_levels = after_reset.levels >= solved_levels

    # --- 4. Q3: replay the same actions, verify every frame --------------
    replay_ok = True
    mismatch_at = None
    for i, enc in enumerate(flat):
        a, data = decode(enc)
        nf = w.step(engine.action_for(a), data=data)
        if nf is None:
            replay_ok, mismatch_at = False, i
            break
        after_reset = engine.to_obs(nf, after_reset.grid)
        if grid_hash(after_reset.grid) != step_hashes[i]:
            replay_ok, mismatch_at = False, i
            break
    replay_levels = after_reset.levels
    q3_replay_reclears = replay_ok and replay_levels == solved_levels

    return {
        "game": game,
        "ok": bool(solved_ok and q3_replay_reclears),
        "actions_in_solution": len(flat),
        "levels_before": start_levels,
        "levels_after_solve": solved_levels,
        "levels_after_reset": after_reset.levels if not q2_keeps_levels else solved_levels,
        "q1_reset_restores_initial_frame": q1_restores_frame,
        "q2_reset_keeps_completed_levels": q2_keeps_levels,
        "q3_replay_reclears_level": q3_replay_reclears,
        "q4_model_decisions_saved": len(flat) if q3_replay_reclears else 0,
        "mismatch_at_action": mismatch_at,
        "solved_hash": solved_hash,
        "start_hash": start_hash,
        "reset_hash": reset_hash,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify the v8 replay premise on the real engine")
    ap.add_argument("--solutions", default=str(ROOT / "local" / "solutions.json"))
    ap.add_argument("--games", default=None, help="comma list; default = every solved game")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    doc = json.loads(Path(args.solutions).read_text())
    sols = doc.get("solutions", doc)
    if args.games:
        keep = {g.strip() for g in args.games.split(",")}
        sols = {g: p for g, p in sols.items() if g in keep}

    games = engine.discover_games()
    print(f"silnik: {len(games)} gier | testuje {len(sols)} rozwiazan\n")

    results = []
    for game, paths in sorted(sols.items()):
        if game not in games:
            print(f"{game:6} POMINIETE (brak gry)")
            continue
        r = verify_one(games[game], game, paths)
        results.append(r)
        if not r.get("ok"):
            print(f"{game:6} FAIL  {r}")
            continue
        print(f"{game:6} OK   {r['actions_in_solution']:2} akcji | "
              f"poziomy {r['levels_before']}->{r['levels_after_solve']} | "
              f"Q1 reset=start: {r['q1_reset_restores_initial_frame']} | "
              f"Q2 zachowuje poziomy: {r['q2_reset_keeps_completed_levels']} | "
              f"Q3 replay: {r['q3_replay_reclears_level']}")

    ok = [r for r in results if r.get("ok")]
    print("\n" + "=" * 74)
    print(f"Q1 reset przywraca klatke startowa : "
          f"{sum(r['q1_reset_restores_initial_frame'] for r in ok)}/{len(ok)}")
    print(f"Q2 reset ZACHOWUJE ukonczone poziomy: "
          f"{sum(r['q2_reset_keeps_completed_levels'] for r in ok)}/{len(ok)}  "
          f"<-- jesli 0, po smierci gra leci od poziomu 1")
    print(f"Q3 replay odtwarza poziom          : "
          f"{sum(r['q3_replay_reclears_level'] for r in ok)}/{len(ok)}")
    saved = sum(r["q4_model_decisions_saved"] for r in ok)
    print(f"Q4 decyzje modelu zaoszczedzone    : {saved} na {len(ok)} grach")

    verdict = "POTWIERDZONA" if ok and all(
        r["q3_replay_reclears_level"] for r in ok) else "NIEPOTWIERDZONA"
    print(f"\nPRZESLANKA v8: {verdict}")
    if ok and not any(r["q2_reset_keeps_completed_levels"] for r in ok):
        print("Uwaga: RESET cofa licznik poziomow do zera, wiec po kazdej smierci agent")
        print("odtwarza CALA dotychczasowa sciezke — replay oszczedza wlasnie te decyzje.")
    print("=" * 74)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(
            {"verdict": verdict, "results": results,
             "engine": "arc-agi 0.9.9 / arcengine 0.9.3"}, indent=2) + "\n")
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
