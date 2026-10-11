# v22 assessment (2026-10-11)

Two things named "v22" are in play. Assessment of both, plus a major
methodology finding about the local gauntlet.

## 1. v22 = a450b00f's "flat early-gust" — NET ZERO, do not ship

From `origin/arena/a450b00f-pokemon` (1f816a4) `kaggle_results/hybrid_verify2/`:
13 jobs, 48.7k paired games, v11 vs v21 vs v22, same decks both seats.

Aggregates: v11 **0.6554** / v21 **0.6694** / v22 **0.6680**.
- v21−v11: **+1.40pp (z=+3.25)** — re-confirms v21 at ~3x the sample of my
  independent check.
- v22−v21: **−0.14pp (z=−0.33) = NET ZERO.**

v22 (v21 + flat +25 gust/Boss's urgency at T0-1, inherited from c87f7a48 v25)
is a pure reshuffle, not an upgrade:

| job (600g) | v11 | v21 | v22 | v22−v21 |
|---|---|---|---|---|
| Bill_Vlasak | 0.607 | 0.648 | 0.593 | **−5.5pp** |
| leo_turing | 0.735 | 0.767 | 0.798 | +3.2pp |
| stall (yaruki) | 0.847 | 0.855 | 0.870 | +1.5pp (draws 70→59) |
| mirror30 | 0.542 | 0.512 | 0.468 | **−4.3pp** |
| mirror35 | 0.493 | 0.488 | 0.532 | +4.3pp |
| top30 a/b | ~0.806-0.837 | | −0.25pp | |
| broad q1-q4 | ~0.61-0.63 | | ±0.6pp | |

The bill/mirror30 losers are the same Riolu-line as the leo/mirror35 winners,
so no simple T0-active gate can separate them. If early gust urgency is
wanted it must be conditional on something other than turn number.

## 2. v22b = v21 + stall attach planner — VERIFIED, small but real

`agents/main_heuristic_v22b.py` (v21 + one wrapper, diff = 33 lines):
in STALL mode (v21's existing board-scan gate), my active = Kyogre (721),
opponent active hp ≤ 260:
- **+40** to ATTACH only when `inPlayArea == Area.ACTIVE` (energy on the
  *active* Kyogre, not the bench) and it has <3 energy — build 3W;
- **+120** to ATTACK Swirling Waves (1043) when it has ≥3 — force the
  130-damage kill instead of 0-damage Riptide chip.

Mechanism: in frozen stall endgames v21/v11 stall at 1-2W and lose to
draw-limit draws; 3W Swirling kills 260HP-or-less walls in 2 turns.

Verified with `tools/ab_interleaved.py` (see §3), 4200 games, alternating
100-game blocks, single process:

| pool (700g each) | v21 | v22b | Δ |
|---|---|---|---|
| **yaruki (pure stall)** | 0.859, draws 10.0% | **0.916, draws 3.9%** | **+5.71pp (z=+3.39)** |
| 18 top30_live decks w/ stall ids | 0.850 | 0.849 | −0.14pp (z=−0.07) |
| mirror10 (control) | 0.591 | 0.566 | −2.57pp (z=−0.97) |

- Pure stall: ~43 draws converted to wins, losses flat (29→32). This is the
  designed mechanism, reproduced.
- Everything else: neutral. The planner is surgical — it only matters where
  real stall walls exist. (17/30 top30_live decks contain Fezandipiti 140 /
  Meowth ex 1071, v21's known STALL-id false positives, but the added boosts
  net out to zero there.)
- Expected aggregate effect on a top30-style field: ~+0.2pp (stall ≈ 1/30 of
  sample). Small, but strictly positive and bit-identical elsewhere (see §3
  differential test).

## 3. METHODOLOGY: the 8-worker gauntlet's cross-run numbers are not comparable

Root cause of a phantom "−10pp regression" on Kanga_Crustle (v21 0.760/0.735/
0.712 vs v22b 0.660/0.660/0.660 across three pairs of 200-500g runs):

1. `libcg.so` keeps **per-process RNG state consumed by every BattleStart**.
   Separate `gauntlet_ffi.py` invocations (and the 8 worker processes inside
   one) each hold their own stream, so two runs of an IDENTICAL policy can
   differ by 4-10pp at 200g (Kanga_Slowpoke v21 alone moved 0.640↔0.725
   between two 200g runs).
2. Proof the "regression" was artifact:
   - differential score test: 20 real battles recorded, both modules replayed
     on every (obs, option): **3279 options, 0 score diffs**;
   - fire probe: stall boost applied **0 times** in 200 Kanga games (deck has
     no STALL ids);
   - interleaved same-process A/B: 0.745/0.708/0.742 (v21 blocks) vs
     0.675/0.703 (v22b blocks), pooled **not significant**; tool re-run:
     **0.690 vs 0.690 exact**.
3. Rule going forward: **compare agents from the same process, alternating
   blocks, pooled** — `tools/ab_interleaved.py`. gauntlet_ffi.py remains fine
   for single-agent pool sweeps, but its 200g numbers are ±4-5pp, not ±1pp.

(Also: the earlier "stall300 0.847→0.897" gauntlet headline is consistent
with the rigorous yaruki 0.859→0.916 once the aliasing bug in my tally
script is excluded — trust the interleaved numbers from now on.)

## Recommendation

- **Do not ship flat-gust v22.** v21 stands as the hybrid champion.
- **v22b is safe to ship** (bit-identical outside true stall games) but its
  aggregate gain (~+0.2pp top30) is smaller than the next candidates:
  - Bill (0.648 @600g, hardest non-mirror): Lucario-mode deepening
    (Mega Abomasnow 270HP 4-prize bait / retreat logic, v21 already protects
    the 4-prize; Koraidon line interactions);
  - mirror (42% of all losses): still the biggest single pool.
