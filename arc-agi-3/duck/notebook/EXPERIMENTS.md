# Experiment ledger (save runs: 10 demo games x 48 min, 1 pass)

Eval set: cn04 dc22 g50t ka59 ls20 m0r0 s5i5 sc25 su15 tn36. Per-game single-run spread is huge
(Franzen's own 4 passes: m0r0 0-100, tn36 3.6-100, cn04 4.8-47.6), so a single 10-game run only detects
effects of roughly +10 or more; behaviour metrics from transcripts are the primary readout.

| run | variant | mean | notes |
|---|---|---|---|
| Franzen 4x25 | baseline | 29.48 (these 10 games, mean of 4 passes) | |
| r007 | v2 think-less (patch 0001) | 30.54 | noise; actions/baseline barely moved |
| r013 | v3 world model (patch 0002, tools + prompt only) | 29.02 | **not adopted**: model_state/model_step defined in 1/10 games (s5i5: 32/32 transitions predicted, level-3 win predicted by model_goal, then KeyError on level 4 never fixed). plan() never called. |
| r015 | v4 = v3 + per-turn world-model status (ARC3_WORLD_MODEL_NUDGE) | **23.11** | adopted in 7/10 games, but models were inaccurate: automatic checks 283/813 transitions predicted overall (ls20 0/213, tn36 0/199, m0r0 42/87 + 15 errors, dc22 82/130, ka59 105/123, s5i5 29/30). plan() found a plan 2 times (dc22). Fewer actions (1638 vs 2318 in v3), fewer levels (28 vs 35). Exact-match states with volatile fields (step counter, budget bar, raw pixel sets) mismatch every transition; the agent mostly kept acting regardless. |

Per game r013 (v3): cn04 47.6, dc22 26.6, g50t 21.3, ka59 21.4, ls20 21.8, m0r0 14.3, s5i5 16.7, sc25 64.3, su15 13.3, tn36 42.8.

Per game r015 (v4): cn04 13.5, dc22 14.3, g50t 10.0, ka59 8.4, ls20 20.8, m0r0 47.6, s5i5 1.8, sc25 71.4, su15 13.3, tn36 29.9.

## Verdict on the executable world model (patch 0002)
- As an optional tool (v3), it is ignored and changes nothing.
- When enforced (v4), it costs thinking tokens and actions, and at this model's capability the models are too inaccurate for plan() to help: -6 points (within noise, but the action/level counts point the same way).
- If it is revisited: report per-field accuracy instead of exact match, let the model mark volatile fields, and nudge only on stuck levels (e.g. after the stuck audit fires), never on easy levels.
