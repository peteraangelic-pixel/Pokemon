# ARC-AGI-3 experiment log

Every public `[arc-eval]` run publishes its full outcome as a GitHub check
("Public ARC graph evaluation") on the evaluated commit; compact summaries,
transition geometry and frame sketches are in the check output, full
recordings remain a 14-day workflow artifact. This file records decisions and
results that matter across sessions, so an interrupted session can resume from
committed state alone.

## 2026-09-03/04 — bounded public evaluation loop (games: ls20, vc33; 400 actions each)

Scorecard progression over 25 consecutive `[arc-eval]` commits
(oldest → newest):

| ls20 level | vc33 level | scorecard |
| --- | --- | --- |
| 0 | 1 | 0.0014–0.0022 |
| 1 | 1 | 1.787103152557669 |
| 2 | 1 | 5.35853172398624 |

- ls20 advanced 0→1 (`aabfaf0`) and 1→2 (`011a084`); vc33 never left level 1.
- `91ded55`–`5309031` (meter-budget routing) regressed ls20 to level 1;
  recovered at `ade01b1`. Since `ade01b1` the score is **frozen at 5.3585**
  (ls20 `NOT_FINISHED` on level 2, vc33 `NOT_FINISHED` on level 1) across 15+
  eval commits.
- `811d6f5` ("avoid visually revalidated forced tile entries") added blocking of
  tiles that caused a *forced avatar displacement*. Its eval (run
  33782702566) showed the agent falling out of tile navigation into generic
  `graph-simple-frontier` on ls20 level 2 and dying 3× instead of 2×; score
  unchanged. **Reverted in `73d5f2f`** — displacement alone is not reliable
  death evidence (it can be a normal teleport/control mechanic). Do not block
  tiles on displacement evidence again.

Observed ls20 level-2 failure mode (baseline `827f377`, run 33782014515):
after every game-over reset the agent replays the identical corridor route and
repeats the identical fatal decision — entering tile `(10,3)` via action 2
after the badge/control exit sequence — dying at the same geometry twice per
run (steps ~190 and ~318). Each cycle costs ~130 actions and the agent never
sees any level-2 content past that point. Terminal feedback is not retained
across resets.

Observed vc33 failure mode: the entire run stays in `graph-click-frontier`
mode (394/400 actions); the agent has not recognised a structured mechanic on
level 1 at all and dies from edge-band clicks.

## 2026-09-04 — terminal landing guards (iterations 1–2)

Experiment: retain explicit GAME_OVER landing tiles per level
(`(levels_completed, tile)`), treat them as blocked for planning, with public
evidence counters `terminal-landings-seen/learned` and
`terminal-landing-diverted/rerouted`.

- **Iteration 1** (`7807910`, confirmation after ≥2 deaths): mechanism worked
  exactly as designed (`learned: 1`, `rerouted: 29`, ls20 L2 deaths 2 instead
  of the historical repeated pattern; 3rd attempt visibly diverted), but the
  score stayed **5.3585** — the second ~130-step corridor attempt was fully
  wasted confirming the guard, and only ~80 steps of the 400-action budget
  remained to exploit the diverted route (not even enough to re-cross the
  corridor).
- **Iteration 2** (confirmation after ≥1 death): both measured games show a
  deterministic board per level (identical death geometry across every
  attempt in every run), so one observed landing is reliable evidence there;
  the guard is still isolated per level for games whose boards do differ.
  Rationale: turn the second doomed attempt into a fully diverted ~200-step
  exploration instead of burning it on a repeat death.
  Result (`9ff53a7`, 400 steps): ls20 game overs drop from the historical
  repeat-death pattern to two deaths at two *different* tiles
  (`terminal-landings-learned: 2`, `terminal-landing-rerouted: 82`), L0/L1
  mode counts identical to baseline, but score stays **5.3585**. Each ls20
  level-2 attempt costs ~130 actions of corridor approach, so a 400-action
  run fits only ~3 attempts and the 3rd is truncated ~80 steps in.
- **Diagnostic** (temporary EVAL_STEPS=1200, workflow change only, since
  reverted): with the single-death guard the agent learned **8 distinct fatal
  tiles** (`terminal-landings-learned: 8`, `rerouted: 818`, 9 deaths) but
  still did not finish ls20 level 2. Death cadence stayed ~133 actions per
  attempt. **Conclusion: the ls20 plateau is a mechanic wall, not a budget
  artifact** — avoiding fatal tiles one-by-one never completes the level; the
  policy must learn *why* the badge/control-area interactions kill (or how to
  pass them), and per-attempt corridor cost leaves little budget for probing
  that zone.

## Working hypotheses (next steps)

1. ls20 level 2 completion is gated by the badge/control-area mechanic, not by
   repeated deaths. The guard is worth keeping (it converts repeat deaths into
   new-tile discoveries and costs nothing on L0/L1), but the next improvement
   must come from understanding the killing interaction — study the terminal
   transitions *inside* the badge region (from recordings of the guard runs,
   retained 14 days as workflow artifacts) instead of adding more avoidance
   rules.
2. vc33 level 1: 394+ clicks/run stay in `graph-click-frontier` — the policy
   has no structured perception for this game at all. Needs frame-level study
   of vc33 L1 (which visual affordance should be clicked) before any new
   primitive.
3. Reconsider the per-attempt corridor cost (~130 actions) once the L2
   mechanic is understood; e.g. whether level resets could be avoided
   altogether by not dying.

## 2026-09-04 — DECYZJA: wątek ARC-AGI-3 zamknięty

Właściciel repo rezygnuje z ubiegania się o nagrody ARC Prize 2026 (patrz
`ARC_AGI3_PLAN.md`): eligibility (open-source, angielskie write-upy, wywiady/
weryfikacja przy wygranej, KYC) odpada, a realne szanse na leaderboard są
znikome. Brak dalszych publicznych ewaluacji; kod zostaje jako archiwum.
Następny cel: do decyzji właściciela (repo zawiera też wstrzymany wątek
matematyczny Hall/census/gadget).
