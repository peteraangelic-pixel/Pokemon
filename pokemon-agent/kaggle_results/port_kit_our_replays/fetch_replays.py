#!/usr/bin/env python3
"""Fetch PTCG replays — our own episodes + official top-episodes dataset.

This is the PTCG equivalent of the Kaggriculture replay archive.

WHY TWO SOURCES
---------------
1. Our own episodes: `kaggle competitions episodes <submission_id>` gives us the
   last games our agent played, with opponent team names and submissionIds.
   From those we can see who beats us and how.

2. Official daily top-episodes dataset:
   `kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-01`
   (and newer dates if they exist). Kaggle publishes ~20 GiB/day of top replays
   ranked by average agent rating. This is the same idea as
   `ashok205/kaggriculture-top10-replay-archive` from the previous project.

   The dataset is public and downloadable via `kaggle datasets download`.

Both are fetched in GitHub Actions (which has internet to Kaggle), committed
back to the branch, and then analyzed locally or in a second Actions step.

USAGE (in Actions)
------------------
    pip install kaggle
    export KAGGLE_API_TOKEN=...
    python tools/fetch_replays.py --competition ... --outdir kaggle_results/replays --top-k 7

Outputs
-------
    kaggle_results/replays/
        episodes_*.csv          # raw episode list per submission
        episode-<id>-replay.json # downloaded replays
        manifest.csv            # from official dataset (if fetched)
        summary.json            # machine-readable index
        summary.md              # human-readable
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SLUG = "the-pokemon-company-ptcg-ai-battle-challenge-playground"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "kaggle_results" / "replays"

# Official daily top-episodes datasets — try in order, newest first.
# The 2026-10-01 one is confirmed to exist (731 MB). Newer dates may appear.
OFFICIAL_DATASETS = [
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-09",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-08",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-07",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-06",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-05",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-04",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-03",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-02",
    "kaggle/the-pokemon-company-ptcg-ai-battle-challenge-playground-episodes-2026-10-01",
]


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


def list_our_submissions(slug: str) -> list[dict]:
    rc, out, err = kaggle(["competitions", "submissions", "-c", slug, "--format", "csv", "--page-size", "200", "-q"])
    if rc != 0:
        print(f"submissions failed: {(err or out)[:500]}", file=sys.stderr)
        return []
    return rows_from_csv(out)


def list_episodes(submission_id: str, out_path: Path) -> list[dict]:
    """List episodes for a submission, save raw output, return parsed rows if csv."""
    # Try csv first
    rc, out, err = kaggle(["competitions", "episodes", str(submission_id), "--format", "csv", "-q"])
    if rc == 0 and out.strip():
        out_path.write_text(out.strip() + "\n", encoding="utf-8")
        rows = rows_from_csv(out)
        if rows:
            return rows
    # Fallback to verbose text
    rc, out, err = kaggle(["competitions", "episodes", str(submission_id), "-v"])
    if rc != 0:
        print(f"episodes {submission_id} failed: {(err or out)[:500]}", file=sys.stderr)
        return []
    out_path.write_text(out, encoding="utf-8")
    # Parse episode ids from verbose output: lines starting with digits
    ids = re.findall(r"^\s*(\d{6,})", out, flags=re.MULTILINE)
    # Return as dicts with id
    return [{"id": eid, "EpisodeId": eid} for eid in ids]


def download_replay(episode_id: str, dest_dir: Path) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    rc, out, err = kaggle(["competitions", "replay", str(episode_id), "-p", str(dest_dir)])
    if rc != 0:
        print(f"replay {episode_id} failed: {(err or out)[:500]}", file=sys.stderr)
        return False
    # kaggle CLI writes episode-<id>-replay.json
    expected = dest_dir / f"episode-{episode_id}-replay.json"
    if expected.exists():
        return True
    # Some versions write without prefix
    found = list(dest_dir.glob(f"*{episode_id}*.json"))
    return len(found) > 0


def try_download_official_dataset(dest_dir: Path) -> tuple[str | None, int]:
    """Try official datasets in order, return (dataset_slug, file_count) or (None,0)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for ds in OFFICIAL_DATASETS:
        print(f"Trying official dataset {ds}...")
        rc, out, err = kaggle(["datasets", "download", "-d", ds, "-p", str(dest_dir), "--unzip", "-q"])
        if rc == 0:
            # Count json files
            count = len(list(dest_dir.rglob("*.json")))
            # Also look for manifest.csv
            manifests = list(dest_dir.rglob("manifest.csv"))
            print(f"  -> got {count} json files, {len(manifests)} manifests from {ds}")
            return ds, count
        else:
            print(f"  {ds} not available: {(err or out)[:300]}")
    # Also try to list datasets matching pattern
    rc, out, err = kaggle(["datasets", "list", "-s", "ptcg-ai-battle-challenge-playground-episodes", "--format", "csv"])
    if rc == 0:
        print("Available episode datasets:")
        print(out[:2000])
    return None, 0


