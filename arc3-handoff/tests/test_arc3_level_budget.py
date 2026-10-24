"""Testy jednostkowe patcha 0004 (arc3_level_budget) + dowód dwóch bugów 0003.

Offline: bez harnessa, bez GPU, bez arcengine, bez slota Kaggle.
Uruchomienie:  python3 -m pytest -q tests/test_arc3_level_budget.py
           albo: python3 tests/test_arc3_level_budget.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

FRAMEWORK = Path(__file__).resolve().parent.parent / "ARC3-Inference" / "inference" / "framework"
sys.path.insert(0, str(FRAMEWORK))

import arc3_level_budget as lb  # noqa: E402

try:                      # wariant standalone nie zawiera patcha 0003
    import arc3_abandon as ab  # noqa: E402
except ModuleNotFoundError:
    ab = None


class TestDefaultOff(unittest.TestCase):
    """Kill-switch: bez enva zachowanie MUSI być identyczne ze stockowym."""

    def test_cap_zero_never_acts(self):
        t = lb.LevelBudget(level_token_cap=0)
        self.assertFalse(t.enabled)
        for tokens in (0, 60_000, 500_000, 10_000_000):
            for levels in (0, 1, 5):
                self.assertEqual(t.peek(tokens, levels), lb.KEEP_GOING, (tokens, levels))
                self.assertEqual(t.step(tokens, levels), lb.KEEP_GOING, (tokens, levels))

    def test_from_env_reads_nothing_when_unset(self):
        for k in ("ARC3_LEVEL_TOKEN_CAP", "ARC3_LEVEL_RESETS_MAX", "ARC3_LEVEL_MIN_DONE"):
            os.environ.pop(k, None)
        t = lb.LevelBudget.from_env()
        self.assertEqual(t.cap, 0)
        self.assertEqual(t.max_resets, lb.DEFAULT_RESETS_MAX)
        self.assertFalse(t.enabled)

    def test_from_env_parses_values(self):
        os.environ["ARC3_LEVEL_TOKEN_CAP"] = "45000"
        os.environ["ARC3_LEVEL_RESETS_MAX"] = "2"
        os.environ["ARC3_LEVEL_MIN_DONE"] = "1"
        try:
            t = lb.LevelBudget.from_env()
            self.assertEqual((t.cap, t.max_resets, t.min_done), (45000, 2, 1))
            self.assertTrue(t.enabled)
        finally:
            for k in ("ARC3_LEVEL_TOKEN_CAP", "ARC3_LEVEL_RESETS_MAX", "ARC3_LEVEL_MIN_DONE"):
                os.environ.pop(k, None)

    def test_garbage_env_falls_back_to_default(self):
        os.environ["ARC3_LEVEL_TOKEN_CAP"] = "nie-liczba"
        try:
            self.assertEqual(lb.LevelBudget.from_env().cap, 0)
        finally:
            os.environ.pop("ARC3_LEVEL_TOKEN_CAP", None)


class TestDecisionSequence(unittest.TestCase):
    """Scenariusz z r019: tn36 robi poziom 0 tanio, potem miele poziom 1."""

    def test_reset_then_abandon(self):
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=1)
        self.assertEqual(t.step(10_000, 0), lb.KEEP_GOING)     # poziom 0 w budzecie
        self.assertEqual(t.step(50_000, 1), lb.KEEP_GOING)     # poziom 0 zrobiony -> swiezy budzet
        self.assertEqual(t.level_start_tokens, 50_000)
        self.assertEqual(t.resets_used, 0)
        self.assertEqual(t.step(80_000, 1), lb.KEEP_GOING)     # 30k na poziomie 1
        self.assertEqual(t.step(95_000, 1), lb.RESET_LEVEL)    # 45k -> darmowy RESET
        self.assertEqual(t.resets_used, 1)
        self.assertEqual(t.step(120_000, 1), lb.KEEP_GOING)    # 25k po resecie
        self.assertEqual(t.step(140_000, 1), lb.ABANDON)       # 45k po resecie, resetow brak
        self.assertEqual(t.peek(140_000, 1), lb.ABANDON)

    def test_progress_after_reset_cancels_abandon(self):
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=1)
        t.step(50_000, 1)
        self.assertEqual(t.step(95_000, 1), lb.RESET_LEVEL)
        self.assertEqual(t.step(130_000, 2), lb.KEEP_GOING)    # reset zadzialal: poziom 2 zrobiony
        self.assertEqual(t.resets_used, 0)                     # licznik resetow odnowiony
        self.assertEqual(t.level_start_tokens, 130_000)
        self.assertEqual(t.peek(150_000, 2), lb.KEEP_GOING)    # 20k na nowym poziomie
        self.assertEqual(t.peek(174_999, 2), lb.KEEP_GOING)    # 130k+45k jeszcze nie
        # po przekroczeniu cap na nowym poziomie znów przysluguje darmowy reset
        self.assertEqual(t.peek(999_000, 2), lb.RESET_LEVEL)
        self.assertEqual(t.resets_used, 0, "peek musi byc czysty")

    def test_peek_is_pure_under_repeated_calls(self):
        """should_stop() jest callbackiem analyzera - bywa wywolany wiele razy na ture.
        Czysty peek NIE moze zuzyc resetow."""
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=1)
        t.step(50_000, 1)
        for _ in range(50):
            self.assertEqual(t.peek(95_000, 1), lb.RESET_LEVEL)
        self.assertEqual(t.resets_used, 0, "peek zuzyl reset - powinien byc czysty")
        self.assertEqual(t.step(95_000, 1), lb.RESET_LEVEL)
        self.assertEqual(t.resets_used, 1)

    def test_peek_never_abandons_on_the_turn_a_level_completes(self):
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=0)
        t.step(0, 0)
        # step jeszcze nie widzial postepu, ale peek musi go uszanowac
        self.assertEqual(t.peek(500_000, 1), lb.KEEP_GOING)
        self.assertEqual(t.peek(500_000, 0), lb.ABANDON)

    def test_min_done_protects_early_games(self):
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=0, min_done_levels=1)
        self.assertEqual(t.peek(999_000, 0), lb.KEEP_GOING)    # 0 poziomow -> chroniona
        # zeby testowac prog, tracker musi najpierw zobaczyc ukończony poziom
        t.step(50_000, 1)
        self.assertEqual(t.peek(999_000, 1), lb.ABANDON)       # 1 poziom >= min_done -> mozna porzucic
        t2 = lb.LevelBudget(level_token_cap=45_000, resets_max=0, min_done_levels=3)
        t2.step(50_000, 1)
        self.assertEqual(t2.peek(999_000, 1), lb.KEEP_GOING)   # 1 < 3 -> chroniona
        t2.step(60_000, 3)
        self.assertEqual(t2.peek(999_000, 3), lb.ABANDON)

    def test_zero_resets_means_immediate_abandon(self):
        t = lb.LevelBudget(level_token_cap=60_000, resets_max=0)
        self.assertEqual(t.step(60_000, 0), lb.ABANDON)

    def test_budget_is_marginal_not_cumulative(self):
        """Kluczowa roznica vs 0003: liczy sie wydatek na BIEZACY poziom.
        Gra, ktora robi poziomy tanio, nigdy nie wpada w cap mimo 400k tokenow lacznie."""
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=1)
        tokens = 0
        for level in range(1, 9):
            tokens += 30_000                    # 30k na poziom = ponizej cap
            self.assertEqual(t.step(tokens, level), lb.KEEP_GOING, f"level {level}")
        self.assertEqual(tokens, 240_000)


@unittest.skipIf(ab is None, "arc3_abandon nieobecny (wariant 0004-standalone)")
class TestPatch0003Bugs(unittest.TestCase):
    """Udokumentowane bugi v7-abandon (patch 0003) - dlatego potrzebny jest 0004."""

    def test_bug1_games_with_any_progress_are_never_abandoned(self):
        for k in ("ARC3_ABANDON_TOKENS", "ARC3_ABANDON_MIN_LEVELS"):
            os.environ.pop(k, None)
        os.environ["ARC3_ABANDON_TOKENS"] = "60000"
        os.environ["ARC3_ABANDON_MIN_LEVELS"] = "0"
        try:
            # tn36 z r019: 1 poziom zrobiony, 86% tokenow (≈170k) na niedokonczonym poziomie
            self.assertFalse(ab.should_abandon(170_000, 1),
                             "0003 chroni dokladnie te gry, ktore najwiecej marnuja")
            self.assertTrue(ab.should_abandon(170_000, 0))
        finally:
            for k in ("ARC3_ABANDON_TOKENS", "ARC3_ABANDON_MIN_LEVELS"):
                os.environ.pop(k, None)

    def test_bug2_per_step_cursor_can_never_reach_the_cap(self):
        """solver.py przekazuje `analyzer_tokens - token_baseline`, a token_baseline
        jest przesuwany po KAŻDEJ akcji (komentarz w solver.py: 'it is a cursor').
        Przy LOCAL_ANALYZER_MAX_OUTPUT=12k jeden krok nigdy nie da 60k."""
        os.environ["ARC3_ABANDON_TOKENS"] = "60000"
        try:
            per_step_tokens = 12 * 1024          # MAX_OUTPUT z cell 9
            self.assertFalse(ab.should_abandon(per_step_tokens, 0))
            self.assertFalse(ab.should_abandon(841, 0))   # srednia z r019: 841 tok/akcje
        finally:
            os.environ.pop("ARC3_ABANDON_TOKENS", None)


class TestCatchesTheLeak0003Missed(unittest.TestCase):
    """Ten sam wyciek, ktory 0003 przepuszcza - obsluzony przez 0004."""

    def test_0004_catches_the_same_leak(self):
        t = lb.LevelBudget(level_token_cap=45_000, resets_max=1)
        t.step(20_000, 1)                        # poziom 0 zrobiony za 20k
        self.assertEqual(t.step(190_000, 1), lb.RESET_LEVEL)   # 170k na poziomie 1 -> reset
        self.assertEqual(t.step(240_000, 1), lb.ABANDON)       # i dopiero potem porzucenie


class TestHarnessCallShape(unittest.TestCase):
    """Symulacja wywolan dokladnie tak, jak robi to solver.py po patchu 0004."""

    class FakeState:
        def __init__(self, levels): self.levels_completed = levels

    class FakeGame:
        def __init__(self): self.current_state = TestHarnessCallShape.FakeState(0)

    class FakeSession:
        """game_token_baseline = tokeny analyzera na starcie gry (jak w play())."""
        def __init__(self, cap):
            self.game = TestHarnessCallShape.FakeGame()
            self.game_token_baseline = 1_000
            self.analyzer_tokens = 1_000
            self._arc3_level_budget = lb.LevelBudget(level_token_cap=cap, resets_max=1)
            self.resets_executed = 0
            self.stopped = False

        def turn(self, generated: int, levels: int):
            self.analyzer_tokens = self.game_token_baseline + generated
            self.game.current_state.levels_completed = levels
            spent = self.analyzer_tokens - self.game_token_baseline
            # should_stop() - peek, wywolany kilka razy (callback analyzera)
            for _ in range(3):
                if self._arc3_level_budget.peek(spent, levels) == lb.ABANDON:
                    self.stopped = True
            if self.stopped:
                return "stopped"
            d = self._arc3_level_budget.step(spent, levels)
            if d == lb.RESET_LEVEL:
                self.resets_executed += 1
                return "reset"
            if d == lb.ABANDON:
                self.stopped = True
                return "stopped"
            return "play"

    def test_full_game_trajectory(self):
        s = self.FakeSession(cap=45_000)
        seq = [s.turn(t, lv) for t, lv in [
            (10_000, 0), (20_000, 1), (40_000, 1), (60_000, 1),   # 40k na poziomie 1
            (70_000, 1),                                           # 50k -> RESET
            (90_000, 1), (115_000, 1),                             # 45k po resecie -> ABANDON
            (200_000, 1),
        ]]
        self.assertEqual(seq[:5], ["play", "play", "play", "play", "reset"])
        self.assertEqual(seq[6], "stopped")
        self.assertEqual(s.resets_executed, 1)
        self.assertTrue(all(x == "stopped" for x in seq[6:]), "po ABANDON gra stoi na dobre")

    def test_disabled_session_plays_forever(self):
        s = self.FakeSession(cap=0)
        for tokens in range(0, 1_000_000, 25_000):
            self.assertEqual(s.turn(tokens, 0), "play")
        self.assertEqual(s.resets_executed, 0)
        self.assertFalse(s.stopped)


if __name__ == "__main__":
    unittest.main(verbosity=2)
