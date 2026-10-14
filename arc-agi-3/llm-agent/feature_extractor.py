"""
ARC-AGI-3 Feature Extractor (na podstawie c87f7a48-pokemon)

Ekstrahuje 20 cech z stanu gry ARC-AGI-3 do trenowania MLP value model.
"""

import numpy as np
from typing import Any


def count_connected_components(grid: list[list[int]]) -> int:
    """Count connected components of non-zero cells."""
    if not grid or not grid[0]:
        return 0
    
    height = len(grid)
    width = len(grid[0])
    visited = [[False] * width for _ in range(height)]
    
    def dfs(r, c, color):
        if r < 0 or r >= height or c < 0 or c >= width:
            return
        if visited[r][c] or grid[r][c] != color:
            return
        visited[r][c] = True
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            dfs(r+dr, c+dc, color)
    
    components = 0
    for r in range(height):
        for c in range(width):
            if not visited[r][c] and grid[r][c] != 0:
                dfs(r, c, grid[r][c])
                components += 1
    
    return components


def count_affordances(grid: list[list[int]]) -> int:
    """Count clickable objects (contours, dots, markers)."""
    if not grid or not grid[0]:
        return 0
    
    height = len(grid)
    width = len(grid[0])
    affordances = 0
    
    # Look for isolated cells (potential click targets)
    for r in range(height):
        for c in range(width):
            if grid[r][c] == 0:
                continue
            # Count neighbors
            neighbors = 0
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < height and 0 <= nc < width and grid[nr][nc] == grid[r][c]:
                    neighbors += 1
            # Isolated cell = affordance
            if neighbors == 0:
                affordances += 1
    
    return affordances


def compute_symmetry(grid: list[list[int]]) -> float:
    """Compute horizontal symmetry score (0-1)."""
    if not grid or not grid[0]:
        return 0.0
    
    height = len(grid)
    width = len(grid[0])
    mid = width // 2
    
    matches = 0
    total = 0
    
    for r in range(height):
        for c in range(mid):
            mirror_c = width - 1 - c
            if grid[r][c] == grid[r][mirror_c]:
                matches += 1
            total += 1
    
    return matches / max(1, total)


def compute_edge_ratio(grid: list[list[int]]) -> float:
    """Compute ratio of non-zero cells on edges."""
    if not grid or not grid[0]:
        return 0.0
    
    height = len(grid)
    width = len(grid[0])
    
    edge_cells = 0
    edge_nonzero = 0
    
    for r in range(height):
        for c in range(width):
            if r == 0 or r == height-1 or c == 0 or c == width-1:
                edge_cells += 1
                if grid[r][c] != 0:
                    edge_nonzero += 1
    
    return edge_nonzero / max(1, edge_cells)


def compute_pattern_similarity(grid: list[list[int]]) -> float:
    """Compute similarity between top-left pattern and rest of grid."""
    if not grid or not grid[0] or len(grid) < 10 or len(grid[0]) < 10:
        return 0.0
    
    # Assume top-left 10x10 is pattern
    pattern = [row[:10] for row in grid[:10]]
    
    # Compare with rest of grid (sliding window)
    height = len(grid)
    width = len(grid[0])
    
    max_similarity = 0.0
    
    for r in range(0, height-9, 5):
        for c in range(0, width-9, 5):
            if r == 0 and c == 0:
                continue  # Skip pattern itself
            
            # Compare
            matches = 0
            total = 0
            for pr in range(10):
                for pc in range(10):
                    if r+pr < height and c+pc < width:
                        if grid[r+pr][c+pc] == pattern[pr][pc]:
                            matches += 1
                        total += 1
            
            if total > 0:
                similarity = matches / total
                max_similarity = max(max_similarity, similarity)
    
    return max_similarity


def encode_goal_class(goal_class: str) -> float:
    """Encode goal class as float (0-1)."""
    classes = {
        "COVER": 0.0,
        "REACH": 0.14,
        "COPY": 0.28,
        "REDUCE": 0.42,
        "PLACE": 0.56,
        "FLOW": 0.70,
        "ALIGN": 0.84,
        "LOCAL_CONSTRAINTS": 1.0,
    }
    return classes.get(goal_class, 0.5)