def analyze_replay_file(path: Path) -> dict:
    """Lightweight analysis of a PTCG replay JSON — extract teams, winner, steps."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"file": path.name, "error": str(exc)}

    info = data.get("info") or {}
    # Kaggle replay format varies; try common fields
    team_names = info.get("TeamNames") or info.get("teamNames") or []
    episode_id = info.get("EpisodeId") or info.get("episodeId") or path.stem

    steps = data.get("steps") or []
    # Last step has rewards
    winner = None
    rewards = []
    if steps:
        last = steps[-1]
        if isinstance(last, list) and len(last) >= 2:
            r0 = last[0].get("reward")
            r1 = last[1].get("reward")
            rewards = [r0, r1]
            if r0 == 1:
                winner = team_names[0] if len(team_names) > 0 else "P0"
            elif r1 == 1:
                winner = team_names[1] if len(team_names) > 1 else "P1"
            else:
                winner = "draw"

    # Try to extract deck ids from first observation (engine stores deck)
    # The first step's observation may contain players' decks? Let's look.
    deck_info = []
    try:
        if steps and isinstance(steps[0], list):
            for p in range(min(2, len(steps[0]))):
                obs = steps[0][p].get("observation") or {}
                cur = obs.get("current") or {}
                players = cur.get("players") or []
                if players and len(players) > p:
                    # deck not directly in observation, but we can try to find
                    pass
    except Exception:
        pass

    return {
        "file": path.name,
        "episodeId": episode_id,
        "teamNames": team_names,
        "winner": winner,
        "rewards": rewards,
        "steps": len(steps),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", default=os.environ.get("KAGGLE_COMPETITION", DEFAULT_SLUG))
    ap.add_argument("--outdir", default=str(DEFAULT_OUT))
    ap.add_argument("--top-k", type=int, default=7, help="last N episodes per submission to download")
    ap.add_argument("--include-official", action="store_true", default=True, help="also try official top-episodes dataset")
    ap.add_argument("--no-official", dest="include_official", action="store_false")
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

    print(f"Fetching replays into {outdir}")

    # 1. Our submissions
    subs = list_our_submissions(args.competition)
    print(f"Found {len(subs)} own submissions")
    # Sort by date newest first
    def sdate(r):
        return r.get("date") or r.get("Date") or r.get("submitted") or ""
    subs_sorted = sorted(subs, key=sdate, reverse=True)

    all_episodes: list[dict] = []
    downloaded = 0

    for sub in subs_sorted[:2]:  # latest 2 live submissions
        ref = sub.get("ref") or sub.get("id") or sub.get("submissionId")
        if not ref:
            continue
        print(f"\n=== Submission {ref} ({sub.get('fileName')}) ===")
        ep_path = outdir / f"episodes_{ref}.csv"
        eps = list_episodes(str(ref), ep_path)
        print(f"  episodes listed: {len(eps)}")
        all_episodes.extend(eps)

        # Download last top-k
        # Episode list is usually newest first? Assume as listed, take first K
        for ep in eps[: args.top_k]:
            eid = ep.get("id") or ep.get("Id") or ep.get("EpisodeId") or ep.get("episodeId")
            if not eid:
                continue
            eid = str(eid).strip()
            if not eid.isdigit():
                continue
            ok = download_replay(eid, outdir)
            if ok:
                downloaded += 1
                print(f"  downloaded replay {eid}")

    # 2. Official dataset
    official_slug = None
    official_count = 0
    if args.include_official:
        print("\n=== Trying official top-episodes dataset ===")
        official_slug, official_count = try_download_official_dataset(outdir / "official")

    # 3. Analyze what we have
    replays = list(outdir.rglob("*.json"))
    # Exclude summary.json
    replays = [p for p in replays if p.name not in ("summary.json",)]
    print(f"\nTotal replay JSONs on disk: {len(replays)}")

    analyzed = []
    for rp in replays[:100]:  # limit analysis to first 100 to keep it fast
        analyzed.append(analyze_replay_file(rp))

    summary = {
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "competition": args.competition,
        "own_submissions": len(subs),
        "episodes_listed": len(all_episodes),
        "replays_downloaded": downloaded,
        "official_dataset": official_slug,
        "official_files": official_count,
        "total_json_on_disk": len(replays),
        "sample_analysis": analyzed[:20],
    }

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Human readable
    lines = []
    lines.append(f"# Replays — {args.competition}")
    lines.append("")
    lines.append(f"_fetched {summary['fetched_utc']}_")
    lines.append("")
    lines.append(f"- Own submissions: {len(subs)}")
    lines.append(f"- Episodes listed: {len(all_episodes)}")
    lines.append(f"- Replays downloaded (our last {args.top_k} per live sub): {downloaded}")
    lines.append(f"- Official dataset: {official_slug or 'none found'} ({official_count} files)")
    lines.append(f"- Total JSON on disk: {len(replays)}")
    lines.append("")
    lines.append("## Recent episodes (our agents)")
    lines.append("")
    for ep in all_episodes[:20]:
        lines.append(f"- {ep}")
    lines.append("")
    lines.append("## Sample replay analysis (first 20)")
    lines.append("")
    for a in analyzed[:20]:
        lines.append(f"- {a.get('file')}: teams={a.get('teamNames')} winner={a.get('winner')} steps={a.get('steps')}")

    (outdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {outdir}/summary.json + summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
