"""Rollouty self-play przez FFI (jak league_eval), z zapisem decyzji.
Policy = callable(obs, me) -> indeks opcji (dla strony, ktora trenujemy)."""
import ctypes, json, sys
sys.path.insert(0, 'tools')
import gauntlet_ffi as G


def load_pilot(path, deck, tag):
    m = G.load_module(path, f"_rl_{tag}")
    d = G.load_deck(deck)
    G.rebind(m, d)
    return m.agent, d


def play_game(lib, our_fn, opp_fn, our_deck, opp_deck, seat, record=None, rfz=None):
    """our_fn(obs)->idx dla naszego gracza (seat). record: lista na decyzje
    (tokens, state, opts, mask, action) jesli rfz podany."""
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck),
                                  *(opp_deck if seat == 0 else our_deck))
    bp = lib.BattleStart(cards).battlePtr
    if not bp:
        return 0
    r = 0
    try:
        while True:
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1)
                break
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            if me == seat:
                if record is not None and rfz is not None:
                    sel = obs.get("select") or {}
                    tt = sel.get("type")
                    if (tt is not None and int(tt) == 0) and int(sel.get("maxCount") or 1) == 1:
                        enc = rfz.encode(obs, me)
                        a = our_fn(obs)
                        ai = a[0] if isinstance(a, list) and a else 0
                        record.append((enc[0], enc[1], enc[2], enc[3], ai, seat))
                        dec = a
                    else:
                        dec = our_fn(obs)
                else:
                    dec = our_fn(obs)
            else:
                dec = opp_fn(obs)
            if not isinstance(dec, list):
                dec = []
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    return r


def play_game_pg(lib, policy_lp, opp_fn, our_deck, opp_deck, seat, rfz, traj, fallback_fn=None):
    """Jak play_game, ale policy_lp(obs)->(idx, logprob); traj dostaje
    (tokens, state, opts, mask, action, logprob) dla decyzji MAIN gracza seat."""
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck),
                                  *(opp_deck if seat == 0 else our_deck))
    bp = lib.BattleStart(cards).battlePtr
    if not bp:
        return 0
    r = 0
    try:
        while True:
            obs = json.loads(lib.GetBattleData(bp).json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1)
                break
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            if me == seat:
                sel = obs.get("select") or {}
                tt = sel.get("type")
                if (tt is not None and int(tt) == 0) and int(sel.get("maxCount") or 1) == 1:
                    enc = rfz.encode(obs, me)
                    ai, lp = policy_lp(enc)
                    traj.append((enc[0], enc[1], enc[2], enc[3], ai, lp))
                    dec = [ai]
                else:
                    # decyzje nie-MAIN delegujemy do championa (jak agenci produkcyjni)
                    dec = fallback_fn(obs) if fallback_fn is not None else [policy_lp(rfz.encode(obs, me))[0]]
            else:
                dec = opp_fn(obs)
            if not isinstance(dec, list):
                dec = []
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    return r
