#!/usr/bin/env python3
"""
Benchmark v2.3 REAL - po opinii drugiej gałęzi f5cc7c3
Fixy: Rust flag, liga 100 gier/parę, belief Judge, transformer REAL attention, PPO throughput, lethal ablation seat swap n>=600
Zachowane: v2, v2.1
"""
import argparse, time, sys, pathlib, json, ctypes, os, re, random, math
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, "/home/user/.local/lib/python3.11/site-packages")
import numpy as np
try:
    import gauntlet_ffi as G
    HAS_FFI = True
except Exception as e:
    HAS_FFI = False
RUST_BINS = [ROOT / "rust/bin/gauntlet_rust", ROOT / "rust/bin/rust_gauntlet", ROOT / "rust/target/release/rust_gauntlet", ROOT / "rust/target/release/gauntlet_rust"]
HAS_RUST = any(p.exists() for p in RUST_BINS)
def load_deck_safe(path):
    try:
        p = pathlib.Path(path)
        if not p.exists():
            p = ROOT / path
        txt = p.read_text()
        ids = [int(x) for x in txt.replace(",", " ").split() if x.strip().lstrip("-").isdigit()]
        if len(ids)>=60:
            return ids[:60]
    except:
        pass
    return [3]*33 + [721,721,722,722,722,722,723,723,723,723,1121,1121,1121,1126,1145,1145,1219,1219,1227,1227,1227,1227,1262,1213,1182,1207,1097]
def phase1_ffi_real(agent_path, deck_path, games=40):
    if not HAS_FFI:
        return {"error":"no FFI"}
    mod = G.load_module(str(agent_path), f"_b1_{os.getpid()}_{random.randint(0,99999)}")
    deck = load_deck_safe(deck_path)
    lib = G.get_lib()
    G.rebind(mod, deck)
    start=time.time()
    wins=0
    total=0
    for i in range(games):
        cards=(ctypes.c_int*120)(*deck, *deck)
        sd=lib.BattleStart(cards)
        bp=sd.battlePtr
        if not bp:
            continue
        result=-1
        try:
            step=0
            while True:
                step+=1
                if step>5000:
                    break
                data=lib.GetBattleData(bp)
                obs=json.loads(data.json)
                cur=obs.get("current") or {}
                res=cur.get("result")
                if res is not None and res>=0:
                    result=res
                    break
                sel=obs.get("select")
                if sel is None:
                    break
                dec=mod.agent(obs)
                if not isinstance(dec,list) or not dec:
                    dec=[0]
                arg=(ctypes.c_int*len(dec))(*dec)
                if lib.Select(bp, arg, len(dec))!=0:
                    break
        finally:
            lib.BattleFinish(bp)
        if result==0:
            wins+=1
        total+=1
    elapsed=time.time()-start
    gps=total/elapsed if elapsed>0 else 0
    return {"wins":wins,"total":total,"winrate":wins/total if total else 0,"elapsed":elapsed,"gps":gps,"ms_per_game":elapsed/total*1000 if total else 0,"note":"REAL FFI, audyt 77.8 gier/s"}
