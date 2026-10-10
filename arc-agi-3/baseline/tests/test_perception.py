"""Perception signals: motion tracking and maze anti-oscillation memory.

These guard the two fixes that broke the revisit plateau. If either regresses,
the agent silently falls back to cycling through a handful of states.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.policy import (  # noqa: E402
    Component,
    moving_component_cells,
)


def component(color: int, cells) -> Component:
    return Component(color=color, cells=tuple(sorted(cells, key=lambda p: (p[1], p[0]))))


class MotionTrackingTests(unittest.TestCase):
    def test_no_reference_frame_yields_no_motion(self) -> None:
        current = (component(1, [(0, 0)]),)
        self.assertEqual(moving_component_cells((), current), frozenset())

    def test_static_world_yields_no_motion(self) -> None:
        before = (component(1, [(5, 5), (6, 5)]),)
        after = (component(1, [(5, 5), (6, 5)]),)
        self.assertEqual(moving_component_cells(before, after), frozenset())

    def test_translated_component_is_detected(self) -> None:
        before = (component(1, [(5, 5), (6, 5)]),)
        after = (component(1, [(9, 5), (10, 5)]),)
        motion = moving_component_cells(before, after)
        self.assertEqual(motion, frozenset({(9, 5), (10, 5)}))

    def test_newly_appeared_component_is_detected(self) -> None:
        before = (component(1, [(0, 0)]),)
        after = (component(1, [(0, 0)]), component(2, [(20, 20)]))
        motion = moving_component_cells(before, after)
        self.assertIn((20, 20), motion)
        self.assertNotIn((0, 0), motion)

    def test_colour_change_is_not_treated_as_the_same_object(self) -> None:
        # Ten sam kształt, inny kolor -> to nie jest ten sam obiekt.
        before = (component(1, [(5, 5)]),)
        after = (component(9, [(5, 5)]),)
        self.assertEqual(moving_component_cells(before, after), frozenset({(5, 5)}))

    def test_big_size_change_counts_as_new(self) -> None:
        before = (component(1, [(0, 0), (1, 0)]),)
        after = (component(1, [(x, 5) for x in range(12)]),)
        motion = moving_component_cells(before, after)
        self.assertTrue(motion)


if __name__ == "__main__":
    unittest.main()


class LethalClickTests(unittest.TestCase):
    """A click that killed must be demoted, not merely deprioritised."""

    def test_lethal_click_is_remembered(self) -> None:
        from agent.policy import COMPLEX_ACTION, ExplorerPolicy, Snapshot

        grid = tuple(tuple(1 for _ in range(6)) for _ in range(6))
        frame = Snapshot("PLAYING", 0, (COMPLEX_ACTION,), (grid,))
        policy = ExplorerPolicy()
        policy.choose(frame)
        pending = policy._pending
        self.assertIsNotNone(pending)
        # Symuluj: klikniecie zakonczylo sie zgonem.
        for _ in range(2):
            policy.choose(Snapshot("GAME_OVER", 0, (COMPLEX_ACTION,), (grid,)))
            policy.choose(frame)
        self.assertTrue(policy._lethal_clicks())

    def test_motion_bonus_outweighs_colour_rarity(self) -> None:
        from agent.policy import MOTION_BONUS, DEAD_CLICK_PENALTY

        self.assertGreater(MOTION_BONUS, 1000)
        self.assertGreater(DEAD_CLICK_PENALTY, 1000)
