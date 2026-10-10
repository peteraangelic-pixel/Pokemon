# SUBMISSION_LOG

One row per Kaggle upload. The rule we hold ourselves to: **each submission carries
exactly one hypothesis**, and the hypothesis must already have local evidence — the
ladder is for confirming, not for exploring.

Budget: **5 submissions/day**, of which only the **latest 2** stay active. So an
upload both spends a slot and *retires* an older agent; never experiment with both
slots filled by experiments.

μ starts at 600 for every new submission. Treat any single-day μ move under ~15 as
noise (see `NOTES_STRATEGY.md` §5).

---

## Local evidence ledger

Everything below was measured on the real `cabt` engine via `tools/ab_test.py`
(identical deck both sides, sides alternating every game).

| # | Change | Test | Result | Verdict |
|---|---|---|---|---|
| L1 | **GO_FIRST** = go first vs go second | 120 games, BO1 | first player wins **63.3 %** (76–44, z ≈ +2.9) | **adopt** `GO_FIRST = True` |
| L2 | **Variable-damage estimation** (`PTCG_VAR_DMG`) vs raw printed damage | 2000 games, BO1 | **56.65 %** (1113–887, **z = +5.05**) | **adopt** (default on) |
| L3 | Heuristic vs random-move agent | 100 games, BO1 | **94 %** win rate | baseline established |
| L4 | Robustness fuzz vs freshly generated rules-legal opponent decks | 120 + 40 games | 0 exceptions, 0 contract violations, all seats `DONE` | **ship-ready** |
| L5 | Contract check: never return more than `maxCount`, never out-of-range, never a duplicate index | all fuzz games | 0 violations | **ship-ready** |
| L6 | Deck-construction rules the engine enforces (`errorType 4`) | 1431 cards instrumented | 4-copy limit is **by card name**; ≤ 1 ACE SPEC (incl. ACE SPEC *energies*) | documented in `tools/deck_rules.py` |
| L7 | **Local gauntlet**: our deck vs 11 auto-assembled archetypes, both seats | 200 games/seat | overall 0.748; we beat 9 archetypes at 0.83+ and lose to **2 anti-ex walls** (Crustle 0.195, Safeguard 0.285) | walls are the Phase 2 target |
| L8 | **Damage-prevention detection** (`pv` flag) + switch to an attacker that can hit | 120 games/seat, 11 archetypes | Crustle 0.195→**0.325**, Sylveon 0.285→**0.500**, overall 0.748→**0.780**, no other matchup moved | **adopt** (default on) |
| L10 | **Wall v2**: retreat 340 when walled, fighter_score -500 for walled attackers +200 for escape attacker, attach +40 to non-walled bench, Surfing Beach 345 when walled | 60 games/seat gauntlet | crustle 0.367→**0.450**, sylveon 0.300→**0.617**, overall 0.776→**0.809** | **adopt** |
| L9 | Deck variants: `+2 Boss's Orders` and `+2 Kyogre +2 Boss +2 Ultra Ball`, paid for with energy | 120 games/seat | both **worse everywhere** (0.383 / 0.425 vs baseline) — cutting energy cuts Hammer-lanche from ~330 to ~270 | **reject** — see `decks/README.md` |

### Why L2 mattered so much

429 of the engine's 1755 attacks (24 %) print `damage = 0` and put the real number in
the effect text. Our first heuristic scored all of them as zero, which meant the
agent rated Mega Abomasnow ex's **Hammer-lanche** — the deck's actual win condition,
~330 average damage for two Water Energy — *below* the printed 200-damage
Frost Barrier. It was playing the deck backwards. Details in `NOTES_STRATEGY.md` §4.2.

---

## Uploads

### 2026-10-09 — FIRST ATTEMPT: both submissions FAILED  ⚠️

Uploaded `phase0_random` and `phase1_heuristic`. **Both came back Error.** The
downloadable agent logs are kept at `kaggle_results/error_logs/`:

```
File "/kaggle_simulations/agent/main.py", line 240, in _candidate_dirs
    here = os.path.dirname(os.path.abspath(__file__))
NameError: name '__file__' is not defined
    kaggle_environments.errors.InvalidArgument: Invalid raw Python
```

**Root cause.** Kaggle does not *import* our module — it compiles the source and
`exec`s it (`kaggle_environments/agent.py` → `get_last_callable` →
`exec(code_object, env)`). In that namespace `__file__` does not exist. Our
`_candidate_dirs()` touched it **outside** any try/except, so the agent died at
import time and never played a turn.

**Why nothing local caught it.** Our `smoke()` test loads `main.py` with
`importlib.util.spec_from_file_location`, and *importing defines `__file__`*. The
test reproduced the game but not the loader, so it was structurally incapable of
catching this — it would have passed forever.

**Fix.**
- `_HERE` computed inside `try/except NameError`; the Kaggle absolute paths
  (`/kaggle_simulations/agent`, `.../assets`) are tried **first** and need no `__file__`.
