#!/usr/bin/env python3
"""Fast gauntlet: our agent+deck vs a directory of opponent decks, on the real
cabt engine via DIRECT FFI into libcg.so (no kaggle_environments wrapper).

Measured on this sandbox: ~8 ms/game vs ~200 ms/game with the
kaggle_environments wrapper (~20x).  Both seats alternate per game.  The
opponent is the SAME policy with a different deck (deck-only delta), matching
the semantics of tools/vs_top10.py / tools/gauntlet_live.py but faster.

RUST NOTE (2026-10-11): this sandbox has no Rust toolchain and the network
allowlist blocks rustup/dist servers, so rust/ cannot be rebuilt here.  The
prebuilt rust/bin/rust_full aborts on ENERGY selects ("buffer full.
capacity:7") and its heuristic is a rough approximation of the Python agent,
so it cannot evaluate the real submission either.  This FFI driver is the
fast tool here; on a machine with cargo, port the same libcg.so FFI contract
(rust/src/engine.rs) to get the ~150x single-process speedup with rayon
fan-out over deck pairs.

Usage:
  .venv/bin/python tools/gauntlet_ffi.py --agent agents/best_from_search.py \
      --our-deck decks/v10_34_sig4.csv --opp-dir decks/top30_live --games 8
  .venv/bin/python tools/gauntlet_ffi.py ... --workers 2 --only Xinyu,OceanMix
"""
from __future__ import annotations
import argparse, ctypes, importlib.util, json, os, sys, time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"
if not LIB.exists():
    import sysconfig
    _sp = Path(sysconfig.get_paths()["purelib"])
    _cand = _sp / "kaggle_environments/envs/cabt/cg/libcg.so"
    if _cand.exists():
        LIB = _cand

class StartData(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]

_lib = None
def get_lib():
    global _lib
    if _lib is None:
        lib = ctypes.cdll.LoadLibrary(str(LIB))
        lib.GameInitialize()
        lib.BattleStart.restype = StartData
        lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.BattleFinish.argtypes = [ctypes.c_void_p]
        lib.GetBattleData.restype = SerialData
        lib.GetBattleData.argtypes = [ctypes.c_void_p]
        lib.Select.restype = ctypes.c_int
        lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        _lib = lib
    return _lib

def load_deck(path):
    return [int(t) for line in open(path) for t in line.replace(",", " ").split() if t]

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def rebind(mod, deck):
    mod.DECK = list(deck)
    if hasattr(mod, "_build_plan"):
        mod.PLAN = mod._build_plan(mod.DECK)

# our-side agent, loaded once per worker process
_OUR = {"agent": None, "deck": None, "path": None}

def _worker_init(agent_path: str, deck: list[int]):
    mod = load_module(agent_path, "_gauntlet_our")
    rebind(mod, deck)
    _OUR["agent"] = mod.agent
    _OUR["deck"] = list(deck)
    _OUR["path"] = agent_path

def _fn_our(obs):
    if obs.get("select") is None:
        return list(_OUR["deck"])
    return _OUR["agent"](obs)

def _run_pair(task: tuple) -> tuple[str, int, int, int]:
    """task = (name, our_deck, opp_deck, games). Both sides same policy."""
    name, our_deck, opp_deck, games = task
    opp_mod = load_module(_OUR["path"], "_gauntlet_opp")
    rebind(opp_mod, opp_deck)
    def fn_opp(obs):
        if obs.get("select") is None:
            return list(opp_deck)
        return opp_mod.agent(obs)

    lib = get_lib()
    w = l = d = 0
    for g in range(games):
        seat = g % 2
        d0 = our_deck if seat == 0 else opp_deck
        d1 = opp_deck if seat == 0 else our_deck
        cards = (ctypes.c_int * 120)(*d0, *d1)
        sd = lib.BattleStart(cards)
        bp = sd.battlePtr
        if not bp:
            d += 1
            continue
        r = 0
        step = 0
        try:
            while True:
                step += 1
                data = lib.GetBattleData(bp)
                obs = json.loads(data.json)
                cur = obs.get("current") or {}
                res = cur.get("result")
                if res is not None and res >= 0:
                    r = 0 if res == 2 else (1 if res == seat else -1)
                    break
                sel = obs.get("select")
                if sel is None:
                    break
                me = int((obs.get("current") or {}).get("yourIndex", 0))
                dec = _fn_our(obs) if me == seat else fn_opp(obs)
                if not isinstance(dec, list):
                    dec = []
                arg = (ctypes.c_int * len(dec))(*dec)
                if lib.Select(bp, arg, len(dec)) != 0:
                    break
                if step > 5000:
                    break
        finally:
            lib.BattleFinish(bp)
        if r == 1:
            w += 1
        elif r == -1:
            l += 1
        else:
            d += 1
    return name, w, l, d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/best_from_search.py")
    ap.add_argument("--our-deck", default="decks/v10_34_sig4.csv")
    ap.add_argument("--opp-dir", default="decks/top30_live")
    ap.add_argument("--games", type=int, default=8, help="games per opponent deck (both seats)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--only", default="", help="comma-separated name filter (substring)")
    ap.add_argument("--slice", default="", help="A:B rows of the sorted deck list (parallel jobs)")
    args = ap.parse_args()

    agent_path = str((ROOT / args.agent) if not os.path.isabs(args.agent) else args.agent)
    our_deck_path = (ROOT / args.our_deck) if not os.path.isabs(args.our_deck) else Path(args.our_deck)
    our_deck = load_deck(str(our_deck_path))
    assert len(our_deck) == 60, f"our deck must have 60 cards, got {len(our_deck)}"
    opp_dir = (ROOT / args.opp_dir) if not os.path.isabs(args.opp_dir) else Path(args.opp_dir)

    names = [f.stem for f in sorted(opp_dir.glob("*.csv")) if not f.stem.startswith("_")]
    if args.only:
        want = [x.strip() for x in args.only.split(",") if x.strip()]
        names = [n for n in names if any(x in n for x in want)]
    if not names:
        raise SystemExit(f"no opponent decks in {opp_dir} (filter: {args.only!r})")
    tasks = []
    for n in names:
        try:
            od = load_deck(str(opp_dir / f"{n}.csv"))
        except Exception:
            continue
        if len(od) != 60:
            print(f"skip {n}: not a 60-card deck ({len(od)} ids)")
            continue
        tasks.append((n, our_deck, od, args.games))

    t0 = time.time()
    if args.workers <= 1:
        _worker_init(agent_path, our_deck)
        results = [_run_pair(t) for t in tasks]
    else:
        pool = Pool(args.workers, initializer=_worker_init, initargs=(agent_path, our_deck))
        results = pool.map(_run_pair, tasks)
        pool.close(); pool.join()

    rows = []
    for name, w, l, d in results:
        n = w + l + d
        rows.append((w / n if n else 0.0, w, l, d, name))
    rows.sort(reverse=True)
    tw = sum(r[1] for r in rows); tl = sum(r[2] for r in rows); td = sum(r[3] for r in rows)
    for rate, w, l, d, name in rows:
        print(f"{name:42s} {w:2d}-{l:2d}-{d:2d}  {rate:.3f}")
    n = tw + tl + td
    print(f"\nTOTAL {tw}W-{tl}L-{td}D = {tw/n:.3f}  ({len(rows)} decks x {args.games} games, {time.time()-t0:.0f}s)")
    print("worst 5:")
    for rate, w, l, d, name in rows[-5:][::-1]:
        print(f"  {name:42s} {w}-{l}-{d}  {rate:.3f}")

if __name__ == "__main__":
    main()
