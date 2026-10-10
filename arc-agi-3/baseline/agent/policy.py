"""Deterministic, graph-driven exploration policy for ARC-AGI-3.

This module deliberately has no ARC SDK or model dependency.  It turns a frame
into a small, JSON-safe ``Snapshot`` and proposes one legal action.  Keeping the
policy pure Python makes its decision rules unit-testable locally and lets the
Kaggle adapter stay thin.

The policy is a baseline, not a claim of a solved ARC-AGI-3 agent.  Its purpose
is to replace a random-action starter with reproducible exploration that:

* honours the action set advertised by each environment;
* prioritises visually salient click targets over uniform random pixels;
* learns local obstacles while navigating visually recognized tile mazes;
* tracks whether actions changed a state, advanced a level, revisited a state,
  or caused a game-over; and
* avoids repeating the same click in an unchanged state.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from hashlib import blake2b
from heapq import heappop, heappush
from math import sqrt
from typing import Any, Iterable, Sequence

RESET = "RESET"
ACTION_NAMES = (RESET, *(f"ACTION{i}" for i in range(1, 8)))
ACTION_SET = frozenset(ACTION_NAMES)
COMPLEX_ACTION = "ACTION6"
DIRECTIONAL_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
# The standard directional protocol forms two inverse pairs.  Treating a newly
# discovered movement edge as reversible first lets the explorer expand a state
# graph breadth-first rather than walking one action direction into every
# corridor before trying its siblings.  The observed successor still decides
# whether the inverse actually returns, so this remains safe for games with
# one-way mechanics.
INVERSE_DIRECTIONAL_ACTION = {
    "ACTION1": "ACTION2",
    "ACTION2": "ACTION1",
    "ACTION3": "ACTION4",
    "ACTION4": "ACTION3",
}

Grid = tuple[tuple[int, ...], ...]
Planes = tuple[Grid, ...]
Coordinate = tuple[int, int]
TileGlyph = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Snapshot:
    """A dependency-free representation of one ARC observation."""

    state: str
    levels_completed: int
    available_actions: tuple[str, ...]
    planes: Planes

    @property
    def signature(self) -> str:
        """Stable content signature used for state-graph bookkeeping."""
        payload = repr(
            (self.state, self.levels_completed, self.available_actions, self.planes)
        ).encode("utf-8")
        return blake2b(payload, digest_size=12).hexdigest()


@dataclass(frozen=True)
class ActionProposal:
    """An action selected by the pure policy before SDK conversion."""

    name: str
    x: int | None = None
    y: int | None = None
    reasoning: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        if self.name == COMPLEX_ACTION:
            return f"{self.name}:{self.x}:{self.y}"
        return self.name


@dataclass
class ActionStats:
    """Observed consequences of a proposal, accumulated across states."""

    attempts: int = 0
    changed: int = 0
    level_gains: int = 0
    game_overs: int = 0
    revisits: int = 0

    @property
    def noops(self) -> int:
        return self.attempts - self.changed

    def observe(
        self,
        *,
        changed: bool,
        level_gain: int,
        game_over: bool,
        revisit: bool,
    ) -> None:
        self.attempts += 1
        self.changed += int(changed)
        self.level_gains += max(0, level_gain)
        self.game_overs += int(game_over)
        self.revisits += int(revisit)

    def utility(self) -> int:
        """Conservative integer utility for tie-breaking future probes."""
        if not self.attempts:
            return 0
        changed_rate = self.changed / self.attempts
        noop_rate = self.noops / self.attempts
        death_rate = self.game_overs / self.attempts
        revisit_rate = self.revisits / self.attempts
        return int(
            320 * changed_rate
            - 160 * noop_rate
            - 500 * death_rate
            - 90 * revisit_rate
            + 900 * self.level_gains
        )


@dataclass(frozen=True)
class Component:
    """One four-connected region of a same-colour grid."""

    color: int
    cells: tuple[Coordinate, ...]

    @property
    def size(self) -> int:
        return len(self.cells)


def normalize_state(value: Any) -> str:
    """Return an SDK-independent game-state name."""
    raw = getattr(value, "value", value)
    text = str(raw).strip().upper()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text or "NOT_PLAYED"


def normalize_action_name(value: Any) -> str | None:
    """Normalize int, Enum, or string action identifiers to ``ACTIONn``."""
    raw = getattr(value, "name", value)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        candidate = RESET if raw == 0 else f"ACTION{raw}"
        return candidate if candidate in ACTION_SET else None

    text = str(raw).strip().upper().replace(" ", "")
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    if text.isdigit():
        return normalize_action_name(int(text))
    return text if text in ACTION_SET else None


def normalize_actions(values: Iterable[Any] | None) -> tuple[str, ...]:
    """Return unique action names in the protocol's canonical order."""
    found = {
        normalized
        for value in (values or ())
        if (normalized := normalize_action_name(value)) is not None
    }
    return tuple(name for name in ACTION_NAMES if name in found)


def _as_builtin(value: Any) -> Any:
    """Convert NumPy-like values without making NumPy a project dependency."""
    converter = getattr(value, "tolist", None)
    if callable(converter):
        return converter()
    return value


def _is_sequence(value: Any) -> bool:
    value = _as_builtin(value)
    return isinstance(value, (list, tuple))


def _looks_like_grid(value: Any) -> bool:
    value = _as_builtin(value)
    if not _is_sequence(value):
        return False
    for row in value:
        row = _as_builtin(row)
        if not _is_sequence(row):
            return False
        if any(_is_sequence(cell) for cell in row):
            return False
    return True


def _freeze_grid(value: Any) -> Grid:
    rows = _as_builtin(value)
    frozen_rows: list[tuple[int, ...]] = []
    for row in rows:
        converted: list[int] = []
        for cell in _as_builtin(row):
            try:
                converted.append(int(cell))
            except (TypeError, ValueError):
                converted.append(0)
        frozen_rows.append(tuple(converted))
    return tuple(frozen_rows)


def normalize_planes(value: Any) -> Planes:
    """Normalize a 2-D grid or a list of 2-D grids into immutable planes."""
    value = _as_builtin(value)
    if not _is_sequence(value) or not value:
        return ()
    if _looks_like_grid(value):
        return (_freeze_grid(value),)
    planes = [_freeze_grid(plane) for plane in value if _looks_like_grid(plane)]
    return tuple(planes)


def snapshot_from_frame(frame: Any) -> Snapshot:
    """Build a ``Snapshot`` from an ARC FrameData-like object."""
    return Snapshot(
        state=normalize_state(getattr(frame, "state", "NOT_PLAYED")),
        levels_completed=int(getattr(frame, "levels_completed", 0) or 0),
        available_actions=normalize_actions(getattr(frame, "available_actions", ())),
        planes=normalize_planes(getattr(frame, "frame", ())),
    )


def primary_grid(planes: Planes) -> Grid:
    """Choose the largest plane; ARC frames normally contain exactly one."""
    if not planes:
        return ()
    return max(planes, key=lambda grid: sum(len(row) for row in grid))


def grid_shape(grid: Grid) -> tuple[int, int]:
    """Return maximum width and height, tolerating malformed/jagged grids."""
    return (max((len(row) for row in grid), default=0), len(grid))


def _at(planes: Planes, plane: int, x: int, y: int) -> int | None:
    if plane >= len(planes) or y >= len(planes[plane]) or y < 0 or x < 0:
        return None
    row = planes[plane][y]
    return row[x] if x < len(row) else None


def changed_coordinates(
    previous: Planes,
    current: Planes,
    excluded: set[Coordinate] | frozenset[Coordinate] | None = None,
) -> set[Coordinate]:
    """Find coordinates changed in any plane, optionally ignoring HUD cells."""
    changed: set[Coordinate] = set()
    excluded = excluded or frozenset()
    max_planes = max(len(previous), len(current))
    for plane_idx in range(max_planes):
        before = previous[plane_idx] if plane_idx < len(previous) else ()
        after = current[plane_idx] if plane_idx < len(current) else ()
        width = max(grid_shape(before)[0], grid_shape(after)[0])
        height = max(grid_shape(before)[1], grid_shape(after)[1])
        for y in range(height):
            for x in range(width):
                if (x, y) in excluded:
                    continue
                if _at(previous, plane_idx, x, y) != _at(current, plane_idx, x, y):
                    changed.add((x, y))
    return changed


