"""Create compact, credential-free Markdown sketches from ARC JSONL recordings.

The summary intentionally contains only public grid observations, action labels,
and game IDs. It ignores request headers, service URLs, and free-form reasoning
so it can be attached to a GitHub Actions check for rapid visual regression
review when raw artifact downloads are inconvenient.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

PALETTE = "0123456789ABCDEF"
MAX_SIDE = 64


def _grid_from_frame(frame: Any) -> list[list[int]]:
    """Return the largest valid 2-D plane from a FrameData-style payload."""
    if not isinstance(frame, list) or not frame:
        return []
    planes = frame if isinstance(frame[0], list) and frame[0] and isinstance(frame[0][0], list) else [frame]
    grids: list[list[list[int]]] = []
    for plane in planes:
        if not isinstance(plane, list) or not all(isinstance(row, list) for row in plane):
            continue
        grid: list[list[int]] = []
        for row in plane[:MAX_SIDE]:
            converted: list[int] = []
            for value in row[:MAX_SIDE]:
                try:
                    converted.append(int(value))
                except (TypeError, ValueError):
                    converted.append(-1)
            grid.append(converted)
        grids.append(grid)
    return max(grids, key=lambda grid: sum(len(row) for row in grid), default=[])


def frame_to_text(frame: Any) -> str:
    """Render a palette-indexed plane as deterministic, terminal-safe text."""
    grid = _grid_from_frame(frame)
    if not grid:
        return "<no frame>"
    width = min(MAX_SIDE, max((len(row) for row in grid), default=0))
    lines = []
    for row in grid:
        lines.append(
            "".join(PALETTE[value] if 0 <= value < len(PALETTE) else "?" for value in row).ljust(width, "?")
        )
    return "\n".join(lines)


def striped_avatar_tile(grid: list[list[int]]) -> str:
    """Return a safe coarse coordinate for an opt-in 5×5 striped avatar.

    This mirrors the deliberately strict visual contract used by the pure
    tile-maze navigator, without importing the agent into this standalone
    recorder utility. It is diagnostic metadata only: ``-`` means no matching
    sprite was visible, for example during a full-screen modal transition.
    """
    if len(grid) < 5 or max((len(row) for row in grid), default=0) < 5:
        return "-"
    counts: dict[int, int] = {}
    for row in grid:
        for value in row:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "-"
    background = max(counts, key=lambda value: counts[value])
    candidates: list[tuple[int, int, int]] = []
    for y in range(len(grid) - 4):
        for x in range(max((len(row) for row in grid), default=0) - 4):
            glyph = [row[x : x + 5] for row in grid[y : y + 5]]
            if any(len(row) != 5 or len(set(row)) != 1 for row in glyph):
                continue
            row_colours = [row[0] for row in glyph]
            colours = set(row_colours)
            if len(colours) != 2 or background in colours:
                continue
            if sum(left != right for left, right in zip(row_colours, row_colours[1:])) != 1:
                continue
            candidates.append((sum(counts[colour] for colour in colours), y, x))
    if not candidates:
        return "-"
    _, y, x = min(candidates)
    return f"({x // 5},{y // 5})"


def _events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("data") if isinstance(event, dict) else None
        if isinstance(data, dict) and _grid_from_frame(data.get("frame")):
            events.append(data)
    return events


def _action_label(event: dict[str, Any]) -> str:
    action = event.get("action_input")
    if not isinstance(action, dict):
        return "initial"
    identifier = action.get("id")
    if identifier is None:
        return "initial"
    data = action.get("data")
    if isinstance(data, dict) and "x" in data and "y" in data:
        return f"action {identifier} at ({data['x']}, {data['y']})"
    return f"action {identifier}"


def _policy_mode(event: dict[str, Any]) -> str:
    """Return only a policy-owned mode label, never arbitrary reasoning text."""
    action = event.get("action_input")
    if not isinstance(action, dict):
        return "-"
    reasoning = action.get("reasoning")
    kind = reasoning.get("kind") if isinstance(reasoning, dict) else None
    if not isinstance(kind, str) or not kind or len(kind) > 80:
        return "-"
    if not all(character.islower() or character.isdigit() or character == "-" for character in kind):
        return "-"
    return kind


def _game_id(events: Iterable[dict[str, Any]], fallback: str) -> str:
    for event in events:
        value = event.get("game_id")
        if value:
            return str(value).split("-", 1)[0]
    return fallback


def _changed_geometry(before_frame: Any, after_frame: Any) -> tuple[int, str, int]:
    """Return a compact visual delta for two public frames."""
    before_grid = _grid_from_frame(before_frame)
    after_grid = _grid_from_frame(after_frame)
    width = max(
        max((len(row) for row in before_grid), default=0),
        max((len(row) for row in after_grid), default=0),
    )
    height = max(len(before_grid), len(after_grid))
    changed = []
    for y in range(height):
        for x in range(width):
            old = before_grid[y][x] if y < len(before_grid) and x < len(before_grid[y]) else None
            new = after_grid[y][x] if y < len(after_grid) and x < len(after_grid[y]) else None
            if old != new:
                changed.append((x, y))
    if not changed:
        return 0, "-", 0
    xs, ys = zip(*changed)
    return (
        len(changed),
        f"x={min(xs)}..{max(xs)}, y={min(ys)}..{max(ys)}",
        sum(y < 8 or y >= height - 8 for _, y in changed),
    )


def transition_geometry(events: list[dict[str, Any]], limit: int = 64) -> list[str]:
    """Describe each action's visual delta without repeating full frame data."""
    rows = [
        "",
        "#### Transition geometry",
        "| Step | Submitted action | Changed cells | Bounding box | Edge-band cells | State | Avatar tile |",
        "| ---: | --- | ---: | --- | ---: | --- | --- |",
    ]
    for step, (before, after) in enumerate(zip(events, events[1:]), start=2):
        if step - 1 > limit:
            rows.append(f"| … | remaining {len(events) - limit} transitions omitted | | | | | |")
            break
        changed, bbox, edge = _changed_geometry(before.get("frame"), after.get("frame"))
        rows.append(
            "| {step} | {action} | {count} | `{bbox}` | {edge} | `{state}` | `{avatar}` |".format(
                step=step,
                action=_action_label(after),
                count=changed,
                bbox=bbox,
                edge=edge,
                state=str(after.get("state", "?")).replace("|", "\\|"),
                avatar=striped_avatar_tile(_grid_from_frame(after.get("frame"))),
            )
        )
    return rows


