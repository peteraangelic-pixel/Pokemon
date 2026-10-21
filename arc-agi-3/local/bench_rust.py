"""Measure the Rust kernel against the Python kernel on *your* machine.

Everything printed here is timed on the hardware it runs on — no extrapolation
from someone else's box. Run it after `cargo build --release`.

    cd arc-agi-3
    python local/bench_rust.py                     # real frames from all games
    python local/bench_rust.py --frames 2000       # longer, for stable numbers
    python local/bench_rust.py --scale 1000000     # extrapolate to ~1M frames

The `--scale` number is what turns a ms/frame measurement into an answer to
"how long would analysing every frame of every recorded run take?".
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine  # noqa: E402
from rust_bridge import RustBridge  # noqa: E402


def collect_frames(n_per_game: int, max_games: int | None = None) -> list[np.ndarray]:
    """Real 64x64 frames from real games — not synthetic noise."""
    import random

    games = engine.discover_games()
    names = sorted(games)
    if max_games:
        names = names[:max_games]
    frames: list[np.ndarray] = []
    rng = random.Random(0)
    for name in names:
        try:
            w = engine.make_wrapper(games[name], seed=0)
            f = w.reset()
            obs = engine.to_obs(f)
            frames.append(obs.grid)
            for _ in range(n_per_game - 1):
                act = rng.choice([a for a in obs.available])
                data = {"x": rng.randrange(64), "y": rng.randrange(64)} if act == 6 else None
                nf = w.step(engine.action_for(act), data=data)
                if nf is None:
                    break
                obs2 = engine.to_obs(nf, obs.grid)
                if obs2.terminal:
                    break
                frames.append(obs2.grid)
                obs = obs2
        except Exception as exc:  # pragma: no cover
            print(f"  skip {name}: {type(exc).__name__}: {exc}")
    return frames


def main() -> None:
    ap = argparse.ArgumentParser(description="Rust vs Python segmentation benchmark")
    ap.add_argument("--frames", type=int, default=400, help="total real frames to use")
    ap.add_argument("--per-game", type=int, default=16)
    ap.add_argument("--threads", type=int, default=0, help="0 = all cores")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--scale", type=int, default=0,
                    help="extrapolate cost to this many frames")
    ap.add_argument("--check", action="store_true",
                    help="verify Rust and Python agree on click candidates")
    args = ap.parse_args()

    bridge = RustBridge(threads=args.threads or None)
    print(f"backend : {bridge.backend}")
    print(f"binary  : {bridge.binary or '(not built — cargo build --release in arc-agi-3/rust)'}")
    print(f"threads : {bridge.threads}")

    per_game = max(1, args.per_game)
    frames = collect_frames(per_game)
    if args.frames and len(frames) > args.frames:
        frames = frames[: args.frames]
    print(f"frames  : {len(frames)} real game frames "
          f"({len({f.shape for f in frames})} shape(s), "
          f"{len({int(f.max()) for f in frames})} max-colour values)\n")

    if not frames:
        print("no frames collected — cannot benchmark")
        return

    # --- correctness first: a fast wrong answer is worthless ---------------
    if args.check and bridge.backend == "rust":
        from segmentation import click_candidates as py_cc

        rust_side = RustBridge(binary=bridge.binary)
        agree, total = 0, min(40, len(frames))
        mismatches = []
        for g in frames[:total]:
            a = py_cc(g, limit=16)
            b = rust_side.click_candidates(g, limit=16)
            if a == b:
                agree += 1
            elif len(mismatches) < 3:
                mismatches.append((a[:4], b[:4]))
        print(f"click parity : {agree}/{total} identical "
              f"({'OK' if agree == total else 'MISMATCH'})")
        for a, b in mismatches:
            print(f"   python {a}  vs  rust {b}")
        print()

    # --- python baseline --------------------------------------------------
    py_clicks_ms = _time_click_candidates(frames, args.repeats, binary=None)
    print(f"python  clicks : {py_clicks_ms:9.2f} ms for {len(frames)} frames "
          f"({py_clicks_ms / len(frames):.3f} ms/frame)")

    # --- rust -------------------------------------------------------------
    result = bridge.benchmark(frames, repeats=args.repeats)
    rust_clicks_ms = None
    if bridge.backend == "rust":
        rust_clicks_ms = _time_click_candidates(frames, args.repeats, binary=bridge.binary)
        print(f"rust    clicks : {rust_clicks_ms:9.2f} ms for {len(frames)} frames "
              f"({rust_clicks_ms / len(frames):.3f} ms/frame)")
        print(f"speedup        : {py_clicks_ms / rust_clicks_ms:.1f}x on click candidates")

    print(f"\nsegmentation (segment_layer): {result}")

    if args.scale:
        n = args.scale
        py_s = py_clicks_ms / len(frames) * n / 1000
        print(f"\nextrapolated to {n:,} frames (measured ms/frame x N, your hardware):")
        print(f"  python : {py_s:9.1f} s  ({py_s / 3600:6.2f} h)")
        if rust_clicks_ms:
            rust_s = rust_clicks_ms / len(frames) * n / 1000
            print(f"  rust   : {rust_s:9.1f} s  ({rust_s / 60:6.2f} min)")
            print(f"  saved  : {(py_s - rust_s) / 3600:.2f} h")

    print("\nnote: `segment_layer` in Rust also computes contours, containment and "
          "object hashes, which the Python fallback here does not — so the "
          "segmentation row understates the Rust/Python gap, not overstates it.")


def _time_click_candidates(frames, repeats: int, binary) -> float:
    """Time click candidate generation; `binary=None` forces the Python path."""
    from segmentation import click_candidates as py_cc

    if binary is None:
        t0 = time.perf_counter()
        for _ in range(repeats):
            for g in frames:
                py_cc(g, limit=16)
        return (time.perf_counter() - t0) * 1000 / repeats

    b = RustBridge(binary=binary)
    b._run("clicks", frames[:1], ["--limit", "16"])  # warm up
    t0 = time.perf_counter()
    for _ in range(repeats):
        b._run("clicks", frames, ["--limit", "16"])
    return (time.perf_counter() - t0) * 1000 / repeats


if __name__ == "__main__":
    main()
