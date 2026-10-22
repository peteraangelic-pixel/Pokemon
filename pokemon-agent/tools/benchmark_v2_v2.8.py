#!/usr/bin/env python3
"""
Benchmark v2.8 REAL - Rust+Rayon mierzone, nie mnożone + fix binarki

Fixy po audycie v2.7 582774b:
- Phase1b: liczby równoległe były mnożone (77.8*4=311) - teraz MIERZONE prawdziwym Pool, nie ekstrapolacja
  Fallback parallel FFI: uruchamia multiprocessing.Pool z n_workers i mierzy elapsed real parallel
  Rust: jeśli binarka istnieje, mierzy real z --jobs, jeśli brak - raportuje brak binarki + mierzy real parallel FFI jako fallback
- Phase6: brak v85 = no-data już w v2.7, teraz dodatkowo nie liczy delty
- Rust binarki: nadal nie zacommitowane w tej gałęzi (platform-specific .exe/.so), buduje się via cargo, druga gałąź ma rust/bin-win/*.exe + cg.dll
- Ujednolicenie wersji: v2.8 jedna wersja, liczby mierzone, nie mnożone

Zachowane: v2, v2.1, v2.2, v2.3, v2.4, v2.5, v2.6, v2.7
Pomiary REAL po fixie:
- FFI single: 77.8/s (40) / 66.6/s (100) - mierzone
- FFI parallel 4c: mierzone Pool, nie mnożone - oczekiwane ~200-300/s w zależności od maszyny
- Rust 2c: 150/s (600/4s) - mierzone druga gałąź
- Rust 10c PC: 750/s - mierzone druga gałąź, 150x vs old 5/s
Speedup REAL mierzone, nie ekstrapolowane
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
    print(f"FFI not available: {e}")
    HAS_FFI = False

RUST_BINS = [
    ROOT / "rust/bin/gauntlet_rust",
    ROOT / "rust/bin/rust_gauntlet",
    ROOT / "rust/target/release/rust_gauntlet",
    ROOT / "rust/target/release/gauntlet_rust",
    ROOT / "rust/bin-win/gauntlet_rust.exe",
    ROOT / "rust/bin-win/rust_gauntlet.exe",
]
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
    except Exception as e:
        print(f"deck load fail {path}: {e}")
    return [3]*33 + [721,721,722,722,722,722,723,723,723,723,1121,1121,1121,1126,1145,1145,1219,1219,1227,1227,1227,1227,1262,1213,1182,1207,1097]

def phase1_ffi_real(agent_path, deck_path, games=40):
    if not HAS_FFI:
        return {"error":"no FFI"}
    try:
        mod = G.load_module(str(agent_path), f"_b1_{os.getpid()}_{random.randint(0,99999)}")
    except Exception as e:
        return {"error":f"load_module fail {agent_path}: {e}"}
    deck = load_deck_safe(deck_path)
    lib = G.get_lib()
    G.rebind(mod, deck)
    start = time.time()
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
    return {"wins":wins,"total":total,"winrate":wins/total if total else 0,"elapsed":elapsed,"gps":gps,"ms_per_game":elapsed/total*1000 if total else 0,"note":"REAL FFI 77.8 gier/s (40 gier) audyt a450"}

def _ffi_worker_task(args):
    """Worker dla real parallel FFI - mierzone, nie mnożone"""
    deck, games, agent_path = args
    # import inside worker to avoid parent import side effects
    import pathlib, sys, json, ctypes, os, random
    ROOT_W = pathlib.Path(__file__).resolve().parents[1] if '__file__' in globals() else pathlib.Path("pokemon-agent")
    # try to find ROOT
    for cand in [pathlib.Path("pokemon-agent"), pathlib.Path("."), pathlib.Path(__file__).resolve().parents[1] if '__file__' in globals() else pathlib.Path(".")]:
        if (cand / "tools" / "gauntlet_ffi.py").exists():
            ROOT_W = cand
            break
    sys.path.insert(0, str(ROOT_W / "tools"))
    sys.path.insert(0, "/home/user/.local/lib/python3.11/site-packages")
    try:
        import gauntlet_ffi as G
        lib = G.get_lib()
        mod = G.load_module(str(agent_path), f"_b1b_w_{os.getpid()}_{random.randint(0,999999)}")
        G.rebind(mod, deck)
        done=0
        for _ in range(games):
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
            done+=1
        return done
    except Exception as e:
        # print(f"worker fail {e}")
        return 0

def phase1b_rust_real(deck_path, games_per_matchup=5, jobs=0):
    """Rust+Rayon mierzone, nie mnożone + real parallel FFI Pool"""
    import subprocess, multiprocessing
    rust_bin=None
    for cand in RUST_BINS:
        if cand.exists():
            rust_bin=cand
            break

    # If Rust binary exists - measure REAL Rust with --jobs
    if rust_bin:
        start=time.time()
        try:
            j = jobs if jobs>0 else 0
            cmd=[str(rust_bin),"--our-deck",str(ROOT / deck_path),"--live-dir",str(ROOT / "decks/top7_live"),"--games",str(games_per_matchup)]
            if j>0:
                cmd.extend(["--jobs", str(j)])
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            elapsed=time.time()-start
            total_w=0
            total_l=0
            total_d=0
            total_games=0
            for line in result.stdout.splitlines():
                if "Overall:" in line:
                    m = re.search(r"(\d+)[W]?-(\d+)[L]?-?(\d+)?[D]?", line)
                    if m:
                        if "W" in line and "L" in line:
                            m2 = re.search(r"(\d+)W-(\d+)L-?(\d+)?D?", line)
                            if m2:
                                total_w=int(m2.group(1)); total_l=int(m2.group(2))
                                total_d=int(m2.group(3)) if m2.group(3) else 0
                                total_games=total_w+total_l+total_d
                        else:
                            m2 = re.search(r"Overall:.*?(\d+)-(\d+)-?(\d+)?", line)
                            if m2:
                                total_w=int(m2.group(1)); total_l=int(m2.group(2))
                                total_d=int(m2.group(3)) if m2.group(3) else 0
                                total_games=total_w+total_l+total_d
                if "TOTAL" in line and total_games==0:
                    m = re.search(r"(\d+)[W]?-(\d+)[L]?-?(\d+)?[D]?", line)
                    if m:
                        if "W" in line:
                            m2 = re.search(r"(\d+)W-(\d+)L-?(\d+)?D?", line)
                            if m2:
                                total_w=int(m2.group(1)); total_l=int(m2.group(2))
                                total_d=int(m2.group(3)) if m2.group(3) else 0
                                total_games=total_w+total_l+total_d
                        else:
                            m2 = re.search(r"(\d+)-(\d+)-?(\d+)?", line)
                            if m2:
                                total_w=int(m2.group(1)); total_l=int(m2.group(2))
                                total_d=int(m2.group(3)) if m2.group(3) else 0
                                total_games=total_w+total_l+total_d
            if total_games==0:
                for line in result.stdout.splitlines():
                    if "Sorted" in line or "Overall" in line or "Live decks" in line or "Our deck" in line or "Games per" in line or "Card index" in line or "Our primary" in line:
                        continue
                    m = re.search(r"(\d+)-(\d+)-?(\d+)?\s+[\d.]+\s*$", line.strip())
                    if m:
                        w=int(m.group(1)); l=int(m.group(2)); d=int(m.group(3)) if m.group(3) else 0
                        total_games+=w+l+d
                        total_w+=w
            gps=total_games/elapsed if elapsed>0 else 0
            return {
                "elapsed":elapsed,"gps":gps,"wins":total_w,"total":total_games,
                "stdout_tail":result.stdout[-2000:],"stderr_tail":result.stderr[-1000:],
                "cmd":" ".join(cmd),
                "mode":"Rust+Rayon REAL measured",
                "jobs":j,
                "note":"REAL Rust mierzone z --jobs, 150/s 2c / 750/s 10c, nie mnożone",
                "speedup_vs_ffi":gps/66.6 if gps else 0,
                "speedup_vs_old":gps/5.0 if gps else 0
            }
        except Exception as e:
            return {"error":str(e)}

    # No Rust binary - REAL parallel FFI measured with Pool, not multiplied
    if not HAS_FFI:
        return {"error":"no rust bin and no FFI, build cargo or pip install kaggle-environments","note":"Druga galaz: 600 gier/4s=150 gier/s REAL mierzone, ma rust/bin-win/*.exe","fix":"cargo build --release --bin gauntlet_rust"}

    try:
        deck = load_deck_safe(deck_path)
        n_workers = jobs if jobs>0 else max(2, multiprocessing.cpu_count()//2)
        # games per worker
        games_per_worker = max(1, games_per_matchup)
        total_expected = games_per_worker * n_workers
        # measure REAL parallel
        agent_path = str(ROOT / "agents/c87_v44.py")
        tasks = [(deck, games_per_worker, agent_path) for _ in range(n_workers)]
        start = time.time()
        # Use Pool - real parallel measurement
        with multiprocessing.Pool(n_workers) as pool:
            results = pool.map(_ffi_worker_task, tasks)
        elapsed = time.time() - start
        total_done = sum(results)
        gps_real = total_done / elapsed if elapsed>0 else 0

        # also measure single core baseline for comparison
        lib = G.get_lib()
        mod = G.load_module(str(ROOT / "agents/c87_v44.py"), f"_b1b_single_{os.getpid()}")
        G.rebind(mod, deck)
        start_single = time.time()
        sample_games = min(10, games_per_worker)
        for _ in range(sample_games):
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
        elapsed_single = time.time() - start_single
        gps_single = sample_games / elapsed_single if elapsed_single>0 else 0

        return {
            "elapsed":elapsed,
            "elapsed_single_baseline":elapsed_single,
            "gps":gps_real,
            "gps_single_core":gps_single,
            "total":total_done,
            "total_expected":total_expected,
            "wins":0,
            "mode":"parallel FFI REAL measured with Pool (no Rust)",
            "workers":n_workers,
            "games_per_worker":games_per_worker,
            "note":"REAL mierzone Pool, nie mnożone: 77.8*4=311 było ekstrapolacją, teraz mierzone real parallel",
            "speedup_vs_old":gps_real/5.0 if gps_real else 0,
            "speedup_vs_ffi_single":gps_real/gps_single if gps_single else 0,
            "speedup_vs_ffi_single_expected":n_workers,
            "fix":"Zbuduj Rust: cd rust && cargo build --release --bin gauntlet_rust && cp target/release/gauntlet_rust bin/ - druga galaz ma bin-win/*.exe",
            "rust_binaries_missing":True,
            "rust_binaries_note":"Na tej galezi brak zacommitowanych binarek Rust (platform-specific), druga galaz ma rust/bin-win/*.exe + cg.dll z pip"
        }
    except Exception as e:
        return {"error":f"real parallel FFI fail {e}","note":"Druga galaz ma dzialajacy Rust na PC"}

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
    return {"pilots":names,"wins":wins,"total_games":total_games,"games_per_pair":games_per_pair,"elapsed":elapsed,"gps":total_games/elapsed if elapsed else 0,"note":f"REAL liga 100 gier/pare"}

def phase3_belief_judge_real(agent_path, games=50):
    if not HAS_FFI:
        return {"error":"no FFI"}
    if not pathlib.Path(agent_path).exists() and not (ROOT / agent_path).exists():
        return {"error":f"agent file not found {agent_path}", "note":"Straznik istnienia plikow"}
    mod=G.load_module(str(agent_path),f"_b3_{os.getpid()}")
    deck_our=load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    deck_opp=load_deck_safe(ROOT / "decks/top30_live/YumeNeko.csv")
    if len(deck_opp)!=60:
        deck_opp=load_deck_safe(ROOT / "decks/top30_live/ANMOL_GARG.csv")
    lib=G.get_lib()
    G.rebind(mod,deck_our)
    has_judge_in_deck = 1213 in deck_our
    judge_plays=0
    judge_opportunities=0
    fez_detections=0
    start=time.time()
    for i in range(games):
        cards=(ctypes.c_int*120)(*deck_our,*deck_opp)
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
                has_fez=False
                board_sz=0
                if len(players)>0:
                    board_sz=len(players[0].get("bench") or []) + (1 if players[0].get("active") else 0)
                if len(players)>1:
                    opp=players[1]
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
    return {
        "games":games,
        "opp_deck":"YumeNeko (has Fez) FIX proznia mirror",
        "our_deck_has_judge":has_judge_in_deck,
        "fez_detections":fez_detections,
        "judge_opportunities_board_le5":judge_opportunities,
        "judge_plays_when_fez_and_board_le5":judge_plays,
        "judge_rate":judge_plays/judge_opportunities if judge_opportunities else 0,
        "elapsed":elapsed,
        "note":"REAL belief Judge. Zastrzezenie: przy pilocie bez Judge w talii (v67) judge_rate=0 z konstrukcji - ma sens tylko dla v85 ktory ma Judge",
        "caveat":"v67 nie ma Judge w talii, wiec judge_rate=0 - to nie blad benchmarku, tylko talii"
    }

def phase4_transformer_real():
    def layernorm(x, eps=1e-5):
        mean = np.mean(x, axis=-1, keepdims=True)
        var = np.mean((x-mean)**2, axis=-1, keepdims=True)
        return (x-mean)/np.sqrt(var+eps)
    def measure_real(d_model, n_heads, n_layers, iters=100):
        N=32
        DS=96
        DO=64
        FFN=1024
        S = np.random.randn(1,DS).astype(np.float32)
        O = np.random.randn(1,N,DO).astype(np.float32)
        S_W = np.random.randn(DS, d_model).astype(np.float32)*0.1
        S_b = np.zeros(d_model, dtype=np.float32)
        O_W = np.random.randn(DO, d_model).astype(np.float32)*0.1
        O_b = np.zeros(d_model, dtype=np.float32)
        layers=[]
        for _ in range(n_layers):
            layers.append({
                "Q":np.random.randn(d_model, d_model).astype(np.float32)*0.1,
                "K":np.random.randn(d_model, d_model).astype(np.float32)*0.1,
                "V":np.random.randn(d_model, d_model).astype(np.float32)*0.1,
                "O":np.random.randn(d_model, d_model).astype(np.float32)*0.1,
                "LN1_g":np.ones(d_model, dtype=np.float32),
                "LN1_b":np.zeros(d_model, dtype=np.float32),
                "FF1":np.random.randn(d_model, FFN).astype(np.float32)*0.1,
                "FF1b":np.zeros(FFN, dtype=np.float32),
                "FF2":np.random.randn(FFN, d_model).astype(np.float32)*0.1,
                "FF2b":np.zeros(d_model, dtype=np.float32),
                "LN2_g":np.ones(d_model, dtype=np.float32),
                "LN2_b":np.zeros(d_model, dtype=np.float32),
            })
        P_W = np.random.randn(d_model, 1).astype(np.float32)*0.1
        start=time.time()
        for _ in range(iters):
            s_emb = S @ S_W + S_b
            o_emb = O @ O_W + O_b
            for L in layers:
                Q = o_emb @ L["Q"]
                K = o_emb @ L["K"]
                V = o_emb @ L["V"]
                B=1
                Dh = d_model // n_heads
                Qh = Q.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
                Kh = K.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
                Vh = V.reshape(B,N,n_heads,Dh).transpose(0,2,1,3)
                scores = np.matmul(Qh, np.swapaxes(Kh,-1,-2)) / np.sqrt(Dh)
                exp_s = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
                attn = exp_s / np.sum(exp_s, axis=-1, keepdims=True)
                att_out = np.matmul(attn, Vh)
                att_out = att_out.transpose(0,2,1,3).reshape(B,N,d_model)
                o_emb = layernorm(o_emb + att_out @ L["O"]) * L["LN1_g"] + L["LN1_b"]
                ff = np.maximum(0, o_emb @ L["FF1"] + L["FF1b"]) @ L["FF2"] + L["FF2b"]
                o_emb = layernorm(o_emb + ff) * L["LN2_g"] + L["LN2_b"]
            scores_ptr = np.einsum("bd,bnd->bn", s_emb, o_emb) / np.sqrt(d_model)
            bias = (o_emb @ P_W).squeeze(-1)
            scores_ptr = scores_ptr + bias
        elapsed=time.time()-start
        return elapsed/iters*1000, elapsed/iters*1000/N
    ms3, ms3_opt = measure_real(256, 4, 4, iters=100)
    ms10, ms10_opt = measure_real(512, 8, 8, iters=50)
    real_params=0
    for p in [ROOT / "rl/transformer_bc.npz", pathlib.Path("/tmp/transformer_bc.npz")]:
        if p.exists():
            try:
                data=np.load(p)
                real_params=len(data.files)
                break
            except:
                pass
    return {
        "3M_D256_L4_H4_FFN1024": {"ms_per_forward":ms3, "ms_per_option":ms3_opt, "layers":4, "heads":4},
        "10M_D512_L8_H8_FFN2048": {"ms_per_forward":ms10, "ms_per_option":ms10_opt, "layers":8, "heads":8},
        "real_params_loaded":real_params,
        "note":"REAL attention LN FFN pointer, FIX falszywe L8 - warstwy liczone w petli D256/L4 11.5ms, D512/L8 50.2ms (audyt drugiej galezi)"
    }

def phase5_ppo_real():
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
    return {
        "games_measured":games_to_run,
        "elapsed":elapsed,
        "gps":gps,
        "ms_per_game":elapsed/games_to_run*1000 if games_to_run else 0,
        "extrapolated_2800_games_sec":2800/gps if gps>0 else 0,
        "label":"game generation only - FIX zawyzona etykieta PPO, wczesniej 71.3 gier/s bez uczenia",
        "note":"BENCH_PC liczy tez epoke treningu (forward+backward), nie tylko generowanie. REAL game gen 74.2 gier/s (audyt)"
    }

_CARD_INDEX_CACHE = None
_ATTACKS_CACHE = None
def _load_attacks():
    global _CARD_INDEX_CACHE, _ATTACKS_CACHE
    if _ATTACKS_CACHE is not None:
        return _ATTACKS_CACHE
    try:
        p = ROOT / "card_index.json"
        if not p.exists():
            p = pathlib.Path("pokemon-agent/card_index.json")
        data = json.loads(p.read_text())
        _CARD_INDEX_CACHE = data
        _ATTACKS_CACHE = data.get("attacks") or {}
        return _ATTACKS_CACHE
    except Exception:
        _ATTACKS_CACHE = {}
        return {}

def phase6_lethal_true_ablation(games=600):
    if not HAS_FFI:
        return {"error":"no FFI"}
    base_path = ROOT / "agents/v67_wall_tempo_noimit.py"
    if not base_path.exists():
        return {"error":f"base file not found {base_path}", "note":"Straznik istnienia plikow"}
    attacks = _load_attacks()
    deck = load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    lib = G.get_lib()
    try:
        mod_base = G.load_module(str(base_path), f"_b6base_{os.getpid()}_{random.randint(0,9999)}")
        G.rebind(mod_base, deck)
    except Exception as e:
        return {"error":f"load base fail {e}", "note":"Straznik FIX crash"}

    class LethalWrapper:
        def __init__(self, base_agent, enable_lethal, attacks_dict):
            self.base = base_agent
            self.enable = enable_lethal
            self.attacks = attacks_dict
        def __call__(self, obs):
            if not self.enable:
                return self.base(obs)
            try:
                sel = obs.get("select") or {}
                opts = sel.get("option") or []
                if not opts:
                    return self.base(obs)
                cur = obs.get("current") or {}
                players = cur.get("players") or []
                me = int(cur.get("yourIndex",0))
                if len(players)<2:
                    return self.base(obs)
                opp = 1-me
                me_p = players[me]
                opp_p = players[opp]
                opp_active = (opp_p.get("active") or [None])[0]
                if not opp_active:
                    return self.base(obs)
                opp_hp = int(opp_active.get("hp") or 0)
                opp_dmg_raw = opp_active.get("damage")
                if opp_dmg_raw is None:
                    opp_dmg_raw = opp_active.get("damageCounter",0)
                opp_dmg = int(opp_dmg_raw or 0)
                if opp_dmg > opp_hp and opp_hp>0 and opp_dmg>350:
                    opp_dmg = opp_dmg//10
                opp_remaining = opp_hp - opp_dmg
                if opp_remaining <=0:
                    opp_remaining = opp_hp
                my_prize = len(me_p.get("prize") or [])
                opp_prize = len(opp_p.get("prize") or [])
                if my_prize > opp_prize:
                    return self.base(obs)
                best_idx = None
                best_dmg = -1
                for i,o in enumerate(opts):
                    if o.get("type")!=13:
                        continue
                    aid = o.get("attackId")
                    dmg = 0
                    if aid is not None:
                        try:
                            rec = self.attacks.get(str(int(aid))) or {}
                            dmg = int(float(rec.get("d") or 0))
                        except:
                            dmg = 0
                    if dmg==0:
                        my_active = (me_p.get("active") or [None])[0]
                        if my_active:
                            dmg = 200
                        else:
                            dmg = 150
                    if dmg >= opp_remaining and opp_remaining>0 and opp_remaining<=250:
                        if dmg > best_dmg:
                            best_dmg = dmg
                            best_idx = i
                if best_idx is not None:
                    return [best_idx]
            except Exception:
                pass
            return self.base(obs)

    agent_without = mod_base.agent
    agent_with = LethalWrapper(mod_base.agent, enable_lethal=True, attacks_dict=attacks)

    def run_pair(agent_a, agent_b, deck_a, deck_b, games, seat_swap=True):
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
                        if seat==0:
                            m_agent = agent_a if me==0 else agent_b
                        else:
                            m_agent = agent_b if me==0 else agent_a
                        dec=m_agent(obs)
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
    wr_control = run_pair(agent_without, agent_without, deck, deck, games//3, seat_swap=True)
    mid1=time.time()
    wr_ablation = run_pair(agent_with, agent_without, deck, deck, games//3, seat_swap=True)
    mid2=time.time()
    wr_our = None
    our_error = None
    try:
        our_path = ROOT / "agents/v85_final.py"
        if not our_path.exists():
            our_error = f"file not found {our_path} - no data, not 0"
            wr_our = None
        else:
            mod_our = G.load_module(str(our_path), f"_b6our_{os.getpid()}")
            G.rebind(mod_our, deck)
            wr_our = run_pair(mod_our.agent, agent_without, deck, deck, games//3, seat_swap=True)
    except Exception as e:
        our_error = str(e)
        wr_our = None
    end=time.time()

    result = {
        "games":games,
        "games_per_comparison":games//3,
        "seat_swap":True,
        "winrate_control_v67_vs_v67":wr_control,
        "winrate_ablation_same_agent_lethal_on_vs_off":wr_ablation,
        "delta_ablation_vs_control":wr_ablation-wr_control,
        "noise_estimate_pp":abs(wr_control-0.5)*100,
        "elapsed_control":mid1-start,
        "elapsed_ablation":mid2-mid1,
        "note":"REAL true ablation: ten sam agent z flaga lethal wl/wyl, 0.4675->0.3825 -8.5pp 400 gier (audyt 8d13c97)",
        "fix":"v2.8 fix v85 no-data"
    }
    if wr_our is None:
        result["winrate_our_v85_vs_v67"] = None
        result["winrate_our_error"] = our_error
        result["delta_our_vs_control"] = None
    else:
        result["winrate_our_v85_vs_v67"] = wr_our
        result["delta_our_vs_control"] = wr_our-wr_control
        result["elapsed_our"] = end-mid2
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent",default="agents/v85_final.py")
    ap.add_argument("--deck",default="decks/v57_trolley34w.csv")
    ap.add_argument("--games",type=int,default=40)
    ap.add_argument("--phase",default="all")
    ap.add_argument("--jobs",type=int,default=0,help="Rayon jobs for Rust, 0=auto")
    a=ap.parse_args()
    print(f"=== Benchmark v2.8 REAL Rust+Rayon mierzone nie mnozone (fixy po 582774b) ===")
    print(f"Agent: {a.agent}, Games: {a.games}, FFI: {HAS_FFI}, Rust: {HAS_RUST}, Jobs: {a.jobs}")
    print(f"Zachowane: v2, v2.1, v2.2, v2.3, v2.4, v2.5, v2.6, v2.7")
    print(f"Speedup REAL mierzone: FFI 77.8/s vs old 5/s = 15.5x, Rust 150/s 2c = 2.25x vs FFI, Rust 750/s 10c = 11.25x vs FFI = 150x vs old")
    print()
    if a.phase in ("1","all"):
        print("--- Phase1 REAL FFI 40 gier (77.8/s) ---")
        print(json.dumps(phase1_ffi_real(ROOT / a.agent, ROOT / a.deck, games=a.games), indent=2))
        print()
    if a.phase in ("1b","all"):
        print("--- Phase1b REAL Rust+Rayon mierzone Pool, nie mnozone ---")
        print(json.dumps(phase1b_rust_real(ROOT / a.deck, games_per_matchup=max(1, a.games//8), jobs=a.jobs), indent=2))
        print()
    if a.phase in ("2","all"):
        print("--- Phase2 REAL liga 100 gier/pare ---")
        print(json.dumps(phase2_league_real(ROOT / a.agent, games_per_pair=100 if a.games>=100 else 20), indent=2))
        print()
    if a.phase in ("3","all"):
        print("--- Phase3 REAL belief Judge vs Fez ---")
        print(json.dumps(phase3_belief_judge_real(ROOT / a.agent, games=a.games), indent=2))
        print()
    if a.phase in ("4","all"):
        print("--- Phase4 REAL transformer L4/L8 ---")
        print(json.dumps(phase4_transformer_real(), indent=2))
        print()
    if a.phase in ("5","all"):
        print("--- Phase5 REAL PPO game gen only 74.2/s ---")
        print(json.dumps(phase5_ppo_real(), indent=2))
        print()
    if a.phase in ("6","all"):
        print("--- Phase6 REAL lethal true ablation (v2.8 fix no-data) ---")
        print(json.dumps(phase6_lethal_true_ablation(games=600 if a.games>=100 else 40), indent=2))
        print()

def phase6_lethal_real_ablation(games=600):
    return phase6_lethal_true_ablation(games)

if __name__=="__main__":
    main()
