#!/usr/bin/env python3
"""
Run LLM Agent v7.0 locally (test with mock environment)

Usage:
    export LLM_BASE_URL="http://localhost:9000/v1"
    export LLM_MODEL="qwen2.5-7b"
    python3 run_local_v7.py
"""

import os
import sys
import json
import random
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm_policy_v7_0 import LLMPolicyV7_0
from goal_classifier import detect_goal_class


def mock_game_env(step=0, game_id="test"):
    """Mock game environment for testing - generates different grids"""
    
    # Vary grid based on step to simulate game progression
    random.seed(step)
    
    # Different grid types
    if game_id == "cover_test":
        # COVER: many small markers
        grid = [
            [0, 1, 0, 1, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 2, 0, 0, 2, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 1, 0, 0, 1, 0],
        ]
    elif game_id == "copy_test":
        # COPY: pattern in top-left corner
        grid = [
            [1, 1, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0],
            [3, 3, 4, 4, 0, 0, 0, 0, 0, 0, 0, 0],
            [3, 3, 4, 4, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 1, 2, 2, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 1, 2, 2, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 3, 4, 4, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 3, 4, 4, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
    elif game_id == "reduce_test":
        # REDUCE: many pieces to eliminate
        grid = [[0] * 20 for _ in range(20)]
        for i in range(0, 20, 2):
            for j in range(0, 20, 2):
                if random.random() < 0.5:
                    grid[i][j] = 1
    else:
        # Generic grid
        grid = [[random.randint(0, 3) for _ in range(10)] for _ in range(10)]
    
    return {
        "grid": grid,
        "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"],
        "levels_completed": 0,
        "current_level": 1,
        "action_count": step,
        "actions_since_level": step,
        "lives": 3,
        "score": 0,
        "step_limit": 400,
        "no_op_count": 0,
        "goal_class": None,
        "game": game_id,
    }


class MockLLMClient:
    """Mock LLM client that returns scripted responses"""
    class Chat:
        class Completions:
            def __init__(self, game_id):
                self._game_id = game_id
            
            def create(self, messages, temperature=None, max_tokens=None, **kwargs):
                # Simple mock: return different actions based on goal class detected
                # Find goal class in system prompt
                goal_class = None
                for msg in messages:
                    if msg.get("role") == "system":
                        content = msg.get("content", "")
                        if "DETECTED GOAL CLASS:" in content:
                            start = content.find("DETECTED GOAL CLASS:") + len("DETECTED GOAL CLASS:")
                            end = content.find("\n", start)
                            goal_class = content[start:end].strip()
                        break
                
                if goal_class == "COVER":
                    action = "ACTION1"  # click on markers
                elif goal_class == "COPY":
                    action = "ACTION3"  # trace pattern
                elif goal_class == "REDUCE":
                    action = "ACTION2"  # jump pieces
                else:
                    action = "ACTION1"  # explore
                
                content = f'{{"action": "{action}", "reasoning": "mock action for {goal_class}", "notes": "test note"}}'
                
                class MockChoice:
                    class Message:
                        def __init__(self, c):
                            self.content = c
                    def __init__(self, c):
                        self.message = self.Message(c)
                
                class MockResponse:
                    def __init__(self, c):
                        self.choices = [MockChoice(c)]
                
                return MockResponse(content)
        def __init__(self, game_id):
            self.completions = self.Completions(game_id)
    def __init__(self, game_id="test"):
        self.chat = self.Chat(game_id)


def main():
    """Run agent on multiple test games"""
    
    print("=" * 60)
    print("ARC-AGI-3 LLM Agent v7.0 - Local Test")
    print("=" * 60)
    
    games = ["cover_test", "copy_test", "reduce_test", "generic_test"]
    max_actions = 30  # Short test
    
    for game_id in games:
        print(f"\n{'='*60}")
        print(f"Game: {game_id}")
        print(f"{'='*60}")
        
        # Create policy with mock client
        client = MockLLMClient(game_id)
        policy = LLMPolicyV7_0(client)
        policy.reset()
        
        # Run game
        for step in range(max_actions):
            frame = mock_game_env(step, game_id)
            action = policy.get_action(frame)
            
            # Print first 3 and last action
            if step < 3 or step == max_actions - 1:
                print(f"Step {step+1:2d}: {action}")
            elif step == 3:
                print(f"  ... ({max_actions - 4} more steps) ...")
        
        # Results
        detected = policy.state.goal_class
        stuck = policy.state.stuck_count
        ml_value = policy.state.ml_value
        print(f"\nResults for {game_id}:")
        print(f"  Detected goal class: {detected}")
        print(f"  ValueGate value: {ml_value:.2f}")
        print(f"  Stuck count: {stuck}")
        
        # Verify goal classifier
        expected_class = {
            "cover_test": "COVER",
            "copy_test": "COPY",
            "reduce_test": "REDUCE",
            "generic_test": None,  # unpredictable
        }.get(game_id)
        
        if expected_class:
            if detected == expected_class:
                print(f"  ✓ Correctly detected {detected}")
            else:
                print(f"  ✗ Expected {expected_class}, got {detected}")


if __name__ == "__main__":
    main()
