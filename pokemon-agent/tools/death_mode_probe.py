#!/usr/bin/env python3
"""Death-mode probe: play OUR agent vs an opponent agent and report the
live-loss mechanics directly (empty-bench deaths, board development).

This is the metric that maps to live losses (2026-10-12/13 forensics):
- % of losses with our board at <=1 alive pokemon (board collapse)
- our alive board early in the game (development)
- plain W-L.

Usage:
  .venv/bin/python tools/death_mode_probe.py \
      --agent agents/main_heuristic_v26.py --opp agents/opp_thickbot.py \
      --our-deck decks/v22_35w_noBoss.csv --opp-deck decks/v22_35w_noBoss.csv \
      --games 100
"""
from __future__ import annotations
import argparse, ctypes, json, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G


def alive_board(cur, idx):
    try:
        p = cur["players"][idx]
        n = 0
        act = p.get("active")
        if isinstance(act, list):
            n += sum(1 for q in act if isinstance(q, dict) and int(q.get("hp") or 0) > 0)
        elif isinstance(act, dict) and int(act.get("hp") or 0) > 0:
            n += 1
        for b in p.get("bench") or []:
            if isinstance(b, dict) and int(b.get("hp") or 0) > 0:
                n += 1
        return n
    except Exception:
        return -1


def run_game(lib, agent, opp_agent, our_deck, opp_deck, seat, stats):
    cards = (ctypes.c_int * 120)(*(our_deck if seat == 0 else opp_deck),
                                 *(opp_deck if seat == 0 else our_deck))
    sd = lib.BattleStart(cards)
    bp = sd.battlePtr
    if not bp:
        stats["coinflips"] += 1
        return 2
    r = 2
    step = 0
    our_turns = 0
    b4_samples = []
    last_cur = None
    try:
        while True:
            step += 1
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            if int(cur.get("yourIndex", 0)) == seat:
                last_cur = cur
            res = cur.get("result")
            if res is not None and res >= 0:
                r = 0 if res == 2 else (1 if res == seat else -1)
                break
            if obs.get("select") is None:
                break
            me = int(cur.get("yourIndex", 0))
            if me == seat:
                our_turns += 1
                if our_turns in (3, 4, 5):
                    b4_samples.append(alive_board(cur, seat))
                if our_turns > 5000:
                    break
                dec = agent(obs)
            else:
                dec = opp_agent(obs)
            if not isinstance(dec, list):
                dec = []
            arg = (ctypes.c_int * len(dec))(*dec)
            if lib.Select(bp, arg, len(dec)) != 0:
                break
    finally:
        lib.BattleFinish(bp)
    if r == -1:
        stats["losses"] += 1
        fin = alive_board(last_cur, seat) if last_cur else -1
        stats["loss_final_board"].append(fin)
        if fin <= 1:
            stats["empty_bench_deaths"] += 1
    elif r == 1:
        stats["wins"] += 1
    if b4_samples:
        stats["board_samples"] += b4_samples
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--opp", required=True)
    ap.add_argument("--our-deck", required=True)
    ap.add_argument("--opp-deck", required=True)
    ap.add_argument("--games", type=int, default=100)
    args = ap.parse_args()

    our_deck = G.load_deck(args.our_deck)
    opp_deck = G.load_deck(args.opp_deck)
    m = G.load_module(args.agent, f"_dmp_a_{uuid.uuid4().hex[:8]}")
    G.rebind(m, our_deck)
    agent = m.agent
    mo = G.load_module(args.opp, f"_dmp_o_{uuid.uuid4().hex[:8]}")
    G.rebind(mo, opp_deck)
    opp_agent = mo.agent

    stats = {"wins": 0, "losses": 0, "draws": 0, "coinflips": 0,
             "empty_bench_deaths": 0, "loss_final_board": [], "board_samples": []}
    lib = G.get_lib()
    for g in range(args.games):
        seat = g % 2
        stats["_last_alive"] = -1
        # wrap: capture last alive for loss classification
        prev_loss = stats["losses"]
        r = run_game(lib, agent, opp_agent, our_deck, opp_deck, seat, stats)
        if stats["losses"] > prev_loss:
            stats["loss_final_board"][-1] = stats["loss_final_board"][-1] if stats["loss_final_board"] else -1
        if r == 2:
            stats["draws"] += 1
    n = stats["wins"] + stats["losses"]
    bs = stats["board_samples"]
    print(f"games={args.games} W={stats['wins']} L={stats['losses']} D={stats['draws']} "
          f"WR={stats['wins'] / max(1, n):.3f}")
    print(f"empty-bench deaths: {stats['empty_bench_deaths']}/{stats['losses']} losses "
          f"({100 * stats['empty_bench_deaths'] / max(1, stats['losses']):.0f}%)")
    if bs:
        print(f"our board size samples (our turns 3-5): mean={sum(bs)/len(bs):.2f} "
              f"n={len(bs)}")


if __name__ == "__main__":
    main()
