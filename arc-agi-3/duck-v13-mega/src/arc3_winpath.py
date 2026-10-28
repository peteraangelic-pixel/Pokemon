"""ARC3 Duck v13, patch 0006: win-path memory + deterministic replay.

Problem (measured on this harness): a run plays every game for n_passes
passes, and every pass starts the game from zero. The world model is wiped
between passes (`ensure_session` restarts the analyzer), so a level the
agent already solved in pass 1 is re-derived from scratch in passes 2..20:
fresh exploration, fresh tokens, and - because RHAE is quadratic in the
action count - a fresh pile of wasted actions on every repeat. The same
waste happens inside one pass after a game-over reset.

Fix: remember, per (game, level), the exact action sequence that completed
the level, verified frame-by-frame. On any later entry into that level
(fresh pass, post-reset retry), replay the stored sequence directly
through `_execute_action` with `generated_tokens=0`: no analyzer call, and
the action count is the short recorded path instead of a new exploration.
Every replayed action still goes through the normal execution path, so it
is counted exactly like any other action - this saves tokens and time,
and replaces re-exploration actions with the known-short path.

Safety: replay is verified against the recorded grid-hash chain (initial
grid + grid after every action). The first mismatch, an unavailable
action, a game-over, or an exception aborts the replay immediately and
the LLM plays the level from the current position as usual; the aborted
prefix stays in the attempt buffer, so if the LLM finishes the level, the
completed (longer but valid) sequence replaces the broken one. A level
whose replay fails 3 times is never replayed again. With ARC3_WINPATH
unset the module is completely inert.

Offline seed: if `playbook.json` sits in the win-path dir (written by the
notebook from offline BFS/beam sweeps of the public games, every sequence
re-validated against the real game code), its levels are merged into the
store under the same verification rules. Game-id matching is tolerant
(exact, else alphanumeric prefix match), because gateway ids may carry
suffixes.

Dead-game skip (ARC3_DEAD_SKIP=1): a game that finished >=3 earlier
passes with zero completed levels stops consuming full passes: sessions
with pass_index >= ARC3_DEAD_MIN_PASS (default 4) exit immediately, so
the serving slots go to games that are still making progress.

Env switches (all optional):
  ARC3_WINPATH=1          master switch (default 0 = stock behaviour)
  ARC3_WINPATH_REPLAY=1   replay stored paths (default 1; 0 = record only)
  ARC3_WINPATH_DIR        store dir (default /kaggle/working/arc3_winpath,
                          falls back to the system temp dir)
  ARC3_DEAD_SKIP=1        enable the dead-game pass skip (default 0)
  ARC3_DEAD_MIN_PASS=4    first pass index eligible for skipping
  ARC3_DEAD_MIN_PASSES=3  completed zero-level passes required to skip
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

MAX_REPLAY_ACTIONS = 1000
MAX_LEVEL_FAILS = 3

_SESSIONS: dict[int, "_SessionState"] = {}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def enabled() -> bool:
    return os.environ.get("ARC3_WINPATH", "0") == "1"


def replay_enabled() -> bool:
    return enabled() and os.environ.get("ARC3_WINPATH_REPLAY", "1") != "0"


def winpath_dir() -> Path:
    candidates = []
    raw = os.environ.get("ARC3_WINPATH_DIR", "").strip()
    if raw:
        candidates.append(raw)
    candidates.append("/kaggle/working/arc3_winpath")
    candidates.append(str(Path(tempfile.gettempdir()) / "arc3_winpath"))
    for cand in candidates:
        try:
            path = Path(cand)
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".wp_probe"
            probe.write_text("1")
            probe.unlink()
            return path
        except Exception:
            continue
    return Path(tempfile.gettempdir())


def _sanitize(game_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", game_id)[:80] or "game"


def _norm(game_id: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(game_id).lower())


def _grid_of(state) -> tuple:
    if state is None:
        return ()
    data = state.frame.data
    rows = data.tolist() if hasattr(data, "tolist") else data
    rows = list(rows)
    # Peel an animation stack (k, H, W) down to its last frame.
    while (rows and isinstance(rows[0], (list, tuple)) and len(rows[0])
           and isinstance(rows[0][0], (list, tuple))):
        rows = list(rows[-1])
    return tuple(tuple(int(c) for c in row) for row in rows)


def grid_key_of_grid(grid: tuple) -> str:
    return hashlib.sha256(repr(grid).encode()).hexdigest()[:16]


def grid_key_of_state(state) -> str:
    return grid_key_of_grid(_grid_of(state))


class _Store:
    """Per-game JSON store: winning sequences + run metadata."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.path = winpath_dir() / (_sanitize(game_id) + ".json")
        self.data = {"game_id": game_id, "best_levels": 0,
                     "passes_completed": 0, "levels": {}}
        self._force: set[str] = set()  # levels (re)recorded by this instance
        self._load()
        self._merge_playbook()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
            if isinstance(raw, dict) and isinstance(raw.get("levels"), dict):
                self.data.update({k: raw[k] for k in
                                  ("best_levels", "passes_completed", "levels")
                                  if k in raw})
        except Exception:
            pass

    def _merge_playbook(self) -> None:
        try:
            book = json.loads((self.path.parent / "playbook.json").read_text())
            games = book.get("games", {}) if isinstance(book, dict) else {}
            mine = _norm(self.game_id)
            match = None
            for key, val in games.items():
                other = _norm(key)
                if other and (other == mine or
                              (len(other) >= 3 and mine.startswith(other)) or
                              (len(mine) >= 3 and other.startswith(mine))):
                    match = val
                    break
            if match:
                for lvl, entry in (match.get("levels") or {}).items():
                    self.data["levels"].setdefault(str(lvl), dict(entry))
        except Exception:
            pass

    def save(self) -> None:
        try:
            # Merge with whatever is on disk now: concurrent sessions of the
            # same game must not clobber each other's levels.
            disk = {}
            try:
                disk = json.loads(self.path.read_text())
            except Exception:
                disk = {}
            if isinstance(disk, dict) and isinstance(disk.get("levels"), dict):
                merged = dict(disk["levels"])
                for lvl, entry in self.data["levels"].items():
                    if lvl in self._force or lvl not in merged \
                            or merged[lvl].get("src") != "run":
                        merged[lvl] = entry
                    elif entry.get("src") == "run":
                        # Another session's recorded path stays, but a fail
                        # counted here must never be lost.
                        merged[lvl] = {**merged[lvl], "fails": max(
                            int(merged[lvl].get("fails", 0)),
                            int(entry.get("fails", 0)))}
                self.data["levels"] = merged
                self.data["best_levels"] = max(
                    int(disk.get("best_levels", 0)), int(self.data["best_levels"]))
                self.data["passes_completed"] = max(
                    int(disk.get("passes_completed", 0)),
                    int(self.data["passes_completed"]))
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data))
            os.replace(tmp, self.path)
        except Exception:
            pass

    def record_level(self, level: int, actions: list, init: str,
                     hashes: list) -> None:
        self._force.add(str(level))
        self.data["levels"][str(level)] = {
            "actions": actions, "init": init, "hashes": hashes,
            "n": len(actions), "src": "run", "fails": 0,
        }
        self.data["best_levels"] = max(int(self.data["best_levels"]), level + 1)
        self.save()

    def note_fail(self, level: int) -> None:
        entry = self.data["levels"].get(str(level))
        if entry is not None:
            entry["fails"] = int(entry.get("fails", 0)) + 1
            self.save()


