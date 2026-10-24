"""ARC-AGI-3: deterministyczne wyszukiwanie BEZ tokenów LLM (dowód koncepcji).

Dlaczego to działa: `arcengine.perform_action()` zwraca `FrameData` z polami
    frame (1,64,64) | state | levels_completed | win_levels | available_actions
Sygnał sukcesu, legalne akcje i pełna plansza są dostępne za darmo — walutą
w konkursie są tokeny GENEROWANE przez model, a wyszukiwanie ich nie zużywa.

Zmierzone (sandbox Arena, 2 rdzenie, 2026-10-24):
    ls20 poziom 0: czysty BFS, 13 akcji (baseline 22 -> poziom warty 115 pkt, cap),
    1801 węzłów, 48.5 s, 0 tokenów LLM.

Koszty silnika (pomiar):
    perform_action 4.36 ms | copy.deepcopy(game) 16.9 ms | level_reset() 1.82 ms
    -> snapshot deepcopy zamiast odtwarzania sekwencji opłaca się od głębokości ~4.

Użycie:
    pip install --no-deps --ignore-requires-python arcengine numpy   # py3.11 działa mimo wymogu 3.12
    python3 arc3_search.py <sciezka_do_gry.py> <NazwaKlasy> [--mode bfs|beam] [--cap 4000]
                           [--beam 400] [--click-candidates 24] [--time 120]

Gry "click" (available_actions == [6]): przestrzeń to 4096 współrzędnych, więc BFS
odpada. Kandydaci są wtedy generowani z prostej segmentacji (spójne obszary tego
samego koloru -> centroid + skraje), tak jak robi to harness w
inference/utils/segmentation.py (jego port Rust leży w repo niepodpięty).

Wniosek dla harnessa: sandbox `python` udostępniany modelowi daje wyłącznie
current_frame/history i NIE może stepować silnika — więc taki search musi siedzieć
w harnessie (patch), nie w promptcie.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import time
from collections import deque

import numpy as np
from arcengine import ActionInput, GameAction

# GameAction.value to krotka (id, typ), więc GameAction(1) rzuca ValueError -> from_id()
BY_ID = {i: GameAction.from_id(i) for i in range(8)}
RESET = BY_ID[0]
MOUSE = BY_ID[6]
MOUSE_ID = 6


def load_game(path: str, cls: str):
    """Wczytuje plik gry z environment_files (działa offline, bez arc_agi/gatewaya)."""
    spec = importlib.util.spec_from_file_location("arc3_game_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, cls)


def frame_of(fd) -> np.ndarray:
    """Ostatnia ramka (silnik potrafi zwrócić kilka klatek animacji: shape (k,64,64))."""
    a = np.asarray(fd.frame, dtype=np.uint8)
    while a.ndim > 2:
        a = a[-1]
    return a


def key_of(fd) -> bytes:
    """Sygnatura stanu do deduplikacji: ramka + postęp (poziom może się zmienić przy tej samej ramce)."""
    return hashlib.blake2b(frame_of(fd).tobytes(), digest_size=16).digest() + bytes([int(fd.levels_completed)])


def click_candidates(frame: np.ndarray, limit: int) -> list[tuple[int, int]]:
    """Zawęża 4096 współrzędnych do ~limit sensownych punktów kliknięcia.

    Prosta segmentacja 4-spójna po kolorze; dla każdego obiektu: centroid i dwa skraje.
    Kolejność: od największego obiektu (najczęściej interaktywny).
    """
    h, w = frame.shape
    labels = np.zeros((h, w), dtype=np.int32)
    blobs: list[tuple[int, list[tuple[int, int]]]] = []
    nxt = 0
    for y0 in range(h):
        for x0 in range(w):
            color = int(frame[y0, x0])
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
    for _size, pts in blobs:
        ys = np.array([p[0] for p in pts])
        xs = np.array([p[1] for p in pts])
        for (cy, cx) in ((int(ys.mean()), int(xs.mean())),
                         (int(ys[ys.argmin()]), int(xs[ys.argmin()])),
                         (int(ys[ys.argmax()]), int(xs[ys.argmax()]))):
            if (cx, cy) not in out:
                out.append((cx, cy))  # ComplexAction chce (x, y)
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


def novelty(fd, prev: np.ndarray | None) -> float:
    """Heurystyka dla beam: ile pikseli zmieniło się względem ramki rodzica."""
    f = frame_of(fd)
    if prev is None or prev.shape != f.shape:
        return 1.0
    return float((prev != f).sum())


def search(cls, *, mode="bfs", cap=4000, beam=400, t_limit=120.0, click_limit=24,
             max_depth=60, verbose=True):
    """Zwraca (sekwencja | None, węzły, sekundy, info). Sukces = wzrost levels_completed."""
    root = cls()
    fd0 = root.perform_action(ActionInput(id=RESET))
    frame0 = frame_of(fd0)
    base_levels = int(fd0.levels_completed)
    info = {"base_levels": base_levels, "win_levels": int(fd0.win_levels),
            "avail": [int(a) for a in (fd0.available_actions or [])], "seen": 0}
    seen = {key_of(fd0)}
    # element frontu: (stan_gry, ramka, sekwencja, dostępne_akcje, heurystyka)
    item0 = (root, frame0, [], info["avail"], 0.0)
    frontier = deque([item0]) if mode == "bfs" else [item0]
    t0 = time.time()
    nodes = 0

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
                el = time.time() - t0
                out = seq + [move]
                info["seen"] = len(seen)
                if verbose:
                    print(f"  *** POZIOM UKOŃCZONY: {len(out)} akcji, {nodes} węzłów, {el:.1f}s",
                          flush=True)
                return out, nodes, el, info
            k = key_of(fd)
            if k in seen:
                continue
            seen.add(k)
            child_frame = frame_of(fd)
            child_avail = [int(a) for a in (fd.available_actions or avail)]
            item = (child, child_frame, seq + [move], child_avail, novelty(fd, frame))
            if mode == "bfs":
                frontier.append(item)
            else:
                frontier.append(item)
                if len(frontier) > beam:
                    frontier.sort(key=lambda e: -e[4])
                    del frontier[beam:]
        if verbose and nodes % 500 < 8:
            print(f"  ... {nodes} węzłów, {len(seen)} stanów, głębokość {len(seq)}, "
                  f"{time.time() - t0:.0f}s", flush=True)
    info["seen"] = len(seen)
    return None, nodes, time.time() - t0, info


def label(move: ActionInput) -> str:
    if move.id == MOUSE:
        return f"MOUSE({move.data.get('x')},{move.data.get('y')})"
    return move.id.name


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game", help="ścieżka do <g>.py z environment_files")
    ap.add_argument("cls", help="nazwa klasy gry, np. Ls20")
    ap.add_argument("--mode", default="bfs", choices=["bfs", "beam"])
    ap.add_argument("--cap", type=int, default=4000, help="limit węzłów")
    ap.add_argument("--beam", type=int, default=400, help="szerokość wiązki (mode=beam)")
    ap.add_argument("--click-candidates", type=int, default=24, help="ile punktów kliknięcia na ramkę")
    ap.add_argument("--time", type=float, default=120.0, help="limit sekund")
    a = ap.parse_args()

    G = load_game(a.game, a.cls)
    probe = G()
    fd = probe.perform_action(ActionInput(id=RESET))
    print(f"gra={fd.game_id} win_levels={fd.win_levels} dostępne_akcje={list(fd.available_actions)} "
          f"plansza={frame_of(fd).shape}")
    print(f"{a.mode.upper()} (snapshoty deepcopy, cap={a.cap} węzłów, limit {a.time:.0f}s):")
    seq, nodes, el, info = search(G, mode=a.mode, cap=a.cap, beam=a.beam, t_limit=a.time,
                                  click_limit=a.click_candidates)
    print(f"odrębnych stanów: {info['seen']}")
    if seq:
        print(f"WYNIK: SUKCES — {len(seq)} akcji, {nodes} węzłów, {el:.1f}s, "
              f"{nodes / max(el, 1e-9):.0f} węzłów/s, 0 tokenów LLM")
        print("sekwencja:", [label(m) for m in seq])
    else:
        print(f"WYNIK: brak rozwiązania w budżecie ({nodes} węzłów, {el:.1f}s, "
              f"{nodes / max(el, 1e-9):.0f} węzłów/s)")
        print("→ potrzebna heurystyka celowa (segmentacja → obiekty docelowe) albo LLM jako doradca")


if __name__ == "__main__":
    main()
