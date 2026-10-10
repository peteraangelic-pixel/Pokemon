"""graph_evidence() must honestly report whether revisited states are recognised.

If this regresses, exploration silently degenerates into repeated probing: the
agent keeps seeing a "new" state and never learns that it has been there.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.policy import COMPLEX_ACTION, ExplorerPolicy, Snapshot  # noqa: E402


def snapshot(*, fill: int, state: str = "PLAYING", levels: int = 0) -> Snapshot:
    grid = tuple(tuple(fill for _ in range(6)) for _ in range(6))
    return Snapshot(
        state=state,
        levels_completed=levels,
        available_actions=(COMPLEX_ACTION,),
        planes=(grid,),
    )


class GraphEvidenceTests(unittest.TestCase):
    def test_repeated_identical_states_are_recognised(self) -> None:
        policy = ExplorerPolicy()
        for _ in range(4):
            policy.choose(snapshot(fill=1))
        ev = policy.graph_evidence()
        self.assertEqual(ev["observations"], 4)
        self.assertEqual(ev["distinct_states"], 1)
        self.assertEqual(ev["distinct_ratio_permille"], 250)

    def test_distinct_states_are_counted_separately(self) -> None:
        policy = ExplorerPolicy()
        for fill in (1, 2, 3):
            policy.choose(snapshot(fill=fill))
        ev = policy.graph_evidence()
        self.assertEqual(ev["observations"], 3)
        self.assertEqual(ev["distinct_states"], 3)

    def test_level_progress_changes_the_signature(self) -> None:
        policy = ExplorerPolicy()
        policy.choose(snapshot(fill=1, levels=0))
        policy.choose(snapshot(fill=1, levels=1))
        self.assertEqual(policy.graph_evidence()["distinct_states"], 2)

    def test_evidence_contains_only_integers(self) -> None:
        policy = ExplorerPolicy()
        policy.choose(snapshot(fill=1))
        ev = policy.graph_evidence()
        self.assertTrue(ev)
        for key, value in ev.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, int)


if __name__ == "__main__":
    unittest.main()
