#!/usr/bin/env python3
"""Build a compact episode table + loss snapshots from downloaded episode JSONs.

Usage:
    python tools/summarize_episodes.py [--outdir kaggle_results/our_replays]

Reads:   <outdir>/episode-*-replay.json   (full episode dumps)
         <outdir>/episodes_<submissionId>.csv  (episode list per submission)
Writes:  <outdir>/episodes_table.csv      (one row per episode: who, win/loss, turns, decks)
         <outdir>/loss_snapshots.jsonl    (per LOSS: final board + last moves, compact)
         <outdir>/summary.md              (W-L by submission/archetype/opponent)

Only LOSS replays are kept in <outdir>/loss_replays/ (wins are deleted to save
repo space — the table + snapshots preserve what mattered).
"""
import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from gauntlet_ffi import CARD_NAMES  # local names if available
except Exception:  # noqa: BLE001
    CARD_NAMES = {}

C = None
NAME = {}


def load_names(outdir):
    global C, NAME
    base = os.path.dirname(os.path.dirname(os.path.abspath(outdir)))
    for cand in (os.path.join(base, "data", "cards.json"),
                 os.path.join(os.path.dirname(base), "data", "cards.json")):
        if os.path.exists(cand):
            C = {c["cardId"]: c for c in json.load(open(cand))}
            NAME = {i: c["name"] for i, c in C.items()}
            return
    NAME = dict(CARD_NAMES)


def cname(cid):
    return NAME.get(int(cid), f"card{cid}")


DECK_TAGS = {
    "KYOGRE": {721, 722, 723},
    "LUCARIO": {677, 678},
    "KOROIDON": {979},
    "SLOWPOKE": {162, 163},
    "LATIAS": {184},
    "CLEFAIRY": {272},
    "MEOWTH": {1071},
    "FEZANDIP": {140},
    "KYUREM": {144},
    "CONKELDURR": {115},
    "OGERPON": {1023, 1024, 1025, 1026},
    "DRAGAPULT": {1057, 1058, 1059, 1060},
    "SOLROCK": {317},
    "DUNSPARCE": {589},
    "MUNKIDORI": {914},
    "BUDew": {125},
}


def arch(ids):
    s = set(ids)
    tags = [t for t, m in DECK_TAGS.items() if s & m]
    return "+".join(tags) if tags else "?"


