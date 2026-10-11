"""LLM-based policy for ARC-AGI-3.

Uses a local vLLM server (OpenAI-compatible API) to reason about game states.
Key design:
- The model outputs a PLAN with multiple actions when possible
- Actions are cached and executed without re-calling the model
- Anti-loop detection forces re-planning when stuck
- Context is managed to stay within the model's window
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.error
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from .grid_utils import (
    ARC_COLOR_CHARS,
    ARC_COLOR_LEGEND,
    format_grid_ascii,
    segment_grid,
    compact_segmentation_summary,
    grid_to_png_bytes,
)

# ---------------------------------------------------------------------------
# Action protocol
# ---------------------------------------------------------------------------
RESET = "RESET"
ACTION_NAMES = (RESET, *(f"ACTION{i}" for i in range(1, 8)))
COMPLEX_ACTION = "ACTION6"
DIRECTIONAL_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
DIRECTION_NAMES = {
    "ACTION1": "UP", "ACTION2": "DOWN",
    "ACTION3": "LEFT", "ACTION4": "RIGHT",
}
MODEL_TO_ENGINE = {
    "UP": "ACTION1", "DOWN": "ACTION2",
    "LEFT": "ACTION3", "RIGHT": "ACTION4",
    "MOUSE": "ACTION6", "CLICK": "ACTION6",
}
ENGINE_TO_MODEL = {v: k for k, v in MODEL_TO_ENGINE.items()}
ENGINE_TO_MODEL.update(DIRECTION_NAMES)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    base_url: str = ""
    model_id: str = ""
    api_key: str = "EMPTY"
    max_output_tokens: int = 2048
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    timeout: float = 120.0
    context_window: int = 32768
    enable_thinking: bool = True
    multimodal: bool = False
    upscale: int = 4

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
            model_id=os.environ.get("LLM_MODEL_ID", ""),
            api_key=os.environ.get("LLM_API_KEY", "EMPTY"),
            max_output_tokens=int(os.environ.get("LLM_MAX_OUTPUT", "2048")),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.6")),
            top_p=float(os.environ.get("LLM_TOP_P", "0.95")),
            top_k=int(os.environ.get("LLM_TOP_K", "20")),
            timeout=float(os.environ.get("LLM_TIMEOUT", "120")),
            context_window=int(os.environ.get("LLM_CONTEXT_WINDOW", "32768")),
            enable_thinking=os.environ.get("LLM_ENABLE_THINKING", "1").lower() in ("1", "true", "yes"),
            multimodal=os.environ.get("LLM_MULTIMODAL", "0").lower() in ("1", "true", "yes"),
            upscale=int(os.environ.get("LLM_UPSCALE", "4")),
        )


class LLMClient:
    """Minimal OpenAI-compatible chat completion client (no dependencies)."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.total_tokens = 0
        self.total_calls = 0
        self.total_time = 0.0
    
    def chat(self, messages: list[dict]) -> dict:
        """Call chat completions. Returns the message dict."""
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        
        payload: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": self.config.max_output_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": False,
        }
        
        if self.config.enable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )
        
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[LLM] Request failed after {time.time()-t0:.1f}s: {e}")
            return {"role": "assistant", "content": ""}
        finally:
            self.total_time += time.time() - t0
        
        self.total_calls += 1
        usage = result.get("usage", {})
        self.total_tokens += usage.get("total_tokens", 0)
        
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {"role": "assistant", "content": ""})
        return {"role": "assistant", "content": ""}


# ---------------------------------------------------------------------------
# System prompt (optimized for structured JSON output)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are an expert puzzle solver playing a grid-based game. You see the game board as a 64×64 color grid and must figure out the mechanics through experimentation.

COLOR LEGEND: {ARC_COLOR_LEGEND}

