#!/usr/bin/env python3
"""Eval worker for the Rust evolve_tempo orchestrator (rust/src/bin/evolve_tempo.rs).

One process = one candidate config. The parent sets PTCG_* env vars; this
process drives libcg.so via direct FFI (NO `import kaggle_environments` —
auto-init would abort with 'buffer full. capacity:7'), plays the full pool
with the real agent in-process, and prints ONE JSON summary on stdout:

  {"per_deck": {name: [w, l]}, "t9": f, "fp": f, "turns": f, "games": n}

t9 = mean prizes taken by turn 9; fp = mean turn of first prize (our seat).

Usage (normally launched by evolve_tempo):
  PTCG_ATTACH=... python3 rust/worker_eval.py --agent agents/main_heuristic_v11.py \
      --our-deck decks/v12_30_boss4.csv --repo . --pool evolve_pool.json --games 30
"""
from __future__ import annotations
import argparse, ctypes, importlib.util, json, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--our-deck", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--games", type=int, default=30)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    rel = "lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"
    lib_path = None
    for root in (repo, repo.parent, repo / "Pokemon/pokemon-agent", Path.cwd()):
        cand = root / ".venv" / rel
        if cand.exists():
            lib_path = cand
            break
    if lib_path is None:
        import sysconfig
        lib_path = Path(sysconfig.get_paths()["purelib"]) / "kaggle_environments/envs/cabt/cg/libcg.so"

    class SD(ctypes.Structure):
        _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]
    class RD(ctypes.Structure):
        _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)),
                    ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

    lib = ctypes.cdll.LoadLibrary(str(lib_path))
    lib.GameInitialize()  # exactly once in this process
    lib.BattleStart.restype = SD
    lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
    lib.BattleFinish.argtypes = [ctypes.c_void_p]
    lib.GetBattleData.restype = RD
    lib.GetBattleData.argtypes = [ctypes.c_void_p]
    lib.Select.restype = ctypes.c_int
    lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]

    def load_deck(p):
        return [int(x) for x in Path(p).read_text().replace(",", " ").split() if x]

    our_deck = load_deck(args.our_deck)
    pool = json.loads(Path(args.pool).read_text())

    spec = importlib.util.spec_from_file_location("worker_agent", args.agent)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["worker_agent"] = mod
    spec.loader.exec_module(mod)  # reads PTCG_* from env

    def make_fn(deck):
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

    fA = make_fn(our_deck)
    per_deck = {}
    t9s, fps, turnss = [], [], []
    for entry in pool:
        name = entry["name"]
        fB = make_fn(entry["deck"])
        w = l = 0
        for g in range(args.games):
            seat_a = g % 2
            d0, d1 = (our_deck, entry["deck"]) if seat_a == 0 else (entry["deck"], our_deck)
            cards = (ctypes.c_int * 120)(*d0, *d1)
            bp = lib.BattleStart(cards).battlePtr
            if not bp:
                l += 1
                continue
            res = 0
            fp = None
            t9 = 0
            last_t = 0
            steps = 0
            try:
                while True:
                    steps += 1
                    obs = json.loads(lib.GetBattleData(bp).json)
                    cur = obs.get("current") or {}
                    t = cur.get("turn") or 0
                    last_t = max(last_t, t)
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
                        taken = (6 - len(plz)) if plz else 0
                        if taken > 0:
                            if fp is None:
                                fp = t
                            if t <= 9:
                                t9 = max(t9, taken)
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
            if res == 1:
                w += 1
            else:
                l += 1
            t9s.append(t9)
            if fp is not None:
                fps.append(fp)
            turnss.append(last_t)
        per_deck[name] = [w, l]

    n = sum(w + l for w, l in per_deck.values())
    print(json.dumps({
        "per_deck": per_deck,
        "t9": sum(t9s) / max(1, len(t9s)),
        "fp": sum(fps) / max(1, len(fps)),
        "turns": sum(turnss) / max(1, len(turnss)),
        "games": n,
    }))

if __name__ == "__main__":
    main()
