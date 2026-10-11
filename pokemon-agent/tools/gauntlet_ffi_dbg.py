#!/usr/bin/env python3
"""Debug variant of gauntlet_ffi.py:
- dumps the OBSERVATION structure once per worker (can we see the opponent's deck?)
- logs a line for every DRAWN game (result==2) with final turn, deck sizes, prizes.

Usage: same flags as gauntlet_ffi.py. Prints obs dump to stderr and draw lines
to stdout prefixed with DRAW: (plus the normal per-deck table).
"""
from __future__ import annotations
import argparse, ctypes, importlib.util, json, os, sys, time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"

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

_OUR = {"agent": None, "deck": None, "path": None}
_OBS_DUMPED = [False]

def _dump_obs_once(obs, seat):
    if _OBS_DUMPED[0]:
        return
    _OBS_DUMPED[0] = True
    cur = obs.get("current") or {}
    print("== OBS STRUCTURE DUMP (seat %d) ==" % seat, file=sys.stderr)
    print("current keys:", sorted(cur.keys()), file=sys.stderr)
    players = cur.get("players") or []
    for i, p in enumerate(players[:2]):
        red = {k: (type(v).__name__ if not isinstance(v, (int, float, str, bool)) else v) for k, v in p.items()}
        print(f"player[{i}] keys:", json.dumps(red, ensure_ascii=False)[:800], file=sys.stderr)
        deck = p.get("deck")
        if deck is not None:
            print(f"player[{i}].deck len={len(deck)} first6={json.dumps(deck[:6], default=str)[:400]}", file=sys.stderr)
        hand = p.get("hand")
        if hand is not None:
            print(f"player[{i}].hand len={len(hand) if hasattr(hand,'__len__') else hand}", file=sys.stderr)

def _snapshot(cur, seat):
    try:
        players = cur.get("players") or []
        me, op = players[seat], players[1 - seat]
        def deckn(p):
            try: return int(p.get("deckCount") or 0)
            except Exception: return -1
        def prizes(p):
            pr = p.get("prize") or []
            return sum(1 for x in pr if x is not None)
        def act(p):
            a = p.get("active") or (p.get("pokemons") or [None])[0]
            if isinstance(a, dict):
                return f"{a.get('id')}:{a.get('hp')}/{a.get('maxHp')}"
            return str(a)
        return (f"turn={cur.get('turn')} myDeck={deckn(me)} oppDeck={deckn(op)} "
                f"myPrizes={prizes(me)} oppPrizes={prizes(op)} active[{act(me)} vs {act(op)}]")
    except Exception as e:
        return f"snapshot-error {e}"

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

def _run_pair(task):
    name, opp_deck, games, dbg = task
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
        d0 = _OUR["deck"] if seat == 0 else opp_deck
        d1 = opp_deck if seat == 0 else _OUR["deck"]
        cards = (ctypes.c_int * 120)(*d0, *d1)
        sd = lib.BattleStart(cards)
        bp = sd.battlePtr
        if not bp:
            d += 1
            continue
        r = 0
        step = 0
        cause = "battlestart_fail"
        last_snap = ""
        try:
            while True:
                step += 1
                data = lib.GetBattleData(bp)
                obs = json.loads(data.json)
                cur = obs.get("current") or {}
                if dbg:
                    _dump_obs_once(obs, seat)
                last_snap = _snapshot(cur, seat) if dbg else ""
                res = cur.get("result")
                if res is not None and res >= 0:
                    r = 0 if res == 2 else (1 if res == seat else -1)
                    cause = f"result={res}"
                    if dbg:
                        try:
                            me, op = cur["players"][seat], cur["players"][1 - seat]
                            print(f"END: r={r} steps={step} turn={cur.get('turn')} "
                                  f"myPrize={[x if isinstance(x,int) else 'N' for x in (me.get('prize') or [])]} "
                                  f"oppPrize={[x if isinstance(x,int) else 'N' for x in (op.get('prize') or [])]} "
                                  f"myDeckCount={me.get('deckCount')} oppDeckCount={op.get('deckCount')} "
                                  f"winFlags=({me.get('win')},{op.get('win')})")
                        except Exception as e:
                            print(f"END: snapshot-error {e}")
                    break
                sel = obs.get("select")
                if sel is None:
                    cause = "select_none"
                    break
                me = int(cur.get("yourIndex", 0))
                dec = _fn_our(obs) if me == seat else fn_opp(obs)
                if not isinstance(dec, list):
                    cause = "agent_returned_nonlist"
                    break
                arg = (ctypes.c_int * len(dec))(*dec)
                if lib.Select(bp, arg, len(dec)) != 0:
                    cause = "select_rejected"
                    break
                if step > 5000:
                    cause = "step_limit"
                    break
        finally:
            lib.BattleFinish(bp)
        if r == 1:
            w += 1
        elif r == -1:
            l += 1
        else:
            d += 1
            if dbg:
                print(f"DRAW: cause={cause} seat={seat} steps={step} {last_snap}")
    return name, w, l, d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/best_from_search.py")
    ap.add_argument("--our-deck", default="decks/v12_30_boss4.csv")
    ap.add_argument("--opp-dir", default="decks/top7_live")
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated name filter (substring)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dbg", action="store_true", help="obs dump + draw lines")
    args = ap.parse_args()

    agent_path = str((ROOT / args.agent) if not os.path.isabs(args.agent) else args.agent)
    our_deck = load_deck(str((ROOT / args.our_deck) if not os.path.isabs(args.our_deck) else Path(args.our_deck)))
    assert len(our_deck) == 60, f"our deck must have 60 cards, got {len(our_deck)}"
    opp_dir = (ROOT / args.opp_dir) if not os.path.isabs(args.opp_dir) else Path(args.opp_dir)
    want = [x.strip() for x in args.only.split(",") if x.strip()]
    pairs = []
    for p in sorted(opp_dir.glob("*.csv")):
        if want and not any(w.lower() in p.stem.lower() for w in want):
            continue
        try:
            od = load_deck(str(p))
        except Exception:
            continue
        if len(od) == 60:
            pairs.append((p.stem, od, args.games, args.dbg))
    if not pairs:
        raise SystemExit(f"no opponent decks in {opp_dir} (filter: {args.only!r})")

    total_w = total_l = total_d = 0
    if args.workers > 1:
        with Pool(args.workers, initializer=_worker_init, initargs=(agent_path, our_deck)) as pool:
            for name, w, l, d in pool.imap_unordered(_run_pair, pairs):
                total_w += w; total_l += l; total_d += d
                g = w + l + d
                print(f"{name:<42} {w:>3}-{l:<3}-{d:<2}  {w / g:.3f}")
    else:
        _worker_init(agent_path, our_deck)
        for t in pairs:
            name, w, l, d = _run_pair(t)
            total_w += w; total_l += l; total_d += d
            g = w + l + d
            print(f"{name:<42} {w:>3}-{l:<3}-{d:<2}  {w / g:.3f}")
    print(f"\nTOTAL {total_w}W-{total_l}L-{total_d}D = {total_w / max(1,(total_w+total_l+total_d)):.3f}  ({len(pairs)} decks x {args.games} games)")

if __name__ == "__main__":
    main()