- Module-level `DECK` / `_INDEX` loads wrapped so an import-time failure degrades
  to the hardcoded fallback instead of killing the agent.
- Same fix in `main_random.py`.

**New mandatory gate.** `tools/test_kaggle_import.py` unpacks the built `.tar.gz`
and execs `main.py` into a namespace with **no `__file__`**, then checks it
returns 60 ids, that the deck matches `deck.csv` (not the fallback), that the
card index loaded, and that self-play finishes. `build_submission.py` runs it on
every build and **refuses to ship** otherwise.

| check | result |
|---|---|
| loads without `__file__` | ok |
| `agent()` returns 60 ids | ok |
| deck matches `deck.csv` | ok |
| card index loaded (1431 cards) | ok |
| self-play BO1 + BO3 | `DONE` / `DONE` |
| robustness fuzz, 120 games | 240/240 seats `DONE`, 0 violations |

**Action: re-upload both** — `bundles/phase1_heuristic.tar.gz` (86.8 KiB) and
`bundles/phase0_random.tar.gz` (75.8 KiB), both rebuilt and gated.

---

### 2026-10-09 — LIVE RATING after second attempt

| file | status | score | date |
|---|---|---|---|
| `phase1_heuristic (2).tar.gz` | COMPLETE | **462.0** (down from 600.0) | 2026-10-09 10:37:37 |
| `phase0_random (1).tar.gz` | COMPLETE | 74.5 (down from 76.1) | 2026-10-09 10:01:38 |

Leaderboard: 271 teams, best 1210.3 (YumeNeko), median 640.9, worst -28.1
Our team **Lauresowe 3D** rank 192/271 top 71% (was 148 top 54% at 600.0 start)
Top 25% needs 833.3, top 10% 959.5, top 50% 643.3

Interpretation: heuristic loses more than it wins live. Gauntlet 60/seat shows
why: 9 archetypes we crush at 76-100%, but 2 anti-ex walls crush us. Even after
wall v1 (0.325/0.500) we were still losing those. Live meta likely contains
more walls + RL agents that are stronger than our simple archetypes.

Next hypothesis H1: wall v2 (see L10) — should gain ~30-40 μ if walls are ~15%
of field. Ship as phase1_heuristic v3.

---

### 2026-10-09 — SECOND ATTEMPT: random passed, heuristic failed  ⚠️

After the `__file__` fix: **phase0_random passed**, **phase1_heuristic failed**.
Logs in `kaggle_results/error_logs/120488910-*.json`:

```
agent.py:154, in callable_agent
    return agent(*args) if callable(agent) else agent
TypeError: _score_yes_no() missing 3 required positional arguments
```

Note what `self.agent` actually is: **`_score_yes_no`**, not our `agent`.

**Root cause.** `kaggle_environments.agent.get_last_callable()` ends with

```python
return [v for v in env.values() if callable(v)][-1]
```

Kaggle does **not** look for a function named `agent` — it takes whatever
callable was defined **last** in the file. Our helper functions (`_fallback`,
`_decide`, `_score_yes_no`) were defined *below* `agent`, so Kaggle called
`_score_yes_no(obs)` and it blew up on missing arguments.

This also explains the asymmetry the same day: `main_random.py` happens to
define `agent` last, so it passed while the heuristic failed.

**Fix.** `agent` moved to the very end of `main_heuristic.py`, with a comment
explaining why it must stay there. `tools/test_kaggle_import.py` now calls
**Kaggle's own `get_last_callable()`** and fails the build unless it resolves to
`agent` with exactly one parameter. `build_submission.py` runs it, so this
cannot reach an upload again.

Both bundles rebuilt and fully gated. **Re-upload `phase1_heuristic`.**

---

### 2026-10-08 — submission 1: Phase 0 (random)

* **Bundle:** `bundles/phase0_random.tar.gz` (75 KiB)
* **Content:** `main.py` = uniform random legal option; deck from `deck.csv`.
* **Hypothesis:** *the packaging and validation path work end to end.* This is a
  pipeline test, not a strength test — it should pass the Validation Episode
  (agent vs copies of itself) and land at μ ≈ 600.
* **Why it is worth a slot:** it proves bundle format, deck delivery, and log
  retrieval are correct before any strategy code is trusted. If it errors, the bug
  is in packaging, not in the heuristic.
* **μ after 24 h:** _pending — paste from the Submissions page_
* **σ after 24 h:** _pending_

### 2026-10-08 — submission 2: Phase 1 (heuristic) — **the one to actually run**

* **Bundle:** `bundles/phase1_heuristic.tar.gz` (85 KiB)
* **Content:** rule-based agent; banded scoring (Supporter → Item → Basic → Evolve →
  Attach → Stadium → Ability → attack → retreat → end), deck-plan inference, energy
  attachment aimed at *turning on attacks*, variable-damage estimation, mill-deck-out
  guard, retreat-on-threat.
* **Hypothesis:** *a precondition-aware rule agent clears μ ≈ 600 and holds it.*
  Public evidence says a rule-based agent on this exact deck plateaus at 600–700
  (`NOTES_STRATEGY.md` §2.2).
