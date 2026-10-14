"""ARC-AGI-3 Agent adapter for the LLM-based policy.

Plugs LLMPolicy into the ARC-AGI-3-Agents reference framework.
The agent calls the LLM to get actions, with anti-loop detection
and action batching for efficiency.
"""
from __future__ import annotations

import os
import sys
import time
from threading import RLock
from typing import Any

# Ensure imports work both in competition and locally
_dir = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_dir)
for p in (_dir, _parent):
    if p not in sys.path:
        sys.path.insert(0, p)

from arcengine import ActionInput, FrameData, GameAction, GameState
from agents.agent import Agent

try:
    from .llm_policy import LLMPolicy, LLMConfig, FrameInfo
    from .grid_utils import format_grid_ascii
except ImportError:
    from llm_policy import LLMPolicy, LLMConfig, FrameInfo
    from grid_utils import format_grid_ascii


def _extract_grid(frame_data: FrameData) -> tuple[tuple[int, ...], ...]:
    """Extract the numeric grid from a FrameData object."""
    # Try multiple paths to get the grid data
    for attr_path in [
        lambda f: f.raw_state.data,
        lambda f: f.raw_state.planes[0] if f.raw_state.planes else None,
        lambda f: f.planes[0] if hasattr(f, 'planes') and f.planes else None,
    ]:
        try:
            data = attr_path(frame_data)
            if data is None:
                continue
            if hasattr(data, 'tolist'):
                rows = data.tolist()
            else:
                rows = list(data)
            if rows and rows[0]:
                return tuple(tuple(int(c) for c in row) for row in rows)
        except Exception:
            continue
    # Absolute fallback
    return ((0,) * 64,) * 64


def _frame_to_info(frame_data: FrameData) -> FrameInfo:
    """Convert FrameData to our FrameInfo."""
    grid = _extract_grid(frame_data)
    
    # State name
    try:
        state = frame_data.state
        state_name = state.name if hasattr(state, 'name') else str(state)
    except Exception:
        state_name = "PLAYING"
    
    # Levels completed
    try:
        levels_completed = int(frame_data.levels_completed)
    except Exception:
        levels_completed = 0
    
    # Available actions
    available = []
    try:
        for act_id in frame_data.available_actions:
            try:
                act = GameAction.from_id(int(act_id))
                if act.name != "RESET":
                    available.append(act.name)
            except Exception:
                pass
    except Exception:
        available = ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"]
    
    # Step number
    try:
        step = int(frame_data.step)
    except Exception:
        step = 0
    
    return FrameInfo(
        grid=grid,
        step=step,
        level=levels_completed + 1,
        state_name=state_name,
        levels_completed=levels_completed,
        available_actions=available,
    )


class LLMAgent(Agent):
    """LLM-powered agent for ARC-AGI-3."""
    
    _ACTION_LOCK = RLock()
    
    ACTION_BUDGET = 400
    MAX_ACTIONS = ACTION_BUDGET
    
    # Soft time limit per game (seconds)
    # 110 games × 4 min = 440 min ≈ 7.3 hours — fits in 9h with margin
    GAME_TIME_LIMIT = 240
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = LLMConfig.from_env()
        self.policy = LLMPolicy(self.config)
        self._holds_action_lock = False
        self._game_start_time = time.time()
        self._actions_in_game = 0
        self._first_action = True
    
    @property
    def name(self) -> str:
        return f"{super().name}.llm-v2"
    
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        """Stop conditions: win, budget, or time limit."""
        if self._actions_in_game >= self.ACTION_BUDGET:
            return True
        try:
            if latest_frame.state is GameState.WIN:
                return True
        except Exception:
            pass
        if time.time() - self._game_start_time > self.GAME_TIME_LIMIT:
            return True
        return False
    
    @staticmethod
    def _to_game_action(proposal: dict) -> GameAction:
        """Convert policy output to GameAction enum."""
        action_name = proposal.get("name", "RESET")
        
        try:
            action = GameAction[action_name]
        except KeyError:
            action = GameAction.RESET
        
        if action.is_complex():
            x = proposal.get("x", 0) or 0
            y = proposal.get("y", 0) or 0
            action.set_data({"x": max(0, min(63, int(x))), "y": max(0, min(63, int(y)))})
        else:
            action.set_data({})
        
        action.reasoning = proposal.get("reasoning", {})
        return action
    
    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        """Main entry point called by the framework each turn."""
        self._ACTION_LOCK.acquire()
        self._holds_action_lock = True
        
        try:
            frame_info = _frame_to_info(latest_frame)
            
            # Initialize on first call
            if self._first_action:
                self._first_action = False
                self._game_start_time = time.time()
                self.policy.reset_game()
            
            # Auto-reset on GAME_OVER
            if frame_info.state_name == "GAME_OVER":
                action = GameAction.RESET
                action.set_data({})
                action.reasoning = {"auto_reset": True, "game_over": True}
                return action
            
            # Call the LLM policy
            proposal = self.policy.choose_action(frame_info)
            self._actions_in_game += 1
            
            return self._to_game_action(proposal)
            
        except Exception as e:
            import traceback
            print(f"[LLMAgent] Error: {e}")
            traceback.print_exc()
            action = GameAction.RESET
            action.set_data({})
            action.reasoning = {"error": str(e)}
            return action
        finally:
            if self._holds_action_lock:
                self._holds_action_lock = False
                self._ACTION_LOCK.release()
    
    def take_action(self, action: GameAction):  # type: ignore[override]
        """Execute action and record the result."""
        try:
            frame = super().take_action(action)
            if frame is not None:
                frame.action_input = ActionInput(
                    id=action,
                    data=action.action_data.model_dump(),
                    reasoning=getattr(action, "reasoning", None),
                )
            return frame
        finally:
            if getattr(self, "_holds_action_lock", False):
                self._holds_action_lock = False
                self._ACTION_LOCK.release()
    
    def finalize_diagnostics(self) -> None:
        """Log final stats for this game."""
        elapsed = time.time() - self._game_start_time
        print(f"[LLMAgent] Game done: "
              f"{self._actions_in_game} actions in {elapsed:.0f}s, "
              f"{self.policy.total_tokens} tokens ({self.policy.total_calls} calls, "
              f"{self.policy.client.total_time:.0f}s LLM time), "
              f"{len(self.policy.tracker.unique_states_seen)} unique states, "
              f"{self.policy.tracker.game_over_count} deaths")
