#!/usr/bin/env python3
"""Imitation data from Kaggle episode replays (NOTES_STRATEGY §19 step 3).

Walks replay JSONs; for every MAIN single-choice select where the acting
agent's action is valid, featurizes ALL options with v42's ml_features
(obs, me, opp, option) and records the chosen index. Saves grouped data for
softmax behavior cloning: X (n_options_total, F), group offsets, chosen pos,
plus per-decision meta (team, won, episode).

Usage: .venv/bin/python tools/extract_imitation.py [--winners-only]
Out:   kaggle_results/imitation_data.npz
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gauntlet_ffi as G

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="kaggle_results/replays")
    ap.add_argument("--out", default="kaggle_results/imitation_data.npz")
    ap.add_argument("--winners-only", action="store_true",
                    help="keep only decisions of the player who won the game")
    args = ap.parse_args()

    mod = G.load_module(str(ROOT / "agents/main_heuristic_v42.py"), "_imit_feat")
    files = sorted(glob.glob(str(ROOT / args.dir / "episode-*-replay.json")))
    print(f"{len(files)} replay files")

    X, starts, chosen, meta_team, meta_won, meta_ep = [], [], [], [], [], []
    n_off = 0
    stats = {"games": 0, "decisions": 0, "skipped": 0}
    for p in files:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        steps = d.get("steps") or []
        rewards = d.get("rewards") or [0, 0]
        teams = (d.get("info") or {}).get("TeamNames") or ["?", "?"]
        if len(steps) < 20:
            continue
        stats["games"] += 1
        ep = Path(p).stem
        for s in steps:
            if not isinstance(s, list):
                continue
            for entry in s:
                if not isinstance(entry, dict):
                    continue
                act = entry.get("action")
                if not act:
                    continue
                obs = entry.get("observation") or {}
                sel = obs.get("select") or {}
                opts = sel.get("option") or []
                if not opts or len(act) != 1:
                    continue
                ctx = sel.get("context")
                typ = sel.get("type")
                if not (ctx == 0 or typ == 0):
                    continue  # MAIN selects only
                if int(sel.get("maxCount") or 1) != 1:
                    continue
                ci = act[0]
                if not isinstance(ci, int) or not (0 <= ci < len(opts)):
                    stats["skipped"] += 1
                    continue
                cur = obs.get("current") or {}
                me = int(cur.get("yourIndex", 0))
                if me not in (0, 1):
                    continue
                won = 1 if len(rewards) > me and (rewards[me] or 0) > 0 else 0
                if args.winners_only and not won:
                    continue
                try:
                    feats = [mod.ml_features(obs, me, 1 - me, o) for o in opts]
                except Exception:
                    stats["skipped"] += 1
                    continue
                starts.append(n_off)
                X.extend(feats)
                n_off += len(opts)
                chosen.append(ci)
                meta_team.append(teams[me] if me < len(teams) else "?")
                meta_won.append(won)
                meta_ep.append(ep)
                stats["decisions"] += 1

    Xa = np.asarray(X, dtype=np.float32)
    print("stats:", stats, "X:", Xa.shape)
    np.savez_compressed(
        ROOT / args.out,
        X=Xa,
        starts=np.asarray(starts, dtype=np.int64),
        chosen=np.asarray(chosen, dtype=np.int32),
        team=np.asarray(meta_team),
        won=np.asarray(meta_won, dtype=np.int8),
        episode=np.asarray(meta_ep),
    )
    print("saved", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
