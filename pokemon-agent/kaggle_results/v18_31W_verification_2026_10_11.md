# v18 / v18+31W / v19 @100g verification (2026-10-11, branch arena/8560a56a-pokemon)

Context: `arena/c87f7a48-pokemon` shipped **v19** (v18 + early gust T0-1 vs walls +
retrieval-vs-Hammer +30) and claimed (5g numbers, commit 4abff24):
- v18: 100g v14_opp_test v11 0.636 -> v18 0.690 (+5.4pp) — "first improvement over v11 @100g"
- final bundle: **v18 agent + v17_31_v2 deck (31W)** = top30 0.861 @5g BEST
- v19: broad 0.648 / top30 0.817 @5g, mirror 0.400 vs v18 0.650 @20g -> "v18 better"

`arena/a450b00f-pokemon` independently verified v11/v18/v11m3* @7k FFI + 900g H2H:
statistical tie everywhere, plateau holds (see their SUBMISSION_LOG 17:55 entry).

## My @100g verification (gauntlet_ffi, v12 engine, both seats, same pools same run)

Pools: top30_live (25 valid decks), broad_field_v2 (56 decks, incl. all mirrors +
new-loss opponents), mirror10 (PeterSharps/vrm/Tom/Mitsuaki/Shixiang/Avik/AByT3s/
Jonathan_Axl/F_A_Nina/Kevin_Hulin), newloss6 (DavideSanta/Noel_Bobby/nguyenbaotri/
Riccardo/Kazama/Schott — my reconstruction of their v14_opp_test; the dir itself
exists on no branch).

| pool @100g | v11+30W | v18+30W | v18+31W | v19+31W |
|---|---|---|---|---|
| **top30_live (25)** | 0.785 | 0.793 | **0.809** | 0.630 |
| **broad_field_v2 (56)** | **0.617** | 0.612 | 0.615 | — |
| **mirror10 (10)** | **0.595** | 0.568 | 0.554 | — |
| **newloss6 (6)** | **0.537** | 0.528 | 0.517 | — |

(earlier same-pool A/B this week: v11 0.617 vs v18 0.612 broad, 0.573 vs 0.571 mirrors — tie)

## Findings

1. **v19 is a clear loss** — 0.630 on top30_live @100g vs 0.785-0.809 for the rest.
   The early-gust T0-1 rule wrecks non-mirror games. REJECT (confirms their own
   20g mirror read, now at 100g on top30 too).
2. **v18+31W is a real trade, not a free lunch**:
   - BEST on top30_live: +2.4pp vs v11 (z≈+1.9 @2500g) — the strongest positive
     signal seen this week for any alternative config.
   - but WORST on mirror10 (−4.1pp vs v11, z≈−1.9 @1000g) and newloss6 (−2.0pp).
   - 31W slows the start (extra energy = less Signal/Lillie draw tempo) and the
     mirror damage race (we already lose the 35W mirror).
3. **Their "+5.4pp v14_opp_test" does not reproduce** on my newloss6: v11 0.537 ->
   v18 0.528 (-0.9pp). Their 0.861 top30 = 5g noise; 100g reality = 0.809.
4. **v18+30W** remains statistically indistinguishable from v11+30W everywhere
   (|Δ| ≤ 0.8pp @100g, mirrors ±1pp run-to-run).

## Verdict (same bar as SUBMISSION_LOG: +5pp required)

- **Submission unchanged: v11 + 30W, at-reset armed 00:00 UTC.** No config cleared
  the bar on any pool; the only positive (v18+31W top30 +2.4pp) is paid for by a
  real mirror regression, and mirror is 42% of live losses.
- **Booked as the standing candidate** if the 00:00 UTC ladder result is flat:
  v18+31W (top30+ vs mirror-) is the only alternative with a measured top30 gain.
  Re-test at 200g top30 + 200g mirror10 before any swap; accept only if mirror
  floor ≥ 0.57 at 200g.
- v19: reject, do not build on.
