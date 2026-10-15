#!/usr/bin/env python3
"""CEM/ES tuning of v41's PTCG_* weights (NOTES_STRATEGY §19 step 1).

Fitness = in-process FFI games (multiprocessing Pool) vs THREE opponent pilots
(c87_v34, c87_v42.1 per-arch, pristine v41-defaults) on rotating subsets of the
top50_provisional pool; our deck fixed (34W Kyo3). The current defaults are
evaluated every generation as a control (subset-difficulty drift + winner's
curse guard). Output: kaggle_results/es_tune/{history.csv,state.json,best.json}.

Run:  .venv/bin/python tools/cem_tune.py --gens 30 --pop 16
      .venv/bin/python tools/cem_tune.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mega50_test as m50  # noqa: E402  (get_lib/load_deck/load_mod/rebind/play)

OUR_DECK = ROOT / "decks/v41_34w_kyo3.csv"
AGENT = ROOT / "agents/main_heuristic_v41.py"
POOL_DIR = ROOT / "decks/top50_provisional"
OPP_PILOTS = [ROOT / "agents/c87_v34.py", ROOT / "agents/c87_v42_1_perarch.py", AGENT]
HARD_DECKS = ["decks/top50_provisional/Ricardo_Paizinho__122908409.csv",
              "decks/live_oct13/live_ogerpon_hydrapple.csv",
              "decks/live_oct13/live_alakazam_toolbox.csv",
              "decks/top7_live/Eugen_LNCanti.csv",
              "decks/top7_live/GiovanniCR.csv",
              "decks/top50_provisional/YumeNeko__118690867.csv"]
FIT_W_HARD = float(os.environ.get("CEM_FIT_W_HARD", "0.45"))

# name -> (center, sigma, lo, hi); centers = current v41 setdefaults (lines 209-234)
KNOBS = {
    "PTCG_SUPPORTER": (346, 28, 280, 430),
    "PTCG_ITEM": (325, 28, 250, 410),
    "PTCG_BENCH": (304, 28, 220, 400),
    "PTCG_EVOLVE": (292, 28, 210, 390),
    "PTCG_ATTACH": (287, 28, 200, 380),
    "PTCG_STADIUM": (270, 24, 180, 360),
    "PTCG_ABILITY": (259, 24, 170, 350),
    "PTCG_ATTACK_KO": (273, 24, 190, 370),
    "PTCG_ATTACK": (195, 20, 110, 300),
    "PTCG_RETREAT_BASE": (122, 18, 40, 230),
    "PTCG_RETREAT_NO_ATK": (219, 22, 130, 320),
    "PTCG_RETREAT_KO": (277, 24, 190, 380),
    "PTCG_RETREAT_WALL": (350, 28, 260, 460),
    "PTCG_GUST_BONUS": (70, 18, -20, 190),
    "PTCG_WALL_PENALTY": (-650, 70, -950, -350),
    "PTCG_WALL_ESCAPE": (230, 24, 120, 350),
    "PTCG_ATTACH_WALL_BONUS": (30, 16, -60, 130),
    "PTCG_ATTACH_WALL_PENALTY": (-35, 16, -130, 60),
    "PTCG_BEACH_WALL": (335, 26, 250, 440),
    "PTCG_FIGHTER_READY": (22, 14, -70, 130),
    "PTCG_FIGHTER_NOT_READY": (-63, 16, -170, 40),
    "PTCG_PRIZE_PENALTY": (16, 10, -40, 90),
    "PTCG_ENABLE_BONUS": (14, 10, -50, 90),
    "PTCG_PROGRESS_BONUS": (32, 12, -30, 110),
    "PTCG_ACTIVE_BONUS": (6, 8, -50, 70),
    "PTCG_PRIMARY_BONUS": (7, 8, -50, 70),
}
NAMES = list(KNOBS)
CENTER = {k: v[0] for k, v in KNOBS.items()}

_W = {}


def _worker_init():
    _W["lib"] = m50.get_lib()
    _W["our_deck"] = m50.load_deck(OUR_DECK)
    _W["pool"] = [(p.name, m50.load_deck(p)) for p in sorted(POOL_DIR.glob("*.csv"))]
    _W["hard"] = [(Path(h).name, m50.load_deck(ROOT / h)) for h in HARD_DECKS]
    _W["opps"] = []
    for i, p in enumerate(OPP_PILOTS):
        _W["opps"].append(m50.load_mod(p, f"_cem_opp_{i}"))
    # pristine v41 = third opp module above (loaded with default env)
    _W["n"] = 0


def _eval_candidate(task):
    knobs, plan = task  # plan: list of (opp_idx, src, [deck_idx,...], games_per_seat)
    lib, our_deck, pool = _W["lib"], _W["our_deck"], _W["pool"]
    for k in NAMES:
        os.environ[k] = str(int(round(knobs[k])))
    _W["n"] += 1
    name = f"_cem_cand_{os.getpid()}_{_W['n']}"
    cand = m50.load_mod(AGENT, name)
    m50.rebind(cand, our_deck)
    agg = {"pool": [0, 0, 0], "hard": [0, 0, 0]}
    w = d = l = e = 0
    try:
        for opp_idx, src, deck_idxs, gps in plan:
            opp = _W["opps"][opp_idx]
            deckset = _W["hard"] if src == "hard" else pool
            for di in deck_idxs:
                _, odeck = deckset[di]
                for _ in range(gps):
                    for seat in (0, 1):
                        r = m50.play(lib, cand, opp, our_deck, odeck, seat)
                        if r == 1:
                            w += 1; agg[src][0] += 1
                        elif r == -1:
                            l += 1; agg[src][1] += 1
                        elif r == 0:
                            d += 1; agg[src][2] += 1
                        else:
                            e += 1
    finally:
        sys.modules.pop(name, None)
    n = w + d + l
    def _wr(a):
        ww, ll, dd = a
        return (ww + 0.5 * dd) / (ww + ll + dd) if (ww + ll + dd) else 0.0
    wr_pool, wr_hard = _wr(agg["pool"]), _wr(agg["hard"])
    fit = (1 - FIT_W_HARD) * wr_pool + FIT_W_HARD * wr_hard if agg["hard"][0] + agg["hard"][1] else wr_pool
    return {"wr": fit, "wr_pool": wr_pool, "wr_hard": wr_hard,
            "w": w, "d": d, "l": l, "err": e, "n": n}


def make_plan(rng: random.Random, val: bool = False):
    npool = len(list(POOL_DIR.glob("*.csv")))
    idx = list(range(npool))
    if val:
        a = rng.sample(idx, 40); b = rng.sample(idx, 16); c = rng.sample(idx, 16)
        return [(0, "pool", a, 3), (1, "pool", b, 3), (2, "pool", c, 3),
                (0, "hard", list(range(6)), 8)]  # 240+96+96+96 = 528
    a = rng.sample(idx, 24); b = rng.sample(idx, 12); c = rng.sample(idx, 12)
    return [(0, "pool", a, 2), (1, "pool", b, 2), (2, "pool", c, 2),
            (0, "hard", list(range(6)), 6)]  # 96+48+48+72 = 264 games


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=30)
    ap.add_argument("--pop", type=int, default=16)
    ap.add_argument("--elites", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="kaggle_results/es_tune")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    from multiprocessing import Pool
    pool = Pool(2, initializer=_worker_init)

    if args.selftest:
        plan = make_plan(random.Random(123), val=False)
        t0 = time.time()
        res = pool.map(_eval_candidate, [(CENTER, plan)])
        print("baseline selftest:", res, f"{time.time()-t0:.1f}s")
        pool.close(); pool.join()
        return 0

    mu = dict(CENTER)
    sigma = {k: float(KNOBS[k][1]) for k in NAMES}
    start_gen = 0
    hist_path = out / "history.csv"
    if args.resume and (out / "state.json").exists():
        st = json.loads((out / "state.json").read_text())
        mu, sigma, start_gen = st["mu"], st["sigma"], st["gen"]
        print(f"resumed at gen {start_gen}", flush=True)

    hist_f = open(hist_path, "a", newline="")
    hist = csv.writer(hist_f)
    if hist_path.stat().st_size == 0:
        hist.writerow(["gen", "cand", "fitness", "w", "l", "n", "is_control", "is_elite_mean"])

    best = {"fitness": -1.0, "knobs": dict(CENTER)}
    if (out / "best.json").exists():
        best = json.loads((out / "best.json").read_text())

    for gen in range(start_gen, start_gen + args.gens):
        plan = make_plan(rng)
        cands = []
        for _ in range(args.pop):
            c = {}
            for k in NAMES:
                lo, hi = KNOBS[k][2], KNOBS[k][3]
                c[k] = min(hi, max(lo, rng.gauss(mu[k], sigma[k])))
            cands.append(c)
        tasks = [(c, plan) for c in cands] + [(dict(CENTER), plan)]
        t0 = time.time()
        res = pool.map(_eval_candidate, tasks)
        ctrl = res[-1]["wr"]
        scored = sorted(zip(cands, res[:-1]), key=lambda x: x[1]["wr"], reverse=True)
        elites = scored[: args.elites]
        for i, (c, r) in enumerate(scored):
            hist.writerow([gen, i, f"{r['wr']:.4f}", r["w"], r["l"], r["n"], 0, 0])
        hist.writerow([gen, -1, f"{ctrl:.4f}", res[-1]["w"], res[-1]["l"], res[-1]["n"], 1, 0])
        hist_f.flush()
        # CEM update on elites
        for k in NAMES:
            vals = [c[k] for c, _ in elites]
            mu[k] = sum(vals) / len(vals)
            var = sum((v - mu[k]) ** 2 for v in vals) / len(vals)
            sigma[k] = max(0.3 * KNOBS[k][1], (var ** 0.5) * 1.05)
        top_wr, top_knobs = scored[0][1]["wr"], scored[0][0]
        print(f"gen {gen}: top={top_wr:.4f} ctrl={ctrl:.4f} "
              f"elite_mean={sum(r['wr'] for _, r in elites)/len(elites):.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
        if top_wr > best["fitness"]:
            best = {"fitness": top_wr, "knobs": {k: int(round(v)) for k, v in top_knobs.items()},
                    "gen": gen, "control_that_gen": ctrl}
            (out / "best.json").write_text(json.dumps(best, indent=1))
        (out / "state.json").write_text(json.dumps(
            {"mu": mu, "sigma": sigma, "gen": gen + 1}, indent=1))
        # periodic fixed-seed validation of mu vs control
        if (gen + 1) % 5 == 0:
            vplan = make_plan(random.Random(999), val=True)
            mu_i = {k: int(round(mu[k])) for k in NAMES}
            vres = pool.map(_eval_candidate, [(mu_i, vplan), (dict(CENTER), vplan)])
            print(f"  VALIDATION gen {gen}: mu={vres[0]['wr']:.4f} (n={vres[0]['n']}) "
                  f"ctrl={vres[1]['wr']:.4f} (n={vres[1]['n']})", flush=True)
            with open(out / "validation.log", "a") as f:
                f.write(f"gen {gen}: mu={vres[0]['wr']:.4f} n={vres[0]['n']} "
                        f"ctrl={vres[1]['wr']:.4f} n={vres[1]['n']} mu_knobs={json.dumps(mu_i)}\n")

    (out / "final_mu.json").write_text(json.dumps(
        {"mu": {k: int(round(mu[k])) for k in NAMES}, "best": best}, indent=1))
    print("BEST:", json.dumps(best))
    pool.close(); pool.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
