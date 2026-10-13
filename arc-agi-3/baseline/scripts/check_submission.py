"""Sprawdza submission.parquet PRZED zgłoszeniem na Kaggle.

Powód: zgłoszenie 57075036 (11 X 2026) poszło z atrapy zapisanej w fazie
„save” notebooka (`placeholder`, score 0.0). API `kaggle competitions submit`
bierze istniejące wyjście notebooka i nie uruchamia gry. Ten skrypt blokuje
zgłoszenie, jeśli plik wygląda jak atrapa albo nie ma żadnej rozegranej gry.

Użycie:
    python scripts/check_submission.py path/to/submission.parquet

Kod wyjścia 0 = plik przechodzi, 1 = odrzucony (z listą powodów).
Sama walidacja (`validate_rows`) nie wymaga pandas; pandas jest potrzebny
tylko do wczytania pliku.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = ("row_id", "game_id", "end_of_game", "score")
PLACEHOLDER_GAME_ID = "placeholder"


def validate_rows(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Zwraca listę problemów. Pusta lista = plik przechodzi."""
    problems: list[str] = []
    rows = list(rows)
    if not rows:
        return ["plik nie ma żadnego wiersza — nie rozegrano żadnej gry"]

    columns = set().union(*(r.keys() for r in rows))
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        return [f"brak wymaganych kolumn: {', '.join(missing)}"]

    placeholder_rows = [r for r in rows if str(r.get("game_id", "")) == PLACEHOLDER_GAME_ID]
    if placeholder_rows:
        problems.append(
            f"{len(placeholder_rows)} wiersz(y) z game_id='{PLACEHOLDER_GAME_ID}' — "
            "to atrapa z fazy zapisu, nie wynik gry"
        )
    real_rows = [r for r in rows if str(r.get("game_id", "")) != PLACEHOLDER_GAME_ID]
    if not real_rows:
        problems.append("brak prawdziwych wierszy gry (wszystkie to atrapa)")

    for i, r in enumerate(real_rows):
        score = r.get("score")
        try:
            value = float(score)
        except (TypeError, ValueError):
            problems.append(f"wiersz {i}: score nie jest liczbą ({score!r})")
            continue
        if math.isnan(value) or value < 0:
            problems.append(f"wiersz {i}: score poza zakresem ({score!r})")
    return problems


def load_rows(path: Path) -> list[dict[str, Any]]:
    import pandas as pd  # import leniwy: testy nie potrzebują pandas

    frame = pd.read_parquet(path)
    return frame.to_dict(orient="records")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"ODRZUCONE: brak pliku {path}")
        return 1
    problems = validate_rows(load_rows(path))
    if problems:
        print("ODRZUCONE — nie zgłaszaj tego pliku:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {path} przechodzi walidację.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
