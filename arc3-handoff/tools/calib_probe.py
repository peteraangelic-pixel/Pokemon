#!/usr/bin/env python3
"""SONDA KALIBRACYJNA: diagnostyka gry BEZ przeszukiwania (koszt ~0.5-8 s na grę).

Po co osobno: pełny przebieg `sweep2.py` kosztuje do 300 s na grę i kończy się wynikiem
„0 poziomów", z którego nie wynika, CZY gra jest nieprzeszukiwalna, czy tylko nie została
przeszukana tym razem. Ta sonda odpowiada na pierwsze pytanie tanio: mierzy dokładnie te
same wielkości co `play_game` w sweep2 (importuje te same funkcje, więc metoda jest
identyczna), ale zatrzymuje się przed searchem.

Mierzy dla każdej gry:
  available_actions        numery akcji z FrameData (publiczne API - bez współrzędnych)
  calib_responsive         ile z sondujących klików w ogóle zmienia ramkę
  calib_distinct_effects   ile RÓŻNYCH efektów (hash ramki po kliku) - to jest prawdziwe
                           rozgałęzienie gry click-owej; dla ft09 = 8 = liczba przycisków
  calib_median_delta       mediana liczby zmienionych pikseli (1-4 px = kursor/znacznik,
                           nie postęp - heurystyka nowości jest wtedy szumem)
  moves_raw / effective_branch / pruned_fell_back / mode
  signal_quality           dead_clicks | cursor_only | ok

signal_quality - definicje (zmierzone, nie zgadnięte):
  dead_clicks  gra wystawia ACTION6, ale ŻADEN klik nie zmienia ramki (sc25: 0 z 4096).
               Legalne ruchy o efekcie odroczonym - kryterium „ramka się zmieniła" ich nie
               wykrywa, więc ani kalibracja, ani heurystyka nowości nie działają.
  cursor_only  klik zmienia 1-4 px. W tn36 to NIE kursor a nakładane znaczniki (przemienne
               i addytywne - FAKTY §1bis(c)), ale skutek dla searcha jest ten sam: sygnał
               postępu tonie w szumie.
  ok           wyraźna zmiana stanu - search ma z czego wybierać.

Użycie:
  python3 calib_probe.py [--games-dir DIR] [--only g1,g2] [--out plik.jsonl]

Wynik dokleja się do results/game_metadata.json polem `calibration` (skrypt tego nie robi
sam - patrz komentarz na dole), żeby nie nadpisywać pól pochodzących z pełnych przebiegów.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from arcengine import ActionInput

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sweep2 as S  # noqa: E402  (współdzielimy load_game/frame_of/calibrate_clicks/...)


def probe(path: str, cls: str, step: int, calib_time: float, max_clicks: int,
          click_candidates: int, min_moves: int, bfs_branch: int) -> dict:
    args = S.Args(node_cap=0, sec_cap=0.0, max_levels=0, max_depth=0, beam=0,
                  click_candidates=click_candidates, max_clicks=max_clicks,
                  bfs_branch=bfs_branch, min_moves=min_moves,
                  calib_step=step, calib_time=calib_time)
    t0 = time.time()
    out: dict = {"game": Path(path).stem, "cls": cls, "error": None}
    try:
        game = S.load_game(path, cls)
        fd = game.perform_action(ActionInput(id=S.RESET))
        avail = [int(x) for x in (fd.available_actions or [])]
        frame = S.frame_of(fd)
        out.update({"win_levels": int(fd.win_levels), "avail": avail,
                    "levels_completed": int(fd.levels_completed)})

        if S.MOUSE_ID in avail:
            reps, n_resp, med_delta, n_eff = S.calibrate_clicks(
                game, frame, step, calib_time, max_clicks)
        else:
            reps, n_resp, med_delta, n_eff = [], 0, 0.0, 0
        moves_raw = S.build_moves(game, frame, avail, args, reps)
        moves = S.prune_moves(game, frame, moves_raw, min_moves)
        branch = len(moves)
        out.update({
            "calib_responsive": n_resp,
            "calib_distinct_effects": n_eff,
            "calib_median_delta": round(float(med_delta), 2),
            "click_reps": len(reps),
            "moves_raw": len(moves_raw),
            "effective_branch": branch,
            "pruned_fell_back": len(moves_raw) > 0 and len(moves) == len(moves_raw),
            "mode": "bfs" if branch <= bfs_branch else "beam",
            "signal_quality": ("dead_clicks" if S.MOUSE_ID in avail and n_resp == 0
                               else "cursor_only" if 0 < med_delta <= 4 else "ok"),
            "seconds": round(time.time() - t0, 2),
        })
    except Exception as exc:  # noqa: BLE001 - sonda ma raportować, nie padać
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["seconds"] = round(time.time() - t0, 2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games-dir", default="/home/user/arc3-scratch/games")
    ap.add_argument("--only", default="", help="lista gier po przecinku (puste = wszystkie)")
    ap.add_argument("--calib-step", type=int, default=4, help="siatka prób kliku (px)")
    ap.add_argument("--calib-time", type=float, default=8.0, help="limit czasu kalibracji (s)")
    ap.add_argument("--max-clicks", type=int, default=14)
    ap.add_argument("--click-candidates", type=int, default=28)
    ap.add_argument("--min-moves", type=int, default=3)
    ap.add_argument("--bfs-branch", type=int, default=8)
    ap.add_argument("--workers", type=int, default=1,
                    help="ZOSTAW 1: przy 2 workerach z deepcopy pada pamięć (kswapd0 100%%)")
    ap.add_argument("--out", default="")
    p = ap.parse_args()

    files = sorted(Path(p.games_dir).glob("*.py"))
    if p.only:
        want = {x.strip() for x in p.only.split(",") if x.strip()}
        files = [f for f in files if f.stem in want]
    jobs = []
    for f in files:
        txt = f.read_text(errors="replace")
        cls = next((l.split("class ", 1)[1].split("(")[0].strip() for l in txt.splitlines()
                    if l.startswith("class ") and "(ARCBaseGame)" in l), None)
        if cls:
            jobs.append((str(f), cls))
        else:
            print(f"!! {f.stem}: brak klasy ARCBaseGame", file=sys.stderr)

    print(f"{len(jobs)} gier, kalib_step={p.calib_step}px, max_clicks={p.max_clicks}, "
          f"workers={p.workers}", flush=True)
    hdr = (f"{'gra':6} {'avail':14} {'resp':>5} {'effekty':>7} {'medΔpx':>7} "
           f"{'rozg':>5} {'tryb':>5} {'sygnał':12} {'s':>6}")
    print(hdr)
    results = []
    for i, (path, cls) in enumerate(jobs, 1):
        r = probe(path, cls, p.calib_step, p.calib_time, p.max_clicks,
                  p.click_candidates, p.min_moves, p.bfs_branch)
        results.append(r)
        if r.get("error"):
            print(f"{r['game']:6} ERROR {r['error'][:70]}")
            continue
        print(f"{r['game']:6} {str(r['avail'])[:14]:14} {r['calib_responsive']:>5} "
              f"{r['calib_distinct_effects']:>7} {r['calib_median_delta']:>7} "
              f"{r['effective_branch']:>5} {r['mode']:>5} {r['signal_quality']:12} "
              f"{r['seconds']:>6}   [{i}/{len(jobs)}]", flush=True)
    if p.out:
        with open(p.out, "w") as fh:
            for r in results:
                fh.write(json.dumps(r) + "\n")
        print(f"\nZAPISANO {p.out} ({len(results)} gier)")
    hist: dict[str, int] = {}
    for r in results:
        q = r.get("signal_quality") or "error"
        hist[q] = hist.get(q, 0) + 1
    print("signal_quality:", json.dumps(hist, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
