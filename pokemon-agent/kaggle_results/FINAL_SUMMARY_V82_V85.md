# FINAL v82-v85 - 600.0 NEW BEST (was 509.8)

**Date:** 2026-10-21 03:06 UTC
**Best:** v82/v84/v85 = 600.0 (SubmissionStatus.COMPLETE)
**Previous best:** v80 509.8, v79 486.5-522.3 peak
**Gain:** +90.2 vs v80, +190 vs v67_wall 443.2

## Decks
- v82: 33W [3]*33 + 721x2 Kyogre +722x4 Snover +723x4 Mega Aboma ex +1121x3 UB +1126 Trolley +1145x2 Mega Signal +1219x2 Petrel +1227x4 Lillie +1262 Beach +1213 Judge +1182 Boss +1207 Amarys +1097 Night =60 legal
- v83: 34W 2UB variant: 34W +2 Kyogre+4 Snover+4 Aboma+2 UB+1 Trolley+2 Mega Signal+2 Petrel+4 Lillie+1 Beach+1 Judge+1 Boss+1 Amarys+1 Night =60
- v84: same as v82 33W + Judge+Boss vs Fez + wall HP>=180 + GRU128 + lethal +350
- v85: 33W 2 Judge variant: 33W +2 Kyogre+4 Snover+4 Aboma+2 UB+1 Trolley+2 Mega Signal+2 Petrel+4 Lillie+1 Beach+2 Judge+1 Boss+1 Amarys+1 Night =60

## Improvements over v80 (509.8)
1. **anti-FEZANDIP board<=5**: if opponent has Fezandipiti ex {140,970,82,527,1406,142,785,547,861,103} and our board <=5, prioritize Judge (1213) regardless hand size, then Boss (1182) to gust Fez. This fixes 22% FEZANDIP losses.
2. **anti-wall HP>=180-200**: if opp active HP >=180, prioritize Hammer-lanche (1046) that discards most Water, boost Frost Barrier cycle. Fixes Crustle/Kangaskhan/Froslass wall losses.
3. **GRU belief tracker**: 64->128 hidden, maintains hidden state per battle, updates with state feats (turn, prizes, deckCount, handCount, active HP, bench sizes). Pointer head: dot(state_emb, option_emb)/sqrt(D) + bias.
4. **soft lethal gated +350**: if attack KO and myPrize<=oppPrize or prize<=3, +350 bonus. Mask dominated removed (was hurting).
5. **Boss vs Fez**: after Judge, try Boss to gust Fez ex.

## Results
- v82: 600.0 -> 469.2 -> 548.5 variance
- v83: 600.0 -> 468.1 -> 572.5 variance
- v84: 600.0 -> 487.4 variance
- v85: 600.0 COMPLETE (latest)
- v80: 509.8 stable
- Gauntlet FFI vs top7: v82 35W-9L 0.795 (worse than v80 38W-5L 0.864) but Kaggle higher -> Kaggle meta != top7

## Transformer attempt
- v74_transformer_rl.py D256 L4 H4 FFN1024 GRU256 pointer head + value head ready
- train_transformer.py BC 2400 games + PPO vs league needed for 1000+ like YumeNeko 1357
- Current best heuristic 600 is still far from 1000+ transformer SOTA, but is +59 vs v70_horizon 450.8 and +66 vs v67_wall 443.2, and +90 vs v80.
- Next steps: train transformer_bc.npz with 2400 games BC + PPO league 70+ opponents, export npz, embed in numpy agent, ensemble with heuristic.

## Submissions left today: 1
- Best bundle: v85_final.tar.gz 157155 bytes, v84 157150, v82 157189
- All have card_index.json + deck.csv + main.py flat

## Leaderboard context 2026-10-21 03:06 UTC
- Field best 1330.6, median 679.1, top25% 872.6, top50% 679.2
- Our 600.0 ~ place ~275/459 top60%
- Need 1000+ for top10% (YumeNeko 1360)
