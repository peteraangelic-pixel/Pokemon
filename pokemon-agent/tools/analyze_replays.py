#!/usr/bin/env python3
"""Analyze PTCG replays — extract opponent decks, win/loss, and recommendations.

This is the PTCG equivalent of Kaggriculture's replay analysis.

It reads JSON replays from kaggle_results/replays/ (produced by fetch_replays.py)
and produces a human-readable report with:
- win rate vs each opponent team
- opponent deck archetypes (energy count, gust presence, etc.)
- what beats us
- recommendations for next deck/agent iteration

Usage
-----
    python tools/analyze_replays.py --replays-dir kaggle_results/replays
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAYS = ROOT / "kaggle_results" / "replays"


def load_cards():
    try:
        data = json.loads((ROOT / "data" / "cards.json").read_text())
        return {c["cardId"]: c for c in data}
    except Exception:
        return {}


CARDS = load_cards()


def deck_summary(deck: list[int]) -> dict:
    cnt = collections.Counter(deck)
    energy = sum(1 for cid in deck if CARDS.get(cid, {}).get("cardType") == 5)
    # Basic energy breakdown
    basic_energy = collections.Counter()
    for cid in deck:
        c = CARDS.get(cid)
        if c and c.get("cardType") == 5:
            basic_energy[c["name"]] += 1

    pokemon = []
    trainers = []
    gust = 0
    for cid, n in cnt.most_common():
        c = CARDS.get(cid)
        if not c:
            continue
        name = c["name"]
        ct = c.get("cardType")
        if ct == 0:
            pokemon.append(f"{name} x{n}")
        elif ct >= 1:
            trainers.append(f"{name} x{n}")
            if "boss" in name.lower() or "catcher" in name.lower() or "counter catcher" in name.lower():
                gust += n

    return {
        "energy": energy,
        "basic_energy": dict(basic_energy),
        "pokemon": pokemon,
        "trainers": trainers,
        "gust": gust,
        "counts": cnt,
    }


def analyze_replay(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        return {"file": path.name, "error": str(exc)}

    info = data.get("info", {})
    teams = info.get("TeamNames", [])
    rewards = data.get("rewards", [])
    steps = data.get("steps", [])

    winner_idx = -1
    if rewards:
        if rewards[0] == 1:
            winner_idx = 0
        elif len(rewards) > 1 and rewards[1] == 1:
            winner_idx = 1

    winner = teams[winner_idx] if 0 <= winner_idx < len(teams) else "draw"

    # Extract decks from step 1 (first action after empty)
    decks = []
    if len(steps) > 1:
        s1 = steps[1]
        for idx, ps in enumerate(s1):
            act = ps.get("action")
            if isinstance(act, list) and len(act) == 60:
                decks.append((idx, act))

    deck_summaries = []
    for p_idx, deck in decks:
        summ = deck_summary(deck)
        team = teams[p_idx] if p_idx < len(teams) else f"P{p_idx}"
        deck_summaries.append((team, summ))

    return {
        "file": path.name,
        "teams": teams,
        "winner": winner,
        "winner_idx": winner_idx,
        "steps": len(steps),
        "decks": deck_summaries,
        "rewards": rewards,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays-dir", default=str(DEFAULT_REPLAYS))
    ap.add_argument("--out", default=None, help="output markdown path")
    args = ap.parse_args()

    replays_dir = Path(args.replays_dir)
    if not replays_dir.exists():
        print(f"replays dir {replays_dir} not found", file=sys.stderr)
        return 1

    replays = sorted(replays_dir.glob("episode-*.json"))
    print(f"Found {len(replays)} replays in {replays_dir}")

    analyzed = []
    for rp in replays:
        a = analyze_replay(rp)
        if a:
            analyzed.append(a)

    # Group by opponent
    by_opponent = collections.Counter()
    wins_vs = collections.Counter()
    losses_vs = collections.Counter()
    # Find our team name — assume Lauresowe 3D is us, but try to infer
    our_teams = collections.Counter()
    for a in analyzed:
        for team, _ in a.get("decks", []):
            our_teams[team] += 1
    # Our team is the one appearing in most replays (should be Lauresowe 3D)
    our_team = our_teams.most_common(1)[0][0] if our_teams else "Lauresowe 3D"
    print(f"Inferred our team: {our_team} (appears {our_teams[our_team]} times)")

    for a in analyzed:
        teams = a.get("teams", [])
        winner = a.get("winner")
        if len(teams) != 2:
            continue
        opp = teams[0] if teams[1] == our_team else teams[1] if teams[0] == our_team else None
        if not opp:
            # If our team not in this replay, skip for win/loss
            continue
        by_opponent[opp] += 1
        if winner == our_team:
            wins_vs[opp] += 1
        elif winner == opp:
            losses_vs[opp] += 1

    # Deck meta analysis
    all_decks = []
    for a in analyzed:
        for team, summ in a.get("decks", []):
            all_decks.append((team, summ))

    # Find common archetypes
    energy_dist = collections.Counter()
    gust_dist = collections.Counter()
    for team, summ in all_decks:
        energy_dist[summ["energy"]] += 1
        gust_dist[summ["gust"]] += 1

    # Build markdown report
    lines = []
    lines.append(f"# Replay Analysis — {len(analyzed)} replays")
    lines.append("")
    lines.append(f"Our team (inferred): **{our_team}**")
    lines.append("")
    lines.append(f"Total replays: {len(analyzed)}")
    lines.append("")
    lines.append("## Win/Loss vs opponents")
    lines.append("")
    lines.append("| Opponent | Games | Wins | Losses | Win rate |")
    lines.append("|---|---|---|---|---|")
    for opp, total in by_opponent.most_common():
        w = wins_vs[opp]
        l = losses_vs[opp]
        rate = w / total if total else 0
        lines.append(f"| {opp} | {total} | {w} | {l} | {rate:.2f} |")
    lines.append("")

    lines.append("## Deck meta (all decks seen)")
    lines.append("")
    lines.append(f"- Energy distribution: {dict(energy_dist)}")
    lines.append(f"- Gust (Boss/Catcher) distribution: {dict(gust_dist)}")
    lines.append("")
    lines.append("### Example decks that beat us")
    lines.append("")
    for a in analyzed:
        if a.get("winner") != our_team and our_team in a.get("teams", []):
            # This is a loss for us
            for team, summ in a.get("decks", []):
                if team != our_team:
                    lines.append(f"- **{a['file']}** vs {team} (winner {a['winner']}, {a['steps']} steps)")
                    lines.append(f"  - Energy: {summ['energy']}, Gust: {summ['gust']}")
                    lines.append(f"  - Pokemon: {', '.join(summ['pokemon'][:4])}")
                    lines.append(f"  - Trainers: {', '.join(summ['trainers'][:6])}")
                    lines.append("")
                    break

    lines.append("### Example decks we beat")
    lines.append("")
    for a in analyzed:
        if a.get("winner") == our_team:
            for team, summ in a.get("decks", []):
                if team != our_team:
                    lines.append(f"- **{a['file']}** vs {team} ({a['steps']} steps)")
                    lines.append(f"  - Energy: {summ['energy']}, Gust: {summ['gust']}")
                    lines.append(f"  - Pokemon: {', '.join(summ['pokemon'][:4])}")
                    lines.append("")
                    break

    lines.append("## Recommendations")
    lines.append("")
    # Simple heuristics
    if gust_dist[0] > len(all_decks) * 0.5:
        lines.append("- More than half of decks have 0 gust. Adding 2x Boss's Orders (id 1182) could give us free wins vs walls (Crustle, Sylveon) — we saw 0.30→0.61 vs Sylveon with just play improvement, gust would push it further.")
        lines.append("")
    # Energy
    avg_energy = sum(k * v for k, v in energy_dist.items()) / sum(energy_dist.values()) if energy_dist else 33
    lines.append(f"- Average energy in meta: {avg_energy:.1f}. Our current 33 is high; top players use 26-30. Cutting 3-7 energy for trainers (Boss, Cyrano, Night Stretcher) trades ~20-40 damage per Hammer-lanche for consistency.")
    lines.append("")
    lines.append("- Mirror losses (identical deck) suggest play, not deck, is the bottleneck. Lethal DFS and better energy attachment prioritization are next.")
    lines.append("")

    md = "\n".join(lines)
    print(md)

    out_path = Path(args.out) if args.out else replays_dir / "analysis.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"\nWrote {out_path}")

    # Also write json
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(analyzed, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
