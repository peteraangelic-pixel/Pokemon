"""
bench_quick_windows.py — szybki benchmark min 60s na Windows, Python multiprocessing

Uruchom w PowerShell:
  .\.venv\Scripts\python tools\bench_quick_windows.py --games 0 --min-seconds 60 --workers 32
"""
import argparse, time, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/v69_tunable.py")
    ap.add_argument("--deck", default="decks/v66_alakazam_simple.csv")
    ap.add_argument("--opp-dir", default="decks/trolley_pool")
    ap.add_argument("--games", type=int, default=0, help="0 = licz do min-seconds")
    ap.add_argument("--min-seconds", type=int, default=60)
    ap.add_argument("--workers", type=int, default=32)
    args=ap.parse_args()

    print(f"=== bench_quick_windows — min {args.min_seconds}s warmup, {args.workers} workers ===")
    
    # ensure deck exists
    deck_path = ROOT/args.deck
    if not deck_path.exists():
        # restore simple deck
        deck=[5,5,5,5,5,13,5,19,19,19,19,66,66,66,140,305,305,305,305,741,741,741,741,742,742,742,742,743,743,743,743,1079,1079,1079,1079,1081,1081,1086,1086,1086,1086,1097,1097,1129,1152,1152,1152,1152,1182,1182,1182,1184,1225,1225,1225,1231,1231,1231,1264,1264]
        deck_path.write_text(",".join(map(str,deck)))
        print(f"restored deck {deck_path}")

    total_games=0
    t0=time.time()
    batch=0
    while True:
        batch+=1
        games_this = 600 if args.games==0 else args.games
        cmd=[sys.executable, str(ROOT/"tools/gauntlet_ffi.py"),
             "--agent", args.agent,
             "--our-deck", args.deck,
             "--opp-dir", args.opp_dir,
             "--games", str(games_this),
             "--workers", str(args.workers)]
        print(f"\n[batch {batch}] {games_this} gier...")
        res=subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
        print(res.stdout[-1000:])
        # count games from output? approximate
        total_games+=games_this * len(list(Path(ROOT/args.opp_dir).glob("*.csv"))) if Path(ROOT/args.opp_dir).is_dir() else games_this
        elapsed=time.time()-t0
        gps=total_games/elapsed if elapsed>0 else 0
        print(f"elapsed {elapsed:.1f}s, total {total_games} gier, {gps:.1f} g/s")
        if elapsed>=args.min_seconds:
            break

    print(f"\n=== RESULT po {elapsed:.1f}s rozgrzewki ===")
    print(f"total {total_games} gier, {gps:.1f} g/s")
    print(f"600g: {600/gps:.1f}s")
    print(f"40k: {40000/gps/60:.1f} min")
    print(f"1.6M rollout: {1600000/gps/3600:.2f}h")
    print(f"1.6M + trening: {40*(40000/gps+480)/3600:.1f}h")

if __name__=="__main__":
    main()
