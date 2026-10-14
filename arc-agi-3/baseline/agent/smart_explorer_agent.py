"""ARC-AGI-3 SDK adapter for SmartExplorer agent."""
from __future__ import annotations

from threading import RLock
from typing import Any

from arcengine import ActionInput, FrameData, GameAction, GameState
from agents.agent import Agent

try:
    from .smart_explorer import SmartExplorerPolicy, ActionProposal, Snapshot
except ImportError:
    from smart_explorer import SmartExplorerPolicy, ActionProposal, Snapshot


def snapshot_from_frame_smart(frame: FrameData) -> Snapshot:
    """Build a Snapshot from an ARC FrameData."""
    grid_data = getattr(frame, 'frame', [])
    if grid_data and len(grid_data) > 0:
        grid = tuple(tuple(row) for row in grid_data[0])
    else:
        grid = ()
    
    available = list(getattr(frame, 'available_actions', []))
    levels_completed = int(getattr(frame, 'levels_completed', 0) or 0)
    state = str(getattr(frame, 'state', 'NOT_PLAYED'))
    
    return Snapshot(
        grid=grid,
        available_actions=available,
        levels_completed=levels_completed,
        state=state,
    )


class SmartExplorerAgent(Agent):
    """Agresywny agent eksploracyjny - uczy się z eksperymentów."""
    
    _ACTION_LOCK = RLock()
    
    # Budżet akcji - wystarczający na eksplorację
    ACTION_BUDGET = 300
    MAX_ACTIONS = ACTION_BUDGET
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = SmartExplorerPolicy()
        self._holds_action_lock = False
        self._last_levels_completed = 0
    
    @property
    def name(self) -> str:
        return f"{super().name}.smart-explorer-v1"
    
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        """Stop on win or budget."""
        return self.action_counter >= self.ACTION_BUDGET or latest_frame.state is GameState.WIN
    
    @staticmethod
    def _to_game_action(proposal: ActionProposal) -> GameAction:
        """Translate a proposal to the ARC SDK enum."""
        try:
            action = GameAction[proposal.name]
        except KeyError:
            action = GameAction.RESET
        
        if action.is_complex():
            x = 0 if proposal.x is None else max(0, min(63, int(proposal.x)))
            y = 0 if proposal.y is None else max(0, min(63, int(proposal.y)))
            action.set_data({"x": x, "y": y})
        else:
            action.set_data({})
        
        action.reasoning = proposal.reasoning
        return action
    
    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        self._ACTION_LOCK.acquire()
        self._holds_action_lock = True
        try:
            # Sprawdź, czy przeszedł do nowego poziomu
            current_levels = int(getattr(latest_frame, 'levels_completed', 0) or 0)
            if current_levels > self._last_levels_completed:
                self.policy.reset_level()
                self._last_levels_completed = current_levels
            
            snapshot = snapshot_from_frame_smart(latest_frame)
            proposal = self.policy.choose(snapshot)
            return self._to_game_action(proposal)
        except Exception:
            self._holds_action_lock = False
            self._ACTION_LOCK.release()
            raise
    
    def take_action(self, action: GameAction):
        try:
            frame = super().take_action(action)
            if frame is not None:
                frame.action_input = ActionInput(
                    action.name,
                    action.action_data if hasattr(action, 'action_data') else {},
                )
            return frame
        finally:
            if self._holds_action_lock:
                self._holds_action_lock = False
                self._ACTION_LOCK.release()
    
    def finalize_diagnostics(self) -> None:
        """Record final state."""
        if self.frames:
            stats = self.policy.action_stats
            print(f"[SmartExplorer] Level {self.policy.level}, Stats: {dict(stats)}")
