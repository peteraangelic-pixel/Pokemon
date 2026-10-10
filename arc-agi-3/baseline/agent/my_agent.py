"""ARC-AGI-3 SDK adapter for the deterministic novelty-explorer baseline.

The policy itself lives in :mod:`policy` and has no third-party dependencies.
This adapter is intentionally thin: it converts ``FrameData`` to a Snapshot,
asks the policy for one legal proposal, and converts that proposal back to a
``GameAction`` expected by ARC's reference agent framework.
"""
from __future__ import annotations

from threading import RLock
from typing import Any

from arcengine import ActionInput, FrameData, GameAction, GameState
from agents.agent import Agent

try:  # Package import on Kaggle, direct-file import in scripts/play_local.py.
    from .policy import ActionProposal, ExplorerPolicy, snapshot_from_frame
except ImportError:  # pragma: no cover - exercised by the local framework loader
    from policy import ActionProposal, ExplorerPolicy, snapshot_from_frame


class MyAgent(Agent):
    """A reproducible perception-and-novelty baseline for ARC-AGI-3."""

    # ``GameAction`` is an enum whose members carry mutable ``action_data``.
    # The upstream Swarm runs game agents in threads, so protect conversion and
    # the immediately following environment step as one critical section.
    _ACTION_LOCK = RLock()

    # This is an exploration ceiling, not a target. Competition scoring rewards
    # few actions, but a non-random baseline needs room to infer simple controls.
    # The reference Agent loop uses ``<= MAX_ACTIONS``, so ``is_done`` below
    # additionally enforces this exact budget instead of allowing an off-by-one.
    ACTION_BUDGET = 240
    MAX_ACTIONS = ACTION_BUDGET

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = ExplorerPolicy()
        self._holds_action_lock = False

    @property
    def name(self) -> str:
        return f"{super().name}.novelty-v5"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        """Stop on win or budget; GAME_OVER must otherwise be followed by RESET."""
        return self.action_counter >= self.ACTION_BUDGET or latest_frame.state is GameState.WIN

    @staticmethod
    def _to_game_action(proposal: ActionProposal) -> GameAction:
        """Translate a validated policy proposal to the ARC SDK enum."""
        try:
            action = GameAction[proposal.name]
        except KeyError:
            # A policy bug must never emit an invalid action to a competition
            # environment. RESET is the protocol-safe recovery operation.
            action = GameAction.RESET

        if action.is_complex():
            x = 0 if proposal.x is None else max(0, min(63, int(proposal.x)))
            y = 0 if proposal.y is None else max(0, min(63, int(proposal.y)))
            action.set_data({"x": x, "y": y})
        else:
            # GameAction members are enum singletons; reset their payload so a
            # previous call cannot leak data into a later action.
            action.set_data({})
        action.reasoning = proposal.reasoning
        return action

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        # Agent.main() invokes take_action immediately after this method. Hold
        # the lock over that pair so another swarm thread cannot overwrite a
        # mutable GameAction enum member between conversion and env.step().
        self._ACTION_LOCK.acquire()
        self._holds_action_lock = True
        try:
            snapshot = snapshot_from_frame(latest_frame)
            proposal = self.policy.choose(snapshot)
            return self._to_game_action(proposal)
        except Exception:
            self._holds_action_lock = False
            self._ACTION_LOCK.release()
            raise

    def finalize_diagnostics(self) -> None:
        """Record the final returned frame without submitting another action."""
        if self.frames:
            self.policy.finalize(snapshot_from_frame(self.frames[-1]))

    def take_action(self, action: GameAction):  # type: ignore[override]
        try:
            frame = super().take_action(action)
            if frame is not None:
                # The current reference Agent conversion omits raw.action_input.
                # Restore the exact submitted action before append_frame records
                # it, preserving a usable public replay and action/frame pairing.
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
