#!/usr/bin/env python3
"""Model ekonomii tokenowej: wynik LB jako funkcja tok/akcję.

Po co ten plik
--------------
Wszystkie poprzednie analizy w tym katalogu liczyły, ile GŁĘBOKOŚCI (poziomów) da się
kupić za budżet tokenów. Ten model odpowiada na pytanie odwrotne i ważniejsze:

    przy jakiej ekonomii tokenów (tok/akcję) próg nagród 49.85 staje się osiągalny?

Punktem wyjścia są dwa ZMIERZONE, a nie założone stosunki tok/akcję z dwóch różnych linii:

    linia szybka (SGLang, Qwen3.8-Flash-Next W4A16 + MTP drafter), run r019
        1.74 M tokenów / 2065 akcji = 841 tok/akcję
        źródło: FAKTY-I-POMIARY.md L694-696

    linia wolna (vLLM, Qwen3.6-27B-FP8), run r050
        231 k tokenów / 521 akcji = 443.4 tok/akcję
        źródło: FAKTY-I-POMIARY.md L711

Model jest CEILINGIEM wykonalności budżetowej, NIE prognozą wyniku. Zakłada, że każdy
akcja z budżetu zamienia się w postęp przy efektywności EFF. Kalibracja przeciwko
rzeczywistości jest wypisana na końcu (sufit vs zmierzony LB), żeby nikt nie pomylił
jednego z drugim.

Użycie
------
    python3 tools/token_economy_model.py
    python3 tools/token_economy_model.py --tpa 444 --per-game
    python3 tools/token_economy_model.py --eff 0.90

Wymaga tylko results/game_metadata.json i results/playbook.json. Bez GPU, bez arcengine,
bez Kaggle, bez tokenów LLM.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))

# --- stałe wywiedzione z pomiarów, nie z założień -----------------------------
POOL_TOKENS = 175_000   # na grę: 755 tok/s * 9 h / 110 runów * 0.80 (FAKTY, arytmetyka budżetu)
EFF_DEFAULT = 0.95      # efektywność ruchów na UKOŃCZONYM poziomie: pomiar 17/27 poziomów
                        # r019 siedzących na capie 115 (niezależne potwierdzenie tw. o capie)
TPA_FAST = 841          # r019, linia szybka
TPA_SLOW = 443.4        # r050, linia wolna
PRIZE_THRESHOLD = 49.85 # 5. miejsce na live LB 24.10 = ostatnie płatne ($5k)

MEASURED_LB = 26.25     # ich najlepszy zmierzony wynik (duck v3, ref 57247568, 16.10)


def _load(name: str):
    with open(os.path.join(RESULTS, name), encoding="utf-8") as fh:
        return json.load(fh)


def load_games() -> List[Tuple[str, dict]]:
    md = _load("game_metadata.json")
    games = md.get("games", md) if isinstance(md, dict) else md
    if isinstance(games, dict):
        return list(games.items())
    return [(g.get("game_id") or g.get("id"), g) for g in games]


def load_playbook_depths() -> Dict[str, int]:
    """Ile początkowych (sekwencyjnych) poziomów playbook już rozwiązuje w danej grze.

    Poziomy w grze są sekwencyjne, a playbook rozwiązuje prefiks — więc te poziomy
    można przejść za ZERO tokenów LLM. To jest warm-start, nie tylko podłoga punktowa.
    """
    pb = _load("playbook.json")
    games = pb.get("games", {})
    out: Dict[str, int] = {}
    for gid, val in games.items():
        levels = val.get("levels") if isinstance(val, dict) else val
        out[gid] = len(levels) if hasattr(levels, "__len__") else 0
    return out


def score(m: int, n: int) -> float:
    """Wzór konkursowy: waga poziomu = k+1, wynik gry = 100 * Σw(ukończone)/Σw(wszystkie).

    Zweryfikowany co do setnej na r019 (FAKTY-I-POMIARY.md, sekcja o punktacji).
    Przy capie 115 i efektywności >= 0.93 każdy ukończony poziom daje 115, więc wynik
    zależy WYŁĄCZNIE od tego, KTÓRE poziomy są ukończone (twierdzenie o capie, FAKTY §2).
    """
    if n <= 0:
        return 0.0
    return 100.0 * sum(k + 1 for k in range(m)) / sum(k + 1 for k in range(n))


def levels_affordable(baselines: List[int], budget_actions: float, eff: float,
                      free_prefix: int = 0) -> int:
    """Maksymalna liczba sekwencyjnie ukończonych poziomów za dany budżet akcji.

    `free_prefix` poziomów jest już rozwiązanych przez playbook (koszt 0 tokenów),
    więc licznik zaczyna się od nich, a budżet idzie w całości na dalsze poziomy.
    """
    n = len(baselines)
    m = min(free_prefix, n)
    spent = 0.0
    for k in range(m, n):
        cost = baselines[k] / eff
        if spent + cost <= budget_actions:
            spent += cost
            m = k + 1
        else:
            break
    return m


def evaluate(tpa: float, eff: float, use_playbook: bool,
             pool: int = POOL_TOKENS) -> Tuple[float, float, List[tuple]]:
    budget = pool / tpa
    pb = load_playbook_depths() if use_playbook else {}
    total = 0.0
    detail: List[tuple] = []
    games = load_games()
    for gid, g in games:
        baselines = g.get("baseline_actions") or []
        n = g.get("n_levels") or len(baselines)
        if not baselines:
            detail.append((gid, n, 0, 0.0))
            continue
        m = levels_affordable(baselines, budget, eff, pb.get(gid, 0))
        s = score(m, n)
        total += s
        detail.append((gid, n, m, s))
    return total / len(games), budget, detail


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tpa", type=float, default=None,
                    help="pokaż szczegóły per gra dla tej wartości tok/akcję")
    ap.add_argument("--eff", type=float, default=EFF_DEFAULT,
                    help=f"efektywność ruchów na ukończonym poziomie (domyślnie {EFF_DEFAULT})")
    ap.add_argument("--pool", type=int, default=POOL_TOKENS,
                    help=f"pula tokenów na grę (domyślnie {POOL_TOKENS})")
    ap.add_argument("--per-game", action="store_true", help="wypisz tabelę per gra")
    args = ap.parse_args()

    print(f"Pula na grę: {args.pool:,} tokenów | efektywność: {args.eff} | "
          f"próg nagród (5. miejsce, live 24.10): {PRIZE_THRESHOLD}")
    print(f"Zmierzone punkty odniesienia: linia szybka r019 = {TPA_FAST} tok/akcję, "
          f"linia wolna r050 = {TPA_SLOW} tok/akcję")
    print()
    print(f"{'tok/akcję':>10s} {'akcji w puli':>13s} {'LB bez PB':>10s} {'LB z PB':>9s} "
          f"{'Δ playbook':>11s} {'gier całk.':>11s}")

    grid = [841, 800, 700, 600, 500, 444, 400, 350, 300, 274, 250, 200, 150]
    rows = []
    for tpa in grid:
        lb0, budget, _ = evaluate(tpa, args.eff, False, args.pool)
        lb1, _, det = evaluate(tpa, args.eff, True, args.pool)
        full = sum(1 for _, n, m, _ in det if m == n and n > 0)
        rows.append((tpa, budget, lb0, lb1, full))
        mark = ""
        if abs(tpa - TPA_FAST) < 1:
            mark = "  <- stan obecny (r019)"
        elif abs(tpa - TPA_SLOW) < 1:
            mark = "  <- ekonomia linii wolnej (r050)"
        print(f"{tpa:>10.0f} {budget:>13.0f} {lb0:>10.2f} {lb1:>9.2f} "
              f"{lb1 - lb0:>+11.2f} {full:>11d}{mark}")

    print()
    print("=== kalibracja: to jest SUFIT wykonalności, nie prognoza ===")
    lb_now, _, _ = evaluate(TPA_FAST, args.eff, True, args.pool)
    print(f"  sufit przy obecnych {TPA_FAST} tok/akcję (z playbookiem): {lb_now:.2f}")
    print(f"  zmierzony LB ich najlepszej submisji (duck v3):           {MEASURED_LB}")
    gap_abs = lb_now - MEASURED_LB
    gap_mul = MEASURED_LB / lb_now if lb_now else 0.0
    print(f"  => model jest optymistyczny o {gap_abs:.2f} pp (×{gap_mul:.3f}).")
    print("     Różnica to eksploracja: agent nie zna rozwiązania, więc część budżetu")
    print("     idzie w hipotezy, które nie działają (35% puli w poziom nigdy nieukończony).")

    print()
    print("=== ile trzeba tok/akcję na próg nagród 49.85? ===")
    for label, use_pb in (("z playbookiem", True), ("bez playbooka", False)):
        hit = None
        # LB rośnie, gdy tok/akcję maleje, więc idziemy od NAJWIĘKSZEGO tok/akcję w dół
        # i bierzemy PIERWSZE trafienie = najmniejszą wymaganą poprawę ekonomii tokenów.
        for tpa in sorted(grid, reverse=True):
            lb, _, _ = evaluate(tpa, args.eff, use_pb, args.pool)
            if lb >= PRIZE_THRESHOLD:
                hit = (tpa, lb)
                break
        if hit:
            tpa, lb = hit
            cal_add = lb - gap_abs
            cal_mul = lb * gap_mul
            print(f"  {label}: {tpa:.0f} tok/akcję -> sufit {lb:.2f}")
            print(f"      po kalibracji: {cal_add:.1f} (addytywnie) / {cal_mul:.1f} (multiplikatywnie)")
        else:
            print(f"  {label}: nie osiąga progu w tym zakresie")

    if args.tpa or args.per_game:
        tpa = args.tpa or TPA_FAST
        lb, budget, det = evaluate(tpa, args.eff, True, args.pool)
        pb = load_playbook_depths()
        print()
        print(f"=== per gra przy {tpa:.0f} tok/akcję (budżet {budget:.0f} akcji, z playbookiem) ===")
        print(f"  {'gra':6s} {'suma_base':>9s} {'×budżet':>8s} {'PB':>3s} {'poz':>7s} {'score':>7s}")
        for gid, n, m, s in sorted(det, key=lambda x: -x[3]):
            g = dict(load_games())[gid]
            sb = g.get("sum_baseline")
            rat = (sb / budget) if isinstance(sb, (int, float)) else None
            print(f"  {gid:6s} {str(sb):>9s} {(f'{rat:.2f}' if rat else '-'):>8s} "
                  f"{pb.get(gid, 0):>3d} {f'{m}/{n}':>7s} {s:>7.2f}")
        print(f"  LB = {lb:.2f}")


if __name__ == "__main__":
    main()
