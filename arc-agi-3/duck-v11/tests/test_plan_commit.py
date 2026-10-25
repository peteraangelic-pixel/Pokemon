"""Offline tests for commit(): pure logic and the real sandbox.

No GPU, no game, no model. The integration half runs the same bootstrap string
the Kaggle kernel runs, with a scripted four-cell world standing in for the
engine, so `commit()` is exercised exactly where it will be used.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inference.utils.plan_commit import (  # noqa: E402
    pc_digest,
    pc_observe,
    pc_play,
)


class _Frame:
    def __init__(self, ascii_text, step=0, level=1, shape=(4, 4)):
        self.ascii = ascii_text
        self.step = step
        self.level = level
        self.shape = shape


BOARD = "\n".join(["WWWW", "WRWW", "WWWW", "WWWW"])


class _World:
    """One marker on a 4x4 board; UP moves it up, DOWN moves it down."""

    def __init__(self):
        self.row = 1
        self.step = 0
        self.level = 1
        self.terminal = None

    def render(self):
        rows = [["W"] * 4 for _ in range(4)]
        rows[self.row][1] = "R"
        return "\n".join("".join(row) for row in rows)

    def frame(self):
        return _Frame(self.render(), step=self.step, level=self.level)

    def act(self, action):
        name = str(action.get("action", "")).upper()
        before = self.render()
        self.step += 1
        if name == "UP" and self.row > 0:
            self.row -= 1
        elif name == "DOWN" and self.row < 3:
            self.row += 1
        elif name == "WIN":
            self.level += 1
            self.terminal = "level_completed"
        after = self.render()
        return {
            "executed": True,
            "level": self.level,
            "step": self.step,
            "board_changed": before != after,
            "level_completed": self.terminal == "level_completed",
            "game_over": False,
            "run_complete": False,
            "done": False,
        }


def _play(world, plan, **kwargs):
    return pc_play(plan, world.act, world.frame, **kwargs)


class PlanCommitUnitTests(unittest.TestCase):
    def test_clean_plan_runs_to_the_end(self):
        world = _World()
        report = _play(world, ["UP", "DOWN", "UP"])
        self.assertEqual(report["stop_reason"], "complete")
        self.assertEqual(report["executed"], 3)
        self.assertEqual(report["requested"], 3)
        self.assertEqual(report["expectations_checked"], 0)
        self.assertNotIn("mismatch", report)

    def test_stops_on_the_first_failed_expectation(self):
        world = _World()
        report = _play(world, [
            "UP",
            {"action": "DOWN", "expect": {"level": 9}},
            "UP",
            "UP",
        ])
        self.assertEqual(report["stop_reason"], "mismatch")
        self.assertEqual(report["executed"], 2, "the rest of the plan must not run")
        self.assertEqual(report["mismatch"]["step"], 2)
        self.assertEqual(report["mismatch"]["failed"][0]["field"], "level")
        self.assertEqual(report["mismatch"]["failed"][0]["got"], 1)

    def test_cells_expectation_matches_the_observed_board(self):
        world = _World()
        report = _play(world, [
            {"action": "UP", "expect": {"cells": {"0,1": "R"}}},
        ])
        self.assertEqual(report["stop_reason"], "complete")
        self.assertEqual(report["expectations_checked"], 1)

    def test_cells_expectation_reports_the_cell_that_moved(self):
        world = _World()
        report = _play(world, [
            {"action": "UP", "expect": {"cells": {"0,1": "W"}}},
        ])
        self.assertEqual(report["stop_reason"], "mismatch")
        failure = report["mismatch"]["failed"][0]
        self.assertEqual(failure["field"], "cell(0,1)")
        self.assertEqual(failure["got"], "R")

    def test_board_changed_expectation(self):
        world = _World()
        hanging = _play(world, [{"action": "UP", "expect": {"board_changed": False}}])
        self.assertEqual(hanging["stop_reason"], "mismatch")
        world = _World()
        moved = _play(world, [{"action": "UP", "expect": {"board_changed": True}}])
        self.assertEqual(moved["stop_reason"], "complete")

    def test_level_completion_ends_the_plan(self):
        world = _World()
        report = _play(world, ["WIN", "UP", "UP"])
        self.assertEqual(report["stop_reason"], "level_completed")
        self.assertEqual(report["executed"], 1)
        self.assertEqual(report["terminal"]["reason"], "level_completed")

    def test_max_actions_caps_a_runaway_plan(self):
        world = _World()
        report = _play(world, ["UP"] * 100, max_actions=5)
        self.assertEqual(report["stop_reason"], "max_actions")
        self.assertEqual(report["executed"], 5)
        self.assertEqual(world.step, 5)

    def test_digest_is_stable_and_input_sensitive(self):
        self.assertEqual(pc_digest(BOARD), pc_digest(BOARD))
        self.assertNotEqual(pc_digest(BOARD), pc_digest(BOARD.replace("R", "B")))
        self.assertEqual(len(pc_digest(BOARD)), 16)

    def test_observe_uses_the_action_result_level(self):
        observed = pc_observe(_Frame(BOARD, level=1), {"level": 2, "board_changed": True})
        self.assertEqual(observed["level"], 2)
        self.assertTrue(observed["board_changed"])


def _state(world):
    frame = world.frame()
    payload = {
        "ascii": frame.ascii,
        "step": frame.step,
        "level": frame.level,
        "shape": [4, 4],
        "grid": [[0] * 4 for _ in range(4)],
    }
    return {
        "current_frame": payload,
        "history": [],
        "valid_actions": ["UP", "DOWN", "WIN"],
        "last_action_result": {},
    }


class PlanCommitSandboxTests(unittest.TestCase):
    """Runs commit() inside the real sandbox bootstrap string."""

    def setUp(self):
        os.environ["ARC3_PLAN_COMMIT"] = "1"

    def tearDown(self):
        os.environ.pop("ARC3_PLAN_COMMIT", None)

    def _run(self, code):
        from inference.agent.python_tool_sandbox import run_sandboxed_python

        world = _World()

        def handler(actions, stale_after=None):
            results = []
            for action in actions:
                result = world.act(action)
                results.append(result)
            return {
                "action_result": results[-1] if results else {"executed": False},
                "state": _state(world),
            }

        state = _state(world)
        return run_sandboxed_python(
            code=code,
            timeout_seconds=30,
            initial_state=state,
            action_handler=handler,
        )

    def test_commit_is_exposed_and_reports_a_mismatch(self):
        out = self._run(
            "good = commit(['UP', {'action': 'DOWN', 'expect': {'board_changed': True}}])\n"
            "bad = commit(['UP', {'action': 'UP', 'expect': {'level': 7}}, 'DOWN'])\n"
            "result = {'good': good, 'bad': bad, 'digest': frame_digest()}\n"
        )
        self.assertFalse(out.get("error"), out.get("error"))
        payload = out["result"]
        self.assertEqual(payload["good"]["stop_reason"], "complete")
        self.assertEqual(payload["good"]["executed"], 2)
        self.assertEqual(payload["bad"]["stop_reason"], "mismatch")
        self.assertEqual(payload["bad"]["executed"], 2)
        self.assertEqual(payload["bad"]["mismatch"]["failed"][0]["field"], "level")
        self.assertEqual(len(payload["digest"]), 16)

    def test_world_model_tools_ride_along_with_plan_commit(self):
        # Escalation needs check_model()/plan(); they are exposed with commit()
        # even though ARC3_WORLD_MODEL (addendum + auto report) stays off.
        os.environ["ARC3_PLAN_COMMIT"] = "1"
        os.environ.pop("ARC3_WORLD_MODEL", None)
        from inference.agent.python_tool_sandbox import run_sandboxed_python

        world = _World()
        out = run_sandboxed_python(
            code=(
                "result = ['commit' in dir(), 'check_model' in dir(), "
                "'plan' in dir(), 'frame_digest' in dir()]\n"
            ),
            timeout_seconds=30,
            initial_state=_state(world),
            action_handler=lambda actions, stale_after=None: {
                "action_result": {"executed": False}, "state": _state(world)},
        )
        self.assertFalse(out.get("error"), out.get("error"))
        self.assertEqual(out["result"], [True, True, True, True])

    def test_commit_is_absent_when_the_switch_is_off(self):
        from inference.agent.python_tool_sandbox import run_sandboxed_python

        os.environ.pop("ARC3_PLAN_COMMIT", None)
        world = _World()
        state = _state(world)
        out = run_sandboxed_python(
            code="result = 'commit' in dir()\n",
            timeout_seconds=30,
            initial_state=state,
            action_handler=lambda actions, stale_after=None: {
                "action_result": {"executed": False}, "state": _state(world)},
        )
        self.assertFalse(out.get("error"), out.get("error"))
        self.assertFalse(out["result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
