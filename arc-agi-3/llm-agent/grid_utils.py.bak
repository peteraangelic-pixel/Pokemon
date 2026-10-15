"""Grid formatting and segmentation utilities for ARC-AGI-3 LLM agent.

Derived from the Duck harness (MIT license, Tufa Labs).
Simplified for use with the ARC-AGI-3-Agents framework.
"""
from __future__ import annotations

import hashlib
from typing import Any, Sequence

# ARC color palette: index -> single-char label
ARC_COLOR_CHARS = "WwgGcBMPRbSYOrNp"
ARC_COLOR_LEGEND = (
    "W=white, w=light gray, g=gray, G=dark gray, c=charcoal, B=black, "
    "M=magenta, P=pink, R=red, b=blue, S=sky blue, Y=yellow, O=orange, "
    "r=dark red, N=light green, p=purple"
)

# ARC color palette: index -> RGB
ARC_COLOR_MAP: dict[int, tuple[int, int, int]] = {
    0: (255, 255, 255), 1: (204, 204, 204), 2: (153, 153, 153),
    3: (102, 102, 102), 4: (51, 51, 51),    5: (0, 0, 0),
    6: (229, 58, 163),  7: (255, 123, 204), 8: (249, 60, 49),
    9: (30, 147, 255),  10: (136, 216, 241), 11: (255, 220, 0),
    12: (255, 133, 27), 13: (146, 18, 49),  14: (79, 204, 48),
    15: (163, 86, 214),
}


def format_grid_ascii(grid: Sequence[Sequence[int]]) -> str:
    """Render a numeric grid as ASCII art using ARC color characters."""
    if not grid:
        return "(empty grid)"
    lines = []
    for row in grid:
        chars = []
        for v in row:
            chars.append(ARC_COLOR_CHARS[max(0, min(15, int(v)))])
        lines.append("".join(chars))
    return "\n".join(lines)


