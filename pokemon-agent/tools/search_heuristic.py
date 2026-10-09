#!/usr/bin/env python3
"""Evolutionary search for best heuristic config — PTCG version of Kaggriculture's 40-parallel screening.

User's previous project: arena.ai uploaded 40 parallel versions with different feature configs,
each played vs simulated top players, selected best 3, then varied them again.

This implements same for PTCG:
- Search space: scoring bands, wall bonuses, etc. (all env vars in main_tunable.py)
- Evaluation: win rate vs top10 decks (decks/top10/*.csv) — 20 games each, both seats
- Selection: top 3, then mutate around them for next generation

Usage:
    python tools/search_heuristic.py --generations 3 --pop-size 20 --games 15 --top10-dir decks/top10

Outputs:
    search_results/
        gen0.json, gen1.json, ...
        best_configs.json
        best_agent.py (copy of tunable with best env baked in)

The Rust speedup mentioned: Kaggriculture had Rust port 100x faster. For PTCG we use Python
kaggle_environments (0.15s/game) — okay for 20*15*15=4500 games (~10 min). For larger searches,
Actions matrix with 40 parallel jobs gives ~40x speedup (like original).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# Search space: param -> (default, min, max, type)
# Based on current heuristic defaults that matter most
SEARCH_SPACE = {
    # Scoring bands — order must be preserved, but exact values tunable within bands
    "PTCG_SUPPORTER": (340, 320, 360),
    "PTCG_ITEM": (330, 310, 350),
    "PTCG_BENCH": (320, 300, 340),
    "PTCG_EVOLVE": (310, 290, 330),
    "PTCG_ATTACH": (300, 280, 320),
    "PTCG_STADIUM": (290, 270, 310),
    "PTCG_ABILITY": (270, 250, 290),
    "PTCG_ATTACK_KO": (260, 240, 280),
    "PTCG_ATTACK": (200, 180, 220),
    # Retreat
    "PTCG_RETREAT_BASE": (120, 80, 160),
    "PTCG_RETREAT_NO_ATK": (205, 180, 230),
    "PTCG_RETREAT_KO": (285, 260, 310),
    "PTCG_RETREAT_WALL": (340, 320, 380),
    # Wall handling
    "PTCG_GUST_BONUS": (60, 30, 100),
    "PTCG_WALL_PENALTY": (-500, -700, -300),
    "PTCG_WALL_ESCAPE": (200, 100, 300),
    "PTCG_ATTACH_WALL_BONUS": (40, 20, 80),
    "PTCG_ATTACH_WALL_PENALTY": (-20, -50, 0),
    "PTCG_BEACH_WALL": (345, 320, 370),
    # Fighter
    "PTCG_FIGHTER_READY": (60, 30, 90),
    "PTCG_FIGHTER_NOT_READY": (-40, -80, -10),
    "PTCG_PRIZE_PENALTY": (25, 10, 40),
    # Energy
    "PTCG_ENABLE_BONUS": (30, 15, 50),
    "PTCG_PROGRESS_BONUS": (18, 8, 30),
    "PTCG_ACTIVE_BONUS": (12, 5, 25),
    "PTCG_PRIMARY_BONUS": (10, 5, 20),
}


def random_config() -> dict:
    cfg = {}
    for k, (default, mn, mx) in SEARCH_SPACE.items():
        # Gaussian around default, clipped to min/max
        # For first gen, uniform random in range
        cfg[k] = random.randint(mn, mx)
    return cfg


def mutate_config(parent: dict, strength: float = 0.2) -> dict:
    """Mutate parent config by ±strength*range"""
    cfg = {}
    for k, (default, mn, mx) in SEARCH_SPACE.items():
        rng = mx - mn
        # 20% chance to keep parent value exactly
        if random.random() < 0.2:
            cfg[k] = parent[k]
        else:
            # Add gaussian noise
            delta = random.gauss(0, rng * strength * 0.3)
            val = int(parent[k] + delta)
            val = max(mn, min(mx, val))
            cfg[k] = val
    return cfg


def evaluate_config(cfg: dict, games: int, top10_dir: str, our_deck: str, agent_path: str) -> dict:
    """Evaluate one config vs top10, return win rate"""
    # Set env vars for this evaluation
    env = os.environ.copy()
    for k, v in cfg.items():
        env[k] = str(v)

    # We need to run vs_top10 logic but with env vars
    # Import here to avoid circular
    import subprocess
    import sys

    # Use vs_top10.py as subprocess with env
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "vs_top10.py"),
        "--games",
        str(games),
        "--top10-dir",
        top10_dir,
        "--our-deck",
        our_deck,
        "--agent",
        agent_path,
    ]

    # Run with env
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    out = result.stdout + result.stderr

    # Parse overall win rate from output
    # Look for "Overall vs top10: 0.XXX"
    import re

    m = re.search(r"Overall vs top10:\s+([0-9.]+)", out)
    if m:
        rate = float(m.group(1))
    else:
        # Fallback: parse per-deck rates and average
        rates = re.findall(r"\s([0-9.]+)\s+\(\d+-\d+", out)
        if rates:
            # Last one is overall? Actually overall line is separate
            # Take average of per-deck rates
            try:
                rate = sum(float(r) for r in rates) / len(rates)
            except:
                rate = 0.0
        else:
            rate = 0.0

    return {"config": cfg, "win_rate": rate, "output": out[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=2, help="number of generations")
    ap.add_argument("--pop-size", type=int, default=20, help="population per generation")
    ap.add_argument("--games", type=int, default=15, help="games per top10 deck per evaluation")
    ap.add_argument("--top10-dir", default="decks/top10")
    ap.add_argument("--our-deck", default="decks/v3_boss33.csv", help="our deck to test")
    ap.add_argument("--agent", default="agents/main_tunable.py")
    ap.add_argument("--outdir", default="search_results")
    ap.add_argument("--workers", type=int, default=4, help="parallel workers")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Search: {args.generations} gens x {args.pop_size} pop, {args.games} games vs top10")
    print(f"Our deck: {args.our_deck}")
    print(f"Agent: {args.agent}")
    print(f"Top10 dir: {args.top10_dir} ({len(list(Path(args.top10_dir).glob('*.csv')))} decks)")

    # Check top10 decks exist
    if not Path(args.top10_dir).exists() or len(list(Path(args.top10_dir).glob("*.csv"))) == 0:
        print(f"Top10 dir {args.top10_dir} empty, falling back to decks/top10 from official dataset")
        # Try to use decks/top10 from earlier extraction
        if not Path("decks/top10").exists():
            print("No top10 decks found, abort", file=sys.stderr)
            return 1

    all_results = []

    # Generation 0: random
    population = [random_config() for _ in range(args.pop_size)]

    for gen in range(args.generations):
        print(f"\n{'='*60}")
        print(f"Generation {gen} — evaluating {len(population)} configs")
        print(f"{'='*60}")

        gen_results = []

        # Parallel evaluation
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(evaluate_config, cfg, args.games, args.top10_dir, args.our_deck, args.agent): i
                for i, cfg in enumerate(population)
            }
            for fut in concurrent.futures.as_completed(futures):
                idx = futures[fut]
                try:
                    res = fut.result()
                    gen_results.append(res)
                    print(f"  [{idx}] win_rate={res['win_rate']:.3f} cfg={ {k:res['config'][k] for k in list(res['config'])[:3]} }...")
                except Exception as exc:
                    print(f"  [{idx}] failed: {exc}")

        # Sort by win rate
        gen_results.sort(key=lambda r: r["win_rate"], reverse=True)

        # Save gen results
        gen_path = outdir / f"gen{gen}.json"
        gen_path.write_text(json.dumps(gen_results, indent=2) + "\n", encoding="utf-8")
        print(f"\nGen {gen} best: {gen_results[0]['win_rate']:.3f}")
        for i, r in enumerate(gen_results[:3]):
            print(f"  Top {i+1}: {r['win_rate']:.3f}")

        all_results.extend(gen_results)

        # Next generation: top 3 parents, each produces pop_size//3 mutated children
        if gen < args.generations - 1:
            parents = [r["config"] for r in gen_results[:3]]
            new_pop = []
            # Keep best parent as is (elitism)
            new_pop.append(parents[0])
            # Generate mutated children
            while len(new_pop) < args.pop_size:
                parent = random.choice(parents)
                # Decrease mutation strength over generations
                strength = 0.3 - gen * 0.05
                strength = max(0.1, strength)
                child = mutate_config(parent, strength=strength)
                new_pop.append(child)
            population = new_pop

    # Final best
    all_results.sort(key=lambda r: r["win_rate"], reverse=True)
    best = all_results[0]

    print(f"\n{'='*60}")
    print(f"BEST overall: win_rate={best['win_rate']:.3f}")
    print(f"Config: {json.dumps(best['config'], indent=2)}")

    # Save best
    (outdir / "best_configs.json").write_text(json.dumps(all_results[:10], indent=2) + "\n", encoding="utf-8")

    # Create best_agent.py with env baked in (for Kaggle, we need to hardcode best values)
    # We'll generate a file that sets os.environ at top
    tunable_src = Path(args.agent).read_text(encoding="utf-8")
    # Inject best config as env defaults at top of file
    inject = "\n".join([f'os.environ.setdefault("{k}", "{v}")' for k, v in best["config"].items()])
    # Find where to inject — after imports, before GO_FIRST
    # Look for "GO_FIRST ="
    if "GO_FIRST =" in tunable_src:
        tunable_src = tunable_src.replace("GO_FIRST =", f"{inject}\n\nGO_FIRST =", 1)
    else:
        tunable_src = inject + "\n\n" + tunable_src

    best_agent_path = outdir / "best_agent.py"
    best_agent_path.write_text(tunable_src, encoding="utf-8")
    print(f"Wrote best agent to {best_agent_path}")

    # Also copy to agents/best_from_search.py
    best_dest = ROOT / "agents" / "best_from_search.py"
    best_dest.write_text(tunable_src, encoding="utf-8")
    print(f"Wrote best to {best_dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
