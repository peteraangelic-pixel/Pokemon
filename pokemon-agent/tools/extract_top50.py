#!/usr/bin/env python3
"""Extract TOP50 target-team decks + winners from replay JSONs (a450).

Manifest-driven version:
- Reads <src>/top10_manifest.csv (rank, team_name, episode_id, file, status).
- For every selected episode, opens the replay, identifies the seat of the
  manifest team in info.TeamNames, and emits that team's 60-card deck.
- Dedupes by (team, sorted deck). An episode between two target teams can
  therefore emit both decks when it appears in both teams' manifest rows.
- Writes <src>/top50_extract.csv with one row per manifest episode, including
  whether the target team won.

Fallback (no manifest): extracts both decks from every episode and labels
them by TeamNames. This is only for old ad-hoc dirs; prefer manifest mode.

Usage:
  .venv/bin/python tools/extract_top50.py \
      --src kaggle_results/top50_live --out decks/top50
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    s = re.sub(r"[^A-Za-z0-9]+", "_", name or "team").strip("_")
    return s[:48] or "team"


def find_episode_file(src: Path, episode_id: str, manifest_file: str) -> Path | None:
    candidates = []
    if manifest_file:
        candidates.append(src / manifest_file)
    candidates += [src / f"episode-{episode_id}-replay.json", src / f"episode-{episode_id}.json"]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def load_episode(path: Path):
    r = json.load(open(path))
    teams = r.get("info", {}).get("TeamNames") or []
    rewards = r.get("rewards") or []
    decks: list[list[int]] = []
    steps = r.get("steps") or []
    if steps:
        deep_decks(steps[0], decks)
    return r, teams, rewards, decks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="kaggle_results/top30_live")
    ap.add_argument("--out", default="decks/top50")
    ap.add_argument("--manifest", default=None, help="default: <src>/top10_manifest.csv")
    args = ap.parse_args()

    src = ROOT / args.src
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else src / "top10_manifest.csv"
    if manifest_path and not manifest_path.is_absolute():
        # Allow either repo-root-relative or src-relative manifest paths.
        if not manifest_path.exists() and (ROOT / args.manifest).exists():
            manifest_path = ROOT / args.manifest

    rows: list[dict] = []
    seen_pairs: set[tuple[str, tuple[int, ...]]] = set()
    parsed_episodes: set[str] = set()
    manifest_rows: list[dict] = []
    if manifest_path.exists():
        manifest_rows = list(csv.DictReader(open(manifest_path, encoding="utf-8-sig")))

    def emit(team: str, deck: list[int], episode_id: str) -> None:
        key = (team, tuple(sorted(deck)))
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        name = f"{slug(team)}__{episode_id}.csv"
        (out / name).write_text("\n".join(map(str, deck)) + "\n")

    if manifest_rows:
        for m in manifest_rows:
            ep_id = str(m.get("episode_id") or "").strip()
            team = (m.get("team_name") or "").strip()
            if not ep_id or not team:
                continue
            p = find_episode_file(src, ep_id, (m.get("file") or "").strip())
            if p is None:
                rows.append({"episode": ep_id, "file": "", "rank": m.get("rank", ""), "team": team,
                             "opponent": "", "target_seat": "", "winner": "", "target_won": "",
                             "note": "file_missing"})
                continue
            try:
                _r, teams, rewards, decks = load_episode(p)
            except Exception as e:
                rows.append({"episode": ep_id, "file": p.name, "rank": m.get("rank", ""), "team": team,
                             "opponent": "", "target_seat": "", "winner": "", "target_won": "",
                             "note": f"parse_error:{e}"})
                continue
            if len(teams) < 2 or len(decks) < 2:
                rows.append({"episode": ep_id, "file": p.name, "rank": m.get("rank", ""), "team": team,
                             "opponent": "", "target_seat": "", "winner": "", "target_won": "",
                             "note": f"bad_episode teams={len(teams)} decks={len(decks)}"})
                continue
            parsed_episodes.add(ep_id)
            if team not in teams:
                rows.append({"episode": ep_id, "file": p.name, "rank": m.get("rank", ""), "team": team,
                             "opponent": " / ".join(teams), "target_seat": "", "winner": "",
                             "target_won": "", "note": "target_team_not_in_TeamNames"})
                continue
            seat = teams.index(team)
            opponent = teams[1 - seat] if len(teams) > 1 else ""
            emit(team, decks[seat], ep_id)
            winner = ""
            target_won = ""
            if rewards and len(rewards) >= 2:
                winner = teams[int(max(range(len(rewards)), key=lambda i: rewards[i]))]
                target_won = "1" if rewards[seat] == max(rewards) and rewards[seat] > 0 else "0"
            rows.append({"episode": ep_id, "file": p.name, "rank": m.get("rank", ""), "team": team,
                         "opponent": opponent, "target_seat": seat, "winner": winner,
                         "target_won": target_won, "note": m.get("status", "")})
    else:
        for p in sorted(src.glob("episode-*.json")):
            try:
                _r, teams, rewards, decks = load_episode(p)
            except Exception as e:
                print(f"skip {p.name}: {e}")
                continue
            ep = str(_r.get("info", {}).get("EpisodeId") or p.stem)
            if len(decks) < 2 or len(teams) < 2:
                continue
            parsed_episodes.add(ep)
            for seat, team in enumerate(teams[:2]):
                emit(team, decks[seat], ep)
            winner = teams[rewards.index(max(rewards))] if rewards else "?"
            rows.append({"episode": ep, "file": p.name, "rank": "", "team": teams[0],
                         "opponent": teams[1], "target_seat": 0, "winner": winner,
                         "target_won": "", "note": "fallback_no_manifest"})

    extract_path = src / "top50_extract.csv"
    fields = ["episode", "file", "rank", "team", "opponent", "target_seat", "winner", "target_won", "note"]
    with open(extract_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    teams_covered = len({r["team"] for r in rows if r.get("note") != "file_missing"})
    print(f"manifest rows: {len(manifest_rows)}, extract rows: {len(rows)}, "
          f"episodes parsed: {len(parsed_episodes)}, distinct target decks: {len(seen_pairs)}, "
          f"teams covered: {teams_covered}, out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
