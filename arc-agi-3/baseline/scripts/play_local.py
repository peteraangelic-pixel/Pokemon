"""Run the local ARC-AGI-3 novelty-explorer against public environments.

This runner uses the official MIT-licensed ARC-AGI-3-Agents framework after it
has been cloned to ``vendor/`` by ``make setup``. It is intentionally separate
from Kaggle submission mode: a local run is an inexpensive debugging signal,
not a leaderboard submission.
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ARC-AGI-3-Agents"
MAX_POLICY_TRACE_REPORT_STEPS = 1_000


def _policy_trace_limit(action_budget: int) -> int:
    """Keep a report's frame-free policy trace bounded and useful."""
    return min(max(1, action_budget), MAX_POLICY_TRACE_REPORT_STEPS)


@dataclass(frozen=True)
class RunResult:
    """Small, credential-free outcome record for a completed local game."""

    game_id: str
    state: str
    levels_completed: int
    actions: int
    policy_evidence: dict[str, dict[str, int]]
    policy_decisions: dict[str, int]
    meter_evidence: dict[str, int]
    token_evidence: dict[str, int]
    policy_trace: list[dict[str, Any]]


def _state_name(value: object) -> str:
    """Serialize SDK enums and stand-in values consistently in reports."""
    raw = getattr(value, "value", value)
    return str(raw).rsplit(".", 1)[-1].upper()


def write_report(
    path: Path,
    *,
    requested_games: list[str],
    results: list[RunResult],
    scorecard: object | None,
) -> None:
    """Write a compact JSON report without frames, credentials, or API URLs."""
    score = getattr(scorecard, "score", scorecard)
    payload = {
        "schema_version": 1,
        "requested_games": requested_games,
        "results": [asdict(result) for result in results],
        "scorecard": None if score is None else str(score),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_framework() -> None:
    """Copy the current source agent into the generated framework checkout."""
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "prepare_framework.py")],
        check=True,
    )


def load_agent_class():
    if not VENDOR.is_dir():
        raise SystemExit(f"Framework not found at {VENDOR}. Run `make setup` first.")
    prepare_framework()
    sys.path.insert(0, str(VENDOR))
    module = importlib.import_module("agents.templates.my_agent")
    return module.MyAgent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game",
        default="ls20,vc33",
        help="Comma-separated short game IDs; use --all for every discovered game.",
    )
    parser.add_argument("--all", action="store_true", help="Play all discovered local/remote games.")
    parser.add_argument("--list", action="store_true", help="List discovered games and exit.")
    parser.add_argument("--max-steps", type=int, default=120, help="Per-game action ceiling.")
    parser.add_argument("--record", action="store_true", help="Save JSONL recordings under recordings/.")
    parser.add_argument(
        "--report",
        type=Path,
        help="Write a compact JSON outcome report (no frames or credentials).",
    )
    parser.add_argument("--offline", action="store_true", help="Use only already-downloaded game files.")
    args = parser.parse_args()

    if args.max_steps < 1:
        parser.error("--max-steps must be positive")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Optional local ARC_API_KEY lives in ignored .env and unlocks the full
    # public game catalogue. The baseline still works with anonymous access.
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    MyAgent = load_agent_class()

    import arc_agi
    from arc_agi import OperationMode

    mode = OperationMode.OFFLINE if args.offline else OperationMode.NORMAL
    recordings_dir = ROOT / "recordings"
    # The SDK receives this directory as a constructor argument, while the
    # reference framework's Recorder reads only RECORDINGS_DIR. Keep both
    # components aligned so --record never drops JSONL files into the source
    # tree or outside the ignored recordings directory.
    os.environ["RECORDINGS_DIR"] = str(recordings_dir)
    arcade = arc_agi.Arcade(
        operation_mode=mode,
        environments_dir=str(ROOT / "environment_files"),
        recordings_dir=str(recordings_dir),
    )
    environments = arcade.get_environments()

    if args.list:
        for env in environments:
            print(f"{env.game_id}\t{getattr(env, 'title', '')}")
        return
    if not environments:
        raise SystemExit(
            "No environments available. Run without --offline while connected to the "
            "ARC service, or add the public environment files first."
        )

    known = {env.game_id.split("-", 1)[0] for env in environments}
    requested = {game.strip().split("-", 1)[0] for game in args.game.split(",") if game.strip()}
    game_ids = sorted(known if args.all else known.intersection(requested))
    missing = requested - known if not args.all else set()
    if missing:
        raise SystemExit(f"Unknown/unavailable game IDs: {sorted(missing)}. Try --list.")
    if not game_ids:
        raise SystemExit("No games selected.")

    # Keep the runner's public ceiling exact even though the upstream loop uses
    # ``<= MAX_ACTIONS`` internally.
    MyAgent.ACTION_BUDGET = args.max_steps
    MyAgent.MAX_ACTIONS = args.max_steps
    results: list[RunResult] = []
    for game_id in game_ids:
        print(f"\n=== {game_id} ===")
        env = arcade.make(game_id, save_recording=args.record)
        if env is None:
            print("Could not create environment; skipped.")
            continue
        agent = MyAgent(
            card_id="local-dev",
            game_id=game_id,
            agent_name=f"novelty-v5.{game_id}",
            ROOT_URL="http://localhost",
            record=args.record,
            arc_env=env,
            tags=["local-dev", "novelty-v5"],
        )
        agent.main()
        agent.finalize_diagnostics()
        final = agent.frames[-1]
        result = RunResult(
            game_id=game_id,
            state=_state_name(final.state),
            levels_completed=int(final.levels_completed),
            actions=int(agent.action_counter),
            policy_evidence=agent.policy.diagnostics(),
            policy_decisions=agent.policy.decision_evidence(),
            meter_evidence=agent.policy.meter_evidence(),
            token_evidence=agent.policy.token_evidence(),
            policy_trace=agent.policy.transition_trace(limit=_policy_trace_limit(args.max_steps)),
        )
        results.append(result)
        print(
            f"state={result.state} levels={result.levels_completed} "
            f"actions={result.actions}"
        )
        print(f"policy evidence={result.policy_evidence}")

    print("\n=== summary ===")
    for result in results:
        print(
            f"{result.game_id}: state={result.state}, "
            f"levels={result.levels_completed}, actions={result.actions}"
        )
    scorecard = arcade.get_scorecard()
    if scorecard is not None:
        print(f"local scorecard score={getattr(scorecard, 'score', scorecard)}")
    if args.report:
        write_report(
            args.report,
            requested_games=game_ids,
            results=results,
            scorecard=scorecard,
        )
        print(f"outcome report={args.report}")


if __name__ == "__main__":
    main()
