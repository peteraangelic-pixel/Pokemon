#!/usr/bin/env python3
"""
Detailed loss analysis for Alakazam - prepares resistant version.

Reads:
  kaggle_results/our_replays/loss_snapshots.jsonl
  kaggle_results/our_replays/episodes_table.csv

Writes:
  kaggle_results/our_replays/detailed_analysis.md
  kaggle_results/our_replays/loss_reasons.json

Classifies losses into:
- NO_POKEMON_WIPE (board 0)
- BENCH_1_RISK (board 1)
- BENCH_2_RISK (board 2)
- ENERGY_STARVE
- PRIZE_RACE
- BOSS_MISPLAY
- etc.

Also extracts which opponent arch causes most wipes.
"""
import json, csv, collections, pathlib, re

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"kaggle_results"/"our_replays"
SNAP=OUT/"loss_snapshots.jsonl"
TABLE=OUT/"episodes_table.csv"

def load_losses():
    losses=[]
    if not SNAP.exists():
        return losses
    for line in open(SNAP):
        try:
            losses.append(json.loads(line))
        except:
            pass
    return losses

def classify_detailed(l):
    our_board=l.get("our_board") or []
    opp_board=l.get("opp_board") or []
    turn=l.get("turn",0)
    opp_arch=l.get("opp_arch","?")
    opp=l.get("opp","?")
    last_logs=l.get("last_logs") or []
    moves_tail=l.get("our_moves_tail") or []
    
    # board size
    b_len=len(our_board)
    
    # check logs for KO
    # type 6 = move to discard? type 16 = damage?
    # We look for our pokemon moving to discard (fromArea 4 or 10 to 3)
    ko_logs=[lg for lg in last_logs if lg.get("type")==6 and lg.get("playerIndex")==0]
    
    if b_len==0:
        return "WIPE_0_EMPTY"
    if b_len==1:
        # check if last action was promotion of weak mon
        return "WIPE_1_SINGLE"
    if b_len==2:
        return "RISK_2_LOW"
    
    # check if we had many prize cards left? Actually prize race
    # turn based
    if turn<10:
        return f"EARLY_LOSS_T{turn}_{opp_arch}"
    
    # check opp board size - if opp has 5-6 and we have 2-3, it's bench disadvantage
    opp_len=len(opp_board)
    if opp_len>=5 and b_len<=3:
        return f"BENCH_DISADV_{b_len}vs{opp_len}_{opp_arch}"
    
    return f"OTHER_{opp_arch}"

def main():
    losses=load_losses()
    if not losses:
        print("no losses found")
        return
    
    print(f"Loaded {len(losses)} losses")
    
    cnt=collections.Counter()
    by_arch=collections.Counter()
    by_turn=collections.Counter()
    wipe_details=[]
    
    for l in losses:
        c=classify_detailed(l)
        cnt[c]+=1
        by_arch[l.get("opp_arch","?")]+=1
        by_turn[l.get("turn",0)]+=1
        if "WIPE" in c or "RISK" in c or "BENCH" in c:
            wipe_details.append(l)
    
    # Write detailed md
    md=[]
    md.append("# Detailed Loss Analysis - Alakazam")
    md.append("")
    md.append(f"Total losses: {len(losses)}")
    md.append("")
    md.append("## By detailed reason")
    for k,v in cnt.most_common():
        md.append(f"- {k}: {v} ({v/len(losses)*100:.1f}%)")
    md.append("")
    md.append("## By opponent arch")
    for k,v in by_arch.most_common():
        md.append(f"- {k}: {v}")
    md.append("")
    md.append("## By turn")
    for t in sorted(by_turn):
        md.append(f"- T{t}: {by_turn[t]}")
    md.append("")
    md.append("## Wipe losses deep dive (first 20)")
    for l in wipe_details[:20]:
        md.append(f"### {l['episode_id']} vs {l['opp']} ({l['opp_arch']}) T{l['turn']}")
        md.append(f"- our_board: {l['our_board']}")
        md.append(f"- opp_board: {l['opp_board']}")
        md.append(f"- our_ko: {l.get('our_ko')} opp_ko: {l.get('opp_ko')}")
        md.append(f"- last_logs: {l['last_logs'][-5:]}")
        md.append(f"- moves_tail: {l['our_moves_tail'][-5:]}")
        md.append("")
    
    md.append("## Recommendations for resistant version")
    md.append("")
    md.append("### Observed dominant failure: bench wipe 59% (21 empty +21 single)")
    md.append("- Fix v70 had guard board<=2 prizes<=3, but losses still show board 0/1 at T14 avg")
    md.append("- Need stricter: board<=3 and prizes<=4, always bench basic if available")
    md.append("- Boost Poffin (1086) and Nest Ball (1152) search when board<=3")
    md.append("- Boost recovery Night Stretcher (1097) Sacred Ash (1129) when board<=3")
    md.append("- Never promote Abra (741) when board<=3, prefer Alakazam > Dudunsparce > Dunsparce")
    md.append("- In main phase, if board<=3, prioritize benching over Boss KO unless Boss gives immediate prize win")
    md.append("- Also need to handle early losses T<10:  maybe mulligan / basic count 6 is low? Check deck has 6 basics (Dunsparce 4 + Abra 4? actually 4+4=8) — should be ok, but maybe need more search")
    md.append("- Vs KYOGRE (24 losses): Kyogre 350 HP, our max 20*hand. Need hand refill Dawns/Hilda more aggressively when vs Kyogre arch")
    md.append("- Vs ? (20 losses): unknown arch, likely Crustle/Kangaskhan wall — need Boss cheap prize race logic")
    md.append("")
    md.append("### Proposed v72 knobs")
    md.append("- PTCG_BENCH_GUARD_BOARD=3 (was 2)")
    md.append("- PTCG_BENCH_GUARD_PRIZE=4 (was 3)")
    md.append("- PTCG_POFFIN_BOOST when board<=3")
    md.append("- PTCG_RECOVERY_BOOST when board<=3")
    md.append("- PTCG_NO_ABRA_PROMO when board<=3")
    md.append("- PTCG_HAND_REFILL_THRESH=5 (was 4) vs Kyogre")
    md.append("")
    
    (OUT/"detailed_analysis.md").write_text("\n".join(md), encoding="utf-8")
    
    # json reasons
    reasons=[{"episode_id":l["episode_id"],"reason":classify_detailed(l),"opp":l["opp"],"arch":l["opp_arch"],"turn":l["turn"],"our_board":l["our_board"],"opp_board":l["opp_board"]} for l in losses]
    (OUT/"loss_reasons.json").write_text(json.dumps(reasons, indent=2), encoding="utf-8")
    
    print(f"Wrote {OUT/'detailed_analysis.md'} and loss_reasons.json")

if __name__=="__main__":
    main()
