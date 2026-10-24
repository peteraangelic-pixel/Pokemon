"""sweep2 - przeszukiwanie z KALIBRACJĄ ruchów (poprawka sweep.py).

Dlaczego ten plik istnieje (pomiar, nie domysł): skan wszystkich 4096 współrzędnych kliknięcia
na trzech grach pokazał, że generator ruchów w sweep.py był dla części gier ślepy:

  ft09  available_actions=[6]; moja segmentacja dawała 28 kandydatów i ŻADEN nie zmieniał
        ramki. Prawda: responsywnych jest 288 współrzędnych (7%), wszystkie w zwartym
        obszarze x∈[36,57] y∈[36,57] i wszystkie zmieniają DOKŁADNIE 38 pikseli
        -> to jeden przycisk. Efektywne rozgałęzienie ≈ 1, a search widział 28 martwych ruchów.
  sc25  available_actions=[1,2,3,4,6]; 0 z 4096 klików cokolwiek zmienia -> gra się
        klawiaturą, a beam (wybrany z powodu obecności ACTION6) marnował budżet na 28 klikach.
  tn36  responsywne są WSZYSTKIE 4096 współrzędne, ale zmieniają 1-4 piksele (mediana 1)
        -> to kursor, nie zmiana stanu; heurystyka "liczba zmienionych pikseli" jest bezużyteczna.

Trzy poprawki:
  1. KALIBRACJA KLIKÓW: siatka prób (domyślnie co 4 px = 256 prób, ~0.5 s) przez
     `level_reset()` (1.82 ms) zamiast deepcopy (16.9 ms). Responsywne próby grupuję w
     spójne obszary i biorę po jednym reprezentancie -> dla ft09 to 1 przycisk zamiast 0.
  2. PRUNING RUCHÓW: każdy ruch (klawiatura też) testowany raz; te, które nie zmieniają
     ramki, wypadają z generatora (sc25: 32 -> 4).
  3. TRYB PO EFEKTYWNYM ROZGAŁĘZIENIU, nie po obecności ACTION6: <= bfs_branch -> BFS
     (wyczerpujący, optymalna liczba akcji), inaczej beam.

Dla tn36 (i gier, gdzie klik zmienia 1-4 px) sama kalibracja nie wystarczy - tam potrzebna
jest inna heurystyka niż nowość ramki. Ten plik to uczciwie raportuje (`signal_quality`).
"""
from __future__ import annotations

import argparse
import collections
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
ACTION_INDEX = {BY_ID[i]: i for i in range(8)}   # GameAction.value to krotka -> własna mapa


