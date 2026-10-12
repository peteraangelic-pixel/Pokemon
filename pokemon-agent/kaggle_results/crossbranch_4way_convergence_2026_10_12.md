# Cross-branch 4-way convergence (2026-10-12, 14:30–16:00 UTC)

User request: "sprawdz najnowsze wersje na arena/a450b00f i ponownie porownaj".

## What a450b00f did (tip 4c212b6)

- Imported **my v25** (byte-identical, verified by diff: 1719 lines, same md5)
  as `v25knobs` and c87f7a48's **v25_genius** as `v25genius`; ran a **4-way
  35W showdown (54,800 games, 13,700/arm, 5 pools**: broad_field, meta1012,
  top30_live, water_meta, thick_mirrors — GitHub Actions matrix-verify).
- Verdict: **v25knobs (mine) = point leader 0.6291, +0.80pp (z=1.37) vs
  v22b+35W control, non-negative in ALL 5 pools, thick_mirrors +1.81**
  (the pool built for the live death-mode — matches my K1 +2.25pp thickbot
  35W mirror direction).
- Their stated conclusion: "localny instrument osiągnął granicę
  rozdzielczości" (diffs ≤0.9pp, max |z|=1.4) — agent choice at this level is
  a bet on the live mechanism, not a local measurement.
- **Their FINAL slot rec: slot 1 = my `phase1_tuned_v25_35w.tar.gz`,
  slot 2 = their `ptcg_v22b_35w.tar.gz`** — the E-vs-B pair is a clean live
  A/B isolating the 5-line knob effect (same base, same deck).

a450b00f 4-way (their pools):
| arm | WR | vs v22b+35W control |
|---|---|---|
| B v22b+35W | 0.6211 | — |
| D v24d+35W | 0.6230 | +0.19pp (z=0.32) |
| V25 genius+35W (c87f) | 0.6202 | −0.09pp (z=−0.15) |
| **E v25knobs+35W (8560a56a = mine)** | **0.6291** | **+0.80pp (z=1.37)** |

## My independent re-test (23.2k + 22.4k games, my pools: refreshed top30
25 decks [c87f fetch 79c2def] + Jonathan_Axl mirror + 35W thickbot mirror)

Pairwise against v22b+35W as the common control (5,600 g/agent each):

| arm | pool52 25 decks | Jonathan_Axl | thickbot 35W mirror | TOTAL WR | Δ vs v22b35 |
|---|---|---|---|---|---|
| v25 (mine) [R1 vs ctrl] | +0.04 (z0.05) | +15.50 (z3.15, n=200) | +1.25 (z0.35) | **0.8036** | **+0.68pp (z≈0.9)** |
| v24d [R2 vs ctrl] | +0.10 (z0.13) | +3.50 (z0.70) | +3.50 (z0.99) | 0.7995 | +0.46pp (z≈0.6) |
| v22b35 control [R1/R2 A] | — | — | — | 0.7967 | — |
| v25_genius [T1 vs v25] | −1.86 (z−2.47) | +1.50 (z0.30) | −1.75 (z−0.50) | 0.7873 | −0.94pp (z≈−1.2) transitive |

Direct pairwise highlights: **v25 vs v25_genius = +1.73pp (z=+2.3, T1)**;
v25 vs v22b35 = +0.68pp (R1); v24d vs v22b35 = +0.46pp (R2); my v25 WR = 0.8036 (R1) / 0.8046 (T1) across
two independent runs.

## Convergence — the SAME 4-way order on two independent pools

| rank | a450b00f pools (54.8k) | 8560a56a pools (23.2k) |
|---|---|---|
| 1 | **v25 (mine) 0.6291** | **v25 (mine) 0.8046** |
| 2 | v24d 0.6230 | v24d 0.7995 |
| 3 | v22b35 0.6211 | v22b35 0.7967 |
| 4 | v25_genius 0.6202 | v25_genius 0.7873 |

Different pools, different infrastructures, different RNG streams — identical
ordering, my v25 on top in both, genius last in both. The search-mutated
Gen5 bands + board-dev superset does not reproduce the 12:15 three-way
"genius #1" (that was within 0.23pp noise, as their own 4-way then showed).

## Final state — all three branches agree on the ship plan

- **Slot 1: `phase1_tuned_v25_35w.tar.gz`** (8560a56a: v22b + 5 v11f
  wall-escape knobs + 35W-noBoss) — surgical (5-line diff), point leader on
  both independent 4-ways, targets death-mode #2 (walls not retreating),
  base with best live WR (v22b 0.474).
- **Slot 2: `ptcg_v22b_35w.tar.gz`** (a450b00f: v22b + 35W-noBoss) —
  identical base + deck, only the knobs differ → the two slots form a
  clean live A/B of the knob mechanism. Readout: our_replays WR at 24-48h
  (±5pp @90+ games), NOT μ (±110 noise).
- Rejected: v11f full rollback (live WR 0.36 era), v24d-solo (absorbed:
  it ranks 2nd anyway, inside noise), v25_genius (4th on both pools).
- c87f7a48's 12:15 rec (genius slot 1) is superseded by the 4-way — their
  own branch now also recommends my v25. User decision, nothing armed.
