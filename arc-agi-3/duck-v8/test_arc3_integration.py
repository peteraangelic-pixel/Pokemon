"""Offline INTEGRATION test for patch 0004 (solved-level replay).

Unlike test_arc3_replay.py (pure logic), this drives the REAL patched
ToolAgent._run_python_tool with a fake step-env callback - no GPU, no LLM,
no arcengine. The model's tool calls are replaced by fixed `code` strings
that call action([...]) exactly like model-generated code would.

Requirements:
  * A PATCHED ARC3-Inference tree (bundle + 0004 applied). Point
    ARC3_BUNDLE_SRC at the directory containing `inference/`.
  * requests + pillow importable (ToolAgent imports them).

Run:
  ARC3_BUNDLE_SRC=/path/to/ARC3-Inference python3 -m pytest test_arc3_integration.py -q

The fake game has 2 levels. Level 1 is solved by ACTION1, ACTION2.
Level semantics mirror the real harness payloads (see r050 transcripts).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BUNDLE_SRC = os.environ.get("ARC3_BUNDLE_SRC", "")
if BUNDLE_SRC and BUNDLE_SRC not in sys.path:
    sys.path.insert(0, BUNDLE_SRC)
    # the sandbox child process inherits env, not sys.path
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [BUNDLE_SRC, os.environ.get("PYTHONPATH", "")]
    ).strip(os.pathsep)

try:
    from inference.agent.runtime_state import Frame, HistoryEntry, write_runtime_state
    from inference.agent.tool_agent import ToolAgent
    from inference.agent.arc3_replay import SolutionStore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"patched bundle not importable ({exc!r}); set ARC3_BUNDLE_SRC", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fake environment (harness-side): deterministic 2-level game
# ---------------------------------------------------------------------------

L1_START = ((1, 0), (0, 0))
L1_MID = ((2, 0), (0, 0))
L2_START = ((9, 9), (9, 0))
L2_MID = ((9, 9), (9, 5))
L1_DIVERGED = ((7, 0), (0, 0))  # what ACTION1 does in the "diverged" world


class FakeEnv:
    def __init__(self, state_path: Path, *, diverged: bool = False) -> None:
        self.state_path = state_path
        self.diverged = diverged
        self.grid: tuple = L1_START
        self.level = 1
        self.step = 0
        self.history: list[HistoryEntry] = []
        self.executed: list[str] = []
        write_runtime_state(
            state_path,
            current_frame=Frame(grid=self.grid, step=0, level=1),
            history=[],
        )

    # --- transitions -------------------------------------------------------
    def _apply(self, name: str) -> bool:
        """Returns level_completed."""
        if self.level == 1 and name == "ACTION1":
            self.grid = L1_DIVERGED if self.diverged else L1_MID
            return False
        if self.level == 1 and name == "ACTION2" and not self.diverged:
            self.grid = L2_START
            self.level = 2
            return True
        if self.level == 2 and name == "ACTION3":
            self.grid = L2_MID
            return False
        return False

    # --- harness step-env callback ----------------------------------------
    def callback(self, payload: dict) -> dict:
        actions = list(payload.get("actions") or [])
        completed = False
        for item in actions:
            name = str(item.get("action", ""))
            self.executed.append(name)
            self.step += 1
            if self._apply(name):
                completed = True
            self.history.append(
                HistoryEntry(action=name, frame=Frame(grid=self.grid, step=self.step, level=self.level))
            )
            write_runtime_state(
                self.state_path,
                current_frame=Frame(grid=self.grid, step=self.step, level=self.level),
                history=self.history,
            )
        return {
            "executed": True,
            "action_num": self.step,
            "level": self.level,
            "score": 0,
            "reward": 0.0,
            "state": "NOT_FINISHED",
            "valid_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION9"],
            "board_changed": True,
            "done": False,
            "level_completed": completed,
            "game_over": False,
            "run_complete": False,
            "action_display": str(actions[-1].get("action")) if actions else "",
            "executed_actions": [str(a.get("action")) for a in actions],
            "requested_count": len(actions),
            "executed_count": len(actions),
        }


def _agent(state_path: Path, env: FakeEnv) -> ToolAgent:
    os.environ.setdefault("LOCAL_ANALYZER_MODEL_ID", "test-model")
    agent = ToolAgent(model="local")
    agent._step_env_callback = env.callback  # what HarnessSolver wires in
    return agent


def _play(agent: ToolAgent, state_path: Path, *action_names: str) -> None:
    listed = ", ".join("{'action': '%s'}" % n for n in action_names)
    agent._run_python_tool(state_path, {"code": f"action([{listed}])\n"})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_record_then_replay_in_fresh_session(tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    monkeypatch.setenv("ARC3_REPLAY", "1")
    monkeypatch.setenv("ARC3_REPLAY_DIR", str(store_dir))

    # Session 1: solve level 1 (ACTION1, ACTION2), then touch level 2 so the
    # level-1 segment closes and gets recorded.
    s1 = tmp_path / "a" / "testgame_p0_tool_runtime_state.json"
    env1 = FakeEnv(s1)
    agent1 = _agent(s1, env1)
    _play(agent1, s1, "ACTION1", "ACTION2")
    _play(agent1, s1, "ACTION3")

    sol = SolutionStore(store_dir).best("testgame", 1)
    assert sol is not None, "level-1 solution was not recorded"
    assert [a["action"] for a in sol["actions"]] == ["ACTION1", "ACTION2"]

    # Session 2: fresh game, fresh agent, same store. The model's first (and
    # only) decision is ACTION9 - replay must drive ACTION1, ACTION2 first.
    s2 = tmp_path / "b" / "testgame_p0_tool_runtime_state.json"
    env2 = FakeEnv(s2)
    agent2 = _agent(s2, env2)
    _play(agent2, s2, "ACTION9")

    assert env2.executed == ["ACTION1", "ACTION2", "ACTION9"]
    assert env2.level == 2


def test_divergence_aborts_replay_and_model_takes_over(tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    monkeypatch.setenv("ARC3_REPLAY", "1")
    monkeypatch.setenv("ARC3_REPLAY_DIR", str(store_dir))
    SolutionStore(store_dir).record(
        "testgame", 1,
        start_hash=_hash(L1_START, 1),
        actions=[{"action": "ACTION1"}, {"action": "ACTION2"}],
        end_hash=_hash(L2_START, 2),
        step_hashes=[_hash(L1_MID, 1), _hash(L2_START, 2)],
    )
    s = tmp_path / "testgame_p0_tool_runtime_state.json"
    env = FakeEnv(s, diverged=True)  # ACTION1 lands somewhere else here
    agent = _agent(s, env)
    _play(agent, s, "ACTION9")
    # replay tried ACTION1, hash mismatched, stopped; model action followed.
    assert env.executed == ["ACTION1", "ACTION9"]


def test_kill_switch_disables_everything(tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    monkeypatch.delenv("ARC3_REPLAY", raising=False)
    monkeypatch.setenv("ARC3_REPLAY_DIR", str(store_dir))
    s = tmp_path / "testgame_p0_tool_runtime_state.json"
    env = FakeEnv(s)
    agent = _agent(s, env)
    _play(agent, s, "ACTION1", "ACTION2")
    _play(agent, s, "ACTION3")
    assert env.executed == ["ACTION1", "ACTION2", "ACTION3"]  # untouched flow
    assert SolutionStore(store_dir).best("testgame", 1) is None  # nothing stored


def _hash(grid, level):
    from inference.agent.arc3_replay import frame_hash

    return frame_hash(grid, level=level)
