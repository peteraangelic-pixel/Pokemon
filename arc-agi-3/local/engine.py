"""Local CPU engine harness for ARC-AGI-3 games.

Runs games directly against the local `arcengine` build (no LLM, no network, no
Kaggle). Measured on the reference machine: **0.10 ms per game step**, so a
full episode (~750 actions) costs ~75 ms of CPU. That makes brute-force
rollout search, CEM/ES parameter evolution and offline replay analysis
practical on 16 cores.

Requirements (on the machine that will run it):
    python3.12 -m venv .venv
    .venv/bin/pip install "arc-agi>=0.9.9"

Usage:
    python local/gauntlet.py --games all --rollouts 32 --workers 16
    python local/gauntlet.py --games ls20,vc33 --rollouts 64 --policy heuristic
"""
from __future__ import annotations

import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GAMES_DIR = ROOT / "games" / "environment_files"

# Action ids in arcengine: 1=UP 2=DOWN 3=LEFT 4=RIGHT 5=INTERACT 6=CLICK 7=?
_ACTION_CACHE: dict[int, Any] = {}


def action_for(action_id: int):
    """Return the arcengine GameAction for a numeric action id (1..7)."""
    if action_id not in _ACTION_CACHE:
        from arcengine import GameAction

        _ACTION_CACHE[action_id] = getattr(GameAction, f"ACTION{int(action_id)}")
    return _ACTION_CACHE[action_id]


# ---------------------------------------------------------------------------
# Environment discovery
# ---------------------------------------------------------------------------
def discover_games(games_dir: Path = GAMES_DIR) -> dict[str, Any]:
    """Map short game id -> EnvironmentInfo for every local game."""
    from arc_agi import Arcade, OperationMode

    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(games_dir),
        recordings_dir=str(Path("/tmp") / "arc3-recordings"),
    )
    out = {}
    for info in arcade.get_environments():
        short = info.game_id.split("-")[0]
        out[short] = info
    return out


def make_wrapper(info: Any, seed: int = 0, recordings_dir: str | None = None):
    """Create a fresh LocalEnvironmentWrapper (no recording by default)."""
    from arc_agi.local_wrapper import LocalEnvironmentWrapper

    log = logging.getLogger("arc3.local")
    log.setLevel(logging.ERROR)
    return LocalEnvironmentWrapper(
        environment_info=info,
        logger=log,
        scorecard_id="local",
        seed=seed,
        save_recording=False,
        recordings_dir=recordings_dir or "/tmp/arc3-recordings",
    )


# ---------------------------------------------------------------------------
# Observation helpers
# ---------------------------------------------------------------------------
@dataclass
class Obs:
    """Minimal, cheap observation used by local policies and search."""

    grid: np.ndarray                 # last frame, HxW int8
    levels: int
    state: str
    available: tuple[int, ...]
    action_counter: int

    @property
    def terminal(self) -> bool:
        return self.state in ("WIN", "GAME_OVER")


def to_obs(frame, prev_grid: np.ndarray | None = None) -> Obs:
    """Build an Obs; terminal frames sometimes carry no frame list."""
    frames = getattr(frame, "frame", None) or []
    if frames:
        grid = np.asarray(frames[-1], dtype=np.int16)
    elif prev_grid is not None:
        grid = prev_grid
    else:
        grid = np.zeros((64, 64), dtype=np.int16)
    state = str(getattr(frame.state, "value", frame.state)).rsplit(".", 1)[-1].upper()
    return Obs(
        grid=grid,
        levels=int(getattr(frame, "levels_completed", 0) or 0),
        state=state,
        available=tuple(int(a) for a in (getattr(frame, "available_actions", None) or [1, 2, 3, 4])),
        action_counter=0,
    )


def frame_hash(obs: Obs) -> int:
    """Cheap hash of the visible grid, used for loop detection / dedup."""
    return hash((obs.levels, obs.grid.tobytes()))


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------
@dataclass
class EpisodeResult:
    game: str
    seed: int
    policy: str
    levels: int
    win_levels: int
    steps: int
    wall_ms: float
    solved: bool = False
    error: str | None = None
    trace: list[dict] = field(default_factory=list)

    @property
    def level_rate(self) -> float:
        return self.levels / self.win_levels if self.win_levels else 0.0


def run_episode(
    info: Any,
    game: str,
    policy: Callable[[Obs, random.Random, dict], int],
    seed: int = 0,
    max_steps: int = 1200,
    policy_kwargs: dict | None = None,
    keep_trace: bool = False,
) -> EpisodeResult:
    """Play one episode with `policy(obs, rng, ctx) -> action_id`."""
    rng = random.Random(seed)
    ctx: dict[str, Any] = {"prev_grid": None, "prev_levels": 0, "seen": set()}
    if policy_kwargs:
        ctx.update(policy_kwargs)

    t0 = time.perf_counter()
    try:
        wrapper = make_wrapper(info, seed=seed)
        frame = wrapper.reset()
        win_levels = int(getattr(frame, "win_levels", 0) or 0)
        obs = to_obs(frame)
        steps = 0
        trace: list[dict] = []
        while steps < max_steps and not obs.terminal:
            decision = policy(obs, rng, ctx)
            data = None
            if isinstance(decision, tuple):
                act, data = decision
            else:
                act = decision
            if act not in obs.available:
                act = rng.choice(obs.available)
                data = None
            if act == 6 and not data:
                data = {"x": rng.randrange(64), "y": rng.randrange(64)}
            frame = wrapper.step(action_for(act), data=data)
            if frame is None:
                break
            prev_grid, prev_levels = obs.grid, obs.levels
            obs = to_obs(frame, prev_grid)
            obs.action_counter = steps + 1
            ctx["prev_grid"], ctx["prev_levels"] = prev_grid, prev_levels
            steps += 1
            if keep_trace:
                trace.append({"step": steps, "action": act, "levels": obs.levels})
            if obs.levels > prev_levels:
                ctx["seen"].clear()
        wall = (time.perf_counter() - t0) * 1000
        return EpisodeResult(
            game=game, seed=seed, policy=getattr(policy, "__name__", "policy"),
            levels=obs.levels, win_levels=win_levels, steps=steps,
            wall_ms=wall, solved=obs.state == "WIN", trace=trace,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return EpisodeResult(
            game=game, seed=seed, policy=getattr(policy, "__name__", "policy"),
            levels=0, win_levels=0, steps=0,
            wall_ms=(time.perf_counter() - t0) * 1000, error=f"{type(exc).__name__}: {exc}",
        )
