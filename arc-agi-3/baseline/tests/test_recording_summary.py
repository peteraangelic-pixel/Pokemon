"""Regression tests for the portable public-recording visual summary."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import summarize_recordings  # noqa: E402


class RecordingSummaryTests(unittest.TestCase):
    def test_frame_to_text_uses_palette_and_unknown_marker(self) -> None:
        self.assertEqual(
            summarize_recordings.frame_to_text([[[0, 10, 15, 99], [1]]]),
            "0AF?\n1???",
        )
        self.assertEqual(summarize_recordings.frame_to_text([]), "<no frame>")

    def test_striped_avatar_tile_reports_coarse_coordinate_or_safe_placeholder(self) -> None:
        grid = [[4 for _ in range(12)] for _ in range(12)]
        for row, color in enumerate((12, 12, 9, 9, 9)):
            grid[5 + row][4:9] = [color] * 5
        self.assertEqual(summarize_recordings.striped_avatar_tile(grid), "(0,1)")
        self.assertEqual(summarize_recordings.striped_avatar_tile([[4] * 4 for _ in range(4)]), "-")

    def test_summary_keeps_first_and_final_of_longest_recording_per_game(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recordings = Path(directory)
            short = recordings / "ls20.short.recording.jsonl"
            long = recordings / "ls20.long.recording.jsonl"
            short.write_text(json.dumps({"data": {"game_id": "ls20-a", "frame": [[[1]]]}}) + "\n")
            long.write_text(
                "\n".join(
                    json.dumps({"data": event})
                    for event in (
                        {"game_id": "ls20-a", "frame": [[[1]]], "state": "NOT_FINISHED", "levels_completed": 0},
                        {
                            "game_id": "ls20-a",
                            "frame": [[[2]]],
                            "state": "WIN",
                            "levels_completed": 1,
                            "action_input": {"id": 6},
                            "reasoning": {"must_not": "appear"},
                        },
                    )
                )
                + "\n"
            )
            summary = summarize_recordings.summarize_paths(recordings.glob("*.jsonl"))

        self.assertIn("### ls20 (2 recorded frames)", summary)
        self.assertIn("**first**", summary)
        self.assertIn("**final** — action 6, state `WIN`, levels `1`", summary)
        self.assertIn("\n1\n", summary)
        self.assertIn("\n2\n", summary)
        self.assertNotIn("must_not", summary)

    def test_transition_geometry_reports_action_coordinates_and_delta_box(self) -> None:
        events = [
            {"frame": [[[0, 0], [0, 0]]], "state": "NOT_FINISHED"},
            {
                "frame": [[[0, 0], [0, 9]]],
                "state": "NOT_FINISHED",
                "action_input": {"id": 6, "data": {"x": 1, "y": 1}},
            },
        ]
        table = "\n".join(summarize_recordings.transition_geometry(events))
        self.assertIn("action 6 at (1, 1)", table)
        self.assertIn("| 2 | action 6 at (1, 1) | 1 | `x=1..1, y=1..1` | 1 |", table)

    def test_checkpoint_windows_include_later_progress_and_only_safe_policy_kind(self) -> None:
        def frame(color: int) -> list[list[list[int]]]:
            return [[[color] * 5 for _ in range(5)]]

        events = [
            {"frame": frame(0), "state": "NOT_FINISHED", "levels_completed": 0},
            {
                "frame": frame(1),
                "state": "GAME_OVER",
                "levels_completed": 0,
                "action_input": {
                    "id": 3,
                    "reasoning": {"kind": "tile-maze-navigation", "private": "must-not-appear"},
                },
            },
            {
                "frame": frame(2),
                "state": "NOT_FINISHED",
                "levels_completed": 0,
                "action_input": {"id": 4, "reasoning": {"kind": "bad|secret"}},
            },
            {
                "frame": frame(3),
                "state": "NOT_FINISHED",
                "levels_completed": 1,
                "action_input": {"id": 1, "reasoning": {"kind": "resource-navigation"}},
            },
        ]
        table = "\n".join(summarize_recordings.checkpoint_transition_geometry(events))

        self.assertIn("Checkpoint transition windows", table)
        self.assertIn("state-change", table)
        self.assertIn("level 0->1", table)
        self.assertIn("tile-maze-navigation", table)
        self.assertIn("resource-navigation", table)
        self.assertNotIn("must-not-appear", table)
        self.assertNotIn("bad|secret", table)

    def test_empty_directory_has_explicit_safe_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = summarize_recordings.summarize_paths(Path(directory).glob("*.jsonl"))
        self.assertIn("No usable frame recording", summary)


if __name__ == "__main__":
    unittest.main()
