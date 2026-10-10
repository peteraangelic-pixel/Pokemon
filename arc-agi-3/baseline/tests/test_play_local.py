"""Tests for the local public-game runner's portable outcome report."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import play_local  # noqa: E402


class _State:
    value = "game_over"


class _Scorecard:
    score = 1.75


class LocalRunnerReportTests(unittest.TestCase):
    def test_policy_trace_limit_preserves_short_runs_and_bounds_long_ones(self) -> None:
        self.assertEqual(play_local._policy_trace_limit(17), 17)
        self.assertEqual(play_local._policy_trace_limit(1_000), 1_000)
        self.assertEqual(play_local._policy_trace_limit(50_000), 1_000)

    def test_state_name_accepts_sdk_like_enums_and_plain_values(self) -> None:
        self.assertEqual(play_local._state_name(_State()), "GAME_OVER")
        self.assertEqual(play_local._state_name("win"), "WIN")

    def test_write_report_is_compact_json_safe_and_frame_free(self) -> None:
        result = play_local.RunResult(
            game_id="ls20",
            state="NOT_FINISHED",
            levels_completed=2,
            actions=17,
            policy_evidence={"ACTION6": {"attempts": 4, "changed": 3}},
            policy_decisions={"graph-click-frontier": 1},
            meter_evidence={"candidate-observations": 2, "estimates-established": 1},
            token_evidence={"control-entries": 1, "orientation-improving-entries": 1},
            policy_trace=[
                {
                    "action": "ACTION6:1:1",
                    "decision_kind": "graph-click-frontier",
                    "meter_bounded_resource": False,
                    "changed": True,
                    "level_gain": 0,
                    "game_over": False,
                    "revisit": False,
                    "next_state": "NOT_FINISHED",
                    "levels_completed": 2,
                }
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            play_local.write_report(
                path,
                requested_games=["ls20", "vc33"],
                results=[result],
                scorecard=_Scorecard(),
            )
            report = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["requested_games"], ["ls20", "vc33"])
        self.assertEqual(report["scorecard"], "1.75")
        self.assertEqual(report["results"], [
            {
                "actions": 17,
                "game_id": "ls20",
                "levels_completed": 2,
                "meter_evidence": {"candidate-observations": 2, "estimates-established": 1},
                "policy_decisions": {"graph-click-frontier": 1},
                "policy_evidence": {"ACTION6": {"attempts": 4, "changed": 3}},
                "token_evidence": {"control-entries": 1, "orientation-improving-entries": 1},
                "policy_trace": [
                    {
                        "action": "ACTION6:1:1",
                        "changed": True,
                        "decision_kind": "graph-click-frontier",
                        "meter_bounded_resource": False,
                        "game_over": False,
                        "level_gain": 0,
                        "levels_completed": 2,
                        "next_state": "NOT_FINISHED",
                        "revisit": False,
                    }
                ],
                "state": "NOT_FINISHED",
            }
        ])
        self.assertNotIn("frame", path.name + json.dumps(report).lower())


if __name__ == "__main__":
    unittest.main()
