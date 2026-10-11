#!/usr/bin/env python3
"""Gen8 evolution with tempo fitness: winrate + prize pace to T9
Based on second branch diagnosis: policy gap 35pp, leaders T6-7 first prize, 2.2 prize by T9
FFI engine 120 games in 3s -> population 1000+

Fitness = winrate*0.7 + prize_score*0.2 + first_score*0.1
prize_score = min(prize_T9 / 2.2, 1.0)
first_score = min(7.0 / first_prize_turn, 1.0) with penalty if first>10
"""
import argparse, json, os, random, sys, time
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

# Search space from search_heuristic.py but narrowed around gen6 best
SEARCH_SPACE = {
    "PTCG_SUPPORTER": (345, 335, 355),
    "PTCG_ITEM": (315, 305, 325),
    "PTCG_BENCH": (313, 303, 323),
    "PTCG_EVOLVE": (294, 284, 304),
    "PTCG_ATTACH": (281, 271, 291),
    "PTCG_STADIUM": (270, 260, 280),
    "PTCG_ABILITY": (266, 256, 276),
    "PTCG_ATTACK_KO": (273, 263, 283),
    "PTCG_ATTACK": (205, 195, 215),
    "PTCG_RETREAT_BASE": (123, 100, 140),
    "PTCG_RETREAT_NO_ATK": (203, 190, 220),
    "PTCG_RETREAT_KO": (282, 265, 295),
    "PTCG_RETREAT_WALL": (353, 335, 365),
    "PTCG_GUST_BONUS": (70, 40, 90),  # boosted for early gust T0-1 like leaders
    "PTCG_WALL_PENALTY": (-650, -720, -500),
    "PTCG_WALL_ESCAPE": (230, 180, 280),
    "PTCG_ATTACH_WALL_BONUS": (30, 10, 50),
    "PTCG_ATTACH_WALL_PENALTY": (-20, -45, -5),
    "PTCG_BEACH_WALL": (335, 315, 365),
    "PTCG_FIGHTER_READY": (38, 20, 60),
    "PTCG_FIGHTER_NOT_READY": (-54, -70, -30),
    "PTCG_PRIZE_PENALTY": (24, 15, 35),
    "PTCG_ENABLE_BONUS": (18, 10, 30),
    "PTCG_PROGRESS_BONUS": (29, 20, 40),  # higher for Hammer-lanche progress
    "PTCG_ACTIVE_BONUS": (5, 2, 15),
    "PTCG_PRIMARY_BONUS": (13, 5, 20),
}

def random_config():
    cfg={}
    for k,(default,mn,mx) in SEARCH_SPACE.items():
        cfg[k]=random.randint(mn,mx)
    return cfg

def mutate_config(parent, strength=0.2):
    cfg={}
    for k,(default,mn,mx) in SEARCH_SPACE.items():
        rng=mx-mn
        if random.random()<0.2:
            cfg[k]=parent[k]
        else:
            delta=random.gauss(0, rng*strength*0.3)
            val=int(parent[k]+delta)
            val=max(mn, min(mx, val))
            cfg[k]=val
    return cfg

