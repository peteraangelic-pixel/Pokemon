#!/usr/bin/env python3
"""
Szybki benchmark — 100 gier, 3 sekundy, szacuje 1.6M i 600g.

Uruchom:
  /tmp/venv/bin/python tools/bench_quick.py --agent agents/v69_tunable.py --deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --games 100 --workers 32
"""
import argparse, time, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
import gauntlet_ffi as G
from multiprocessing import Pool
import ctypes, json, os

def main():
    ap=argparse.ArgumentParser(description="Szybki benchmark 100 gier -> szacuje 1.6M")
    ap.add_argument("--agent", default="agents/v69_tunable.py")
    ap.add_argument("--deck", default="decks/v66_alakazam_simple.csv")
    ap.add_argument("--opp-dir", default="decks/trolley_pool")
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--workers", type=int, default=32)
    args=ap.parse_args()

    print(f"=== bench_quick: {args.games} gier, {args.workers} workers ===")
    print(f"agent={args.agent} deck={args.deck} opp={args.opp_dir}")

    # use gauntlet_ffi
    import subprocess
    cmd=[f"{ROOT}/../.venv/bin/python" if (ROOT/".venv").exists() else "/tmp/venv/bin/python",
         str(ROOT/"tools/gauntlet_ffi.py"),
         "--agent", args.agent,
         "--our-deck", args.deck,
         "--opp-dir", args.opp_dir,
         "--games", str(args.games),
         "--workers", str(args.workers)]
    # fallback to python
    if not Path(cmd[0]).exists():
        cmd[0]="python3"
    
    t0=time.time()
    res=subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    elapsed=time.time()-t0
    print(res.stdout[-2000:])
    if res.stderr:
        print(res.stderr[-1000:], file=sys.stderr)

    # parse games/sec from output? Estimate from elapsed
    total_games = args.games * len(list(Path(args.opp_dir).glob("*.csv"))) if Path(args.opp_dir).is_dir() else args.games
    gps = total_games / max(elapsed,0.001)
    print(f"\n=== WYNIK SZYBKI ===")
    print(f"Zmierzone: {total_games} gier w {elapsed:.1f}s = {gps:.1f} g/s")
    print(f"600g test: {600/gps:.1f}s")
    print(f"40k rollout: {40000/gps:.1f}s = {40000/gps/60:.1f} min")
    print(f"1.6M rollout: {1600000/gps:.1f}s = {1600000/gps/3600:.2f}h")
    print(f"1.6M + trening (8 min/40k): {(40000/gps + 480)/3600*40:.1f}h")
    print(f"\nTo jest SZYBKI benchmark — sam trwa {elapsed:.1f}s, a szacuje 1.6M bez liczenia!")

if __name__=="__main__":
    main()