def walk(f, our_idx):
    d = json.load(open(f))
    info = d.get("info") or {}
    steps = d.get("steps") or []
    rew = d.get("rewards") or []
    win = (rew[our_idx] == 1) if len(rew) == 2 and rew[our_idx] is not None else None

    serial_map = {0: {}, 1: {}}
    our_deck, opp_deck = [], []
    turn = 0
    last_players = None
    last_logs = []
    our_moves = []
    our_ko, opp_ko = [], []
    prev_active = {}
    for s in steps:
        for ai, ag in enumerate(s):
            o = ag.get("observation") or {}
            logs = o.get("logs") or []
            for e in logs:
                pi, ser, cid = e.get("playerIndex"), e.get("serial"), e.get("cardId")
                if pi in (0, 1) and ser is not None and cid is not None:
                    serial_map[pi][int(ser)] = int(cid)
            last_logs = logs[-25:]
            if o.get("select") and ai == our_idx:
                sel = o["select"]
                opt = sel.get("option") or (sel.get("options") or [{}])[0]
                our_moves.append({"turn": (o.get("current") or {}).get("turn"),
                                  "type": sel.get("type"),
                                  "opt": opt.get("option") if isinstance(opt, dict) else None})
            cur = o.get("current") or {}
            if not cur.get("players"):
                continue
            turn = max(turn, cur.get("turn") or 0)
            last_players = cur
            pl = cur["players"]
            for i in (0, 1):
                if i >= len(pl):
                    continue
                a = (pl[i].get("active") or [None])[0]
                pa = prev_active.get(i)
                if pa is not None and (a is None or (pa.get("id") != a.get("id"))) and (pa.get("hp") or 0) == 0:
                    (our_ko if i == our_idx else opp_ko).append(cname(pa.get("id")))
                prev_active[i] = a
    for pi, seat in ((our_idx, "our_deck"), (1 - our_idx, "opp_deck")):
        deck = sorted(set(serial_map[pi].values()))
        if seat == "our_deck":
            our_deck = deck
        else:
            opp_deck = deck

    def side_board(i):
        out = []
        if last_players and i < len(last_players["players"]):
            p = last_players["players"][i]
            a = (p.get("active") or [None])[0]
            if a and a.get("id") is not None:
                out.append(f"A:{cname(a['id'])}({a.get('hp')}/{a.get('maxHp')})")
            for b in (p.get("bench") or []):
                if b and b.get("id") is not None:
                    out.append(f"B:{cname(b['id'])}({b.get('hp')})")
        return out

    return {"win": win, "turn": turn, "our_deck": our_deck, "opp_deck": opp_deck,
            "opp_arch": arch(opp_deck), "our_arch": arch(our_deck),
            "our_ko": our_ko, "opp_ko": opp_ko,
            "our_board": side_board(our_idx), "opp_board": side_board(1 - our_idx),
            "last_logs": last_logs, "our_moves_tail": our_moves[-14:],
            "teams": info.get("TeamNames") or [],
            "episode_id": re.search(r"episode-(\d+)-replay\.json", f).group(1),
            "file": os.path.basename(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="kaggle_results/our_replays")
    args = ap.parse_args()
    outdir = args.outdir
    load_names(outdir)

    sub_of = {}
    for cf in sorted(glob.glob(os.path.join(outdir, "episodes_*.csv"))):
        sub = os.path.basename(cf).split("_")[1].split(".")[0]
        try:
            with open(cf, encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    key = (row.get("id") or row.get("Id") or "").strip()
                    if key:
                        sub_of[key] = sub
        except Exception as exc:
            print(f"WARN: could not parse {cf}: {exc!r}")

    rows = []
    skipped = []
    for f in sorted(glob.glob(os.path.join(outdir, "episode-*-replay.json"))):
        try:
            d0 = json.load(open(f))
            teams = (d0.get("info") or {}).get("TeamNames") or []
            if "PeterSharps" not in teams or len(teams) < 2:
                continue
            r = walk(f, teams.index("PeterSharps"))
            r["opp"] = r["teams"][1 - teams.index("PeterSharps")]
            r["sub"] = sub_of.get(r["episode_id"], "?")
            rows.append(r)
        except Exception as exc:  # noqa: BLE001 - one bad file must not kill the run
            skipped.append((os.path.basename(f), repr(exc)))
            try:
                os.remove(f)  # drop the poison file so it stops breaking re-runs
            except OSError:
                pass
    if skipped:
        print(f"SKIPPED {len(skipped)} episode file(s): {skipped[:5]}")

    # table
    tpath = os.path.join(outdir, "episodes_table.csv")
    with open(tpath, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["episode_id", "sub", "opp", "win", "turn", "our_arch", "opp_arch",
                    "opp_ko_our", "we_ko", "opp_board", "our_board", "file"])
        for r in rows:
            w.writerow([r["episode_id"], r["sub"], r["opp"], int(r["win"]) if r["win"] is not None else -1,
                        r["turn"], r["our_arch"], r["opp_arch"],
                        "|".join(r["opp_ko"]), "|".join(r["our_ko"]),
                        " ".join(r["opp_board"]), " ".join(r["our_board"]), r["file"]])

    # loss snapshots + keep only loss replays
    ldir = os.path.join(outdir, "loss_replays")
    os.makedirs(ldir, exist_ok=True)
    snaps = []
    for r in rows:
        src = os.path.join(outdir, r["file"])
        if r["win"]:
            if os.path.exists(src):
                os.remove(src)
            continue
        snaps.append({k: r[k] for k in
                      ("episode_id", "sub", "opp", "turn", "opp_arch", "our_arch",
                       "our_ko", "opp_ko", "our_board", "opp_board", "last_logs", "our_moves_tail")})
        if os.path.exists(src):
            shutil.move(src, os.path.join(ldir, r["file"]))
    with open(os.path.join(outdir, "loss_snapshots.jsonl"), "w") as fh:
        for s in snaps:
            fh.write(json.dumps(s, default=str) + "\n")

    # summary
    L = ["# Our episodes summary", f"_fetched by kaggle-our-replays_{rows[0]['sub'] if rows else ''}_", ""]
    by_sub = {}
    for r in rows:
        by_sub.setdefault(r["sub"], []).append(r)
    for sub, rs in sorted(by_sub.items()):
        w_ = sum(1 for r in rs if r["win"])
        L.append(f"## submission {sub}: {len(rs)} episodes, {w_}W-{len(rs)-w_}L = {w_/max(1,len(rs)):.3f}")
        ba = {}
        for r in rs:
            ba.setdefault(r["opp_arch"], [0, 0])
            ba[r["opp_arch"]][0 if r["win"] else 1] += 1
        for a, (ww, ll) in sorted(ba.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
            L.append(f"- vs {a}: {ww}W-{ll}L ({ww/(ww+ll):.2f}) n={ww+ll}")
        bo = {}
        for r in rs:
            bo.setdefault(r["opp"], [0, 0])
            bo[r["opp"]][0 if r["win"] else 1] += 1
        rec = [(o, ww, ll) for o, (ww, ll) in bo.items() if ww + ll >= 2]
        if rec:
            L.append("- recurring opponents (n>=2): " +
                     "; ".join(f"{o} {ww}-{ll}" for o, ww, ll in sorted(rec, key=lambda x: -(x[1] + x[2]))))
        L.append("")
    with open(os.path.join(outdir, "summary.md"), "w") as fh:
        fh.write("\n".join(L))

    print(f"episodes parsed: {len(rows)}  (wins: {sum(1 for r in rows if r['win'])}, "
          f"losses: {sum(1 for r in rows if not r['win'])})")
    print(f"wrote {tpath}, loss_snapshots.jsonl ({len(snaps)} losses), {len(os.listdir(ldir))} loss replays kept")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        outdir = "kaggle_results/our_replays"
        try:
            with open(os.path.join(outdir, "summarize_crash.txt"), "w") as fh:
                fh.write(tb)
        except OSError:
            pass
        print("SUMMARIZE CRASH (traceback in summarize_crash.txt):")
        print(tb)
        raise
