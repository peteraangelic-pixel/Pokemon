# pokemon-agent — PTCG AI Battle Challenge (Playground)

Working repo for **The Pokémon Company – PTCG AI Battle Challenge Playground**
([competition](https://www.kaggle.com/competitions/the-pokemon-company-ptcg-ai-battle-challenge-playground)).

Target: a stable, explainable agent that clears ~600 rating in Phase 1 and gives us
the scaffolding (local arena, A/B harness, card database) to reach the top 10 % when
the big-money Strategy edition returns.

---

## Status

| Phase | What | State |
|---|---|---|
| **0** | Random legal-move agent, packaging, validation-episode rehearsal | ✅ done, bundle built |
| **1** | Rule-based heuristic agent priced on PTCG concepts | ✅ done, beats random 94 % |
| **2** | Search (MCTS / expectimax over sampled hidden info) or RL | ⏳ next |

---

## Quickstart

> `.venv/` is **not** persisted between sessions. Run `./setup.sh` first when picking
> this back up — it recreates the venv and reinstalls `kaggle-environments`, which is
> what ships the real `cabt` simulator and its native library.

```bash
cd pokemon-agent
./setup.sh                     # venv + engine + sanity checks (~1 min)

# only needed if you want to refresh the card DB from the engine binary
.venv/bin/python tools/dump_cards.py data
.venv/bin/python tools/build_card_index.py     # -> assets/card_index.json

# measure: heuristic vs random (100 games, ~20 s)
.venv/bin/python tools/run_match.py --a agents/main_heuristic.py --b agents/main_random.py --games 100

# A/B a design decision head-to-head (identical deck, sides alternate)
.venv/bin/python tools/ab_test.py --env-a "PTCG_VAR_DMG=1" --env-b "PTCG_VAR_DMG=0" --games 2000

# package a bundle (verifies the archive, then rehearses a validation episode)
.venv/bin/python build_submission.py --agent agents/main_heuristic.py --smoke
```

Upload `bundles/phase1_heuristic.tar.gz` on the competition **My Submissions** tab.

## The two bundles

| Bundle | What it is | When to use it |
|---|---|---|
| `bundles/phase0_random.tar.gz` | random legal option | pipeline smoke test only |
| `bundles/phase1_heuristic.tar.gz` | **the real agent** | the one worth a slot |

---

## Layout

```
pokemon-agent/
├── agents/
│   ├── main_random.py        # Phase 0: random legal option (+ deck from deck.csv)
│   └── main_heuristic.py     # Phase 1: the real agent — SELF-CONTAINED
├── deck.csv                  # the 60 card ids we submit (Mega Abomasnow ex line)
├── assets/card_index.json    # compact card + attack DB extracted from the engine
├── data/                     # raw dumps (cards.json, attacks.json) for research
├── tools/
│   ├── dump_cards.py         # AllCard / AllAttack out of libcg.so
│   ├── build_card_index.py   # raw dumps -> compact runtime index
│   ├── run_match.py          # local arena, N games, win rate
│   ├── diagnose.py           # why games end, wasted-tempo counters
│   └── ab_test.py            # head-to-head knob A/B with z-score
├── build_submission.py       # .tar.gz packer + verifier + smoke test
├── bundles/                  # committed .tar.gz deliverables (upload these)
├── setup.sh                  # recreate .venv + engine after a fresh session
├── SUBMISSION_LOG.md         # every upload: date, change, hypothesis, rating
└── NOTES_STRATEGY.md         # why the design is the way it is (writeup material)
```

---

## Submission format (verified)

From the Data page and the shipped engine source:

* `.tar.gz`, **flat** archive (`main.py` at the top level, not nested) + `deck.csv`.
* Unpacked at runtime into `/kaggle_simulations/agent/`.
* ≤ 197.7 MiB, **5 submissions/day**, only the **latest 2** are active.
* Our bundle is **~83 KiB**.
* Build it with `python build_submission.py ... --smoke`, which asserts the flat
  layout, the presence of `agent()` and 60 deck cards, then runs a BO1 + BO3
  self-play exactly like the Kaggle Validation Episode.

---

## The agent contract (verified against the engine, not just the docs)

| Step | Agent must return |
|---|---|
| `obs["select"] is None` | the **60 deck card ids** (the engine reads the deck from the agent's first action) |
| otherwise | **indices into `obs["select"]["option"]`**, at most `maxCount`, at least `minCount` |
| `option == []` but `maxCount == 1` | `[]` — this genuinely happens at game end |

Option semantics confirmed by logging real games:

```
7  = PLAY    {"index": <hand index>}
8  = ATTACH  {"index": <hand index>, "inPlayArea": 4|5, "inPlayIndex": <slot>}
9  = EVOLVE  {"index": <hand index>, "inPlayArea": 4|5, "inPlayIndex": <slot>}
10 = ABILITY {"area": <AreaType>, "index": <slot>}
13 = ATTACK  {"attackId": <id>}
14 = END
```

Deck searches legitimately reveal our own deck via `obs["select"]["deck"]`, and the
matching options use `{"area": 1, "index": <index into that list>}` — the agent
reads it rather than guessing.

---

## Where the wins are (from the summer 2026 edition)

Researched from the public writeups of the money competition
(`pokemon-tcg-ai-battle` / `…-challenge-strategy`), summarised in
`NOTES_STRATEGY.md` §2:

1. **Deck choice dominates.** The strongest public claim is that the meta is
   rock–paper–scissors and *the* lever is shipping a counter to the rising
   archetype, not tuning the policy. Also: exposing features (knockout distance,
   energy still missing) helped; hand-written rules hurt RL — but a rule-based
   agent is exactly the right Phase 1.
2. **Rule-based ceilings at ~600–700.** Independently reported, and matches the
   user's Phase 1 target. Phase 2 must be learning or search.
3. **Going first matters** — we measured **63.3 %** for the first player over 120
   games on this deck (7th place reported 57.9 % as the seat that chooses).

---

## Caveats we are aware of

* The card pool here (1431 cards) is what the shipped engine exposes; the
  competition Data page also lists `EN_Card_Data_R2_full.csv`, which we could not
  download (requires accepting the rules with a Kaggle account). Fields we rely on
  are all present in the engine dump, so this has not blocked us.
* The deck is the engine's built-in sample list (Mega Abomasnow ex). It is legal
  and coherent but **not tuned** — deck optimisation is the highest-value Phase 2
  item.
* Damage numbers used for decisions are *estimates* (weakness modelled as ±30,
  variable-damage attacks estimated from visible board counts). The engine always
  has the final say; we only use estimates to rank our own options.
