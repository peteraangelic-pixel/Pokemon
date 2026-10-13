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


def existing_replay(outdir: Path, ep_id: str) -> Path | None:
    """Kaggle CLI writes episode-<id>-replay.json; older notes used episode-<id>.json."""
    for name in (f"episode-{ep_id}-replay.json", f"episode-{ep_id}.json"):
        p = outdir / name
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", default=DEFAULT_SLUG)
    ap.add_argument("--top-n", type=int, default=10, help="top N teams from leaderboard")
    ap.add_argument("--replays-per-team", type=int, default=7, help="last M replays per team")
    ap.add_argument("--subs-per-team", type=int, default=2, help="latest K submissions per team to mine")
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    ap.add_argument("--delay", type=float, default=0.2, help="delay between API calls")
    ap.add_argument("--retry-429-attempts", type=int, default=2, help="extra retries per replay on HTTP 429")
    ap.add_argument("--retry-429-base", type=float, default=20.0, help="base seconds for 429 exponential backoff")
    ap.add_argument("--abort-after-consecutive-429", type=int, default=12, help="stop downloading more episodes after this many consecutive 429 replay failures (0=never)")
    ap.add_argument("--skip-download", action="store_true", help="only select episodes into the manifest; do not call replay download")
    ap.add_argument("--max-downloads", type=int, default=0, help="max unique episodes to download in phase 2 (0=all)")
    ap.add_argument("--download-offset", type=int, default=0, help="skip first N unique selected episodes in phase 2 (batching)")
    ap.add_argument("--rank-start", type=int, default=0, help="only process ranks >= this (0=all)")
    ap.add_argument("--rank-end", type=int, default=0, help="only process ranks <= this (0=all)")
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

    print(f"=== Downloading top {args.top_n} teams, {args.replays_per_team} replays each, subs-per-team={getattr(args,'subs_per_team',2)} ===")
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
    ranked_teams = list(enumerate(lb_sorted[: args.top_n], 1))
    if args.rank_start or args.rank_end:
        lo = args.rank_start or 1
        hi = args.rank_end or args.top_n
        ranked_teams = [(r, t) for r, t in ranked_teams if lo <= r <= hi]
    top_teams = [t for _r, t in ranked_teams]

    print(f"\nTop {args.top_n} teams (processing {len(ranked_teams)}):")
    for i, t in ranked_teams:
        print(f"  {i}. {t.get('TeamName')} (id={t.get('TeamId')}) score={t.get('Score')}")

    # 2. For each team, get their public submissions via team_id.
    # IMPORTANT: --replays-per-team is a quota PER TEAM across all mined
    # submissions (not per submission). The previous version took 7 from each
    # of the latest 2 submissions (= up to 14/team) and, worse, only wrote
    # newly-downloaded files to the manifest, so resumable runs lost coverage.
    manifest: list[dict] = []
    status_rows: list[dict] = []
    downloaded_new = 0
    reused_existing = 0
    failed_downloads = 0
    consecutive_429 = 0
    abort_429 = False

    for rank, team in ranked_teams:
        team_id = team.get("TeamId") or team.get("teamId")
        team_name = team.get("TeamName") or team.get("teamName") or f"team_{team_id}"
        if not team_id:
            status_rows.append({"rank": rank, "team_id": "", "team_name": team_name,
                                "submission_id": "", "submissions_found": 0,
                                "episodes_found": 0, "selected_total_for_team": 0,
                                "note": "missing team_id"})
            continue

        print(f"\n{rank}. {team_name} (team_id={team_id}) — fetching submissions...")

        rc, out, err = kaggle(["competitions", "team-submissions", str(team_id), "--format", "csv", "-q"])
        if rc != 0:
            status_rows.append({"rank": rank, "team_id": team_id, "team_name": team_name,
                                "submission_id": "", "submissions_found": 0,
                                "episodes_found": 0, "selected_total_for_team": 0,
                                "note": f"team-submissions rc={rc}: {(err or out)[:240]!r}"})
            print(f"  team-submissions failed for {team_id}: {err[:300]}")
            continue

        sub_rows = rows_from_csv(out)
        if not sub_rows:
            status_rows.append({"rank": rank, "team_id": team_id, "team_name": team_name,
                                "submission_id": "", "submissions_found": 0,
                                "episodes_found": 0, "selected_total_for_team": 0,
                                "note": f"no submissions parsed; raw={(out or err)[:240]!r}"})
            print(f"  No submissions for team {team_id}")
            continue

        def sub_date(r):
            return r.get("date") or r.get("Date") or r.get("submitted") or r.get("SubmissionDate") or ""

        sub_sorted = sorted(sub_rows, key=sub_date, reverse=True)
        subs_to_mine = sub_sorted[: max(1, getattr(args, "subs_per_team", 2))]
        print(f"  Found {len(sub_rows)} submissions, mining latest {len(subs_to_mine)}; quota={args.replays_per_team}/team")

        seen_episode_ids: set[str] = set()
        selected_for_team = 0

        for sub in subs_to_mine:
            if selected_for_team >= args.replays_per_team:
                break
            sub_id = sub.get("ref") or sub.get("id") or sub.get("submissionId") or sub.get("SubmissionId")
            if not sub_id:
                status_rows.append({"rank": rank, "team_id": team_id, "team_name": team_name,
                                    "submission_id": "", "submissions_found": len(sub_rows),
                                    "episodes_found": 0, "selected_total_for_team": selected_for_team,
                                    "note": f"submission row missing id: {str(sub)[:240]!r}"})
                continue
            sub_id = str(sub_id).strip()
            print(f"    Submission {sub_id} — listing episodes...")

            rc, out, err = kaggle(["competitions", "episodes", str(sub_id), "--format", "csv", "-q"])
            ep_rows: list[dict] = []
            ep_note = ""
            if rc == 0 and out.strip() and "no episodes found" not in out.lower():
                ep_rows = rows_from_csv(out)
                if not ep_rows:
                    ep_note = f"episodes csv parsed 0 rows; raw={out[:240]!r}"
            else:
                if rc != 0:
                    ep_note = f"episodes csv rc={rc}: {(err or out)[:240]!r}"
                rc2, out2, err2 = kaggle(["competitions", "episodes", str(sub_id), "-v"])
                if rc2 == 0 and out2.strip() and "no episodes found" not in out2.lower():
                    import re

                    ids = re.findall(r"^\s*(\d{6,})", out2, flags=re.MULTILINE)
                    ep_rows = [{"id": eid} for eid in ids]
                    if ep_rows:
                        ep_note = (ep_note + " " if ep_note else "") + "fallback verbose parse used"
                elif not ep_note:
                    ep_note = f"no episodes; verbose rc={rc2}: {(err2 or out2)[:240]!r}"

            if not ep_rows:
                status_rows.append({"rank": rank, "team_id": team_id, "team_name": team_name,
                                    "submission_id": sub_id, "submissions_found": len(sub_rows),
                                    "episodes_found": 0, "selected_total_for_team": selected_for_team,
                                    "note": ep_note or "no episodes returned"})
                print(f"      No episodes for submission {sub_id}")
                continue

            print(f"      Found {len(ep_rows)} episodes; team selected so far {selected_for_team}/{args.replays_per_team}")
            for ep in ep_rows:
                if selected_for_team >= args.replays_per_team:
                    break
                ep_id = ep.get("id") or ep.get("Id") or ep.get("EpisodeId") or ep.get("episodeId")
                if not ep_id:
                    continue
                ep_id = str(ep_id).strip()
                if not ep_id.isdigit() or ep_id in seen_episode_ids:
                    continue
                seen_episode_ids.add(ep_id)

                # Phase 1: select only. Replay downloads happen in phase 2 so
                # a Kaggle 429 abort cannot destroy the already-built manifest.
                actual = existing_replay(outdir, ep_id)
                status = "existing" if actual is not None else "selected"
                if actual is not None:
                    reused_existing += 1
                selected_for_team += 1
                manifest.append(
                    {
                        "rank": rank,
                        "team_id": team_id,
                        "team_name": team_name,
                        "team_score": team.get("Score"),
                        "submission_id": sub_id,
                        "episode_id": ep_id,
                        "file": actual.name if actual is not None else "",
                        "status": status,
                    }
                )

            status_rows.append({"rank": rank, "team_id": team_id, "team_name": team_name,
                                "submission_id": sub_id, "submissions_found": len(sub_rows),
                                "episodes_found": len(ep_rows), "selected_total_for_team": selected_for_team,
                                "note": ep_note})

    # Phase 2: download unique selected episodes (batchable via offset/limit).
    # Rows sharing an episode_id are updated together.
    if not args.skip_download:
        rows_by_episode: dict[str, list[dict]] = {}
        for r in manifest:
            rows_by_episode.setdefault(r["episode_id"], []).append(r)
        unique_eps = list(rows_by_episode.keys())
        start = max(0, args.download_offset)
        end = len(unique_eps) if args.max_downloads <= 0 else min(len(unique_eps), start + args.max_downloads)
        print(f"\nPhase 2: downloading unique episodes {start}:{end} of {len(unique_eps)}")
        for idx, ep_id in enumerate(unique_eps):
            rows = rows_by_episode[ep_id]
            if idx < start or idx >= end:
                if rows and rows[0].get("status") == "selected":
                    for r in rows:
                        r["status"] = "pending_batch"
                continue
            actual = existing_replay(outdir, ep_id)
            if actual is not None:
                for r in rows:
                    r["file"] = actual.name
                    r["status"] = "existing"
                continue
            attempt = 0
            while True:
                rc, out, err = kaggle(["competitions", "replay", str(ep_id), "-p", str(outdir)])
                actual = existing_replay(outdir, ep_id)
                if rc == 0 and actual is not None:
                    downloaded_new += 1
                    consecutive_429 = 0
                    for r in rows:
                        r["file"] = actual.name
                        r["status"] = "downloaded"
                    print(f"  [{idx + 1}/{len(unique_eps)}] Downloaded {ep_id} -> {actual.name}")
                    break
                combined = f"{err}\n{out}"
                is_429 = "429" in combined or "Too Many Requests" in combined
                if is_429:
                    consecutive_429 += 1
                else:
                    consecutive_429 = 0
                if is_429 and attempt < max(0, args.retry_429_attempts):
                    wait_s = min(240.0, args.retry_429_base * (2 ** attempt))
                    print(f"  Replay {ep_id} hit Kaggle 429; retry {attempt + 1}/{args.retry_429_attempts} in {wait_s:.0f}s")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                failed_downloads += 1
                for r in rows:
                    r["status"] = "failed_429" if is_429 else "failed"
                print(f"  Failed {ep_id}: rc={rc} err={err[:240]}")
                break
            time.sleep(args.delay)
            if (args.abort_after_consecutive_429 > 0 and consecutive_429 >= args.abort_after_consecutive_429):
                abort_429 = True
                print(f"Stopping phase 2 after {consecutive_429} consecutive Kaggle 429 replay failures")
                for rest_ep in unique_eps[idx + 1:]:
                    for r in rows_by_episode[rest_ep]:
                        if r.get("status") == "selected":
                            r["status"] = "pending_429"
                break
    else:
        print("\nPhase 2 skipped (--skip-download): manifest selection only")

    # Write manifest + per-team/per-submission diagnostics. The manifest now
    # contains every selected episode (downloaded, reused, or failed), so a
    # resumable run cannot silently shrink coverage to only new downloads.
    manifest_path = outdir / "top10_manifest.csv"
    manifest_fields = ["rank", "team_id", "team_name", "team_score", "submission_id", "episode_id", "file", "status"]
    write_csv(manifest_path, manifest, manifest_fields)
    status_path = outdir / "fetch_status.csv"
    status_fields = ["rank", "team_id", "team_name", "submission_id", "submissions_found", "episodes_found", "selected_total_for_team", "note"]
    write_csv(status_path, status_rows, status_fields)

    teams_with_any = len({r["team_name"] for r in manifest})
    teams_with_quota = len({r["team_name"] for r in manifest
                            if sum(1 for x in manifest if x["team_name"] == r["team_name"]) >= args.replays_per_team})
    from collections import Counter
    status_counts = dict(Counter(r.get("status", "") for r in manifest))
    summary = {
        "fetched_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "competition": args.competition,
        "top_n": args.top_n,
        "replays_per_team": args.replays_per_team,
        "subs_per_team": getattr(args, "subs_per_team", 2),
        "teams": len(top_teams),
        "teams_with_any_episode": teams_with_any,
        "teams_with_full_quota": teams_with_quota,
        "selected_rows": len(manifest),
        "unique_episodes": len({r["episode_id"] for r in manifest}),
        "replays_downloaded": downloaded_new,
        "replays_reused_existing": reused_existing,
        "replays_failed": failed_downloads,
        "aborted_429": abort_429,
        "skip_download": bool(args.skip_download),
        "download_offset": args.download_offset,
        "max_downloads": args.max_downloads,
        "status_counts": status_counts,
        "manifest": str(manifest_path),
        "status": str(status_path),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Zip if requested (only when this run actually fetched/reused files).
    zip_path = Path(args.zip) if args.zip else outdir / "TOP10.zip"
    if downloaded_new > 0:
        print(f"\nZipping replay files into {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in outdir.glob("episode-*.json"):
                z.write(f, f.name)
            if manifest_path.exists():
                z.write(manifest_path, manifest_path.name)
        print(f"  Zip size: {zip_path.stat().st_size / 1e6:.1f} MB")

    print(f"\nDone. Selected {len(manifest)} rows ({summary['unique_episodes']} unique episodes) "
          f"for top {args.top_n}; teams_with_quota={teams_with_quota}, new={downloaded_new}, reused={reused_existing}, failed={failed_downloads}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
