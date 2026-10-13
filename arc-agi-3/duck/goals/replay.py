"""Replay agent action histories from benchmark.json on local games (CPU).

Parity check (Franzen 4x25): 100/100 runs reproduce levels_completed exactly.
    python replay.py BENCH.json GAMES_DIR --check
    python replay.py BENCH.json GAMES_DIR --run 17 --png-dir out/   # stuck-level start + final frame
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from play import load_game, to_png
from arcengine import ActionInput, GameAction


def replay(run, games_dir, on_level_start=None):
    gid = run["game_id"][:4]
    g = load_game(games_dir, gid)
    fd = g.perform_action(ActionInput(id=GameAction.RESET))
    lvl = 0
    if on_level_start: on_level_start(g, lvl, 0)
    for i, h in enumerate(run["history"]):
        a = h["action"]
        fd = g.perform_action(ActionInput(id=GameAction[a["id"]], data=a.get("data") or {}))
        if fd.levels_completed != lvl:
            lvl = fd.levels_completed
            if on_level_start: on_level_start(g, lvl, i + 1)
    return g, fd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench"); ap.add_argument("games_dir")
    ap.add_argument("--check", action="store_true"); ap.add_argument("--run", type=int)
    ap.add_argument("--png-dir", default=".")
    a = ap.parse_args()
    runs = json.load(open(a.bench))["game_runs"]
    if a.check:
        bad = 0
        for r in runs:
            _, fd = replay(r, a.games_dir)
            bad += fd.levels_completed != r["levels_completed"]
        print(f"parity: {len(runs) - bad}/{len(runs)}")
        return
    r = runs[a.run]; out = Path(a.png_dir); out.mkdir(parents=True, exist_ok=True)
    snaps = {}
    def cb(g, lvl, i):
        snaps[lvl] = (i, g.camera.render(g.current_level.get_sprites()))
    g, fd = replay(r, a.games_dir, cb)
    k = fd.levels_completed
    i, fr = snaps[k]
    tag = f"{r['game_id'][:4]}_run{a.run}"
    to_png(fr, out / f"{tag}_L{k+1}_start.png")
    to_png(g.camera.render(g.current_level.get_sprites()), out / f"{tag}_L{k+1}_final.png")
    print(json.dumps({"game": r["game_id"], "levels_completed": k, "stuck_level": k + 1,
                      "actions_on_stuck_level": len(r["history"]) - i, "state": str(fd.state)}))


if __name__ == "__main__":
    main()
