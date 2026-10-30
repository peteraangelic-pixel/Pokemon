"""Minimal faithful stub of the harness's `arcengine` module for offline tests.

Mirrors only what arc3_winpath touches:
  GameAction[name]  -> member whose .value is the int action id and .name the label
  ActionInput(id=..., data=...)
"""
import enum
from dataclasses import dataclass, field


class GameAction(enum.Enum):
    RESET = 0
    ACTION1 = 1
    ACTION2 = 2
    ACTION3 = 3
    ACTION4 = 4
    ACTION5 = 5
    ACTION6 = 6
    ACTION7 = 7


@dataclass
class ActionInput:
    id: GameAction
    data: dict = field(default_factory=dict)
