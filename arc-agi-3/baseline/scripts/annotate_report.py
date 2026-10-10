"""Emit a local-run report as GitHub Actions annotations.

The agent sandbox cannot read Actions logs, but it CAN read annotations via
`gh run view <run-id>`. This turns a JSON report into `::notice::` lines so the
outcome is visible without downloading artifacts or logs.

Usage:
    python scripts/annotate_report.py recordings/local-smoke-report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _escape(value: str) -> str:
    return (
        value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )


def emit(title: str, body: str) -> None:
    print(f"::notice title={_escape(title)}::{_escape(body)}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: annotate_report.py <report.json> [more.json ...]", file=sys.stderr)
        return 2

    for raw in sys.argv[1:]:
        path = Path(raw)
        if not path.is_file():
            emit(str(path), "MISSING -- the run probably failed before writing it")
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            emit(str(path), f"unparseable JSON: {exc}")
            continue

        # Struktura raportu rozni sie miedzy wersjami runnera; najpierw
        # probujemy znanych kluczy, potem dowolnej listy slownikow.
        runs = None
        if isinstance(payload, dict):
            for key in ("runs", "results", "games", "outcomes"):
                if isinstance(payload.get(key), list):
                    runs = payload[key]
                    break
            if runs is None:
                runs = [payload]
        elif isinstance(payload, list):
            runs = payload
        if not runs:
            runs = []
        if isinstance(payload, dict) and "scorecard" in str(payload)[:2000]:
            emit(f"scorecard -- {path.name}", str(payload.get("scorecard")))

        lines = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            lines.append(
                "  {game:<6} state={state}  levels={levels}  actions={actions}".format(
                    game=run.get("game_id", "?"),
                    state=run.get("state", "?"),
                    levels=run.get("levels_completed", "?"),
                    actions=run.get("actions", "?"),
                )
            )
            decisions = run.get("policy_decisions") or {}
            if isinstance(decisions, dict) and decisions:
                top = sorted(decisions.items(), key=lambda kv: -kv[1])[:6]
                lines.append(
                    "      modes: "
                    + ", ".join(f"{k}={v}" for k, v in top)
                )
            evidence = run.get("policy_evidence") or {}
            if isinstance(evidence, dict):
                flags = {
                    k: v
                    for k, v in evidence.items()
                    if isinstance(v, dict) and any(v.values())
                }
                if flags:
                    lines.append("      evidence keys: " + ", ".join(sorted(flags)[:8]))

        emit(f"ARC-AGI-3 local run -- {path.name}", "\n".join(lines) or "(no runs)")
        raw = json.dumps(payload, ensure_ascii=False)
        if raw and raw not in ("{}", "[]"):
            emit(f"raw JSON -- {path.name}", raw[:1200])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
