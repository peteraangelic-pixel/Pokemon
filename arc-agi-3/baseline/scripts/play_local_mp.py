"""Fast local ARC-AGI-3 runner with multiprocessing Pool.

Based on pattern from c87f7a48-pokemon (96k samples in 115s vs 24min sequential).
Each game runs in a separate worker process for parallel execution.

Usage:
  python3 play_local_mp.py --game ls20,vc33 --workers 4
  python3 play_local_mp.py --all --workers 8 --report report.json
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from multiprocessing import Pool
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
    meter_evidence: dict[str, int] = field(default_factory=dict)
    token_evidence: dict[str, int] = field(default_factory=dict)
    policy_trace: list[dict[str, Any]] = field(default_factory=list)
    graph_evidence: dict[str, int] = field(default_factory=dict)


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


# Global state for workers
_GLOBAL = {}


def worker_init(max_steps: int, record: bool):
    """Initialize worker with agent class and settings."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    
    MyAgent = load_agent_class()
    MyAgent.ACTION_BUDGET = max_steps
    MyAgent.MAX_ACTIONS = max_steps
    
    import arc_agi
    from arc_agi import OperationMode
    
    recordings_dir = ROOT / "recordings"
    os.environ["RECORDINGS_DIR"] = str(recordings_dir)
    
    arcade = arc_agi.Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(ROOT / "environment_files"),
        recordings_dir=str(recordings_dir),
    )
    
    _GLOBAL["MyAgent"] = MyAgent
    _GLOBAL["arcade"] = arcade
    _GLOBAL["record"] = record
    _GLOBAL["max_steps"] = max_steps


def run_one_game(game_id: str) -> RunResult | None:
    """Run a single game in a worker process."""
    MyAgent = _GLOBAL["MyAgent"]
    arcade = _GLOBAL["arcade"]
    record = _GLOBAL["record"]
    max_steps = _GLOBAL["max_steps"]
    
    try:
        env = arcade.make(game_id, save_recording=record)
        if env is None:
            print(f"[{game_id}] Could not create environment; skipped.", file=sys.stderr)
            return None
        
        agent = MyAgent(
            card_id="local-dev",
            game_id=game_id,
            agent_name=f"novelty-v5.{game_id}",
            ROOT_URL="http://localhost",
            record=record,
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
            graph_evidence=getattr(agent.policy, "graph_evidence", dict)(),
            meter_evidence=agent.policy.meter_evidence(),
            token_evidence=agent.policy.token_evidence(),
            policy_trace=agent.policy.transition_trace(limit=_policy_trace_limit(max_steps)),
        )
        
        print(
            f"[{game_id}] state={result.state} levels={result.levels_completed} actions={result.actions}",
            file=sys.stderr
        )
        return result
        
    except Exception as e:
        print(f"[{game_id}] ERROR: {e}", file=sys.stderr)
        return None


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
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes (default: 4).")
    args = parser.parse_args()

    if args.max_steps < 1:
        parser.error("--max-steps must be positive")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    # Load environments to get game list
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    
    import arc_agi
    from arc_agi import OperationMode
    
    recordings_dir = ROOT / "recordings"
    os.environ["RECORDINGS_DIR"] = str(recordings_dir)
    arcade = arc_agi.Arcade(
        operation_mode=OperationMode.OFFLINE,
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

    print(f"Running {len(game_ids)} games with {args.workers} workers...")
    
    # Parallel execution
    with Pool(processes=args.workers, initializer=worker_init, initargs=(args.max_steps, args.record)) as pool:
        results_list = pool.map(run_one_game, game_ids)
    
    # Filter out None results
    results = [r for r in results_list if r is not None]
    
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
