"""Offline solver: search for action sequences that clear levels, once, on CPU.

Measured on the reference box:
    step: 0.10 ms      deepcopy(game): 3-14 ms (game dependent)      reset: ~17 ms

Because the engine is deterministic and its state can be deep-copied, we can run
a beam search over action sequences and store the winning path. A found path is
a *guaranteed* level completion, independent of the LLM: replay it first, then
hand control back to the agent.

Usage:
    python local/solver.py --games sp80,m0r0,r11l --budget 4000 --depth 40
    python local/solver.py --games all --budget 20000 --workers 16 --out local/solutions.json
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402
from rust_bridge import RustBridge  # noqa: E402

_W: dict = {}


def _init(games_dir: str) -> None:
    _W["games"] = engine.discover_games(Path(games_dir))
    _W["bridge"] = RustBridge()  # resolved once per worker; falls back to python


def _step(game, action_id: int, data=None):
    from arcengine import ActionInput

    if action_id == 6 and not data:
        data = {"x": 0, "y": 0}
    return game.perform_action(
        ActionInput(id=engine.action_for(action_id), data=data or {}), raw=True)


def _click_candidates(obs, rng: random.Random, limit: int = 12,
                      strategy: str = "objects",
                      bridge: RustBridge | None = None) -> list[tuple[int, int]]:
    """Proposals for ACTION6.

    ``objects`` (default) asks the segmentation kernel for component bbox centres
    and contour pixels — one click per object instead of a dart throw. That is
    the difference between 4 dead nodes and a solved level on click-only games
    (vc33). ``naive`` keeps the old random non-background sampling as a control.
    """
    g = obs.grid
    if strategy == "objects":
        try:
            b = bridge or RustBridge()
            cands = b.click_candidates(g, limit=limit)
            if cands:
                return cands
        except Exception:
            pass  # fall through to naive

    bg = int(np.bincount(g.ravel()).argmax())
    mask = g != bg
    if not mask.any():
        return [(rng.randrange(g.shape[1]), rng.randrange(g.shape[0])) for _ in range(limit)]
    ys, xs = np.nonzero(mask)
    idx = rng.sample(range(len(xs)), min(limit, len(xs)))
    return [(int(xs[i]), int(ys[i])) for i in idx]


def _encode(action_id: int, data) -> list[int]:
    if action_id == 6:
        return [6, int(data["x"]), int(data["y"])]
    return [action_id]


def solve_game(
    info,
    name: str,
    node_budget: int = 4000,
    max_depth: int = 40,
    beam: int = 1,
    click_limit: int = 12,
    seed: int = 0,
    max_levels: int = 3,
    clicks: str = "objects",
    bridge: RustBridge | None = None,
) -> dict:
    """Search for level-clearing paths. Returns {'game', 'paths', 'nodes', 'ms'}.

    `paths` is a list of action paths, one per cleared level, meant to be
    replayed in order from a fresh reset.
    """
    rng = random.Random(seed)
    t0 = time.perf_counter()
    w = engine.make_wrapper(info, seed=0)
    frame = w.reset()
    base_game = w._game
    obs = engine.to_obs(frame)
    win_levels = int(getattr(frame, "win_levels", 0) or 0)

    paths: list[list[list[int]]] = []
    nodes = 0
    game_ctx = base_game  # game object positioned at the start of current level

    for _level in range(max_levels):
        start_levels = obs.levels
        seen = {(obs.levels, obs.grid.tobytes())}
        frontier = [(copy.deepcopy(game_ctx), [], obs)]
        found = None
        while frontier and not found and nodes < node_budget:
            nxt = []
            for game, path, cur in frontier:
                if cur.available and 6 in cur.available and click_limit:
                    proposals: list[tuple[int, dict | None]] = [
                        (a, None) for a in cur.available if a != 6
                    ]
                    for (cx, cy) in _click_candidates(cur, rng, click_limit,
                                                      clicks, bridge):
                        proposals.append((6, {"x": cx, "y": cy}))
                else:
                    proposals = [(a, None) for a in cur.available]

                for aid, data in proposals:
                    if nodes >= node_budget:
                        break
                    try:
                        g2 = copy.deepcopy(game)
                        f2 = _step(g2, aid, data)
                    except Exception:
                        continue
                    nodes += 1
                    o = engine.to_obs(f2, cur.grid)
                    if o.levels > start_levels or o.state == "WIN":
                        found = (path + [_encode(aid, data)], o, g2)
                        break
                    key = (o.levels, o.grid.tobytes())
                    if key in seen:
                        continue
                    seen.add(key)
                    nxt.append((g2, path + [_encode(aid, data)], o))
                if found:
                    break
            if not found:
                if beam > 0:
                    nxt.sort(key=lambda t: -int(np.count_nonzero(t[2].grid)))
                    nxt = nxt[: max(1, beam)]
                frontier = nxt
        if not found:
            break
        path, obs, game_ctx = found
        paths.append(path)
        if obs.state == "WIN" or obs.levels >= win_levels:
            break

    return {
        "game": name,
        "clicks": clicks,
        "win_levels": win_levels,
        "levels_found": len(paths),
        "paths": paths,
        "nodes": nodes,
        "ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def replay(info, encoded_paths: list[list[list[int]]]) -> dict:
    """Verify a stored solution: replay it and report levels reached."""
    w = engine.make_wrapper(info, seed=0)
    frame = w.reset()
    steps = 0
    levels0 = int(getattr(frame, "levels_completed", 0) or 0)
    for path in encoded_paths:
        for enc in path:
            aid = enc[0]
            data = {"x": enc[1], "y": enc[2]} if aid == 6 and len(enc) > 2 else None
            f = w.step(engine.action_for(aid), data=data)
            if f is None:
                break
            steps += 1
    lv = int(getattr(f, "levels_completed", 0) or 0) if f is not None else levels0
    state = str(getattr(getattr(f, "state", None), "value", "")).upper()
    return {"levels": lv, "steps": steps, "state": state,
            "win_levels": int(getattr(f, "win_levels", 0) or 0)}


def _task(t: dict) -> dict:
    info = _W["games"].get(t["game"])
    if info is None:
        return {"game": t["game"], "error": "unknown game"}
    return solve_game(info, t["game"], node_budget=t["budget"], max_depth=t["depth"],
                      beam=t["beam"], click_limit=t["click_limit"], seed=t["seed"],
                      clicks=t["clicks"], bridge=_W.get("bridge"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline level solver (CPU)")
    ap.add_argument("--games", default="all")
    ap.add_argument("--budget", type=int, default=4000, help="nodes per game")
    ap.add_argument("--depth", type=int, default=40)
    ap.add_argument("--beam", type=int, default=0, help="0 = keep all frontier nodes (BFS)")
    ap.add_argument("--click-limit", type=int, default=8)
    ap.add_argument("--max-levels", type=int, default=3)
    ap.add_argument("--clicks", default="objects", choices=["objects", "naive"],
                    help="ACTION6 proposal strategy (objects = segmentation kernel)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="local/solutions.json")
    args = ap.parse_args()

    games = (sorted(engine.discover_games().keys())
             if args.games == "all" else [g.strip() for g in args.games.split(",")])

    tasks = [{"game": g, "budget": args.budget, "depth": args.depth,
              "beam": args.beam, "click_limit": args.click_limit, "seed": i,
              "clicks": args.clicks}
             for i, g in enumerate(games)]

    t0 = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init,
                             initargs=(str(engine.GAMES_DIR),)) as ex:
        for r in ex.map(_task, tasks, chunksize=1):
            results.append(r)
            print(f"{r['game']:6} levels={r.get('levels_found', 0)}/{r.get('win_levels', '?')} "
                  f"nodes={r.get('nodes', 0)} {r.get('ms', 0):.0f}ms "
                  f"paths={r.get('paths', [])[:2]}")
    wall = time.perf_counter() - t0

    solved = [r for r in results if r.get("levels_found")]
    total_levels = sum(r.get("levels_found", 0) for r in results)
    print("-" * 70)
    print(f"{len(solved)}/{len(results)} games with >=1 solved level, "
          f"{total_levels} levels total, {wall:.1f}s on {args.workers} workers")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "budget": args.budget, "depth": args.depth, "beam": args.beam,
        "wall_s": round(wall, 1),
        "solutions": {r["game"]: r["paths"] for r in results if r.get("levels_found")},
        "detail": results,
    }, indent=2) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