def load_game(path: str, cls: str):
    spec = importlib.util.spec_from_file_location(f"arc3s2_{cls.lower()}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, cls)()


def frame_of(fd) -> np.ndarray:
    """FrameData.frame bywa (64,64), (k,64,64) [animacja] albo płaski (4096,)."""
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


def blob_candidates(frame: np.ndarray, limit: int) -> list[tuple[int, int]]:
    """Klasyczna segmentacja 4-spójna: centroidy + skraje obiektów (jak w sweep.py)."""
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


def calibrate_clicks(game, base_frame: np.ndarray, step: int, t_limit: float, max_reps: int = 12):
    """Siatka prób -> grupowanie PO EFEKCIE (hash ramki), nie po położeniu.

    Używa `level_reset()` (1.82 ms) zamiast deepcopy (16.9 ms), więc 256 prób to ~0.5 s.

    Dlaczego po efekcie: ft09 ma 8 przycisków w obszarze x,y in [36,57] (288 responsywnych
    współrzędnych przy kroku 1). Grupowanie przestrzenne sklejało je w JEDEN obszar i search
    dostawał rozgałęzienie 1 zamiast 8 - a to różne przyciski o różnych skutkach. Klucz
    "responsywna współrzędna -> hash ramki po kliku" daje dokładnie tyle reprezentantów,
    ile jest RÓŻNYCH efektów, i każdy z nich jest prawdziwą, zmierzoną współrzędną.

    Zwraca (reprezentanci, liczba_responsywnych, medianowa_zmiana_pikseli, liczba_efektów).
    """
    h, w = base_frame.shape
    responsive: list[tuple[int, int, int]] = []
    effects: dict[bytes, tuple[int, int]] = {}
    t0 = time.time()
    for y in range(0, h, step):
        if time.time() - t0 > t_limit:
            break
        for x in range(0, w, step):
            if time.time() - t0 > t_limit:
                break
            game.level_reset()
            fd = game.perform_action(ActionInput(id=MOUSE, data={"x": x, "y": y}))
            f = frame_of(fd)
            d = int((f != base_frame).sum())
            if d > 0:
                responsive.append((x, y, d))
                k = hashlib.blake2b(f.tobytes(), digest_size=16).digest()
                effects.setdefault(k, (x, y))
    game.level_reset()
    if not responsive:
        return [], 0, 0.0, 0
    reps = list(effects.values())[:max_reps]
    deltas = [d for _, _, d in responsive]
    return reps, len(responsive), float(np.median(deltas)), len(effects)


def prune_moves(game, base_frame: np.ndarray, moves: list[ActionInput],
                allow_noop_moves: bool = True) -> list[ActionInput]:
    """Wyrzuca ruchy, które nie zmieniają ramki (mierzone, nie zgadywane).

    UWAGA - dwie pułapki pomiarowe:
      * porównanie z base_frame sprzed kalibracji bywa nieaktualne (stan mógł się przesunąć),
        dlatego przy braku trafień powtarzamy pomiar względem świeżej ramki po level_reset,
      * pruning NIGDY nie może zwrócić pustej listy: są gry, w których legalny ruch nie
        zmienia ramki od razu (sc25: 0 z 4096 klików zmieniało piksele, choć klik jest
        poprawny - efekt widać dopiero po kolejnej akcji). Pusty zestaw = martwy search.
    """
    out = []
    for m in moves:
        game.level_reset()
        fd = game.perform_action(m)
        if int((frame_of(fd) != base_frame).sum()) > 0:
            out.append(m)
    game.level_reset()
    if out or not allow_noop_moves:
        return out
    return list(moves)


def build_moves(game, frame: np.ndarray, avail: list[int], args, calib_reps) -> list[ActionInput]:
    out: list[ActionInput] = []
    clicks: list[tuple[int, int]] = []
    if MOUSE_ID in avail:
        clicks = list(calib_reps) + [c for c in blob_candidates(frame, args.click_candidates)
                                     if c not in calib_reps]
        clicks = clicks[:args.max_clicks]
    for (x, y) in clicks:
        out.append(ActionInput(id=MOUSE, data={"x": x, "y": y}))
    for a in avail:
        if a != MOUSE_ID and a in BY_ID:
            out.append(ActionInput(id=BY_ID[a]))
    return out


def search_level(game, base_levels, root, frame0, moves0, *, mode, cap, t_limit,
                 beam_width, max_depth):
    seen: set[bytes] = set()
    frontier = deque([(root, frame0, [], moves0, 0.0)]) if mode == "bfs" else [(root, frame0, [], moves0, 0.0)]
    t0 = time.time(); nodes = 0
    while frontier and nodes < cap and time.time() - t0 < t_limit:
        if mode == "bfs":
            state, frame, seq, moves, _ = frontier.popleft()
        else:
            frontier.sort(key=lambda e: -e[4])
            state, frame, seq, moves, _ = frontier.pop(0)
        if len(seq) >= max_depth:
            continue
        for move in moves:
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
            nov = float((frame != cf).sum()) if frame.shape == cf.shape else 1.0
            item = (child, cf, seq + [move], moves, nov)
            if mode == "bfs":
                frontier.append(item)
            else:
                frontier.append(item)
                if len(frontier) > beam_width:
                    frontier.sort(key=lambda e: -e[4])
                    del frontier[beam_width:]
    return None, nodes, time.time() - t0, len(seen)


def play_game(a):
    path, cls, args = a[0], a[1], a[2]
    out = {"game": Path(path).stem, "cls": cls, "levels": [], "error": None}
    t_start = time.time()
    try:
        game = load_game(path, cls)
        fd = game.perform_action(ActionInput(id=RESET))
        avail = [int(x) for x in (fd.available_actions or [])]
        frame = frame_of(fd)
        out.update({"win_levels": int(fd.win_levels), "avail": avail})

        reps, n_resp, med_delta, n_eff = calibrate_clicks(
            game, frame, args.calib_step, args.calib_time, args.max_clicks) \
            if MOUSE_ID in avail else ([], 0, 0.0, 0)
        moves_raw = build_moves(game, frame, avail, args, reps)
        moves = prune_moves(game, frame, moves_raw)
        branch = len(moves)
        pruned_all = bool(moves_raw) and len(moves) == len(moves_raw) and n_resp == 0
        mode = "bfs" if branch <= args.bfs_branch else "beam"
        # jakość sygnału: czy nowość ramki w ogóle coś rozróżnia (tn36: mediana 1 px = kursor)
        out.update({"calib_responsive": n_resp, "calib_distinct_effects": n_eff,
                    "calib_median_delta": med_delta,
                    "click_reps": len(reps), "effective_branch": branch, "mode": mode,
                    "moves_raw": len(moves_raw), "pruned_fell_back": pruned_all,
                    "signal_quality": ("dead_clicks" if MOUSE_ID in avail and n_resp == 0 else
                                       "cursor_only" if 0 < med_delta <= 4 else "ok")})
        if branch == 0:
            out["error"] = "brak efektywnych ruchów po kalibracji"
            return out

        state, base = game, int(fd.levels_completed)
        for lvl in range(args.max_levels):
            left_s = max(5.0, args.sec_cap - (time.time() - t_start))
            seq, nodes, el, nseen = search_level(
                state, base, state, frame, moves, mode=mode, cap=args.node_cap,
                t_limit=left_s, beam_width=args.beam, max_depth=args.max_depth)
            rec = {"level": base, "solved": seq is not None,
                   "actions": len(seq) if seq else None, "nodes": nodes,
                   "seconds": round(el, 1), "states": nseen, "mode": mode}
            if seq:
                probe = copy.deepcopy(state)
                for m in seq[:-1]:
                    probe.perform_action(m)
                fd_last = probe.perform_action(seq[-1])
                rec["seq"] = [({"a": MOUSE_ID, "x": m.data.get("x"), "y": m.data.get("y")}
                               if m.id == MOUSE else {"a": ACTION_INDEX[m.id], "name": m.id.name})
                              for m in seq]
                state, frame, base = probe, frame_of(fd_last), int(fd_last.levels_completed)
                avail = [int(x) for x in (fd_last.available_actions or avail)]
                reps, n_resp, med, n_eff = calibrate_clicks(
                    state, frame, args.calib_step, args.calib_time, args.max_clicks) \
                    if MOUSE_ID in avail else ([], 0, 0.0, 0)
                moves = prune_moves(state, frame, build_moves(state, frame, avail, args, reps))
                if not moves:
                    out["levels"].append(rec); break
            out["levels"].append(rec)
            if not seq:
                break
        out["total_seconds"] = round(time.time() - t_start, 1)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["tb"] = traceback.format_exc()[-1200:]
    return out


class Args:  # przenoszone do workera przez pickle
    def __init__(self, **kw): self.__dict__.update(kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games-dir", default="/home/user/arc3-scratch/games")
    ap.add_argument("--node-cap", type=int, default=12000)
    ap.add_argument("--sec-cap", type=float, default=300.0)
    ap.add_argument("--max-levels", type=int, default=6)
    ap.add_argument("--max-depth", type=int, default=80)
    ap.add_argument("--beam", type=int, default=120)
    ap.add_argument("--click-candidates", type=int, default=28)
    ap.add_argument("--max-clicks", type=int, default=40)
    ap.add_argument("--bfs-branch", type=int, default=8, help="efektywne rozgałęzienie <= tego -> BFS")
    ap.add_argument("--calib-step", type=int, default=4, help="siatka prób kliku (px)")
    ap.add_argument("--calib-time", type=float, default=8.0, help="limit czasu kalibracji (s)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="/home/user/arc3-scratch/sweep2_results.jsonl")
    p = ap.parse_args()

    files = sorted(Path(p.games_dir).glob("*.py"))
    if p.only:
        want = {x.strip() for x in p.only.split(",")}
        files = [f for f in files if f.stem in want]
    args = Args(**{k: v for k, v in vars(p).items() if k not in ("only", "out", "workers", "games_dir")})
    jobs = []
    for f in files:
        txt = f.read_text(errors="replace")
        cls = next((l.split("class ", 1)[1].split("(")[0].strip() for l in txt.splitlines()
                    if l.startswith("class ") and "(ARCBaseGame)" in l), None)
        if cls:
            jobs.append((str(f), cls, args))
        else:
            print(f"!! {f.stem}: brak klasy ARCBaseGame")

    print(f"{len(jobs)} gier, workers={p.workers}, node_cap={p.node_cap}, sec_cap={p.sec_cap}s, "
          f"bfs_branch<={p.bfs_branch}, calib_step={p.calib_step}px", flush=True)
    with open(p.out, "w") as fh:
        with mp.Pool(p.workers) as pool:
            for i, res in enumerate(pool.imap_unordered(play_game, jobs), 1):
                fh.write(json.dumps(res) + "\n"); fh.flush()
                solved = sum(1 for r in res["levels"] if r["solved"])
                print(f"[{i}/{len(jobs)}] {res['game']:6} tryb={res.get('mode','?'):5} "
                      f"rozg={res.get('effective_branch','?'):>3} "
                      f"sygnal={res.get('signal_quality','?'):12} "
                      f"rozwiazane={solved} akcje={[r['actions'] for r in res['levels']]} "
                      f"{res.get('total_seconds','?')}s "
                      f"{('ERR ' + res['error']) if res.get('error') else ''}", flush=True)
    print("ZAPISANO", p.out, flush=True)


if __name__ == "__main__":
    main()
