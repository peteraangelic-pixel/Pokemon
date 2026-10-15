"""v6.9: Runtime goal-class detection (counter-picking) — port z ich v7.0
(Pokemon/arena/7911f950-pokemon @3ad6a47, goal_classifier.py), z poprawkami.

Klasy (taxonomia GOAL_CATALOG/FIELD GUIDE):
COVER, REACH, COPY, REDUCE, PLACE, FLOW, ALIGN, LOCAL_CONSTRAINTS, UNKNOWN.

Różnice vs ich wersja (uczciwie):
1. BUGFIX: pusta/tło-only plansza dawała u nich COPY (wzorzec 10×10 z zerów
   „pokrywał" inne zerowe okna z similarity 1.0). U nas: early-return UNKNOWN
   dla pustych plansz + wzorzec narożnika musi mieć ≥4 komórki ≠ 0.
2. BUGFIX: metadata gridu liczona z list[list[int]] — u nas przyjmujemy też
   tuple[tuple[int, ...], ...] (Format FrameInfo.grid), normalizacja na wejściu.
3. NIE portujemy StrategyParams (wagi heurystyki do counter-pickingu) — u nich
   to martwy kod (nikt nie importuje), u nas heurystycznych wag nie ma; nasz
   counter-picking działa na poziomie promptu: STRATEGY_HINTS poniżej.
"""

from __future__ import annotations

from dataclasses import dataclass


GOAL_CLASSES = (
    "COVER", "REACH", "COPY", "REDUCE", "PLACE", "FLOW", "ALIGN",
    "LOCAL_CONSTRAINTS", "UNKNOWN",
)


@dataclass
class GameFeatures:
    """Cechy planszy używane do detekcji klasy."""
    # Pokrycie
    small_markers_count: int = 0         # Izolowane komórki (małe markery)
    outlined_positions_count: int = 0    # Komórki „obrysowane" innym kolorem
    colored_edge_markers_count: int = 0  # Niezerowe komórki na krawędzi
    # Wzorce
    pattern_in_corner: bool = False      # Powtarzalny wzorzec 10×10 z rogu
    pattern_similarity: float = 0.0
    # Obiekty
    pieces_count: int = 0                # Małe obiekty (1–4 komórki)
    empty_cells_count: int = 0
    boxes_count: int = 0                 # Duże obiekty (≥5 komórek)
    target_zone_detected: bool = False
    # Mechaniki
    dispenser_detected: bool = False     # Jednolity niezerowy wiersz 0 (FLOW)
    vessels_count: int = 0
    tile_keys_3x3_count: int = 0         # Gęste bloki 3×3 (LOCAL_CONSTRAINTS)
    # Grid
    grid_height: int = 0
    grid_width: int = 0
    unique_colors: int = 0
    non_zero_cells: int = 0


