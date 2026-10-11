# Branch handover — arena/c87f7a48-pokemon (the other session stalled at tip 9a5bf9b, 15:09)

Their session stopped; this branch now carries the combined work. Status of
everything they shipped (all claims verified at 100g unless noted):

## Their late-wave commits (13:58–15:09), verdict per item

| commit | artifact | their claim | 100g verdict |
|---|---|---|---|
| 55277c2 | v16_gen8_tempo bundle + gen8_meta pool | "1.000 vs Lucario/Ogerpon" | **REJECT** — the 1.000 is 4 games each (search_results_gen8/best.json); whole agent = 0.584 @100g (gen8_cross_validation.md) |
| 582deeb | v12b opening fix | +5.2pp top30, +0.9pp v14 | **REJECT** — the fix IS the LOW_E_AGGRO rule (721 −150/722 +80, 16 IDs) |
| 7e597bd | rust binaries + build.log | — | merged (skip-ci binaries, harmless) |
| 9a5bf9b (tip) | **v13 = v11f + v12b rule**, bundle phase1_tuned_v16_30_boss4_v13 | 0.835 top30 **@20g**, 0.622 broad @30g | **REJECT** — diff vs v11f is exactly the 12-line LOW_E_AGGRO block; = the v13 I cross-validated: **0.557 @100g** (v13_cross_validation.md). 20g claims are noise |

Their "valuable progress" (v12b → v13 → v13 bundle) all reduces to ONE
structural rule, already rejected at 100g. Do NOT submit any v13/v12b/v16
bundle.

## Duplicated or already-solved work

- **kaggle_fetch_90_100.yml (BROKEN, 0 replays)** — inline `kaggle
  competitions leaderboard show --csv` = invalid CLI syntax ("Either --show or
  --download must be specified" captured into manifest.csv). ALREADY REPLACED
  by my working `kaggle_fetch_weak.yml` (same default rank band 90–100,
  positional-arg `tools/download_top10_replays.py`, `decks/weak_field/`
  populated). No action needed.
- **v15 (5775fdc)** = the same v15 I built and submitted (30W Boss4 deck +
  v11/v11f code). No divergence.
- **gen8_meta/ 8 decks** = real top30 meta templates, not fabrications:
  Alakazam 2E (Kentaro Totsuka #7), Dipplin 6E (ANMOL GARG #1), Dragapult 10E
  (Kevin Hulin), Sinistcha 3E — all identified in my v14_diagnosis.md;
  Lucario/Ogerpon/Mirror are near-duplicates of the loss pool (identical
  unique-id sets, slightly different counts).

## Verified: v11 @100g vs the 4 NEW meta templates (30W deck)

| meta | 100g | old small-sample claim (v14_diagnosis, v11f+v13_29) |
|---|---|---|
| Alakazam_2E | 0.860 | 1.000 |
| Dipplin_6E | 0.820 | 0.850 |
| Dragapult_10E | 0.780 | 0.900 |
| Sinistcha_3E | 0.930 | 0.950 |
| **total** | **0.848** | 0.867 |

v11 is already strong vs the real top30 meta; small-sample numbers all
deflated as expected.

## Net position (unchanged by the handover)

- Final version = **v11** (0.711 core @100g, 0.848 vs new top30 meta @100g)
  — already in the submitted v15 bundles.
- Only open structural problem: **mirror coin flip** (0.47–0.55, symmetric
  equilibrium; lead-order rules M1/M2 failed @100g — gen8_results.md).
- Next candidates: conditional mill-race timing (energy/retreat priority vs
  own line), any new top30 replays after this afternoon.
