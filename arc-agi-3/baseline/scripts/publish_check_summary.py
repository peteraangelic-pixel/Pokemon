"""Publish a credential-free ARC run summary to the current GitHub check.

This is deliberately a best-effort reporting helper. A reporting API failure
must not turn a completed game run into a false failure, so callers should run
it after the actual test and it returns successfully after emitting a warning.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

API_VERSION = "2022-11-28"


def _safe(value: Any) -> str:
    return str(value).replace("|", "\\|")


def _safe_mode(value: Any) -> str:
    """Keep public policy-mode diagnostics bounded and non-free-form."""
    text = value if isinstance(value, str) else "unspecified"
    if (
        not text
        or len(text) > 80
        or not all(character.islower() or character.isdigit() or character == "-" for character in text)
    ):
        return "unspecified"
    return text


def _modes_by_resulting_level(trace: list[Any]) -> list[str]:
    """Summarize bounded policy modes by visually observed progress phase.

    The runner records the level count returned after each submitted action.
    Aggregating it here exposes where an explorer spends its budget without
    publishing board coordinates, pixels, free-form reasoning, or game rules.
    """
    phases: dict[int, dict[str, int]] = {}
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        level = entry.get("levels_completed")
        if not isinstance(level, int) or isinstance(level, bool) or level < 0:
            continue
        modes = phases.setdefault(level, {})
        mode = _safe_mode(entry.get("decision_kind"))
        modes[mode] = modes.get(mode, 0) + 1
    output: list[str] = []
    for level, modes in sorted(phases.items())[:12]:
        rendered = "; ".join(
            f"{mode}: {count}"
            for mode, count in sorted(modes.items(), key=lambda item: item[0])
        )
        output.append(f"L{level}: {rendered}")
    return output


def build_summary(report_path: Path, sketch_path: Path, log_path: Path) -> str:
    """Create bounded Markdown from trusted local report/sketch artifacts."""
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = report.get("results", [])
        if not isinstance(rows, list):
            rows = []
        summary = [
            "### ARC public-game run",
            "",
            "| Game | Final state | Levels | Actions |",
            "| --- | --- | ---: | ---: |",
        ]
        for row in rows:
            if not isinstance(row, dict):
                continue
            summary.append(
                "| {game} | {state} | {levels} | {actions} |".format(
                    game=_safe(row.get("game_id", "?")),
                    state=_safe(row.get("state", "?")),
                    levels=row.get("levels_completed", 0),
                    actions=row.get("actions", 0),
                )
            )
        if not rows:
            summary.append("| _none_ | no completed game report | 0 | 0 |")

        summary.extend(["", "#### Probe evidence"])
        for row in rows:
            if not isinstance(row, dict):
                continue
            evidence = []
            raw_evidence = row.get("policy_evidence", {})
            if isinstance(raw_evidence, dict):
                for action, stats in sorted(raw_evidence.items()):
                    if not isinstance(stats, dict):
                        continue
                    evidence.append(
                        "{action}: {changed}/{attempts} changed, {gains} level gains, {overs} game overs".format(
                            action=_safe(action),
                            changed=stats.get("changed", 0),
                            attempts=stats.get("attempts", 0),
                            gains=stats.get("level_gains", 0),
                            overs=stats.get("game_overs", 0),
                        )
                    )
            summary.append(
                "- **{game}** — {evidence}".format(
                    game=_safe(row.get("game_id", "?")),
                    evidence="; ".join(evidence) or "no completed transitions",
                )
            )
            raw_decisions = row.get("policy_decisions", {})
            if isinstance(raw_decisions, dict):
                decisions = [
                    "{mode}: {count}".format(mode=_safe_mode(mode), count=count)
                    for mode, count in sorted(raw_decisions.items(), key=lambda item: str(item[0]))
                    if isinstance(count, int) and not isinstance(count, bool) and count > 0
                ]
                if decisions:
                    summary.append("  - Decision modes: " + "; ".join(decisions))
            trace = row.get("policy_trace", [])
            if isinstance(trace, list):
                phase_modes = _modes_by_resulting_level(trace)
                if phase_modes:
                    summary.append("  - Modes by resulting level: " + " | ".join(phase_modes))
            raw_meter_evidence = row.get("meter_evidence", {})
            if isinstance(raw_meter_evidence, dict):
                meter_evidence = [
                    "{mode}: {count}".format(mode=_safe_mode(mode), count=count)
                    for mode, count in sorted(raw_meter_evidence.items(), key=lambda item: str(item[0]))
                    if isinstance(count, int) and not isinstance(count, bool) and count > 0
                ]
                if meter_evidence:
                    summary.append("  - Meter evidence: " + "; ".join(meter_evidence))
            raw_token_evidence = row.get("token_evidence", {})
            if isinstance(raw_token_evidence, dict):
                token_evidence = [
                    "{mode}: {count}".format(mode=_safe_mode(mode), count=count)
                    for mode, count in sorted(raw_token_evidence.items(), key=lambda item: str(item[0]))
                    if isinstance(count, int) and not isinstance(count, bool) and count > 0
                ]
                if token_evidence:
                    summary.append("  - Token/control evidence: " + "; ".join(token_evidence))
            trace = row.get("policy_trace", [])
            if isinstance(trace, list):
                recent = [entry for entry in trace[-8:] if isinstance(entry, dict)]
                if recent:
                    summary.append(
                        "  - Recent probes: "
                        + ", ".join(
                            "{action} ({outcome})".format(
                                action=_safe(entry.get("action", "?")),
                                outcome="changed" if entry.get("changed") else "no visible change",
                            )
                            for entry in recent
                        )
                    )
        summary.extend(
            [
                "",
                f"Scorecard: `{_safe(report.get('scorecard'))}`.",
                "Full diagnostics and any recording are retained for 14 days as a workflow artifact.",
            ]
        )
    else:
        tail = (
            log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            if log_path.is_file()
            else "No log was produced."
        )
        summary = [
            "### ARC public-game run",
            "",
            "No structured report was produced. Log tail:",
            "```text",
            tail,
            "```",
        ]

    if sketch_path.is_file():
        summary.extend(
            [
                "",
                sketch_path.read_text(encoding="utf-8", errors="replace")[:48000],
            ]
        )
    return "\n".join(summary)[:65000]


def _api(url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": API_VERSION,
        },
        method="GET" if payload is None else "PATCH",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def publish(check_name: str, summary: str) -> None:
    """Update the current Actions check output using its ephemeral job token."""
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    base = f"https://api.github.com/repos/{repo}"
    runs = _api(f"{base}/commits/{sha}/check-runs", token)
    target = max(
        (run for run in runs["check_runs"] if run["name"] == check_name),
        key=lambda run: run["id"],
    )
    _api(
        f"{base}/check-runs/{target['id']}",
        token,
        {"output": {"title": "ARC public-game run", "summary": summary}},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-name", required=True, help="Exact GitHub Actions job display name")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sketches", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    try:
        publish(args.check_name, build_summary(args.report, args.sketches, args.log))
    except Exception as error:  # noqa: BLE001 - reporting is intentionally non-fatal
        print(f"Warning: could not publish ARC run summary: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
