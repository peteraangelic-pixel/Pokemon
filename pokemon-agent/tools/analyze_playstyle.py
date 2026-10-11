#!/usr/bin/env python3
"""Analyze playstyle from replays: gust timing, retrieval usage, wall escape.

Extracts from episode JSONs (kaggle_results/top30_live/):
- For each team, how often they play gust (Boss's Orders 1182, Prime Catcher 1088, Pokemon Catcher 1124)
- When they play gust (turn distribution)
- Retrieval usage: Lillie's Determination 1227, Waitress 1235, Night Stretcher 1097, Sacred Ash 1129, Cyrano 1205
- Energy attachment rate
- Wall-related: Crustle wall detection via opponent deck containing Crustle? We approximate via logs.

Usage:
  python tools/analyze_playstyle.py --replays-dir kaggle_results/top30_live --out kaggle_results/top30_live/playstyle.md
"""
from __future__ import annotations
import argparse, json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS_PATH = ROOT / "data" / "cards.json"

def load_cards():
    try:
        data = json.loads(CARDS_PATH.read_text())
        return {c["cardId"]: c.get("name","") for c in data}
    except Exception:
        return {}

CARD_NAMES = load_cards()

# Key card IDs (from cards.json)
GUST_IDS = {1182, 1088, 1124, 1184}  # Boss, Prime Catcher, Pokemon Catcher, Lana's Aid? Actually Lana is not gust but keep
GUST_NAMES = {"Boss's Orders", "Prime Catcher", "Pokémon Catcher", "Counter Catcher"}  # Counter not in list but check
RETRIEVAL_IDS = {1227, 1235, 1097, 1129, 1205, 1219, 1231}  # Lillie Det, Waitress, Night Stretcher, Sacred Ash, Cyrano, Petrel, Dawn
RETRIEVAL_NAMES = {"Lillie's Determination", "Waitress", "Night Stretcher", "Sacred Ash", "Cyrano", "Team Rocket's Petrel", "Dawn"}

ENERGY_IDS = {3,5,19}  # Basic W, Basic P, Telepath etc? We'll treat any energy cardType 5 but use names containing Energy

