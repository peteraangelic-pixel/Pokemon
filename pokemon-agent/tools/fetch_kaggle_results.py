#!/usr/bin/env python3
"""Fetch our Kaggle submission status and leaderboard rating.

WHY THIS IS A SEPARATE STEP
---------------------------
The agent sandbox has no network route to kaggle.com (only github.com,
pypi.org and a couple of package hosts are reachable). So we cannot ask Kaggle
anything from inside the workspace. GitHub Actions runners do have unrestricted
internet, so the fetch runs there, on a schedule, and commits the result back
to the branch -- where the agent can read it with a plain `git pull`.

This is the same trick the project already uses in the other direction
(runners as an escape hatch for long compute), just pointed at the network
instead of at the CPU.

AUTH
----
Reads KAGGLE_USERNAME and KAGGLE_KEY from the environment. Never commit those;
in CI they come from repository secrets, locally from your own shell or from
~/.kaggle/kaggle.json.

USAGE
-----
    pip install kaggle
    export KAGGLE_USERNAME=... KAGGLE_KEY=...
    python tools/fetch_kaggle_results.py

    # or point it at another competition / output dir
    python tools/fetch_kaggle_results.py --competition some-slug --outdir out

Outputs into <outdir>/
    submissions.csv   raw `kaggle competitions submissions` dump
    leaderboard.csv   raw leaderboard (unzipped)
    summary.json      machine-readable: our rows, parsed
    summary.md        the same thing in prose, for the file viewer
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

DEFAULT_SLUG = "the-pokemon-company-ptcg-ai-battle-challenge-playground"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(args: list[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    # keep the CLI from paging or prompting
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
    """Kaggle CLI 2.x accepts several credential sources; accept all of them.

    In order: KAGGLE_API_TOKEN env, ~/.kaggle/access_token, KAGGLE_USERNAME +
    KAGGLE_KEY env, ~/.kaggle/kaggle.json.  Our first CI run failed only
    because this check knew about the last two.
    """
    home = os.path.expanduser("~")
    if os.environ.get("KAGGLE_API_TOKEN", "").strip():
        return None
    if os.path.isfile(os.path.join(home, ".kaggle", "access_token")):
        return None
    if os.environ.get("KAGGLE_USERNAME", "").strip() and os.environ.get("KAGGLE_KEY", "").strip():
        return None
    if os.path.isfile(os.path.join(home, ".kaggle", "kaggle.json")):
        return None
    return ("no Kaggle credentials found. Set KAGGLE_API_TOKEN (recommended), "
            "or KAGGLE_USERNAME + KAGGLE_KEY, or create ~/.kaggle/access_token "
            "or ~/.kaggle/kaggle.json")


def rows_from_csv(text: str) -> list[dict]:
    text = text.strip("\ufeff").strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def pick(row: dict, *names: str):
    """Case-insensitive column lookup -- Kaggle renames these now and then."""
    low = {k.lower().strip(): v for k, v in row.items() if k}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", default=os.environ.get("KAGGLE_COMPETITION", DEFAULT_SLUG))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "kaggle_results"))
    ap.add_argument("--team", default=os.environ.get("KAGGLE_TEAM", ""),
                    help="your Kaggle team/user name, to find your own row")
    args = ap.parse_args()

    slug = args.competition
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    if not have_kaggle():
        print("ERROR: the kaggle CLI is not installed.  pip install kaggle", file=sys.stderr)
        return 2
    def _write_failure(msg: str) -> None:
        """Leave the error in the repo -- Actions logs are unreadable here."""
        with open(os.path.join(outdir, "summary.json"), "w") as fh:
            json.dump({"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "competition": slug, "problems": [msg]}, fh, indent=2)
        with open(os.path.join(outdir, "summary.md"), "w") as fh:
            fh.write(f"# Kaggle results - {slug}\n\n## FAILED\n\n{msg}\n")

    err = check_auth()
    if err:
        _write_failure(err)
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    team = args.team or os.environ.get("KAGGLE_USERNAME", "")
    problems: list[str] = []

    # ---- submissions: status (complete / error) + score -------------------
    rc, out, stderr = kaggle(["competitions", "submissions", "-c", slug,
                              "--format", "csv", "--page-size", "200", "-q"])
    subs: list[dict] = []
    if rc != 0:
        problems.append(f"submissions failed: {(stderr or out).strip()[:200]}")
    else:
        subs = rows_from_csv(out)
        with open(os.path.join(outdir, "submissions.csv"), "w") as fh:
            fh.write(out.strip() + "\n")

    # ---- leaderboard: rating (mu) ----------------------------------------
    rc, out, stderr = kaggle(["competitions", "leaderboard", "-c", slug,
                              "-d", "-p", outdir, "-q"])
    lb: list[dict] = []
    if rc != 0:
        problems.append(f"leaderboard download failed: {(stderr or out).strip()[:200]}")
    else:
        zpath = os.path.join(outdir, f"{slug}.zip")
        if os.path.exists(zpath):
            try:
                with zipfile.ZipFile(zpath) as z:
                    names = z.namelist()
                    inner = names[0] if names else f"{slug}.csv"
                    data = z.read(inner).decode("utf-8", "replace")
                with open(os.path.join(outdir, "leaderboard.csv"), "w") as fh:
                    fh.write(data.strip() + "\n")
                lb = rows_from_csv(data)
                os.remove(zpath)
            except Exception as exc:  # noqa: BLE001
                problems.append(f"could not unzip leaderboard: {exc}")
        else:
            problems.append(f"leaderboard zip not found at {zpath}")

    # ---- our own rows -----------------------------------------------------
    def is_ours(row: dict) -> bool:
        if not team:
            return True
        nm = (pick(row, "TeamName", "teamName", "Team", "team") or "")
        return nm.strip().lower() == team.strip().lower()

    our_lb = [r for r in lb if is_ours(r)]
    # newest submission first, whichever date column exists
    def sdate(row: dict) -> str:
        return (pick(row, "Submitted", "submitted", "Date", "date",
                     "SubmissionDate", "submissionDate") or "")

    subs_sorted = sorted(subs, key=sdate, reverse=True)

    summary = {
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "competition": slug,
        "team": team or "(unknown - pass --team to filter)",
        "leaderboard_rows": len(lb),
        "submission_rows": len(subs),
        "our_leaderboard": our_lb,
        "latest_submissions": subs_sorted[:10],
        "problems": problems,
    }
    with open(os.path.join(outdir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    # ---- human-readable --------------------------------------------------
    lines: list[str] = []
    lines.append(f"# Kaggle results — {slug}")
    lines.append("")
    lines.append(f"_fetched {summary['fetched_utc']}_")
    lines.append("")
    if problems:
        lines.append("## ⚠️ problems")
        lines.append("")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")

    lines.append("## Our leaderboard row")
    lines.append("")
    if not our_lb:
        lines.append("_no row found"
                     + (f" for team `{team}`" if team else " (pass `--team`)") + "_")
    for r in our_lb:
        score = pick(r, "Score", "score", "PublicScore", "publicScore")
        lines.append(f"- **score (μ): {score}**")
        for k, v in r.items():
            if k.lower() not in ("score",):
                lines.append(f"  - {k}: {v}")
    lines.append("")

    lines.append("## Latest submissions (newest first)")
    lines.append("")
    if not subs_sorted:
        lines.append("_none_")
    else:
        lines.append("| file | status | score | date |")
        lines.append("|---|---|---|---|")
        for r in subs_sorted[:10]:
            f = pick(r, "FileName", "fileName", "file") or ""
            st = pick(r, "Status", "status") or ""
            sc = pick(r, "PublicScore", "publicScore", "Score", "score") or ""
            dt = sdate(r)
            lines.append(f"| `{f}` | {st} | {sc} | {dt} |")
    lines.append("")

    if lb:
        lines.append("## Leaderboard top 10")
        lines.append("")
        hdr = list(lb[0].keys())
        lines.append("| " + " | ".join(hdr) + " |")
        lines.append("|" + "---|" * len(hdr))
        for r in lb[:10]:
            lines.append("| " + " | ".join(str(r.get(h, "")) for h in hdr) + " |")
        lines.append("")

    with open(os.path.join(outdir, "summary.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"wrote {outdir}/summary.json + summary.md")
    print(f"  leaderboard rows: {len(lb)}   submissions: {len(subs)}")
    for r in our_lb:
        print(f"  OUR SCORE (mu): {pick(r, 'Score', 'score')}")
    for r in subs_sorted[:2]:
        print(f"  latest: {pick(r, 'FileName', 'fileName')} -> "
              f"{pick(r, 'Status', 'status')} "
              f"{pick(r, 'PublicScore', 'publicScore', 'Score', 'score')}")
    if problems:
        for p in problems:
            print(f"  PROBLEM: {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
