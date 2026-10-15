#!/usr/bin/env python3
"""Build decks/broad_field/ — every distinct opponent deck seen in OUR live
replays (kaggle_results/replays/).  This is the real mixed ladder: a blend of
strong, mid and weak players — exactly the population the Kaggle rating is
computed over, as opposed to the narrow top-7 set the agent was tuned on.

Usage: .venv/bin/python tools/build_broad_field.py
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ROOT / "kaggle_results"
OUR_TEAM = "PeterSharps"

def extract(replay_path):
    try:
        data = json.loads(replay_path.read_text())
    except Exception:
        return None
    if not isinstance(data, dict) or "steps" not in data:
        return None
    teams = (data.get("info") or {}).get("TeamNames") or []
    if len(teams) != 2 or OUR_TEAM not in teams:
        return None
    steps = data.get("steps") or []
    found = {}
    for s in steps[:3]:
        for i, ps in enumerate(s):
            act = ps.get("action")
            if isinstance(act, list) and len(act) == 60 and i not in found:
                found[i] = list(act)
    if len(found) != 2:
        return None
    opp = teams[1 - teams.index(OUR_TEAM)]
    return opp, found[1 - teams.index(OUR_TEAM)]

def main():
    lb = {}
    with open(KAGGLE / "leaderboard.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                lb[row["TeamName"].strip()] = (int(row["Rank"]), float(row["Score"]))
            except Exception:
                pass
    rp = sorted((KAGGLE / "replays").glob("*.json"))
    opp_decks: dict[str, tuple[str, list[int]]] = {}
    games_by_opp: Counter = Counter()
    wins_by_opp: Counter = Counter()
    for f in rp:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        teams = (data.get("info") or {}).get("TeamNames") or []
        if len(teams) != 2 or OUR_TEAM not in teams:
            continue
        opp = teams[1 - teams.index(OUR_TEAM)]
        games_by_opp[opp] += 1
        if data.get("rewards", [None, None])[teams.index(OUR_TEAM)] == 1:
            wins_by_opp[opp] += 1
        r = extract(f)
        if r and r[0] == opp:
            _, deck = r
            if opp not in opp_decks:
                opp_decks[opp] = (opp, deck)
    out = ROOT / "decks" / "broad_field"
    out.mkdir(exist_ok=True)
    manifest = []
    for name, (_, deck) in sorted(opp_decks.items()):
        rank, score = lb.get(name, (0, 0))
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip().replace(" ", "_")
        (out / f"{safe}.csv").write_text("\n".join(map(str, deck)) + "\n")
        w = wins_by_opp[name]; g = games_by_opp[name]
        manifest.append((rank, score, name, f"{w}/{g}", safe))
    with open(out / "_manifest.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["opp_rank", "opp_score", "team", "our_record", "file"])
        w.writerows(manifest)
    print(f"broad field: {len(opp_decks)} distinct opponent decks from {sum(games_by_opp.values())} live games")
    print(f"our overall live record: {sum(wins_by_opp.values())}W-{sum(games_by_opp.values())-sum(wins_by_opp.values())}L")
    print("\nopp deck list (rank, our record):")
    for rank, score, name, rec, _ in sorted(manifest, key=lambda x: (x[0] or 999)):
        print(f"  #{rank:<4} {score:7.1f}  {rec:6s}  {name}")

if __name__ == "__main__":
    main()
