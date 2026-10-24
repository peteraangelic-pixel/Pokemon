#!/usr/bin/env python3
"""Formuła punktacji ARC-AGI-3 + jej weryfikacja na opublikowanych wynikach.

Źródło formuły: `taaf/game.py:381-413` w ich gałęzi (nie zgadywane - przepisane).

    per level k : score_k = min(115, (baseline_k / actions_k)^2 * 100)   jeśli ukończony, else 0
    waga        : w_k = k + 1
    per game    : score = Sum(score_k * w_k) / Sum(w_k po WSZYSTKICH poziomach)
                  z capem = Sum(w_k ukończonych) / Sum(w_k) * 100
    leaderboard : średnia po 110 runach

110 runów to NIE jest 110 różnych gier: `taaf/competition_arcade.py` ma
`OFFICIAL_110_RUN_COUNT = 110`, a `official_110()` buduje cykliczne klony 25 oficjalnych
gier (`clone_prefix='k'`, `i % len(source_ids)`). Czyli średnia po 110 runach ≈ średnia
po 25 grach - dlatego playbook liczymy jako sumę score'ów gier podzieloną przez 25.

WERYFIKACJA (ich własny smoke r019, 10 gier x 48 min):
    tn36: 7 poziomów, 1 ukończony  -> opublikowane 3.57
    ls20: 7 poziomów, 1 ukończony  -> opublikowane 3.27
Formuła odtwarza obie liczby co do setnej, gdy podstawi się zmierzoną liczbę akcji
(tn36 ~32 akcje przy baseline 32 -> 100 * 1/28 = 3.57; ls20 ~23 przy baseline 22
-> 91.5 * 1/28 = 3.27). Poniżej `--verify` robi dokładnie ten rachunek odwrotny.

KONSEKWENCJA strategiczna (najważniejsza liczba z całej analizy):
    jeden poziom w 7-poziomowej grze jest wart ~3.5 pkt, bo mianownik to SumW WSZYSTKICH
    poziomów (1+2+...+7 = 28). Wartość robi dopiero GŁĘBOKOŚĆ:
      5 poziomów w 9-poziomowym tu93 = 33.33 pkt
    Punktacja jest WYPUKŁA w głębokości, a efektywność (liczba akcji ponad baseline)
    jest prawie darmowa: sufit z głębokości 29.0 vs pomierzone 27.21 = 1.75 pkt za całą
    optymalizację ruchu.

Użycie:
    python3 score_formula.py --verify                    # sanity check na r019
    python3 score_formula.py --game tu93 --actions 18,10,19,17,29
    python3 score_formula.py --playbook results/playbook.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
# kolejność źródeł baseline_actions: commitowany game_metadata.json (działa wszędzie),
# potem katalog ściągnięty przez tools/fetch_repo_artifacts.sh
GAME_METADATA = HERE.parent / "results" / "game_metadata.json"
META_CANDIDATES = [
    Path("/home/user/arc3-scratch/meta"),
    HERE.parent.parent.parent / "arc3-scratch" / "meta",
    Path("/tmp/arc3/meta"),
]


def level_score(baseline: int, actions: int | None) -> float:
    """min(115, (baseline/actions)^2 * 100); 0 gdy poziom nieukończony."""
    if not actions or actions <= 0:
        return 0.0
    return min(115.0, (baseline / actions) ** 2 * 100.0)


def game_score(baselines: list[int], solved: dict[int, int]) -> float:
    """solved: {indeks_poziomu: liczba_akcji}. Dokładnie taaf/game.py:381-413."""
    W = [k + 1 for k in range(len(baselines))]
    tot = sum(W)
    num = sum(level_score(baselines[k], solved[k]) * W[k] for k in solved)
    cap = sum(W[k] for k in solved) / tot * 100.0
    return min(num / tot, cap)


def depth_ceiling(baselines: list[int], n_completed: int) -> float:
    """Sufit: ile dałoby ukończenie n_completed poziomów IDEALNIE (po 1 akcji)."""
    W = [k + 1 for k in range(len(baselines))]
    tot = sum(W)
    num = sum(115.0 * W[k] for k in range(n_completed))
    return min(num / tot, sum(W[k] for k in range(n_completed)) / tot * 100.0)


def actions_for_published(baselines: list[int], n_completed: int, published: float) -> float:
    """Rachunek odwrotny: ile akcji na poziomie 0 daje opublikowany score."""
    W = [k + 1 for k in range(len(baselines))]
    target = published * sum(W) / W[0]
    ratio = math.sqrt(min(target, 115.0) / 100.0)
    return baselines[0] / ratio if ratio else float("inf")


def load_baselines(game: str) -> list[int]:
    """baseline_actions per poziom - z commitowanego game_metadata.json albo z pobranego repo."""
    if GAME_METADATA.exists():
        rec = json.loads(GAME_METADATA.read_text())["games"].get(game)
        if rec and rec.get("baseline_actions"):
            return rec["baseline_actions"]
    for d in META_CANDIDATES:
        f = d / f"{game}.json"
        if f.exists():
            return json.loads(f.read_text())["baseline_actions"]
    raise SystemExit(f"brak baseline dla {game}: ani {GAME_METADATA}, ani {META_CANDIDATES}\n"
                     f"  -> uruchom tools/fetch_repo_artifacts.sh")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="sanity check na opublikowanych wynikach r019")
    ap.add_argument("--game")
    ap.add_argument("--actions", help="liczby akcji po przecinku, od poziomu 0")
    ap.add_argument("--playbook", help="policz wartość LB całego playbooka")
    ap.add_argument("--n-games", type=int, default=25)
    a = ap.parse_args()

    if a.verify or not (a.game or a.playbook):
        print("=== WERYFIKACJA FORMUŁY NA ICH DANYCH (smoke r019) ===")
        for g, published, n_lv in (("tn36", 3.57, 1), ("ls20", 3.27, 1)):
            b = load_baselines(g)
            need = actions_for_published(b, n_lv, published)
            recomputed = game_score(b, {0: round(need)})
            print(f"  {g}: {len(b)} poziomów, SumW={sum(k+1 for k in range(len(b)))}, "
                  f"baseline[0]={b[0]}")
            print(f"      opublikowane {published}  <=>  {need:.1f} akcji na poziomie 0")
            print(f"      formuła z powrotem daje {recomputed:.2f}  "
                  f"({'ZGODNE' if abs(recomputed - published) < 0.05 else 'ROZJAZD'})")
        print("\n  => formuła odtwarza ich wyniki; można nią liczyć wartość playbooka.")

    if a.game:
        b = load_baselines(a.game)
        acts = [int(x) for x in a.actions.split(",")] if a.actions else []
        solved = {i: n for i, n in enumerate(acts) if n > 0}
        sc = game_score(b, solved)
        print(f"\n=== {a.game}: {len(b)} poziomów, baseline={b} ===")
        for i, n in enumerate(acts):
            print(f"  L{i}: {n} akcji / baseline {b[i]} -> "
                  f"{level_score(b[i], n):.1f} pkt, waga {i+1}")
        print(f"  SCORE GRY = {sc:.2f}")
        for k in range(1, len(b) + 1):
            print(f"    sufit przy {k} ukończonych poziomach: {depth_ceiling(b, k):.1f}")

    if a.playbook:
        pb = json.loads(Path(a.playbook).read_text())
        games = pb.get("games", pb)
        total = 0.0
        print(f"\n=== PLAYBOOK: {len(games)} gier ===")
        for g, rec in sorted(games.items(), key=lambda kv: -kv[1].get("expected_game_score", 0)):
            b = rec.get("baseline_actions") or load_baselines(g)
            solved = {lv["level"]: lv["actions"] for lv in rec["levels"]}
            sc = game_score(b, solved)
            total += sc
            print(f"  {g:6} {len(solved)}/{len(b)} poziomów  score={sc:6.2f}  "
                  f"(sufit z tej głębokości {depth_ceiling(b, len(solved)):.2f})")
        print(f"\n  WARTOŚĆ LB (średnia po {a.n_games} grach): {total / a.n_games:.2f} pkt")
        print(f"  To PODŁOGA: te poziomy są zaliczone zanim model wyda pierwszy token.")


if __name__ == "__main__":
    main()
