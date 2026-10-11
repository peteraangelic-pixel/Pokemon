#!/usr/bin/env python3
"""gen8 evolution: tempo-aware config search for the PTCG heuristic agent.

Sandbox-iteration tool (fast path). The permanent Rust+Rayon port lives in
rust/src/bin/evolve_tempo.rs (built & verified on GitHub Actions).

Architecture (same root-cause rules as tools/gauntlet_ffi.py):
- NO `import kaggle_environments` anywhere (auto-init -> 'buffer full.
  capacity:7' abort). Direct FFI into libcg.so, GameInitialize once per
  worker process.
- Agent policy runs IN-PROCESS (fresh exec_module per candidate config,
  PTCG_* env vars set before import — the agent reads them via setdefault).
- Both seats alternate; opponent = same policy, different deck.

Fitness = 0.65*weighted_winrate + 0.20*prize_pace_by_T9 + 0.15*early_first_prize
(tempo terms are the new lever vs gen6; winrate stays dominant).

Usage:
  .venv/bin/python tools/evolve_gen8.py [--gens 4] [--pop 80] [--games 30]
    [--workers 8] [--seed 7] [--out search_results/gen8.json]
"""
from __future__ import annotations
import argparse, ctypes, importlib.util, json, os, random, sys, time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---------- libcg.so (no kaggle_environments import!) ----------
def _find_lib() -> Path:
    cands = [ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"]
    try:
        import sysconfig
        cands.append(Path(sysconfig.get_paths()["purelib"]) / "kaggle_environments/envs/cabt/cg/libcg.so")
    except Exception:
        pass
    for c in cands:
        if c.exists():
            return c
    raise SystemExit("libcg.so not found — `bash setup.sh`")

LIB = _find_lib()

class _SD(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]

class _RD(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)),
                ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

_lib = None
def get_lib():
    global _lib
    if _lib is None:
        lib = ctypes.cdll.LoadLibrary(str(LIB))
        lib.GameInitialize()
        lib.BattleStart.restype = _SD
        lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.BattleFinish.argtypes = [ctypes.c_void_p]
        lib.GetBattleData.restype = _RD
        lib.GetBattleData.argtypes = [ctypes.c_void_p]
        lib.Select.restype = ctypes.c_int
        lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        _lib = lib
    return _lib

# ---------- decks / agent ----------
def load_deck(p: Path):
    return [int(x) for x in Path(p).read_text().replace(",", " ").split() if x]

