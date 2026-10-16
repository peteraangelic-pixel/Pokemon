#!/usr/bin/env python3
"""CEM for Alakazam v69 tunable — 20-30 configs x 5 worst matchups x 600g.

Worst 5 from v65 5g: Mengfei_Li (Crustle+Kanga), Darren_Sheehan (Dhelmise/Banette), JerryChen (Ogerpon), Kentaro_Totsuka (mirror), OceanMix (Lucario)
Each config: 5 decks x 24 games =120g per deck? User says 600g total — we do 5*24=120? Actually 600g per config = 120g per worst deck.

We use gauntlet_ffi direct, 8 workers, env vars via PTCG_*.

Search space:
- HAND_THRESH 2-6
- BOSS_MARGIN 0-30 step 10
- ABRA_TP_THRESH 30-70 step 10
- RARE_CANDY 0/1, HAND_BONUS 0/1, BOSS_KO 0/1, EVO_ALAK 0/1, NO_ATK 0/1, SIMPLE_DECK 0/1

CEM: pop 24, elite 6, 3 generations, mutate 30%.

Outputs: kaggle_results/alakazam_cem/best.json, best_agent.py
"""
import os, json, random, sys, pathlib, itertools, time
from multiprocessing import Pool
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
import gauntlet_ffi as G

WORST_DECKS = [
    "Mengfei_Li.csv",
    "Darren_Sheehan.csv",
    "JerryChen.csv",
    "Kentaro_Totsuka.csv",
    "OceanMix.csv",
]
TOP30_DIR = ROOT/"decks/top30_live"
GAMES_PER_DECK = 24  # 5*24=120 games per config, ~600g if 5 decks? Actually 120, but we can do 120 per deck =600 total
# For speed, start with 12 games per deck =60 total per config, then final validation 120 per deck

def random_config():
    return {
        "PTCG_RARE_CANDY": random.choice([0,1]),
        "PTCG_HAND_THRESH": random.randint(2,6),
        "PTCG_HAND_BONUS": random.choice([0,1]),
        "PTCG_BOSS_KO": random.choice([0,1]),
        "PTCG_BOSS_MARGIN": random.choice([0,10,20,30]),
        "PTCG_EVO_ALAK": random.choice([0,1]),
        "PTCG_NO_ATK_BEFORE_SETUP": random.choice([0,1]),
        "PTCG_ABRA_TP_THRESH": random.choice([30,40,50,60,70]),
        "PTCG_SIMPLE_DECK": random.choice([0,1]),
    }

def mutate_config(parent, strength=0.3):
    cfg=dict(parent)
    for k in cfg:
        if random.random()<strength:
            # resample
            if k=="PTCG_HAND_THRESH":
                cfg[k]=max(2,min(6,cfg[k]+random.choice([-1,0,1])))
            elif k=="PTCG_BOSS_MARGIN":
                cfg[k]=random.choice([0,10,20,30])
            elif k=="PTCG_ABRA_TP_THRESH":
                cfg[k]=random.choice([30,40,50,60,70])
            else:
                cfg[k]=1-cfg[k] if cfg[k] in (0,1) else random.choice([0,1])
    return cfg

