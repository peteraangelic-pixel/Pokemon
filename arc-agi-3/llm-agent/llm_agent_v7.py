"""ARC-AGI-3 Agent adapter for LLMPolicyV7_0 (counter-picking + ValueGate).

v7.0 improvements over v2:
- Goal classifier (COVER/COPY/REACH/REDUCE/PLACE/FLOW/ALIGN/LOCAL_CONSTRAINTS)
- Counter-picking: strategy hints injected per goal class
- Heuristic ValueGate (no ML weights)
- Escalation ladder (audit #2+ = STRATEGY RESET)
- Robust LEVEL NOTES extraction (case-insensitive, reasoning/reasoning_content)

Plugs LLMPolicyV7_0 into the ARC-AGI-3-Agents reference framework.
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
    from .llm_policy_v7_0 import LLMPolicyV7_0
    from .grid_utils import format_grid_ascii
    from .goal_classifier import detect_goal_class, get_strategy_hint
except ImportError:
    from llm_policy_v7_0 import LLMPolicyV7_0
    from grid_utils import format_grid_ascii
    from goal_classifier import detect_goal_class, get_strategy_hint


# Minimal FrameInfo for compatibility with v7.0 policy
class FrameInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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
        # Create OpenAI client from config (v7.0 policy uses OpenAI client)
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
            # Wrap client to use model_id from config
            class ClientWithModel:
                def __init__(self, client, model_id, temperature, max_output_tokens):
                    self._client = client
                    self._model_id = model_id
                    self._temperature = temperature
                    self._max_output_tokens = max_output_tokens
                class ChatCompletions:
                    def __init__(self, parent):
                        self._parent = parent
                    def create(self, messages, temperature=None, max_tokens=None, **kwargs):
                        return self._parent._client.chat.completions.create(
                            model=self._parent._model_id,
                            messages=messages,
                            temperature=temperature or self._parent._temperature,
                            max_tokens=max_tokens or self._parent._max_output_tokens,
                            **kwargs,
                        )
                class Chat:
                    def __init__(self, parent):
                        self.completions = ClientWithModel.ChatCompletions(parent)
                @property
                def chat(self):
                    return ClientWithModel.Chat(self)
            self.client = ClientWithModel(client, self.config.model_id, self.config.temperature, self.config.max_output_tokens)
        except Exception as e:
            print(f"[LLMAgent] Warning: Failed to create OpenAI client: {e}")
            # Fallback: policy uses MockLLMClient
            self.client = None
        self.policy = LLMPolicyV7_0(self.client)
        self._holds_action_lock = False
        self._game_start_time = time.time()
        self._actions_in_game = 0
        self._first_action = True
    
    @property
    def name(self) -> str:
        return f"{super().name}.llm-v7"
    
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
            # Build frame dict for v7.0 policy
            grid = _extract_grid(latest_frame)
            
            # Available actions
            available = []
            try:
                for act_id in latest_frame.available_actions:
                    try:
                        act = GameAction.from_id(int(act_id))
                        if act.name != "RESET":
                            available.append(act.name)
                    except Exception:
                        pass
            except Exception:
                available = ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"]
            
            # State info
            try:
                state_name = latest_frame.state.name if hasattr(latest_frame.state, "name") else str(latest_frame.state)
            except Exception:
                state_name = "PLAYING"
            
            try:
                levels_completed = int(latest_frame.levels_completed)
            except Exception:
                levels_completed = 0
            
            # Build frame dict that v7.0 policy expects
            frame_dict = {
                "grid": [list(row) for row in grid],
                "available_actions": available,
                "levels_completed": levels_completed,
                "current_level": levels_completed + 1,
                "action_count": self._actions_in_game,
                "actions_since_level": self._actions_in_game,  # simplified
                "lives": 3,  # default
                "score": 0,
                "step_limit": self.ACTION_BUDGET,
                "no_op_count": 0,
                "goal_class": None,
                "game": "unknown",
                "state_name": state_name,
            }
            
            # Initialize on first call
            if self._first_action:
                self._first_action = False
                self._game_start_time = time.time()
                self.policy.reset()
            
            # Auto-reset on GAME_OVER
            if state_name == "GAME_OVER":
                self.policy.record_game_over("Auto-reset: GAME_OVER state")
                action = GameAction.RESET
                action.set_data({})
                action.reasoning = {"auto_reset": True, "game_over": True}
                return action
            
            # Call the LLM policy v7.0
            proposal = self.policy.get_action(frame_dict)
            self._actions_in_game += 1
            
            # Normalize proposal keys (v7.0 returns 'action', we need 'name')
            if "action" in proposal and "name" not in proposal:
                proposal["name"] = proposal["action"]
            
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
        goal_class = getattr(self.policy.state, "goal_class", None)
        stuck = getattr(self.policy.state, "stuck_count", 0)
        levels = getattr(self.policy.state, "current_level", 1) - 1
        ml_value = getattr(self.policy.state, "ml_value", 0.5)
        print(f"[LLMAgent-v7] Game done: "
              f"{self._actions_in_game} actions in {elapsed:.0f}s, "
              f"levels={levels}, goal_class={goal_class}, stuck_count={stuck}, "
              f"ml_value={ml_value:.2f}")
