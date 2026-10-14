"""
LLM Policy v4 for ARC-AGI-3

Ultra-fast agent with aggressive exploration:
- Max 500 token prompt
- Aggressive exploration (more actions, less thinking)
- Automatic new object testing
- Stuck detection and strategy change
"""

import os
import json
import time
from typing import Any
from dataclasses import dataclass
from openai import OpenAI

from grid_utils import format_grid_ascii, segment_grid


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    max_tokens: int = 1024  # Shorter responses
    temperature: float = 0.7  # More exploration
    timeout: float = 30.0  # Faster timeout
    context_window: int = 8192  # Smaller context
    max_actions: int = 400
    stuck_threshold: int = 5  # Change strategy after 5 no-change actions


# ---------------------------------------------------------------------------
# System prompt (ULTRA SHORT - max 500 tokens)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Play grid game. Act fast.

RULES:
- 64x64 grid, colored cells
- Actions: UP/DOWN/LEFT/RIGHT, MOUSE(row,col)
- GAME_OVER=reset, WIN=done
- Decreasing counter = STEP LIMIT (not timer)

STRATEGY:
1. MOVE immediately - don't think
2. If stuck 5x, try NEW approach
3. New object? CLICK it NOW
4. Track: what changes grid = good

GOALS: cover targets, reach positions, copy patterns, reduce pieces, place objects

Output: [{"action":"RIGHT"},{"action":"DOWN"}]
MOUSE: {"action":"MOUSE","row":5,"col":10}
"""


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

@dataclass
class State:
    action_count: int = 0
    tokens_used: int = 0
    last_grid_hash: str = ""
    stuck_count: int = 0
    strategy: str = "explore"  # explore, test_new, avoid_hud
    tested_positions: set = None
    
    def __post_init__(self):
        if self.tested_positions is None:
            self.tested_positions = set()


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class LLMPolicy:
    """LLM-based policy with aggressive exploration"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:9000/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
            timeout=self.config.timeout
        )
        self.state = State()
        self.history = []
    
    def get_action(self, frame: Any) -> dict:
        """Get next action from LLM"""
        
        # Check if done
        if self.state.action_count >= self.config.max_actions:
            return {"action": "RESET"}
        
        # Extract state
        grid = self._get_grid(frame)
        grid_ascii = format_grid_ascii(grid)
        available_actions = self._get_available_actions(frame)
        
        # Detect stuck
        grid_hash = hash(grid_ascii)
        if grid_hash == self.state.last_grid_hash:
            self.state.stuck_count += 1
            if self.state.stuck_count >= self.config.stuck_threshold:
                self.state.strategy = "avoid_hud"
                self.state.stuck_count = 0
        else:
            self.state.stuck_count = 0
            self.state.last_grid_hash = grid_hash
        
        # Detect new objects (simple heuristic: new colors)
        new_colors = self._detect_new_objects(grid)
        if new_colors and self.state.strategy != "avoid_hud":
            self.state.strategy = "test_new"
        
        # Build prompt
        user_prompt = self._build_prompt(grid_ascii, available_actions)
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            content = response.choices[0].message.content
            self.state.tokens_used += response.usage.total_tokens
            
            # Parse action
            action = self._parse_action(content)
            
        except Exception as e:
            print(f"LLM error: {e}")
            action = self._fallback_action(available_actions)
        
        # Execute
        self.state.action_count += 1
        self.history.append(action)
        
        return action
    
    def _build_prompt(self, grid_ascii: str, available_actions: list) -> str:
        """Build short user prompt"""
        
        strategy_hint = ""
        if self.state.strategy == "test_new":
            strategy_hint = "\nNEW OBJECTS detected - CLICK them!"
        elif self.state.strategy == "avoid_hud":
            strategy_hint = "\nSTUCK - try DIFFERENT approach, avoid edges"
        
        prompt = f"""Grid:
{grid_ascii}

Actions: {', '.join(available_actions)}
Strategy: {self.state.strategy}{strategy_hint}

Next 3-5 actions:"""
        
        return prompt
    
    def _parse_action(self, content: str) -> dict:
        """Parse action from LLM response"""
        
        try:
            # Try to parse JSON
            actions = json.loads(content)
            if isinstance(actions, list) and len(actions) > 0:
                return actions[0]
            elif isinstance(actions, dict):
                return actions
        except:
            pass
        
        # Fallback: extract action name
        for action_name in ["UP", "DOWN", "LEFT", "RIGHT"]:
            if action_name in content.upper():
                return {"action": action_name}
        
        # Default
        return {"action": "RIGHT"}
    
    def _fallback_action(self, available_actions: list) -> dict:
        """Fallback action when LLM fails"""
        
        # Cycle through directions
        directions = ["UP", "RIGHT", "DOWN", "LEFT"]
        idx = self.state.action_count % len(directions)
        
        for direction in directions[idx:] + directions[:idx]:
            if direction in available_actions:
                return {"action": direction}
        
        return {"action": available_actions[0] if available_actions else "RIGHT"}
    
    def _get_grid(self, frame: Any) -> list:
        """Extract grid from frame"""
        if hasattr(frame, 'grid'):
            return frame.grid
        elif isinstance(frame, dict) and 'grid' in frame:
            return frame['grid']
        return []
    
    def _get_available_actions(self, frame: Any) -> list:
        """Get available actions from frame"""
        if hasattr(frame, 'available_actions'):
            return frame.available_actions
        elif isinstance(frame, dict) and 'available_actions' in frame:
            return frame['available_actions']
        return ["UP", "DOWN", "LEFT", "RIGHT", "MOUSE"]
    
    def _detect_new_objects(self, grid: list) -> list:
        """Detect new objects in grid (simple color-based heuristic)"""
        
        # Get unique colors
        colors = set()
        for row in grid:
            for cell in row:
                if cell != 0:  # Ignore background
                    colors.add(cell)
        
        # Simple heuristic: if we see new colors, there are new objects
        # (This is very basic - real implementation would track across frames)
        return list(colors)[:3]  # Return up to 3 new colors
    
    def reset(self):
        """Reset state for new game"""
        self.state = State()
        self.history = []
