#!/usr/bin/env python3
"""Merge batched TOP50 fetches into one top50_live dataset (a450).

Batch convention (produced by kaggle_top30.yml workflow_dispatch):
  kaggle_results/top50_b1/top10_manifest.csv, top50_extract.csv, leaderboard.csv
  decks/top50_b1/*.csv
  kaggle_results/top50_b2/...
  decks/top50_b2/*.csv
  ...

Merge rules:
- Manifest: dedupe by (team_name, episode_id); prefer rows whose replay was
  actually obtained (downloaded/existing) over selected/pending/failed rows.
- Extract: dedupe by (episode, team).
- Decks: copy CSVs into decks/top50; filename already contains team+episode,
  so collisions should be identical. If a different deck appears under the
  same filename, keep the batch-suffixed copy too.
- Writes kaggle_results/top50_live/{top10_manifest.csv, top50_extract.csv,
  summary.json, leaderboard.csv}.

Usage:
  .venv/bin/python tools/merge_top50_batches.py --batches 1,2,3,4,5,6,7
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_RANK = {
    "downloaded": 0,
    "existing": 0,
    "selected": 1,
    "pending_batch": 2,
    "pending_429": 3,
    "failed_429": 4,
    "failed": 5,
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", default="1,2,3,4,5,6,7", help="comma list of batch suffixes")
    ap.add_argument("--outdir", default="kaggle_results/top50_live")
    ap.add_argument("--deck-out", default="decks/top50")
    args = ap.parse_args()

    batch_ids = [b.strip() for b in args.batches.split(",") if b.strip()]
    outdir = ROOT / args.outdir
    deck_out = ROOT / args.deck_out
    outdir.mkdir(parents=True, exist_ok=True)
    deck_out.mkdir(parents=True, exist_ok=True)

    manifest_by_key: dict[tuple[str, str], dict] = {}
    extract_by_key: dict[tuple[str, str], dict] = {}
    leaderboard_copied = False
    decks_copied = 0
    decks_conflicts = 0

    for b in batch_ids:
        bdir = ROOT / f"kaggle_results/top50_b{b}"
        ddir = ROOT / f"decks/top50_b{b}"
        for r in read_csv(bdir / "top10_manifest.csv"):
            key = ((r.get("team_name") or "").strip(), (r.get("episode_id") or "").strip())
            if not key[0] or not key[1]:
                continue
            old = manifest_by_key.get(key)
            if old is None or STATUS_RANK.get(r.get("status", ""), 9) < STATUS_RANK.get(old.get("status", ""), 9):
                manifest_by_key[key] = r
        for r in read_csv(bdir / "top50_extract.csv"):
            key = ((r.get("episode") or "").strip(), (r.get("team") or "").strip())
            if key[0] and key[1] and key not in extract_by_key:
                extract_by_key[key] = r
        if not leaderboard_copied and (bdir / "leaderboard.csv").exists():
            shutil.copyfile(bdir / "leaderboard.csv", outdir / "leaderboard.csv")
            leaderboard_copied = True
        if ddir.exists():
            for src in sorted(ddir.glob("*.csv")):
                dst = deck_out / src.name
                data = src.read_bytes()
                if dst.exists():
                    if dst.read_bytes() != data:
                        dst = deck_out / f"{src.stem}__b{b}.csv"
                        decks_conflicts += 1
                        if dst.exists() and dst.read_bytes() == data:
                            continue
                        dst.write_bytes(data)
                        decks_copied += 1
                    continue
                dst.write_bytes(data)
                decks_copied += 1

    manifest = sorted(
        manifest_by_key.values(),
        key=lambda r: (int(float(r.get("rank") or 999)), r.get("team_name") or "", r.get("episode_id") or ""),
    )
    extract = sorted(extract_by_key.values(), key=lambda r: (r.get("team") or "", r.get("episode") or ""))

    manifest_fields = ["rank", "team_id", "team_name", "team_score", "submission_id", "episode_id", "file", "status"]
    extract_fields = ["episode", "file", "rank", "team", "opponent", "target_seat", "winner", "target_won", "note"]
    write_csv(outdir / "top10_manifest.csv", manifest, manifest_fields)
    write_csv(outdir / "top50_extract.csv", extract, extract_fields)

    per_team_selected = Counter(r["team_name"] for r in manifest)
    per_team_obtained = Counter(
        r["team_name"] for r in manifest if r.get("status") in ("downloaded", "existing") and r.get("file")
    )
    status_counts = Counter(r.get("status", "") for r in manifest)
    summary = {
        "batches": batch_ids,
        "teams": len(per_team_selected),
        "teams_with_full_quota_selected": sum(1 for v in per_team_selected.values() if v >= 7),
        "teams_with_full_quota_obtained": sum(1 for v in per_team_obtained.values() if v >= 7),
        "selected_rows": len(manifest),
        "unique_episodes": len({r["episode_id"] for r in manifest}),
        "obtained_rows": sum(1 for r in manifest if r.get("status") in ("downloaded", "existing")),
        "status_counts": dict(status_counts),
        "extract_rows": len(extract),
        "deck_files": len(list(deck_out.glob("*.csv"))),
        "decks_copied": decks_copied,
        "deck_conflicts": decks_conflicts,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
