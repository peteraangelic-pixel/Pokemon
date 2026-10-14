#!/usr/bin/env python3
"""
Run LLM Agent v7.0 on real ARC-AGI-3 games using arcengine.

Usage:
    export LLM_BASE_URL="http://localhost:9000/v1"
    export LLM_MODEL="qwen2.5-7b"
    python3 run_games_v7.py --game ar25 --max-actions 400

Requires: pip install arcengine openai
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def _try_import_arcengine():
    """Try to import arcengine, return None if unavailable."""
    try:
        import arcengine
        return arcengine
    except ImportError:
        return None


def _try_import_openai():
    """Try to import openai, return None if unavailable."""
    try:
        from openai import OpenAI
        return OpenAI
    except ImportError:
        return None


def make_llm_client(base_url: str, model_id: str, api_key: str = "EMPTY"):
    """Create OpenAI client for LLM."""
    OpenAI = _try_import_openai()
    if OpenAI is None:
        raise RuntimeError("openai not installed - pip install openai")
    return OpenAI(base_url=base_url, api_key=api_key)


def run_game_v7(game_env, policy, max_actions: int, verbose: bool = True):
    """Run one game with v7.0 policy.
    
    Args:
        game_env: ARC-AGI-3 game environment
        policy: LLMPolicyV7_0 instance
        max_actions: Maximum actions per game
        verbose: Print progress
    
    Returns:
        dict with results
    """
    policy.reset()
    start_time = time.time()
    actions_taken = 0
    frames_seen = []
    
    for step in range(max_actions):
        try:
            # Get current frame from game env
            frame_data = game_env.get_frame()
            
            # Convert to dict format expected by v7.0 policy
            frame_dict = {
                "grid": frame_data.get("grid", [[0] * 10] * 10),
                "available_actions": frame_data.get("available_actions", ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]),
                "levels_completed": frame_data.get("levels_completed", 0),
                "current_level": frame_data.get("current_level", 1),
                "action_count": step,
                "actions_since_level": step,
                "lives": frame_data.get("lives", 3),
                "score": frame_data.get("score", 0),
                "step_limit": max_actions,
                "no_op_count": 0,
                "goal_class": None,
                "game": getattr(game_env, "name", "unknown"),
            }
            
            # Check if game over
            if frame_data.get("state_name") == "GAME_OVER":
                policy.record_game_over("Game over state")
                break
            
            # Check if win
            if frame_data.get("state_name") == "WIN":
                break
            
            # Get action from policy
            action = policy.get_action(frame_dict)
            actions_taken += 1
            frames_seen.append(frame_dict)
            
            if verbose and (step < 3 or step == max_actions - 1):
                goal_class = policy.state.goal_class
                print(f"Step {step+1:3d}: action={action.get('action', 'RESET')}, goal_class={goal_class}")
            
            # Execute action in game env
            game_env.step(action.get("action", "RESET"))
            
        except Exception as e:
            print(f"Error at step {step}: {e}")
            break
    
    elapsed = time.time() - start_time
    goal_class = policy.state.goal_class
    stuck_count = policy.state.stuck_count
    ml_value = policy.state.ml_value
    levels_completed = frame_data.get("levels_completed", 0) if frames_seen else 0
    
    return {
        "game": getattr(game_env, "name", "unknown"),
        "actions_taken": actions_taken,
        "levels_completed": levels_completed,
        "goal_class": goal_class,
        "stuck_count": stuck_count,
        "ml_value": ml_value,
        "elapsed_seconds": elapsed,
        "status": frame_data.get("state_name", "UNKNOWN") if frames_seen else "ERROR",
    }


class MockGameEnv:
    """Mock game environment for testing without arcengine."""
    
    def __init__(self, name: str, grid=None):
        self.name = name
        self.step_count = 0
        self.grid = grid or [[0] * 10 for _ in range(10)]
        self.levels_completed = 0
        self.state_name = "PLAYING"
    
    def get_frame(self):
        return {
            "grid": self.grid,
            "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"],
            "levels_completed": self.levels_completed,
            "current_level": self.levels_completed + 1,
            "lives": 3,
            "score": 0,
            "state_name": self.state_name,
        }
    
    def step(self, action_name):
        self.step_count += 1
        if self.step_count > 20:
            self.state_name = "GAME_OVER"


def main():
    parser = argparse.ArgumentParser(description="Run LLM Agent v7.0 on ARC-AGI-3 games")
    parser.add_argument("--game", type=str, default="ar25", help="Game ID")
    parser.add_argument("--max-actions", type=int, default=400, help="Max actions per game")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"ARC-AGI-3 LLM Agent v7.0 - Game: {args.game}")
    print("=" * 60)
    
    # Check LLM configuration
    base_url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    model_id = os.environ.get("LLM_MODEL_ID", "qwen2.5-7b")
    api_key = os.environ.get("LLM_API_KEY", "EMPTY")
    
    print(f"LLM config:")
    print(f"  base_url: {base_url}")
    print(f"  model_id: {model_id}")
    
    # Check arcengine
    arcengine = _try_import_arcengine()
    if arcengine is None:
        print("\n[WARN] arcengine not installed - using mock environment")
        game_env = MockGameEnv(args.game)
    else:
        # TODO: Create real game env from arcengine
        print(f"\n[INFO] arcengine available - but not yet integrated")
        print("[INFO] Using mock environment for now")
        game_env = MockGameEnv(args.game)
    
    # Create LLM client
    try:
        client = make_llm_client(base_url, model_id, api_key)
    except Exception as e:
        print(f"\n[WARN] Failed to create LLM client: {e}")
        print("[WARN] Using mock client")
        
        class MockClient:
            class Chat:
                class Completions:
                    def create(self, **kwargs):
                        class Choice:
                            class Message:
                                content = '{"action": "ACTION1", "reasoning": "mock"}'
                            message = Message()
                        class Response:
                            choices = [Choice()]
                        return Response()
                completions = Completions()
            chat = Chat()
        
        client = MockClient()
    
    # Create policy
    from llm_policy_v7_0 import LLMPolicyV7_0
    policy = LLMPolicyV7_0(client)
    
    # Run game
    print(f"\nRunning game {args.game} (max {args.max_actions} actions)...\n")
    result = run_game_v7(game_env, policy, args.max_actions, verbose=args.verbose)
    
    print(f"\n{'='*60}")
    print(f"Results:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    
    # Save result
    output_path = args.output or f"v7_result_{args.game}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