* **μ after 24 h:** _pending_
* **σ after 24 h:** _pending_

> **Operational note.** Only the latest 2 submissions are live. Once Phase 1 is
> confirmed healthy, keep **phase1 in one slot permanently** and use the second slot
> for one experiment at a time. An experiment that flops must not leave us with
> nothing.

---

## What to capture from the Submissions page

For every upload, record:

* **Status** — `Complete` / `Error`. An `Error` means the Validation Episode failed;
  download the **agent logs** and add the traceback below.
* **μ and σ after 24 h** — the whole point of the entry.
* **Number of episodes played** — tells us how fast σ is closing and whether a
  result is even worth reading yet.

### Troubleshooting an `Error`

Our agent is written never to raise (blanket `try/except` returning a legal fallback),
so a Validation-Episode failure most likely means one of these instead:

1. **Bundle shape** — `main.py` nested inside a folder. Re-check with
   `tar -tzvf bundles/*.tar.gz`; it must list `main.py` at the top level.
2. **Deck rejected** — `deck.csv` must hold exactly 60 ids. Note the engine enforces
   construction rules (≤ 4 copies, ≤ 1 ACE SPEC); violation returns `errorType 4` and
   the deck is marked `INVALID`.
3. **`card_index.json` missing** — not fatal (the agent degrades gracefully to
   neutral defaults) but it would play much worse. `build_submission.py --smoke`
   asserts it is present.
4. **Import-time failure** — anything at module scope. `build_submission.py --smoke`
   reproduces the harness by unpacking the tarball to a temp dir and importing
   `main.py` from there.

**A trap we already hit during development, worth remembering when writing tooling:**
the harness inspects the agent callable's *arity*. A callable that accepts two
parameters is called the legacy way as `(observation, configuration)`. Our submitted
`agent(obs)` takes exactly one argument, so it is fine — but a helper wrapper with an
extra defaulted parameter will silently receive the environment configuration as its
observation.

---

## Next hypotheses (queued, one per slot)

