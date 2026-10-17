# SUBMISSION_LOG

| Date | Bundle | Changes / Hypothesis | μ rating after 24h | σ | Notes |
|------|--------|----------------------|--------------------|---|-------|
| 2026-10-11 | v10_34_sig4 0.932 top7 | Best weighted 0.777 vs 40 decks (top7+losses+walls) | 372.1 | - | Overfit top7, weak vs weak players |
| 2026-10-13 | v25_knobs_35w | Knobs 0.6291 weighted +0.80 | 440.3 | - | Best so far, but bench wipe 48% |
| 2026-10-14 | v34_thickWalls | Thick walls KO80 | 401.4 | - | Fixes thin vs weak |
| 2026-10-14 | v36_adaptive | Kaggriculture adaptive | 407.9 | - | |
| 2026-10-14 | v48_cem2best_imit | CEM2 + BC60 113 replays 0.8655 hard6 0.772 | 404.9 | - | |
| 2026-10-15 | v55_mirror_a450 | Mirror | 365.3 | - | |
| 2026-10-15 | v56_tuned_a450 (v56T) | Tuned 34W | 423.9 | - | Wall reference, best wall 0.825 |
| 2026-10-16 | v59_10k_1M_772val | Policy 10k games 998k decisions 0.772 val_acc 142g/s mt | 406.6 (57261105) / 381.3 (57249391) | - | Policy BC, 0.492 vs trolley on 4800g harness |
| 2026-10-16 13:32 UTC | v69_alakazam_simple_652 (57270737) | Simple deck 4x Alakazam 11E, hybrid overrides, 0.652 top30 5g (135W?), 0.825 walls 10g, 0.642 broad | **373.5 COMPLETE** 41ep 18W-23L=0.439 | - | BELOW wall 423.9. Breakdown: KYOGRE mirror 7-10 0.41 n=17, ? (Kangaskhan+Crustle) 2-7 0.22 n=9, MEOWTH+FEZ 2-3 0.40, FEZ 1-2, LUCARIO 6-0 1.0. Bench collapse 5/23=21.7% empty our_board, turns 5-14 early. Second-branch verification: same agent on their 4800g harness trolley 0.492 wall 0.520 grid 0.614 ~= their v65 0.611, while our 5-10g/deck harness inflated 0.652/0.825. CEM best val 0.467 overfit. Loss mode dominant: board wipe with unused prizes (4-1 lead -> last mon dies 1 vs 5, Abra promotion). |
| 2026-10-16 | v70_alakazam_endgame_632 (not yet submitted) | Endgame bench guard >=2, recovery Night Stretcher/Sacred Ash when board<=2, no last Abra promotion, fix PLAY area bug, embed card_index | pending | - | Local: top30 10g 0.615 (vs v69 0.619), broad 0.632 (vs 0.622), Mengfei wall 0.50 (vs v69 0.15 +35pp), walls 0.617-0.633. Should improve live ? category 2-7. Hybrid deck v71 with Toucannon 0.607 top30 0.40 Mengfei (worse than v70). Best candidate for next submit is v70 with simple deck. |
| 2026-10-17 01:24 UTC | v70g_alakazam_endgame_2am_final_tokenfix (57290256) | v70 endgame bench>=2 guard, recovery, no last Abra — 0.596 top30_live 270g ±0.059 (161W-109L), pool_v3 80g 0.637±0.105 (51W-29L), Mengfei 0.45-0.50 vs old 0.15. Policy iter6 from second branch (0.511 vs prev, 0.544 vs seed) tested 0.525 pool_v3 vs v70 0.637, 80ms/step vs 8ms heuristic, slower 750x, worse. Toucannon hybrid v71 0.581 top30 vs v70 0.596. Distinct bundle name per 2026-10-16 08:33 rule. Fixed submit workflow: added KAGGLE_API_TOKEN support (was failing auth), fixed log path ../kaggle_results -> kaggle_results. Submitted via push trigger after 02:00 Warsaw per 2026-10-15 23:19 permission, 5 slots free. | **PENDING** 57290256 01:24 UTC, 4 remaining today | - | Best heuristic so far. Gaps fixed per second branch: bench_pc.sh PG workload (rollout 10k + convert + JAX train 1 epoch) vs heuristic g/s, Alakazam pilot Rust port alakazam.rs + bench_local_v2 --mode alakazam paired seeds CI weighted. |

## Lessons
- Small-sample harness (5-10g/deck) overpromises: 0.652/0.825 -> live 373.5. Need 4800g validation (600g per group, strong pilots, replications) as second branch does.
- Bench wipe is dominant loss: leading 4-1 prizes lose because last Pokémon dies board 1 vs 5. Fix: endgame bench discipline >=2 behind active, recovery timing, never promote last Abra 50 HP.
- Simple deck 11E beats YumeNeko vs Crustle but loses to Kangaskhan 300 HP (needs 15 cards hand). Hybrid 3x Alakazam +2x Toucannon +11E +3 Boss helps via Boss cheap prize race.
- CEM overfits: best val 0.467 on small harness, 0.583 worst5 vs full 0.556 < default 0.652.
- Policy ceiling: BC seed 0.153 vs trolley -> 0.422 with hybrid-v2+simple, lr 8e-4 x3 epochs (was 1e-4 x1 plateau), 40k games x6 iters needed for 1000+.

## Slots
- Only last 2 submissions active for finals. Currently active: 57270737 (373.5) and 57261105 (406.6). 2 slots remaining per log, but per user we have 5 slots free? Actually log shows 2 remaining after v69. Do not auto-submit without permission. Use distinct bundle names.
