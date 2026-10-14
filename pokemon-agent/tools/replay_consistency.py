#!/usr/bin/env python3
"""Replay-vs-code consistency check.

For every fresh live replay, feed OUR recorded observations into the bundled
agents (v48, v51) locally and compare their chosen actions with the actions
recorded in the replay. If the live agent ran the same code, agreement should
be ~100%. Systematic disagreement => the live runtime diverged (timeout
fallback, exception fallback, different code). Per-replay best match also
attributes the replay to a submission.

Usage: .venv/bin/python tools/replay_consistency.py [cutoff] [max_replays]
"""
from __future__ import annotations

import glob
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = int(sys.argv[1]) if len(sys.argv) > 1 else 124200000
MAXR = int(sys.argv[2]) if len(sys.argv) > 2 else 12


def load_agent(bundle_dir: str, name: str):
    spec = importlib.util.spec_from_file_location(name, str(Path(bundle_dir) / "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    import os
    cands = {"v48": "/tmp/b48", "v51": "/tmp/b51", "v38b": "/tmp/b38b", "v36": "/tmp/b36", "v422": "/tmp/b422"}
    if os.environ.get("ONLY"):
        cands = {k: v for k, v in cands.items() if k in os.environ["ONLY"].split(",")}
    agents = {k: load_agent(v, f"bundle_{k}") for k, v in cands.items()}
    files = [f for f in sorted(glob.glob(str(ROOT / "kaggle_results/our_replays/episode-*-replay.json")))
             if int(Path(f).stem.split("-")[1]) > CUTOFF][:MAXR]
    import time
    for f in files:
        d = json.load(open(f))
        teams = (d.get("info") or {}).get("TeamNames") or []
        if "PeterSharps" not in teams:
            continue
        me = teams.index("PeterSharps")
        stats = {k: [0, 0] for k in agents}  # agree, total
        times = {k: 0.0 for k in agents}
        first_disagree = {}
        for s in d.get("steps") or []:
            if not isinstance(s, list) or me >= len(s):
                continue
            a = s[me]
            if not isinstance(a, dict) or not isinstance(a.get("observation"), dict):
                continue
            obs = a["observation"]
            sel = obs.get("select") or {}
            cur0 = obs.get("current") or {}
            if int(cur0.get("yourIndex", -1)) != me:
                continue
            if not sel.get("option"):
                continue
            recorded = a.get("action")
            if not recorded and recorded != 0:
                continue
            rec = recorded if isinstance(recorded, list) else [recorded]
            if len(rec) == 60:  # deck submission
                continue
            for k, mod in agents.items():
                t0 = time.perf_counter()
                try:
                    got = mod.agent(obs)
                except Exception as e:  # noqa: BLE001
                    got = f"EXC:{type(e).__name__}"
                times[k] += time.perf_counter() - t0
                stats[k][1] += 1
                if got == rec:
                    stats[k][0] += 1
                elif k not in first_disagree:
                    first_disagree[k] = (rec, got, (sel.get("context"), len(sel.get("option") or [])))
        line = f"{Path(f).stem[:24]} me={me} "
        for k in agents:
            ag, tot = stats[k]
            line += f"| {k}: {ag}/{tot} agree, {times[k]:.1f}s "
            if k in first_disagree:
                line += f"firstDiff={first_disagree[k]} "
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
