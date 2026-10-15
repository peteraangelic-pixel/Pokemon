#!/usr/bin/env python3
"""Build decks/top30_live/ — the deck of every team in the current top 30,
extracted from all available replays (replays/, top10_live/, top10/).

Also prints our live win rate split by opponent rank tier, to check the
"we beat top7 but lose to weak opponents" hypothesis.

Usage: .venv/bin/python tools/build_top30.py
"""
from __future__ import annotations
import csv, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ROOT / "kaggle_results"
OUR_TEAM = "PeterSharps"

def load_leaderboard():
    lb = {}
    with open(KAGGLE / "leaderboard.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                lb[row["TeamName"].strip()] = (int(row["Rank"]), float(row["Score"]))
            except Exception:
                continue
    return lb

def extract_decks(replay_path: Path):
    """Yield (episode_id, [(team, deck60), ...])."""
    try:
        data = json.loads(replay_path.read_text())
    except Exception:
        return
    if not isinstance(data, dict) or "steps" not in data:
        return
    info = data.get("info") or {}
    teams = info.get("TeamNames") or []
    if len(teams) != 2:
        return
    steps = data.get("steps") or []
    if not steps:
        return
    # deck is the first 60-id action; may be at step 0 or 1
    found = {}
    for s in steps[:3]:
        for i, ps in enumerate(s):
            act = ps.get("action")
            if isinstance(act, list) and len(act) == 60 and i not in found:
                found[i] = list(act)
    if not found:
        return
    ep = replay_path.stem.replace("episode-", "").replace("-replay", "")
    yield int(ep) if ep.isdigit() else 0, [(teams[i], found.get(i)) for i in (0, 1) if i in found]

def main():
    lb = load_leaderboard()
    top30 = sorted(lb.items(), key=lambda kv: kv[1][0])[:30]
    print("current top 30:")
    for name, (rank, score) in top30:
        print(f"  {rank:3d} {score:7.1f}  {name}")

    replay_dirs = [KAGGLE / "replays", KAGGLE / "top10_live", KAGGLE / "top10"]
    team_decks: dict[str, tuple[int, list[int]]] = {}  # team -> (episode, deck)
    for d in replay_dirs:
        if not d.exists():
            continue
        for rp in sorted(d.glob("*.json")):
            for ep, pairs in extract_decks(rp):
                for team, deck in pairs:
                    if team in team_decks and team_decks[team][0] >= ep:
                        continue
                    team_decks[team] = (ep, deck)
    print(f"\nextracted decks for {len(team_decks)} teams")

    out_dir = ROOT / "decks" / "top30_live"
    out_dir.mkdir(exist_ok=True)
    manifest = []
    missing = []
    for name, (rank, score) in top30:
        if name in team_decks:
            ep, deck = team_decks[name]
            safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip().replace(" ", "_")
            (out_dir / f"{safe}.csv").write_text("\n".join(map(str, deck)) + "\n")
            manifest.append((rank, score, name, ep, safe))
        else:
            missing.append((rank, name))
    with open(out_dir / "_manifest.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "score", "team", "episode", "file"])
        w.writerows(manifest)
    print(f"\nwrote {len(manifest)} decks to {out_dir}")
    if missing:
        print("missing (no replay with deck found):")
        for rank, name in missing:
            print(f"  {rank:3d} {name}")

    # ---- our live record split by opponent tier ----
    ours = []
    seen = set()
    for d in replay_dirs:
        if not d.exists():
            continue
        for rp in sorted(d.glob("*.json")):
            for ep, pairs in extract_decks(rp):
                teams = [t for t, _ in pairs]
                if OUR_TEAM not in teams:
                    continue
                key = (rp.name, ep, tuple(teams))
                if key in seen:
                    continue
                seen.add(key)
                data = json.loads(rp.read_text())
                rewards = data.get("rewards") or []
                me = teams.index(OUR_TEAM)
                if len(rewards) < 2 or rewards[me] is None:
                    continue
                opp = teams[1 - me]
                win = 1 if rewards[me] == 1 else 0
                rank = lb.get(opp, (None, None))[0]
                ours.append((opp, rank, win))
    tiers = {"top50 (rank<=50)": lambda r: r is not None and r <= 50,
             "rank 51-150": lambda r: r is not None and 50 < r <= 150,
             "rank 151+ / unknown": lambda r: r is None or r > 150}
    print(f"\nour live record by opponent tier ({len(ours)} games):")
    for tname, pred in tiers.items():
        sel = [w for _, r, w in ours if pred(r)]
        if sel:
            print(f"  {tname:22s} {sum(sel)}W-{len(sel)-sum(sel)}L  ({sum(sel)/len(sel):.3f})")

if __name__ == "__main__":
    main()
