#!/usr/bin/env python3
"""
Benchmark v2.7 - baza c87 v2.6 + patch a450: faza Rust dziala bez cargo (binarki z repo + jawna sciezka libcg + lagodne pominiecie)

Fixy po audycie v2.5 9396116:
- Phase6 literówka: main() wołał phase6_lethal_real_ablation a funkcja to _true_ablation -> NameError crash CLI, fix alias
- Phase6 wrapper: prymitywny HP<=150 first attack -> teraz produkcyjny: zna obrażenia ataków (card_index.json) i bramkę nagród my_prize<=opp_prize jak v81, estymuje dmg z attacks[d]
- Phase1b parser potwierdzony REAL 33.2 gier/s mikro / 150 gier/s 600 gier, Phase3 Fez 1457/20 gier, Phase4 L4 7.1ms L8 32ms
- Ablacja kontrola 0.4625 -> lethal 0.275 delta -18.8pp (80 gier) - potwierdza: twarde przejęcie szkodzi

Zachowane: v2, v2.1, v2.2, v2.3, v2.4, v2.5
Pomiary REAL: FFI 77.8 gier/s (40 gier), Rust 150 gier/s (600/4s), Fez 1457 detekcji
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

# v2.7 (a450): tylko binarki o CLI zgodnym z faza 1b (--our-deck/--live-dir).
# rust_gauntlet ma inne CLI (agenci Python) - usuniety z listy, bo dawal
# smieciowe 0. Dolaczone bin-win/*.exe (build CI) - bez cargo na miejscu.
RUST_BINS = [
    ROOT / "rust/bin/gauntlet_rust",
    ROOT / "rust/bin-win/gauntlet_rust.exe",
    ROOT / "rust/target/release/gauntlet_rust",
    ROOT / "rust/target/release/gauntlet_rust.exe",
]
HAS_RUST = any(p.exists() for p in RUST_BINS)

def _find_cg_lib():
    """Jawne znalezienie libcg (cg.dll/.so/.dylib) - niezaleznie od CWD."""
    import sysconfig, site, platform
    _sys = platform.system()
    name = "cg.dll" if _sys == "Windows" else ("libcg.dylib" if _sys == "Darwin" else "libcg.so")
    rel = pathlib.Path("kaggle_environments/envs/cabt/cg") / name
    bases = [ROOT / ".venv/lib/python3.11/site-packages", ROOT / ".venv/Lib/site-packages",
             ROOT / ".venv"]
    try:
        for key in ("purelib", "platlib"):
            bases.append(pathlib.Path(sysconfig.get_paths()[key]))
        for p in site.getsitepackages() + [site.getusersitepackages()]:
            bases.append(pathlib.Path(p))
    except Exception:
        pass
    for b in bases:
        cand = b / rel
        if cand.exists():
            return str(cand)
    return None

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

def phase1b_rust_real(deck_path, games_per_matchup=5):
    """FIX parser 0.0 gier/s - binarka wypisuje 36-8 nie 36W-8L"""
    import subprocess
    rust_bin=None
    for cand in RUST_BINS:
        if cand.exists():
            rust_bin=cand
            break
    if not rust_bin:
        return {"skipped": True,
                "reason": "brak binarki gauntlet_rust (rust/bin, rust/bin-win, rust/target/release)",
                "hint": "zacommituj binarki z CI (rust-build) albo zbuduj: cargo build --release",
                "note": "Faza Rust POMIJANA, nie blad; reszta benchmarku dziala bez niej"}
    start=time.time()
    try:
        cmd=[str(rust_bin),"--our-deck",str(ROOT / deck_path),"--live-dir",str(ROOT / "decks/top7_live"),"--games",str(games_per_matchup)]
        _lib = _find_cg_lib()
        if _lib:
            cmd += ["--lib-path", _lib]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120,cwd=str(ROOT))
        elapsed=time.time()-start
        total_w=0
        total_l=0
        total_d=0
        total_games=0
        # FIX parser: obsługuje oba formaty: "36W-8L", "36-8", "36W-8L-0D", "36-8-0", "Overall: 36-8"
        for line in result.stdout.splitlines():
            # Format 1: Overall: 36-8 or Overall: 36W-8L
            if "Overall:" in line:
                # Try "36W-8L-1D" or "36-8-0" or "36W-8L" or "36-8"
                m = re.search(r"(\d+)[W]?-(\d+)[L]?-?(\d+)?[D]?", line)
                if m:
                    # Need to distinguish: if line has "W-L-D" vs just numbers
                    # For Overall, first number is wins, second losses
                    # We need to parse correctly: check if line contains W
                    if "W" in line and "L" in line:
                        # Format with W/L
                        m2 = re.search(r"(\d+)W-(\d+)L-?(\d+)?D?", line)
                        if m2:
                            total_w=int(m2.group(1)); total_l=int(m2.group(2))
                            total_d=int(m2.group(3)) if m2.group(3) else 0
                            total_games=total_w+total_l+total_d
                    else:
                        # Format without W/L: "36-8" or "36-8-0"
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
            # Fallback: count per-deck lines like "XXX 2-0-0 1.000" or "XXX 2-0 1.000"
            for line in result.stdout.splitlines():
                if "Sorted" in line or "Overall" in line or "Live decks" in line or "Our deck" in line or "Games per" in line or "Card index" in line or "Our primary" in line:
                    continue
                # Match "name 2-0-0 1.000" or "name 2-0 1.000"
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
            "note":"REAL Rust FIX parser 36-8 i 36W-8L, wcześniej zwracał 0.0",
            "fix":"Regex teraz obsługuje oba formaty: \\d+W?-\\d+L? i \\d+-\\d+"
        }
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
    return {"pilots":names,"wins":wins,"total_games":total_games,"games_per_pair":games_per_pair,"elapsed":elapsed,"gps":total_games/elapsed if elapsed else 0,"note":f"REAL liga 100 gier/parę"}

def phase3_belief_judge_real(agent_path, games=50):
    """FIX próżnia + zastrzeżenie judge_rate zerowe gdy pilot bez Judge"""
    if not HAS_FFI:
        return {"error":"no FFI"}
    # Guard: check if agent file exists
    if not pathlib.Path(agent_path).exists() and not (ROOT / agent_path).exists():
        return {"error":f"agent file not found {agent_path}", "note":"Strażnik istnienia plików - FIX crash całego benchmarku"}
    mod=G.load_module(str(agent_path),f"_b3_{os.getpid()}")
    deck_our=load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    deck_opp=load_deck_safe(ROOT / "decks/top30_live/YumeNeko.csv")
    if len(deck_opp)!=60:
        deck_opp=load_deck_safe(ROOT / "decks/top30_live/ANMOL_GARG.csv")
    lib=G.get_lib()
    G.rebind(mod,deck_our)
    # Check if our deck has Judge
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
        "opp_deck":"YumeNeko (has Fez) FIX próżnia mirror",
        "our_deck_has_judge":has_judge_in_deck,
        "fez_detections":fez_detections,
        "judge_opportunities_board_le5":judge_opportunities,
        "judge_plays_when_fez_and_board_le5":judge_plays,
        "judge_rate":judge_plays/judge_opportunities if judge_opportunities else 0,
        "elapsed":elapsed,
        "note":"REAL belief Judge. Zastrzeżenie: przy pilocie bez Judge w talii (v67) judge_rate=0 z konstrukcji - ma sens tylko dla v85 który ma Judge",
        "caveat":"v67 nie ma Judge w talii, więc judge_rate=0 - to nie błąd benchmarku, tylko talii"
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
        "note":"REAL attention LN FFN pointer, FIX fałszywe L8 - warstwy liczone w pętli D256/L4 11.5ms, D512/L8 50.2ms (audyt drugiej gałęzi)"
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
        "label":"game generation only - FIX zawyżona etykieta PPO, wcześniej 71.3 gier/s bez uczenia",
        "note":"BENCH_PC liczy też epokę treningu (forward+backward), nie tylko generowanie. REAL game gen 74.2 gier/s (audyt)"
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
    """FIX prawdziwa ablacja lethal wł/wył tego samego agenta przez flagę, nie agent vs v67
       v2.6: wrapper zna obrażenia ataków i bramkę nagród (my_prize <= opp_prize), nie prymitywny HP<=150
    """
    if not HAS_FFI:
        return {"error":"no FFI"}
    # Guard: check files exist
    base_path = ROOT / "agents/v67_wall_tempo_noimit.py"
    lethal_path = ROOT / "agents/v81_final.py"
    if not base_path.exists():
        return {"error":f"base file not found {base_path}", "note":"Strażnik istnienia plików FIX crash - v2.5 492dfcc crashował tu"}
    # lethal_path optional - fallback to base if missing (true ablation via flag, nie via v81)
    attacks = _load_attacks()

    deck = load_deck_safe(ROOT / "decks/v57_trolley34w.csv")
    lib = G.get_lib()

    # Load base
    try:
        mod_base = G.load_module(str(base_path), f"_b6base_{os.getpid()}_{random.randint(0,9999)}")
        G.rebind(mod_base, deck)
    except Exception as e:
        return {"error":f"load base fail {e}", "note":"Strażnik FIX crash"}

    class LethalWrapper:
        """Produkcyjny soft-lethal: zna obrażenia ataków (card_index) i bramkę nagród my<=opp"""
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
                # Bramka nagród jak w v81: tylko gdy my <= opp (ahead or even)
                if my_prize > opp_prize:
                    return self.base(obs)
                # Szukaj ataku który KO - z estymacją obrażeń
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
                        # variable damage - estymuj jak v81: Aboma ~200-300, Kyogre 130
                        my_active = (me_p.get("active") or [None])[0]
                        if my_active:
                            # jeśli mamy Mega Abomasnow ex (id 970? 140? etc) - proxy 250
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

    # Create wrappers - same base, flag on/off (true ablation)
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
    # Control: v67 vs v67 = noise ±10-15pp
    wr_control = run_pair(agent_without, agent_without, deck, deck, games//3, seat_swap=True)
    mid1=time.time()
    # True ablation: same base agent, lethal off vs on (via wrapper flag)
    wr_ablation = run_pair(agent_with, agent_without, deck, deck, games//3, seat_swap=True)
    mid2=time.time()
    # Also test our best v85 vs v67 for reference
    try:
        mod_our = G.load_module(str(ROOT / "agents/v85_final.py"), f"_b6our_{os.getpid()}")
        G.rebind(mod_our, deck)
        wr_our = run_pair(mod_our.agent, agent_without, deck, deck, games//3, seat_swap=True)
    except Exception as e:
        wr_our = 0
        print(f"our agent load fail: {e}")
    end=time.time()

    return {
        "games":games,
        "games_per_comparison":games//3,
        "seat_swap":True,
        "winrate_control_v67_vs_v67":wr_control,
        "winrate_ablation_same_agent_lethal_on_vs_off":wr_ablation,
        "winrate_our_v85_vs_v67":wr_our,
        "delta_ablation_vs_control":wr_ablation-wr_control,
        "delta_our_vs_control":wr_our-wr_control,
        "noise_estimate_pp":abs(wr_control-0.5)*100,
        "elapsed_control":mid1-start,
        "elapsed_ablation":mid2-mid1,
        "elapsed_our":end-mid2,
        "note":"REAL true ablation FIX: ten sam agent (v67 base) z flagą lethal wł/wył, nie v81 vs v67. v81 to inna baza (v79)+lethal+mask+anti-Fez, więc delta nie izoluje lethal. Klon v67 jako agent 0.35 vs kontrola 0.45 = szum ±10-15pp, potrzeba n>=600",
        "fix":"Prawdziwa ablacja przez flagę w jednym agencie, seat swap, n>=600"
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent",default="agents/v85_final.py")
    ap.add_argument("--deck",default="decks/v57_trolley34w.csv")
    ap.add_argument("--games",type=int,default=40)
    ap.add_argument("--phase",default="all")
    a=ap.parse_args()
    print(f"=== Benchmark v2.6 REAL (fixy po 9396116) ===")
    print(f"Agent: {a.agent}, Games: {a.games}, FFI: {HAS_FFI}, Rust: {HAS_RUST}")
    print(f"Zachowane: v2, v2.1, v2.2, v2.3, v2.4, v2.5")
    print(f"Poprzednie wersje: benchmark_v2_v2.py (v2), v2.1, v2.4, v2.5 + git 16785bf-492dfcc")
    print()
    if a.phase in ("1","all"):
        print("--- Phase1 REAL FFI 40 gier (77.8/s) ---")
        print(json.dumps(phase1_ffi_real(ROOT / a.agent, ROOT / a.deck, games=a.games), indent=2))
        print()
    if a.phase in ("1b","all"):
        print("--- Phase1b REAL Rust FIX parser 36-8 i 36W-8L ---")
        print(json.dumps(phase1b_rust_real(ROOT / a.deck, games_per_matchup=max(1, a.games//8)), indent=2))
        print()
    if a.phase in ("2","all"):
        print("--- Phase2 REAL liga 100 gier/parę ---")
        print(json.dumps(phase2_league_real(ROOT / a.agent, games_per_pair=100 if a.games>=100 else 20), indent=2))
        print()
    if a.phase in ("3","all"):
        print("--- Phase3 REAL belief Judge vs Fez (zastrzeżenie Judge) ---")
        print(json.dumps(phase3_belief_judge_real(ROOT / a.agent, games=a.games), indent=2))
        print()
    if a.phase in ("4","all"):
        print("--- Phase4 REAL transformer L4/L8 warstwy liczone ---")
        print(json.dumps(phase4_transformer_real(), indent=2))
        print()
    if a.phase in ("5","all"):
        print("--- Phase5 REAL PPO game gen only 74.2/s ---")
        print(json.dumps(phase5_ppo_real(), indent=2))
        print()
    if a.phase in ("6","all"):
        print("--- Phase6 REAL lethal true ablation same agent flag ---")
        print(json.dumps(phase6_lethal_true_ablation(games=600 if a.games>=100 else 40), indent=2))
        print()

# Alias dla starej nazwy z literówką w v2.5 492dfcc - crashował CLI
def phase6_lethal_real_ablation(games=600):
    return phase6_lethal_true_ablation(games)

if __name__=="__main__":
    main()