def evaluate_config(cfg, games, meta_dir, our_deck, agent_path):
    env=os.environ.copy()
    for k,v in cfg.items():
        env[k]=str(v)
    # run gauntlet_tempo
    cmd=[
        sys.executable,
        str(ROOT / "tools" / "gauntlet_tempo.py"),
        "--agent", agent_path,
        "--our-deck", our_deck,
        "--opp-dir", meta_dir,
        "--games", str(games),
    ]
    result=subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    out=result.stdout+result.stderr
    # parse TOTAL line with fitness
    import re
    m=re.search(r"fitness=([0-9.]+)", out)
    fitness=float(m.group(1)) if m else 0.0
    m2=re.search(r"winrate=([0-9.]+)", out)
    winrate=float(m2.group(1)) if m2 else 0.0
    m3=re.search(r"first=([0-9.]+)", out)
    first=float(m3.group(1)) if m3 else 99.0
    m4=re.search(r"prize_T9=([0-9.]+)", out)
    prize=float(m4.group(1)) if m4 else 0.0
    return {"config":cfg, "fitness":fitness, "winrate":winrate, "first":first, "prize_T9":prize, "output":out[-2000:]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--pop-size", type=int, default=20)
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--meta-dir", default="decks/gen8_meta")
    ap.add_argument("--our-deck", default="decks/v12_30_boss4.csv")
    ap.add_argument("--agent", default="agents/main_heuristic_v11.py")
    ap.add_argument("--outdir", default="search_results_gen8")
    ap.add_argument("--workers", type=int, default=2)
    args=ap.parse_args()

    outdir=Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Gen8 search: {args.generations} gens x {args.pop_size} pop, {args.games} games vs {args.meta_dir}")
    print(f"Decks in meta: {len(list(Path(args.meta_dir).glob('*.csv')))}")
    
    population=[random_config() for _ in range(args.pop_size)]
    all_results=[]

    for gen in range(args.generations):
        print(f"\n{'='*60}\nGeneration {gen} — {len(population)} configs\n{'='*60}")
        gen_results=[]
        # sequential for now (FFI has global lib, parallel may conflict)
        for i,cfg in enumerate(population):
            res=evaluate_config(cfg, args.games, args.meta_dir, args.our_deck, args.agent)
            gen_results.append(res)
            print(f"  [{i}] fitness={res['fitness']:.3f} win={res['winrate']:.3f} first={res['first']:.1f} prize_T9={res['prize_T9']:.2f} gust={cfg['PTCG_GUST_BONUS']} retreat_wall={cfg['PTCG_RETREAT_WALL']}")

        gen_results=sorted(gen_results, key=lambda x: x["fitness"], reverse=True)
        # save gen
        (outdir / f"gen{gen}.json").write_text(json.dumps(gen_results, indent=2))
        best=gen_results[0]
        print(f"\nGEN {gen} BEST fitness={best['fitness']:.3f} win={best['winrate']:.3f} first={best['first']:.1f} prize_T9={best['prize_T9']:.2f}")
        print(f"  config: {best['config']}")

        all_results.extend(gen_results)

        # next gen: top 3 mutate
        top3=[r["config"] for r in gen_results[:3]]
        next_pop=[]
        # keep top3
        next_pop.extend(top3)
        # mutate around top3
        for parent in top3:
            for _ in range((args.pop_size-3)//3):
                next_pop.append(mutate_config(parent, strength=0.15))
        # fill rest random
        while len(next_pop)<args.pop_size:
            next_pop.append(random_config())
        population=next_pop[:args.pop_size]

    all_sorted=sorted(all_results, key=lambda x: x["fitness"], reverse=True)
    (outdir / "best.json").write_text(json.dumps(all_sorted[:10], indent=2))
    best=all_sorted[0]
    print(f"\n=== FINAL BEST ===")
    print(f"fitness={best['fitness']:.3f} win={best['winrate']:.3f} first={best['first']:.1f} prize_T9={best['prize_T9']:.2f}")
    print(best["config"])
    # write best agent file with env baked in
    agent_src=Path(args.agent).read_text()
    # create new agent with env defaults
    out_agent=outdir / "best_agent_gen8.py"
    # replace os.environ.setdefault lines with best config
    lines=agent_src.splitlines()
    new_lines=[]
    for line in lines:
        for k,v in best["config"].items():
            if f'"{k}"' in line and "setdefault" in line:
                # replace default value
                # line like os.environ.setdefault("PTCG_GUST_BONUS", "70")
                import re
                line=re.sub(r'setdefault\("{}",\s*"[^"]+"\)'.format(k), f'setdefault("{k}", "{v}")', line)
        new_lines.append(line)
    out_agent.write_text("\n".join(new_lines))
    print(f"Wrote {out_agent}")

if __name__=="__main__":
    import sys
    sys.exit(main())
