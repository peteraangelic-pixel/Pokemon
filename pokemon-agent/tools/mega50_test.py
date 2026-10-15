#!/usr/bin/env python3
"""MEGA-TEST (a450): our agent+deck vs the TOP50 field's actual decks.

Input decks are produced by tools/extract_top50.py from manifest-selected
replays (7 per top50 team). This test measures DECK matchups: the opponent
deck is piloted by one fixed proxy policy for every arm, because the real
top50 policies are closed-source. That is the correct ladder-relevant
question we can answer locally: "how does our agent+deck fare into the decks
actually used by the top50?"

Usage:
  .venv/bin/python tools/mega50_test.py \
      --agent agents/main_heuristic_v37_gate.py \
      --arm2 agents/c87_v34.py \
      --opp-agent agents/c87_v34.py \
      --our-deck decks/v22_35w_noBoss.csv --games 10 \
      --pool decks/top50 \
      --extract kaggle_results/top50_live/top50_extract.csv \
      --leaderboard kaggle_results/top50_live/leaderboard.csv \
      --out kaggle_results/top50_live/mega50_results.csv
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import importlib.util
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"


class StartData(ctypes.Structure):
    _fields_ = [("battlePtr", ctypes.c_void_p), ("errorPlayer", ctypes.c_int), ("errorType", ctypes.c_int)]


class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]


def get_lib():
    lib = ctypes.cdll.LoadLibrary(str(LIB))
    lib.GameInitialize()
    lib.BattleStart.restype = StartData
    lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]
    lib.BattleFinish.argtypes = [ctypes.c_void_p]
    lib.GetBattleData.restype = SerialData
    lib.GetBattleData.argtypes = [ctypes.c_void_p]
    lib.Select.restype = ctypes.c_int
    lib.Select.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    return lib


def load_deck(p: Path) -> list[int]:
    return [int(t) for line in open(p) for t in line.replace(",", " ").split() if t]


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def rebind(m, deck: list[int]) -> None:
    m.DECK = list(deck)
    if hasattr(m, "_build_plan"):
        m.PLAN = m._build_plan(list(deck))


def slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name or "team").strip("_")
    return s[:48] or "team"


def play(lib, our_mod, opp_mod, our_deck: list[int], opp_deck: list[int], seat: int) -> int:
    """Return 1 if our side wins, -1 if loses, 0 draw, 2 error/unfinished."""
    rebind(opp_mod, opp_deck)
    d0 = our_deck if seat == 0 else opp_deck
    d1 = opp_deck if seat == 0 else our_deck
    sd = lib.BattleStart((ctypes.c_int * 120)(*d0, *d1))
    bp = sd.battlePtr
    if not bp:
        return 2
    step = 0
    try:
        while True:
            step += 1
            data = lib.GetBattleData(bp)
            obs = json.loads(data.json)
            cur = obs.get("current") or {}
            res = cur.get("result")
            if res is not None and res >= 0:
                return 0 if res == 2 else (1 if res == seat else -1)
            sel = obs.get("select")
            if sel is None:
                break
            me = int(cur.get("yourIndex", 0))
            mod = our_mod if me == seat else opp_mod
            dec = mod.agent(obs)
            if not isinstance(dec, list):
                dec = []
            dec = [int(x) for x in dec]
            if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec)) != 0:
                break
            if step > 5000:
                break
    finally:
        lib.BattleFinish(bp)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--arm2", default=None)
    ap.add_argument("--opp-agent", default="agents/c87_v34.py")
    ap.add_argument("--our-deck", default="decks/v22_35w_noBoss.csv")
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--pool", default="decks/top50")
    ap.add_argument("--extract", default="kaggle_results/top50_live/top50_extract.csv")
    ap.add_argument("--leaderboard", default="kaggle_results/top50_live/leaderboard.csv")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lib = get_lib()
    our_deck = load_deck(ROOT / args.our_deck)
    assert len(our_deck) == 60, len(our_deck)

    arm_paths = [("arm1", ROOT / args.agent)]
    if args.arm2:
        arm_paths.append(("arm2", ROOT / args.arm2))
    arms = []
    for i, (label, p) in enumerate(arm_paths):
        m = load_mod(p, f"_mega_{label}_{i}")
        rebind(m, our_deck)
        arms.append((label, str(p.relative_to(ROOT)), m))
    opp_mod = load_mod(ROOT / args.opp_agent, "_mega_opp")

    # deck file -> team/rank from extract (preferred) or leaderboard.
    deck_meta: dict[str, dict] = {}
    extract_path = ROOT / args.extract
    if extract_path.exists():
        for r in csv.DictReader(open(extract_path, encoding="utf-8-sig")):
            team = r.get("team") or ""
            ep = r.get("episode") or ""
            if team and ep:
                deck_meta[f"{slug(team)}__{ep}"] = {"team": team, "rank": r.get("rank") or ""}

    team_rank: dict[str, int] = {}
    lb_path = ROOT / args.leaderboard
    if not lb_path.exists():
        alt = ROOT / "kaggle_results/leaderboard.csv"
        if alt.exists():
            lb_path = alt
    if lb_path.exists():
        rows = list(csv.DictReader(open(lb_path, encoding="utf-8-sig")))
        def score(r):
            try:
                return float(r.get("Score") or 0)
            except Exception:
                return 0.0
        for i, r in enumerate(sorted(rows, key=score, reverse=True), 1):
            name = r.get("TeamName") or ""
            if name:
                team_rank[name] = i

    def bucket_for(stem: str) -> tuple[str, str, int | None]:
        meta = deck_meta.get(stem, {})
        team = meta.get("team") or stem.split("__")[0].replace("_", " ")
        rank = None
        if meta.get("rank"):
            try:
                rank = int(float(meta["rank"]))
            except Exception:
                rank = None
        if rank is None:
            rank = team_rank.get(team)
        if rank is None:
            return team, "?", None
        if rank <= 10:
            b = "1-10"
        elif rank <= 25:
            b = "11-25"
        elif rank <= 50:
            b = "26-50"
        else:
            b = "51+"
        return team, b, rank

    pool = sorted((ROOT / args.pool).glob("*.csv"))
    print(f"MEGA-TEST decks={len(pool)} games/deck={args.games} opp_proxy={args.opp_agent}")
    for label, p, _m in arms:
        print(f"  {label}: {p} + {args.our_deck}")

    agg: dict[str, dict[str, list[int]]] = defaultdict(lambda: {label: [0, 0, 0] for label, _p, _m in arms})
    per_deck_rows: list[dict] = []
    counters: list[tuple[int, int, str, str]] = []
    t0 = time.time()

    for p in pool:
        opp_deck = load_deck(p)
        if len(opp_deck) != 60:
            continue
        team, bucket, rank = bucket_for(p.stem)
        row = {"deck_file": p.name, "team": team, "rank": rank or "", "bucket": bucket}
        for label, _path, mod in arms:
            w = l = d = 0
            for g in range(args.games):
                r = play(lib, mod, opp_mod, our_deck, opp_deck, g % 2)
                if r == 1:
                    w += 1
                elif r == -1:
                    l += 1
                else:
                    d += 1
            agg[bucket][label][0] += w
            agg[bucket][label][1] += l
            agg[bucket][label][2] += d
            row[f"{label}_w"] = w
            row[f"{label}_l"] = l
            row[f"{label}_d"] = d
            row[f"{label}_wr"] = f"{w / max(w + l, 1):.3f}"
            if label == "arm1" and l > w:
                counters.append((l - w, l, team, p.name))
        per_deck_rows.append(row)

    print(f"done in {time.time() - t0:.0f}s")
    labels = [label for label, _p, _m in arms]
    header = f"{'bucket':<8}" + "".join(f"{label:>18}" for label in labels) + "   n/arm"
    print(header)
    totals = {label: [0, 0, 0] for label in labels}
    for b in ("1-10", "11-25", "26-50", "51+", "?"):
        if b not in agg:
            continue
        cells = []
        n = 0
        for label in labels:
            w, l, d = agg[b][label]
            totals[label][0] += w
            totals[label][1] += l
            totals[label][2] += d
            n = w + l + d
            cells.append(f"{w}W-{l}L ({w / max(w + l, 1):.3f})")
        print(f"{b:<8}" + "".join(f"{c:>18}" for c in cells) + f"   {n}")
    cells = []
    for label in labels:
        w, l, d = totals[label]
        cells.append(f"{w}W-{l}L ({w / max(w + l, 1):.3f})")
    print(f"{'TOTAL':<8}" + "".join(f"{c:>18}" for c in cells))

    if counters:
        counters.sort(reverse=True)
        print("COUNTERS vs arm1 (losses > wins):")
        for diff, l, team, fname in counters[:15]:
            print(f"  net-{diff} ({l} losses) {team} :: {fname}")

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["deck_file", "team", "rank", "bucket"]
        for label in labels:
            fields += [f"{label}_w", f"{label}_l", f"{label}_d", f"{label}_wr"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(per_deck_rows)
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
