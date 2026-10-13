#!/usr/bin/env python3
"""Extract opponent DECKS + winners from top50 replay JSONs (a450).

Walks each episode-*.json, finds both 60-card int lists at step 0 (via deep
scan), reads info.TeamNames / rewards to seat them, and emits:
  decks/top50/<team_slug>__<epid>.csv   (one file per distinct opponent deck)
  top50_extract.csv                     (episode, team, rank_score, winner_seat, decks)
Dedup: same team+identical deck list -> one file.
"""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "kaggle_results" / "top50_live"
OUT = ROOT / "decks" / "top50"
OUT.mkdir(parents=True, exist_ok=True)


def deep_decks(obj, out, depth=0):
    if depth > 6:
        return
    if isinstance(obj, list) and len(obj) == 60 and all(isinstance(x, int) for x in obj):
        out.append(obj)
        return
    if isinstance(obj, dict):
        for v in obj.values():
            deep_decks(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            deep_decks(v, out, depth + 1)


def slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s[:40] or "team"


rows = []
files = sorted(SRC.glob("episode-*.json"))
seen_pairs = set()
for p in files:
    try:
        r = json.load(open(p))
    except Exception as e:
        print(f"skip {p.name}: {e}")
        continue
    ep = r.get("info", {}).get("EpisodeId") or p.stem[8:-12]
    teams = r.get("info", {}).get("TeamNames") or []
    rewards = r.get("rewards") or []
    decks = []
    deep_decks(r.get("steps", [{}])[0], decks)
    if len(decks) < 2 or len(teams) < 2:
        print(f"skip {p.name}: decks={len(decks)} teams={len(teams)}")
        continue
    # seat by reward sign later at play time; here just dump both decks per team label
    # assume teams[i] corresponds to seat i (engine convention so far)
    for seat, team in enumerate(teams[:2]):
        if seat >= len(decks):
            continue
        d = decks[seat]
        key = (team, tuple(sorted(d)))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        name = slug(team) + "__" + str(ep)
        (OUT / f"{name}.csv").write_text("\n".join(map(str, d)) + "\n")
    winner = teams[rewards.index(max(rewards))] if rewards else "?"
    rows.append({
        "episode": ep, "file": p.name, "teamA": teams[0], "teamB": teams[1],
        "rewards": json.dumps(rewards), "winner": winner,
    })

with open(SRC / "top50_extract.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["episode", "file", "teamA", "teamB", "rewards", "winner"])
    w.writeheader()
    w.writerows(rows)
print(f"episodes parsed: {len(rows)}, distinct decks: {len(seen_pairs)}, files in {OUT}")
