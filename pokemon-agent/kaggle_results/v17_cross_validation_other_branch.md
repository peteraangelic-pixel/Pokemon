# v17 (other branch, cfe7f73) — cross-validation @100g — 2026-10-11

Other session unblocked, shipped v17 (d02dca0, cfe7f73): agent `main_heuristic_v17.py`
(= my gen8r file + 19 re-weighted keys + LOW_E_AGGRO rule + new MIRROR rule
`opp in {721,722,723} -> Kyogre +40, +30 if attack-ready`) + new decks
(31W/32W/33W/34W, Energy Retrieval, Waitress 1-2) + claim "0.696 broad 5g,
0.826 top30, NEW BEST vs new 49 losing decks".

## Their actual "final" bundles

`phase1_tuned_v17_final.tar.gz` main.py == **agents/main_heuristic_v13.py** (0 diff
lines) + 34W deck (Sig4 Lil3 Boss4 Wait2 Pad2 Belt1). The v17.py agent is NOT in
either bundle. So "v17 final" = rejected-rule agent (v13) + new 34W deck.

## New episodes since 13:58 (fetched via kaggle_replays trigger, 22 episodes)

12 losses: **5 = MIRROR** (Avik Das, Shixiang Yan, AByT3s, Mitsuaki Inoue,
Jonathan Axl — all Snover/Aboma/Kyogre lines), 2x Lucario 13E (teriri_15, lswuwu),
Alakazam+Dusknoir (Thiago Silva), Dragapult (Ryan Fernandes),
**Mega Excadrill/Genesect** (new archetype, [Deleted] bc3788a4), 10 wins.
Mirror is 42% of new losses — confirms it is the dominant live problem.
(Note: new replays no longer contain deck lists; archetypes reconstructed from
cards seen in play.)

## Test 1 — agent/deck combos @100g, core 10 (loss8+meta)

| combo | total | mirror29W | vrm a/b | Tom | FA.Nina | Kevin | Lucario | tanzaku | Ocean | Yume |
|---|---|---|---|---|---|---|---|---|---|---|
| v11 + 30W | 0.686 | 0.60 | 0.44/0.56 | 0.44 | 0.84 | 0.88 | 0.77 | 0.78 | 0.84 | 0.71 |
| v11 + 31_v2 (theirs) | 0.697 | 0.53 | 0.47/0.46 | 0.56 | 0.84 | 0.94 | 0.74 | 0.82 | 0.91 | 0.70 |
| v11 + 34_final (theirs) | 0.670 | 0.52 | 0.49/0.40 | 0.46 | 0.73 | 0.91 | 0.77 | 0.86 | 0.84 | 0.72 |
| **v17 + 31_v2 (theirs)** | **0.687** | 0.53 | 0.46/0.50 | 0.55 | 0.82 | 0.91 | 0.73 | 0.76 | 0.90 | 0.71 |
| v13 + 34_final (their bundle) | **0.706** | 0.61 | 0.56/0.44 | 0.44 | 0.81 | 0.90 | 0.80 | 0.83 | 0.86 | 0.81 |

## Test 2 — same combos @100g, 10 NEW-loss opponents (broad 0/X records)

| combo | total | Davide Og28G | Noel Og28G | nguyen Tty+C | Riccardo | Kazama | Schott(R5) |
|---|---|---|---|---|---|---|---|
| v11 + 30W | **0.647** | 0.42 | 0.43 | 0.45 | 0.38 | 0.82 | 0.78 |
| v11 + 31_v2 | 0.659 | 0.41 | 0.43 | 0.48 | 0.40 | 0.88 | 0.85 |
| v17 + 31_v2 | 0.614 | 0.29 | 0.41 | 0.40 | 0.39 | 0.88 | 0.72 |
| v13 + 34_final | 0.634 | 0.38 | 0.39 | 0.47 | 0.46 | 0.80 | 0.77 |

Their "0.696 broad 5g" does not transfer: best @100g = 0.659, and their actual
v17 agent is the worst of the group (0.614). Their "vs wall 0.550 BEST" = 0.45-0.48
@100g.

## Test 3 — deck ablation @100g core 10, agent v11 (all my builds, decks/v11x_*.csv)

| deck | total | note |
|---|---|---|
| 30W ctrl | 0.703 | baseline |
| 31W+Retr (=their 31_v2) | 0.702 | noise |
| 34W plain (=their final) | 0.689 | mirror 0.62 best, Yume 0.67 worst |
| 31W + my trainers | 0.708 | noise |
| 32W + my trainers +Retr | 0.685 | noise |

All within 1σ — no deck effect is robust on core.

## Test 4 — Ogerpon-28G counter @100g x4 (Davide, Noel, tanzaku 14E, tategami)

| combo | total |
|---|---|
| v11+30W | 0.510 |
| v13+30W (LOW_E_AGGRO rule) | 0.505 |
| v11/v13 + 30W+2x Pokégear 3.0 | 0.470-0.492 |
| v11/v13 + 31W+2x Pokégear 3.0 | 0.492-0.520 |

Ogerpon 28G (pure 4x Ogerpon-ex, 28G, 12 acceleration cards) is a **coin flip for
every variant** — the 0.38-0.43 numbers from 100g runs are variance (same
matchup measured 0.30 and 0.42 in different 100g runs). Pokégear 3.0 +
Retrieval do NOT fix it.

## Test 5 — meta-tuned decks @100g, live loss distribution (4 mirror + 4 Ogerpon + 2 aggro)

| deck | total | mirror grp | Ogerpon grp | aggro grp |
|---|---|---|---|---|
| **30W ctrl** | **0.587** | 0.545 | 0.515 | 0.815 |
| 31W+Pkg | 0.565 | 0.505 | 0.513 | 0.790 |
| 32W+Pkg | 0.555 | 0.513 | 0.448 | 0.720 |
| 33W full | 0.567 | 0.490 | 0.513 | 0.830 |
| 31W+Pkg2 | 0.532 | 0.480 | 0.468 | 0.760 |

30W wins the live distribution. Mirror and Ogerpon-28G are coin flips for every
deck tested — no structural fix found this round.

## Verdict

- **v17 agent: REJECT** (0.687 core / 0.614 new-loss pool < v11's 0.703/0.647;
  5g broad claims are noise, confirmed 4th time).
- **Their final bundle (v13+34W): NOT an improvement** — 0.706 core is +1-2pp over
  v11+30W (noise), worse on the new-loss pool (0.634 vs 0.647) and Ogerpon group.
  The 34W deck helps only the pure mirror (0.61) at the cost of aggro tempo.
- **No deck change (31-34W, Retrieval, Pokégear, −Waitress/−Cyrano) is a reliable
  improvement** over 30W on core or live distribution.
- **Decision: v11 + 30W (v12_30_boss4) stays the submission version.**
- Open problems (unchanged): mirror coin flip (now 42% of new losses — biggest
  live issue), Ogerpon-28G coin flip, new Mega Excadrill/Genesect archetype
  (no deck in pool yet).