| # | Hypothesis | Local test to run first | Expected signal |
|---|---|---|---|
| H1 | The sample deck is the bottleneck: adding energy-recycling (Energy Retrieval / Recycler) to loop Hammer-lanche beats the untuned sample list | same policy, old deck vs new deck in `ab_test` | > 55 % for the new deck |
| H2 | A lethal check ("can I take the last prizes this turn?") beats the pure scorer | `ab_test` with `PTCG_LETHAL=0/1` (to be added) | +2–4 pts, and it is *computation*, so it should not pay the rules penalty |
| H3 | Precondition-aware search-card scoring (don't fire a search whose target is already in hand) is worth more than its complexity | `ab_test` toggle | small positive |
| H4 | Retreat thresholds are mis-tuned | sweep the retreat HP threshold | unclear |
| H5 | Phase 2: BC warm-start on heuristic self-play games, then PPO | n/a (offline) | must beat the heuristic > 60 % head-to-head before it earns a slot |

---

## 2026-10-09 — Evolutionary search: 40-parallel screening (Kaggriculture-style)

**Problem:** Live rank 192/271, μ=462.0, user says 65% vs top10 is too low to upload. Need systematic ML search like previous Kaggriculture project (40 parallel versions vs simulated top players, pick best 3, mutate).

**Solution:**
- Created `agents/main_tunable.py` with 22 tunable knobs via env vars (all scoring bands)
- Built `tools/search_heuristic.py` — evolutionary loop: random configs → evaluate vs top10 via `vs_top10.py` subprocess → select top3 → mutate
- Local run: 2 gens x 20 pop x 15 games = 40 configs, 6000 games, ~24 min, 4 workers
- Result: **70.2% vs top10** (158-67) vs baseline 61.3% — +8.9pp
- Best config: more patient (lower bench/evolve/attach), stronger wall avoidance (-625), higher progress bonus (30 vs 18) — matches mill playstyle (survive + build Hammer-lanche)

**Bundles:**
- `phase1_heuristic.tar.gz` 87.6 KiB — baseline heuristic + v3_boss33 (33 Water + Boss x2)
- `phase1_tuned.tar.gz` 88.0 KiB — best_from_search (70.2% vs top10) + v3_boss33, smoke ok

**Actions workflow:**
- `.github/workflows/kaggle_search.yml` — matrix 40 jobs, each random config vs top10, reducer picks best 3, commits `best_from_search.py`
- Alternative: single job evolutionary `--generations 2 --pop-size 20`
- Next: trigger 40-parallel in Actions for continuous search (estimated 5 min wall time)

**Hypothesis for next upload:**
> Patient wall-avoidance (WALL_PENALTY -625) + high progress bonus (30) improves vs top10 from 61.3% to 69.6% (30 games/deck stable). Should improve live μ from 462 to >600.

**Live rating:** not yet uploaded — awaiting user decision (65% too low, now 70% ready)


---

## 2026-10-09 — 40-parallel Actions (71.1%) + Gen2 refinement (75.1% → 70.7% stable)

**Actions run 37985741842:**
- 40 jobs matrix idx 0-39, each random config vs top10 (15 games), 4 min/job, 40x parallel
- Best: idx=33 win=0.711 (160-65) — Supporter 355, Bench 335, Retreat Wall 362, Gust 91, Wall Penalty -569, Attach Wall Bonus 67
- Validation 30 games: 0.671 — high variance, less stable

**Local Gen2 refinement (30 mutated around 0.702, strength 0.15, 15 games, 4 workers):**
- Best: **0.751** idx=14 — Supporter 345, Bench 313, Evolve 294, Attach 281, Stadium 270, Wall Penalty -697 (strongest avoidance), Retreat Wall 353, Progress 29
- Top5 >0.733 — consistent
- Stable 30 games: **0.707 (318-132)** — new record, +9.4pp over baseline 0.613
- Gauntlet: 0.814 (179-41) vs 0.786 baseline

**Bundles:**
- `phase1_tuned_71.tar.gz` 89 KiB — Actions best 71.1% → 66.9% stable
- `phase1_tuned_75.tar.gz` 88 KiB — Gen2 best 75.1% → 70.7% stable, smoke ok — **READY FOR UPLOAD**

**Hypothesis for next upload:**
> Wall Penalty -697 + Evolve 294 + Attach 281 + Retreat Wall 353 improves vs top10 from 61.3% to 70.7% stable (30 games). Patient wall-avoidance + high progress bonus (29) is key for mill.

**Live rating:** still 462.0 rank 192/271 — awaiting upload of phase1_tuned_75

**Next steps:**
- Gen3 refinement around 0.751 with strength 0.08 to try 76%+
- Trigger another 40-parallel in Actions with refined search space (narrow around -697 wall penalty)
- Upload phase1_tuned_75 as next submission (one hypothesis per slot)


---

## 2026-10-10 — Gen8 deck search + TOP7 live gauntlet

**TOP7 live fetch:** Run 38051500906 success, 14 JSONs, 22 unique decks extracted to `decks/top7_live/`, manifest 141 lines. Avg energy 14.8 vs ours 33, gust 2 dominant. New archetypes: Dhelmise/Banette 2E 3 gust, Mega Lucario ex 13E fighting, YumeNeko 7E Abra/Alakazam, Ogerpon grass 14E (6 teams identical).

**Gauntlet live tool:** `tools/gauntlet_live.py` — evaluates our agent+deck vs live decks (22) + archetypes (11) + top10 official (15). Used for Gen8 fitness.

**Gen8 candidates (Gen5 agent, 2g vs live, 20g vs arch, 10g vs top10):**
- v2_boss (30E, Boss x2, Signal x4, Cyrano x2, Night x2, Pad x2, Belt x1, Judge x1, Haul x1, Waitress x1): live 0.864 (38-6), arch 0.786, top10 0.820 → **overall 0.823 BEST**
- v3_boss33 (33E, Boss x2): live 0.724 (4g), arch 0.800, top10 0.707 → 0.744
- v8_29_boss3_v2style (29E, Boss x3, Signal x4, Cyrano x2, Night x2, Pad x2, Judge x1, Waitress x1, Haul x1, Ultra x1): live 0.864, arch **0.827 BEST vs arch**, top10 0.736 → 0.809
- v8_28_boss3_hammer (28E, Boss x3, Hammer x2): live 0.864, arch 0.759, top10 0.720 → 0.781
- v8_30_boss3 (30E, Boss x3): live 0.818, arch 0.777, top10 ~0.707
- v8_26_boss3 (26E, Boss x3): live 0.659 — cutting too much energy hurts Hammer-lanche (330→270 damage)

**Finding:** 30E still best vs live/top10; Boss x3 helps vs walls (arch 0.827) but hurts vs tempo (top10 0.736 vs 0.820). Maximum Belt (ACE SPEC, +50 vs ex) better than Secret Box for this deck — pushes Hammer-lanche 300→350 vs ex, KO vs 360 HP mega.

**Bundles:**
- `phase1_tuned_gen8_v2.tar.gz` 88 KiB — Gen5 agent + v2_boss (30E, Boss x2, diverse) — overall 0.823, smoke ok — **RECOMMENDED FOR UPLOAD**
- `phase1_tuned_gen8_29.tar.gz` 89 KiB — Gen5 agent + 29E Boss x3 v2style — arch 0.827, smoke ok — alternative if wall-heavy meta

**Next:** Poll petersharps PENDING→COMPLETE; Gen8 search with fitness = top10_live 14 replays + gauntlet 11 archetypes, candidate decks 26-30E + Boss x3 + more draw, extract decks from new JSONs to `decks/top7_live/` (done). Next priority: H1 energy recycling + Phase 2 lethal DFS.


---

## 2026-10-10 — PeterSharps live: 372→421 + weak-mirror analysis + Powerglass

**Live poll (run 38057562586 + 38061686393):**
- Submissions: 2x phase1_tuned_80.tar.gz COMPLETE 372.6 and 377.2 → after more episodes 421.0 (rank 225/298, was 238). +43 μ improvement from same bundle playing more games.
- New submit: `phase1_tuned_gen8_v2.tar.gz` PENDING 14:57 UTC — Gen5 agent + v2_boss 30E Boss x2 diverse, best overall 0.823 vs live 0.864 top10 0.820.
- Replays: 13 episodes fetched for PeterSharps, 11 JSONs parsed (6W-5L):
  - Wins: YOUKE144 Lopunny, Guenoir Lucario, [Deleted], BSCode Starmie, cottonandcolor 28W, AByT3s 35W mirror
  - Losses: Atharva_Naik 35W mirror (35W vs our 33W → 350 vs 330 Hammer-lanche), Pawit_Sahare 35W mirror, Rodrigo_S_Faria 33W Powerglass x2, SC Dragapult Hammer x4 Boss x3, Kydyrbek_Kozykorpesh Dragapult Hammer x4 Boss x3
- Pattern: loses to 35W mirrors (more energy = more damage) and Dragapult Hammer (0 energy attacker, mills us) and Powerglass mirrors (recycle).

**Weak-mirror deck analysis:**
- Created `decks/combined_losses/` 17 CSVs (losses 7 + peter_losses 11 minus dup), `decks/all_eval/` 39 CSVs (top7_live 22 + combined 17), `decks/mirror_losses/` 5 worst (Jonathan_Axl, The_Prad_K, cottonandcolor, Rodrigo_S_Faria, Hitisha_Goyal).
- Search vs combined_losses (pop10 g5 gen2): best 0.672 (43-21) vs combined, 0.727 vs top7_live (Gen5 0.864) → overfits to weak.
- Search vs all_eval (pop12 g4 gen2): best 0.682 (101-47) vs all_eval, 0.773 vs top7_live 2g, 0.578 vs combined_losses.
- Search vs mirror_losses (pop12 g6 gen2): best 0.600 (18-12) vs 5 mirrors, Jonathan_Axl 0.500→0.833 in best config. Config: SUPP 347, EVOLVE 300, ATTACK 210, RET_BASE 138, WALL_PEN -710, FIGHTER_READY 45, ENABLE 30, PROGRESS 33.

**Mirror bonus experiments:**
- Implemented `_is_mirror_match()` checks opp active/bench for IDs 721/722/723 (Kyogre/Snover/Aboma), `_mirror_bonus()` +15 then +25 added to EVOLVE/BENCH/ATTACH scores. Created `agents/main_heuristic_gen8_mirror.py` (Gen5 env vars + mirror bonus).
- +15 → mirror_losses 0.500 (10-10) worse than Gen5 0.600; +25 → mirror_losses 0.600 (12-8) same as Gen5 but Jonathan_Axl 0.750 vs 0.500, but vs top7_live 2g 0.682 vs Gen5 0.864, vs 35W mirrors (Eugen/Pawit/Anthony/vrmichalski) 0.188 (3-13) vs Gen5 0.438 (7-9) → mirror bonus hurts vs strong Water mirrors because it triggers vs all Water (35W top7 decks have 721/722/723), so it fires vs Eugen/Pawit/Anthony where patient play is better.

**Powerglass analysis:**
- The_Prad_K/Rodrigo/Hitisha all use Powerglass x2 (1163: end of turn attach Basic Energy from discard if Active). Agent does not explicitly score attaching Powerglass to Active; current attach logic treats Tool as 288 +8 active, no recycle value.
- Created `decks/gen8/v8_29_powerglass.csv` 29W + Lillie4 Mega4 Boss2 Cyrano2 Night2 Pad2 Belt1 Judge1 Haul1 Powerglass2 → vs mirror_losses 4g 0.650 (13-7) vs Gen5 0.600, The_Prad_K 1.000 (4-0) vs 0.500; vs 35W mirrors 0.375. `v8_30_powerglass.csv` 30W same trainers minus Haul/Waitress plus Powerglass2 → vs mirror_losses 0.500, vs top7_live 2g 0.773.
- Cotton deck 28W Snover4 Aboma4 Kyogre2 Signal4 Lillie4 Waitress4 Cyrano2 Ultra2 Boss2 Switch2 Night1 Belt1 (60) beats v2 4-0. Tested + Gen5 agent: vs top7_live 2g 0.744 (32-11) worse than v2 0.864, vs mirror_losses 4g 0.750 (15-5) better than v2 0.600 — tradeoff: more draw (Waitress x4) helps mirror but hurts vs top.

**Deck search tool:**
- Built `tools/search_deck.py` random deck generator (energy 26-33, trainers pool) + eval via gauntlet_live vs all_eval.
- 5 trials: best 0.662 (49-25) with 32W Lillie4 Mega4 Boss3 Pad3 Haul2 Judge1 Waitress1 (10+32+18=60) saved to `decks/gen8/best_from_deck_search.csv`. Tested: vs top7_live 2g 0.818 (36-8) close to Gen5 0.864, vs mirror_losses 4g 0.550 (11-9).
- Timeout at 20 trials (each trial 39*2=78 games ~110s, 20 trials ~36 min) → need games 1 or smaller eval-dir for quick search.

**Bundles ready:**
- `phase1_tuned_gen8_v2.tar.gz` 88 KiB — Gen5 + v2_boss 30E Boss x2 diverse — PENDING live, best overall 0.823
- `phase1_tuned_gen8_mirror.tar.gz` 88 KiB — Gen8 mirror +25 + v2_boss — improves Jonathan_Axl 0.250→0.750 but hurts top7 0.864→0.682 — tradeoff, smoke ok
- `phase1_tuned_gen8_powerglass.tar.gz` 89 KiB — Gen5 + v8_29_powerglass 29W Powerglass2 — 0.650 vs mirror_losses, 1.000 vs The_Prad_K, smoke ok

**Hypothesis for next uploads:**
> v2_boss 30E Boss x2 diverse improves vs low-energy gust meta (top7_live 0.864) and vs weak mirrors with more draw (Boss x2 + Haul + Waitress). Should improve live μ from 421 to >500. If PENDING fails, try Powerglass variant which fixes The_Prad_K 0.500→1.000.

**Next:**
- Wait for gen8_v2 PENDING→COMPLETE rating
- Implement H1 as `_score_wanted_card` boost for Night Stretcher when discard Water>=2 and remaining<8, and Powerglass attach logic (score tool higher if active Kyogre and discard Water>=1)
- Re-test lethal only rem==1 ready-check (previous DFS hurt vs walls, but may help vs mirrors when prize race tight)
- Larger deck search 20 trials games 1 vs all_eval, then test best 3 vs top7_live 4g + combined_losses 4g

---

## 2026-10-10 — PeterSharps live: 372→421 + weak-mirror analysis + Powerglass

**Live poll (run 38057562586 + 38061686393):**
- Submissions: 2x phase1_tuned_80.tar.gz COMPLETE 372.6 and 377.2 → after more episodes 421.0 (rank 225/298, was 238). +43 μ improvement from same bundle playing more games.
- New submit: `phase1_tuned_gen8_v2.tar.gz` PENDING 14:57 UTC — Gen5 agent + v2_boss 30E Boss x2 diverse, best overall 0.823 vs live 0.864 top10 0.820.
- Replays: 13 episodes fetched for PeterSharps, 11 JSONs parsed (6W-5L):
  - Wins: YOUKE144 Lopunny, Guenoir Lucario, [Deleted], BSCode Starmie, cottonandcolor 28W, AByT3s 35W mirror
  - Losses: Atharva_Naik 35W mirror (35W vs our 33W → 350 vs 330 Hammer-lanche), Pawit_Sahare 35W mirror, Rodrigo_S_Faria 33W Powerglass x2, SC Dragapult Hammer x4 Boss x3, Kydyrbek_Kozykorpesh Dragapult Hammer x4 Boss x3
- Pattern: loses to 35W mirrors (more energy = more damage) and Dragapult Hammer (0 energy attacker, mills us) and Powerglass mirrors (recycle).

**Weak-mirror deck analysis:**
- Created `decks/combined_losses/` 17 CSVs (losses 7 + peter_losses 11 minus dup), `decks/all_eval/` 39 CSVs (top7_live 22 + combined 17), `decks/mirror_losses/` 5 worst (Jonathan_Axl, The_Prad_K, cottonandcolor, Rodrigo_S_Faria, Hitisha_Goyal).
- Search vs combined_losses (pop10 g5 gen2): best 0.672 (43-21) vs combined, 0.727 vs top7_live (Gen5 0.864) → overfits to weak.
- Search vs all_eval (pop12 g4 gen2): best 0.682 (101-47) vs all_eval, 0.773 vs top7_live 2g, 0.578 vs combined_losses.
- Search vs mirror_losses (pop12 g6 gen2): best 0.600 (18-12) vs 5 mirrors, Jonathan_Axl 0.500→0.833 in best config. Config: SUPP 347, EVOLVE 300, ATTACK 210, RET_BASE 138, WALL_PEN -710, FIGHTER_READY 45, ENABLE 30, PROGRESS 33.

**Mirror bonus experiments:**
- Implemented `_is_mirror_match()` checks opp active/bench for IDs 721/722/723 (Kyogre/Snover/Aboma), `_mirror_bonus()` +15 then +25 added to EVOLVE/BENCH/ATTACH scores. Created `agents/main_heuristic_gen8_mirror.py` (Gen5 env vars + mirror bonus).
- +15 → mirror_losses 0.500 (10-10) worse than Gen5 0.600; +25 → mirror_losses 0.600 (12-8) same as Gen5 but Jonathan_Axl 0.750 vs 0.500, but vs top7_live 2g 0.682 vs Gen5 0.864, vs 35W mirrors (Eugen/Pawit/Anthony/vrmichalski) 0.188 (3-13) vs Gen5 0.438 (7-9) → mirror bonus hurts vs strong Water mirrors because it triggers vs all Water (35W top7 decks have 721/722/723), so it fires vs Eugen/Pawit/Anthony where patient play is better.

**Powerglass analysis:**
- The_Prad_K/Rodrigo/Hitisha all use Powerglass x2 (1163: end of turn attach Basic Energy from discard if Active). Agent does not explicitly score attaching Powerglass to Active; current attach logic treats Tool as 288 +8 active, no recycle value.
- Created `decks/gen8/v8_29_powerglass.csv` 29W + Lillie4 Mega4 Boss2 Cyrano2 Night2 Pad2 Belt1 Judge1 Haul1 Powerglass2 → vs mirror_losses 4g 0.650 (13-7) vs Gen5 0.600, The_Prad_K 1.000 (4-0) vs 0.500; vs 35W mirrors 0.375. `v8_30_powerglass.csv` 30W same trainers minus Haul/Waitress plus Powerglass2 → vs mirror_losses 0.500, vs top7_live 2g 0.773.
- Cotton deck 28W Snover4 Aboma4 Kyogre2 Signal4 Lillie4 Waitress4 Cyrano2 Ultra2 Boss2 Switch2 Night1 Belt1 (60) beats v2 4-0. Tested + Gen5 agent: vs top7_live 2g 0.744 (32-11) worse than v2 0.864, vs mirror_losses 4g 0.750 (15-5) better than v2 0.600 — tradeoff: more draw (Waitress x4) helps mirror but hurts vs top.

**Deck search tool:**
- Built `tools/search_deck.py` random deck generator (energy 26-33, trainers pool) + eval via gauntlet_live vs all_eval.
- 5 trials: best 0.662 (49-25) with 32W Lillie4 Mega4 Boss3 Pad3 Haul2 Judge1 Waitress1 (10+32+18=60) saved to `decks/gen8/best_from_deck_search.csv`. Tested: vs top7_live 2g 0.818 (36-8) close to Gen5 0.864, vs mirror_losses 4g 0.550 (11-9).
- Timeout at 20 trials (each trial 39*2=78 games ~110s, 20 trials ~36 min) → need games 1 or smaller eval-dir for quick search.

**Bundles ready:**
- `phase1_tuned_gen8_v2.tar.gz` 88 KiB — Gen5 + v2_boss 30E Boss x2 diverse — PENDING live, best overall 0.823
- `phase1_tuned_gen8_mirror.tar.gz` 88 KiB — Gen8 mirror +25 + v2_boss — improves Jonathan_Axl 0.250→0.750 but hurts top7 0.864→0.682 — tradeoff, smoke ok
- `phase1_tuned_gen8_powerglass.tar.gz` 89 KiB — Gen5 + v8_29_powerglass 29W Powerglass2 — 0.650 vs mirror_losses, 1.000 vs The_Prad_K, smoke ok

**Hypothesis for next uploads:**
> v2_boss 30E Boss x2 diverse improves vs low-energy gust meta (top7_live 0.864) and vs weak mirrors with more draw (Boss x2 + Haul + Waitress). Should improve live μ from 421 to >500. If PENDING fails, try Powerglass variant which fixes The_Prad_K 0.500→1.000.

**Next:**
- Wait for gen8_v2 PENDING→COMPLETE rating
- Implement H1 as `_score_wanted_card` boost for Night Stretcher when discard Water>=2 and remaining<8, and Powerglass attach logic (score tool higher if active Kyogre and discard Water>=1)
- Re-test lethal only rem==1 ready-check (previous DFS hurt vs walls, but may help vs mirrors when prize race tight)
- Larger deck search 20 trials games 1 vs all_eval, then test best 3 vs top7_live 4g + combined_losses 4g

---

## 2026-10-10 — v8 spadek 600→308-460 + analiza przegranych + v9

**Live po v8 (poll 16:48 UTC, 300 teams):**
- `phase1_tuned_gen8_h1.tar.gz` COMPLETE **460.1** (było PENDING)
- `phase1_tuned_gen8_powerglass.tar.gz` COMPLETE **308.0** (było 600.0 → -292!)
- `phase1_tuned_gen8_v2.tar.gz` COMPLETE **426.4** (było 600.0 → -173)
- `phase1_tuned_80.tar.gz` COMPLETE 420.2
- Rank 216 (było 163) – **punkty w dół**

**Replays analiza 47 gier (PeterSharps):**
- 16 przegranych decków wyekstrahowanych do `decks/losses_v8/`: Atharva_Naik 35W Waitress4 Cyrano2 Belt1, Pawit_Sahare 35W, eastnix 35W, SC Dragapult Hammer x4, Kydyrbek Dragapult Hammer, mo Lucario 15E Boss3, kloaken Duraludon 11E gust4, Jonathan_Axl 26W Boss2, etc.
- Energy: {33:40, 35:10, 30:8, 29:7, 26:4, 15:4, 12:3, 10:4} – przegrywamy vs 35W (więcej energii = 350 dmg vs nasze 300) i vs low-energy aggro z Hammer x4 i Boss x3-4 (mieli nas, gustują basics przed ewolucją)
- Gust: {0:34, 2:45, 3:9, 4:4} – przeciwnicy z gust 3-4 wygrywają vs nasze Boss x2

**Dlaczego v8 spada:**
- v2_boss 30W diverse (Signal4 Lillie4 Night2 Pad2 Boss2 Cyrano2 Belt1 Judge1 Haul1 Waitress1) – 0.841 vs top7_live 2g, 0.700 vs losses_v8 1g, ale **0.000 vs Atharva/Pawit 35W** (0-2) bo mniej energii = mniej dmg, oraz **0.250 vs walls** (crustle 0.000, sylveon 0.500) bo Boss x2 za mało na gustowanie wokół walli
- v9_33_boss4 33W Boss4 Waitress2 Belt2 Pad1 – **0.864 vs top7_live** (najlepszy!), **0.750 vs walls** (crustle 0.500, sylveon 1.000) vs v2_boss 0.250 – Boss x4 naprawia walls, ale vs losses_v8 **0.567** gorszy niż v2_boss 0.700 bo mniej diverse trainerów
- v9_35_atharva 35W Signal4 Lillie4 Waitress4 Cyrano2 Belt1 (kopia Atharva) – 0.750 vs top7, 0.533 vs losses – nie bije Atharva, bo mirror 0.5, ale traci vs Dragapult
- Powerglass 29W Powerglass x2 – 0.705 vs top7, 0.650 vs mirror_losses, ale live 600→308 – bo 29W za mało energii vs 35W

**Wniosek:** Potrzeba **33W + Boss4 + diverse draw** – balans między energią (33 vs 35) a gustem (Boss4 vs Boss2) i draw (Signal, Lillie, Waitress, Pad, Night, Cyrano)

**v9 search z Rust + Rayon:**
- `tools/search_v9.py` – random deck search z `rust_gauntlet` (rayon 2 thr, 17-20s na 22 decki x2 gry vs 66s Python) – 3-6x speedup
- 20 trials games2 top7+losses weighted 0.7/0.3: best weighted 0.732 (31E top 0.818 loss 0.533)
- 30 trials games1 top7 only: best 0.909 (20-2) – v2_boss też 0.909, więc v2_boss nadal top
- 30 trials games1 top7+losses weighted: best 0.796 (33E Signal1 Pad3 Powerglass3 Cyrano4 Judge2 Petrel2 Lillie2 Waitress1 Beach1) – top 0.909 loss 0.533

**v9_final (ręcznie zaprojektowany na bazie v2_boss + Boss4 + 33W):**
- Deck: 33W + Signal4 Lillie3 Boss4 Waitress2 Belt1 Pad1 Night1 Cyrano1 = 4+3+4+2+1+1+1+1=17 +10+33=60
- `decks/v9_final.csv` – 33W, Boss x4, Waitress2, Belt1, Pad1, Night1, Cyrano1, Signal4, Lillie3
- Test Rust (games2):
  - vs top7_live: **0.841 (37-7)** – blisko best 0.864
  - vs losses_v8: **0.667 (20-10)** – lepszy niż v9_33_boss4 0.567, blisko v2_boss 0.700
  - vs walls: crustle 0.500, sylveon 1.000 → **0.750** vs v2_boss 0.250 – naprawia walls!
  - Weighted 0.7*0.841+0.3*0.667=0.788, vs v2_boss 0.798 – prawie równe, ale lepszy vs walls
- Bundles: `phase1_tuned_v9_final.tar.gz` Gen5 best + v9_final 89 KiB smoke ok, `phase1_tuned_v9_final_h1.tar.gz` H1 + v9_final 89 KiB smoke ok

**Hipoteza v9:**
> 33W Boss x4 Waitress2 Belt1 Pad1 Night1 Cyrano1 Signal4 Lillie3 – 33W daje 330 dmg (vs 350 dla 35W) ale Boss x4 naprawia walls (0.250→0.750) i Dragapult (gustuje Dreepy przed ewolucją), diverse draw (Night, Pad, Cyrano) pomaga vs 35W mirrors (Atharva 0.000→0.500). Powinien poprawić live μ z 460→600+ i zatrzymać spadek.

**Next (jutro, bo dziś limit 5/5 wykorzystany – v9 submit 38069038259 o 16:47 był 6. dziś i został odrzucony przez limit):**
- Submit v9_final i v9_final_h1 jako pierwsze jutro (00:00 UTC reset limitu)
- Dokończyć Rust full port heurystyki (obecnie 0.01s/gra vs 1.5s Python =150x, ale crash przy buffer full capacity:7 dla ENERGY selectów – trzeba przenieść pełne `_score_generic_context`)
- Uruchomić większy search 100 trials z Rust vs all_eval 38 decków

