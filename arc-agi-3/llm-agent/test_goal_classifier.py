"""
Testy dla goal_classifier.py

Inspiracja: druga gałąź (98ddb59f-pokemon) - 104/104 testów w v6.9
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goal_classifier import detect_goal_class, extract_game_features, get_strategy_for_goal_class, get_strategy_hint


class TestGoalClassifier(unittest.TestCase):
    """Testy detekcji klasy gry."""
    
    def test_empty_grid(self):
        """Pusta plansza → UNKNOWN."""
        grid = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        self.assertEqual(detect_goal_class(grid), "UNKNOWN")
    
    def test_sparse_grid_no_false_copy(self):
        """Rzadka plansza (więcej zera) → nie fałszywe COPY."""
        grid = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        result = detect_goal_class(grid)
        self.assertNotEqual(result, "COPY")
    
    def test_empty_pattern_in_corner(self):
        """Pusty wzorzec w rogu (wszystkie zera) → nie COPY."""
        grid = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ]
        result = detect_goal_class(grid)
        self.assertNotEqual(result, "COPY")
    
    def test_reduce_threshold_20(self):
        """REDUCE wymaga >20 pionków (nie 10)."""
        grid = [[0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0]]
        result = detect_goal_class(grid)
        self.assertNotEqual(result, "REDUCE")  # 12 pionków < 20
    
    def test_cover_with_small_markers(self):
        """COVER z małymi markerami."""
        grid = [[0, 1, 0, 1, 0], [1, 0, 0, 0, 1], [0, 0, 2, 0, 0], [1, 0, 0, 0, 1], [0, 1, 0, 1, 0]]
        result = detect_goal_class(grid)
        # Powinno wykryć COVER lub UNKNOWN (nie COPY/REDUCE)
        self.assertIn(result, ["COVER", "UNKNOWN", "ALIGN"])
    
    def test_random_grids_no_false_copy(self):
        """200 losowych plansz → 0 fałszywych COPY."""
        import random
        random.seed(42)
        false_copies = 0
        for _ in range(200):
            height = random.randint(3, 20)
            width = random.randint(3, 20)
            grid = [[random.choice([0, 0, 0, 1, 2]) for _ in range(width)] for _ in range(height)]
            result = detect_goal_class(grid)
            if result == "COPY":
                false_copies += 1
        self.assertEqual(false_copies, 0, f"Fałszywe COPY: {false_copies}/200")


class TestGameFeatures(unittest.TestCase):
    """Testy ekstrakcji cech."""
    
    def test_empty_grid_features(self):
        """Pusta plansza → wszystkie cechy 0."""
        grid = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        features = extract_game_features(grid)
        self.assertEqual(features.grid_height, 3)
        self.assertEqual(features.grid_width, 3)
        self.assertEqual(features.non_zero_cells, 0)
        self.assertEqual(features.unique_colors, 1)  # Tylko 0
    
    def test_non_empty_grid_features(self):
        """Niepusta plansza → poprawne cechy."""
        grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        features = extract_game_features(grid)
        self.assertEqual(features.grid_height, 3)
        self.assertEqual(features.grid_width, 3)
        self.assertEqual(features.non_zero_cells, 9)
        self.assertEqual(features.unique_colors, 9)  # 1-9 (0 nie występuje)


class TestStrategyForGoalClass(unittest.TestCase):
    """Testy counter-picking."""
    
    def test_all_goal_classes_have_strategy(self):
        """Wszystkie klasy gier mają strategię."""
        goal_classes = ["COVER", "REACH", "COPY", "REDUCE", "PLACE", "FLOW", "ALIGN", "LOCAL_CONSTRAINTS", "UNKNOWN"]
        for goal_class in goal_classes:
            strategy = get_strategy_for_goal_class(goal_class)
            self.assertIsNotNone(strategy)
            self.assertGreater(strategy.explore_weight, 0)
            self.assertGreater(strategy.exploit_weight, 0)
    
    def test_copy_strategy_high_pattern_weight(self):
        """COPY ma wysoką wagę pattern_weight."""
        strategy = get_strategy_for_goal_class("COPY")
        self.assertGreater(strategy.pattern_weight, 2.5)
    
    def test_reduce_strategy_high_exploit_weight(self):
        """REDUCE ma wysoką wagę exploit_weight."""
        strategy = get_strategy_for_goal_class("REDUCE")
        self.assertGreater(strategy.exploit_weight, 2.5)
    
    def test_all_goal_classes_have_hint(self):
        """Wszystkie klasy gier mają strategy hint."""
        goal_classes = ["COVER", "REACH", "COPY", "REDUCE", "PLACE", "FLOW", "ALIGN", "LOCAL_CONSTRAINTS", "UNKNOWN"]
        for goal_class in goal_classes:
            hint = get_strategy_hint(goal_class)
            self.assertIsNotNone(hint)
            self.assertGreater(len(hint), 10)
    
    def test_copy_hint_mentions_pattern(self):
        """COPY hint wspomina o pattern."""
        hint = get_strategy_hint("COPY")
        self.assertIn("pattern", hint.lower())


if __name__ == "__main__":
    unittest.main()
