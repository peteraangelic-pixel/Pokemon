#!/usr/bin/env python3
"""Batch matchup probe: our candidate (+our deck) vs champion piloting each
extracted live opponent deck. Used to answer 'would our version win the games
the live submission lost?'.

Usage:
  .venv/bin/python tools/live_matchup_probe.py --agent agents/c87_policy_v59_10k.py \
      --our-deck decks/v57_trolley34w.csv --deck-dir kaggle_results/our_replays/opp_decks_v59 \
      --games 100
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G
from death_mode_probe import run_game, alive_board  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
CHAMP = ROOT / 'agents/c87_v44.py'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', required=True)
    ap.add_argument('--our-deck', default='decks/v57_trolley34w.csv')
    ap.add_argument('--deck-dir', default='kaggle_results/our_replays/opp_decks_v59')
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--decks', default='', help='comma files to limit')
    args = ap.parse_args()

    our_deck = G.load_deck(args.our_deck)
    m = G.load_module(str(ROOT / args.agent) if not args.agent.startswith('/') else args.agent,
                      f"_lmp_a_{uuid.uuid4().hex[:8]}")
    G.rebind(m, our_deck)
    champ = G.load_module(str(CHAMP), f"_lmp_c_{uuid.uuid4().hex[:8]}")

    deck_dir = ROOT / args.deck_dir
    man = json.loads((deck_dir / 'manifest.json').read_text())
    if args.decks:
        keep = set(args.decks.split(','))
        man = [v for v in man if v['file'] in keep]

    lib = G.get_lib()
    tot_w = tot_l = 0
    print(f"{'deck':28s} {'arch':8s} {'liveW':>5s} {'n':>3s} {'WR':>6s}  emptyBenchLoss")
    for v in man:
        opp_deck = G.load_deck(deck_dir / v['file'])
        G.rebind(champ, opp_deck)
        stats = {"wins": 0, "losses": 0, "draws": 0, "coinflips": 0,
                 "empty_bench_deaths": 0, "loss_final_board": [], "board_samples": []}
        for g in range(args.games):
            r = run_game(lib, m.agent, champ.agent, our_deck, opp_deck, g % 2, stats)
            if r == 2:
                stats['draws'] += 1
        n = stats['wins'] + stats['losses']
        tot_w += stats['wins']
        tot_l += stats['losses']
        wr = stats['wins'] / n if n else 0.0
        print(f"{v['file'] + ' ' + v['team'][:16]:28s} {v['arch']:8s} {v['v59wins']:5d} "
              f"{n:3d} {wr:6.3f}  {stats['empty_bench_deaths']}/{stats['losses']}", flush=True)
    n = tot_w + tot_l
    print(f"TOTAL: W={tot_w} L={tot_l} WR={tot_w / n:.3f} n={n}")


if __name__ == '__main__':
    main()
