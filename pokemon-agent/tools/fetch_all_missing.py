#!/usr/bin/env python3
"""Download all missing replays for our two active submissions."""
import json, pathlib, subprocess, sys, time, os

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "kaggle_results" / "our_replays"

def kaggle(args):
    env = dict(os.environ)
    env.setdefault("KAGGLE_QUIET","1")
    p = subprocess.run([sys.executable, "-m", "kaggle"]+args, capture_output=True, text=True, env=env)
    if p.returncode!=0:
        p2 = subprocess.run(["kaggle"]+args, capture_output=True, text=True, env=env)
        return p2.returncode, p2.stdout, p2.stderr
    return p.returncode, p.stdout, p.stderr

def download_replay(eid, dest):
    dest.mkdir(parents=True, exist_ok=True)
    # skip if exists in either location
    if (dest/f"episode-{eid}-replay.json").exists() or (dest/"loss_replays"/f"episode-{eid}-replay.json").exists():
        return True
    rc,out,err = kaggle(["competitions","replay",str(eid),"-p",str(dest)])
    if rc!=0:
        print(f"fail {eid}: {(err or out)[:300]}")
        return False
    # check
    if (dest/f"episode-{eid}-replay.json").exists():
        print(f"ok {eid}")
        return True
    found=list(dest.glob(f"*{eid}*.json"))
    if found:
        print(f"ok {eid} via glob")
        return True
    print(f"not found after dl {eid}")
    return False

def main():
    subs=["57290256","57290311"]
    # also try to load latest submissions file to get active ids
    latest = OUT/".."/"latest_submissions.txt"
    # but use hardcoded for now
    for sub in subs:
        full = OUT/f"episodes_full_{sub}.json"
        if not full.exists():
            print(f"missing {full}")
            continue
        data=json.load(open(full))
        parsed=[]
        for d in data:
            try:
                inner=json.loads(d['repr'])
                parsed.append(inner)
            except Exception:
                pass
        ids=[str(p['id']) for p in parsed if str(p.get('id','')).isdigit()]
        missing=[]
        for eid in ids:
            if (OUT/f"episode-{eid}-replay.json").exists() or (OUT/"loss_replays"/f"episode-{eid}-replay.json").exists():
                continue
            missing.append(eid)
        print(f"{sub}: missing {len(missing)} of {len(ids)}")
        fails=0
        for eid in missing:
            ok=download_replay(eid, OUT)
            if not ok:
                fails+=1
                time.sleep(2)
                # retry once
                ok=download_replay(eid, OUT)
                if not ok:
                    print(f"  retry fail {eid}")
                    time.sleep(5)
                    if fails>=10:
                        print("  too many fails, sleeping 30s")
                        time.sleep(30)
                        fails=0
                else:
                    fails=0
            else:
                fails=0
            time.sleep(0.5)
        print(f"{sub}: done, still missing {len([e for e in missing if not (OUT/f'episode-{e}-replay.json').exists() and not (OUT/'loss_replays'/f'episode-{e}-replay.json').exists()])}")

if __name__=="__main__":
    main()
