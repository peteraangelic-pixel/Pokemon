"""Run ARC-AGI-3 demo games locally (CPU, no API) and render frames.

The games are the public environment files (`<g>/<g>/<g>.py` + metadata.json).
arcengine needs Python >=3.12 on PyPI but works on 3.11:
    pip install --no-deps --ignore-requires-python arcengine && pip install pydantic numpy pillow

Usage:
    python play.py GAMES_DIR ls20 --actions "1 1 3 6:10,20" --png out.png
Action syntax: N = ACTIONN, "6:x,y" = click, "0" = RESET.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np

PALETTE = [  # ARC-AGI-3 16-colour palette (index -> RGB)
    (255, 255, 255), (204, 204, 204), (153, 153, 153), (102, 102, 102),
    (51, 51, 51), (0, 0, 0), (229, 58, 163), (255, 123, 204),
    (249, 60, 49), (30, 147, 255), (136, 216, 241), (255, 220, 0),
    (255, 133, 27), (146, 18, 49), (79, 204, 48), (163, 86, 208),
]


def load_game(games_dir: str | Path, gid: str):
    from arcengine import ARCBaseGame
    src = Path(games_dir) / gid / gid / f"{gid}.py"
    spec = importlib.util.spec_from_file_location(f"game_{gid}", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    cls = next(v for v in vars(mod).values()
               if isinstance(v, type) and issubclass(v, ARCBaseGame) and v is not ARCBaseGame)
    return cls()


def act(game, token: str):
    from arcengine import ActionInput, GameAction
    if ":" in token:
        n, xy = token.split(":")
        x, y = (int(v) for v in xy.split(","))
        return game.perform_action(ActionInput(id=GameAction[f"ACTION{n}"], data={"x": x, "y": y}))
    n = int(token)
    return game.perform_action(ActionInput(id=GameAction.RESET if n == 0 else GameAction[f"ACTION{n}"]))


def to_png(frame, path, scale=8):
    from PIL import Image
    a = np.asarray(frame, dtype=np.int64)
    rgb = np.array(PALETTE, dtype=np.uint8)[a % 16]
    Image.fromarray(rgb).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("games_dir"); ap.add_argument("game")
    ap.add_argument("--actions", default=""); ap.add_argument("--png")
    ap.add_argument("--level", type=int, help="jump to level index before acting")
    a = ap.parse_args()
    g = load_game(a.games_dir, a.game)
    fd = act(g, "0")
    if a.level is not None:
        g.set_level(a.level); fd = act(g, "0") if False else fd
    for t in a.actions.split():
        fd = act(g, t)
    frame = g.camera.render(g.current_level.get_sprites())
    print(json.dumps({"state": str(fd.state), "levels_completed": fd.levels_completed,
                      "win_levels": fd.win_levels, "available": fd.available_actions,
                      "level_index": g.level_index}))
    if a.png:
        to_png(frame, a.png)


if __name__ == "__main__":
    main()