HOW THE GAME WORKS:
- You control an avatar/agent on a colored grid
- You take actions to move, interact, or manipulate objects
- Levels are completed when you achieve the goal (often reaching a target, solving a puzzle, or clearing enemies)
- GAME_OVER means you died; the game auto-resets
- WIN means you beat the entire game

AVAILABLE ACTIONS (may vary per game):
- UP / DOWN / LEFT / RIGHT — move in a direction
- MOUSE(row=N, col=M) — click/interact at position (row, col)
- Other game-specific actions may appear in valid_actions

YOUR TASK EACH TURN:
1. Observe the current board state
2. Consider what changed since last turn (if history available)
3. Form/update a hypothesis about the game mechanics and goal
4. Choose the BEST next action

STRATEGIES:
- Start by exploring: move in different directions to understand the world
- Identify the player avatar (usually a distinct colored shape that moves)
- Identify obstacles, enemies, targets, and interactive objects
- For navigation puzzles, plan a path using BFS mentally
- If you die repeatedly, try a different approach
- Don't click on HUD elements (bars at edges that change each step)
- Objects are multi-tile connected components of the same color

IMPORTANT:
- Be decisive. Don't waste actions on indecision.
- If you've been stuck for 10+ actions, radically change strategy.
- Track what worked and what didn't.
- Compact reasoning is fine, but always output a valid action.

OUTPUT FORMAT — you MUST output a JSON object on the LAST line of your response:
```json
{{"action": "ACTION_NAME", "reasoning": "brief explanation"}}
```
For MOUSE actions: {{"action": "MOUSE", "row": 5, "col": 10, "reasoning": "..."}}
For directions: {{"action": "UP", "reasoning": "..."}}
Always output exactly one JSON action block."""


# ---------------------------------------------------------------------------
# Frame info
# ---------------------------------------------------------------------------

@dataclass
class FrameInfo:
    grid: tuple[tuple[int, ...], ...]
    step: int
    level: int
    state_name: str
    levels_completed: int
    available_actions: list[str]
    
    @property
    def ascii(self) -> str:
        return format_grid_ascii(self.grid)
    
    @property
    def shape(self) -> tuple[int, int]:
        rows = len(self.grid)
        cols = max((len(r) for r in self.grid), default=0)
        return (rows, cols)
    
    def segmentation_summary(self) -> str:
        try:
            seg = segment_grid(self.grid)
            return compact_segmentation_summary(seg, max_nodes=15)
        except Exception:
            return "segmentation unavailable"


# ---------------------------------------------------------------------------
# State tracking for anti-loop
# ---------------------------------------------------------------------------

@dataclass
class StateTracker:
    """Track state transitions to detect loops."""
    
    state_signatures: list[str] = field(default_factory=list)
    action_history: list[str] = field(default_factory=list)
    state_action_counts: Counter = field(default_factory=Counter)
    game_over_count: int = 0
    total_actions: int = 0
    unique_states_seen: set = field(default_factory=set)
    
    # Recent window for loop detection
    _recent_sigs: list[str] = field(default_factory=list)
    _recent_actions: list[str] = field(default_factory=list)
    
    def record(self, state_sig: str, action: str, *,
               game_over: bool = False) -> None:
        self.state_signatures.append(state_sig)
        self.action_history.append(action)
        self.state_action_counts[(state_sig, action)] += 1
        self.total_actions += 1
        self.unique_states_seen.add(state_sig)
        
        self._recent_sigs.append(state_sig)
        if len(self._recent_sigs) > 12:
            self._recent_sigs = self._recent_sigs[-12:]
        
        self._recent_actions.append(action)
        if len(self._recent_actions) > 12:
            self._recent_actions = self._recent_actions[-12:]
        
        if game_over:
            self.game_over_count += 1
    
    def is_looped(self) -> bool:
        """Check if we're stuck repeating."""
        if len(self._recent_sigs) < 6:
            return False
        
        # Oscillation: same state appearing at positions 0,2,4
        last6 = self._recent_sigs[-6:]
        if last6[0] == last6[2] == last6[4] and last6[1] == last6[3] == last6[5]:
            return True
        
        # Same action repeated 6+ times
        if len(self._recent_actions) >= 6:
            last6a = self._recent_actions[-6:]
            if len(set(last6a)) == 1:
                return True
        
        # Same state repeated 4+ times
        if len(self._recent_sigs) >= 4:
            last4 = self._recent_sigs[-4:]
            if len(set(last4)) == 1:
                return True
        
        return False
    
    def repeated_in_state(self, state_sig: str, action: str) -> int:
        return self.state_action_counts.get((state_sig, action), 0)
    
    def reset(self) -> None:
        self.state_signatures.clear()
        self.action_history.clear()
        self.state_action_counts.clear()
        self.game_over_count = 0
        self.total_actions = 0
        self.unique_states_seen.clear()
        self._recent_sigs.clear()
        self._recent_actions.clear()