def analyze_one(path: Path):
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return None
    info = data.get("info") or {}
    teams = info.get("TeamNames") or []
    if len(teams)!=2:
        return None
    rewards = data.get("rewards") or []
    steps = data.get("steps") or []
    # per player stats
    per_player = {0: {"gust_plays": [], "retrieval_plays": [], "energy_plays": [], "turns": []}, 1: {"gust_plays": [], "retrieval_plays": [], "energy_plays": [], "turns": []}}
    # we need turn tracking: current.turn from observation
    # Walk steps, extract logs type 4 with turn
    for step_idx, step in enumerate(steps):
        for seat, ps in enumerate(step):
            obs = ps.get("observation") or {}
            cur = obs.get("current") or {}
            turn = cur.get("turn") if isinstance(cur, dict) else None
            logs = obs.get("logs") or []
            for lg in logs:
                if lg.get("type")!=4:
                    continue
                cid = lg.get("cardId")
                pidx = lg.get("playerIndex")
                if pidx not in (0,1):
                    continue
                name = CARD_NAMES.get(cid, "")
                # classify
                if cid in GUST_IDS or "Boss" in name or "Catcher" in name:
                    per_player[pidx]["gust_plays"].append({"turn": turn, "card": name, "id": cid, "step": step_idx})
                if cid in RETRIEVAL_IDS or any(k in name for k in ["Lillie", "Waitress", "Night Stretcher", "Sacred Ash", "Cyrano", "Petrel", "Dawn"]):
                    per_player[pidx]["retrieval_plays"].append({"turn": turn, "card": name, "id": cid, "step": step_idx})
                if "Energy" in name:
                    per_player[pidx]["energy_plays"].append({"turn": turn, "card": name, "id": cid, "step": step_idx})
    # winner
    winner = None
    if rewards and len(rewards)>=2:
        if rewards[0]==1:
            winner = teams[0]
        elif rewards[1]==1:
            winner = teams[1]
    return {"file": path.name, "teams": teams, "winner": winner, "per_player": per_player}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays-dir", default=str(ROOT / "kaggle_results" / "top30_live"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rdir = Path(args.replays_dir)
    replays = sorted(rdir.glob("episode-*.json"))
    print(f"Found {len(replays)} replays in {rdir}")
    analyzed = []
    for rp in replays:
        a = analyze_one(rp)
        if a:
            analyzed.append(a)

    # aggregate per team
    team_stats = collections.defaultdict(lambda: {"games":0, "wins":0, "gust_total":0, "gust_first_turn_sum":0, "gust_first_turn_cnt":0, "retrieval_total":0, "energy_total":0, "gust_turns": []})
    for a in analyzed:
        teams = a["teams"]
        winner = a["winner"]
        pp = a["per_player"]
        for idx, team in enumerate(teams):
            ts = team_stats[team]
            ts["games"]+=1
            if winner==team:
                ts["wins"]+=1
            gust = pp[idx]["gust_plays"]
            retr = pp[idx]["retrieval_plays"]
            ener = pp[idx]["energy_plays"]
            ts["gust_total"]+=len(gust)
            ts["retrieval_total"]+=len(retr)
            ts["energy_total"]+=len(ener)
            if gust:
                first_turn = min((g["turn"] for g in gust if g["turn"] is not None), default=None)
                if first_turn is not None:
                    ts["gust_first_turn_sum"]+=first_turn
                    ts["gust_first_turn_cnt"]+=1
                    ts["gust_turns"].append(first_turn)
                else:
                    ts["gust_turns"].extend([g["turn"] for g in gust if g["turn"] is not None])

    # build markdown
    lines=[]
    lines.append(f"# Playstyle Analysis — {len(analyzed)} replays from {rdir.name}")
    lines.append("")
    lines.append(f"Total replays analyzed: {len(analyzed)}")
    lines.append("")
    lines.append("## Per-team playstyle (top30)")
    lines.append("")
    lines.append("| Team | Games | Win% | Gust/game | First gust turn avg | Retrieval/game | Energy/game |")
    lines.append("|---|---|---|---|---|---|---|")
    for team, st in sorted(team_stats.items(), key=lambda kv: kv[1]["games"], reverse=True):
        games = st["games"]
        winp = st["wins"]/games if games else 0
        gust_pg = st["gust_total"]/games if games else 0
        first_avg = (st["gust_first_turn_sum"]/st["gust_first_turn_cnt"]) if st["gust_first_turn_cnt"] else 0
        retr_pg = st["retrieval_total"]/games if games else 0
        ener_pg = st["energy_total"]/games if games else 0
        lines.append(f"| {team} | {games} | {winp:.2f} | {gust_pg:.2f} | {first_avg:.1f} | {retr_pg:.2f} | {ener_pg:.2f} |")

    lines.append("")
    lines.append("## Gust timing distribution (all teams)")
    all_gust_turns = []
    for st in team_stats.values():
        all_gust_turns.extend(st["gust_turns"])
    if all_gust_turns:
        from collections import Counter
        cnt = Counter(all_gust_turns)
        lines.append("")
        lines.append("| Turn | Count |")
        lines.append("|---|---|")
        for turn in sorted(cnt):
            lines.append(f"| {turn} | {cnt[turn]} |")
    lines.append("")
    lines.append("## Retrieval breakdown")
    # count retrieval cards across all
    retr_cards = collections.Counter()
    for a in analyzed:
        for idx in (0,1):
            for r in a["per_player"][idx]["retrieval_plays"]:
                retr_cards[r["card"]]+=1
    lines.append("")
    lines.append("| Card | Count |")
    lines.append("|---|---|")
    for card,cnt in retr_cards.most_common(20):
        lines.append(f"| {card} | {cnt} |")

    lines.append("")
    lines.append("## Notes for local recreation")
    lines.append("")
    lines.append("- Gust (Boss 1182) timing: top players use gust early to disrupt setup vs late to close? Check first gust turn avg.")
    lines.append("- Retrieval: Lillie 1227 + Waitress 1235 are main draw; Cyrano 1205 for search; Dawn 1231 for energy accel.")
    lines.append("- To recreate opponent locally: use same deck CSV + mimic their gust timing (e.g. if avg first gust turn 3, force gust on turn 3 in sim).")
    lines.append("- Wall escape: needs Crustle detection — look for opponent decks with Crustle (not yet implemented, need deck archetype).")

    md = "\n".join(lines)
    print(md[:2000])
    if args.out:
        Path(args.out).write_text(md)
        print(f"Wrote {args.out}")

if __name__=="__main__":
    main()