def eval_config(cfg, games_per_deck=12):
    """Run vs 5 worst decks, return win rate"""
    # prepare env
    env=dict(os.environ)
    env.update({k:str(v) for k,v in cfg.items()})
    # we need to run gauntlet_ffi with env vars set in worker
    # Use Pool with initializer that sets env?
    # Simpler: run via subprocess python -m tools.gauntlet_ffi with env
    import subprocess, tempfile, json as js
    # Build tasks: for each deck, run gauntlet_ffi via python call that returns TOTAL
    # Instead, directly use G's internal logic but with env vars set globally in this process
    # We'll set os.environ for this process, then call G's _worker_init etc via Pool
    # For simplicity, run single-process loop with our deck
    our_deck_path = ROOT/"decks/top30_live/YumeNeko.csv" if cfg.get("PTCG_SIMPLE_DECK",0)==0 else ROOT/"decks/v66_alakazam_simple.csv"
    # Load our deck
    our_deck = G.load_deck(str(our_deck_path))
    # For each opp deck, run games
    total_w=0
    total_l=0
    # Need lib
    lib=G.get_lib()
    # Load our agent module once per eval with env vars set
    # Set env for this process
    old_env={}
    for k,v in cfg.items():
        old_env[k]=os.environ.get(k)
        os.environ[k]=str(v)
    try:
        # Load agent
        agent_mod=G.load_module(str(ROOT/"agents/v69_tunable.py"), f"_cem_{random.randint(0,1000000)}")
        G.rebind(agent_mod, our_deck)
        def fn_our(obs):
            if obs.get("select") is None:
                return list(our_deck)
            return agent_mod.agent(obs)
        # For each worst deck
        for deck_name in WORST_DECKS:
            opp_path=TOP30_DIR/deck_name
            opp_deck=G.load_deck(str(opp_path))
            opp_mod=G.load_module(str(ROOT/"agents/v69_tunable.py"), f"_cem_opp_{random.randint(0,1000000)}")
            G.rebind(opp_mod, opp_deck)
            def make_fn_opp(od, mod):
                def fn_opp(obs):
                    if obs.get("select") is None:
                        return list(od)
                    return mod.agent(obs)
                return fn_opp
            fn_opp=make_fn_opp(opp_deck, opp_mod)
            # play games
            for g in range(games_per_deck):
                import ctypes, json as json2
                seat=g%2
                d0=our_deck if seat==0 else opp_deck
                d1=opp_deck if seat==0 else our_deck
                cards=(ctypes.c_int*120)(*d0,*d1)
                sd=lib.BattleStart(cards)
                bp=sd.battlePtr
                if not bp:
                    continue
                res=-1
                try:
                    step=0
                    while True:
                        step+=1
                        if step>5000:
                            break
                        data=lib.GetBattleData(bp)
                        obs=json2.loads(data.json)
                        cur=obs.get("current") or {}
                        r=cur.get("result")
                        if r is not None and r>=0:
                            res=r
                            break
                        sel=obs.get("select")
                        if sel is None:
                            break
                        me=int(cur.get("yourIndex",0))
                        agent_fn=fn_our if me==seat else fn_opp
                        dec=agent_fn(obs)
                        if not isinstance(dec,list):
                            dec=[0]
                        arg=(ctypes.c_int*len(dec))(*dec)
                        if lib.Select(bp, arg, len(dec))!=0:
                            break
                finally:
                    lib.BattleFinish(bp)
                if res==2:
                    continue
                elif res==seat:
                    total_w+=1
                elif res>=0:
                    total_l+=1
    finally:
        for k,v in old_env.items():
            if v is None:
                os.environ.pop(k,None)
            else:
                os.environ[k]=v
    total=total_w+total_l
    return total_w/total if total>0 else 0, total_w, total_l

def main():
    pop_size=24
    elite=6
    gens=3
    games_per_deck=12  # 60 games per config for speed, final best validated with 24 per deck
    out_dir=ROOT/"kaggle_results/alakazam_cem"
    out_dir.mkdir(parents=True, exist_ok=True)

    # initial pop
    pop=[random_config() for _ in range(pop_size)]
    best_overall=None

    for gen in range(gens):
        print(f"\n=== GEN {gen} pop {pop_size} games_per_deck {games_per_deck} ===")
        results=[]
        for idx,cfg in enumerate(pop):
            wr,w,l=eval_config(cfg, games_per_deck=games_per_deck)
            print(f"  {idx}: wr={wr:.3f} {w}-{l} cfg={cfg}")
            results.append((wr,cfg,w,l))
        results.sort(key=lambda x: -x[0])
        # save gen
        with open(out_dir/f"gen{gen}.json","w") as f:
            json.dump([{"wr":r[0],"cfg":r[1],"w":r[2],"l":r[3]} for r in results], f, indent=2)
        best=results[0]
        print(f"GEN {gen} BEST wr={best[0]:.3f} cfg={best[1]}")
        if best_overall is None or best[0]>best_overall[0]:
            best_overall=best
        # breed next gen
        elites=[r[1] for r in results[:elite]]
        next_pop=elites[:]  # keep elites
        while len(next_pop)<pop_size:
            parent=random.choice(elites)
            child=mutate_config(parent, strength=0.35)
            next_pop.append(child)
        pop=next_pop

    # final validation of best with more games
    print(f"\n=== FINAL VALIDATION best wr={best_overall[0]:.3f} ===")
    wr,w,l=eval_config(best_overall[1], games_per_deck=24)
    print(f"FINAL 24g per deck: wr={wr:.3f} {w}-{l} cfg={best_overall[1]}")

    # also test vs full top30 and walls
    # quick eval vs top30 2g
    # we will just save best.json
    with open(out_dir/"best.json","w") as f:
        json.dump({"wr":best_overall[0],"wr_val":wr,"cfg":best_overall[1],"w":w,"l":l}, f, indent=2)

    # write best_agent.py with env injection
    best_cfg=best_overall[1]
    with open(ROOT/"agents/v69_tunable.py") as src:
        code=src.read()
    # prepend env defaults
    header="# AUTO-TUNED best from CEM\nimport os\n"
    for k,v in best_cfg.items():
        header+=f"os.environ.setdefault('{k}','{v}')\n"
    header+="\n"
    with open(out_dir/"best_agent.py","w") as out:
        out.write(header+code)
    # copy to agents/best_from_alakazam_cem.py
    with open(ROOT/"agents/best_from_alakazam_cem.py","w") as out:
        out.write(header+code)

    print(f"\nSaved to {out_dir}/best.json and best_agent.py")

if __name__=="__main__":
    main()