# ---------------------------------------------------------------------------
# Main LLM Policy
# ---------------------------------------------------------------------------

class LLMPolicy:
    """LLM-based policy with direct action output (no tool sandbox)."""
    
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()
        self.client = LLMClient(self.config)
        self.tracker = StateTracker()
        
        # Conversation history for the current game
        self._messages: list[dict] = []
        self._initialized = False
        
        # Action cache: actions planned by LLM to execute without re-calling
        self._action_queue: list[dict] = []
        self._last_level = 0
        self._actions_since_last_llm = 0
        self._max_actions_per_plan = 15  # re-plan after this many actions
    
    def reset_game(self) -> None:
        """Reset for a new game."""
        self._messages.clear()
        self._initialized = False
        self.tracker.reset()
        self._action_queue.clear()
        self._last_level = 0
        self._actions_since_last_llm = 0
    
    def choose_action(self, frame: FrameInfo) -> dict:
        """Choose an action for the current frame.
        
        Returns dict: {name: str, x: int|None, y: int|None, reasoning: dict}
        """
        state_sig = self._state_signature(frame)
        
        # Check for level change — re-plan immediately
        if frame.levels_completed != self._last_level:
            self._last_level = frame.levels_completed
            self._action_queue.clear()
            self._actions_since_last_llm = 0
            # Add level change notification to history
            if self._messages:
                self._messages.append({
                    "role": "user",
                    "content": f"[LEVEL COMPLETED! Now on level {frame.levels_completed + 1}. Re-assess the new board.]"
                })
        
        # Check for loop
        if self.tracker.is_looped():
            self._action_queue.clear()
            return self._anti_loop_action(frame)
        
        # Try to use cached action
        if self._action_queue and self._actions_since_last_llm < self._max_actions_per_plan:
            action = self._action_queue.pop(0)
            self._actions_since_last_llm += 1
            self.tracker.record(state_sig, action.get("name", RESET))
            return action
        
        # Need to call LLM
        self._action_queue.clear()
        self._actions_since_last_llm = 0
        
        # Build user turn
        user_content = self._build_user_turn(frame)
        
        if not self._messages:
            self._messages.append({"role": "system", "content": SYSTEM_PROMPT})
        
        self._messages.append({"role": "user", "content": user_content})
        
        # Trim context if too long
        self._trim_context()
        
        # Call LLM
        response = self.client.chat(self._messages)
        content = response.get("content", "") or ""
        
        # Add assistant response to history
        self._messages.append({"role": "assistant", "content": content})
        
        # Parse action(s) from response
        actions = self._parse_response(content, frame)
        
        if not actions:
            # Fallback: try different directions
            action = self._fallback_action(frame)
            self.tracker.record(state_sig, action.get("name", RESET))
            return action
        
        # First action is immediate, rest go to queue
        immediate = actions[0]
        self._action_queue = actions[1:]
        self._actions_since_last_llm = 1
        
        self.tracker.record(state_sig, immediate.get("name", RESET))
        return immediate
    
    def _state_signature(self, frame: FrameInfo) -> str:
        """Compact state signature for loop detection."""
        # Downsample: take every 4th row, every 4th col
        rows = frame.grid
        sampled = []
        for r in range(0, len(rows), 4):
            row_sample = []
            for c in range(0, len(rows[r]), 4):
                row_sample.append(rows[r][c])
            sampled.append(tuple(row_sample))
        payload = f"{frame.level}:{frame.state_name}:{sampled}".encode()
        return hashlib.md5(payload).hexdigest()[:12]
    
    def _build_user_turn(self, frame: FrameInfo) -> str:
        """Build user message with current game state."""
        parts = []
        
        # Status line
        parts.append(f"=== Turn {self.tracker.total_actions + 1} | "
                    f"Level {frame.level} | Step {frame.step} | "
                    f"State: {frame.state_name} | "
                    f"Levels done: {frame.levels_completed} ===")
        
        # Available actions
        model_actions = []
        for a in frame.available_actions:
            model_name = ENGINE_TO_MODEL.get(a, a)
            model_actions.append(model_name)
        parts.append(f"Valid actions: {', '.join(model_actions)}")
        
        # Stats
        if self.tracker.total_actions > 0:
            parts.append(f"Stats: {self.tracker.total_actions} actions taken, "
                        f"{len(self.tracker.unique_states_seen)} unique states seen, "
                        f"{self.tracker.game_over_count} deaths")
        
        # Board (compact)
        rows, cols = frame.shape
        if rows <= 40 and cols <= 40:
            parts.append(f"\nBoard ({rows}×{cols}):")
            # Add row numbers every 10
            ascii_board = frame.ascii
            parts.append(ascii_board)
        else:
            parts.append(f"\nBoard is {rows}×{cols} (large — key objects below)")
        
        # Segmentation
        seg = frame.segmentation_summary()
        parts.append(f"\nObjects detected:\n{seg}")
        
        # Recent history (last 5 actions)
        if self.tracker.action_history:
            recent = self.tracker.action_history[-5:]
            parts.append(f"\nRecent actions: {' → '.join(ENGINE_TO_MODEL.get(a, a) for a in recent)}")
        
        # Anti-loop warning
        if self.tracker.is_looped():
            parts.append("\n⚠️ WARNING: You appear to be stuck in a loop! "
                        "Try a COMPLETELY different approach.")
        
        return "\n".join(parts)
    
    def _parse_response(self, content: str, frame: FrameInfo) -> list[dict]:
        """Parse action(s) from LLM response."""
        actions = []
        
        # Look for JSON blocks
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if not json_blocks:
            # Try without code fences
            json_blocks = re.findall(r'\{[^{}]*"action"[^{}]*\}', content)
        
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                action = self._normalize_action(parsed, frame)
                if action:
                    actions.append(action)
            except json.JSONDecodeError:
                continue
        
        # If no JSON found, try to parse from text
        if not actions:
            action = self._parse_text_action(content, frame)
            if action:
                actions.append(action)
        
        return actions
    
    def _normalize_action(self, parsed: dict, frame: FrameInfo) -> dict | None:
        """Normalize a parsed action dict to our format."""
        action_name = str(parsed.get("action", "")).upper().strip()
        if not action_name:
            return None
        
        # Map friendly names to engine names
        engine_name = MODEL_TO_ENGINE.get(action_name, action_name)
        
        # Validate against available actions
        valid = set(frame.available_actions) | {RESET}
        if engine_name not in valid:
            # Try to find closest match
            for avail in frame.available_actions:
                if avail in action_name or action_name in avail:
                    engine_name = avail
                    break
            else:
                # Check if it's a direction in different format
                if action_name in ("UP", "DOWN", "LEFT", "RIGHT"):
                    engine_name = MODEL_TO_ENGINE.get(action_name, "RESET")
                else:
                    return None
        
        result = {"name": engine_name, "reasoning": {}}
        
        if engine_name == COMPLEX_ACTION:
            # MOUSE/CLICK needs coordinates
            row = parsed.get("row", parsed.get("y", 0))
            col = parsed.get("col", parsed.get("x", 0))
            result["x"] = int(col)
            result["y"] = int(row)
        
        reasoning = parsed.get("reasoning", "")
        if reasoning:
            result["reasoning"]["llm"] = str(reasoning)[:200]
        
        return result
    
    def _parse_text_action(self, text: str, frame: FrameInfo) -> dict | None:
        """Try to parse action from free text."""
        text_upper = text.upper()
        
        # Look for action patterns
        for pattern, engine_name in [
            (r'\bUP\b', 'ACTION1'), (r'\bDOWN\b', 'ACTION2'),
            (r'\bLEFT\b', 'ACTION3'), (r'\bRIGHT\b', 'ACTION4'),
            (r'\bRESET\b', 'RESET'),
        ]:
            if re.search(pattern, text_upper):
                if engine_name in frame.available_actions or engine_name == RESET:
                    return {"name": engine_name, "reasoning": {"parsed_from_text": True}}
        
        # Look for MOUSE/click patterns with coordinates
        mouse_match = re.search(r'MOUSE\s*\(\s*row\s*=\s*(\d+)\s*,\s*col\s*=\s*(\d+)\s*\)', text, re.I)
        if not mouse_match:
            mouse_match = re.search(r'CLICK\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', text, re.I)
        if mouse_match and COMPLEX_ACTION in frame.available_actions:
            return {
                "name": COMPLEX_ACTION,
                "x": int(mouse_match.group(2)),
                "y": int(mouse_match.group(1)),
                "reasoning": {"parsed_from_text": True},
            }
        
        return None
    
    def _anti_loop_action(self, frame: FrameInfo) -> dict:
        """Generate an action to break out of a loop."""
        import random
        
        available = [a for a in frame.available_actions if a != RESET]
        
        # Strategy 1: Reset
        if self.tracker.game_over_count < 3:
            return {"name": RESET, "reasoning": {"anti_loop": "reset"}}
        
        # Strategy 2: Try all different actions
        tried_recent = set(self.tracker._recent_actions[-6:])
        untried = [a for a in available if a not in tried_recent]
        
        if untried:
            choice = random.choice(untried)
            return {"name": choice, "reasoning": {"anti_loop": "try_untried"}}
        
        # Strategy 3: Random from available
        if available:
            choice = random.choice(available)
            return {"name": choice, "reasoning": {"anti_loop": "random"}}
        
        return {"name": RESET, "reasoning": {"anti_loop": "no_actions"}}
    
    def _fallback_action(self, frame: FrameInfo) -> dict:
        """Fallback when LLM fails to produce an action."""
        import random
        
        available = [a for a in frame.available_actions if a != RESET]
        if available:
            # Prefer directional actions
            dirs = [a for a in available if a in DIRECTIONAL_ACTIONS]
            if dirs:
                choice = random.choice(dirs)
            else:
                choice = random.choice(available)
            return {"name": choice, "reasoning": {"fallback": True}}
        
        return {"name": RESET, "reasoning": {"fallback": True}}
    
    def _trim_context(self) -> None:
        """Keep conversation within context window."""
        max_turns = 20  # system + last N user/assistant pairs
        if len(self._messages) > max_turns:
            system = [m for m in self._messages if m["role"] == "system"]
            others = [m for m in self._messages if m["role"] != "system"]
            # Keep last N turns
            self._messages = system + others[-(max_turns - len(system)):]
    
    def record_result(self, result: dict) -> None:
        """Record action result for context (optional)."""
        pass  # Results are incorporated via frame changes
    
    @property
    def total_tokens(self) -> int:
        return self.client.total_tokens
    
    @property
    def total_calls(self) -> int:
        return self.client.total_calls
