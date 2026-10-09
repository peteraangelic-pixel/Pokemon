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