def extract_features_arc(frame: dict[str, Any]) -> list[float]:
    """Extract 20 features from ARC-AGI-3 game state.
    
    Features (normalized to 0-1 range):
    0. grid_height / 30.0
    1. grid_width / 30.0
    2. grid_size / 900.0
    3. unique_colors / 10.0
    4. density (non-zero cells / total cells)
    5. objects_count / 20.0
    6. levels_completed / 5.0
    7. current_level / 5.0
    8. actions_taken / 400.0
    9. actions_since_level / 100.0
    10. lives / 5.0
    11. score / 100.0
    12. steps_remaining / step_limit
    13. no_op_ratio
    14. goal_class_encoded
    15. affordances_count / 10.0
    16. symmetry_score
    17. density (same as 4, for redundancy)
    18. edge_ratio
    19. pattern_similarity
    
    Returns:
        List of 20 floats in [0, 1] range
    """
    grid = frame.get("grid", [])
    
    if not grid or not grid[0]:
        return [0.0] * 20
    
    # Basic grid properties
    grid_height = len(grid)
    grid_width = len(grid[0])
    grid_size = grid_height * grid_width
    
    # Colors and objects
    flat_grid = [cell for row in grid for cell in row]
    unique_colors = len(set(flat_grid))
    non_zero_cells = sum(1 for cell in flat_grid if cell != 0)
    
    # Connected components
    objects_count = count_connected_components(grid)
    
    # Progress
    levels_completed = frame.get("levels_completed", 0)
    current_level = frame.get("current_level", 1)
    actions_taken = frame.get("action_count", 0)
    actions_since_level = frame.get("actions_since_level", 0)
    
    # Resources
    lives = frame.get("lives", 0)
    score = frame.get("score", 0)
    step_limit = frame.get("step_limit", 400)
    steps_remaining = step_limit - actions_taken
    
    # No-op detection
    no_op_count = frame.get("no_op_count", 0)
    no_op_ratio = no_op_count / max(1, actions_taken)
    
    # Goal class
    goal_class = frame.get("goal_class", "UNKNOWN")
    goal_class_encoded = encode_goal_class(goal_class)
    
    # Affordances
    affordances_count = count_affordances(grid)
    
    # Symmetry
    symmetry_score = compute_symmetry(grid)
    
    # Density
    density = non_zero_cells / max(1, grid_size)
    
    # Edge ratio
    edge_ratio = compute_edge_ratio(grid)
    
    # Pattern similarity
    pattern_similarity = compute_pattern_similarity(grid)
    
    features = [
        grid_height / 30.0,
        grid_width / 30.0,
        grid_size / 900.0,
        unique_colors / 10.0,
        density,
        objects_count / 20.0,
        levels_completed / 5.0,
        current_level / 5.0,
        actions_taken / 400.0,
        actions_since_level / 100.0,
        lives / 5.0,
        score / 100.0,
        steps_remaining / max(1, step_limit),
        no_op_ratio,
        goal_class_encoded,
        affordances_count / 10.0,
        symmetry_score,
        density,  # Redundant, but matches Pokemon TCG pattern
        edge_ratio,
        pattern_similarity,
    ]
    
    # Clamp to [0, 1]
    features = [max(0.0, min(1.0, f)) for f in features]
    
    return features


if __name__ == "__main__":
    # Test
    frame = {
        "grid": [
            [0, 1, 1, 0],
            [1, 2, 2, 1],
            [1, 2, 2, 1],
            [0, 1, 1, 0],
        ],
        "levels_completed": 1,
        "current_level": 2,
        "action_count": 50,
        "actions_since_level": 10,
        "lives": 3,
        "score": 25,
        "step_limit": 400,
        "no_op_count": 2,
        "goal_class": "COPY",
    }
    
    features = extract_features_arc(frame)
    print(f"Extracted {len(features)} features:")
    for i, f in enumerate(features):
        print(f"  f{i}: {f:.3f}")
