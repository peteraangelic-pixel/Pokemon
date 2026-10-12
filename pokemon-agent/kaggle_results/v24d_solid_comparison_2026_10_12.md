# v24d solid comparison (2026-10-12)

Interleaved in-process A/B (`tools/ab_interleaved.py`, deck `v12_30_boss4`),
~105k fresh games + earlier v22b/v24d runs. Agents: **v21** (current live
BEST overall), **v22b** (current live #2), **v24d** (v22b + board-development
fix, see `live_loss_forensics_2026_10_12.md`).

## Totals

| config | opponent (fixed ref) | pools | games/agent | v21 | v22b | v24d | Δ v24d−v21 (z) |
|---|---|---|---|---|---|---|---|
| 1 tempo meta | v21 | mirror10 + top30_live (25) | 24.5k | **0.748** | – | 0.744 | −0.44pp (−1.11) |
| 2 developing meta | opp_thickbot | mirror10 + top30_live (25) | 24.5k | **0.753** | 0.579* | 0.743 | −1.01pp (−2.58) |
| 3 key matchups | v24d | 7×500g (see below) | 3.5k | 0.805 | – | **0.823** | +1.77pp (+1.90) |
| 4 field (earlier) | v24d | top30_live (25) | 17.5k | – | **0.810** | 0.808 | – (+0.18pp vs v22b, z+0.42) |
| 5 mirror (earlier) | v24d | mirror10 | 7k | – | 0.582 | **0.584** | – (−0.14pp vs v22b, z−0.17) |

\* v22b vs thickbot from the earlier 7k mirror run (0.579); not re-run at
24.5k.

**Reading: all three agents are locally indistinguishable on the tempo meta
(|z| < 1.1 on totals).** v24d's one real local edge is **stall**:
+8.43pp (z=+5.26) in config 1 and +10.40pp (z=+4.92) in config 3 vs
やる気ミワハルキ (same direction as v22b's stall planner — the development
change independently breaks the frozen endgame). v24d's one real local cost is
**−1.01pp vs thickbot (z=−2.58)**, spread −1…−6pp over most Ogerpon tempo
decks (config 2), offset by +4.43pp vs Bill/Lucario (z=+1.82).

## Config 1 per-pool (25 decks × 700g, opp = v21 ref) — v24d vs v21

worst for v24d: Chonghao_Ogerpon **−5.29pp (z−2.38)** · Bill_Lucario −3.86
(z−1.48) · Majiro_Alakazam −3.43 (z−1.86) · Cristobal_Grookey −3.29 (z−1.72)
· JerryChen_Ogerpon −3.14 (z−1.42)
best for v24d: **Yaruki_stall +8.43pp (z+5.26)** · Raja_Lucario +3.57 (z+2.11)
· Mathieu_Ogerpon +2.71 (z+1.23)
rest: |Δ| ≤ 1.7pp, |z| < 1.3.

## Config 3 key matchups (500g each, opp = v24d ref)

| matchup | v21 | v24d | Δ (z) |
|---|---|---|---|
| leo_turing (Ogerpon #2 live) | 0.758 | 0.758 | 0.00 (0.00) |
| Bill_Vlasak (Lucario) | 0.618 | 0.636 | +1.80 (+0.59) |
| yu_kuo14 (Lucario) | 0.740 | 0.732 | −0.80 (−0.29) |
| **やる気ミワハルキ (stall)** | 0.816 | **0.920** | **+10.40 (+4.92)** |
| Kentaro (Alakazam) | 0.916 | 0.918 | +0.20 (+0.11) |
| Leon_Liu (Dragapult) | 0.912 | 0.916 | +0.40 (+0.23) |
| OceanMix (Lucario) | 0.876 | 0.880 | +0.40 (+0.19) |

## What local CANNOT measure (the whole point)

Live ground truth (116 episodes, `our_replays/`): **v21 49.2%, v22b 43.6%** —
both below 50%. 61/62 live losses = board collapse (empty-bench KO). Against
thickbot, v24d cuts empty-board deaths 94%→86% of losses (200g mode test),
but that converts to zero local win rate because the local meta rewards
one-shot tempo, not bench survival. The local engine's ceiling for this
question is reached: **no local opponent class can discriminate the fix.**

## Verdict

1. No local regression from v24d on the tempo meta (−0.44pp, z−1.11 = noise);
   the −1.01pp vs thickbot is the honest risk and it is spread over Ogerpon
   tempo decks, not a single hole.
2. v24d is the **only** candidate that structurally fixes the live death mode
   (98% of losses), and it independently improves stall (z≈5).
3. v21/v22b/v24d are locally a 3-way tie → the choice is made on the live
   mechanism, not on local μ.

**Recommendation (next reset, 2 ACTIVE slots):**
- **Slot 1: keep v21** (live 49.2% — the proven one).
- **Slot 2: submit v24d** (replaces v22b, live 43.6%) — the controlled
  experiment on the actual loss mechanism. Bundle:
  `bundles/phase1_tuned_v24d_devfix.tar.gz` (smoke-tested, byte-identical to
  `agents/main_heuristic_v24d.py`).
- Pre-registered read-out: after 24–48h, `our_replays` digest (port kit at
  `kaggle_results/port_kit_our_replays/`) → v24d live win rate vs v21's 49.2%.
  Keep if ≥ ~50%, revert slot to v21 if < ~45%.
- Next agent iteration (v25d): threat-aware retreat — never stand a 150/350
  wall into Riptide/Hammer-lanche range with an empty bench (the remaining
  death sub-mode after development is fixed).
