"""Local, LLM-free policies for ARC-AGI-3 games.

Every policy has the signature ``policy(obs, rng, ctx) -> int | (int, dict)``
where ``ctx`` carries cross-step memory and evolvable parameters.

The point of this module is *cheap* policies that can be evaluated thousands of
times per minute against the local engine. They are not meant to beat the LLM
agent outright — they are meant to (a) give a fast, honest fitness signal for
parameter evolution, and (b) act as an action-pruner / fallback inside the LLM
harness.
"""
from __future__ import annotations

import random
from typing import Any

import numpy as np

from engine import Obs

# 1=UP 2=DOWN 3=LEFT 4=RIGHT 5=INTERACT 6=CLICK 7=OTHER
REVERSE = {1: 2, 2: 1, 3: 4, 4: 3}


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------
def random_policy(obs: Obs, rng: random.Random, ctx: dict) -> int:
    """Uniform random over the actions the game currently offers."""
    return rng.choice(obs.available)


def anti_reverse_policy(obs: Obs, rng: random.Random, ctx: dict) -> int:
    """Random, but never immediately undo the previous move (cheap loop guard)."""
    last = ctx.get("last_action")
    choices = [a for a in obs.available if a != REVERSE.get(last)]
    act = rng.choice(choices or list(obs.available))
    ctx["last_action"] = act
    return act


# ---------------------------------------------------------------------------
# Evolvable heuristic
# ---------------------------------------------------------------------------
DEFAULT_PARAMS: dict[str, float] = {
    # exploration temperature over action scores (higher = flatter)
    "temp": 1.0,
    # bonus for actions that changed the frame from a similar state before
    "novelty_weight": 1.0,
    # penalty for repeating the exact action that just produced no change
    "noop_penalty": 1.5,
    # penalty for immediate reversal
    "reverse_penalty": 0.8,
    # probability of taking a pure random action (escape local optimum)
    "epsilon": 0.15,
    # probability of spending a step on a click probe when CLICK is available
    "click_rate": 0.25,
    # decay applied to older action statistics (0..1, 1 = no decay)
    "memory_decay": 0.85,
    # bonus for actions that raised the level (kept per action id)
    "progress_bonus": 3.0,
}


def _state_signature(obs: Obs) -> int:
    """Coarse, cheap signature: level + downsampled grid."""
    g = obs.grid
    coarse = g[::8, ::8].tobytes() if g.size > 64 else g.tobytes()
    return hash((obs.levels, coarse))


def heuristic_policy_factory(params: dict[str, float] | None = None):
    """Build a policy closure over `params` (so CEM can mutate them)."""
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)

    def policy(obs: Obs, rng: random.Random, ctx: dict) -> int | tuple[int, dict]:
        stats: dict[int, float] = ctx.setdefault("stats", {})
        sig = _state_signature(obs)
        last_sig = ctx.get("last_sig")
        last_action = ctx.get("last_action")
        prev_grid = ctx.get("prev_grid")
        prev_levels = ctx.get("prev_levels", 0)

        # --- update statistics from the previous transition -------------
        if last_action is not None and prev_grid is not None:
            changed = not np.array_equal(prev_grid, obs.grid)
            gain = 0.0 if not changed else 1.0
            if obs.levels > prev_levels:
                gain += p["progress_bonus"]
            stats[last_action] = stats.get(last_action, 0.0) * p["memory_decay"] + gain

        ctx["last_sig"] = sig
        if obs.levels > prev_levels:
            stats.clear()  # new level: old statistics are misleading

        # --- random escape ----------------------------------------------
        if rng.random() < p["epsilon"]:
            act = rng.choice(obs.available)
            ctx["last_action"] = act
            return act

        # --- click probing ----------------------------------------------
        if 6 in obs.available and rng.random() < p["click_rate"]:
            h, w = obs.grid.shape
            # bias clicks toward cells that look "interesting" (non-background)
            bg = int(np.bincount(obs.grid.ravel()).argmax())
            mask = obs.grid != bg
            if mask.any():
                ys, xs = np.nonzero(mask)
                i = rng.randrange(len(xs))
                x, y = int(xs[i]), int(ys[i])
            else:
                x, y = rng.randrange(w), rng.randrange(h)
            ctx["last_action"] = 6
            return 6, {"x": min(x, 63), "y": min(y, 63)}

        # --- score available actions ------------------------------------
        scores: dict[int, float] = {}
        for a in obs.available:
            s = stats.get(a, 0.0) * p["novelty_weight"]
            if a == last_action:
                s -= p["noop_penalty"]
            if a == REVERSE.get(last_action):
                s -= p["reverse_penalty"]
            # mild exploration floor so nothing is permanently dead
            s += rng.random() * 0.05
            scores[a] = s

        acts = list(scores)
        vals = np.array([scores[a] for a in acts], dtype=np.float64)
        temp = max(1e-3, p["temp"])
        z = vals / temp
        z -= z.max()
        probs = np.exp(z)
        probs /= probs.sum()
        act = int(rng.choices(acts, weights=probs, k=1)[0])
        ctx["last_action"] = act
        return act

    policy.__name__ = "heuristic_policy"
    return policy


# ---------------------------------------------------------------------------
# Precomputed-solution replay
# ---------------------------------------------------------------------------
def solution_policy_factory(paths: list[list[list[int]]],
                            fallback_params: dict[str, float] | None = None):
    """Replay a solved action sequence first, then fall back to the heuristic.

    `paths` is the per-level list stored by ``local/solver.py``; each action is
    encoded as ``[id]`` or ``[6, x, y]`` for clicks.
    """
    fallback = heuristic_policy_factory(fallback_params)
    flat = [enc for path in paths for enc in path]

    def policy(obs: Obs, rng: random.Random, ctx: dict):
        i = ctx.get("sol_i", 0)
        if i < len(flat):
            enc = flat[i]
            ctx["sol_i"] = i + 1
            ctx["last_action"] = enc[0]
            if enc[0] == 6 and len(enc) > 2:
                return 6, {"x": int(enc[1]), "y": int(enc[2])}
            return int(enc[0])
        return fallback(obs, rng, ctx)

    policy.__name__ = "solution_policy"
    return policy


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def build_policy(name: str, params: dict[str, float] | None = None):
    if name == "random":
        return random_policy
    if name == "anti-reverse":
        return anti_reverse_policy
    if name == "heuristic":
        return heuristic_policy_factory(params)
    if name == "solution":
        paths = (params or {}).get("paths") or []
        fallback_params = {k: v for k, v in (params or {}).items()
                           if k not in ("paths", "fallback_params")} or None
        return solution_policy_factory(paths, fallback_params)
    raise ValueError(f"unknown policy {name!r}; try random|anti-reverse|heuristic|solution")
