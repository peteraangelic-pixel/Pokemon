#!/usr/bin/env python3
"""Build decks/weak_field/ — decks of teams in a leaderboard rank band
(default 90-100, the "weak players" tier) extracted from their fetched
replays (kaggle_results/weak_field_live/episode-*.json).

Unlike build_broad_field.py (our own games only), this works on ANY team's
replays: for each target team we find a replay where it appears and read its
60-card action.  This is the deck set used to test the hypothesis that
top7-tuned agents lose to the weak tier.

Usage:
  .venv/bin/python tools/build_weak_field.py \
      --dir kaggle_results/weak_field_live --out decks/weak_field \
      --rank-min 90 --rank-max 100 \
      --leaderboard kaggle_results/weak_field_live/leaderboard.csv
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def extract_team_deck(replay_path: Path, team_name: str):
    """Return the 60-card deck of `team_name` in this replay, or None."""
    try:
        data = json.loads(replay_path.read_text())
    except Exception:
        return None
    if not isinstance(data, dict) or "steps" not in data:
        return None
    teams = (data.get("info") or {}).get("TeamNames") or []
    if team_name not in teams:
        return None
    idx = teams.index(team_name)
    for s in (data.get("steps") or [])[:4]:
        if not isinstance(s, list):
            continue
        if idx < len(s):
            act = (s[idx] or {}).get("action")
            if isinstance(act, list) and len(act) == 60:
                return list(act)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="kaggle_results/weak_field_live")
    ap.add_argument("--out", default="decks/weak_field")
    ap.add_argument("--rank-min", type=int, default=90)
    ap.add_argument("--rank-max", type=int, default=100)
    ap.add_argument("--leaderboard", default=None,
                    help="leaderboard csv (default: --dir/leaderboard.csv or kaggle_results/leaderboard.csv)")
    args = ap.parse_args()

    d = ROOT / args.dir
    lb_path = (ROOT / args.leaderboard) if args.leaderboard else (d / "leaderboard.csv")
    if not lb_path.exists():
        lb_path = ROOT / "kaggle_results" / "leaderboard.csv"
    targets: dict[str, tuple[int, float]] = {}
    with open(lb_path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                rank = int(row.get("Rank") or 0)
            except Exception:
                continue
            if args.rank_min <= rank <= args.rank_max:
                score = float(row.get("Score") or 0)
                targets[row["TeamName"].strip()] = (rank, score)

    replays = sorted(d.glob("episode-*.json"))
    decks: dict[str, list[int]] = {}
    for name in targets:
        for rp in replays:
            deck = extract_team_deck(rp, name)
            if deck:
                decks[name] = deck
                break

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    # wipe stale deck csvs from previous runs (keep _manifest)
    for f in out.glob("*.csv"):
        if f.name != "_manifest.csv":
            f.unlink()

    manifest = []
    for name in sorted(decks, key=lambda n: targets.get(n, (0, 0))[0]):
        rank, score = targets.get(name, (0, 0.0))
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip().replace(" ", "_")
        (out / f"{safe}.csv").write_text("\n".join(map(str, decks[name])) + "\n")
        manifest.append((rank, score, name, safe))
    with open(out / "_manifest.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "score", "team", "file"])
        w.writerows(manifest)

    print(f"rank band {args.rank_min}-{args.rank_max}: {len(targets)} teams, "
          f"{len(decks)} decks extracted from {len(replays)} replays -> {out}")
    missing = [t for t in targets if t not in decks]
    if missing:
        print("missing:")
        for m in missing:
            print(f"   {targets[m][0]:3d} {m}")

if __name__ == "__main__":
    main()
