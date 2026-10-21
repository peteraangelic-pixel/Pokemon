"""Segmentation + object-aware click candidates for ARC-AGI-3.

This is the Python mirror of `arc-agi-3/rust/src/grid.rs::segment_layer`
(4-connected same-colour components, with contour boundary and containment).
It exists for two reasons:

1. **Fallback** — `rust_bridge.py` uses the Rust binary when it is built and this
   module when it is not, so the solver never depends on a cargo toolchain.
2. **Validation** — the Rust kernel is documented as "byte-identical output" to
   the Python one; keeping both makes that claim testable.

The valuable output for search is `click_candidates()`: instead of throwing darts
at random non-background pixels (what `solver.py` did first), propose *object
centroids and contour pixels*. That is what makes click-only games tractable —
and it is precisely the kernel Rust makes 200-400x cheaper.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass(frozen=True)
class Component:
    id: int
    value: int
    pixels: int
    r0: int
    c0: int
    r1: int
    c1: int
    boundary: tuple[tuple[int, int], ...]

    @property
    def centroid(self) -> tuple[int, int]:
        # bbox centre: cheaper than a true centroid and a better click target,
        # because clicks land on a cell and object interiors are uniform.
        return ((self.c0 + self.c1) // 2, (self.r0 + self.r1) // 2)

    @property
    def area(self) -> int:
        return (self.r1 - self.r0 + 1) * (self.c1 - self.c0 + 1)


def segment(grid: np.ndarray) -> list[Component]:
    """4-connected same-colour components, in reading order (matches Rust)."""
    g = np.asarray(grid)
    h, w = g.shape
    seen = np.zeros((h, w), dtype=bool)
    comps: list[Component] = []

    for sr in range(h):
        for sc in range(w):
            if seen[sr, sc]:
                continue
            value = int(g[sr, sc])
            cells: list[tuple[int, int]] = []
            q = deque([(sr, sc)])
            seen[sr, sc] = True
            while q:
                r, c = q.popleft()
                cells.append((r, c))
                for dr, dc in ORTH:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and not seen[nr, nc] and int(g[nr, nc]) == value:
                        seen[nr, nc] = True
                        q.append((nr, nc))

            rs = [p[0] for p in cells]
            cs = [p[1] for p in cells]
            boundary = []
            cell_set = set(cells)
            for (r, c) in cells:
                edge = (
                    r == 0 or c == 0 or r == h - 1 or c == w - 1
                    or (r + 1, c) not in cell_set or (r - 1, c) not in cell_set
                    or (r, c + 1) not in cell_set or (r, c - 1) not in cell_set
                )
                if edge:
                    boundary.append((r, c))
            comps.append(Component(
                id=len(comps), value=value, pixels=len(cells),
                r0=min(rs), c0=min(cs), r1=max(rs), c1=max(cs),
                boundary=tuple(boundary),
            ))
    return comps


def background_value(grid: np.ndarray) -> int:
    flat = np.asarray(grid).ravel()
    return int(np.bincount(flat).argmax())


def click_candidates(
    grid: np.ndarray,
    limit: int = 12,
    include_background: bool = False,
    min_pixels: int = 1,
    order: str = "area_desc",
) -> list[tuple[int, int]]:
    """Object-aware click proposals: centroids first, then contour pixels.

    Rationale: a click-only game reacts to *objects*, so probing every 64x64 cell
    is hopeless (4096 candidates), while probing one point per object is ~10-40.
    """
    g = np.asarray(grid)
    bg = background_value(g)
    comps = segment(g)
    if not include_background:
        comps = [c for c in comps if c.value != bg]
    comps = [c for c in comps if c.pixels >= min_pixels]
    if not comps:
        return []

    if order == "area_desc":
        comps.sort(key=lambda c: -c.pixels)
    elif order == "area_asc":
        comps.sort(key=lambda c: c.pixels)

    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    def push(x: int, y: int) -> None:
        if 0 <= x < g.shape[1] and 0 <= y < g.shape[0] and (x, y) not in seen:
            seen.add((x, y))
            out.append((x, y))

    for c in comps:                      # pass 1: one click per object
        x, y = c.centroid
        push(x, y)
        if len(out) >= limit:
            return out
    for c in comps:                      # pass 2: contour extremes
        for (r, cc) in (c.boundary[0], c.boundary[len(c.boundary) // 2], c.boundary[-1]):
            push(cc, r)
            if len(out) >= limit:
                return out
    return out


def describe(grid: np.ndarray, top: int = 8) -> str:
    """Human-readable summary, useful in solver logs."""
    comps = segment(grid)
    bg = background_value(grid)
    objs = sorted((c for c in comps if c.value != bg), key=lambda c: -c.pixels)[:top]
    return (f"bg={bg} components={len(comps)} objects={len(comps) - 1 if comps else 0} "
            f"top={[(c.value, c.pixels, c.centroid) for c in objs]}")
