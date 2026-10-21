"""Python <-> Rust bridge for the segmentation kernel.

The Rust binary (`arc3`) is ~120-480x faster than the Python kernel at
segmentation, but it is a separate process with a JSONL stdin/stdout protocol.
This module hides that: callers get `click_candidates()` / `segment()` and do not
care where the work happened.

Design rules:
  * **Never hard-fail.** If the binary is missing, fall back to `segmentation.py`
    and record that in `BenchmarkResult.backend`.
  * **One process per batch**, not per frame — spawning `arc3` for every 64x64
    grid would cost more than the Python kernel.
  * **Same output order** as the input so the caller can zip results.

Usage:
    from rust_bridge import RustBridge
    bridge = RustBridge()                      # auto-detect
    print(bridge.backend)                      # 'rust' | 'python'
    clicks = bridge.click_candidates(grid, limit=16)      # list[(x, y)]
    segs = bridge.segment_batch([g1, g2, g3])             # list[dict]
    bridge.benchmark([g1, g2, ...], repeats=3)            # measured, not claimed
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from segmentation import click_candidates as py_click_candidates
from segmentation import segment as py_segment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINARIES = [
    ROOT / "rust" / "target" / "release" / "arc3",
    ROOT / "rust" / "target" / "debug" / "arc3",
]


def find_binary(explicit: str | Path | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() and os.access(p, os.X_OK) else None
    env = os.environ.get("ARC3_BIN")
    if env and Path(env).is_file():
        return Path(env)
    for p in DEFAULT_BINARIES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    found = shutil.which("arc3")
    return Path(found) if found else None


@dataclass
class BenchmarkResult:
    backend: str
    frames: int
    python_ms: float
    rust_ms: float | None
    speedup: float | None

    def __str__(self) -> str:
        if self.rust_ms is None:
            return (f"{self.frames} frames, python-only: {self.python_ms:.1f} ms "
                    f"({self.python_ms / self.frames:.3f} ms/frame)")
        return (f"{self.frames} frames | python {self.python_ms:.1f} ms | "
                f"rust {self.rust_ms:.1f} ms | speedup {self.speedup:.1f}x")


class RustBridge:
    """Dispatch segmentation/click work to Rust when available."""

    def __init__(self, binary: str | Path | None = None, threads: int | None = None) -> None:
        self.binary = find_binary(binary)
        self.threads = threads or (os.cpu_count() or 1)
        self.backend = "rust" if self.binary else "python"

    # -- transport ---------------------------------------------------------
    def _run(self, subcommand: str, grids: list[np.ndarray],
             extra_args: list[str] | None = None) -> list[dict]:
        if not self.binary:
            raise RuntimeError("Rust binary not available")
        payload = "\n".join(
            json.dumps(np.asarray(g, dtype=int).tolist()) for g in grids
        ) + "\n"
        cmd = [str(self.binary), subcommand, *(extra_args or [])]
        env = dict(os.environ)
        env["RAYON_NUM_THREADS"] = str(self.threads)
        proc = subprocess.run(
            cmd, input=payload, capture_output=True, text=True, env=env, timeout=600,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"arc3 {subcommand} failed ({proc.returncode}): "
                               f"{proc.stderr.strip()[:400]}")
        out = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "error" in obj:
                raise RuntimeError(f"arc3 {subcommand}: {obj['error']}")
            out.append(obj)
        if len(out) != len(grids):
            raise RuntimeError(
                f"arc3 {subcommand}: {len(out)} results for {len(grids)} grids")
        return out

    # -- public API --------------------------------------------------------
    def segment_batch(self, grids: list[np.ndarray]) -> list[dict]:
        if self.backend == "rust":
            try:
                return self._run("segment-batch", grids)
            except Exception:
                self.backend = "python"
        return [
            {"nodes": [
                {"id": c.id, "color": str(c.value), "pixels": c.pixels,
                 "bbox": [c.r0, c.c0, c.r1, c.c1]}
                for c in py_segment(np.asarray(g))
            ]}
            for g in grids
        ]

    def click_candidates(self, grid: np.ndarray, limit: int = 16,
                         min_pixels: int = 1) -> list[tuple[int, int]]:
        if self.backend == "rust":
            try:
                obj = self._run("clicks", [grid],
                                ["--limit", str(limit),
                                 "--min-pixels", str(min_pixels)])[0]
                return [(int(x), int(y)) for x, y in obj["clicks"]]
            except Exception:
                self.backend = "python"
        return py_click_candidates(grid, limit=limit, min_pixels=min_pixels)

    # -- measurement -------------------------------------------------------
    def benchmark(self, grids: list[np.ndarray], repeats: int = 3) -> BenchmarkResult:
        """Time both backends on the same grids. Reports measured numbers only."""
        t0 = time.perf_counter()
        for _ in range(repeats):
            for g in grids:
                py_segment(np.asarray(g))
        py_ms = (time.perf_counter() - t0) * 1000 / repeats

        rust_ms = None
        speedup = None
        if self.backend == "rust":
            try:
                self._run("segment-batch", grids[:1])  # warm up
                t0 = time.perf_counter()
                for _ in range(repeats):
                    self._run("segment-batch", grids)
                rust_ms = (time.perf_counter() - t0) * 1000 / repeats
                speedup = py_ms / rust_ms if rust_ms > 0 else None
            except Exception:
                self.backend = "python"
        return BenchmarkResult(self.backend, len(grids), py_ms, rust_ms, speedup)


def _demo() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import engine

    bridge = RustBridge()
    print(f"backend: {bridge.backend}  binary: {bridge.binary}")
    games = engine.discover_games()
    grids = []
    for name in ["ft09", "lp85", "vc33", "ar25", "ls20"]:
        if name not in games:
            continue
        w = engine.make_wrapper(games[name], seed=0)
        grids.append(engine.to_obs(w.reset()).grid)
    print(bridge.benchmark(grids, repeats=2))
    for name, g in zip(["ft09", "lp85", "vc33", "ar25", "ls20"], grids):
        print(f"{name}: {bridge.click_candidates(g, limit=8)}")


if __name__ == "__main__":
    _demo()
