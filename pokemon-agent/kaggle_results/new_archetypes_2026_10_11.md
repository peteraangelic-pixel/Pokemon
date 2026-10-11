# New top30 archetypes @100g vs v11+30W (2026-10-11)

Question: the current top30 meta flooded with archetypes never measured @100g.
Is there a hole in v11+30W worth fixing?

## Deck reconstruction

Replays expose per-card `serial` (0-59 per seat; seat1 = +60). Aggregating
serial→cardId across all episodes of one archetype (majority vote) recovers the
deck to 50-57/60 cards; remaining serials filled from leftover copies of
observed cards (energy last). Clustering by non-energy card signature separates
distinct builds. Sources: kaggle_results/top30_live (100 episodes) + replays/.
Note: cards.json has duplicate names from two sets — engine/replay IDs verified
(Alakazam=743 not 245, Abra=741 not 109, Dunsparce=305).

Decks written to decks/newarch_pool/ (7 builds; coverage in name suffixes of
recon output): Alakazam_Twilight (n=2, 57/60), Ogerpon_FoV_Meowth (n=6, 57/60 —
dominant top30 team), Ogerpon_FoV_Dipplin (n=1), Dragapult (n=1, 51/60),
Dipplin_Grookey_6E (n=1, 54/60), Kanga_Crustle_wall (n=2, 57/60),
Kanga_Slowpoke (n=1). All legal (60 cards, ≤4 non-energy, ≤1 ACE SPEC).

## Result — gauntlet_ffi, v11 + v12_30_boss4, 100g both seats

| new archetype | winrate |
|---|---|
| Dipplin/Grookey 6E | 0.98 |
| Alakazam/Twilight (Hilda+Dawn+Telepath) | 0.92 |
| Ogerpon 14E FoV Meowth (dominant top30 build) | 0.88 |
| Dragapult ex (Crushing Hammer) | 0.86 |
| Ogerpon 14E FoV Dipplin | 0.76 |
| Mega Kangaskhan + Slowpoke | 0.74 |
| Mega Kangaskhan + Crustle (wall build) | 0.71 |
| **TOTAL (700g)** | **0.836** |

## Verdict

**No hole.** v11+30W beats every new top30 archetype, worst 0.71 (wall build —
already countered by the L8/L10 wall rules). The last open data-driven lever is
exhausted: agent rules plateau (9 agents, 3 sessions), deck tweaks plateau
(31/32/34W), new archetypes not a problem.

Standing weaknesses (unchanged, previously proven unfixable at rule level):
mirror 0.47-0.59 (damage race), Ogerpon 28G 0.47-0.52 (coin flip).

**Submission stands: v11+30W, 00:01:30 UTC from arena/c87f7a48-pokemon.**