def horizontal_hud_mask(snapshot: Snapshot) -> frozenset[Coordinate]:
    """Mask conservative top/bottom HUD bands on normal-sized ARC frames.

    ARC game frames commonly contain a changing progress/step strip along an
    outer horizontal edge. Treating that strip as world state makes a blocked
    move appear novel and breaks graph revisits. Small synthetic grids are left
    untouched; on a 64×64 frame only the outer four rows at each horizontal
    edge are excluded.
    """
    width, height = grid_shape(primary_grid(snapshot.planes))
    if width < 12 or height < 12:
        return frozenset()
    band = min(4, max(1, height // 16))
    return frozenset(
        (x, y)
        for y in (*range(band), *range(height - band, height))
        for x in range(width)
    )


def masked_signature(snapshot: Snapshot, excluded: set[Coordinate] | frozenset[Coordinate]) -> str:
    """Hash an observation after replacing known HUD coordinates with ``-1``."""
    masked_planes = tuple(
        tuple(
            tuple(-1 if (x, y) in excluded else cell for x, cell in enumerate(row))
            for y, row in enumerate(grid)
        )
        for grid in snapshot.planes
    )
    payload = repr(
        (snapshot.state, snapshot.levels_completed, snapshot.available_actions, masked_planes)
    ).encode("utf-8")
    return blake2b(payload, digest_size=12).hexdigest()


def connected_components(grid: Grid) -> tuple[Component, ...]:
    """Return four-connected same-colour components in deterministic order."""
    width, height = grid_shape(grid)
    seen: set[Coordinate] = set()
    out: list[Component] = []

    for y in range(height):
        for x in range(width):
            if (x, y) in seen or x >= len(grid[y]):
                continue
            color = grid[y][x]
            todo: deque[Coordinate] = deque([(x, y)])
            seen.add((x, y))
            cells: list[Coordinate] = []
            while todo:
                cx, cy = todo.popleft()
                cells.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in seen
                        or nx >= len(grid[ny])
                        or grid[ny][nx] != color
                    ):
                        continue
                    seen.add((nx, ny))
                    todo.append((nx, ny))
            out.append(Component(color=color, cells=tuple(sorted(cells, key=lambda p: (p[1], p[0])))))
    return tuple(out)


def _component_representatives(component: Component) -> tuple[Coordinate, ...]:
    """Produce a few stable in-component targets rather than every pixel."""
    cells = component.cells
    if not cells:
        return ()
    center_x = sum(x for x, _ in cells) / len(cells)
    center_y = sum(y for _, y in cells) / len(cells)
    closest_center = min(
        cells,
        key=lambda point: ((point[0] - center_x) ** 2 + (point[1] - center_y) ** 2, point[1], point[0]),
    )
    points = [closest_center, cells[0], cells[-1]]
    unique: list[Coordinate] = []
    for point in points:
        if point not in unique:
            unique.append(point)
    return tuple(unique)


def _fallback_clicks(width: int, height: int) -> tuple[Coordinate, ...]:
    """A deterministic 4×4 lattice used only when perception has no target."""
    if width <= 0 or height <= 0:
        return ()
    points: list[Coordinate] = []
    fractions = (1, 3, 5, 7)
    for fy in fractions:
        for fx in fractions:
            x = min(width - 1, (fx * width) // 8)
            y = min(height - 1, (fy * height) // 8)
            if (x, y) not in points:
                points.append((x, y))
    for point in ((width // 2, height // 2), (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        if point not in points:
            points.append(point)
    return tuple(points)


def rank_click_targets(
    snapshot: Snapshot,
    changed: set[Coordinate] | None = None,
    excluded: set[Coordinate] | frozenset[Coordinate] | None = None,
) -> tuple[tuple[int, Coordinate, dict[str, Any]], ...]:
    """Rank likely clickable pixels using rarity, component size, and change.

    It intentionally does not assume a colour palette or a game's mechanics.
    A small non-background component is a better first probe than a uniformly
    random coordinate, while a coordinate that recently changed gains a bonus.
    """
    grid = primary_grid(snapshot.planes)
    width, height = grid_shape(grid)
    if not width or not height:
        return ()

    changed = changed or set()
    excluded = excluded or frozenset()
    cells = [cell for row in grid for cell in row]
    color_counts = Counter(cells)
    background = color_counts.most_common(1)[0][0] if color_counts else 0
    candidates: dict[Coordinate, tuple[int, dict[str, Any]]] = {}

    for component in connected_components(grid):
        # The largest modal region is normally background. Keep it as a weak
        # fallback but strongly prefer compact or colour-rare regions.
        count_for_color = color_counts[component.color]
        component_size = component.size
        rarity = min(700, int(3600 / max(1, count_for_color)))
        compactness = min(700, int(2200 / max(1.0, sqrt(component_size))))
        foreground = 500 if component.color != background else 0
        size_penalty = min(500, max(0, component_size - 32) * 4)
        base_score = max(20, 100 + rarity + compactness + foreground - size_penalty)

        for x, y in _component_representatives(component):
            if (x, y) in excluded:
                continue
            score = base_score + (1000 if (x, y) in changed else 0)
            reason = {
                "policy": "novelty-explorer-v5",
                "kind": "salient-component",
                "color": component.color,
                "component_size": component_size,
                "recent_change": (x, y) in changed,
            }
            old = candidates.get((x, y))
            if old is None or score > old[0]:
                candidates[(x, y)] = (score, reason)

    for rank, point in enumerate(_fallback_clicks(width, height)):
        if point in excluded:
            continue
        score = 120 - rank
        if point in changed:
            score += 1000
        candidates.setdefault(
            point,
            (
                score,
                {
                    "policy": "novelty-explorer-v5",
                    "kind": "lattice-fallback",
                    "recent_change": point in changed,
                },
            ),
        )

    ordered = [
        (score, point, reason)
        for point, (score, reason) in candidates.items()
        if 0 <= point[0] <= 63 and 0 <= point[1] <= 63 and point not in excluded
    ]
    ordered.sort(key=lambda item: (-item[0], item[1][1], item[1][0]))
    return tuple(ordered)

TILE_SIZE = 5
# Canonical control semantics used by ARC's directional protocol.  The order is
# only a deterministic tie-break for an optimistic path; observed movement is
# what adds a location to the learned obstacle map.
MAZE_DIRECTION_DELTAS: dict[str, Coordinate] = {
    "ACTION1": (0, -1),
    "ACTION2": (0, 1),
    "ACTION3": (-1, 0),
    "ACTION4": (1, 0),
}
MAZE_ACTION_ORDER = ("ACTION3", "ACTION1", "ACTION4", "ACTION2")


@dataclass(frozen=True)
class TokenTarget:
    """A board glyph structurally matched to an edge token after quarter turns."""

    coordinate: Coordinate
    quarter_turns: int
    group_size: int
    appearance_mismatches: int
    appearance_signature: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class BottomEdgeMeter:
    """A long, two-colour paired-pixel indicator found at the bottom edge."""

    row: int
    start: int
    values: tuple[int, ...]


@dataclass(frozen=True)
class TileMazeView:
    """A conservative visual view of a regular tile-navigation board.

    This recognizer is deliberately opt-in: it requires a 5×5 two-colour
    striped avatar and all four directional controls.  It does not inspect a
    game ID or assume a particular colour palette. ``landmarks`` are compact
    non-uniform tile clusters that can be reached as potential switches/goals.
    ``token_targets`` adds an even stricter visual relation: a framed 2× edge
    badge has the same colour-partition glyph as an interior tile under a
    quarter-turn, while preserving raw appearance differences for feedback.
    """

    avatar: Coordinate
    shape: tuple[int, int]
    landmarks: tuple[tuple[Coordinate, frozenset[Coordinate]], ...]
    glyphs: tuple[tuple[Coordinate, TileGlyph], ...]
    token_targets: tuple[TokenTarget, ...]
    control_tiles: tuple[Coordinate, ...]
    resource_tiles: tuple[Coordinate, ...]


def _tile(grid: Grid, x: int, y: int) -> tuple[tuple[int, ...], ...] | None:
    """Return one complete ``TILE_SIZE`` square, or ``None`` at an edge."""
    if x < 0 or y < 0 or y + TILE_SIZE > len(grid):
        return None
    rows = grid[y : y + TILE_SIZE]
    if any(x + TILE_SIZE > len(row) for row in rows):
        return None
    return tuple(tuple(row[x : x + TILE_SIZE]) for row in rows)


def _striped_avatar_origins(grid: Grid) -> tuple[Coordinate, ...]:
    """Find rare, full 5×5 two-colour horizontal stripe glyphs.

    An avatar is learned from geometry rather than a colour ID: every row in
    its glyph is solid, exactly two colours form contiguous horizontal bands,
    and neither is the board's dominant background.  This is intentionally
    stricter than general component detection so ordinary colourful UI does not
    seize control from the graph explorer.
    """
    width, height = grid_shape(grid)
    if width < TILE_SIZE or height < TILE_SIZE:
        return ()
    counts = Counter(cell for row in grid for cell in row)
    if not counts:
        return ()
    background = counts.most_common(1)[0][0]
    candidates: list[tuple[int, int, int]] = []
    for y in range(height - TILE_SIZE + 1):
        for x in range(width - TILE_SIZE + 1):
            glyph = _tile(grid, x, y)
            if glyph is None or any(len(set(row)) != 1 for row in glyph):
                continue
            row_colours = tuple(row[0] for row in glyph)
            colours = set(row_colours)
            if len(colours) != 2 or background in colours:
                continue
            if sum(left != right for left, right in zip(row_colours, row_colours[1:])) != 1:
                continue
            # The rarest valid striped glyph is the most likely movable actor.
            candidates.append((sum(counts[colour] for colour in colours), y, x))
    return tuple((x, y) for _, y, x in sorted(candidates))


def _tile_groups(points: set[Coordinate]) -> tuple[frozenset[Coordinate], ...]:
    """Group four-connected landmark tiles deterministically."""
    groups: list[frozenset[Coordinate]] = []
    remaining = set(points)
    while remaining:
        seed = min(remaining, key=lambda point: (point[1], point[0]))
        remaining.remove(seed)
        group = {seed}
        queue: deque[Coordinate] = deque([seed])
        while queue:
            x, y = queue.popleft()
            for neighbour in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)):
                if neighbour not in remaining:
                    continue
                remaining.remove(neighbour)
                group.add(neighbour)
                queue.append(neighbour)
        groups.append(frozenset(group))
    return tuple(groups)


def _group_representative(group: frozenset[Coordinate]) -> Coordinate:
    """Choose a central, stable target coordinate for a landmark cluster."""
    mean_x = sum(x for x, _ in group) / len(group)
    mean_y = sum(y for _, y in group) / len(group)
    return min(
        group,
        key=lambda point: ((point[0] - mean_x) ** 2 + (point[1] - mean_y) ** 2, point[1], point[0]),
    )


def _uniform_tile_value(glyph: TileGlyph | None) -> int | None:
    """Return a tile's sole visual value, or ``None`` when it is varied."""
    if glyph is None:
        return None
    values = {cell for row in glyph for cell in row}
    return next(iter(values)) if len(values) == 1 else None


def _rotate_tile_glyph(glyph: TileGlyph) -> TileGlyph:
    """Rotate a square visual glyph one quarter turn clockwise."""
    return tuple(
        tuple(glyph[TILE_SIZE - 1 - x][y] for x in range(TILE_SIZE))
        for y in range(TILE_SIZE)
    )


def _colour_isomorphic(left: TileGlyph, right: TileGlyph) -> bool:
    """Whether two glyphs have equal structure under a one-to-one colour map.

    A mutable visual token may need a palette change as well as a rotation.
    Comparing colour partitions, rather than palette IDs, preserves the visual
    shape relation while retaining raw pixel differences for control feedback.
    """
    if len(left) != len(right) or any(len(a) != len(b) for a, b in zip(left, right)):
        return False
    left_to_right: dict[int, int] = {}
    right_to_left: dict[int, int] = {}
    for left_row, right_row in zip(left, right):
        for left_value, right_value in zip(left_row, right_row):
            if (
                left_value in left_to_right and left_to_right[left_value] != right_value
            ) or (
                right_value in right_to_left and right_to_left[right_value] != left_value
            ):
                return False
            left_to_right[left_value] = right_value
            right_to_left[right_value] = left_value
    return True


def _glyph_difference_signature(
    left: TileGlyph, right: TileGlyph
) -> tuple[tuple[int, int], ...]:
    """Describe raw aligned-pixel differences without naming palette values."""
    return tuple(
        (left_value, right_value)
        for left_row, right_row in zip(left, right)
        for left_value, right_value in zip(left_row, right_row)
        if left_value != right_value
    )


def _glyph_difference_count(left: TileGlyph, right: TileGlyph) -> int:
    """Count raw visual cells that remain different between aligned glyphs."""
    return len(_glyph_difference_signature(left, right))


def _framed_glyph(glyph: TileGlyph) -> bool:
    """Recognize a non-uniform 5×5 glyph with one uniform outer frame."""
    if len(glyph) != TILE_SIZE or any(len(row) != TILE_SIZE for row in glyph):
        return False
    border = {
        glyph[y][x]
        for y in range(TILE_SIZE)
        for x in range(TILE_SIZE)
        if x in {0, TILE_SIZE - 1} or y in {0, TILE_SIZE - 1}
    }
    interior = {
        glyph[y][x]
        for y in range(1, TILE_SIZE - 1)
        for x in range(1, TILE_SIZE - 1)
    }
    return len(border) == 1 and len(interior) >= 2


def _edge_badge_glyphs(grid: Grid) -> tuple[TileGlyph, ...]:
    """Find exact 2× scaled framed glyphs anchored near a screen edge.

    Some visual navigation games display the actor's mutable token as a
    magnified edge badge. The geometry is intentionally narrow: arbitrary UI
    text, ordinary tiles, and unframed status bars do not qualify.
    """
    width, height = grid_shape(grid)
    scale = 2
    side = TILE_SIZE * scale
    if width < side or height < side:
        return ()

    badges: set[TileGlyph] = set()
    margin = TILE_SIZE - 1
    planes: Planes = (grid,)
    for top in range(height - side + 1):
        for left in range(width - side + 1):
            if min(left, top, width - (left + side), height - (top + side)) > margin:
                continue
            rows: list[tuple[int, ...]] = []
            valid = True
            for tile_y in range(TILE_SIZE):
                row: list[int] = []
                for tile_x in range(TILE_SIZE):
                    values = {
                        _at(planes, 0, left + tile_x * scale + dx, top + tile_y * scale + dy)
                        for dx in range(scale)
                        for dy in range(scale)
                    }
                    if None in values or len(values) != 1:
                        valid = False
                        break
                    row.append(next(iter(values)))
                if not valid:
                    break
                rows.append(tuple(row))
            glyph = tuple(rows)
            if valid and _framed_glyph(glyph):
                badges.add(glyph)
    return tuple(sorted(badges))


def _bottom_edge_meter(grid: Grid) -> BottomEdgeMeter | None:
    """Find one long paired-pixel, one-or-two-colour bottom-edge indicator.

    This is intentionally geometric rather than palette-specific. A candidate
    does not become a countdown estimate until later frames show a consistent
    small replacement within the same strip, which rejects static footer art.
    """
    width, height = grid_shape(grid)
    minimum_width = max(12, width // 4)
    if width < minimum_width or height < 3:
        return None

    best: tuple[int, int, int, tuple[int, ...]] | None = None
    # HUD indicators conventionally use the final few rows. Requiring two
    # vertically paired pixels filters single-row text and thin maze borders.
    # Prefer the widest stable run first: an inactive meter colour can coincide
    # with the row immediately beneath it, creating a shorter false strip one
    # pixel lower than the full paired indicator.
    for row in range(max(0, height - 4), height - 1):
        paired: list[int | None] = []
        for column in range(width):
            if column >= len(grid[row]) or column >= len(grid[row + 1]):
                paired.append(None)
                continue
            upper, lower = grid[row][column], grid[row + 1][column]
            paired.append(upper if upper == lower else None)
        for start in range(width):
            colours: set[int] = set()
            for end in range(start, width):
                value = paired[end]
                if value is None:
                    break
                colours.add(value)
                if len(colours) > 2:
                    break
                length = end - start + 1
                if length < minimum_width:
                    continue
                candidate = (length, row, -start, tuple(paired[start : end + 1]))
                if best is None or candidate[:3] > best[:3]:
                    best = candidate
    if best is None:
        return None
    _, row, negated_start, values = best
    return BottomEdgeMeter(row=row, start=-negated_start, values=values)


def _meter_at_geometry(grid: Grid, meter: BottomEdgeMeter) -> BottomEdgeMeter | None:
    """Read a candidate meter at a prior geometry when its footer is stable."""
    width, height = grid_shape(grid)
    if meter.row < 0 or meter.row + 1 >= height or meter.start < 0:
        return None
    stop = meter.start + len(meter.values)
    if stop > width:
        return None
    values: list[int] = []
    for column in range(meter.start, stop):
        if column >= len(grid[meter.row]) or column >= len(grid[meter.row + 1]):
            return None
        upper, lower = grid[meter.row][column], grid[meter.row + 1][column]
        if upper != lower:
            return None
        values.append(upper)
    if len(set(values)) > 2:
        return None
    return BottomEdgeMeter(row=meter.row, start=meter.start, values=tuple(values))


def _compact_control_glyph(glyph: TileGlyph | None) -> bool:
    """Identify a small, information-rich single-tile interaction candidate."""
    if glyph is None:
        return False
    core = {
        glyph[y][x]
        for y in range(1, TILE_SIZE - 1)
        for x in range(1, TILE_SIZE - 1)
    }
    # A three-or-more-value inner glyph is deliberately stricter than ordinary
    # two-colour decoration or a seam between two uniform terrain tiles.
    return len(core) >= 3


def _framed_ring_glyph(glyph: TileGlyph | None) -> bool:
    """Recognize a compact framed ring, a common visual pickup affordance."""
    if glyph is None or not _framed_glyph(glyph):
        return False
    frame = glyph[0][0]
    if glyph[TILE_SIZE // 2][TILE_SIZE // 2] != frame:
        return False
    ring = {
        glyph[y][x]
        for y in range(1, TILE_SIZE - 1)
        for x in range(1, TILE_SIZE - 1)
        if (x, y) != (TILE_SIZE // 2, TILE_SIZE // 2)
    }
    return len(ring) == 1 and next(iter(ring)) != frame


def tile_maze_view(snapshot: Snapshot) -> TileMazeView | None:
    """Recognize a regular directional tile maze from one visual observation."""
    if not set(DIRECTIONAL_ACTIONS).issubset(snapshot.available_actions):
        return None
    grid = primary_grid(snapshot.planes)
    width, height = grid_shape(grid)
    if width < 8 * TILE_SIZE or height < 8 * TILE_SIZE:
        return None
    avatars = _striped_avatar_origins(grid)
    if not avatars:
        return None
    avatar_x, avatar_y = avatars[0]
    offset_x, offset_y = avatar_x % TILE_SIZE, avatar_y % TILE_SIZE
    origins_x = tuple(range(offset_x, width - TILE_SIZE + 1, TILE_SIZE))
    origins_y = tuple(range(offset_y, height - TILE_SIZE + 1, TILE_SIZE))
    if len(origins_x) < 8 or len(origins_y) < 8:
        return None
    avatar = ((avatar_x - offset_x) // TILE_SIZE, (avatar_y - offset_y) // TILE_SIZE)

    # A non-uniform grid tile is a possible game object.  Adjacent tiles are
    # clustered because a goal marker may span several tiles around its actual
    # enterable centre.  Fully uniform tiles are deliberately not guessed as
    # walls: unsuccessful moves learn collisions safely from observations.
    glyphs: dict[Coordinate, TileGlyph] = {}
    special: set[Coordinate] = set()
    for tile_y, origin_y in enumerate(origins_y):
        for tile_x, origin_x in enumerate(origins_x):
            glyph = _tile(grid, origin_x, origin_y)
            if glyph is None:
                continue
            coordinate = (tile_x, tile_y)
            glyphs[coordinate] = glyph
            if coordinate != avatar and len({cell for row in glyph for cell in row}) > 1:
                # The actor is a moving overlay, not part of an adjacent goal
                # or control. Keeping it out before grouping prevents it from
                # visually gluing a one-tile control to itself.
                special.add(coordinate)

    groups_by_cell: dict[Coordinate, frozenset[Coordinate]] = {}
    landmarks: list[tuple[Coordinate, frozenset[Coordinate]]] = []
    for group in _tile_groups(special):
        for coordinate in group:
            groups_by_cell[coordinate] = group
        landmarks.append((_group_representative(group), group))
    landmarks.sort(key=lambda item: (item[0][1], item[0][0]))
    if not landmarks:
        return None

    tile_shape = (len(origins_x), len(origins_y))
    control_tiles = tuple(
        sorted(
            (
                representative
                for representative, group in landmarks
                if len(group) == 1 and _compact_control_glyph(glyphs.get(representative))
            ),
            key=lambda point: (point[1], point[0]),
        )
    )
    resource_tiles = tuple(
        sorted(
            (
                representative
                for representative, group in landmarks
                if (
                    len(group) == 1
                    and 1 <= representative[0] < tile_shape[0] - 1
                    and 1 <= representative[1] < tile_shape[1] - 1
                    and _framed_ring_glyph(glyphs.get(representative))
                )
            ),
            key=lambda point: (point[1], point[0]),
        )
    )
    token_options: list[TokenTarget] = []
    for badge in _edge_badge_glyphs(grid):
        rotated = badge
        for quarter_turns in range(4):
            for coordinate, glyph in glyphs.items():
                group = groups_by_cell.get(coordinate)
                if (
                    group is None
                    or coordinate == avatar
                    or not (1 <= coordinate[0] < tile_shape[0] - 1)
                    or not (1 <= coordinate[1] < tile_shape[1] - 1)
                    or not _framed_glyph(glyph)
                    or not _colour_isomorphic(glyph, rotated)
                ):
                    continue
                token_options.append(
                    TokenTarget(
                        coordinate=coordinate,
                        quarter_turns=quarter_turns,
                        group_size=len(group),
                        appearance_mismatches=_glyph_difference_count(glyph, rotated),
                        appearance_signature=_glyph_difference_signature(glyph, rotated),
                    )
                )
            rotated = _rotate_tile_glyph(rotated)
    token_targets = tuple(
        sorted(
            set(token_options),
            key=lambda target: (
                -target.group_size,
                target.appearance_mismatches,
                target.coordinate[1],
                target.coordinate[0],
                target.quarter_turns,
            ),
        )
    )
    return TileMazeView(
        avatar=avatar,
        shape=tile_shape,
        landmarks=tuple(landmarks),
        glyphs=tuple(sorted(glyphs.items(), key=lambda item: (item[0][1], item[0][0]))),
        token_targets=token_targets,
        control_tiles=control_tiles,
        resource_tiles=resource_tiles,
    )


def optimistic_tile_path(
    start: Coordinate,
    target: Coordinate,
    shape: tuple[int, int],
    blocked: set[Coordinate] | frozenset[Coordinate],
) -> tuple[str, ...] | None:
    """Plan through observed-free and as-yet-unseen tiles with deterministic A*."""
    if start == target:
        return ()
    width, height = shape
    sequence = 0
    queue: list[tuple[int, int, int, int, Coordinate, tuple[str, ...]]] = []
    costs: dict[Coordinate, int] = {start: 0}
    heappush(
        queue,
        (abs(start[0] - target[0]) + abs(start[1] - target[1]), 0, 0, sequence, start, ()),
    )
    while queue:
        _, cost, _, _, point, path = heappop(queue)
        if cost != costs.get(point):
            continue
        if point == target:
            return path
        for rank, action in enumerate(MAZE_ACTION_ORDER):
            dx, dy = MAZE_DIRECTION_DELTAS[action]
            neighbour = (point[0] + dx, point[1] + dy)
            if (
                neighbour in blocked
                or neighbour[0] < 0
                or neighbour[1] < 0
                or neighbour[0] >= width
                or neighbour[1] >= height
            ):
                continue
            next_cost = cost + 1
            if next_cost >= costs.get(neighbour, next_cost + 1):
                continue
            costs[neighbour] = next_cost
            sequence += 1
            heuristic = abs(neighbour[0] - target[0]) + abs(neighbour[1] - target[1])
            heappush(
                queue,
                (next_cost + heuristic, next_cost, rank, sequence, neighbour, path + (action,)),
            )
    return None


class TileMazeNavigator:
    """Learn collisions online while steering to visible interior landmarks.

    It is a small navigation primitive, not a game-specific route: a failed
    directional move records one blocked tile, then optimistic A* replans.  A
    reached landmark is not selected again in the same episode, which makes a
    nearby switch naturally precede a farther revealed target.  Any missing
    avatar/modal frame resets this short-lived model and hands control back to
    the general graph explorer.
    """

    _MAX_TOKEN_CONTROL_ENTRIES = 4
    # A landing tile becomes a navigation guard after one explicit GAME_OVER on
    # a level. Repeated runs of the measured public games show a deterministic
    # board per level (identical death geometry across attempts), so a single
    # observed landing is reliable causal evidence there; two confirmations
    # merely wasted an entire doomed ~130-step attempt inside a 400-action cap.
    # The memory stays isolated per level for games whose boards do differ.
    _MIN_TERMINAL_CONFIRMATIONS = 1

    def __init__(self) -> None:
        self._blocked: set[Coordinate] = set()
        self._blocked_uniform_values: set[int] = set()
        self._traversable_uniform_values: set[int] = set()
        # Landing tiles that explicitly ended an attempt on a level, keyed by
        # (levels_completed, tile). Unlike episode geometry this deliberately
        # survives terminal resets so a replay of the same level never repeats
        # the identical fatal step; level keys stop old boards from influencing
        # later levels, and the whole policy is one game instance anyway.
        self._terminal_landing_counts: dict[tuple[int, Coordinate], int] = {}
        self._visited: set[Coordinate] = set()
        self._active: tuple[Coordinate, frozenset[Coordinate]] | None = None
        self._last_avatar: Coordinate | None = None
        self._last_action: str | None = None
        self._last_view: TileMazeView | None = None
        # One unreadable animation/modal frame should not erase a relation
        # that is visually re-established on the next observation.
        self._view_misses = 0
        self._levels_completed: int | None = None
        # An optional visual relation between an edge token, a compact control,
        # and a framed board target. These are coordinates inferred fresh from
        # pixels, never a task layout or an action script.
        self._token_goal: Coordinate | None = None
        self._token_control: Coordinate | None = None
        self._control_entries = 0
        self._control_entries_by_tile: dict[Coordinate, int] = {}
        self._control_effects: dict[Coordinate, tuple[bool, bool]] = {}
        self._retired_controls: set[Coordinate] = set()
        self._last_token_target: TokenTarget | None = None
        self._last_bottom_meter: BottomEdgeMeter | None = None
        self._meter_tick_pair: tuple[int, int] | None = None
        self._meter_tick_observations = 0
        self._meter_active_value: int | None = None
        self._meter_units_per_action: int | None = None
        # Aggregate only generic meter-observation counts. Unlike the current
        # meter estimate, these survive episode resets for a safe run report.
        self._meter_evidence: Counter[str] = Counter()
        # Compact visual-control outcomes likewise survive retries. They carry
        # no palette values, tile coordinates, or inferred game rules, but make
        # a held-out run diagnostic enough to distinguish a bad route from a
        # control whose observed effect is moving away from the target.
        self._token_evidence: Counter[str] = Counter()
        self._bounce_return: str | None = None
        self._active_resource: Coordinate | None = None
        self._active_resource_meter_bound = False
        # ``_used_resources`` has a deliberately literal meaning: a resource
        # enters it only after the avatar is observed on its tile. Routes that
        # cannot currently be used are deferred separately, so a tightened
        # meter estimate never fabricates a pickup merely to avoid replanning.
        self._used_resources: set[Coordinate] = set()
        self._route_deferred_resources: set[Coordinate] = set()
        self._meter_deferred_resources: dict[Coordinate, int] = {}

    def reset(self, *, reason: str | None = None) -> None:
        """Forget episode-local geometry after terminal or modal feedback."""
        if reason is not None:
            self._token_evidence[f"reset-{reason}"] += 1
        self._blocked.clear()
        self._blocked_uniform_values.clear()
        self._traversable_uniform_values.clear()
        self._visited.clear()
        self._active = None
        self._last_avatar = None
        self._last_action = None
        self._last_view = None
        self._view_misses = 0
        self._levels_completed = None
        self._token_goal = None
        self._token_control = None
        self._control_entries = 0
        self._control_entries_by_tile.clear()
        self._control_effects.clear()
        self._retired_controls.clear()
        self._last_token_target = None
        self._last_bottom_meter = None
        self._meter_tick_pair = None
        self._meter_tick_observations = 0
        self._meter_active_value = None
        self._meter_units_per_action = None
        self._bounce_return = None
        self._active_resource = None
        self._active_resource_meter_bound = False
        self._used_resources.clear()
        self._route_deferred_resources.clear()
        self._meter_deferred_resources.clear()

    @staticmethod
    def _glyph_at(view: TileMazeView, coordinate: Coordinate) -> TileGlyph | None:
        """Look up one lattice glyph without exposing mutable image state."""
        for point, glyph in view.glyphs:
            if point == coordinate:
                return glyph
        return None

    def _known_blocked(self, view: TileMazeView) -> set[Coordinate]:
        """Combine exact collisions, wall style, and confirmed death landings."""
        blocked = set(self._blocked)
        for coordinate, glyph in view.glyphs:
            if (
                coordinate != view.avatar
                and _uniform_tile_value(glyph) in self._blocked_uniform_values
            ):
                blocked.add(coordinate)
        blocked.update(self._confirmed_terminal_tiles())
        return blocked

    def note_terminal_landing(self, snapshot: Snapshot, view: TileMazeView | None) -> None:
        """Retain one explicit GAME_OVER landing for a level.

        The landing tile is the avatar tile of the terminal frame when the tile
        board is still visible; otherwise it is estimated from the tile the
        last directional action was about to enter. A tile becomes a navigation
        guard after the level has ended on it once (see
        ``_MIN_TERMINAL_CONFIRMATIONS``); the memory stays isolated per level
        so boards that do vary between attempts cannot poison a later level.
        """
        landing: Coordinate | None = view.avatar if view is not None else None
        if (
            landing is None
            and self._last_action in MAZE_DIRECTION_DELTAS
            and self._last_avatar is not None
        ):
            dx, dy = MAZE_DIRECTION_DELTAS[self._last_action]
            landing = (self._last_avatar[0] + dx, self._last_avatar[1] + dy)
        if landing is None:
            return
        self._token_evidence["terminal-landings-seen"] += 1
        key = (snapshot.levels_completed, landing)
        count = self._terminal_landing_counts.get(key, 0) + 1
        self._terminal_landing_counts[key] = count
        if count == self._MIN_TERMINAL_CONFIRMATIONS:
            self._token_evidence["terminal-landings-learned"] += 1

    def _confirmed_terminal_tiles(self) -> frozenset[Coordinate]:
        """Return tiles whose entry ended the current level with GAME_OVER."""
        if self._levels_completed is None:
            return frozenset()
        return frozenset(
            tile
            for (level, tile), count in self._terminal_landing_counts.items()
            if level == self._levels_completed
            and count >= self._MIN_TERMINAL_CONFIRMATIONS
        )

    def _clear_spatial_navigation(self) -> None:
        """Discard route geometry while retaining an independently live relation."""
        self._blocked.clear()
        self._blocked_uniform_values.clear()
        self._traversable_uniform_values.clear()
        self._visited.clear()
        self._active = None
        self._last_avatar = None
        self._last_action = None
        self._last_view = None
        self._view_misses = 0
        self._bounce_return = None
        self._active_resource = None
        self._active_resource_meter_bound = False
        self._used_resources.clear()
        self._route_deferred_resources.clear()
        self._meter_deferred_resources.clear()

    def _relation_is_live(self, view: TileMazeView) -> bool:
        """Whether the selected token relation still appears at its live tiles."""
        if self._token_goal is None or self._target_for_goal(view, self._token_goal) is None:
            return False
        return self._token_control is None or self._token_control in view.control_tiles

    def _has_verified_token_relation(self) -> bool:
        """Whether the last accepted tile view established the selected target."""
        return (
            self._token_goal is not None
            and self._last_token_target is not None
            and self._last_token_target.coordinate == self._token_goal
        )

    def _clear_local_navigation(self) -> None:
        """Clear all local assumptions after an incompatible avatar displacement."""
        self._clear_spatial_navigation()
        self._token_goal = None
        self._token_control = None
        self._control_entries = 0
        self._control_entries_by_tile.clear()
        self._control_effects.clear()
        self._retired_controls.clear()
        self._last_token_target = None
        self._last_bottom_meter = None
        self._meter_tick_pair = None
        self._meter_tick_observations = 0
        self._meter_active_value = None
        self._meter_units_per_action = None

    def _observe_avatar(self, view: TileMazeView) -> None:
        if self._last_avatar is None or self._last_action is None:
            return
        dx, dy = MAZE_DIRECTION_DELTAS[self._last_action]
        expected = (self._last_avatar[0] + dx, self._last_avatar[1] + dy)
        if view.avatar == self._last_avatar:
            self._blocked.add(expected)
            previous_glyph = (
                self._glyph_at(self._last_view, expected)
                if self._last_view is not None
                else None
            )
            blocked_value = _uniform_tile_value(previous_glyph)
            # A visual terrain style is generalized only after we have observed
            # a different uniform style underneath a successful move. This
            # preserves the collision-first discipline for dynamic obstacles.
            if (
                blocked_value is not None
                and blocked_value not in self._traversable_uniform_values
            ):
                self._blocked_uniform_values.add(blocked_value)
        elif view.avatar == expected:
            # Once an avatar leaves a tile, the newly exposed uniform glyph is
            # direct evidence that this visual style can be traversed.
            traversed_value = _uniform_tile_value(self._glyph_at(view, self._last_avatar))
            if traversed_value is not None:
                self._traversable_uniform_values.add(traversed_value)
        else:
            # A teleport, moving platform, or a changed tile scale invalidates
            # the local path model. Preserve a stricter high-level relation
            # only when its board token and selected control are still visible
            # at the same freshly perceived tile coordinates; otherwise rebuild
            # all local assumptions as before.
            if self._relation_is_live(view):
                self._token_evidence["unexpected-avatar-relation-preserved"] += 1
                self._clear_spatial_navigation()
            else:
                self._token_evidence["unexpected-avatar-resets"] += 1
                self._clear_local_navigation()

    def _observe_bottom_meter(self, snapshot: Snapshot) -> None:
        """Learn a depleting bottom indicator only after repeated small ticks."""
        grid = primary_grid(snapshot.planes)
        meter = _bottom_edge_meter(grid)
        previous = self._last_bottom_meter
        # At a full reset, a same-colour footer detail can extend a raw run by
        # one pixel. Retain the prior geometry only when the new raw candidate
        # substantially overlaps it and every old paired pixel still agrees.
        if (
            meter is not None
            and previous is not None
            and meter.row == previous.row
            and (meter.start, len(meter.values)) != (previous.start, len(previous.values))
        ):
            overlap = max(
                0,
                min(meter.start + len(meter.values), previous.start + len(previous.values))
                - max(meter.start, previous.start),
            )
            if overlap * 4 >= min(len(meter.values), len(previous.values)) * 3:
                aligned = _meter_at_geometry(grid, previous)
                if aligned is not None:
                    meter = aligned
                    self._meter_evidence["geometry-alignments"] += 1
        self._last_bottom_meter = meter
        if meter is not None:
            self._meter_evidence["candidate-observations"] += 1
        if meter is None:
            return
        if previous is None:
            if self._meter_active_value is not None or self._meter_units_per_action is not None:
                self._meter_tick_pair = None
                self._meter_tick_observations = 0
                self._meter_active_value = None
                self._meter_units_per_action = None
                self._meter_evidence["geometry-estimate-resets"] += 1
            return
        if (meter.row, meter.start, len(meter.values)) != (
            previous.row,
            previous.start,
            len(previous.values),
        ):
            # A new footer geometry cannot safely inherit an old active colour
            # or tick width. This also keeps a preserved high-level token
            # relation from steering by a stale meter after a screen shift.
            self._meter_tick_pair = None
            self._meter_tick_observations = 0
            self._meter_active_value = None
            self._meter_units_per_action = None
            self._meter_evidence["geometry-estimate-resets"] += 1
            return
        self._meter_evidence["matching-geometry-observations"] += 1
        replacements = [
            (before, after)
            for before, after in zip(previous.values, meter.values)
            if before != after
        ]
        # A regular countdown tick is deliberately narrow compared with a
        # level transition or a broad HUD redraw. The bound scales with the
        # indicator width and tolerates meters with a few units per action.
        if not replacements or len(replacements) > max(4, len(meter.values) // 8):
            return
        pair_counts = Counter(replacements)
        if len(pair_counts) != 1:
            return
        pair, units = next(iter(pair_counts.items()))
        self._meter_evidence["regular-tick-observations"] += 1
        if pair == self._meter_tick_pair:
            self._meter_tick_observations += 1
        else:
            self._meter_tick_pair = pair
            self._meter_tick_observations = 1
        # One accidental small UI update is not enough to steer navigation.
        # Two consecutive same-direction replacements establish both the
        # active value and its observed consumption per submitted action.
        if self._meter_tick_observations >= 2:
            if (self._meter_active_value, self._meter_units_per_action) != (pair[0], units):
                self._meter_evidence["estimates-established"] += 1
            self._meter_active_value = pair[0]
            self._meter_units_per_action = units

    def _meter_actions_remaining(self) -> int | None:
        """Return an observed countdown budget, never a palette-specific guess."""
        if (
            self._last_bottom_meter is None
            or self._meter_active_value is None
            or self._meter_units_per_action is None
        ):
            return None
        active_units = sum(
            value == self._meter_active_value
            for value in self._last_bottom_meter.values
        )
        return active_units // self._meter_units_per_action

    def meter_evidence(self) -> dict[str, int]:
        """Return aggregate, palette-free meter observations for a run report."""
        return dict(sorted(self._meter_evidence.items()))

    def token_evidence(self) -> dict[str, int]:
        """Return aggregate, coordinate-free visual control outcomes for a run."""
        return dict(sorted(self._token_evidence.items()))

    def _resource_is_urgent_before_control(
        self, view: TileMazeView, target: TokenTarget, control: Coordinate
    ) -> int | None:
        """Use a reachable ring before a control when a learned meter is tight."""
        self._meter_evidence["staged-route-checks"] += 1
        remaining = self._meter_actions_remaining()
        if remaining is None:
            self._meter_evidence["route-checks-without-estimate"] += 1
            return None
        blocked = self._known_blocked(view)
        to_control = optimistic_tile_path(view.avatar, control, view.shape, blocked)
        control_to_target = optimistic_tile_path(control, target.coordinate, view.shape, blocked)
        if to_control is None or control_to_target is None:
            self._meter_evidence["route-checks-without-path"] += 1
            return None
        # This deliberately ignores unknown control-cycle counts. If merely
        # reaching the selected control and then the visible board target
        # already exceeds the measured budget, a reachable ring is a safer
        # visually justified waypoint than the direct route.
        if len(to_control) + len(control_to_target) > remaining:
            self._meter_evidence["meter-tight-route-checks"] += 1
            return remaining
        return None

    @staticmethod
    def _interior_landmarks(view: TileMazeView) -> tuple[tuple[Coordinate, frozenset[Coordinate]], ...]:
        width, height = view.shape
        interior = tuple(
            landmark
            for landmark in view.landmarks
            if 1 <= landmark[0][0] < width - 1 and 1 <= landmark[0][1] < height - 2
        )
        return interior or view.landmarks

    @staticmethod
    def _target_for_goal(view: TileMazeView, goal: Coordinate) -> TokenTarget | None:
        """Recover the live visual state of one previously selected board token."""
        return next((target for target in view.token_targets if target.coordinate == goal), None)

    def _token_target(self, view: TileMazeView) -> TokenTarget | None:
        """Select one stable badge-to-board relation and its first compact control."""
        if self._token_goal is not None:
            return self._target_for_goal(view, self._token_goal)

        blocked = self._known_blocked(view)
        options: list[tuple[int, int, int, int, TokenTarget, Coordinate]] = []
        for target_rank, target in enumerate(view.token_targets):
            for control in view.control_tiles:
                if control == target.coordinate:
                    continue
                path = optimistic_tile_path(view.avatar, control, view.shape, blocked)
                if path is None:
                    continue
                options.append(
                    (
                        target_rank,
                        len(path),
                        control[1],
                        control[0],
                        target,
                        control,
                    )
                )
        if not options:
            return None
        _, _, _, _, target, control = min(options)
        self._token_evidence["relations-selected"] += 1
        self._token_goal = target.coordinate
        self._token_control = control
        self._control_entries = 0
        self._control_entries_by_tile.clear()
        self._control_effects.clear()
        self._retired_controls.clear()
        self._last_token_target = None
        self._bounce_return = None
        # Route eligibility is relative to the target/control relation. A
        # newly recognized relation warrants retrying any resource that was
        # deferred for the preceding one; it still does not make it "used".
        self._route_deferred_resources.clear()
        self._meter_deferred_resources.clear()
        # Avoid advancing the older landmark model while this stricter visual
        # relation is active.
        self._active = None
        return target

    def _select_token_control(
        self, view: TileMazeView, target: TokenTarget
    ) -> Coordinate | None:
        """Choose an unretired reachable control using only observed feedback."""
        blocked = self._known_blocked(view)
        candidates: list[tuple[int, int, int, int, Coordinate]] = []
        for control in view.control_tiles:
            if control == target.coordinate or control in self._retired_controls:
                continue
            path = optimistic_tile_path(view.avatar, control, view.shape, blocked)
            if path is None:
                continue
            affects_turns, affects_appearance = self._control_effects.get(control, (False, False))
            helps_open_difference = (
                target.quarter_turns > 0 and affects_turns
            ) or (
                target.appearance_mismatches > 0 and affects_appearance
            )
            # A control that has already visibly addressed the outstanding
            # difference wins; otherwise sample the nearest unknown one.
            candidates.append(
                (
                    0 if helps_open_difference else 1,
                    len(path),
                    control[1],
                    control[0],
                    control,
                )
            )
        if not candidates:
            self._token_control = None
            return None
        _, _, _, _, control = min(candidates)
        if control != self._token_control:
            # A route-neutral resource detour is evaluated against the active
            # control. Reconsider prior route deferrals after that destination
            # changes, without conflating them with consumed resources.
            self._route_deferred_resources.clear()
        self._token_control = control
        self._bounce_return = None
        return control

    def _record_control_entry(self, target: TokenTarget, entered_control: bool) -> None:
        """Learn which visual difference changed after entering a control tile."""
        control = self._token_control
        if not entered_control or control is None:
            return
        self._control_entries += 1
        self._control_entries_by_tile[control] = self._control_entries_by_tile.get(control, 0) + 1
        self._token_evidence["control-entries"] += 1
        before = self._last_token_target
        if before is None or before.coordinate != target.coordinate:
            self._token_evidence["control-entries-without-comparison"] += 1
            return
        turns_changed = before.quarter_turns != target.quarter_turns
        if turns_changed:
            self._token_evidence["orientation-changing-entries"] += 1
            before_distance = min(before.quarter_turns, 4 - before.quarter_turns)
            after_distance = min(target.quarter_turns, 4 - target.quarter_turns)
            if after_distance < before_distance:
                self._token_evidence["orientation-improving-entries"] += 1
            elif after_distance > before_distance:
                self._token_evidence["orientation-worsening-entries"] += 1
            else:
                self._token_evidence["orientation-neutral-entries"] += 1
        # Ignore an incidental raw-pixel rearrangement caused by a rotation:
        # a palette control is evidenced by a changed aligned appearance while
        # its inferred orientation remains the same.
        appearance_changed = (
            not turns_changed
            and before.appearance_signature != target.appearance_signature
        )
        if appearance_changed:
            self._token_evidence["appearance-changing-entries"] += 1
            if target.appearance_mismatches < before.appearance_mismatches:
                self._token_evidence["appearance-improving-entries"] += 1
            elif target.appearance_mismatches > before.appearance_mismatches:
                self._token_evidence["appearance-worsening-entries"] += 1
            else:
                self._token_evidence["appearance-neutral-entries"] += 1
        previous_turns, previous_appearance = self._control_effects.get(control, (False, False))
        self._control_effects[control] = (
            previous_turns or turns_changed,
            previous_appearance or appearance_changed,
        )

    def _control_needs_reentry(self, control: Coordinate, target: TokenTarget) -> bool:
        """Decide whether the current control still affects an open mismatch."""
        entries = self._control_entries_by_tile.get(control, 0)
        if entries == 0:
            # If the avatar began on a control, leave and re-enter once to
            # obtain an actual visual intervention observation.
            return True
        if entries >= self._MAX_TOKEN_CONTROL_ENTRIES:
            return False
        affects_turns, affects_appearance = self._control_effects.get(control, (False, False))
        return (
            target.quarter_turns > 0 and affects_turns
        ) or (
            target.appearance_mismatches > 0 and affects_appearance
        )

    def _record_maze_action(self, view: TileMazeView, action: str | None) -> None:
        """Retain only the last visual movement observation for online learning."""
        self._last_avatar = view.avatar
        self._last_action = action
        self._last_view = view
        self._last_token_target = (
            self._target_for_goal(view, self._token_goal)
            if self._token_goal is not None
            else None
        )

    def _token_bounce_action(self, view: TileMazeView) -> str | None:
        """Step out of a responsive control so a later step can re-enter it."""
        if self._token_control is None:
            return None
        blocked = self._known_blocked(view)
        if self._last_avatar is not None and self._last_action in INVERSE_DIRECTIONAL_ACTION:
            dx, dy = MAZE_DIRECTION_DELTAS[self._last_action]
            entered = (self._last_avatar[0] + dx, self._last_avatar[1] + dy)
            exit_action = INVERSE_DIRECTIONAL_ACTION[self._last_action]
            if entered == self._token_control and self._last_avatar not in blocked:
                self._bounce_return = self._last_action
                return exit_action
        for action in MAZE_ACTION_ORDER:
            dx, dy = MAZE_DIRECTION_DELTAS[action]
            neighbour = (view.avatar[0] + dx, view.avatar[1] + dy)
            if (
                0 <= neighbour[0] < view.shape[0]
                and 0 <= neighbour[1] < view.shape[1]
                and neighbour not in blocked
            ):
                self._bounce_return = INVERSE_DIRECTIONAL_ACTION[action]
                return action
        return None

    def _observe_resource_arrival(self, view: TileMazeView) -> None:
        """Mark one visually selected resource after the avatar reaches its tile."""
        if self._active_resource is not None and view.avatar == self._active_resource:
            self._token_evidence["resource-arrivals"] += 1
            self._used_resources.add(self._active_resource)
            self._route_deferred_resources.discard(self._active_resource)
            self._meter_deferred_resources.pop(self._active_resource, None)
            # Reaching a resource is an observed world transition. Other route
            # deferrals were based on the preceding board and can be retried.
            self._route_deferred_resources.clear()
            self._active_resource = None
            self._active_resource_meter_bound = False

    def _resource_proposal(
        self,
        view: TileMazeView,
        *,
        goal: Coordinate,
        require_goal_neutral_route: bool,
        max_actions_to_resource: int | None = None,
    ) -> ActionProposal | None:
        """Route to a framed resource under optional route and meter constraints."""
        blocked = self._known_blocked(view)
        meter_bounded = max_actions_to_resource is not None
        candidates = [
            resource
            for resource in view.resource_tiles
            if (
                resource not in self._used_resources
                and resource not in self._route_deferred_resources
                and resource != view.avatar
            )
        ]
        if self._active_resource is not None:
            candidates = [self._active_resource]
        if meter_bounded:
            self._meter_evidence["meter-resource-route-attempts"] += 1
            eligible: list[Coordinate] = []
            for resource in candidates:
                deferred_at = self._meter_deferred_resources.get(resource)
                if deferred_at is not None and max_actions_to_resource <= deferred_at:
                    self._meter_evidence["meter-resource-deferred-candidates"] += 1
                    continue
                if deferred_at is not None:
                    # Only a strictly larger observed budget reopens a route
                    # that was previously too long. A falling countdown cannot
                    # make that route safer, but a visually observed refill can.
                    self._meter_deferred_resources.pop(resource, None)
                    self._meter_evidence["meter-resource-retried-candidates"] += 1
                eligible.append(resource)
            candidates = eligible
        else:
            candidates = [
                resource
                for resource in candidates
                if resource not in self._meter_deferred_resources
            ]
        if not candidates:
            if meter_bounded:
                self._meter_evidence["meter-resource-no-candidates"] += 1
            return None

        direct = optimistic_tile_path(view.avatar, goal, view.shape, blocked)
        routes: list[tuple[int, int, int, int, Coordinate, tuple[str, ...]]] = []
        route_deferred: set[Coordinate] = set()
        meter_deferred: set[Coordinate] = set()
        for resource in candidates:
            to_resource = optimistic_tile_path(view.avatar, resource, view.shape, blocked)
            if to_resource is None:
                route_deferred.add(resource)
                if meter_bounded:
                    self._meter_evidence["meter-resource-unreachable-candidates"] += 1
                continue
            if max_actions_to_resource is not None and len(to_resource) > max_actions_to_resource:
                meter_deferred.add(resource)
                self._meter_evidence["meter-resource-over-budget-candidates"] += 1
                continue
            resource_to_goal: tuple[str, ...] | None = None
            if require_goal_neutral_route or max_actions_to_resource is not None:
                resource_to_goal = optimistic_tile_path(resource, goal, view.shape, blocked)
                if resource_to_goal is None:
                    route_deferred.add(resource)
                    if meter_bounded:
                        self._meter_evidence["meter-resource-no-continuation-candidates"] += 1
                    continue
            if require_goal_neutral_route and (
                direct is None
                or len(to_resource) + len(resource_to_goal) > len(direct)
            ):
                # This is a strategic filter rather than an unreachable route:
                # a following meter-bounded check may still justify the same
                # detour, so do not defer the resource here.
                continue
            # For a meter-bounded detour, also prefer a short continuation
            # after the visual reset; ordinary first-resource selection keeps
            # its original nearest-waypoint ranking.
            continuation = 0 if resource_to_goal is None else len(resource_to_goal)
            routes.append(
                (
                    len(to_resource) + continuation if max_actions_to_resource is not None else len(to_resource),
                    len(to_resource),
                    abs(view.avatar[0] - resource[0]) + abs(view.avatar[1] - resource[1]),
                    resource[1],
                    resource,
                    to_resource,
                )
            )
        if not routes:
            # A rejected route is not a collected resource. Keep physical
            # pickup state separate from path eligibility: defer candidates
            # only for the current visual relation, while a meter rejection is
            # retried solely after a strictly larger observed action budget.
            self._route_deferred_resources.update(route_deferred)
            if meter_deferred and max_actions_to_resource is not None:
                newly_meter_deferred = 0
                for resource in meter_deferred:
                    previous_budget = self._meter_deferred_resources.get(resource)
                    if previous_budget is None or max_actions_to_resource > previous_budget:
                        self._meter_deferred_resources[resource] = max_actions_to_resource
                        newly_meter_deferred += 1
                if newly_meter_deferred:
                    self._meter_evidence["meter-resource-deferrals"] += newly_meter_deferred
            if self._active_resource is not None:
                self._active_resource = None
                self._active_resource_meter_bound = False
            return None
        _, _, _, _, resource, path = min(routes)
        self._route_deferred_resources.discard(resource)
        self._meter_deferred_resources.pop(resource, None)
        previous_active_resource = self._active_resource
        self._active_resource = resource
        if meter_bounded:
            self._active_resource_meter_bound = True
        elif resource != previous_active_resource:
            self._active_resource_meter_bound = False
        reasoning: dict[str, Any] = {
            "policy": "novelty-explorer-v5",
            "kind": "tile-resource-navigation",
            "target": list(resource),
            "goal": list(goal),
            "learned_blocked_tiles": len(blocked),
        }
        if max_actions_to_resource is not None:
            reasoning["meter_budget_actions"] = max_actions_to_resource
            self._meter_evidence["meter-bounded-resource-actions"] += 1
        return ActionProposal(path[0], reasoning=reasoning)

    def _token_proposal(
        self, view: TileMazeView, *, entered_control: bool = False
    ) -> ActionProposal | None:
        """Navigate a visually matched badge/control/target relation.

        Each entered compact control is classified from the next badge frame:
        it may change orientation, palette appearance, neither, or both. A
        control is revisited only while its observed effect addresses a still
        open visual difference; otherwise another visible control is sampled.
        No palette ID, control identity, or fixed press count is assumed.
        """
        target = self._token_target(view)
        if target is None:
            return None
        self._record_control_entry(target, entered_control)

        needs_adjustment = (
            target.quarter_turns > 0 or target.appearance_mismatches > 0
        )
        control = self._token_control
        if needs_adjustment and control is None:
            control = self._select_token_control(view, target)
        if (
            needs_adjustment
            and control is not None
            and view.avatar == control
            and not self._control_needs_reentry(control, target)
        ):
            self._retired_controls.add(control)
            self._token_control = None
            self._bounce_return = None
            control = self._select_token_control(view, target)

        # A framed ring is treated as a one-use visual resource. Before an
        # unaligned token reaches its control, try the nearest one. Thereafter
        # retain route-neutral rings, plus a reachable detour only when the
        # independently learned bottom meter cannot cover the visible
        # control-to-target leg. An initially speculative resource route is
        # immediately upgraded to that same bounded contract once repeated
        # meter ticks establish an action estimate; it must not walk past a
        # newly learned deadline merely because it started one frame earlier.
        if self._active_resource is not None:
            meter_budget = self._meter_actions_remaining()
            if meter_budget is not None:
                self._active_resource_meter_bound = True
            if self._active_resource_meter_bound and meter_budget is None:
                # A visual meter route must not silently become unbounded if
                # its geometry disappears during an animation or modal state.
                self._meter_evidence["meter-bound-route-lost-estimate"] += 1
                self._active_resource = None
                self._active_resource_meter_bound = False
            else:
                proposal = self._resource_proposal(
                    view,
                    goal=target.coordinate,
                    require_goal_neutral_route=False,
                    max_actions_to_resource=meter_budget,
                )
                if proposal is not None:
                    return proposal
        elif needs_adjustment and not self._used_resources:
            proposal = self._resource_proposal(
                view,
                goal=target.coordinate,
                require_goal_neutral_route=False,
            )
            if proposal is not None:
                return proposal
        elif needs_adjustment and control is not None:
            # Once a first ring has been reached, a remaining one may still be
            # useful before a newly selected control. Preserve route efficiency:
            # only visit it when the current learned A* path can pass through
            # the ring without becoming longer than going to that control.
            proposal = self._resource_proposal(
                view,
                goal=control,
                require_goal_neutral_route=True,
            )
            if proposal is not None:
                return proposal
            # A longer meter-bounded diversion is reserved for a *new* control
            # after another compact control has visibly changed the token and
            # been retired. This preserves direct probing and repeated use of a
            # single effective control; extra route length is spent only on a
            # demonstrated multi-stage relation.
            has_staged_control_feedback = (
                bool(self._retired_controls)
                and control not in self._retired_controls
                and any(
                    changes_turns or changes_appearance
                    for changes_turns, changes_appearance in self._control_effects.values()
                )
            )
            meter_budget = (
                self._resource_is_urgent_before_control(view, target, control)
                if has_staged_control_feedback
                else None
            )
            if meter_budget is not None:
                proposal = self._resource_proposal(
                    view,
                    goal=control,
                    require_goal_neutral_route=False,
                    max_actions_to_resource=meter_budget,
                )
                if proposal is not None:
                    return proposal

        if self._bounce_return is not None and control is not None:
            action = self._bounce_return
            self._bounce_return = None
            return ActionProposal(
                action,
                reasoning={
                    "policy": "novelty-explorer-v5",
                    "kind": "tile-badge-control-return",
                    "target": list(control),
                    "token_quarter_turns": target.quarter_turns,
                    "token_appearance_mismatches": target.appearance_mismatches,
                    "control_entries": self._control_entries,
                },
            )

        if needs_adjustment:
            if control is None:
                # All observed controls failed to change an outstanding visual
                # difference. Return control to the graph explorer rather than
                # walking into an explicitly mismatched board target.
                return None
            if view.avatar == control:
                action = self._token_bounce_action(view)
                if action is None:
                    return None
                return ActionProposal(
                    action,
                    reasoning={
                        "policy": "novelty-explorer-v5",
                        "kind": "tile-badge-control-exit",
                        "target": list(control),
                        "token_quarter_turns": target.quarter_turns,
                        "token_appearance_mismatches": target.appearance_mismatches,
                        "control_entries": self._control_entries,
                    },
                )
            destination = control
        else:
            proposal = self._resource_proposal(
                view,
                goal=target.coordinate,
                require_goal_neutral_route=True,
            )
            if proposal is not None:
                return proposal
            destination = target.coordinate

        if view.avatar == destination:
            return None
        path = optimistic_tile_path(view.avatar, destination, view.shape, self._known_blocked(view))
        if not path:
            return None
        return ActionProposal(
            path[0],
            reasoning={
                "policy": "novelty-explorer-v5",
                "kind": "tile-badge-navigation",
                "target": list(destination),
                "token_quarter_turns": target.quarter_turns,
                "token_appearance_mismatches": target.appearance_mismatches,
                "control_entries": self._control_entries,
                "learned_blocked_tiles": len(self._known_blocked(view)),
            },
        )

    def choose(self, snapshot: Snapshot) -> ActionProposal | None:
        """Return one legal tile-navigation action, or ``None`` to use graph fallback."""
        view = tile_maze_view(snapshot)
        if view is None:
            # Most ARC games are not tile mazes. A rejected view is eligible
            # for one-frame continuity only after the *last accepted* tile view
            # independently established the stored token target. Otherwise
            # silently clear any partial maze state rather than alternately
            # creating grace and reset evidence on every unrelated frame.
            if not self._has_verified_token_relation():
                self._clear_local_navigation()
                return None
            self._view_misses += 1
            # A one-frame animation can temporarily hide the strict avatar or
            # badge geometry. Yield to the graph explorer for that one frame,
            # but preserve the verified relation so a normal next frame does
            # not restart the entire control plan. Two consecutive misses are
            # treated as a genuine modal/layout change.
            self._last_avatar = None
            self._last_action = None
            self._last_view = None
            if self._view_misses >= 2:
                self.reset(reason="view-rejected")
            else:
                self._token_evidence["view-grace-observations"] += 1
            return None
        self._view_misses = 0
        if self._levels_completed is not None and snapshot.levels_completed != self._levels_completed:
            self.reset(reason="level-changed")
        self._levels_completed = snapshot.levels_completed
        self._observe_bottom_meter(snapshot)
        entered_control = False
        if (
            self._token_control is not None
            and self._last_avatar is not None
            and self._last_action is not None
        ):
            dx, dy = MAZE_DIRECTION_DELTAS[self._last_action]
            entered_control = (
                view.avatar == self._token_control
                and (self._last_avatar[0] + dx, self._last_avatar[1] + dy) == self._token_control
            )
        self._observe_avatar(view)
        self._observe_resource_arrival(view)

        token_proposal = self._token_proposal(view, entered_control=entered_control)
        if token_proposal is not None:
            self._record_maze_action(view, token_proposal.name)
            return token_proposal

        # A decorative goal halo may span several tiles. Only its chosen centre
        # counts as reached: accepting any halo tile prematurely abandons the
        # final move into an enterable target.
        if self._active is not None and view.avatar == self._active[0]:
            self._visited.add(self._active[0])
            self._active = None

        active = self._active
        guards = self._confirmed_terminal_tiles()
        path: tuple[str, ...] | None = None
        if active is not None:
            guarded_blocked = self._known_blocked(view)
            path = optimistic_tile_path(view.avatar, active[0], view.shape, guarded_blocked)
            if path is None:
                # A previously planned route became impassable only because of
                # a confirmed death landing; count the diversion so a run can
                # distinguish "no route exists" from "route avoided on purpose".
                if (
                    guards
                    and optimistic_tile_path(
                        view.avatar,
                        active[0],
                        view.shape,
                        guarded_blocked - guards,
                    )
                    is not None
                ):
                    self._token_evidence["terminal-landing-diverted"] += 1
                self._active = None

        if self._active is None:
            guarded_blocked = self._known_blocked(view)
            naive_blocked = guarded_blocked - guards if guards else guarded_blocked
            candidates: list[tuple[int, int, int, Coordinate, frozenset[Coordinate], tuple[str, ...]]] = []
            for representative, cells in self._interior_landmarks(view):
                if representative in self._visited or view.avatar in cells:
                    continue
                candidate_path = optimistic_tile_path(
                    view.avatar,
                    representative,
                    view.shape,
                    guarded_blocked,
                )
                if guards:
                    naive_path = optimistic_tile_path(
                        view.avatar,
                        representative,
                        view.shape,
                        naive_blocked,
                    )
                    if naive_path is not None and (
                        candidate_path is None or naive_path[0] != candidate_path[0]
                    ):
                        self._token_evidence["terminal-landing-rerouted"] += 1
                if candidate_path is None:
                    continue
                candidates.append(
                    (
                        len(candidate_path),
                        abs(view.avatar[0] - representative[0]) + abs(view.avatar[1] - representative[1]),
                        representative[1],
                        representative,
                        cells,
                        candidate_path,
                    )
                )
            if not candidates:
                self._record_maze_action(view, None)
                return None
            _, _, _, representative, cells, path = min(candidates)
            self._active = (representative, cells)

        if not path:
            # A target that became the current tile is handled on the next
            # observation; do not invent an action merely to make progress.
            self._record_maze_action(view, None)
            return None
        action = path[0]
        self._record_maze_action(view, action)
        return ActionProposal(
            action,
            reasoning={
                "policy": "novelty-explorer-v5",
                "kind": "tile-maze-navigation",
                "target": list(self._active[0]) if self._active is not None else [],
                "path_length": len(path),
                "learned_blocked_tiles": len(self._known_blocked(view)),
            },
        )


@dataclass(frozen=True)
class Transition:
    """Observed result of one state-action transition."""

    changed: bool
    level_gain: int
    game_over: bool
    revisit: bool


@dataclass
class GraphEdge:
    """A deterministic action edge discovered between semantic game states."""

    proposal: ActionProposal
    successor: str | None = None
    transition: Transition | None = None


@dataclass
class StateNode:
    """Lazily generated action frontier for one semantic game state."""

    actions: tuple[ActionProposal, ...]
    # Discovery depth supplies a stable, low-action-cost traversal order when
    # several graph frontiers are reachable from the current observation.
    depth: int = 0
    tried: set[str] = field(default_factory=set)


class ExplorerPolicy:
    """Deterministic frontier explorer over visually canonicalized states.

    The policy records every attempted state-action edge before observing its
    result. A strict visual tile-maze recognizer gets first use of directional
    controls and learns collision cells online. Otherwise fresh directional
    successors test their protocol inverse first; thereafter the graph follows
    known edges to the shallowest reachable frontier. This avoids mistaking a
    ticking HUD for useful progress, walking an entire corridor before testing
    sibling moves, and repeating one movement that merely changes a status bar.
    """

    def __init__(self) -> None:
        self._previous: Snapshot | None = None
        self._previous_signature: str | None = None
        self._previous_excluded: frozenset[Coordinate] = frozenset()
        self._pending: ActionProposal | None = None
        self._last_transition: Transition | None = None
        self._state_visits: Counter[str] = Counter()
        self._global_stats: dict[str, ActionStats] = defaultdict(ActionStats)
        self._state_stats: dict[tuple[str, str], ActionStats] = defaultdict(ActionStats)
        self._nodes: dict[str, StateNode] = {}
        self._edges: dict[tuple[str, str], GraphEdge] = {}
        self._transition_trace: list[dict[str, Any]] = []
        self._tile_maze = TileMazeNavigator()

    def diagnostics(self) -> dict[str, dict[str, int]]:
        """Return compact, serializable aggregate evidence for a replay."""
        return {
            action: {
                "attempts": stats.attempts,
                "changed": stats.changed,
                "level_gains": stats.level_gains,
                "game_overs": stats.game_overs,
                "revisits": stats.revisits,
            }
            for action, stats in sorted(self._global_stats.items())
        }

    def transition_trace(self, limit: int = 80) -> list[dict[str, Any]]:
        """Return recent action/outcome evidence without retaining grid pixels."""
        if limit < 1:
            return []
        return [dict(entry) for entry in self._transition_trace[-limit:]]

    def decision_evidence(self) -> dict[str, int]:
        """Count bounded policy modes across the completed replay.

        This deliberately exposes only policy-owned mode labels and a boolean
        meter-routing flag, never frame data, coordinates, or arbitrary
        free-form reasoning. It lets a public evaluation distinguish an
        unexercised route from an exercised route that did not score.
        """
        counts: Counter[str] = Counter()
        for entry in self._transition_trace:
            kind = entry.get("decision_kind", "unspecified")
            if isinstance(kind, str):
                counts[kind] += 1
            if entry.get("meter_bounded_resource"):
                counts["meter-bounded-resource"] += 1
        return dict(sorted(counts.items()))

    def meter_evidence(self) -> dict[str, int]:
        """Expose palette-free bottom-meter observation counts for a run report."""
        return self._tile_maze.meter_evidence()

    def token_evidence(self) -> dict[str, int]:
        """Expose coordinate-free visual-control outcome counts for a run report."""
        return self._tile_maze.token_evidence()

    def finalize(self, snapshot: Snapshot) -> None:
        """Account for a final environment response when no next action is due.

        Framework loops stop immediately on a win or an action budget, leaving
        the final step without a subsequent ``choose`` call. The local runner
        invokes this method solely for accurate diagnostics; it never proposes
        or executes another action.
        """
        if self._pending is None:
            return
        excluded = horizontal_hud_mask(snapshot)
        signature = masked_signature(snapshot, excluded)
        self._observe_transition(snapshot, signature, excluded)
        self._pending = None

    def _observe_transition(
        self,
        current: Snapshot,
        signature: str,
        excluded: frozenset[Coordinate],
    ) -> set[Coordinate]:
        changed: set[Coordinate] = set()
        self._last_transition = None
        if self._previous is None or self._pending is None or self._previous_signature is None:
            return changed

        changed = changed_coordinates(
            self._previous.planes,
            current.planes,
            set(excluded | self._previous_excluded),
        )
        level_gain = current.levels_completed - self._previous.levels_completed
        transition = Transition(
            changed=bool(changed) or level_gain > 0,
            level_gain=max(0, level_gain),
            game_over=current.state == "GAME_OVER",
            revisit=self._state_visits[signature] > 0,
        )
        self._last_transition = transition
        self._global_stats[self._pending.name].observe(
            changed=transition.changed,
            level_gain=transition.level_gain,
            game_over=transition.game_over,
            revisit=transition.revisit,
        )
        self._state_stats[(self._previous_signature, self._pending.key)].observe(
            changed=transition.changed,
            level_gain=transition.level_gain,
            game_over=transition.game_over,
            revisit=transition.revisit,
        )
        edge = self._edges.setdefault(
            (self._previous_signature, self._pending.key),
            GraphEdge(proposal=self._pending),
        )
        edge.successor = signature
        edge.transition = transition
        decision_kind = self._pending.reasoning.get("kind", "unspecified")
        # Policy-created labels are intentionally simple identifiers. Avoid
        # passing arbitrary free-form reasoning into reports or artifacts.
        if not (
            isinstance(decision_kind, str)
            and decision_kind
            and len(decision_kind) <= 80
            and all(character.islower() or character.isdigit() or character == "-" for character in decision_kind)
        ):
            decision_kind = "unspecified"
        self._transition_trace.append(
            {
                "action": self._pending.key,
                "decision_kind": decision_kind,
                "meter_bounded_resource": isinstance(
                    self._pending.reasoning.get("meter_budget_actions"), int
                ),
                "changed": transition.changed,
                "level_gain": transition.level_gain,
                "game_over": transition.game_over,
                "revisit": transition.revisit,
                "next_state": current.state,
                "levels_completed": current.levels_completed,
            }
        )
        return changed

    @staticmethod
    def _simple_priority(name: str) -> int:
        if name in DIRECTIONAL_ACTIONS:
            return 80 - DIRECTIONAL_ACTIONS.index(name) * 5
        if name == "ACTION5":
            return 45
        if name == "ACTION7":
            return -80
        return 0

    def _candidate_actions(
        self,
        snapshot: Snapshot,
        changed: set[Coordinate],
        excluded: frozenset[Coordinate],
    ) -> tuple[ActionProposal, ...]:
        """Build a deterministic, finite action frontier for a new node."""
        valid = tuple(action for action in snapshot.available_actions if action != RESET)
        candidates: list[tuple[int, int, str, ActionProposal]] = []

        for action in valid:
            if action == COMPLEX_ACTION:
                continue
            proposal = ActionProposal(
                action,
                reasoning={
                    "policy": "novelty-explorer-v5",
                    "kind": "graph-simple-frontier",
                },
            )
            candidates.append((600 + self._simple_priority(action), 1, action, proposal))

        if COMPLEX_ACTION in valid:
            for salience, (x, y), reason in rank_click_targets(snapshot, changed, excluded):
                proposal = ActionProposal(
                    name=COMPLEX_ACTION,
                    x=x,
                    y=y,
                    reasoning={
                        **reason,
                        "policy": "novelty-explorer-v5",
                        "kind": "graph-click-frontier",
                        "target": [x, y],
                        "salience": salience,
                    },
                )
                # A visually salient component should beat a directional probe;
                # the generic lattice remains a lower-priority fallback.
                candidates.append((200 + salience, 0, proposal.key, proposal))

        candidates.sort(
            key=lambda item: (
                -item[0],
                item[1],
                ACTION_NAMES.index(item[3].name),
                item[3].y if item[3].y is not None else -1,
                item[3].x if item[3].x is not None else -1,
            )
        )
        return tuple(item[3] for item in candidates)

    def _node(
        self,
        snapshot: Snapshot,
        signature: str,
        changed: set[Coordinate],
        excluded: frozenset[Coordinate],
    ) -> StateNode:
        """Get a graph node, prioritising a validated inverse on discovery.

        A move into a previously unseen screen state normally leaves its parent
        with other untried actions.  Probing the protocol inverse first is a
        cheap way to establish the return edge; subsequent choices can then
        navigate to the shallowest remaining frontier rather than committing
        to an arbitrary depth-first walk.
        """
        node = self._nodes.get(signature)
        if node is not None:
            return node

        actions = list(self._candidate_actions(snapshot, changed, excluded))
        parent = self._nodes.get(self._previous_signature or "")
        incoming = self._pending
        transition = self._last_transition
        depth = 0
        if parent is not None and incoming is not None and transition is not None and not transition.game_over:
            depth = parent.depth + 1
            inverse = INVERSE_DIRECTIONAL_ACTION.get(incoming.name)
            if inverse is not None:
                # Keep the policy-generated proposal (and its reasoning) but
                # put the likely return movement ahead of deeper probes.
                actions.sort(key=lambda proposal: proposal.name != inverse)

        node = StateNode(tuple(actions), depth=depth)
        self._nodes[signature] = node
        return node

    @staticmethod
    def _next_untested(node: StateNode) -> ActionProposal | None:
        return next((action for action in node.actions if action.key not in node.tried), None)

    def _route_to(self, start: str, target: str) -> tuple[ActionProposal, ...] | None:
        """Return a shortest safe known directed route, if one exists."""
        if start == target:
            return ()
        queue: deque[str] = deque([start])
        parents: dict[str, tuple[str, GraphEdge]] = {}
        visited = {start}

        while queue:
            state = queue.popleft()
            outgoing = [
                edge
                for (origin, _), edge in self._edges.items()
                if origin == state
                and edge.successor is not None
                and edge.successor not in visited
                and (edge.transition is None or not edge.transition.game_over)
            ]
            for edge in sorted(outgoing, key=lambda candidate: candidate.proposal.key):
                assert edge.successor is not None
                successor = edge.successor
                visited.add(successor)
                parents[successor] = (state, edge)
                if successor == target:
                    route: list[ActionProposal] = []
                    while successor != start:
                        previous, parent_edge = parents[successor]
                        route.append(parent_edge.proposal)
                        successor = previous
                    return tuple(reversed(route))
                queue.append(successor)
        return None

    def _scheduled_frontier(self, current: str) -> ActionProposal | None:
        """Choose the shallowest reachable open node and route toward it.

        Local expansion alone is depth-first: a successful ``ACTION1`` causes
        another ``ACTION1`` at every fresh successor.  Scheduling globally by
        discovery depth keeps inverse-verified routes short and samples all
        sibling directions before spending an entire episode down one branch.
        """
        options: list[tuple[int, int, int, str, tuple[ActionProposal, ...], ActionProposal]] = []
        for state, node in self._nodes.items():
            next_action = self._next_untested(node)
            if next_action is None:
                continue
            route = self._route_to(current, state)
            if route is None:
                continue
            options.append((node.depth, len(node.tried), len(route), state, route, next_action))
        if not options:
            return None
        _, _, _, _, route, next_action = min(options)
        return route[0] if route else next_action

    def choose(self, snapshot: Snapshot) -> ActionProposal:
        """Observe ``snapshot`` and select one legal, systematic probe."""
        excluded = horizontal_hud_mask(snapshot)
        signature = masked_signature(snapshot, excluded)
        changed = self._observe_transition(snapshot, signature, excluded)
        self._state_visits[signature] += 1

        if snapshot.state in {"NOT_PLAYED", "GAME_OVER"}:
            if snapshot.state == "GAME_OVER":
                # Record the explicit fatal landing before the terminal reset
                # forgets episode geometry, so a replay of the same level can
                # avoid repeating the identical death step.
                self._tile_maze.note_terminal_landing(snapshot, tile_maze_view(snapshot))
            self._tile_maze.reset(reason="terminal")
            proposal = ActionProposal(
                RESET,
                reasoning={
                    "policy": "novelty-explorer-v5",
                    "kind": "reset",
                    "state": snapshot.state,
                },
            )
            self._remember(snapshot, signature, excluded, proposal)
            return proposal

        valid = tuple(action for action in snapshot.available_actions if action != RESET)
        if not valid:
            proposal = ActionProposal(
                RESET,
                reasoning={"policy": "novelty-explorer-v5", "kind": "no-valid-actions"},
            )
            self._remember(snapshot, signature, excluded, proposal)
            return proposal

        self._node(snapshot, signature, changed, excluded)
        proposal = self._tile_maze.choose(snapshot)
        if proposal is None:
            proposal = self._scheduled_frontier(signature)
        if proposal is None or proposal.name not in valid:
            # A reset is the deterministic way to revisit a known root when
            # this directed graph has no safe route to another unexplored node.
            proposal = ActionProposal(
                RESET,
                reasoning={
                    "policy": "novelty-explorer-v5",
                    "kind": "frontier-reset",
                    "state_visits": self._state_visits[signature],
                },
            )

        self._remember(snapshot, signature, excluded, proposal)
        return proposal

    def _remember(
        self,
        snapshot: Snapshot,
        signature: str,
        excluded: frozenset[Coordinate],
        proposal: ActionProposal,
    ) -> None:
        # Mark an edge before execution. A reset or terminal response can end a
        # loop before another observation, and must not make this edge appear
        # untested on the next visit.
        node = self._nodes.get(signature)
        if node is not None:
            node.tried.add(proposal.key)
        self._edges.setdefault((signature, proposal.key), GraphEdge(proposal=proposal))
        self._previous = snapshot
        self._previous_signature = signature
        self._previous_excluded = excluded
        self._pending = proposal
