"""Sweep: ile poziomów官方 25 gier da się rozwiązać BEZ ani jednego tokena LLM.

Strategia per gra:
  - branching <= 6 (gry keyboard)      -> BFS z deduplikacją stanów (optymalna liczba akcji)
  - branching >  6 (gry click, ACTION6) -> beam z heurystyką nowości (zmiana ramki)
Po ukończeniu poziomu search idzie dalej (następny poziom), aż do --max-levels albo budżetu.

Wynik: JSONL + tabela markdown. Wszystko na CPU, offline, bez arc_agi/gatewaya/Kaggle.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import multiprocessing as mp
import time
import traceback
from collections import deque
from pathlib import Path

import numpy as np
from arcengine import ActionInput, GameAction

BY_ID = {i: GameAction.from_id(i) for i in range(8)}
RESET = BY_ID[0]
MOUSE = BY_ID[6]
MOUSE_ID = 6
ACTION_INDEX = {BY_ID[i]: i for i in range(8)}   # GameAction.value to krotka -> wlasna mapa na int


def load_game(path: str, cls: str):
    spec = importlib.util.spec_from_file_location(f"arc3g_{cls.lower()}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, cls)


def frame_of(fd) -> np.ndarray:
    """FrameData.frame bywa (64,64), (k,64,64) [animacja] albo plaski (4096,)."""
    a = np.asarray(fd.frame)
    while a.ndim > 2:
        a = a[-1]
    if a.ndim == 1:
        n = int(round(a.size ** 0.5))
        a = a.reshape(n, n) if n * n == a.size else a.reshape(1, -1)
    return a.astype(np.uint8)


def key_of(fd) -> bytes:
    return (hashlib.blake2b(frame_of(fd).tobytes(), digest_size=16).digest()
            + bytes([int(fd.levels_completed) & 0xFF]))


def click_candidates(frame: np.ndarray, limit: int) -> list[tuple[int, int]]:
    """4096 współrzędnych -> ~limit punktów: centroidy + skraje spójnych obiektów (4-sąsiedztwo)."""
    h, w = frame.shape
    labels = np.zeros((h, w), dtype=np.int32)
    blobs: list[tuple[int, list[tuple[int, int]]]] = []
    nxt = 0
    for y0 in range(h):
        row = frame[y0]
        for x0 in range(w):
            color = int(row[x0])
            if color == 0 or labels[y0, x0]:
                continue
            nxt += 1
            stack = [(y0, x0)]
            pts: list[tuple[int, int]] = []
            while stack:
                y, x = stack.pop()
                if not (0 <= y < h and 0 <= x < w) or labels[y, x] or int(frame[y, x]) != color:
                    continue
                labels[y, x] = nxt
                pts.append((y, x))
                stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
            if len(pts) >= 2:
                blobs.append((len(pts), pts))
    blobs.sort(key=lambda b: -b[0])
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for _size, pts in blobs:
        ys = np.array([p[0] for p in pts]); xs = np.array([p[1] for p in pts])
        for cy, cx in ((int(ys.mean()), int(xs.mean())),
                       (int(ys.min()), int(xs[ys.argmin()])),
                       (int(ys.max()), int(xs[ys.argmax()]))):
            if (cx, cy) not in seen:
                seen.add((cx, cy)); out.append((cx, cy))
            if len(out) >= limit:
                return out
    return out


def moves_for(avail: list[int], frame: np.ndarray, click_limit: int) -> list[ActionInput]:
    out: list[ActionInput] = []
    for a in avail:
        if a == MOUSE_ID:
            for (x, y) in click_candidates(frame, click_limit):
                out.append(ActionInput(id=MOUSE, data={"x": x, "y": y}))
        elif a in BY_ID:
            out.append(ActionInput(id=BY_ID[a]))
    return out


def search_level(cls, base_levels: int, root, frame0, avail0, *, mode, cap, t_limit,
                 beam_width, click_limit, max_depth):
    """Zwraca (sekwencja|None, węzły, sekundy, liczba_stanów). Sukces = levels_completed > base."""
    seen: set[bytes] = set()
    item0 = (root, frame0, [], avail0, 0.0)
    frontier = deque([item0]) if mode == "bfs" else [item0]
    t0 = time.time(); nodes = 0
    while frontier and nodes < cap and time.time() - t0 < t_limit:
        if mode == "bfs":
            state, frame, seq, avail, _ = frontier.popleft()
        else:
            frontier.sort(key=lambda e: -e[4])
            state, frame, seq, avail, _ = frontier.pop(0)
        if len(seq) >= max_depth:
            continue
        for move in moves_for(avail, frame, click_limit):
            child = copy.deepcopy(state)
            fd = child.perform_action(move)
            nodes += 1
            if int(fd.levels_completed) > base_levels:
                return seq + [move], nodes, time.time() - t0, len(seen)
            k = key_of(fd)
            if k in seen:
                continue
            seen.add(k)
            cf = frame_of(fd)
            cavail = [int(a) for a in (fd.available_actions or avail)]
            prev = frame
            nov = float((prev != cf).sum()) if prev.shape == cf.shape else 1.0
            item = (child, cf, seq + [move], cavail, nov)
            if mode == "bfs":
                frontier.append(item)
            else:
                frontier.append(item)
                if len(frontier) > beam_width:
                    frontier.sort(key=lambda e: -e[4])
                    del frontier[beam_width:]
    return None, nodes, time.time() - t0, len(seen)


def play_game(args):
    path, cls, node_cap, sec_cap, max_levels, beam_width, click_limit = args
    out = {"game": Path(path).stem, "cls": cls, "levels": [], "error": None}
    t_start = time.time()
    try:
        G = load_game(path, cls)
        g = G()
        fd = g.perform_action(ActionInput(id=RESET))
        avail = [int(a) for a in (fd.available_actions or [])]
        mode = "bfs" if (avail and max(avail) != MOUSE_ID and len(avail) <= 6) else "beam"
        out.update({"win_levels": int(fd.win_levels), "avail": avail, "mode": mode})
        state, frame, base = g, frame_of(fd), int(fd.levels_completed)
        for lvl in range(max_levels):
            left_s = max(5.0, sec_cap - (time.time() - t_start))
            seq, nodes, el, nseen = search_level(
                G, base, state, frame, avail, mode=mode, cap=node_cap, t_limit=left_s,
                beam_width=beam_width, click_limit=click_limit, max_depth=80)
            # `base` = liczba ukonczonych poziomow PRZED ta proba, czyli numer poziomu,
            # ktory wlasnie gramy (0-based). Wczesniej bylo `base + lvl` - ale `base` samo
            # rosnie po kazdym rozwiazanym poziomie, wiec indeksy wychodzily 0,2,4,6,8...
            rec = {"level": base, "solved": seq is not None, "actions": len(seq) if seq else None,
                   "nodes": nodes, "seconds": round(el, 1), "states": nseen, "mode": mode}
            if seq:
                probe = copy.deepcopy(state)
                for m in seq[:-1]:
                    probe.perform_action(m)
                fd_last = probe.perform_action(seq[-1])
                rec["actions_after"] = int(fd_last.levels_completed)
                rec["seq"] = [({"a": 6, "x": m.data.get("x"), "y": m.data.get("y")}
                               if m.id == MOUSE else {"a": ACTION_INDEX[m.id], "name": m.id.name})
                              for m in seq]
                state, frame, base = probe, frame_of(fd_last), int(fd_last.levels_completed)
                avail = [int(a) for a in (fd_last.available_actions or avail)]
            out["levels"].append(rec)
            if not seq:
                break
        out["total_seconds"] = round(time.time() - t_start, 1)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["tb"] = traceback.format_exc()[-1200:]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games-dir", default="/home/user/arc3-scratch/games")
    ap.add_argument("--node-cap", type=int, default=2500)
    ap.add_argument("--sec-cap", type=float, default=120.0)
    ap.add_argument("--max-levels", type=int, default=3)
    ap.add_argument("--beam", type=int, default=60)
    ap.add_argument("--click-candidates", type=int, default=20)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", default="", help="lista gier po przecinku (puste = wszystkie)")
    ap.add_argument("--out", default="/home/user/arc3-scratch/sweep_results.jsonl")
    a = ap.parse_args()

    files = sorted(Path(a.games_dir).glob("*.py"))
    if a.only:
        want = {x.strip() for x in a.only.split(",")}
        files = [f for f in files if f.stem in want]
    jobs = []
    for f in files:
        txt = f.read_text(errors="replace")
        cls = None
        for line in txt.splitlines():
            if line.startswith("class ") and "(ARCBaseGame)" in line:
                cls = line.split("class ", 1)[1].split("(")[0].strip()
                break
        if not cls:
            print(f"!! {f.stem}: brak klasy ARCBaseGame")
            continue
        jobs.append((str(f), cls, a.node_cap, a.sec_cap, a.max_levels, a.beam, a.click_candidates))

    print(f"{len(jobs)} gier, workers={a.workers}, node_cap={a.node_cap}, sec_cap={a.sec_cap}s", flush=True)
    with open(a.out, "w") as fh:
        with mp.Pool(a.workers) as pool:
            for i, res in enumerate(pool.imap_unordered(play_game, jobs), 1):
                fh.write(json.dumps(res) + "\n"); fh.flush()
                solved = sum(1 for r in res["levels"] if r["solved"])
                print(f"[{i}/{len(jobs)}] {res['game']:6} mode={res.get('mode','?'):5} "
                      f"poziomy_rozwiazane={solved} akcje={[r['actions'] for r in res['levels']]} "
                      f"wezel={sum(r['nodes'] for r in res['levels'])} "
                      f"{res.get('total_seconds','?')}s {('ERR '+res['error']) if res.get('error') else ''}",
                      flush=True)
    print("ZAPISANO", a.out, flush=True)


if __name__ == "__main__":
    main()
