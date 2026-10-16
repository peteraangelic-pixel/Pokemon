#!/usr/bin/env python3
"""4800-game validation harness per second-branch critique.

Groups (600 games each, total 4800):
- trolley: v56_trolley, v57_trolley34w, shaun2024_wall (200 each)
- crustle_wall: live_killers WALL + yumeneko metal? Actually use shaun + trolley already, but separate
- mengfei_wall: Mengfei_Li (Kangaskhan 300 HP)
- top10_live: top 10 from top30_live (by name? use top10 dir)
- top30_rest: remaining 20 from top30_live
- live_killers: 18 decks from live_killers (600 games = ~33 per deck? use 33*18=594)
- broad_field sample: 20 decks from broad_field

We use gauntlet_ffi with workers=4.
Reports grid, trolley, wall, etc.
"""
import subprocess, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
VENV="/tmp/venv/bin/python"
if not pathlib.Path(VENV).exists():
    VENV="python3"

def run(agent, deck, opp_dir, games, workers=4):
    cmd=[VENV, str(ROOT/"tools/gauntlet_ffi.py"), "--agent", agent, "--our-deck", deck, "--opp-dir", opp_dir, "--games", str(games), "--workers", str(workers)]
    print(f"Running: {' '.join(cmd)}")
    res=subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    print(res.stdout[-2000:])
    if res.stderr:
        print(res.stderr[-1000:], file=sys.stderr)
    # parse TOTAL line
    for line in res.stdout.splitlines():
        if line.startswith("TOTAL"):
            return line
    return "NO TOTAL"

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent", default="agents/v70_alakazam_endgame.py")
    ap.add_argument("--deck", default="decks/v66_alakazam_simple.csv")
    args=ap.parse_args()
    groups=[
        ("trolley", "decks/trolley_pool", 200),  # we will create trolley_pool dir
        ("mengfei", "/tmp/mengfei", 600),
        ("top30", "decks/top30_live", 20),  # 27*20=540
        ("live_killers", "decks/live_killers", 33), # 18*33=594
        ("broad", "decks/broad_field", 8), # 67*8=536
    ]
    # ensure trolley_pool exists
    tp=ROOT/"decks/trolley_pool"
    tp.mkdir(exist_ok=True)
    # copy trolley decks
    for f in ["v56_trolley.csv","v57_trolley34w.csv","shaun2024_wall.csv"]:
        src=ROOT/f"decks/{f}"
        if src.exists():
            (tp/f).write_bytes(src.read_bytes())
    for name, opp_dir, games in groups:
        line=run(args.agent, args.deck, opp_dir, games)
        print(f"{name}: {line}")
