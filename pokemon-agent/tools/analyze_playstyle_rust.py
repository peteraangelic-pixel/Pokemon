#!/usr/bin/env python3
"""Wrapper for analyze_playstyle_rust — uses Rust+Rayon if binary exists, else falls back to Python.

Usage:
  python tools/analyze_playstyle_rust.py --replays-dir kaggle_results/top30_live --out kaggle_results/top30_live/playstyle.md
  # or directly Rust:
  ./rust/bin/analyze_playstyle_rust --replays-dir kaggle_results/top30_live --out kaggle_results/top30_live/playstyle.md
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUST_BIN = ROOT / "rust" / "bin" / "analyze_playstyle_rust"
PY_FALLBACK = ROOT / "tools" / "analyze_playstyle.py"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays-dir", default=str(ROOT / "kaggle_results" / "top30_live"))
    ap.add_argument("--out", default="")
    ap.add_argument("--cards", default=str(ROOT / "data" / "cards.json"))
    args = ap.parse_args()

    if RUST_BIN.exists():
        cmd = [str(RUST_BIN), "--replays-dir", args.replays_dir, "--cards", args.cards]
        if args.out:
            cmd += ["--out", args.out]
        print(f"Using Rust binary {RUST_BIN} (Rayon, 10-20x faster)")
        subprocess.run(cmd, check=True)
    else:
        print(f"Rust binary not found at {RUST_BIN}, falling back to Python {PY_FALLBACK} (slower)")
        cmd = [sys.executable, str(PY_FALLBACK), "--replays-dir", args.replays_dir]
        if args.out:
            cmd += ["--out", args.out]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
