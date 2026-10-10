"""Local, SDK-free probe for revisit behaviour.

The real ARC SDK needs Python 3.12 and network access, neither of which the
sandbox has. This rig drives the pure policy against a tiny synthetic game so
revisit behaviour can be measured in seconds instead of a 5-minute CI round.

The question it answers: when the *same* world state is presented again with
only irrelevant pixels changed, does the policy recognise it as visited?

Usage:
    python3 tools/synthetic_probe.py                 # static world
    python3 tools/synthetic_probe.py --noise          # + animated pixel inside the field
    python3 tools/synthetic_probe.py --noise --steps 400
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.policy import (  # noqa: E402
    COMPLEX_ACTION,
    Snapshot,
    horizontal_hud_mask,
    masked_signature,
)

SIZE = 64


class SyntheticGame:
    """A click-only game: one target region advances the level, nothing else does."""

    def __init__(self, *, noise: bool, seed: int, size: int = SIZE) -> None:
        self.rng = random.Random(seed)
        self.size = size
        self.noise = noise
        self.steps = 0
        self.levels_completed = 0
        # Cel: prostokat, ktorego klikniecie daje postep.
        self.target = (40, 20, 48, 26)
        # Dekoracje, zeby komponenty mialy sens.
        self.blobs = []
        for _ in range(6):
            w = self.rng.randint(3, 7)
            h = self.rng.randint(3, 7)
            x = self.rng.randint(6, size - w - 6)
            y = self.rng.randint(8, size - h - 8)
            self.blobs.append((x, y, w, h, self.rng.randint(1, 5)))

    def _grid(self) -> tuple[tuple[int, ...], ...]:
        g = [[0] * self.size for _ in range(self.size)]
        for x, y, w, h, c in self.blobs:
            for r in range(y, y + h):
                for cc in range(x, x + w):
                    g[r][cc] = c
        # Cel jest zawsze ten sam -- swiat jest statyczny.
        x0, y0, x1, y1 = self.target
        for r in range(y0, y1):
            for cc in range(x0, x1):
                g[r][cc] = 9
        if self.noise:
            # Piksel animowany WEWNATRZ pola gry (nie w maskowanym HUD).
            g[30 + (self.steps % 2)][12] = 7
        return tuple(tuple(row) for row in g)

    def frame(self, state: str = "PLAYING") -> Snapshot:
        return Snapshot(
            state=state,
            levels_completed=self.levels_completed,
            available_actions=(COMPLEX_ACTION,),
            planes=(self._grid(),),
        )

    def apply(self, proposal) -> Snapshot:
        x0, y0, x1, y1 = self.target
        hit = (
            proposal.name == COMPLEX_ACTION
            and proposal.x is not None
            and x0 <= proposal.x < x1
            and y0 <= proposal.y < y1
        )
        self.steps += 1
        if hit:
            self.levels_completed += 1
            return self.frame()
        return self.frame()


def run(*, noise: bool, steps: int, seed: int) -> dict:
    from agent.policy import ExplorerPolicy

    game = SyntheticGame(noise=noise, seed=seed)
    policy = ExplorerPolicy()

    signatures: list[str] = []
    revisits = 0
    observations = 0
    clicks: set[tuple[int, int]] = set()
    levels = []

    snapshot = game.frame()
    for _ in range(steps):
        excluded = horizontal_hud_mask(snapshot)
        sig = masked_signature(snapshot, excluded)
        observations += 1
        if sig in signatures:
            revisits += 1
        signatures.append(sig)

        proposal = policy.choose(snapshot)
        if proposal.name == COMPLEX_ACTION and proposal.x is not None:
            clicks.add((proposal.x, proposal.y))
        snapshot = game.apply(proposal)
        levels.append(snapshot.levels_completed)

    distinct = len(set(signatures))
    return {
        "noise": noise,
        "steps": steps,
        "observations": observations,
        "distinct_states": distinct,
        "distinct_ratio": distinct / max(observations, 1),
        "revisits": revisits,
        "revisit_rate": revisits / max(observations, 1),
        "distinct_clicks": len(clicks),
        "levels_completed": levels[-1] if levels else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--noise", action="store_true", help="animate one pixel inside the play field")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    res = run(noise=args.noise, steps=args.steps, seed=args.seed)
    print(f"synthetic probe  (noise={res['noise']}, steps={res['steps']})")
    print("-" * 52)
    print(f"  observations          : {res['observations']}")
    print(f"  distinct states       : {res['distinct_states']}")
    print(f"  distinct ratio        : {res['distinct_ratio']:.3f}")
    print(f"  revisits              : {res['revisits']}  ({100*res['revisit_rate']:.1f}%)")
    print(f"  distinct click targets: {res['distinct_clicks']}")
    print(f"  levels completed      : {res['levels_completed']}")
    print()
    if res["distinct_ratio"] > 0.5 and not res["noise"]:
        print("UWAGA: swiat jest statyczny, a agent i tak widzi wiele 'nowych' stanow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
