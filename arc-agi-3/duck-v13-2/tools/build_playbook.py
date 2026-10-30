#!/usr/bin/env python3
"""Build playbook.json for ARC3 Duck v13 (patch 0006 win-path replay).

Reads sweep2 result JSONL files (levels solved offline by BFS/beam search),
REPLAYS every recorded action sequence on a fresh instance of the real game
(arcengine, the game's own Python module) and keeps only sequences that
provably complete the level again, deterministically, from a cold start.
For every kept sequence it records the harness-style grid hash before the
first action and after every action, so the Kaggle-side replay can verify
frame-by-frame that it is still on the recorded track and bail out to the
LLM on the first mismatch.

Usage:
  python3 tools/build_playbook.py --games-dir <environment_files dir> \
      --sweep sweep2_result.jsonl [--sweep more.jsonl ...] \
      --out playbook.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from arcengine import ActionInput, GameAction


def frame_of(fd) -> np.ndarray:
    a = np.asarray(fd.frame)
    while a.ndim > 2:
        a = a[-1]
    if a.ndim == 1:
        n = int(round(a.size ** 0.5))
        a = a.reshape(n, n) if n * n == a.size else a.reshape(1, -1)
    return a.astype(np.uint8)


def grid_key(fd) -> str:
    grid = tuple(tuple(int(c) for c in row) for row in frame_of(fd))
    return hashlib.sha256(repr(grid).encode()).hexdigest()[:16]


def load_game(path: Path):
    txt = path.read_text(errors="replace")
    cls = next((l.split("class ", 1)[1].split("(")[0].strip()
                for l in txt.splitlines()
                if l.startswith("class ") and "(ARCBaseGame)" in l), None)
    if cls is None:
        raise ValueError(f"no ARCBaseGame class in {path}")
    spec = importlib.util.spec_from_file_location(f"pb_{path.stem}", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, cls)()


def to_action(entry: dict) -> ActionInput:
    action = GameAction.from_id(int(entry["a"]))
    if "x" in entry and entry.get("x") is not None:
        return ActionInput(id=action, data={"x": int(entry["x"]), "y": int(entry["y"])})
    return ActionInput(id=action, data={})


def is_game_over(fd) -> bool:
    state = getattr(fd, "state", None)
    name = getattr(state, "name", str(state)) if state is not None else ""
    return "GAME_OVER" in str(name).upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games-dir", required=True)
    ap.add_argument("--sweep", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    game_files = {p.stem: p for p in Path(args.games_dir).rglob("*.py")}

    # Collect candidate sequences: shortest per (game, level).
    cand: dict[str, dict[int, list]] = {}
    for sweep_path in args.sweep:
        for line in open(sweep_path):
            if not line.strip():
                continue
            row = json.loads(line)
            game = row.get("game")
            for lv in row.get("levels") or []:
                if lv.get("solved") and lv.get("seq"):
                    slot = cand.setdefault(game, {})
                    lvl = int(lv["level"])
                    if lvl not in slot or len(lv["seq"]) < len(slot[lvl]):
                        slot[lvl] = lv["seq"]

    playbook: dict[str, dict] = {}
    n_ok = n_fail = 0
    for game in sorted(cand):
        path = game_files.get(game)
        if path is None:
            print(f"{game}: BRAK pliku gry -> pomijam")
            continue
        try:
            eng = load_game(path)
        except Exception as exc:  # noqa: BLE001
            print(f"{game}: ładowanie gry padło: {exc!r}")
            continue
        fd = eng.perform_action(ActionInput(id=GameAction.RESET))
        levels_out: dict[str, dict] = {}
        chain_ok = True
        for lvl in sorted(cand[game]):
            seq = cand[game][lvl]
            before = int(fd.levels_completed)
            if before != lvl:
                print(f"{game} L{lvl}: łańcuch przerwany (oczekiwano poziomu {lvl}, gra na {before})")
                chain_ok = False
                break
            init_key = grid_key(fd)
            hashes: list[str] = []
            died = False
            for entry in seq:
                fd = eng.perform_action(to_action(entry))
                hashes.append(grid_key(fd))
                if is_game_over(fd):
                    died = True
                    break
            after = int(fd.levels_completed)
            if not died and after == before + 1:
                levels_out[str(lvl)] = {
                    "actions": [
                        ({"name": GameAction.from_id(int(e["a"])).name,
                          "data": ({"x": int(e["x"]), "y": int(e["y"])}
                                   if e.get("x") is not None else {})})
                        for e in seq
                    ],
                    "init": init_key,
                    "hashes": hashes,
                    "n": len(seq),
                    "src": "offline-sweep",
                }
                n_ok += 1
                print(f"{game} L{lvl}: OK ({len(seq)} akcji)")
            else:
                n_fail += 1
                print(f"{game} L{lvl}: FAIL (śmierć={died}, poziomy {before}->{after})")
                chain_ok = False
                break
        if levels_out:
            playbook[game] = {"levels": levels_out}
        if not chain_ok:
            print(f"{game}: dalsze poziomy odrzucone (łańcuch od świeżego startu przerwany)")

    out = {"version": 1, "games": playbook}
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    total_actions = sum(l["n"] for g in playbook.values() for l in g["levels"].values())
    print(f"\nZAPISANO {args.out}: {len(playbook)} gier, {n_ok} poziomów OK, "
          f"{n_fail} odrzuconych, łącznie {total_actions} akcji")
    return 0


if __name__ == "__main__":
    sys.exit(main())
