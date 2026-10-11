# DISCOVERIES.md — cross-branch knowledge base

_Written 2026-10-11 ~21:00 UTC on `arena/a450b00f-pokemon` after a ~65k-game day
(FFI local + 43.6k paired games on a 13-job GitHub Actions matrix).
TL;DR po polsku na końcu. Intended for ANY branch/session working on this
competition: read this before designing agents, tests or submissions._

---

## 0. TL;DR for agents picking this project up

1. **v11 + 30W (`v12_30_boss4` deck) is the verified optimum** of the heuristic
   family; weight-space search is exhausted (160+ candidates two branches,
   40-parallel screening best 0.684).
2. **v21 (archetype-scan hybrid) is the first config to beat it
   statistically: +1.10pp over 43 600 PAIRED games (≈3.4σ), 12/13 jobs ≥0** —
   gains: stall +4.2pp, mirror35W +3.5pp, Bill Vlasak (#1 live) +2.5pp,
   leo_turing +2.4pp, top30 +2.3pp, broad 0 to +1.9pp. Agent:
   `agents/main_heuristic_v21.py`, bundle `bundles/phase1_tuned_v21_hybrid.tar.gz`.
3. **Before v21, every "improvement layer" (v18/v19b) was DEAD CODE** — it
   compared v11 to v11. Rule: if your agent references an undefined symbol and
   has `except: pass` anywhere, it silently no-ops. Verify namespace after load.
4. Draws vs stall were an **infinite Riptide/Hammer self-mill loop**; breaking
   it converts ~12% draws into wins (0.78 → 0.86 vs the stall team).
5. Test methodology: **paired A/B in the same run, ≥600g per critical matchup
   with repeats, or a matrix** (how-to in §8). Noise floor ±3pp @600g per
   matchup; 5–20g numbers are noise, full stop.

---

## 1. DEAD CODE pattern — cross-branch comparisons were void (2026-10-11)

`agents/main_heuristic_v18.py`, `v19b.py` (and their bundles) append a rules
layer referencing `MIRROR_IDS`, `RIPTIDE_ID`, `HAMMER_ID`, `WALL_IDS` — **none
of which are defined anywhere in the v11 family**. The `NameError` is swallowed
by the layer's `except Exception: pass`, so the wrapper scores the base result
and the agent plays as v11.

- Verified programmatically: after `import`, none of the four symbols exist in
  the module namespace; `PLAN` loads fine.
- Consequences: all "v18 vs v11" comparisons on ALL branches (incl. "+5.4pp",
  "top30 0.814 @100g", "broad 0.641 @100g") were **v11 vs v11 = noise**.
  Only v19 (different, non-wrapper rules elsewhere in the file) actually
  differed — and was a catastrophe (0.591 top30 / 0.536 broad @30g, confirmed
  independently by two branches).
- **Check before trusting any agent variant:**
  ```python
  m = load(agent_file)
  assert m._score_main_option is not m._score_main_option_original  # wrapper actually wired
  assert all(hasattr(m, s) for s in symbols_the_wrapper_uses)       # no silent NameError
  ```

## 2. Kaggle loader boundary — wrapper MUST be defined BEFORE `def agent()`

Kaggle's loader picks the LAST function named `agent`-candidate heuristics;
empirically (build_submission.py gate): a wrapper function defined AFTER
`def agent(...)` gets picked **instead of `agent`** → submission plays garbage.
`build_submission.py --smoke` catches this ("REFUSING TO SHIP") — always build
through it. v21 needed its rules block spliced before `def agent`
(sanitized post-splice: stall 0.910, top30-half 0.812 — unchanged behavior).
This is the second, independent reason v18/v19b bundles could never have worked.

## 3. Engine & observation facts (libcg.so FFI, verified with tools/gauntlet_ffi_dbg.py)

- Opponent's **deck is NOT visible** (only `deckCount`); their **hand is None**.
- **VISIBLE for archetype scanning:** their active + bench pokemon **ids**,
  their **discard pile** (ids), both players' `deckCount`, `prize` lists,
  statuses, energies on board pokemon.
- `prize` semantics: entries are `None/'N'` while unclaimed; the list SHRINKS
  as that player TAKES prizes (empty = all taken). winFlags stay (0,0) —
  rely on `result`.
- `result == 2` = draw. **The engine does NOT enforce deckout on the draw
  step** → if both decks are empty and nobody can take a prize, the game loops
  forever (our step-limit 5001 ends it as a draw; live Kaggle presumably caps
  differently). Never assume deckout resolves the game.
- Attack IDs are card_index-scoped: Riptide=1042, Hammer-lanche=1046,
  Frost Barrier=1047, Swirling Waves=1043 in THIS repo's numbering. Other
  branches had different numbering — always read `assets/card_index.json`
  (structure: `raw['cards'][id]`, `raw['attacks'][id]`).
- Card facts used by v21/v20 rules: Mega Abomasnow ex (723) 350HP **pt=4**;
  Kyogre (721)/Snover (722) pt=1; Mega Lucario ex (678) 340HP pt=4,
  Mega Brave 270 one-shots Kyogre/Snover and KOs an Abomasnow at ≥80 damage;
  Aura Jab 130 re-attaches 3 Fighting from discard.

## 4. Draws → wins: the stall mechanism and the fix

Instrumented 100–200g vs the utility/stall team (やる気元気ミワハルキ: Slowpoke/
Slowking/Latias ex/Clefairy ex/Fezandipiti/Kyurem/Meowth ex/Mega Kangaskhan,
12×P+8 energy items): **12–16% of games hit step_limit at turn ~1240–1660**
with our last Pokemon vs an energy-less wall, prizes 0–0, both decks empty.

Mechanism (our own cards, their stall):
1. Hammer-lanche self-mills 6 cards/turn → our deck empties;
2. Riptide SHUFFLES discard Water back into our deck → W-in-discard drops to 0
   → next Riptide deals ~0 damage;
3. engine doesn't enforce their deckout on the draw step → infinite loop.
Meanwhile **their deck self-mills to 0 around T35–51 in normal games** — games
we survive are wins by THEIR deckout (verified in END snapshots).

v21 STALL mode (scanned any of {115,140,144,162,163,183,184,224,272,377,1071}
in their board/discard):
- Hammer: **−200 when our deckCount ≤ 20**, −40 at ≤30 (stop burning our ammo;
  survive → their deckout wins),
- Riptide: −120 while deckCount > 12 (kills the 0-damage loop),
- +30 to any other attack (walls never heal; Swirling Waves 130×2 kills them).
Result: draws 12–16% → 7.5% (88→60 @600g paired), WR 0.78–0.85 → **0.915**.

## 5. v21 hybrid spec (agents/main_heuristic_v21.py)

- Base: v11 unchanged. Thin `_score_main_option` wrapper (defined BEFORE
  `def agent`) adjusts scores; a sticky per-process `_V21_SEEN` set accumulates
  opponent card ids from active+bench+discard each turn (archetype scan —
  no deck list needed).
- Modes: STALL (§4), LUCARIO ({677,678} seen: when our Mega Abomasnow is
  active at ≥80 damage with ≥3F on their attacker → +140 retreat/switch,
  +90 Frost Barrier — protect the 4-prize Mega), MIRROR ({721,722,723} seen:
  Hammer −150 at real deckCount ≤10).
- Verified (paired, Actions matrix, deck v12_30_boss4): see §0.2. Aggregate
  v11 0.6385 → v21 0.6494. Full logs:
  `kaggle_results/hybrid_verify/*__main_heuristic_v11.txt` / `__v21.txt` (24 files).
- Bundle: `bundles/phase1_tuned_v21_hybrid.tar.gz` (built via
  build_submission.py, smoke-passed, loader-check-passed).

## 6. Live matchup intel (top30 manifest 2026-10-11, decks in decks/top30_live/)

- **Bill Vlasak (rank #1, 1243.5)** switched archetypes: now Riolu×4 +
  **Mega Lucario ex** ×4 + Koraidon + **20× Basic Fighting** + full draw suite
  (Cheren×4, Urbain×3, Poké Pad×4, Boss's×2). Energy starvation impossible;
  prize auction of the two 4-prize Megas decides. v11 ≈0.61, v21 ≈0.65.
- leo_turing (#2 area) runs a second Lucario variant: v11 0.77, v21 0.80.
- Stall/utility team: draws were the loss mode, now converted (§4).
- Our rating on 2026-10-11 fell 484.1 → 321.9 (rank 222 → 269) as v14 aged;
  the 00:00 UTC reset submission matters.

## 7. Negative results register (do NOT re-test without new mechanics)

| idea | verdict | evidence |
|---|---|---|
| Weight tuning of v11 family | plateau | 160+ candidates (2 branches), gen0–gen8 evolution, 40-parallel screen best 0.684 |
| LOW_E_AGGRO opening rule (v12b/v13) | ≈v11 | rejected @100g by 8560a56a; our broad/top30 ties |
| v19 early-gust T0–1 | **catastrophe** | 0.591/0.536 @30g (us), 0.630 top30 @100g (them) |
| Riptide boost at low deck | **hurts ALL Water decks** | v20: 5/5 worst broad regressions were waterline decks (per-deck diff correlation) |
| 31/32/33/34W decks, Retrieval, Pokégear, Waitress/Cyrano cuts | ≈30W, mirror-only upside | v17 cross-validation @100g, ~25k games (8560a56a) |
| v18/v19b rule layers | dead code (§1) | namespace check |
| Deck-margin mirror rules v11m3/B/C/D | neutral | their ~30k games + our 1000g mirrors (m3_C best-but-below-bar 0.495) |
| gen8r (Rust-search weights) | weaker top30 | 0.783 vs 0.797 |

## 8. Methodology that works (and the matrix pattern)

- Engine is **non-deterministic across runs** (no seed): same config replays
  differ. Noise floor: **±3pp @600g/matchup**, σ≈1.6pp @1000g. 5–20g results
  are noise (confirmed 5+ times). Draws count in WR — track them separately.
- **Paired A/B in one run** (same process pool, same opponent set) cancels
  run-to-run drift. For big N, use the Actions matrix:
  `.github/workflows/hybrid_verify.yml` — 13 parallel 4-core jobs, each runs
  BOTH agents over a slice/matchup (`tools/gauntlet_ffi.py --slice A:B`),
  commits per-agent result files. 43.6k paired games in ~4 wall-clock minutes.
- Acceptance bar: old bar was "+5pp on ≤1–2k games". With paired matrix
  testing, **+1pp @≥40k paired games (≥3σ) is resolvable and real** — but
  require NO regression >2pp anywhere and 12+/13 jobs ≥0.
- Rust+Rayon is useless for evaluating the PYTHON agents (the repo's rust
  engine substitutes its own approximate heuristic) — use it for deck/weight
  search only. Parallel Python FFI on Actions is the eval workhorse.

## 9. Submission logistics (learned the hard way)

- Quota ~5 slots/day, reset **00:00 UTC** (submissions are per-day).
- Two branches both armed at-reset with the SAME bundle → would burn 2 slots
  on duplicates. Fix patterns implemented in
  `.github/workflows/kaggle_submit_at_reset.yml`:
  two-phase sleep+`gh api .../dispatches` (dispatch is exempt from the
  GITHUB_TOKEN recursion block; jobs cap at 6h), **DISARM marker file**
  checked by phase 2 at branch tip, **trigger-file priority over dispatch
  input** (phase 2 re-reads `at_reset.trigger` at wake-up → re-arming while
  phase 1 sleeps works), dynamic submit message.
- The sandbox cannot cancel Actions runs (integration token 403) — design
  guards INTO the workflow instead.
- Sandbox has no route to kaggle.com or Actions log storage; the ONLY channel
  is files committed back to the branch. Workflows must `tee` results into
  `kaggle_results/**` and commit with rebase-retry (races with sibling jobs).

## 10. Harness traps

- **card_index reachability**: an agent file loaded from /tmp (or anywhere
  without `assets/card_index.json` reachable) gets an EMPTY card DB and plays
  crippled (~0.60 instead of ~0.83) — fakes "regression everywhere". Always
  test from `pokemon-agent/` with paths relative to it. (Trap from 8560a56a's
  mirror_fix doc; keep honoring it.)
- **Platform sandbox recreation between turns**: the worktree can be re-cloned
  at an old commit with files restored from the workspace snapshot — local
  commits vanish from `.git` but everything pushed is safe. Recovery:
  `git fetch origin '+refs/heads/*:refs/remotes/origin/*' && git reset --hard
  origin/arena/<branch>`; after re-clone, `git push` needs explicit
  `git push origin <branch>`; `.venv` and cargo vanish (rebuild via
  `bash setup.sh`, ~60 s; no Rust toolchain in sandbox).
- Clone is single-branch: remote-tracking refs for other branches require the
  explicit refspec fetch above.

## 11. Data / file index

- `SUBMISSION_LOG.md` — chronological decisions (this branch).
- `kaggle_results/comparison_m3v18/RESULTS.md` — all A/B tables incl. v20/v20b/v20c, v21, raw logs.
- `kaggle_results/hybrid_verify/` — 24 files, the 43.6k paired matrix.
- `tools/gauntlet_ffi_dbg.py` — obs-structure dump + DRAW/END snapshot instrumentation (how §3/§4 facts were established).
- `tools/gauntlet_ffi.py` — added `--slice A:B` for matrix jobs.
- `.github/workflows/hybrid_verify.yml` — the matrix pattern (reuse for any future candidate).
- Other branches' docs worth reading: `mirror_fix_2026_10_11.md` (8560a56a),
  `v18_31W_verification_2026_10_11.md` (8560a56a), `v17_cross_validation_other_branch.md` (here).

## 12. Open problems (next candidates)

- Per-archetype ATTACKER plan (current rules bias scores; swapping the whole
  attack plan vs Mega/stall is untested).
- Stall endgame: attack the wall with Swirling Waves requires 3W attach cadence
  — v21 penalizes the loop but does not yet plan the attach sequence.
- Mirror remains a deck-level coin flip (30W vs 35W damage race) — no agent
  rule fixes it; only live opponent detection could justify deck swaps, which
  the engine does not allow pre-match.
- Banette rematch: they can adapt; re-run the stall diagnosis each few days
  (deck CSVs refresh via kaggle_top30 workflow).

---

## TL;DR (PL)

v11+30W pozostaje bazą, ale **v21 (hybryda ze skanem archetypu) to pierwszy
kandydat, który ją statystycznie pokonuje: +1.10pp na 43 600 sparowanych gier
(3.4σ), bez żadnej regresji poza szumem** — zyski: stall +4.2pp (remisy→wygrane),
mirror 35W +3.5pp, Bill Vlasak (#1) +2.5pp, top30 +2.3pp. Kluczowe lekcje:
(1) wcześniejsze „warstwy ulepszeń" v18/v19b były martwym kodem (undefined id +
`except: pass`) — weryfikuj namespace po imporcie; (2) wrapper musi być przed
`def agent`, inaczej Kaggle-loader go wybierze (build_submission --smoke to
łapie); (3) remisy vs stall to pętla Riptide+Hammer (samobójczy mill) — trik:
nie wypalaj swojego decku, ich deck wypala się sam ~T35–51; (4) testuj
sparowane A/B w jednym runie, ≥600g/meczup × powtórki albo matrix na Actions
(wzorzec w repo); (5) sufit szumu ±3pp @600g — 5–20g to szum zawsze.
