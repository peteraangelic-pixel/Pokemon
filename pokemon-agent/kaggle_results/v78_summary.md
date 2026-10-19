# v78 RL Super - 715.4 Kaggle Rating (NEW BEST)

**Date:** 2026-10-19 22:22 UTC
**Branch:** arena/c87f7a48-pokemon commit f429741
**Bundle:** v78_rl.tar.gz 1.9M flat (no champion.py)

## Results

- **Kaggle live:** 715.4 rating (SubmissionStatus.COMPLETE) - previous best 443.2 (v67_stack) and 415.9 (v70_meta)
- **Local vs v67:** 14-6 0.700 (20 games, Python wrapper) - BC2000 was 7-13 0.350, so BC6000+PPO is +0.35 better vs v67
- **Gauntlet FFI vs top7_live (22 decks x2 =44 games):**
  - BC2000: 37W-7L 0.841 (run 39329640580)
  - BC6000+PPO: 34W-10L 0.773 (run 39334380392) - worse FFI but better Kaggle, suggests Kaggle meta != top7_live
- **Gauntlet Rust:** failed due to missing _build_plan in RL agent (gauntlet_live.py rebind logic), but FFI works

## Model

- D128 L3 GRU128? Actually D256 L4 in model_v2.py but weights from a450 branch are D128? Need to check.
- Weights: BC6000 + PPO 12 iter from a450 branch (params_best.npz 1.9M, 64 tensors)
- BC loss: held-out match 0.969-0.977
- PPO eval: champion 0.63, v67 0.67 after iter 11
- Features: soft lethal +200 gated margin +100/-100, mask dominated, belief GRU, meta-counter, Judge J1

## Fixes applied

- Restored data/cards.json 568K + attacks.json 249K from a450b00f (missing in c87)
- Restored tools/deck_rules.py and tools/archetypes.py
- Fixed gauntlet.yml double prefix pokemon-agent/pokemon-agent/...
- Fixed lib path in train_v2.py to search purelib/platlib

## Pending

- BC2000 version pending Kaggle score (submitted 22:33 UTC, still PENDING at 23:19)
- RL v8/v9 trainings stuck in_progress >2h, cannot cancel via API 403
- Need to build v79 with D256 L4 + GRU128 + BC6000+PPO from scratch once RL training finishes

## Next steps

- Wait for BC2000 score to compare vs 715.4
- Retrain with D256 L4 + GRU128 2.3M params + BC6000 + PPO 20 iter + league 8-12 pilots
- Implement pointer head for card selection (instead of flat 300 logits)
- Add belief state for opponent hand (GRU)
