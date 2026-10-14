"""
LLM Policy v4.1 for ARC-AGI-3

Based on FAILURES.md analysis and coordination with Smak-Domu-Konkurs v6:
- FIELD GUIDE: classes of goals (cover targets, reach positions, copy patterns, etc.)
- GOAL PERSISTENCE: one game = one win condition
- STUCK PROTOCOL: audit every 15 actions after 40 without completing level
- ANTI-DISSERTATION: max ~60 words; batch up to 8 actions
- NOTATION: model can add "notes" to actions; policy keeps last 4 and injects each turn

Realistic improvement: ~24-32 (not 35-45 as previously estimated)
"""

import os
import json
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from openai import OpenAI

from grid_utils import format_grid_ascii, segment_grid


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: float = 30.0
    context_window: int = 8192
    max_actions: int = 400
    stuck_threshold: int = 5
    audit_interval: int = 15  # Audit every 15 actions
    audit_after: int = 40  # Start auditing after 40 actions without level completion
    max_notes: int = 4  # Keep last 4 notes from model
    max_words_reasoning: int = 60  # Anti-dissertation: max ~60 words


# ---------------------------------------------------------------------------
# Field Guide (from GOAL_CATALOG.md)
# ---------------------------------------------------------------------------

FIELD_GUIDE = """
FIELD GUIDE - Classes of Goals (from GOAL_CATALOG.md):

1. COVER: Cover all target markers with objects
   - Look for: dots, dashed outlines, small markers in moving object's color
   - Examples: ar25 (mirrors), re86 (crosses)

2. REACH: Reach all target positions
   - Look for: outlined positions, goal markers
   - Examples: bp35 (gems), r11l (dotted diamonds), tu93 (exits)

3. COPY: Make canvas match a pattern
   - Look for: thumbnail in corner, canvas in middle
   - Examples: cd82 (10×10 pixels), sb26 (sequential), sk48 (snake order)

4. REDUCE: Leave exactly 1 piece (jump over others like checkers)
   - Look for: green pieces on board
   - Example: lf52

5. PLACE: Put all objects in target zone
   - Look for: outlined target area, boxes to push
   - Example: wa30

6. FLOW: Fill all containers without spilling
   - Look for: dispenser at top, vessels at bottom
   - Example: sp80

7. ALIGN: Match target positions by color
   - Look for: colored markers on edges
   - Example: vc33

KEY PATTERNS:
- Decreasing counter = STEP LIMIT (zeroing = LOSS, not win!)
- One game = one win condition class (all levels same type)
- "All" means ALL: all targets covered, all avatars on exits, all containers full
- Large non-interactive area = pattern to copy (not something to click)
- Dashed outlines, small markers in moving object's color = targets

CONFIRMATION:
- In sb26, sp80: CONFIRM (action 5) only ONCE after setting configuration
- Don't click CONFIRM "to test" - limited attempts
"""


