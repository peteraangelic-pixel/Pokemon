#!/usr/bin/env python3
"""Multiprocessing wrapper for summarize_recordings.

Przetwarza wiele nagrań JSONL równolegle, co przyspiesza analizę
kilkadziesiąt razy dla dużych zbiorów danych.

Usage:
    python3 summarize_recordings_mp.py recordings_dir --output summary.md
"""

import argparse
import json
import sys
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any

# Importuj funkcje z oryginalnego skryptu
sys.path.insert(0, str(Path(__file__).parent))
from summarize_recordings import _events, _game_id, frame_to_text, transition_geometry, checkpoint_transition_geometry


def process_single_recording(path: Path) -> tuple[str, list[dict[str, Any]]] | None:
    """Przetwórz pojedyncze nagranie JSONL.

    Zwraca tuple (game_id, events) lub None jeśli brak użytecznych danych.
    """
    try:
        events = _events(path)
        if not events:
            return None
        game = _game_id(events, path.stem)
        return (game, events)
    except Exception as e:
        print(f"Warning: Failed to process {path}: {e}", file=sys.stderr)
        return None


def summarize_paths_parallel(paths: list[Path], max_workers: int = None) -> str:
    """Render first and last observations from each usable recording by game.

    Wersja multiprocessing - przetwarza pliki równolegle.
    """
    if max_workers is None:
        max_workers = min(cpu_count(), len(paths))

    print(f"Processing {len(paths)} recordings with {max_workers} workers...", file=sys.stderr)

    # Przetwarzaj równolegle
    with Pool(max_workers) as pool:
        results = pool.map(process_single_recording, paths)

    # Zbierz wyniki
    by_game: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if result is None:
            continue
        game, events = result
        # Retain the longer trajectory
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


def _action_label(event: dict) -> str:
    """Extract action label from event."""
    action = event.get("action", {})
    if isinstance(action, dict):
        return action.get("name", "?")
    return str(action)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recordings", type=Path, help="Directory containing JSONL recordings")
    parser.add_argument("--output", type=Path, help="Optional Markdown output path; stdout otherwise")
    parser.add_argument("--workers", type=int, help="Number of worker processes (default: CPU count)")
    args = parser.parse_args()

    if args.recordings.is_dir():
        paths = list(args.recordings.glob("*.jsonl"))
        summary = summarize_paths_parallel(paths, max_workers=args.workers)
    else:
        summary = "## Recorded frame sketches\n\nNo usable frame recording was produced.\n"

    if args.output:
        args.output.write_text(summary, encoding="utf-8")
        print(f"Summary written to {args.output}", file=sys.stderr)
    else:
        print(summary, end="")


if __name__ == "__main__":
    main()
