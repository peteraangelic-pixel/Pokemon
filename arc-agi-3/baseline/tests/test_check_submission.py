"""Testy walidacji submission (bez pandas i bez sieci)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_submission import validate_rows  # noqa: E402

ATRAPA = [{"row_id": "placeholder_0", "game_id": "placeholder", "end_of_game": True, "score": 0.0}]
REAL = [
    {"row_id": "ls20_0", "game_id": "ls20", "end_of_game": True, "score": 0.42},
    {"row_id": "vc33_0", "game_id": "vc33", "end_of_game": False, "score": 0.0},
]


class ValidateRowsTest(unittest.TestCase):
    def test_atrapa_zostaje_odrzucona(self) -> None:
        problems = validate_rows(ATRAPA)
        self.assertTrue(problems)
        self.assertTrue(any("placeholder" in p for p in problems))

    def test_prawdziwy_wynik_przechodzi(self) -> None:
        self.assertEqual(validate_rows(REAL), [])

    def test_mieszane_atrapa_i_wyniki_sa_odrzucone(self) -> None:
        problems = validate_rows(REAL + ATRAPA)
        self.assertTrue(any("placeholder" in p for p in problems))

    def test_pusty_plik_jest_odrzucony(self) -> None:
        self.assertTrue(validate_rows([]))

    def test_brak_kolumny_jest_odrzucony(self) -> None:
        problems = validate_rows([{"row_id": "x", "game_id": "ls20", "score": 1.0}])
        self.assertTrue(any("end_of_game" in p for p in problems))

    def test_ujemny_lub_nan_score_jest_odrzucony(self) -> None:
        bad = [{"row_id": "a", "game_id": "ls20", "end_of_game": True, "score": -1.0}]
        self.assertTrue(validate_rows(bad))
        nan = [{"row_id": "a", "game_id": "ls20", "end_of_game": True, "score": float("nan")}]
        self.assertTrue(validate_rows(nan))


if __name__ == "__main__":
    unittest.main()
