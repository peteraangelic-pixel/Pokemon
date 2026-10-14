#!/usr/bin/env python3
"""Loss forensics on fresh live replays (kaggle_results/our_replays).

Replay steps are per-agent entries whose observation is that agent's own
last-seen state; mixing seats corrupts end-state stats. We therefore read
ONLY our seat's entries (yourIndex == our seat) for our board/prizes/deck
and the opponent's board as seen by us.

For every replay with episode id > CUTOFF: result, opponent team + deck
(deck is submitted as the first action, fully visible), archetype from
state_feats, our opening size, prizes/deck at our last observation, and a
coarse loss-cause class.
Usage: .venv/bin/python tools/analyze_live_losses.py [cutoff_episode_id]
"""
from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_feats import deck_archetype

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = int(sys.argv[1]) if len(sys.argv) > 1 else 124200000
FROSLASS = 861
ENERGY_IDS = set(range(1, 12))


def board(player: dict) -> list[int]:
    ids = []
    for zone in ("active", "bench"):
        for poke in player.get(zone) or []:
            if isinstance(poke, dict) and poke.get("id") is not None:
                ids.append(int(poke["id"]))
    return ids


def submitted_deck(step1_actions, seat) -> list[int]:
    try:
        act = step1_actions[seat].get("action") or []
        return [int(c) for c in act if isinstance(c, int) and int(c) > 12]
    except Exception:
        return []


def main() -> int:
    files = [f for f in sorted(glob.glob(str(ROOT / "kaggle_results/our_replays/episode-*-replay.json")))
             if int(Path(f).stem.split("-")[1]) > CUTOFF]
    print(f"fresh replays: {len(files)}")
    W = L = 0
    loss_causes = Counter()
    opp_arch_all, opp_arch_loss = Counter(), Counter()
    opp_teams_loss = Counter()
    famine = games_open = froslass_games = 0
    rows = []
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        teams = (d.get("info") or {}).get("TeamNames") or ["?", "?"]
        rewards = d.get("rewards") or [0, 0]
        seats = [i for i, t in enumerate(teams) if t == "PeterSharps"]
        steps = d.get("steps") or []
        if len(seats) != 1 or len(steps) < 2:
            continue
        me, op = seats[0], 1 - seats[0]
        won = (rewards[me] or 0) > 0
        opp_deck_sig = submitted_deck(steps[1], op)
        arch = deck_archetype(opp_deck_sig) if opp_deck_sig else "?"
        opp_arch_all[arch] += 1
        if FROSLASS in opp_deck_sig:
            froslass_games += 1
        my_last = None
        my_turn2_basics = None
        for s in steps:
            if not isinstance(s, list) or me >= len(s):
                continue
            cur = ((s[me] or {}).get("observation") or {}).get("current") or {}
            players = cur.get("players") or []
            if len(players) < 2 or int(cur.get("yourIndex", -1)) != me:
                continue
            my_last = cur
            if int(cur.get("turn") or 0) >= 1 and my_turn2_basics is None:
                my_turn2_basics = len(board(players[me]))
        if my_last is None:
            continue
        players = my_last.get("players") or [{}, {}]
        taken_me = 6 - len(players[me].get("prize") or [])
        taken_op = 6 - len(players[op].get("prize") or [])
        my_deck = int(players[me].get("deckCount") or 0)
        my_board_n = len(board(players[me]))
        my_turns = int(my_last.get("turn") or 0)
        games_open += 1
        if my_turn2_basics is not None and my_turn2_basics <= 1:
            famine += 1
        if won:
            W += 1
            continue
        L += 1
        opp_arch_loss[arch] += 1
        opp_teams_loss[teams[op]] += 1
        if my_deck <= 0:
            cause = "deckout"
        elif my_board_n == 0:
            cause = "benchout-wiped"
        elif my_turns <= 4 and taken_me <= 1:
            cause = "early-collapse"
        elif taken_op >= 5 and taken_me <= 2:
            cause = "blowout"
        elif taken_me >= 4 and taken_op >= 5:
            cause = "prize-race-close"
        else:
            cause = "other"
        loss_causes[cause] += 1
        rows.append((Path(f).stem.replace("-replay", ""), teams[op], arch,
                     my_turns, f"{taken_me}-{taken_op}", my_deck, my_board_n, cause))
    print(f"W={W} L={L} WR={W / max(1, W + L):.3f}  (n={W + L})")
    print(f"famine(<=1 basic at our turn>=1): {famine}/{games_open} | Froslass games: {froslass_games}")
    print("\nloss causes:", dict(loss_causes))
    print("opp archetypes (all):", dict(opp_arch_all))
    print("opp archetypes (losses):", dict(opp_arch_loss))
    print("teams beating us:", dict(opp_teams_loss.most_common(10)))
    print("\nlosses (ep, opp, arch, ourTurns, prizes me-op, ourDeck, ourBoard, cause):")
    for r in rows:
        print(" ", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
