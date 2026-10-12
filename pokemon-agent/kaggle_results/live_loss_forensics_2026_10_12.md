# Live loss forensics — 2026-10-12 (v21 / v22b overnight submissions)

**Question:** why is the team still rank 254/324 (μ 407.1) when three sessions of local
testing praised v21 and v22b (0.80+ vs top30 locally)?

**Answer: the local gauntlet measures a different game than the live one.**
Live, the field develops 3-4 pokemon boards and one-shots our lone wall; locally,
both seats play the same thin-board one-shot tempo race that our agent wins on tempo.

---

## 1. The submissions (verified 2026-10-12 07:04 UTC)

| sub | upload | score | state |
|---|---|---|---|
| v21 hybrid | 00:18:24 | 385.1 | ACTIVE |
| v22b stall planner | 00:19:26 | 407.1 | ACTIVE |

- Same v21 code scored **600.0 / 449.9 / 385.1** in three same-morning uploads
  (±110 μ per run). Live μ A/B is below the noise floor — "v21 vs v22b = 385 vs 407"
  is uninterpretable.
- Field @07:04: best 1248.2, top50% cutoff 657.1, median 654.8. We are 407.1.

## 2. Live win rate (116 own episodes, 00:19 → 07:18 UTC, `our_replays/`)

| submission | W-L | win% | vs KYOGRE (mirror) | vs LUCARIO | vs new-meta "?" |
|---|---|---|---|---|---|
| v21 (57089461) | 30-31 | **49.2%** | 18-9 (67%) | 4-6 (40%) | 3-9 (25%) |
| v22b (57089489) | 24-31 | **43.6%** | 10-12 (45%) | 2-5 (29%) | 8-10 (44%) |

Below 50% in both → below field median → rank 254/324. (v11-era sample of 75
Oct-11 episodes: 27-48 = 36% — the old agent was even worse.)

## 3. How we lose: board collapse (98%)

- **61/62 v21+v22b losses end with ≤1 pokemon left on our board** (active KO'd,
  bench empty → instant loss). Avg ending turn 11.3.
- Same mode in the v11 era: 43/48. **Chronic, not a v21/v22b regression.**
- Last-stand pokemon are often at full HP: 350/350 Mega Abomasnow ex KO'd by one
  **Hammer-lanche** (atk 1046: discard top 6, 100 dmg per Basic {W} ≈ 300-500);
  150/150 Kyogre KO'd by one **Riptide** (150).
- Live mirror opponent boards at T8-T12: 3-4 pokemon, often **two charged
  Abomasnow ex**. Our board at the same turns: 1-2.
- The mirror opponents play the *same* Kyogre deck (revealed: 1 Kyogre / 3 Snover /
  4 Mega Abomasnow ex / 22 {W} / Mega Signal / Cyrano / Lillie's / Waitress).
  Same deck, same ~2.9 distinct pokemon per game — **they put them on the board,
  we don't.**

## 4. Root cause (code level, v11 → v22b inheritance)

Instrumented local games (`/tmp/main_selects2.py` pattern) on v22b:

1. **Search clogging.** `_score_wanted_card` scored every search target by
   `plan_power`; Mega Abomasnow ex (top power) won *every* search once the bench
   held ≥1 pokemon (the basic bonus only applied to an empty bench). Result:
   2-3 stage-2 ex held in hand **for 12+ turns** with no Snover on the board to
   evolve onto; Mega Signal (the #1 used search) kept fetching unplayable ex.
2. **No board pressure.** With no basics in hand (10/60 pokemon deck, thin
   opening), the agent had nothing to play: 35/40 early selects with bench ≤1
   had no playable basic in hand.
3. **Wall suicide.** Retreat protection triggers only at `hp ≤ 80`
   (`RETREAT_KO`). The 150 Kyogre / 350 Abomasnow "walls" never retreat from
   Riptide/Hammer-lanche range — they stand and die with an empty bench behind.

## 5. Why local testing said "great" (the measurement trap)

- Local gauntlet = self-play: **both seats share the thin-board defect.** The
  game becomes a one-shot tempo race (who lands Riptide/Hammer-lanche first),
  and our tempo engine wins it: 0.66-0.85 vs curated pools.
- vs a *developing* opponent (thickbot surrogate, 7k mirror games): v22b still
  wins 0.579 — thickbot one-shots poorly, so the thin board is not punished.
- vs a developing **and competent** reference opponent (v24d, 7k mirror + 17.5k
  field games): thin v22b and thick v24d both win ~0.58 / ~0.81.
  **The local engine's tempo meta rewards the one-shot, not the bench.**
- Conclusion: local A/B on self-play pools **cannot predict live mirror/field
  strength**. It measures tempo execution only. (It remains valid for
  deck-vs-deck and same-defect deltas.)

## 6. Fix shipped: v24d (`agents/main_heuristic_v24d.py`)

v22b + development fix:

- `_score_wanted_card`: evolution targets with **no pre-evo on the board** are
  penalized (−90, −40 extra if already in hand); basics are bonus-scored while
  the board is thin (80/45/20 for board ≤1/2/3).
- `_v24d_search_gate`: Mega Signal (1145) and Night Stretcher (1097) are not
  played when no ex has a pre-evo on the board (−150); Cyrano (1205) gated when
  the discard holds nothing usable (−80).

Local effect (30 games each, devstats):
board@T4 1.00 → 1.67; empty-board deaths vs thickbot 94% → 86% of losses.
A/B win rate: **neutral** in local pools (−0.14…−0.17pp mirror across two
opponent variants, +0.18pp field, all |z|<0.5) — the local engine cannot
credit the fix. **Its value is only
measurable live.** Ship as the development candidate next reset.

Known remaining gap (next step, v25): threat-aware retreat — never stand a
150/350 wall into Riptide/Hammer-lanche range with no bench backup. Current
retreat trigger `my_hp <= 80` is too narrow, but a naive "retreat whenever
opponent can KO" discards our own energy (retreat cost) and breaks the engine;
needs a safe-retreat model (backup survives next turn / ≤1 energy sacrificed).

## 7. Artifacts

- `our_replays/episodes_table.csv` — one row per episode (116): sub, opponent,
  win/loss, turn, archetypes, final boards.
- `our_replays/loss_snapshots.jsonl` — 62 losses: final boards, KO'd pokemon,
  last 25 log events, our last 14 decisions.
- `our_replays/summary.md` — per-submission W-L by archetype/opponent.
- `agents/opp_thickbot.py` + `tools/ab_interleaved.py --agent-opp` — the
  developing-opponent surrogate for local A/B.
- `tools/summarize_episodes.py` + `kaggle-our-replays.yml` (top-k 80,
  loud-on-failure) — re-run any time by touching
  `kaggle_results/our_replays.trigger`.

## 8. Conclusions (honest)

1. v21/v22b are **not** the breakthrough the local numbers promised. They are
   ~44-49% agents — below the field median. The local 0.80+ numbers were a
   self-play tempo artifact.
2. The single biggest lever found is **board development** (v24d), with the
   second biggest being **threat-aware retreat** (not yet built). Both target
   the one death mode we actually die by (98% of losses).
3. Live scoring noise (±110 μ per submission) means **one live submission per
   reset, max** — A/B on μ is impossible; judge changes by win rate in
   `our_replays` (90+ games ≈ ±5% win-rate resolution).
4. The Kyogre mirror is actually winnable (v21 18-9) — the developing fix
   should protect the mirror further; the Lucario (40/29%) and new-meta
   (25-44%) holes need archetype-specific attention (out of scope for v24d).
