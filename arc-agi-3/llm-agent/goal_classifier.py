"""
ARC-AGI-3 Goal Classifier - detekcja klasy gry w runtime

Inspiracja: c87f7a48-pokemon (Pokemon TCG) - FROSLASS_IDS, LOW_E_AGGRO_IDS
W Pokemon: detekcja archetypu przeciwnika w runtime, zmiana strategii
W ARC-AGI-3: detekcja klasy gry w runtime, zmiana parametrów heurystyki

Klasy gier (z GOAL_CATALOG.md):
1. COVER: pokryj wszystkie znaczniki
2. REACH: dotrzyj do wszystkich pozycji
3. COPY: skopiuj wzorzec
4. REDUCE: zostaw dokładnie 1 element
5. PLACE: umieść wszystkie obiekty w strefie
6. FLOW: wypełnij wszystkie naczynia
7. ALIGN: wyrównaj pozycje według koloru
8. LOCAL_CONSTRAINTS: każdy kafel-klucz 3×3 mówi o sąsiadach

Counter-picking: zmiana parametrów heurystyki na podstawie klasy gry
"""

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Goal Classifier - detekcja klasy gry w runtime
# ---------------------------------------------------------------------------

@dataclass
class GameFeatures:
    """Cechy gry używane do detekcji klasy."""
    
    # Pokrycie
    small_markers_count: int = 0         # Małe markery (kontury, kropki)
    outlined_positions_count: int = 0    # Wyznaczone pozycje (outlined)
    colored_edge_markers_count: int = 0  # Kolorowe markery na krawędziach
    
    # Wzorce
    pattern_in_corner: bool = False      # Wzorzec w lewym górnym rogu
    pattern_similarity: float = 0.0      # Podobieństwo do wzorca
    
    # Obiekty
    pieces_count: int = 0                # Pionki (jak w samotniku)
    empty_cells_count: int = 0           # Puste komórki
    boxes_count: int = 0                 # Skrzynki
    target_zone_detected: bool = False   # Strefa celu
    
    # Mechaniki
    dispenser_detected: bool = False     # Dozownik (FLOW)
    vessels_count: int = 0               # Naczynia
    tile_keys_3x3_count: int = 0         # Kafelki-klucze 3×3
    
    # Grid
    grid_height: int = 0
    grid_width: int = 0
    unique_colors: int = 0
    non_zero_cells: int = 0