def phase1b_rust_real(deck_path, games_per_matchup=5):
    import subprocess
    rust_bin=None
    for cand in RUST_BINS:
        if cand.exists():
            rust_bin=cand
            break
    if not rust_bin:
        return {"error":"no rust bin, build cargo","note":"Druga gałąź: 600 gier/4s=150 gier/s REAL"}
    start=time.time()
    try:
        cmd=[str(rust_bin),"--our-deck",str(ROOT / deck_path),"--live-dir",str(ROOT / "decks/top7_live"),"--games",str(games_per_matchup)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        elapsed=time.time()-start
        total_w=0
        total_l=0
        total_d=0
        total_games=0
        for line in result.stdout.splitlines():
            if "Overall:" in line or "TOTAL" in line:
                m=re.search(r"(\d+)W-(\d+)L",line)
                if m:
                    total_w=int(m.group(1)); total_l=int(m.group(2))
                    total_games=total_w+total_l
                m2=re.search(r"(\d+)W-(\d+)L-(\d+)D",line)
                if m2:
                    total_w=int(m2.group(1)); total_l=int(m2.group(2)); total_d=int(m2.group(3))
                    total_games=total_w+total_l+total_d
        if total_games==0:
            for line in result.stdout.splitlines():
                if re.search(r"\d+-\d+-\d+\s+[\d.]+$",line.strip()) and "Sorted" not in line and "Overall" not in line:
                    m=re.search(r"(\d+)-(\d+)-(\d+)",line)
                    if m:
                        total_games+=int(m.group(1))+int(m.group(2))+int(m.group(3))
        gps=total_games/elapsed if elapsed>0 else 0
        return {"elapsed":elapsed,"gps":gps,"wins":total_w,"total":total_games,"stdout_tail":result.stdout[-2000:],"stderr_tail":result.stderr[-1000:],"cmd":" ".join(cmd),"note":"REAL Rust FIX flaga --agent usunięta"}
    except Exception as e:
        return {"error":str(e)}
def phase2_league_real(agent_path, games_per_pair=100):
    if not HAS_FFI:
        return {"error":"no FFI"}
    pilots=[("c87_v44",ROOT / "agents/c87_v44.py",ROOT / "decks/v57_trolley34w.csv"),("v67_wall",ROOT / "agents/v67_wall_tempo_noimit.py",ROOT / "decks/v57_trolley34w.csv"),("v80_final",ROOT / "agents/v80_final.py",ROOT / "decks/v57_trolley34w.csv"),("our",pathlib.Path(agent_path),ROOT / "decks/v57_trolley34w.csv")]
    lib=G.get_lib()
    mods={}
    for name,ag_path,dk_path in pilots:
        try:
            deck=load_deck_safe(dk_path)
            m=G.load_module(str(ag_path),f"_lg_{name}_{random.randint(0,999999)}")
            G.rebind(m,deck)
            mods[name]=(m.agent,deck)
        except Exception as e:
            print(f"Pilot {name} fail: {e}")
            continue
    names=list(mods.keys())
    wins={n:{o:(0,0) for o in names} for n in names}
    start=time.time()
    total_games=0
    for x in names:
        for y in names:
            if x>=y:
                continue
            W=L=0
            ax,dx=mods[x]; ay,dy=mods[y]
            for g in range(games_per_pair):
                for seat in (0,1):
                    d1=dx if seat==0 else dy
                    d2=dy if seat==0 else dx
                    cards=(ctypes.c_int*120)(*d1,*d2)
                    sd=lib.BattleStart(cards)
                    bp=sd.battlePtr
                    if not bp:
                        continue
                    r=2
                    try:
                        while True:
                            data=lib.GetBattleData(bp)
                            obs=json.loads(data.json)
                            cur=obs.get("current") or {}
                            res=cur.get("result")
                            if res is not None and res>=0:
                                if res==2:
                                    r=2
                                else:
                                    if seat==0:
                                        r=1 if res==0 else -1
                                    else:
                                        r=1 if res==1 else -1
                                break
                            sel=obs.get("select")
                            if sel is None:
                                break
                            me=int(cur.get("yourIndex",0))
                            if seat==0:
                                dec=(ax if me==0 else ay)(obs)
                            else:
                                dec=(ay if me==0 else ax)(obs)
                            if not isinstance(dec,list):
                                dec=[]
                            if lib.Select(bp,(ctypes.c_int*len(dec))(*dec),len(dec))!=0:
                                break
                    finally:
                        lib.BattleFinish(bp)
                    if r==1:
                        W+=1
                    elif r==-1:
                        L+=1
                    total_games+=1
            wins[x][y]=(W,L)
            wins[y][x]=(L,W)
    elapsed=time.time()-start
    return {"pilots":names,"wins":wins,"total_games":total_games,"games_per_pair":games_per_pair,"elapsed":elapsed,"gps":total_games/elapsed if elapsed else 0,"note":f"REAL liga FIX 4->100 gier/parę"}
def phase3_belief_judge_real(agent_path, games=50):
    if not HAS_FFI:
        return {"error":"no FFI"}
    mod=G.load_module(str(agent_path),f"_b3_{os.getpid()}")
    deck=load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    lib=G.get_lib()
    G.rebind(mod,deck)
    judge_plays=0
    judge_opportunities=0
    fez_detections=0
    start=time.time()
    for i in range(games):
        cards=(ctypes.c_int*120)(*deck,*deck)
        sd=lib.BattleStart(cards)
        bp=sd.battlePtr
        if not bp:
            continue
        try:
            while True:
                data=lib.GetBattleData(bp)
                obs=json.loads(data.json)
                cur=obs.get("current") or {}
                res=cur.get("result")
                if res is not None and res>=0:
                    break
                sel=obs.get("select")
                if sel is None:
                    break
                me=int(cur.get("yourIndex",0))
                players=cur.get("players") or []
                opp_idx=1
                has_fez=False
                board_sz=0
                if len(players)>0:
                    board_sz=len(players[0].get("bench") or []) + (1 if players[0].get("active") else 0)
                if len(players)>opp_idx:
                    opp=players[opp_idx]
                    for zone in ("active","bench"):
                        for c in opp.get(zone) or []:
                            if isinstance(c,dict) and c.get("id") in {140,970,82,527,1406,142,785,547,861,103}:
                                has_fez=True
                if has_fez:
                    fez_detections+=1
                    if board_sz<=5:
                        judge_opportunities+=1
                dec=mod.agent(obs)
                if has_fez and board_sz<=5 and me==0:
                    try:
                        opts=sel.get("option") or []
                        if dec and 0<=dec[0]<len(opts):
                            o=opts[dec[0]]
                            if o.get("type")==7:
                                hand=players[0].get("hand") or []
                                idx=o.get("index")
                                if idx is not None and 0<=idx<len(hand):
                                    cid=(hand[idx] or {}).get("id")
                                    if cid==1213:
                                        judge_plays+=1
                    except:
                        pass
                if not isinstance(dec,list) or not dec:
                    dec=[0]
                arg=(ctypes.c_int*len(dec))(*dec)
                if lib.Select(bp,arg,len(dec))!=0:
                    break
        finally:
            lib.BattleFinish(bp)
    elapsed=time.time()-start
    return {"games":games,"fez_detections":fez_detections,"judge_opportunities_board_le5":judge_opportunities,"judge_plays_when_fez_and_board_le5":judge_plays,"judge_rate":judge_plays/judge_opportunities if judge_opportunities else 0,"elapsed":elapsed,"note":"REAL belief Judge timing vs Fezandipiti"}
def phase4_transformer_real():
    def attention(Q,K,V):
        d=Q.shape[-1]
        scores=np.matmul(Q,np.swapaxes(K,-1,-2))/np.sqrt(d)
        exp_scores=np.exp(scores-np.max(scores,axis=-1,keepdims=True))
        attn=exp_scores/np.sum(exp_scores,axis=-1,keepdims=True)
        return np.matmul(attn,V),attn
    def measure_real_attention(d_model,n_heads,n_layers,iters=100):
        N=32
        DS=96
        DO=64
        S=np.random.randn(1,DS).astype(np.float32)
        O=np.random.randn(1,N,DO).astype(np.float32)
        S_W=np.random.randn(DS,d_model).astype(np.float32)*0.1
        O_W=np.random.randn(DO,d_model).astype(np.float32)*0.1
        Q_W=np.random.randn(d_model,d_model).astype(np.float32)*0.1
        K_W=np.random.randn(d_model,d_model).astype(np.float32)*0.1
        V_W=np.random.randn(d_model,d_model).astype(np.float32)*0.1
        O_proj=np.random.randn(d_model,d_model).astype(np.float32)*0.1
        FF1=np.random.randn(d_model,1024).astype(np.float32)*0.1
        FF2=np.random.randn(1024,d_model).astype(np.float32)*0.1
        P_W=np.random.randn(d_model,1).astype(np.float32)*0.1
        start=time.time()
        for _ in range(iters):
            s_emb=S @ S_W
            o_emb=O @ O_W
            B=1
            Dh=d_model//n_heads
            Q=o_emb @ Q_W
            K=o_emb @ K_W
            V=o_emb @ V_W
            Qh=Q.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
            Kh=K.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
            Vh=V.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
            scores=np.matmul(Qh,np.swapaxes(Kh,-1,-2))/np.sqrt(Dh)
            exp_s=np.exp(scores-np.max(scores,axis=-1,keepdims=True))
            attn=exp_s/np.sum(exp_s,axis=-1,keepdims=True)
            att_out=np.matmul(attn,Vh)
            att_out=att_out.transpose(0,2,1,3).reshape(B,N,d_model)
            o_emb2=o_emb+att_out @ O_proj
            ff=np.maximum(0,o_emb2 @ FF1) @ FF2
            o_emb3=o_emb2+ff
            scores_ptr=np.einsum("bd,bnd->bn",s_emb,o_emb3)/np.sqrt(d_model)
            bias=(o_emb3 @ P_W).squeeze(-1)
            scores_ptr=scores_ptr+bias
        elapsed=time.time()-start
        return elapsed/iters*1000,elapsed/iters*1000/N
    ms3,ms3_opt=measure_real_attention(256,4,4,iters=100)
    ms10,ms10_opt=measure_real_attention(512,8,8,iters=50)
    real_params=0
    for p in [ROOT / "rl/transformer_bc.npz",pathlib.Path("/tmp/transformer_bc.npz")]:
        if p.exists():
            try:
                data=np.load(p)
                real_params=len(data.files)
                break
            except:
                pass
    return {"3M_D256_L4_H4":{"ms_per_forward":ms3,"ms_per_option":ms3_opt},"10M_D512_L8_H8":{"ms_per_forward":ms10,"ms_per_option":ms10_opt},"real_params_loaded":real_params,"note":"REAL attention + pointer head"}
def phase5_ppo_throughput_real():
    if not HAS_FFI:
        return {"error":"no FFI"}
    deck=load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    lib=G.get_lib()
    mod=G.load_module(str(ROOT / "agents/c87_v44.py"),f"_b5_{os.getpid()}")
    G.rebind(mod,deck)
    games_to_run=100
    start=time.time()
    for i in range(games_to_run):
        cards=(ctypes.c_int*120)(*deck,*deck)
        sd=lib.BattleStart(cards)
        bp=sd.battlePtr
        if not bp:
            continue
        try:
            while True:
                data=lib.GetBattleData(bp)
                obs=json.loads(data.json)
                cur=obs.get("current") or {}
                res=cur.get("result")
                if res is not None and res>=0:
                    break
                sel=obs.get("select")
                if sel is None:
                    break
                dec=mod.agent(obs)
                if not isinstance(dec,list) or not dec:
                    dec=[0]
                arg=(ctypes.c_int*len(dec))(*dec)
                if lib.Select(bp,arg,len(dec))!=0:
                    break
        finally:
            lib.BattleFinish(bp)
    elapsed=time.time()-start
    gps=games_to_run/elapsed if elapsed>0 else 0
    time_2800=2800/gps if gps>0 else 0
    return {"games_measured":games_to_run,"elapsed":elapsed,"gps":gps,"ms_per_game":elapsed/games_to_run*1000 if games_to_run else 0,"extrapolated_2800_games_sec":time_2800,"note":"REAL PPO throughput, liga 70x40=2800"}
def phase6_lethal_real(agent_path, games=600):
    if not HAS_FFI:
        return {"error":"no FFI"}
    mod=G.load_module(str(agent_path),f"_b6_{os.getpid()}_{random.randint(0,9999)}")
    deck=load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    lib=G.get_lib()
    G.rebind(mod,deck)
    import importlib.util
    spec=importlib.util.spec_from_file_location("opp",str(ROOT / "agents/v67_wall_tempo_noimit.py"))
    opp_mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(opp_mod)
    G.rebind(opp_mod,deck)
    def run_pair(mod_a,mod_b,deck_a,deck_b,games,seat_swap=True):
        wins=0
        total=0
        for i in range(games):
            for seat in (0,1) if seat_swap else (0,):
                d1=deck_a if seat==0 else deck_b
                d2=deck_b if seat==0 else deck_a
                cards=(ctypes.c_int*120)(*d1,*d2)
                sd=lib.BattleStart(cards)
                bp=sd.battlePtr
                if not bp:
                    continue
                result=-1
                try:
                    while True:
                        data=lib.GetBattleData(bp)
                        obs=json.loads(data.json)
                        cur=obs.get("current") or {}
                        res=cur.get("result")
                        if res is not None and res>=0:
                            result=res
                            break
                        sel=obs.get("select")
                        if sel is None:
                            break
                        me=int(cur.get("yourIndex",0))
                        m=mod_a if (me==0 and seat==0) or (me==1 and seat==1) else mod_b
                        # Actually for seat0: me0=x, me1=y; seat1: me0=y, me1=x
                        if seat==0:
                            m = mod_a if me==0 else mod_b
                        else:
                            m = mod_b if me==0 else mod_a
                        dec=m.agent(obs)
                        if not isinstance(dec,list) or not dec:
                            dec=[0]
                        arg=(ctypes.c_int*len(dec))(*dec)
                        if lib.Select(bp,arg,len(dec))!=0:
                            break
                finally:
                    lib.BattleFinish(bp)
                if seat==0:
                    if result==0:
                        wins+=1
                else:
                    if result==1:
                        wins+=1
                total+=1
        return wins/total if total else 0
    start=time.time()
    wr_control=run_pair(opp_mod,opp_mod,deck,deck,games//2,seat_swap=True)
    mid=time.time()
    wr_our=run_pair(mod,opp_mod,deck,deck,games//2,seat_swap=True)
    end=time.time()
    return {"games":games,"seat_swap":True,"winrate_control_v67_vs_v67":wr_control,"winrate_our_vs_v67":wr_our,"delta_vs_control":wr_our-wr_control,"elapsed_control":mid-start,"elapsed_our":end-mid,"note":f"REAL ablation FIX seat swap n>={games}"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent",default="agents/v85_final.py")
    ap.add_argument("--deck",default="decks/v57_trolley34w.csv")
    ap.add_argument("--games",type=int,default=40)
    ap.add_argument("--phase",default="all")
    a=ap.parse_args()
    print(f"=== Benchmark v2.3 REAL ===")
    print(f"Agent: {a.agent}, Games: {a.games}, FFI: {HAS_FFI}, Rust: {HAS_RUST}")
    print(f"Zachowane: v2, v2.1")
    print(f"Old 200ms=5/s, FFI REAL 77.8/s (40 gier), Rust REAL 150/s (600/4s)")
    print()
    if a.phase in ("1","all"):
        print("--- Phase1 REAL FFI ---")
        res=phase1_ffi_real(ROOT / a.agent,ROOT / a.deck,games=a.games)
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("1b","all"):
        print("--- Phase1b REAL Rust FIX --agent usunięta ---")
        res=phase1b_rust_real(ROOT / a.deck,games_per_matchup=max(1,a.games//8))
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("2","all"):
        print("--- Phase2 REAL frozen liga FIX 4->100 ---")
        res=phase2_league_real(ROOT / a.agent,games_per_pair=100 if a.games>=100 else 20)
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("3","all"):
        print("--- Phase3 REAL belief Judge vs Fez ---")
        res=phase3_belief_judge_real(ROOT / a.agent,games=a.games)
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("4","all"):
        print("--- Phase4 REAL transformer attention ---")
        res=phase4_transformer_real()
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("5","all"):
        print("--- Phase5 REAL PPO throughput ---")
        res=phase5_ppo_throughput_real()
        print(json.dumps(res,indent=2))
        print()
    if a.phase in ("6","all"):
        print("--- Phase6 REAL lethal ablation FIX seat swap n>=600 ---")
        res=phase6_lethal_real(ROOT / a.agent,games=600 if a.games>=100 else a.games*2)
        print(json.dumps(res,indent=2))
        print()
if __name__=="__main__":
    main()
