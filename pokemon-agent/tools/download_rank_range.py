#!/usr/bin/env python3
"""Download replays for rank range (e.g., 90-100) and top N — for meta analysis

Usage:
    python tools/download_rank_range.py --top-n 7 --replays-per-team 7 --outdir kaggle_results/top7_live
    python tools/download_rank_range.py --rank-start 90 --rank-end 100 --replays-per-team 7 --outdir kaggle_results/rank90_100_live
"""

import argparse, csv, io, json, os, subprocess, sys, time
from pathlib import Path

DEFAULT_SLUG = "the-pokemon-company-ptcg-ai-battle-challenge-playground"
ROOT = Path(__file__).resolve().parents[1]

def sh(args):
    env=dict(os.environ)
    env.setdefault("KAGGLE_QUIET","1")
    p=subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr

def kaggle(args):
    rc,out,err=sh([sys.executable, "-m", "kaggle"]+args)
    if rc==0:
        return rc,out,err
    return sh(["kaggle"]+args)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--competition", default=DEFAULT_SLUG)
    ap.add_argument("--rank-start", type=int, default=0)
    ap.add_argument("--rank-end", type=int, default=0)
    ap.add_argument("--top-n", type=int, default=0)
    ap.add_argument("--replays-per-team", type=int, default=7)
    ap.add_argument("--outdir", default=str(ROOT / "kaggle_results" / "rank90_100_live"))
    ap.add_argument("--delay", type=float, default=0.2)
    args=ap.parse_args()

    outdir=Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Download leaderboard via show --csv
    print("Downloading leaderboard via show --csv...")
    rc,out,err=kaggle(["competitions","leaderboard","show","-c",args.competition,"--csv"])
    if rc!=0:
        print(f"Leaderboard show failed: {err[:500]}")
        return 1

    lb_file=outdir / "leaderboard.csv"
    lb_file.write_text(out, encoding="utf-8")
    rows=list(csv.DictReader(io.StringIO(out)))
    print(f"Total leaderboard rows: {len(rows)}")

    if args.top_n>0:
        selected=rows[:args.top_n]
        print(f"Selected top {args.top_n} teams")
    elif args.rank_start>0 and args.rank_end>0:
        selected=[]
        for r in rows:
            try:
                rank=int(r.get("Rank",0))
                if args.rank_start <= rank <= args.rank_end:
                    selected.append(r)
            except:
                continue
        print(f"Selected rank {args.rank_start}-{args.rank_end}: {len(selected)} teams")
    else:
        print("Need --top-n or --rank-start/--rank-end")
        return 1

    # Save manifest
    manifest_path=outdir / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as mf:
        writer=csv.DictWriter(mf, fieldnames=["Rank","TeamId","TeamName","Score"])
        writer.writeheader()
        for r in selected:
            writer.writerow({"Rank":r.get("Rank"),"TeamId":r.get("TeamId"),"TeamName":r.get("TeamName"),"Score":r.get("Score")})

    for team_row in selected:
        team_id=team_row.get("TeamId")
        team_name=team_row.get("TeamName")
        rank=team_row.get("Rank")
        print(f"\n=== Rank {rank} Team {team_name} Id {team_id} ===")

        rc,out,err=kaggle(["competitions","team-submissions","-c",args.competition,"--team-id",str(team_id)])
        if rc!=0:
            print(f"  team-submissions failed: {err[:300]}")
            time.sleep(args.delay)
            continue

        try:
            sub_rows=list(csv.DictReader(io.StringIO(out)))
        except Exception as e:
            print(f"  Parse submissions failed: {e}")
            continue

        if not sub_rows:
            print(f"  No submissions")
            continue

        sub_rows=sorted(sub_rows, key=lambda x: x.get("date",""), reverse=True)
        for sub in sub_rows[:2]:
            sub_ref=sub.get("ref")
            print(f"  Sub {sub_ref} {sub.get('fileName')} {sub.get('status')}")
            rc2,out2,err2=kaggle(["competitions","episodes","-c",args.competition,"--submission-id",str(sub_ref)])
            if rc2!=0:
                print(f"    episodes failed: {err2[:300]}")
                time.sleep(args.delay)
                continue

            try:
                ep_rows=list(csv.DictReader(io.StringIO(out2)))
            except:
                print(f"    Parse episodes failed")
                continue

            if not ep_rows:
                print(f"    No episodes")
                continue

            ep_rows=sorted(ep_rows, key=lambda x: x.get("id",""), reverse=True)
            for ep in ep_rows[:args.replays_per_team]:
                ep_id=ep.get("id")
                print(f"    Episode {ep_id} — downloading replay...")
                # Try episode-replay
                rc3,out3,err3=kaggle(["competitions","episode-replay","-c",args.competition,"--episode-id",str(ep_id)])
                if rc3==0 and out3.strip().startswith("{"):
                    (outdir / f"episode-{ep_id}-replay.json").write_text(out3, encoding="utf-8")
                    print(f"      Saved episode-{ep_id}-replay.json ({len(out3)} bytes)")
                else:
                    # Try replay command with -p
                    rc3b,_,_=kaggle(["competitions","replay","-c",args.competition,"--episode-id",str(ep_id),"-p",str(outdir)])
                    replay_files=list(outdir.glob(f"*{ep_id}*.json"))
                    if replay_files:
                        print(f"      Saved {replay_files[0].name}")
                    else:
                        print(f"      Failed to get replay for {ep_id}: {err3[:200]}")

                time.sleep(args.delay)
            time.sleep(args.delay)

    print(f"\nDone. JSONs in {outdir}: {len(list(outdir.glob('*.json')))}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