def extract_game_features(grid: list[list[int]]) -> GameFeatures:
    """Ekstrahuj cechy z gridu do detekcji klasy gry."""
    if not grid or not grid[0]:
        return GameFeatures()
    
    height = len(grid)
    width = len(grid[0])
    
    # Podstawowe cechy gridu
    flat = [cell for row in grid for cell in row]
    unique_colors = len(set(flat))
    non_zero_cells = sum(1 for cell in flat if cell != 0)
    empty_cells = sum(1 for cell in flat if cell == 0)
    
    # Detekcja wzorca w rogu (COPY)
    # Sprawdzamy czy lewy górny róg (10×10) jest wzorcem
    # BUGFIX #1: Sprawdź czy wzorzec NIE jest pusty (0 vs 0 = fałszywe dopasowanie)
    # BUGFIX #2: Sprawdź czy wzorzec ma znaczące non-zero cells (>10%)
    # BUGFIX #3 (v7): Uniform róg (1 kolor) nie jest wzorcem - wymaga ≥2 kolorów
    pattern_in_corner = False
    pattern_similarity = 0.0
    if height >= 10 and width >= 10:
        pattern = [row[:10] for row in grid[:10]]
        pattern_flat = [cell for row in pattern for cell in row]
        pattern_non_zero = sum(1 for cell in pattern_flat if cell != 0)
        pattern_density = pattern_non_zero / 100.0
        
        # FIX BUG 1: Sprawdź liczbę kolorów we wzorcu (≥2 = realny wzorzec)
        pattern_colors = set(cell for cell in pattern_flat if cell != 0)
        has_structure = len(pattern_colors) >= 2
        
        # Tylko jeśli wzorzec jest znaczący (>10% non-zero) I ma strukturę (≥2 kolory)
        if pattern_density > 0.1 and has_structure:
            # Porównaj z resztą gridu
            max_sim = 0.0
            for r in range(0, height-9, 5):
                for c in range(0, width-9, 5):
                    if r == 0 and c == 0:
                        continue
                    matches = 0
                    total = 0
                    for pr in range(10):
                        for pc in range(10):
                            if r+pr < height and c+pc < width:
                                # BUGFIX #1: Nie licz 0 vs 0 jako dopasowanie
                                if grid[r+pr][c+pc] == pattern[pr][pc] and pattern[pr][pc] != 0:
                                    matches += 1
                                # Licz tylko non-zero cells we wzorcu
                                if pattern[pr][pc] != 0:
                                    total += 1
                    if total > 0:
                        sim = matches / total
                        max_sim = max(max_sim, sim)
            pattern_similarity = max_sim
            pattern_in_corner = max_sim > 0.7  # 70% podobieństwa = wzorzec
    
    # Detekcja małych markerów (COVER)
    # Małe markery = izolowane komórki (sąsiedzi != kolor)
    small_markers = 0
    for r in range(height):
        for c in range(width):
            if grid[r][c] == 0:
                continue
            neighbors = []
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < height and 0 <= nc < width:
                    neighbors.append(grid[nr][nc])
            # Izolowana komórka (wszyscy sąsiedzi != kolor) = mały marker
            if grid[r][c] not in neighbors:
                small_markers += 1
    
    # Detekcja wyznaczonych pozycji (REACH)
    # Outlined positions = komórki otoczone innym kolorem
    outlined_positions = 0
    for r in range(height):
        for c in range(width):
            if grid[r][c] == 0:
                continue
            # Sprawdź czy jest otoczona innym kolorem
            neighbor_colors = set()
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < height and 0 <= nc < width:
                    neighbor_colors.add(grid[nr][nc])
            if len(neighbor_colors) > 1 and grid[r][c] not in neighbor_colors:
                outlined_positions += 1
    
    # Detekcja kolorowych markerów na krawędziach (ALIGN)
    colored_edge_markers = 0
    for r in range(height):
        for c in range(width):
            if r == 0 or r == height-1 or c == 0 or c == width-1:
                if grid[r][c] != 0:
                    colored_edge_markers += 1
    
    # Detekcja skrzynek (PLACE)
    # Skrzynki = duże bloki tego samego koloru (5+ komórek)
    visited = [[False] * width for _ in range(height)]
    boxes = 0
    for r in range(height):
        for c in range(width):
            if visited[r][c] or grid[r][c] == 0:
                continue
            # BFS
            queue = [(r, c)]
            component = []
            color = grid[r][c]
            while queue:
                cr, cc = queue.pop(0)
                if visited[cr][cc] or grid[cr][cc] != color:
                    continue
                visited[cr][cc] = True
                component.append((cr, cc))
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = cr+dr, cc+dc
                    if 0 <= nr < height and 0 <= nc < width:
                        queue.append((nr, nc))
            if len(component) >= 5:  # Skrzynka = 5+ komórek
                boxes += 1
    
    # Detekcja strefy celu (PLACE)
    # Strefa celu = prostokątny obszar z innym kolorem
    target_zone = False
    # Proste heurystyki: jeśli jest duży prostokątny obszar jednego koloru
    # (implementacja uproszczona)
    if boxes > 0 and non_zero_cells > height * width * 0.5:
        target_zone = True
    
    # Detekcja dozownika (FLOW)
    # Dozownik = rząd komórek na górze (wiersz 0) z jednym kolorem
    dispenser = False
    if height > 0 and width > 0:
        top_row = grid[0]
        top_colors = set(c for c in top_row if c != 0)
        if len(top_colors) == 1 and len(top_row) > 5:
            dispenser = True
    
    # Detekcja naczyń (FLOW)
    # Naczynia = małe prostokątne obszary na dole
    vessels = 0
    if height > 5:
        bottom_rows = grid[-5:]
        for r in range(len(bottom_rows)):
            for c in range(width):
                if bottom_rows[r][c] != 0:
                    vessels += 1
        vessels = max(0, vessels // 10)  # Normalizacja
    
    # Detekcja kafelków-kluczy 3×3 (LOCAL_CONSTRAINTS)
    tile_keys = 0
    for r in range(1, height-1):
        for c in range(1, width-1):
            # Sprawdź czy jest 3×3 blok z centralną komórką
            if grid[r][c] != 0:
                is_key = True
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if grid[r+dr][c+dc] == 0:
                            is_key = False
                            break
                    if not is_key:
                        break
                if is_key:
                    tile_keys += 1
    
    # Detekcja pionków (REDUCE)
    # Pionki = małe izolowane obiekty (1-4 komórki)
    visited = [[False] * width for _ in range(height)]
    pieces = 0
    for r in range(height):
        for c in range(width):
            if visited[r][c] or grid[r][c] == 0:
                continue
            # BFS
            queue = [(r, c)]
            component = []
            color = grid[r][c]
            while queue:
                cr, cc = queue.pop(0)
                if visited[cr][cc] or grid[cr][cc] != color:
                    continue
                visited[cr][cc] = True
                component.append((cr, cc))
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = cr+dr, cc+dc
                    if 0 <= nr < height and 0 <= nc < width:
                        queue.append((nr, nc))
            if 1 <= len(component) <= 4:  # Pionek = 1-4 komórki
                pieces += 1
    
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


def detect_goal_class(grid: list[list[int]]) -> str:
    """Detekcja klasy gry na podstawie wizualnych cech.
    
    Returns:
        COVER, COPY, REACH, REDUCE, PLACE, FLOW, ALIGN, LOCAL_CONSTRAINTS, UNKNOWN
    """
    features = extract_game_features(grid)
    
    # FIX BUG 1: Zmień kolejność reguł
    # Najbardziej specyficzne: pattern (COPY) i mechanika (FLOW) przed strukturą (LOCAL_CONSTRAINTS)
    # Powtarzalny wzorzec 10×10 lub dozownik+naczynia to mocniejsze dowody niż gęstość bloków 3×3
    if features.pattern_in_corner:
        return "COPY"
    
    if features.dispenser_detected and features.vessels_count > 2:
        return "FLOW"
    
    # Po FLOW, przed resztą
    if features.tile_keys_3x3_count > 3:
        return "LOCAL_CONSTRAINTS"
    
    if features.boxes_count > 2 and features.target_zone_detected:
        return "PLACE"
    
    if features.pieces_count > 20 and features.empty_cells_count > features.pieces_count:
        return "REDUCE"
    
    if features.colored_edge_markers_count > 5:
        return "ALIGN"
    
    if features.outlined_positions_count > 5:
        return "REACH"
    
    if features.small_markers_count > 10:
        return "COVER"
    
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Counter-picking - zmiana parametrów heurystyki na podstawie klasy gry
# ---------------------------------------------------------------------------

@dataclass
class StrategyParams:
    """Parametry strategii dla danej klasy gry."""
    
    explore_weight: float = 1.0
    exploit_weight: float = 2.0
    noop_penalty: float = -1.0
    level_progress_weight: float = 5.0
    affordance_weight: float = 1.5
    pattern_weight: float = 2.0
    stuck_threshold: int = 40
    temp_base: float = 0.6
    batch_size: int = 4


# Counter-picking na poziomie promptu (jak druga gałąź v6.9)
STRATEGY_HINTS = {
    "COVER": "Focus on finding and covering ALL small markers (dots, outlines). Click on each marker once.",
    "COPY": "Find the pattern in the top-left corner. Replicate it exactly in the target area. Don't click the pattern itself.",
    "REACH": "Navigate avatar(s) to all outlined goal positions. Watch for obstacles and traps.",
    "REDUCE": "Jump pieces over each other (like checkers). Goal: leave exactly 1 piece remaining.",
    "PLACE": "Push all boxes into the target zone. Boxes must be RELEASED in the zone (not held).",
    "FLOW": "Set up the configuration FIRST, then CONFIRM (action 5). Limited attempts - don't waste them.",
    "ALIGN": "Align colored markers to match target positions by color. Click markers to move them.",
    "LOCAL_CONSTRAINTS": "Each 3×3 tile-key shows constraints for neighbors. Click to change colors cyclically.",
    "UNKNOWN": "Explore systematically. Test different actions to understand the mechanics. Take notes.",
}


def get_strategy_for_goal_class(goal_class: str) -> StrategyParams:
    """Zwróć parametry strategii dla danej klasy gry.
    
    Inspiracja: c87f7a48-pokemon - FROSLASS counter, LOW_E_AGGRO counter
    """
    strategies = {
        "COVER": StrategyParams(
            explore_weight=1.5,
            exploit_weight=1.8,
            affordance_weight=2.5,  # Klikaj na markery
            stuck_threshold=35,
        ),
        "COPY": StrategyParams(
            explore_weight=0.8,
            exploit_weight=2.2,
            pattern_weight=3.5,  # Priorytet: kopiuj wzorzec
            stuck_threshold=50,  # Więcej czasu na zrozumienie wzorca
        ),
        "REACH": StrategyParams(
            explore_weight=1.3,
            exploit_weight=2.0,
            level_progress_weight=3.0,
            stuck_threshold=40,
        ),
        "REDUCE": StrategyParams(
            explore_weight=1.0,
            exploit_weight=2.8,  # Priorytet: skoki
            noop_penalty=-2.0,  # Kara za brak ruchu
            stuck_threshold=30,
        ),
        "PLACE": StrategyParams(
            explore_weight=1.2,
            exploit_weight=2.3,
            affordance_weight=2.2,  # Klikaj na skrzynki
            stuck_threshold=45,
        ),
        "FLOW": StrategyParams(
            explore_weight=1.0,
            exploit_weight=2.0,
            pattern_weight=3.0,  # Priorytet: wzorzec przepływu
            stuck_threshold=30,  # Mniej czasu (ograniczone próby)
        ),
        "ALIGN": StrategyParams(
            explore_weight=1.4,
            exploit_weight=1.9,
            affordance_weight=2.4,  # Klikaj na markery
            stuck_threshold=40,
        ),
        "LOCAL_CONSTRAINTS": StrategyParams(
            explore_weight=1.1,
            exploit_weight=2.1,
            affordance_weight=2.6,  # Klikaj na kafelki-klucze
            noop_penalty=-1.5,
            stuck_threshold=35,
        ),
        "UNKNOWN": StrategyParams(
            explore_weight=1.0,
            exploit_weight=2.0,
            stuck_threshold=40,
        ),
    }
    
    return strategies.get(goal_class, strategies["UNKNOWN"])


def get_strategy_hint(goal_class: str) -> str:
    """Zwróć hint taktyczny dla danej klasy gry (do wstrzyknięcia w prompt)."""
    return STRATEGY_HINTS.get(goal_class, STRATEGY_HINTS["UNKNOWN"])


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test
    grid = [
        [0, 1, 1, 0, 0],
        [1, 2, 2, 1, 0],
        [1, 2, 2, 1, 0],
        [0, 1, 1, 0, 0],
    ]
    
    features = extract_game_features(grid)
    goal_class = detect_goal_class(grid)
    strategy = get_strategy_for_goal_class(goal_class)
    
    print(f"Grid: {grid}")
    print(f"Features: {features}")
    print(f"Detected goal class: {goal_class}")
    print(f"Strategy: {strategy}")