def grid_to_png_bytes(grid: Sequence[Sequence[int]], upscale: int = 4) -> bytes:
    """Render a numeric grid as a PNG image (no PIL dependency — pure bytes)."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return b""
    
    rows = len(grid)
    cols = max((len(r) for r in grid), default=0) if rows else 0
    if rows <= 0 or cols <= 0:
        return b""
    
    image = Image.new("RGB", (cols, rows), ARC_COLOR_MAP[0])
    pixels = image.load()
    for row_idx, row in enumerate(grid):
        for col_idx in range(cols):
            value = row[col_idx] if col_idx < len(row) else 0
            pixels[col_idx, row_idx] = ARC_COLOR_MAP.get(int(value), ARC_COLOR_MAP[0])
    
    if upscale > 1:
        image = image.resize((cols * upscale, rows * upscale), Image.Resampling.NEAREST)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Segmentation (connected-component analysis)
# ---------------------------------------------------------------------------

_ORTH = ((-1, 0), (1, 0), (0, -1), (0, 1))
_CW = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1))
_CW_INDEX = {off: i for i, off in enumerate(_CW)}


def _trace_outer_contour(cells, start):
    """Moore-neighbour trace of outer perimeter, clockwise."""
    if len(cells) == 1:
        return [start]
    contour = [start]
    b = start
    prev = (start[0], start[1] - 1)
    second = None
    for _ in range(8 * len(cells) + 16):
        idx = _CW_INDEX[(prev[0] - b[0], prev[1] - b[1])]
        nxt = None
        for k in range(1, 9):
            off = _CW[(idx + k) % 8]
            cand = (b[0] + off[0], b[1] + off[1])
            if cand in cells:
                nxt = cand
                back = _CW[(idx + k - 1) % 8]
                new_prev = (b[0] + back[0], b[1] + back[1])
                break
        if nxt is None:
            break
        if second is None:
            second = nxt
        elif b == start and nxt == second:
            break
        contour.append(nxt)
        prev, b = new_prev, nxt
    if len(contour) > 1 and contour[-1] == contour[0]:
        contour.pop()
    return contour


def _corner_points(contour):
    """Reduce contour to direction-change points."""
    if len(contour) <= 2:
        return list(contour)
    m = len(contour)
    corners = []
    for i in range(m):
        prev_c, cur, nxt = contour[i - 1], contour[i], contour[(i + 1) % m]
        d_in = (cur[0] - prev_c[0], cur[1] - prev_c[1])
        d_out = (nxt[0] - cur[0], nxt[1] - cur[1])
        if d_in != d_out:
            corners.append(cur)
    return corners


def _object_hash(cells, color):
    """Translation-invariant signature of an object."""
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    norm = sorted((r - min_r, c - min_c) for r, c in cells)
    payload = repr((color, norm)).encode()
    return hashlib.sha1(payload).hexdigest()[:16]


def segment_grid(grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    """Segment a grid into connected components.
    
    Returns dict with:
      - nodes: list of {id, color, hash, pixels, boundary, children}
      - adjacency_list: list of [i, j] pairs
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    if not height or not width:
        return {"nodes": [], "adjacency_list": []}
    
    # Connected components via flood fill
    comp_id = [[-1] * width for _ in range(height)]
    components = []
    
    for sr in range(height):
        for sc in range(width):
            if comp_id[sr][sc] != -1:
                continue
            value = grid[sr][sc]
            cid = len(components)
            cells = set()
            stack = [(sr, sc)]
            while stack:
                r, c = stack.pop()
                if (r, c) in cells:
                    continue
                if 0 <= r < height and 0 <= c < width and grid[r][c] == value and comp_id[r][c] == -1:
                    cells.add((r, c))
                    comp_id[r][c] = cid
                    for dr, dc in _ORTH:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < height and 0 <= nc < width and comp_id[nr][nc] == -1 and grid[nr][nc] == value:
                            stack.append((nr, nc))
            components.append({"value": value, "cells": cells, "start": (sr, sc)})
    
    # Build nodes
    nodes = []
    for cid, comp in enumerate(components):
        color_char = ARC_COLOR_CHARS[max(0, min(15, comp["value"]))]
        obj_hash = _object_hash(comp["cells"], comp["value"])
        contour = _trace_outer_contour(comp["cells"], comp["start"])
        boundary = _corner_points(contour)
        nodes.append({
            "id": cid,
            "color": color_char,
            "hash": obj_hash,
            "pixels": len(comp["cells"]),
            "boundary": [[r, c] for r, c in boundary[:12]],  # limit size
            "children": [],
        })
    
    # Compute containment (children)
    for outer_id, outer_comp in enumerate(components):
        outer_cells = outer_comp["cells"]
        for inner_id, inner_comp in enumerate(components):
            if inner_id == outer_id:
                continue
            # Check if inner is fully enclosed by outer
            inner_cells = inner_comp["cells"]
            if all(any((r + dr, c + dc) in outer_cells for dr, dc in _ORTH)
                   for r, c in inner_cells):
                # Check no path from inner to grid edge without crossing outer
                # Simple check: all neighbors of inner cells are either inner or outer
                is_child = True
                for r, c in inner_cells:
                    for dr, dc in _ORTH:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < height and 0 <= nc < width:
                            if comp_id[nr][nc] != outer_id and comp_id[nr][nc] != inner_id:
                                is_child = False
                                break
                    if not is_child:
                        break
                if is_child:
                    nodes[outer_id]["children"].append(inner_id)
    
    # Compute adjacency
    adj_set = set()
    for r in range(height):
        for c in range(width):
            cid = comp_id[r][c]
            for dr, dc in _ORTH:
                nr, nc = r + dr, c + dc
                if 0 <= nr < height and 0 <= nc < width:
                    nid = comp_id[nr][nc]
                    if cid != nid:
                        pair = (min(cid, nid), max(cid, nid))
                        adj_set.add(pair)
    
    return {
        "nodes": nodes,
        "adjacency_list": sorted(adj_set),
    }


def compact_segmentation_summary(seg: dict, max_nodes: int = 20) -> str:
    """Create a compact text summary of segmentation for LLM context."""
    nodes = seg.get("nodes", [])
    adj = seg.get("adjacency_list", [])
    
    lines = [f"Objects: {len(nodes)}, Adjacencies: {len(adj)}"]
    for node in nodes[:max_nodes]:
        boundary_str = ",".join(f"{r},{c}" for r, c in node["boundary"][:4])
        children_str = f", children=[{','.join(map(str, node['children']))}]" if node["children"] else ""
        lines.append(
            f"  obj#{node['id']}: color={node['color']}, size={node['pixels']}px, "
            f"hash={node['hash'][:8]}, corners=[{boundary_str}]{children_str}"
        )
    if len(nodes) > max_nodes:
        lines.append(f"  ... and {len(nodes) - max_nodes} more objects")
    return "\n".join(lines)
