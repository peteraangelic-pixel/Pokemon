import json, os, random, re, subprocess, sys
random.seed(72072)
BASE = {"PTCG_B39_BENCH0":1000, "PTCG_B39_BENCH_TARGET":3, "PTCG_V45_IMIT_W":60,
        "PTCG_WALL_PENALTY":-500, "PTCG_WALL_ESCAPE":260, "PTCG_V41_HANDCAP":6}
RANGES = {"PTCG_B39_BENCH0":(200,2000), "PTCG_B39_BENCH_TARGET":(2,5), "PTCG_V45_IMIT_W":(0,120),
          "PTCG_WALL_PENALTY":(-900,-100), "PTCG_WALL_ESCAPE":(0,600), "PTCG_V41_HANDCAP":(4,10)}
def ev(cfg, games=700):
    env = dict(os.environ); env.update({k:str(v) for k,v in cfg.items()})
    tot=0.0; det=[]
    for opp,odeck in (("agents/c87_v44.py","decks/v57_trolley34w.csv"),
                      ("agents/v65_alakazam.py","decks/v66_alakazam_simple.csv")):
        cmd=[".venv/bin/python","tools/prizetest.py","--agent","agents/v67_wall_tempo_noimit.py",
             "--opp",opp,"--our-deck","decks/v57_trolley34w.csv","--opp-deck",odeck,"--games",str(games)]
        out=subprocess.run(cmd, capture_output=True, text=True, env=env).stdout
        m=re.search(r"WR=([\d.]+)", out); f=re.search(r"0 nagrod=\d+ \((\d+)%\)", out)
        wr=float(m.group(1)) if m else 0.0; det.append((wr, int(f.group(1)) if f else 99))
        tot+=wr
    return tot/2, det
def mutate(cfg):
    c=dict(cfg); k=random.choice(list(c))
    lo,hi=RANGES[k]; step=max(1,(hi-lo)//8)
    c[k]=max(lo,min(hi, c[k]+random.randint(-step,step)))
    return c
pop=[dict(BASE) for _ in range(6)]
for i in range(1,6): pop[i]=mutate(pop[i-1])
bf,_=ev(dict(BASE)); best=(bf, dict(BASE))
print("BAZA fitness:", best[0], best[1], flush=True)
scored=[]
for c in pop[1:]:
    f,_=ev(c); scored.append((f,c)); print("kandydat:", round(f,3), c, flush=True)
    if f>best[0]: best=(f,dict(c))
for gen in range(3):
    newpop=[]
    parents=sorted(scored+[(best[0],best[1])], key=lambda x:-x[0])[:3]
    for f,c in parents: newpop.append(dict(c))
    while len(newpop)<6: newpop.append(mutate(random.choice(parents)[1]))
    scored=[]
    for c in newpop[3:]:
        f,_=ev(c); scored.append((f,c)); print(f"gen{gen} kandydat:", round(f,3), c, flush=True)
        if f>best[0]: best=(f,dict(c))
print("BEST:", best)
json.dump({"best_cfg":best[1], "best_fitness":best[0]}, open('/tmp/es_best.json','w'))