def extract_game_features(grid) -> GameFeatures:
    """Ekstrakcja cech z gridu (listy lub krotki wierszy; 0 = tło)."""
    rows = [list(r) for r in grid]
    if not rows or not rows[0]:
        return GameFeatures()
    height = len(rows)
    width = len(rows[0])

    flat = [cell for row in rows for cell in row]
    unique_colors = len(set(flat))
    non_zero_cells = sum(1 for cell in flat if cell != 0)
    empty_cells = sum(1 for cell in flat if cell == 0)

    # Wzorzec w rogu (COPY): lewy górny 10×10 vs inne okna 10×10 (krok 5).
    # BUGFIX #3 vs ich wersja: oni liczyli też dopasowania zero-vs-zero, więc
    # na rzadkich planszach niemal wszystko dawało similarity ~0.9+ → fałszywe
    # COPY. U nas score liczy WYŁĄCZNIE strukturę niezerową (trafienia w
    # niezerowe komórki wzorca / (trafienia + nadmiarowe niezerowe okna)).
    pattern_in_corner = False
    pattern_similarity = 0.0
    if height >= 10 and width >= 10:
        pattern = [row[:10] for row in rows[:10]]
        pat_nz = [(r, c) for r in range(10) for c in range(10) if pattern[r][c] != 0]
        pat_colors = {pattern[r][c] for (r, c) in pat_nz}
        # BUGFIX #5 (15.10, lekcja z ich v7.0): uniform róg (1 kolor) „pasuje"
        # do innych uniform okien → fałszywe COPY na planszach FLOW/pełnych.
        # Prawdziwy powtarzalny wzorzec ma strukturę: >=2 kolory.
        if len(pat_nz) >= 4 and len(pat_colors) >= 2:
            best = 0.0
            for r in range(0, height - 9, 5):
                for c in range(0, width - 9, 5):
                    if r == 0 and c == 0:
                        continue
                    window_nz = sum(
                        1 for rr in range(10) for cc in range(10)
                        if r + rr < height and c + cc < width
                        and rows[r + rr][c + cc] != 0)
                    matches = sum(
                        1 for (rr, cc) in pat_nz
                        if r + rr < height and c + cc < width
                        and rows[r + rr][c + cc] == pattern[rr][cc])
                    extra = max(0, window_nz - matches)
                    score = matches / (matches + extra) if (matches + extra) else 0.0
                    best = max(best, score)
            pattern_similarity = best
            pattern_in_corner = best > 0.7

    # Małe markery (COVER): komórka, której 4-sąsiedzi nie mają jej koloru.
    small_markers = 0
    for r in range(height):
        for c in range(width):
            if rows[r][c] == 0:
                continue
            neighbors = []
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < height and 0 <= nc < width:
                    neighbors.append(rows[nr][nc])
            if rows[r][c] not in neighbors:
                small_markers += 1

    # Obrysowane pozycje (REACH): komórka ≠ 0, wokół ≥2 różne kolory, w tym
    # żaden równy jej kolorowi.
    outlined_positions = 0
    for r in range(height):
        for c in range(width):
            if rows[r][c] == 0:
                continue
            neighbor_colors = set()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < height and 0 <= nc < width:
                    neighbor_colors.add(rows[nr][nc])
            if len(neighbor_colors) > 1 and rows[r][c] not in neighbor_colors:
                outlined_positions += 1

    # Krawędziowe markery (ALIGN)
    colored_edge_markers = 0
    for r in range(height):
        for c in range(width):
            if r in (0, height - 1) or c in (0, width - 1):
                if rows[r][c] != 0:
                    colored_edge_markers += 1

    def _components(min_size: int, max_size: int | None) -> int:
        """Licz spójnych obszarów tego samego koloru o rozmiarze w granicach."""
        seen = [[False] * width for _ in range(height)]
        count = 0
        for r in range(height):
            for c in range(width):
                if seen[r][c] or rows[r][c] == 0:
                    continue
                queue = [(r, c)]
                size = 0
                color = rows[r][c]
                while queue:
                    cr, cc = queue.pop()
                    if cr < 0 or cc < 0 or cr >= height or cc >= width:
                        continue
                    if seen[cr][cc] or rows[cr][cc] != color:
                        continue
                    seen[cr][cc] = True
                    size += 1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        queue.append((cr + dr, cc + dc))
                if size >= min_size and (max_size is None or size <= max_size):
                    count += 1
        return count

    boxes = _components(5, None)          # Skrzynki (PLACE): duże obszary
    pieces = _components(1, 4)            # Pionki (REDUCE): małe obiekty

    # Strefa celu (PLACE, uproszczone): gęsta plansza z dużymi obiektami.
    target_zone = boxes > 0 and non_zero_cells > height * width * 0.5

    # Dozownik (FLOW): wiersz 0 jednolity niezerowy (szerokość > 5).
    dispenser = False
    top_colors = {c for c in rows[0] if c != 0}
    if len(top_colors) == 1 and width > 5:
        dispenser = True

    # Naczynia (FLOW, uproszczone): niezerowe komórki w 5 dolnych wierszach.
    vessels = 0
    if height > 5:
        bottom_nonzero = sum(1 for row in rows[-5:] for cell in row if cell != 0)
        vessels = max(0, bottom_nonzero // 10)

    # Kafelki-klucze 3×3 (LOCAL_CONSTRAINTS): środki w pełni niezerowych 3×3.
    tile_keys = 0
    for r in range(1, height - 1):
        for c in range(1, width - 1):
            if rows[r][c] == 0:
                continue
            dense = True
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if rows[r + dr][c + dc] == 0:
                        dense = False
                        break
                if not dense:
                    break
            if dense:
                tile_keys += 1

    return GameFeatures(
        small_markers_count=small_markers,
        outlined_positions_count=outlined_positions,
        colored_edge_markers_count=colored_edge_markers,
        pattern_in_corner=pattern_in_corner,
        pattern_similarity=pattern_similarity,
        pieces_count=pieces,
        empty_cells_count=empty_cells,
        boxes_count=boxes,
        target_zone_detected=target_zone,
        dispenser_detected=dispenser,
        vessels_count=vessels,
        tile_keys_3x3_count=tile_keys,
        grid_height=height,
        grid_width=width,
        unique_colors=unique_colors,
        non_zero_cells=non_zero_cells,
    )


def detect_goal_class(grid) -> str:
    """Detekcja klasy gry z pierwszej planszy. Zwraca element GOAL_CLASSES."""
    rows = [list(r) for r in grid]
    if not rows or not rows[0]:
        return "UNKNOWN"
    features = extract_game_features(rows)
    # BUGFIX vs ich wersja: pusta/tło-only plansza → UNKNOWN (u nich dawała
    # fałszywe COPY przez „wzorzec" z samych zer).
    if features.non_zero_cells == 0:
        return "UNKNOWN"
    # Priorytet: od najbardziej specyficznych. Lekcje z ich v7.0 (15.10):
    # (a) gęsty wzorzec COPY ma pełne bloki 3×3 → LOCAL_CONSTRAINTS (tile_keys>3)
    # muszą czekać na COPY; (b) uniform plansza z dozownikiem ma „gęsty róg",
    # ale wzorzec bez >=2 kolorów nie liczy się (BUGFIX #5) — FLOW z konkretnym
    # dozownikiem+naczyniami rozstrzygamy najpierw.
    if features.dispenser_detected and features.vessels_count > 2:
        return "FLOW"
    if features.pattern_in_corner:
        return "COPY"
    if features.tile_keys_3x3_count > 3:
        return "LOCAL_CONSTRAINTS"
    if features.boxes_count > 2 and features.target_zone_detected:
        return "PLACE"
    # BUGFIX #4 vs ich wersja: próg 20 zamiast 10 — u nich izolowane markery
    # COVER (1-komórkowe = „pionki") wygrywały REDUCE przez kolejność reguł.
    if features.pieces_count > 20 and features.empty_cells_count > features.pieces_count:
        return "REDUCE"
    if features.colored_edge_markers_count > 5:
        return "ALIGN"
    if features.outlined_positions_count > 5:
        return "REACH"
    if features.small_markers_count > 10:
        return "COVER"
    return "UNKNOWN"


# Nasz counter-picking: poziom promptu (hint taktyczny per klasa), zamiast ich
# StrategyParams (wagi heurystyki — u nas martwy kod, nie mamy takich wag).
STRATEGY_HINTS: dict[str, str] = {
    "COVER": "small markers likely must ALL be covered/activated — count them, "
             "verify each interaction changes exactly one marker",
    "REACH": "outlined positions likely must ALL be visited — plan the shortest "
             "route and confirm each visit registers",
    "COPY": "a pattern repeats on the board — reproduce it elsewhere (translation "
            "or completion), compare cell-by-cell",
    "REDUCE": "many small pieces must be reduced to few/one — find the removal "
              "rule on a single piece first",
    "PLACE": "large objects belong into a zone — move one object fully first to "
             "learn the placement rule",
    "FLOW": "a dispenser/source feeds vessels — trace the flow path before "
            "touching anything",
    "ALIGN": "edge-colored markers suggest ordering/alignment — test whether "
             "order matters by aligning two markers first",
    "LOCAL_CONSTRAINTS": "dense 3×3 blocks hint at local-neighborhood rules — "
                         "change one cell and observe which neighbors react",
}
