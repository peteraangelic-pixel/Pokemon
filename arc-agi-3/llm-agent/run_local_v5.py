#!/usr/bin/env python3
"""
Run LLM Agent v5.0 locally with LM Studio or any OpenAI-compatible API.

Usage:
    export LLM_BASE_URL="http://localhost:9000/v1"
    export LLM_MODEL="qwen2.5-7b"
    python3 run_local_v5.py --game ar25 --max-actions 100
"""

import argparse
import json
import os
import sys
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI
from llm_policy_v5 import LLMPolicyV5


def create_llm_client() -> OpenAI:
    """Create OpenAI-compatible client."""
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:9000/v1")
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    return OpenAI(base_url=base_url, api_key=api_key)


def mock_arc_environment(game_name: str) -> dict[str, Any]:
    """Mock ARC environment for testing.
    
    In real usage, this would be replaced with actual ARC-AGI-3 environment.
    """
    # Mock frame for testing
    return {
        "game": game_name,
        "grid": [
            [0, 0, 1, 0, 0],
            [0, 1, 1, 1, 0],
            [1, 1, 2, 1, 1],
            [0, 1, 1, 1, 0],
            [0, 0, 1, 0, 0],
        ],
        "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"],
        "levels_completed": 0,
        "current_level": 1,
        "score": 0,
        "lives": 3,
        "step_count": 0,
    }


def run_game(game_name: str, max_actions: int = 100):
    """Run one game with LLM Agent v5.0."""
    print(f"=== Running game: {game_name} (max {max_actions} actions) ===\n")
    
    # Create LLM client
    client = create_llm_client()
    
    # Create policy
    policy = LLMPolicyV5(client)
    policy.reset()
    
    # Mock environment
    frame = mock_arc_environment(game_name)
    
    # Game loop
    for action_num in range(max_actions):
        # Get action from policy
        action = policy.get_action(frame)
        
        print(f"Action {action_num + 1}: {action}")
        
        # Mock environment step (in real usage, this would update the environment)
        # For now, just simulate some changes
        if action.get("action") == "ACTION1":
            frame["step_count"] += 1
            frame["grid"][0][0] = 1  # Simulate grid change
        elif action.get("action") == "ACTION2":
            frame["step_count"] += 1
            # Simulate no-op (grid doesn't change)
        
        # Check if level completed (mock)
        if frame["step_count"] >= 10:
            frame["levels_completed"] = 1
            frame["current_level"] = 2
            frame["step_count"] = 0
            print(f"\n✓ Level 1 completed!\n")
        
        # Check if game over (mock)
        if frame["lives"] <= 0:
            policy.record_game_over(f"Lives depleted at action {action_num + 1}")
            print(f"\n✗ Game over: {policy.state.game_overs[-1]}\n")
            break
        
        # Small delay for readability
        import time
        time.sleep(0.1)
    
    print(f"\n=== Game finished ===")
    print(f"Total actions: {policy.state.action_count}")
    print(f"Levels completed: {frame['levels_completed']}")
    print(f"Level notes: {policy.state.level_notes}")
    print(f"Game overs: {policy.state.game_overs}")
    
    return {
        "game": game_name,
        "actions": policy.state.action_count,
        "levels_completed": frame["levels_completed"],
        "level_notes": policy.state.level_notes,
        "game_overs": policy.state.game_overs,
    }


def main():
    parser = argparse.ArgumentParser(description="Run LLM Agent v5.0 locally")
    parser.add_argument("--game", type=str, default="ar25", help="Game name (default: ar25)")
    parser.add_argument("--max-actions", type=int, default=100, help="Max actions per game (default: 100)")
    args = parser.parse_args()
    
    result = run_game(args.game, args.max_actions)
    
    # Save result
    output_file = f"v5_result_{args.game}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to {output_file}")


if __name__ == "__main__":
    main()