class _SessionState:
    def __init__(self, game_id: str) -> None:
        self.store = _Store(game_id)
        self.bufs: dict[int, dict] = {}
        self.broken: set[int] = set()
        self.max_levels = 0


def _game_id_of(session) -> str:
    try:
        gid = getattr(getattr(session.game, "game_run", None), "game_id", "")
        if gid:
            return str(gid)
    except Exception:
        pass
    return f"game_{getattr(session, 'game_index', 0)}"


def begin_session(session) -> None:
    if not enabled():
        return
    _SESSIONS[id(session)] = _SessionState(_game_id_of(session))


def end_session(session) -> None:
    state = _SESSIONS.pop(id(session), None)
    if state is None:
        return
    try:
        data = state.store.data
        data["passes_completed"] = int(data.get("passes_completed", 0)) + 1
        try:
            current = int(session.game.current_state.levels_completed)
        except Exception:
            current = 0
        data["best_levels"] = max(int(data.get("best_levels", 0)),
                                  state.max_levels, current)
        state.store.save()
    except Exception:
        pass


def record_action(session, *, action_name: str, action_data: dict,
                  previous_completed: int, previous_grid: tuple,
                  new_state, payload: dict) -> None:
    """Hook called from _execute_action after every executed action."""
    state = _SESSIONS.get(id(session))
    if state is None:
        return
    if action_name == "RESET":
        state.bufs.clear()
        return
    level = int(previous_completed)
    buf = state.bufs.get(level)
    if buf is None:
        buf = {"init": grid_key_of_grid(previous_grid), "actions": [],
               "hashes": []}
        state.bufs[level] = buf
    buf["actions"].append({"name": action_name, "data": dict(action_data or {})})
    buf["hashes"].append(grid_key_of_state(new_state))
    try:
        levels_now = int(new_state.levels_completed)
    except Exception:
        levels_now = level
    state.max_levels = max(state.max_levels, levels_now)
    if payload.get("game_over"):
        state.bufs.pop(level, None)
    elif levels_now > level:
        state.store.record_level(level, list(buf["actions"]), buf["init"],
                                 list(buf["hashes"]))
        state.bufs.pop(level, None)