# ---------------------------------------------------------------------------
# System Prompt (with Field Guide)
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    return f"""ARC-AGI-3 Puzzle Solver

{FIELD_GUIDE}

STRATEGY:
1. ACT FAST - don't think too much (max 60 words reasoning)
2. Track what changes grid = good; what doesn't = bad
3. If stuck 5x, try NEW approach
4. New object? CLICK it NOW to test
5. Take NOTES: add "notes" field to actions to remember discoveries

GOAL PERSISTENCE:
- One game = one win condition class
- After solving level 1, remember the goal class
- All levels in same game have same goal type

STUCK PROTOCOL (after 40 actions without completing level):
- Every 15 actions: audit hypotheses
- List what you tried (✗) and what worked (✓)
- Test one cheap hypothesis

OUTPUT FORMAT:
```json
[
  {{"action": "RIGHT", "reasoning": "explore right", "notes": "saw blue gem"}},
  {{"action": "DOWN", "reasoning": "continue down"}}
]
```

For MOUSE: {{"action": "MOUSE", "row": 5, "col": 10, "reasoning": "click target"}}

Keep reasoning SHORT (max 60 words). Use "notes" to remember discoveries.
"""


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    action_count: int = 0
    actions_since_level: int = 0  # Actions since last level completion
    last_grid_hash: str = ""
    stuck_count: int = 0
    strategy: str = "explore"
    notes: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    failed_hypotheses: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class LLMPolicy:
    """LLM-based policy with field guide and stuck protocol"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:9000/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
            timeout=self.config.timeout
        )
        self.state = GameState()
        self.system_prompt = build_system_prompt()
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
        levels_completed = self._get_levels_completed(frame)
        
        # Check for level completion
        current_levels = levels_completed
        if current_levels > 0 and self.state.actions_since_level > 0:
            # Level completed! Reset stuck counter
            self.state.actions_since_level = 0
            self.state.stuck_count = 0
            self.state.strategy = "explore"
        
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
        
        # Stuck protocol: audit after 40 actions without level completion
        self.state.actions_since_level += 1
        if self.state.actions_since_level > self.config.audit_after:
            if self.state.actions_since_level % self.config.audit_interval == 0:
                self.state.strategy = "audit"
        
        # Build prompt
        user_prompt = self._build_prompt(grid_ascii, available_actions)
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            content = response.choices[0].message.content
            
            # Parse action and notes
            action, notes = self._parse_action_and_notes(content)
            
            # Update notes
            if notes:
                self.state.notes.append(notes)
                if len(self.state.notes) > self.config.max_notes:
                    self.state.notes.pop(0)
            
        except Exception as e:
            print(f"LLM error: {e}")
            action = self._fallback_action(available_actions)
        
        # Execute
        self.state.action_count += 1
        self.history.append(action)
        
        return action
    
    def _build_prompt(self, grid_ascii: str, available_actions: list) -> str:
        """Build user prompt with notes and strategy hint"""
        
        strategy_hint = ""
        if self.state.strategy == "audit":
            strategy_hint = "\n\nSTUCK PROTOCOL: Audit hypotheses now. List what worked (✓) and failed (✗)."
        elif self.state.strategy == "avoid_hud":
            strategy_hint = "\n\nSTUCK - try DIFFERENT approach, avoid edges/HUD"
        
        # Inject recent notes
        notes_section = ""
        if self.state.notes:
            notes_section = "\n\nRECENT NOTES:\n" + "\n".join(f"- {note}" for note in self.state.notes[-self.config.max_notes:])
        
        prompt = f"""Grid:
{grid_ascii}

Actions: {', '.join(available_actions)}
Strategy: {self.state.strategy}{strategy_hint}{notes_section}

Next 3-8 actions (keep reasoning short, use "notes" for discoveries):"""
        
        return prompt
    
    def _parse_action_and_notes(self, content: str) -> tuple[dict, Optional[str]]:
        """Parse action and notes from LLM response"""
        
        try:
            # Try to parse JSON
            actions = json.loads(content)
            if isinstance(actions, list) and len(actions) > 0:
                action = actions[0]
                notes = action.get("notes")
                return action, notes
            elif isinstance(actions, dict):
                return actions, actions.get("notes")
        except:
            pass
        
        # Fallback: extract action name
        for action_name in ["UP", "DOWN", "LEFT", "RIGHT"]:
            if action_name in content.upper():
                return {"action": action_name}, None
        
        # Default
        return {"action": "RIGHT"}, None
    
    def _fallback_action(self, available_actions: list) -> dict:
        """Fallback action when LLM fails"""
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
    
    def _get_levels_completed(self, frame: Any) -> int:
        """Get levels completed from frame"""
        if hasattr(frame, 'levels_completed'):
            return frame.levels_completed
        elif isinstance(frame, dict) and 'levels_completed' in frame:
            return frame['levels_completed']
        return 0
    
    def reset(self):
        """Reset state for new game"""
        self.state = GameState()
        self.history = []
