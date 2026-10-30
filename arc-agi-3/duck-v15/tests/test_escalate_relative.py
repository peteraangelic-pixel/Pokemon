#!/usr/bin/env python3
"""Offline tests for patch 0007's pc_escalate_at (pure threshold logic).

Runs against the patched tree the same way test_plan_commit.py does:
the file is copied into ARC3-Inference/tests/ and run with
`python -m unittest tests.test_escalate_relative` from ARC3-Inference/.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inference.utils.plan_commit import pc_escalate_at  # noqa: E402


class EscalateAtTests(unittest.TestCase):
    def test_feature_off(self):
        self.assertEqual(pc_escalate_at(0, None, 1, 0), 0)

    def test_absolute_without_baseline(self):
        self.assertEqual(pc_escalate_at(20, None, 1, 0), 20)
        self.assertEqual(pc_escalate_at(20, None, 3, 1), 40)
        self.assertEqual(pc_escalate_at(20, [], 2, 0), 20)

    def test_relative_waits_for_baseline(self):
        # human needs 300 actions: directive at 1.2x = 360, not at 20
        self.assertEqual(pc_escalate_at(20, [300], 1, 0), 360)
        self.assertEqual(pc_escalate_at(20, [300], 1, 1), 720)

    def test_relative_floor_is_absolute(self):
        # human needs 10: max(20, 12) = 20, the absolute floor rules
        self.assertEqual(pc_escalate_at(20, [10], 1, 0), 20)

    def test_level_indexing_is_one_based(self):
        self.assertEqual(pc_escalate_at(20, [0, 73], 2, 0), 87)  # int(73*1.2)
        self.assertEqual(pc_escalate_at(20, [0, 73], 1, 0), 20)  # level 1: 0 -> absolute
        self.assertEqual(pc_escalate_at(20, [0, 73], 5, 0), 20)  # out of range

    def test_per_level_cap(self):
        self.assertEqual(pc_escalate_at(20, None, 1, 2), 0)          # cap 2 reached
        self.assertEqual(pc_escalate_at(20, None, 1, 5, max_per_level=0), 120)  # 0 = unlimited
        self.assertEqual(pc_escalate_at(20, [300], 1, 1, max_per_level=1), 0)

    def test_rate_is_applied(self):
        self.assertEqual(pc_escalate_at(20, [100], 1, 0, rate=2.0), 200)
        self.assertEqual(pc_escalate_at(20, [100], 1, 0, rate=1.0), 100)


if __name__ == "__main__":
    unittest.main()