def _fail(state: _SessionState, level: int, count: bool) -> None:
    state.broken.add(level)
    if count:
        state.store.note_fail(level)


def maybe_replay(session) -> bool:
    """Execute a stored winning sequence for the current level, if any.

    Returns True when the call consumed the turn (replayed at least one
    action, or completed/aborted a replay), False to play normally.
    """
    if not replay_enabled():
        return False
    state = _SESSIONS.get(id(session))
    if state is None:
        return False
    try:
        return _replay_once(session, state)
    except Exception:
        return False


def _replay_once(session, state: _SessionState) -> bool:
    import arcengine

    game_state = session.game.current_state
    level = int(game_state.levels_completed)
    if level in state.broken:
        return False
    buf = state.bufs.get(level)
    if buf and buf["actions"]:
        return False  # an attempt is already in progress on this level
    entry = state.store.data["levels"].get(str(level))
    if not entry:
        return False
    if int(entry.get("fails", 0)) >= MAX_LEVEL_FAILS:
        return False
    actions = entry.get("actions") or []
    if not actions or len(actions) > MAX_REPLAY_ACTIONS:
        return False
    if entry.get("init") and entry["init"] != grid_key_of_state(game_state):
        state.broken.add(level)  # different start: never waste an action
        return False
    hashes = entry.get("hashes") or []
    executed = False
    for index, stored in enumerate(actions):
        if session.should_stop():
            break
        name = stored.get("name", "")
        if name == "RESET":
            break
        try:
            action_id = arcengine.GameAction[name]
        except Exception:
            break
        current = session.game.current_state
        try:
            if action_id.value not in current.available_actions:
                _fail(state, level, executed)
                return executed
        except Exception:
            pass
        payload = session._execute_action(
            arcengine.ActionInput(id=action_id,
                                  data=dict(stored.get("data") or {})),
            batch_index=index + 1, batch_size=len(actions), generated_tokens=0)
        executed = True
        if payload.get("game_over"):
            _fail(state, level, True)
            return True
        if hashes and grid_key_of_state(session.game.current_state) != hashes[index]:
            _fail(state, level, True)
            return True
        if int(session.game.current_state.levels_completed) > level:
            return True  # level completed; recorder already saved the path
    if executed and int(session.game.current_state.levels_completed) <= level:
        _fail(state, level, True)
    return executed


def dead_skip(session) -> bool:
    """True when this session is a late pass of a never-progressing game."""
    if not enabled() or os.environ.get("ARC3_DEAD_SKIP", "0") != "1":
        return False
    state = _SESSIONS.get(id(session))
    if state is None:
        return False
    if int(getattr(session, "pass_index", 0)) < _env_int("ARC3_DEAD_MIN_PASS", 4):
        return False
    data = state.store.data
    return (int(data.get("best_levels", 0)) <= 0
            and int(data.get("passes_completed", 0))
            >= _env_int("ARC3_DEAD_MIN_PASSES", 3))
