# Diagnosis: where Franzen's M2 solution loses points

Data: `ops/results/r005-output/out_dfranzen__arc-agi-3-milestone-2-solution/benchmark.json`
(his public v3 run: 25 demo games × 4 passes = 100 runs, 8h11m, RTX PRO 6000, 2026-10-03).
Transcripts of the weakest games (pass 0): `ops/results/r006-output/.../transcripts/`.

## Scoring recap (TAAF mirror of arc_agi scorecard)
Per level `min(115, (human_actions / agent_actions)^2 * 100)`, weight = level index (1..n).
Final = weighted mean, **capped at (sum of weights of completed levels) / (total weight)**.
Every action counts, including RESET and actions of failed attempts.
Later levels weigh more: for a 7-level game, levels 1–3 are only 21 % of the maximum.

## Numbers (100 runs, demo set)
| | points |
|---|---|
| mean score | **46.49** (LB of the same code: 27.89; reruns 21–31) |
| mean completion ceiling (score if every solved level were ≥ human efficiency) | 49.12 |
| **lost to unsolved levels** | **50.9** |
| lost to inefficiency on solved levels | **2.6** |

- Solved levels: 417. Agent actions / human actions: p10 0.32, p25 0.46, **median 0.64**, p75 0.94, p90 1.34.
  80 % of solved levels already use fewer actions than the human baseline; only 4 % use > 2×.
- 67 / 100 runs end `gave_up` (budget/scheduler), 33 `won`.
- Levels completed: 0:7, 1:18, 2:8, 3:10, 4:12, 5:5, 6:18, 7:7, 8:12, 9:3.
- Noise: mean per-game std across the 4 passes = 15 pts; a single-pass 25-game mean has sd ≈ 3.9.

**Conclusion: action efficiency is not the problem. Points are lost because levels are not
solved in the compute each game gets.** A shortest-path solver would recover at most ~2.6 pts.

## What the transcripts of stuck games show (first read)
- The model already writes its own Python simulator of the mechanics. In sk48 its model
  "matched reality 16/16 actions"; the failure was the **win-condition hypothesis**
  (it reproduced the legend layout and nothing happened). The failure is in understanding the game, not in
  search speed. Speeding up the search (e.g. Rust) does not address this.
- Very long thinking per turn (≈ 2–12k tokens), few turns (18–99 analysis steps per game).
- The priority scheduler starves games without progress: sk48 got 18 minutes
  (14:09–14:26) and ~64k tokens out of an 8-hour run.
- The system prompt says "Optimize for as few in-game actions as possible", yet the agent
  already uses only 0.64× human actions. It trades cheap actions for expensive tokens.

## Levers, ranked by expected value
1. **Tokens per solved level**: let the model probe more and deliberate less (there is
   ~1.5× action headroom before the score drops), with shorter turns and anti-verbosity guidance.
2. **Throughput** (tok/s): measurable in short save runs without spending a submission.
   Peak decode: Franzen 946, lordhansolo 1135, sirikilohit 1159 tok/s.
3. **Goal inference when stuck**: an explicit hypothesis ledger of tested and falsified
   win conditions, plus a strategy audit.
4. Scheduler: compute allocation between easy and stuck games.
