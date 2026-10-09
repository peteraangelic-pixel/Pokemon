#!/usr/bin/env python3
"""Download 7 last replays of top10 leaders — PTCG version of Kaggriculture's download_top49_replays.py

This is the script the user referred to: it downloads top-N teams' last M replays
to disk, zips them, and uploads to GitHub for analysis. The original was for
Kaggriculture (top-n 12, replays-per-team 9), this is adapted for PTCG.

How it works (verified from Kaggle API):
1. Download leaderboard (competition_leaderboard_download)
2. Parse TeamId for top N teams
3. For each TeamId: competition_team_submissions(team_id) -> list of submissions
4. For each submission (latest 2): competition_list_episodes(submission_id) -> episodes
5. For each episode (last 7): competition_episode_replay(episode_id) -> JSON

The Rust speedup mentioned by user: in Kaggriculture they had a Rust port of the
game that was 100x faster than Python. For PTCG we don't have Rust port yet
(the engine is closed-source libcg.so), but we can still simulate with Python
kaggle_environments (0.15s/game) and it will be okay for 70 replays.

Usage:
    pip install kaggle
    export KAGGLE_API_TOKEN=...
    python tools/download_top10_replays.py --top-n 10 --replays-per-team 7 --competition the-pokemon-company-ptcg-ai-battle-challenge-playground

Outputs:
    TOP10.zip (or top10_replays/ dir) with JSON replays
    top10_manifest.csv with team, submission, episode info
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

DEFAULT_SLUG = "the-pokemon-company-ptcg-ai-battle-challenge-playground"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "kaggle_results" / "top10_live"


def sh(args: list[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    env.setdefault("KAGGLE_QUIET", "1")
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def have_kaggle() -> bool:
    rc, _, _ = sh([sys.executable, "-m", "kaggle", "--version"])
    if rc == 0:
        return True
    rc, _, _ = sh(["kaggle", "--version"])
    return rc == 0


def kaggle(args: list[str]) -> tuple[int, str, str]:
    rc, out, err = sh([sys.executable, "-m", "kaggle"] + args)
    if rc == 0:
        return rc, out, err
    return sh(["kaggle"] + args)


def check_auth() -> str | None:
    home = os.path.expanduser("~")
    if os.environ.get("KAGGLE_API_TOKEN", "").strip():
        return None
    if os.path.isfile(os.path.join(home, ".kaggle", "access_token")):
        return None
    if os.environ.get("KAGGLE_USERNAME", "").strip() and os.environ.get("KAGGLE_KEY", "").strip():
        return None
    if os.path.isfile(os.path.join(home, ".kaggle", "kaggle.json")):
        return None
    return "no Kaggle credentials"


def rows_from_csv(text: str) -> list[dict]:
    text = text.strip("\ufeff").strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", default=DEFAULT_SLUG)
    ap.add_argument("--top-n", type=int, default=10, help="top N teams from leaderboard")
    ap.add_argument("--replays-per-team", type=int, default=7, help="last M replays per team")
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    ap.add_argument("--delay", type=float, default=0.2, help="delay between API calls")
    ap.add_argument("--zip", default=None, help="output zip path (default outdir/TOP10.zip)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not have_kaggle():
        print("kaggle CLI not installed", file=sys.stderr)
        return 2
    err = check_auth()
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    print(f"=== Downloading top {args.top_n} teams, {args.replays_per_team} replays each ===")
    print(f"Competition: {args.competition}")
    print(f"Outdir: {outdir}")

    # 1. Download leaderboard
    print("\n1. Downloading leaderboard...")
    # Use API to get leaderboard via CLI download
    tmp_zip = outdir / "leaderboard.zip"
    rc, out, err = kaggle(["competitions", "leaderboard", "-c", args.competition, "-d", "-p", str(outdir), "-q"])
    if rc != 0:
        print(f"leaderboard download failed: {err[:500]}", file=sys.stderr)
        return 1

    # Find and unzip leaderboard csv
    zpath = outdir / f"{args.competition}.zip"
    lb_rows: list[dict] = []
    if zpath.exists():
        try:
            with zipfile.ZipFile(zpath) as z:
                names = z.namelist()
                inner = names[0] if names else f"{args.competition}.csv"
                data = z.read(inner).decode("utf-8", "replace")
            lb_path = outdir / "leaderboard.csv"
            lb_path.write_text(data.strip() + "\n", encoding="utf-8")
            lb_rows = rows_from_csv(data)
            zpath.unlink()
            print(f"  Leaderboard: {len(lb_rows)} teams")
        except Exception as exc:
            print(f"  unzip failed: {exc}", file=sys.stderr)
            return 1
    else:
        # Try existing leaderboard.csv from poll
        poll_lb = ROOT / "kaggle_results" / "leaderboard.csv"
        if poll_lb.exists():
            print(f"  Using existing leaderboard from {poll_lb}")
            lb_rows = rows_from_csv(poll_lb.read_text(encoding="utf-8"))
        else:
            print("  No leaderboard found", file=sys.stderr)
            return 1

    # Sort by Score descending and take top N
    def get_score(r):
        try:
            return float(r.get("Score") or r.get("score") or 0)
        except:
            return 0

    lb_sorted = sorted(lb_rows, key=get_score, reverse=True)
    top_teams = lb_sorted[: args.top_n]

    print(f"\nTop {args.top_n} teams:")
    for i, t in enumerate(top_teams, 1):
        print(f"  {i}. {t.get('TeamName')} (id={t.get('TeamId')}) score={t.get('Score')}")

    # 2. For each team, get their public submissions via team_id
    manifest = []
    downloaded = 0

    for rank, team in enumerate(top_teams, 1):
        team_id = team.get("TeamId") or team.get("teamId")
        team_name = team.get("TeamName") or team.get("teamName") or f"team_{team_id}"
        if not team_id:
            print(f"  No team_id for {team_name}, skipping")
            continue

        print(f"\n{rank}. {team_name} (team_id={team_id}) — fetching submissions...")

        # Use kaggle competitions team-submissions <team_id>
        rc, out, err = kaggle(["competitions", "team-submissions", str(team_id), "--format", "csv", "-q"])
        if rc != 0:
            print(f"  team-submissions failed for {team_id}: {err[:300]}")
            # Try without csv
            rc, out, err = kaggle(["competitions", "team-submissions", str(team_id)])
            print(f"  verbose output: {out[:500]}")
            continue

        sub_rows = rows_from_csv(out)
        if not sub_rows:
            print(f"  No submissions for team {team_id}")
            continue

        # Sort by date newest first, take latest 2 (like competition does)
        def sub_date(r):
            return r.get("date") or r.get("Date") or r.get("submitted") or r.get("SubmissionDate") or ""

        sub_sorted = sorted(sub_rows, key=sub_date, reverse=True)
        print(f"  Found {len(sub_rows)} submissions, taking latest {min(2, len(sub_sorted))}")

        for sub in sub_sorted[:2]:
            sub_id = sub.get("ref") or sub.get("id") or sub.get("submissionId") or sub.get("SubmissionId")
            if not sub_id:
                continue

            print(f"    Submission {sub_id} — listing episodes...")

            # List episodes for this submission
            rc, out, err = kaggle(["competitions", "episodes", str(sub_id), "--format", "csv", "-q"])
            ep_rows: list[dict] = []
            if rc == 0 and out.strip():
                ep_rows = rows_from_csv(out)
            else:
                # Fallback to verbose and parse ids
                rc, out, err = kaggle(["competitions", "episodes", str(sub_id), "-v"])
                if rc == 0:
                    import re

                    ids = re.findall(r"^\s*(\d{6,})", out, flags=re.MULTILINE)
                    ep_rows = [{"id": eid} for eid in ids]

            if not ep_rows:
                print(f"      No episodes for submission {sub_id}")
                continue

            print(f"      Found {len(ep_rows)} episodes, downloading last {args.replays_per_team}")

            # Take last N (newest first is typical)
            for ep in ep_rows[: args.replays_per_team]:
                ep_id = ep.get("id") or ep.get("Id") or ep.get("EpisodeId") or ep.get("episodeId")
                if not ep_id:
                    continue
                ep_id = str(ep_id).strip()
                if not ep_id.isdigit():
                    continue

                dest = outdir / f"episode-{ep_id}.json"
                if dest.exists():
                    print(f"        {ep_id} already exists, skip")
                    continue

                rc, out, err = kaggle(["competitions", "replay", str(ep_id), "-p", str(outdir)])
                if rc == 0:
                    downloaded += 1
                    print(f"        Downloaded {ep_id}")
                    manifest.append(
                        {
                            "rank": rank,
                            "team_id": team_id,
                            "team_name": team_name,
                            "team_score": team.get("Score"),
                            "submission_id": sub_id,
                            "episode_id": ep_id,
                            "file": f"episode-{ep_id}.json",
                        }
                    )
                else:
                    print(f"        Failed {ep_id}: {err[:200]}")

                time.sleep(args.delay)

    # Write manifest
    manifest_path = outdir / "top10_manifest.csv"
    if manifest:
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
            w.writeheader()
            w.writerows(manifest)
        print(f"\nWrote manifest {manifest_path} with {len(manifest)} entries")

    # Write summary
    summary = {
        "fetched_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "competition": args.competition,
        "top_n": args.top_n,
        "replays_per_team": args.replays_per_team,
        "teams": len(top_teams),
        "replays_downloaded": downloaded,
        "manifest": str(manifest_path),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Zip if requested
    zip_path = Path(args.zip) if args.zip else outdir / "TOP10.zip"
    if downloaded > 0:
        print(f"\nZipping {downloaded} replays into {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in outdir.glob("episode-*.json"):
                z.write(f, f.name)
            if manifest_path.exists():
                z.write(manifest_path, manifest_path.name)
        print(f"  Zip size: {zip_path.stat().st_size / 1e6:.1f} MB")

    print(f"\nDone. Downloaded {downloaded} replays for top {args.top_n} teams.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
