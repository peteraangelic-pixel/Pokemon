# Mirror structural fix — analysis, attempts, verdict (2026-10-11)

Mirror is 42% of the 12 newest live losses (5/12: Avik Das, Shixiang Yan,
AByT3s, Mitsuaki Inoue, Jonathan Axl). Every agent/deck variant tested so far
sits at 0.47-0.61 — a robust coin flip. This doc: the mechanics, what was tried
(both branches' ideas), and the comparison protocol for v18 (theirs) vs v11m3
(mine).

## Attack mechanics (from data/attacks.json — verified)

| attack | cost | effect |
|---|---|---|
| Hammer-lanche (1046, Abomasnow) | 2W | **discard top 6 of YOUR deck**, 100 dmg per W among them (30W→~300, 34W→~340) |
| Riptide (1042, Kyogre) | 1W | 20 dmg per W in your discard, then **shuffle those W into your deck** |
| Frost Barrier (1047, Abomasnow) | 3W | flat 200 + 30 dmg prevention next turn, **no mill** |
| Swirling Waves (1043, Kyogre) | 3W | 130, discard 2E |
| retreat costs | | Snover 3W, Kyogre 3W, Abomasnow 4W |

So the mirror is a **2-resource race (HP + deck)**: Hammer self-mills for
damage; Riptide recycles (value scales with W in discard: 20×wd dmg + refills
the deck). v11 already has a hard guard (mill would deck us out → score 5 at
deckCount ≤ 7) but **Riptide is always under-scored vs Hammer (~212 vs ~282)
even when the deck is low**, so v11 idles on 0-dmg Riptides (traced: T4
Riptide with 0 W in discard) or stalls with a Kyogre lead.

## What was tried (mine, all @100g, 4 mirrors: 29W/vrm×35W/Tom35W)

| variant | rules | MIRRORS | regress (FA.Nina/tanzaku/Ocean/Yume) |
|---|---|---|---|
| A v11 (baseline) | — | 0.525 (runs: 0.485-0.555) | 0.818 |
| B atk-only | margin: Hammer −120@dme≤14 / −70 behind / +80 opp≤14; Riptide +30×wd @dme≤25 +120@dme≤18, −60 early-worthless; Frost +50 | 0.537 | 0.792 |
| C atk+retreat | B + rotate Kyogre(≥1W) to active @dme≤18 or margin<−4 (+140) | 0.517 | 0.835 |
| D full | C + mirror lead (Snover +80, Kyogre −60 in _fighter_score) | 0.512 | 0.810 |
| C @200g | confirmation | 0.522 vs v11 0.537 | — |

**Verdict: no rule combination beats v11 beyond noise** (±3.5pp run-to-run on
400g; 200g confirmation: C 0.522 < v11 0.537). Their v17 mirror rule
(Kyogre +40/+30) and proposed v18 (Riptide +100 @deck<15, Hammer de-boost
@<10) are the same family — absolute-threshold late-game tweaks. My version
added the relative margin + wd-scaling + rotation; it is neutral.

Sub-structure (stable across runs): **vs 29W mirror we WIN the damage race
(0.57-0.63); vs 35W mirror we LOSE it (0.44-0.56); true 30W mirror ≈ 0.50.**
The 35W losses are a damage-race problem (300 vs 350) that 34W deck fixed
partially but hurt aggro tempo (v17_cross_validation.md, test 5).

## ⚠️ TEST-HARNESS TRAP (cost me hours — check before trusting ANY number)

The agent loads `card_index.json` from dirs derived from `__file__` + cwd
(`/kaggle_simulations/agent`, cwd, _HERE, parent…). **An agent file tested from
/tmp (or anywhere without card_index.json reachable) imports with an EMPTY card
DB: `card()={}` for all ids, `PLAN` empty (primary=None), and the agent plays
crippled (~0.60-0.73 instead of ~0.83 vs Lucario)** — while the opponent's
agent (loaded from agents/) plays healthy. This fakes "the new rule regresses
everywhere". Verify every test file first:
`python -c "from tools.evolve_gen8 import *; from pathlib import Path;
m=load_agent_cached(Path('PATH'),{},'x'); print(m.PLAN['primary'])"` → must
print 723 (not None). All files below are in `agents/` and verified.

Also: the engine is non-deterministic (no seed in BattleStart; same config
replays 45-50 vs 42-50 on 50g) → 100g/matchup σ≈14%; use ≥200g for calls.

## Comparison protocol (for their v18)

Same file location (agents/), deck v12_30_boss4.csv, 4 mirrors × ≥200g
(121975059 29W, 121986752/121988745 vrm 35W, 121982770 Tom 35W) + 4 regressions
×100g (F.A.Nina 121984759, tanzaku 121988739, OceanMix, YumeNeko — top30_live).
Baselines this round: **v11 mirror 0.537@200g / regress 0.818-0.835@100g.**
Accept bar for any mirror rule (mine or theirs): ≥ +5pp on 200g mirrors AND
no regress drop > 3pp.

## Bottom line

- My best version after ~30k games of testing (both sessions combined):
  **v11 + 30W stays the submission version** — unchanged, as the other
  session also concluded.
- v11m3 (agents/main_heuristic_v11m3.py = D) and its ablations
  (…_B.py atk-only, …_C.py atk+retreat) are kept as experimental artifacts;
  C is the cleanest if a mirror bet is ever made, but the data says it is
  statistically indistinguishable from v11.
- The mirror's real asymmetries are deck-level (29W win / 35W lose the damage
  race), not agent-rulable at 100g power. Next candidate idea (not tested):
  conditional 31-34W deck swap is out (test 5); a 34W deck only when the live
  opponent is known to be 35W is not possible pre-match.
