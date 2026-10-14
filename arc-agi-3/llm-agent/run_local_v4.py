#!/usr/bin/env python3
"""
Run LLM Agent v4 locally with LM Studio

Usage:
    export LLM_BASE_URL="http://localhost:9000/v1"
    export LLM_MODEL="qwen2.5-7b"
    python3 run_local_v4.py
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm_policy_v4 import LLMPolicy, Config


def mock_game_env():
    """Mock game environment for testing"""
    
    class MockFrame:
        def __init__(self, step=0):
            self.step = step
            self.grid = [
                [0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 0, 0, 2, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ]
            self.available_actions = ["UP", "DOWN", "LEFT", "RIGHT", "MOUSE"]
            self.state_name = "PLAYING"
            self.levels_completed = 0
    
    return MockFrame()


def main():
    """Run agent locally"""
    
    print("=" * 60)
    print("ARC-AGI-3 LLM Agent v4 - Local Test")
    print("=" * 60)
    
    # Check environment
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")
    
    if not base_url:
        print("\nERROR: LLM_BASE_URL not set")
        print("\nUsage:")
        print("  export LLM_BASE_URL='http://localhost:9000/v1'")
        print("  export LLM_MODEL='qwen2.5-7b'")
        print("  export OPENAI_API_KEY='dummy'")
        print("  python3 run_local_v4.py")
        sys.exit(1)
    
    print(f"\nConfig:")
    print(f"  LLM_BASE_URL: {base_url}")
    print(f"  LLM_MODEL: {model or 'not set'}")
    
    # Create policy
    config = Config(max_actions=20)  # Short test
    policy = LLMPolicy(config)
    
    print(f"\nRunning agent for {config.max_actions} actions...")
    print("-" * 60)
    
    # Run agent
    for i in range(config.max_actions):
        frame = mock_game_env()
        action = policy.get_action(frame)
        
        print(f"Step {i+1:2d}: {action}")
        
        # Simulate game state change
        frame.step += 1
    
    print("-" * 60)
    print(f"\nResults:")
    print(f"  Actions: {policy.state.action_count}")
    print(f"  Tokens: {policy.state.tokens_used}")
    print(f"  Strategy: {policy.state.strategy}")
    
    # Save history
    history_file = "agent_v4_history.json"
    with open(history_file, 'w') as f:
        json.dump(policy.history, f, indent=2)
    print(f"\nHistory saved to {history_file}")


if __name__ == "__main__":
    main()
