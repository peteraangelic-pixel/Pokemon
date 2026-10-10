"""Tests for the local-to-GitHub compact ARC outcome formatter."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_check_summary  # noqa: E402


class CheckSummaryTests(unittest.TestCase):
    def test_build_summary_includes_safe_outcomes_evidence_and_sketch(self) -> None:
        report = {
            "scorecard": "1.5",
            "results": [
                {
                    "game_id": "vc33",
                    "state": "WIN",
                    "levels_completed": 1,
                    "actions": 8,
                    "policy_evidence": {
                        "ACTION6": {
                            "attempts": 8,
                            "changed": 6,
                            "level_gains": 1,
                            "game_overs": 0,
                        }
                    },
                    "policy_decisions": {
                        "graph-click-frontier": 3,
                        "meter-bounded-resource": 1,
                    },
                    "meter_evidence": {
                        "candidate-observations": 12,
                        "estimates-established": 1,
                    },
                    "token_evidence": {
                        "control-entries": 2,
                        "orientation-improving-entries": 1,
                    },
                    "policy_trace": [
                        {
                            "action": "ACTION6:2:3",
                            "changed": True,
                            "decision_kind": "graph-click-frontier",
                            "levels_completed": 0,
                        },
                        {
                            "action": "ACTION6:3:3",
                            "changed": True,
                            "decision_kind": "meter-bounded-resource",
                            "levels_completed": 1,
                        },
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / "report.json"
            sketch_path = root / "sketch.md"
            log_path = root / "log.txt"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            sketch_path.write_text("## Recorded frame sketches\n\n```text\n012\n```\n", encoding="utf-8")
            summary = publish_check_summary.build_summary(report_path, sketch_path, log_path)

        self.assertIn("| vc33 | WIN | 1 | 8 |", summary)
        self.assertIn("ACTION6: 6/8 changed, 1 level gains, 0 game overs", summary)
        self.assertIn("ACTION6:2:3 (changed)", summary)
        self.assertIn("Decision modes: graph-click-frontier: 3; meter-bounded-resource: 1", summary)
        self.assertIn(
            "Modes by resulting level: L0: graph-click-frontier: 1 | L1: meter-bounded-resource: 1",
            summary,
        )
        self.assertIn("Meter evidence: candidate-observations: 12; estimates-established: 1", summary)
        self.assertIn(
            "Token/control evidence: control-entries: 2; orientation-improving-entries: 1",
            summary,
        )
        self.assertIn("Scorecard: `1.5`", summary)
        self.assertIn("## Recorded frame sketches", summary)

    def test_build_summary_uses_log_tail_when_report_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "log.txt"
            log_path.write_text("x" * 5000 + "tail", encoding="utf-8")
            summary = publish_check_summary.build_summary(
                root / "missing.json", root / "missing.md", log_path
            )

        self.assertIn("No structured report was produced", summary)
        self.assertIn("tail", summary)
        self.assertLessEqual(len(summary), 4200)
        self.assertNotIn("x" * 4001, summary)

    def test_build_summary_bounds_large_sketches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / "report.json"
            sketch_path = root / "sketch.md"
            report_path.write_text('{"results": [], "scorecard": null}', encoding="utf-8")
            sketch_path.write_text("z" * 70000, encoding="utf-8")
            summary = publish_check_summary.build_summary(report_path, sketch_path, root / "none")

        self.assertLessEqual(len(summary), 65000)
        self.assertIn("no completed game report", summary)


if __name__ == "__main__":
    unittest.main()