_mod_cache: dict[str, object] = {}
def load_agent_cached(agent_path: Path, config: dict, tag: str):
    key = f"{agent_path.name}:{json.dumps(config, sort_keys=True)}:{tag}"
    if key in _mod_cache:
        return _mod_cache[key]
    for k in config:
        os.environ[k] = str(config[k])
    name = f"evo_{tag}_{abs(hash(key)) % 10**8}"
    spec = importlib.util.spec_from_file_location(name, str(agent_path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    _mod_cache[key] = m
    return m

def make_fn(mod, deck):
    try:
        mod.DECK = list(deck)
        if hasattr(mod, "_build_plan"):
            mod.PLAN = mod._build_plan(mod.DECK)
    except Exception:
        pass
    def fn(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return fn

# ---------- one game with tempo tracking ----------
def play_game(lib, fA, fB, deckA, deckB, seat_a):
    d0, d1 = (deckA, deckB) if seat_a == 0 else (deckB, deckA)
    cards = (ctypes.c_int * 120)(*d0, *d1)
    bp = lib.BattleStart(cards).battlePtr
    if not bp:
        return None
    fn0, fn1 = (fA, fB) if seat_a == 0 else (fB, fA)
    res = 0
    first_prize_turn = None
    prizes_t9 = 0
    last_turn = 0
    steps = 0
    try:
        while True:
            steps += 1
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            t = cur.get("turn") or 0
            last_turn = max(last_turn, t)
            r = cur.get("result")
            if r is not None and r >= 0:
                res = 0 if r == 2 else (1 if r == seat_a else -1)
                break
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            pl = cur.get("players") or []
            if me < len(pl) and pl[me]:
                plz = pl[me].get("prize")
                taken = (6 - len(plz)) if plz else 0  # empty list = pre-setup, not 6 taken
                if taken > 0:
                    if first_prize_turn is None:
                        first_prize_turn = t
                    if t <= 9:
                        prizes_t9 = max(prizes_t9, taken)
            dec = fA(obs) if me == seat_a else fB(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
            if steps > 5000:
                break
    finally:
        lib.BattleFinish(bp)
    return dict(win=(res == 1), fp=first_prize_turn, t9=prizes_t9, turns=last_turn)

# ---------- worker ----------
_W = {}
def _init_worker(agent_path, our_deck, opp_decks, games):
    _W["lib"] = get_lib()
    _W["agent_path"] = Path(agent_path)
    _W["our_deck"] = our_deck
    _W["opp_decks"] = opp_decks
    _W["games"] = games

def _eval_candidate(job):
    idx, config, tag = job
    lib = _W["lib"]
    mod = load_agent_cached(_W["agent_path"], config, tag)
    fA = make_fn(mod, _W["our_deck"])
    out = {"idx": idx, "config": config, "per_deck": {}, "agg": {}}
    allw = al = 0
    t9s, fps, turnss = [], [], []
    for di, (name, deck) in enumerate(_W["opp_decks"]):
        fB = make_fn(mod, deck)
        w = l = 0
        for g in range(_W["games"]):
            r = play_game(lib, fA, fB, _W["our_deck"], deck, g % 2)
            if r is None:
                l += 1
                continue
            if r["win"]:
                w += 1
            else:
                l += 1
            t9s.append(r["t9"])
            if r["fp"] is not None:
                fps.append(r["fp"])
            turnss.append(r["turns"])
            allw += 1 if r["win"] else 0
            al += 1
        out["per_deck"][name] = [w, l]
    n = max(1, allw + al)
    out["agg"] = {
        "winrate": allw / n,
        "t9": sum(t9s) / max(1, len(t9s)),
        "fp": sum(fps) / max(1, len(fps)),
        "turns": sum(turnss) / max(1, len(turnss)),
        "games": n,
    }
    return out

def _map_chunk(chunk):
    return [_eval_candidate(j) for j in chunk]

# ---------- pool setup ----------
def build_pool(args):
    opp = []
    def add_dir(d, weight, prefix=""):
        for f in sorted(Path(d).glob("*.csv")):
            if f.name.startswith("_"):
                continue
            opp.append((f"{prefix}{f.stem}", load_deck(f), weight))
    add_dir(args.loss_dir, 3)
    for d in args.meta_decks.split(","):
        if d.strip():
            p = ROOT / "decks/top30_live" / f"{d.strip()}.csv"
            opp.append((f"meta:{d.strip()}", load_deck(p), 2))
    add_dir(args.weak_dir, 1, "weak:")
    seen, out = set(), []
    for name, deck, w in opp:
        k = tuple(deck)
        if k in seen:
            continue
        seen.add(k)
        out.append((name, deck, w))
    return out

def fitness(res, weights):
    wr, t9, fp = res["agg"]["winrate"], res["agg"]["t9"], res["agg"]["fp"]
    wsum = 0.0
    wwr = 0.0
    for name, (w, l) in res["per_deck"].items():
        wt = weights.get(name, 1)
        wwr += wt * w
        wsum += wt * (w + l)
    wwr = wwr / max(1.0, wsum)
    t9n = min(1.0, t9 / 2.0)
    fpn = max(0.0, min(1.0, (10.0 - fp) / 4.0))
    return 0.65 * wwr + 0.20 * t9n + 0.15 * fpn, wwr

def mutate(base, sigma, rng):
    c = {}
    for k, v in base.items():
        c[k] = int(round(v * (1.0 + rng.gauss(0.0, sigma))))
    return c

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=str(ROOT / "agents/main_heuristic_v11.py"))
    ap.add_argument("--our-deck", default=str(ROOT / "decks/v12_30_boss4.csv"))
    ap.add_argument("--loss-dir", default=str(ROOT / "decks/v14_losses"))
    ap.add_argument("--meta-decks", default="YumeNeko,OceanMix,Kentaro_Totsuka,ANMOL_GARG,Leon_Liu,Darren_Sheehan")
    ap.add_argument("--weak-dir", default=str(ROOT / "decks/weak_field"))
    ap.add_argument("--games", type=int, default=30, help="games per matchup (both seats)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--pop", type=int, default=80)
    ap.add_argument("--gens", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "search_results/gen8.json"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool = build_pool(args)
    weights = {name: w for name, _, w in pool}
    opp_decks = [(name, deck) for name, deck, _ in pool]
    our_deck = load_deck(Path(args.our_deck))

    import re
    txt = Path(args.agent).read_text()
    base = {}
    for m in re.finditer(r'setdefault\("PTCG_(\w+)", "(-?\d+)"\)', txt):
        base[m.group(1)] = int(m.group(2))
    print(f"pool: {len(pool)} decks, {len(pool)*args.games} games/candidate, base {len(base)} keys", flush=True)
    print("base config:", json.dumps(base, sort_keys=True), flush=True)

    best = None
    history = []
    pop = [base] + [mutate(base, 0.08, rng) for _ in range(args.pop - 1)]
    for g in range(args.gens):
        sigma = [0.08, 0.04, 0.02, 0.01][min(g, 3)]
        nsel = [15, 10, 6, 6][min(g, 3)]
        print(f"\n=== gen {g} ({len(pop)} candidates) ===", flush=True)
        t0 = time.time()
        jobs = [(i, c, f"g{g}") for i, c in enumerate(pop)]
        order = list(range(len(jobs)))
        rng.shuffle(order)
        jobs = [jobs[i] for i in order]
        with Pool(args.workers, initializer=_init_worker,
                  initargs=(args.agent, our_deck, opp_decks, args.games)) as p:
            res = [r for chunk in p.map(_map_chunk, [jobs[i::args.workers] for i in range(args.workers)]) for r in chunk]
        for r in res:
            f, wwr = fitness(r, weights)
            r["fitness"] = f
            r["wwr"] = wwr
        res.sort(key=lambda r: -r["fitness"])
        for r in res[:5]:
            a = r["agg"]
            diff = {k: v for k, v in sorted(r["config"].items()) if v != base.get(k)}
            print(f"  f={r['fitness']:.4f} wwr={r['wwr']:.3f} wr={a['winrate']:.3f} "
                  f"t9={a['t9']:.2f} fp={a['fp']:.1f} d={diff}", flush=True)
        history.append({"gen": g, "top": [{"config": r["config"], "fitness": r["fitness"], "agg": r["agg"]} for r in res[:10]]})
        if best is None or res[0]["fitness"] > best["fitness"]:
            best = res[0]
        elites = [r["config"] for r in res[:nsel]]
        per_elite = max(1, (args.pop - 1) // max(1, len(elites)))
        nxt = [base]
        for e in elites:
            for _ in range(per_elite):
                nxt.append(mutate(e, sigma, rng))
        nxt = nxt[:args.pop]
        pop = nxt
        print(f"gen {g} done in {time.time()-t0:.0f}s", flush=True)

    print("\nBEST:", flush=True)
    print(json.dumps({"config": best["config"], "fitness": best["fitness"], "agg": best["agg"]}, indent=1), flush=True)
    out = Path(args.out)
    out.write_text(json.dumps({"base": base, "best": best, "history": history}, indent=1))
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
