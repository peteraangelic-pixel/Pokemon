"""Fast LLM agent runner with multiprocessing Pool.

Run multiple games in parallel with LLM agent.
Based on pattern from c87f7a48-pokemon (96k samples in 115s vs 24min sequential).

Usage:
  python3 run_games_fast.py --game ls20,vc33 --workers 4
  python3 run_games_fast.py --all --workers 8 --report report.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class GameResult:
    game_id: str
    state: str
    levels_completed: int
    actions: int
    tokens_used: int
    error: str | None = None


# Global state for workers
_GLOBAL = {}


def worker_init(llm_base_url: str, llm_model: str, max_actions: int):
    """Initialize worker with LLM config."""
    _GLOBAL["llm_base_url"] = llm_base_url
    _GLOBAL["llm_model"] = llm_model
    _GLOBAL["max_actions"] = max_actions


def run_one_game(game_id: str) -> GameResult:
    """Run a single game with LLM agent in a worker process."""
    llm_base_url = _GLOBAL["llm_base_url"]
    llm_model = _GLOBAL["llm_model"]
    max_actions = _GLOBAL["max_actions"]
    
    # Set environment variables for this worker
    os.environ["LLM_BASE_URL"] = llm_base_url
    os.environ["LLM_MODEL"] = llm_model
    
    try:
        # Import here to avoid issues with multiprocessing
        sys.path.insert(0, str(ROOT))
        from llm_agent.llm_policy_v4 import LLMPolicy, Config
        
        config = Config(max_actions=max_actions)
        policy = LLMPolicy(config)
        
        # Mock frame for testing (real implementation would use arc_agi)
        # This is a placeholder - real implementation needs actual game environment
        result = GameResult(
            game_id=game_id,
            state="NOT_IMPLEMENTED",
            levels_completed=0,
            actions=0,
            tokens_used=0,
            error="Real game environment not implemented yet"
        )
        
        print(f"[{game_id}] {result.state} (error: {result.error})", file=sys.stderr)
        return result
        
    except Exception as e:
        print(f"[{game_id}] ERROR: {e}", file=sys.stderr)
        return GameResult(
            game_id=game_id,
            state="ERROR",
            levels_completed=0,
            actions=0,
            tokens_used=0,
            error=str(e)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default="ls20,vc33", help="Comma-separated game IDs")
    parser.add_argument("--all", action="store_true", help="Run all games")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes")
    parser.add_argument("--max-actions", type=int, default=400, help="Max actions per game")
    parser.add_argument("--llm-base-url", default="http://localhost:9000/v1", help="LLM API base URL")
    parser.add_argument("--llm-model", default="qwen2.5-7b", help="LLM model name")
    parser.add_argument("--report", type=Path, help="Write JSON report")
    args = parser.parse_args()

    # Get game list
    if args.all:
        # TODO: Get all available games from arcade
        game_ids = ["ls20", "vc33", "bp35", "cd82"]
    else:
        game_ids = [g.strip() for g in args.game.split(",")]

    print(f"Running {len(game_ids)} games with {args.workers} workers...")
    
    # Parallel execution
    with Pool(
        processes=args.workers,
        initializer=worker_init,
        initargs=(args.llm_base_url, args.llm_model, args.max_actions)
    ) as pool:
        results = pool.map(run_one_game, game_ids)
    
    # Summary
    print("\n=== summary ===")
    total_actions = 0
    total_tokens = 0
    total_levels = 0
    
    for result in results:
        print(f"{result.game_id}: state={result.state}, levels={result.levels_completed}, actions={result.actions}, tokens={result.tokens_used}")
        total_actions += result.actions
        total_tokens += result.tokens_used
        total_levels += result.levels_completed
    
    print(f"\nTotal: {len(results)} games, {total_levels} levels, {total_actions} actions, {total_tokens} tokens")
    
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        print(f"Report written to {args.report}")


if __name__ == "__main__":
    main()
