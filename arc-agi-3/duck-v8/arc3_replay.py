"""ARC3 v8: solved-level replay (episodic memory of level solutions).

Rationale: the ARC-AGI-3 score per level is min(115, (baseline/actions)^2*100).
The stock Duck agent re-derives every level from scratch whenever it re-enters
it (game-over restart, analyzer session reset, a second pass over the same
game), and its session knowledge is wiped at level changes. Every re-derivation
burns shared server throughput (the real bottleneck: ~36k tok/min aggregate)
and inflates the action count A, which enters the score SQUARED.

This module is the pure-logic core of a record/replay layer:

* While the agent plays, each completed level is recorded as
  (game_id, level) -> {start_hash, actions, end_hash}, where hashes are
  frame fingerprints taken before the first / after the last action of the
  level segment. Only the SHORTEST verified sequence per (game, level) is
  kept.
* When the agent (re-)enters a level whose start hash matches a recorded
  solution, the wiring replays the recorded actions directly through the
  env callback - no model calls - verifying the frame hash after every
  action. Any mismatch aborts the replay instantly and hands control back
  to the model exactly where it is (never worse than stock behaviour,
  except the small number of replayed actions spent, which the score
  counts but which are required to reach that state anyway).

Env switches (all optional; defaults keep stock behaviour EXACTLY):
  ARC3_REPLAY=1          master switch (default 0 = OFF)
  ARC3_REPLAY_DIR=path   store directory (default /kaggle/working/arc3_replay)
  ARC3_REPLAY_MAX_ACTIONS_PER_LEVEL=N  safety cap per level (default 2000)

Pure logic lives here so it can be unit-tested without the harness
(same pattern as arc3_abandon.py in v7).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Sequence


# --------------------------------------------------------------------------
# Env helpers
# --------------------------------------------------------------------------

def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def replay_enabled() -> bool:
    return _env_bool("ARC3_REPLAY", False)


def replay_dir() -> Path:
    raw = (os.environ.get("ARC3_REPLAY_DIR") or "").strip()
    return Path(raw) if raw else Path("/kaggle/working/arc3_replay")


def max_actions_per_level() -> int:
    return max(1, _env_int("ARC3_REPLAY_MAX_ACTIONS_PER_LEVEL", 2000))


# --------------------------------------------------------------------------
# Frame fingerprinting
# --------------------------------------------------------------------------

def frame_hash(grid: Sequence[Sequence[Any]] | None, *, level: int | None = None) -> str:
    """Stable fingerprint of a frame grid (optionally bound to a level).

    Accepts any nested sequence of scalars (ints/strings). Returns a short
    hex digest. `level` is mixed in so identical boards on different levels
    never alias.
    """
    h = hashlib.sha1()
    h.update(f"level={level};".encode())
    if grid is None:
        h.update(b"none")
        return h.hexdigest()[:16]
    for row in grid:
        h.update(",".join(str(c) for c in row).encode())
        h.update(b"/")
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------
# Level segmentation of a flat (action, before_level, after_hash) stream
# --------------------------------------------------------------------------

def extract_level_segments(
    entries: Iterable[tuple[Any, int, str]],
    initial_hash: str = "",
) -> dict[int, dict[str, Any]]:
    """Split a flat action stream into per-level solution segments.

    `entries` yields (action, level_before_action, frame_hash_after_action)
    in execution order for ONE game run. A level segment closes when the
    next action starts on a different level (level completed) or the stream
    ends while still on that level (segment incomplete -> not returned
    unless it is closed by a level change).

    Returns {level: {"actions": [...], "step_hashes": [...],
    "start_hash": str, "end_hash": str, "complete": bool}}.
    Only segments closed by a level-up are marked complete=True; the final
    open segment is included with complete=False so callers can ignore it.
    `initial_hash` is the frame hash before the very first action.
    """
    segments: dict[int, dict[str, Any]] = {}
    current_level: int | None = None
    current_actions: list[Any] = []
    current_hashes: list[str] = []
    current_start: str = initial_hash
    current_end: str = ""
    last_hash: str = initial_hash

    def _flush(complete: bool) -> None:
        nonlocal current_actions, current_hashes
        if current_level is None or not current_actions:
            return
        prev = segments.get(current_level)
        seg = {
            "actions": list(current_actions),
            "step_hashes": list(current_hashes),
            "start_hash": current_start,
            "end_hash": current_end,
            "complete": complete,
        }
        # Keep the shortest complete segment seen for a level.
        if prev is None or (complete and not prev.get("complete")) or (
            complete == bool(prev.get("complete"))
            and len(seg["actions"]) < len(prev["actions"])
        ):
            segments[current_level] = seg
        current_actions = []
        current_hashes = []

    for action, level_before, hash_after in entries:
        if current_level is None:
            current_level = level_before
            current_start = last_hash
        elif level_before != current_level:
            _flush(complete=True)
            current_level = level_before
            current_start = last_hash
        current_actions.append(action)
        current_hashes.append(hash_after)
        current_end = hash_after
        last_hash = hash_after
    _flush(complete=False)
    return segments


# --------------------------------------------------------------------------
# Persistent solution store (JSONL, append + shortest-wins merge on read)
# --------------------------------------------------------------------------

class SolutionStore:
    """Append-only JSONL store of verified level solutions.

    One file per game (<game_id>.jsonl) inside `directory`. Safe for the
    harness layout (one analyzer process per game); concurrent writers for
    the same game (duplicate passes) are handled by atomic appends and a
    shortest-verified-wins merge at read time.
    """

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def _path(self, game_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(game_id))
        return self.directory / f"{safe}.jsonl"

    def record(
        self,
        game_id: str,
        level: int,
        *,
        start_hash: str,
        actions: Sequence[Any],
        end_hash: str,
        step_hashes: Sequence[str] | None = None,
    ) -> bool:
        """Persist a COMPLETED level solution. Returns True if written."""
        if not actions or len(actions) > max_actions_per_level():
            return False
        existing = self.best(game_id, level)
        if existing is not None and len(existing["actions"]) <= len(actions):
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        row = {
            "game": str(game_id),
            "level": int(level),
            "start_hash": str(start_hash),
            "actions": list(actions),
            "end_hash": str(end_hash),
            "step_hashes": [str(h) for h in step_hashes] if step_hashes else [],
        }
        with open(self._path(game_id), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return True

    def best(self, game_id: str, level: int) -> dict[str, Any] | None:
        """Shortest recorded solution for (game, level), or None."""
        path = self._path(game_id)
        if not path.exists():
            return None
        best_row: dict[str, Any] | None = None
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if int(row.get("level", -1)) != int(level):
                continue
            if best_row is None or len(row.get("actions") or []) < len(best_row.get("actions") or []):
                best_row = row
        return best_row

    def levels(self, game_id: str) -> list[int]:
        """Sorted levels with a recorded solution for a game."""
        path = self._path(game_id)
        if not path.exists():
            return []
        found: set[int] = set()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, AttributeError):
                continue
            if isinstance(row, dict) and "level" in row:
                found.add(int(row["level"]))
        return sorted(found)


# --------------------------------------------------------------------------
# Replay planning / verification (pure; the wiring executes the plan)
# --------------------------------------------------------------------------

def plan_replay(
    store: SolutionStore,
    game_id: str,
    current_level: int,
    current_hash: str,
) -> dict[str, Any] | None:
    """Return the replay plan for the level the agent is about to play.

    A plan applies only when a recorded solution exists for
    (game_id, current_level) AND its start_hash equals the hash of the
    frame the agent currently faces. Otherwise None (model plays).
    """
    sol = store.best(game_id, current_level)
    if sol is None:
        return None
    if str(sol.get("start_hash")) != str(current_hash):
        return None
    actions = list(sol.get("actions") or [])
    if not actions or len(actions) > max_actions_per_level():
        return None
    step_hashes = [str(h) for h in (sol.get("step_hashes") or [])]
    if step_hashes and len(step_hashes) != len(actions):
        step_hashes = []  # legacy row without a trustworthy chain
    return {
        "game": str(game_id),
        "level": int(current_level),
        "actions": actions,
        "step_hashes": step_hashes,
        "expected_end_hash": str(sol.get("end_hash")),
    }


def verify_replay_step(expected_hash: str | None, actual_hash: str) -> bool:
    """Per-step chain check. Frames must match exactly; any drift aborts."""
    if expected_hash is None:
        return True
    return str(expected_hash) == str(actual_hash)