def checkpoint_transition_geometry(
    events: list[dict[str, Any]], *, radius: int = 3, max_rows: int = 72
) -> list[str]:
    """Summarize windows around level/state changes without exposing raw reasoning.

    The regular transition table starts at the beginning of a recording.  These
    small windows make later progress, resets, and the terminal portion visible
    when a fixed-horizon public evaluation runs for hundreds of frames.
    """
    if len(events) < 2:
        return []

    def level(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    markers: dict[int, str] = {}
    progress_anchors: list[int] = []
    state_anchors: list[int] = []
    for after_index in range(1, len(events)):
        before, after = events[after_index - 1], events[after_index]
        changes: list[str] = []
        before_level, after_level = level(before.get("levels_completed")), level(
            after.get("levels_completed")
        )
        if before_level is not None and after_level is not None and before_level != after_level:
            changes.append(f"level {before_level}->{after_level}")
            progress_anchors.append(after_index)
        before_state, after_state = before.get("state"), after.get("state")
        if (
            isinstance(before_state, str)
            and isinstance(after_state, str)
            and before_state != after_state
        ):
            changes.append("state-change")
            state_anchors.append(after_index)
        if changes:
            markers[after_index] = ", ".join(changes)

    # Always include level progress and the latest activity before lower-value
    # state churn. Keep complete windows rather than truncating a random row.
    anchors = [*progress_anchors, len(events) - 1, *state_anchors]
    selected: set[int] = set()
    seen_anchors: set[int] = set()
    omitted_anchors = 0
    for anchor in anchors:
        if anchor in seen_anchors:
            continue
        seen_anchors.add(anchor)
        window = set(range(max(1, anchor - radius), min(len(events), anchor + radius + 1)))
        if len(selected | window) > max_rows:
            omitted_anchors += 1
            continue
        selected.update(window)
    rows = sorted(selected)

    lines = [
        "",
        "#### Checkpoint transition windows",
        "",
        "| Step | Marker | Submitted action | Mode | Changed cells | Bounding box | Edge-band cells | State | Avatar tile |",
        "| ---: | --- | --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    for after_index in rows:
        before, after = events[after_index - 1], events[after_index]
        changed, bounds, edge_band = _changed_geometry(before.get("frame"), after.get("frame"))
        marker = markers.get(after_index, "")
        if after_index == len(events) - 1 and not marker:
            marker = "final-window"
        lines.append(
            "| {step} | {marker} | {action} | {mode} | {changed} | `{bounds}` | {edge_band} | {state} | {avatar} |".format(
                step=after_index + 1,
                marker=marker or "-",
                action=_action_label(after),
                mode=_policy_mode(after),
                changed=changed,
                bounds=bounds,
                edge_band=edge_band,
                state=after.get("state", "-"),
                avatar=striped_avatar_tile(_grid_from_frame(after.get("frame"))),
            )
        )
    if omitted_anchors:
        lines.append(f"| … | {omitted_anchors} checkpoint windows omitted | | | | | | | |")
    return lines


def summarize_paths(paths: Iterable[Path]) -> str:
    """Render first and last observations from each usable recording by game."""
    by_game: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(paths):
        events = _events(path)
        if not events:
            continue
        game = _game_id(events, path.stem)
        # The framework and SDK can both create a recording. Retain the longer
        # trajectory, which is the most informative one for each public game.
        if len(events) > len(by_game.get(game, [])):
            by_game[game] = events

    if not by_game:
        return "## Recorded frame sketches\n\nNo usable frame recording was produced.\n"

    output = [
        "## Recorded frame sketches",
        "",
        "Palette indices are hexadecimal-like glyphs (`0`–`F`); these are first and final public observations.",
    ]
    for game, events in sorted(by_game.items()):
        selected = [("first", events[0])]
        if len(events) > 1:
            selected.append(("final", events[-1]))
        output.extend(["", f"### {game} ({len(events)} recorded frames)"])
        for label, event in selected:
            output.extend(
                [
                    "",
                    f"**{label}** — {_action_label(event)}, state `{event.get('state', '?')}`, levels `{event.get('levels_completed', '?')}`",
                    "```text",
                    frame_to_text(event.get("frame")),
                    "```",
                ]
            )
        output.extend(transition_geometry(events))
        output.extend(checkpoint_transition_geometry(events))
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recordings", type=Path, help="Directory containing JSONL recordings")
    parser.add_argument("--output", type=Path, help="Optional Markdown output path; stdout otherwise")
    args = parser.parse_args()

    summary = summarize_paths(args.recordings.glob("*.jsonl") if args.recordings.is_dir() else ())
    if args.output:
        args.output.write_text(summary, encoding="utf-8")
    else:
        print(summary, end="")


if __name__ == "__main__":
    main()
