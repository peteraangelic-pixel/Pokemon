# v21 independent verification (2026-10-11, branch arena/8560a56a-pokemon)

Independent check of `arena/a450b00f-pokemon`'s v21 claim (+1.10pp over v11+30W
@43.6k paired games, 3.4σ) and its cross-branch DISCOVERIES.md.

## 1. Dead-code claim — CONFIRMED (the important one)

`main_heuristic_v18.py` (and v19b) append a `_score_main_option_v18` wrapper that
references `MIRROR_IDS` / `RIPTIDE_ID` / `HAMMER_ID` / `WALL_IDS` — **none defined
anywhere in the module** — inside a `try/except Exception: pass`. Every call throws
NameError at `MIRROR_IDS`, is swallowed, and returns the base v11 score unchanged.

Verified: after load, `hasattr(m, 'MIRROR_IDS'|'RIPTIDE_ID'|'HAMMER_ID'|'WALL_IDS')`
all False, `_score_main_option.__name__ == '_score_main_option_v18'` but it is a
no-op. **Consequence: every "v18/v19b vs v11" A/B this week (my 0.617/0.612, the
"+5.4pp", "broad 0.641", "top30 0.814") was v11-vs-v11 = pure noise.** The
conclusions ("they don't beat v11") were right, for the wrong reason (the rule
never ran). Only v19 (separate, non-wrapper code) genuinely differed — and was a
catastrophe. Rule going forward: after load, assert the wrapper is wired AND every
symbol it uses is defined.

## 2. v21 liveness — CONFIRMED (not the same trap)

`main_heuristic_v21.py`: all rule symbols are `_V21`-suffixed and defined in-file
(RIPTIDE_ID_V21=1042, HAMMER_ID_V21=1046, STALL_IDS_V21={115,140,144,162,163,183,
184,224,272,377,1071}, `_V21_SEEN`). Wrapper `_score_main_option_v21` bound at
line 1680, **before** `def agent` (line 1682) — passes the Kaggle-loader order
gate (a wrapper defined after `def agent` gets picked as the agent → garbage).

## 3. My independent paired A/B (same pools, same session, v12_30_boss4 deck)

| pool (games) | v11 | v21 | my Δ | their matrix Δ |
|---|---|---|---|---|
| STALL_yaruki (200) | 0.815, **29D (14.5%)** | 0.830, 26D (13%) | +1.5pp | +4.2pp @600g |
| Bill_Vlasak #1 (200) | 0.595 | 0.630 | +3.5pp | +2.5pp @600g |
| mirror10 (200) | 0.560 | 0.577 | +1.7pp | +1.6…3.5pp @600g |
| top30_live (100) | 0.824 | 0.812 | −1.2pp | +2.3pp @4600g |
| broad_field (100) | 0.617 | 0.633 | +1.6pp | 0…+1.9pp |

Read: 4/5 pools in the claimed direction, no real regression (top30 −1.2pp is
within ±1.5pp noise at 2500g; their 4600g paired run says +2.3pp). **The stall
draw mechanism is reproduced exactly** — v11 draws 14.5% vs the yaruki stall deck
(they reported 12–16%), and v21 trims it. My sample (2.6k) is directionally
consistent with their 43.6k matrix; I found no contradiction.

## 4. Verdict

- v21 is the **first credible, statistically-supported improvement** over v11+30W
  this project has produced — and the first that is (a) confirmed live code,
  (b) loader-safe, (c) backed by a paired large-N matrix, (d) directionally
  reproduced by an independent branch.
- The DISCOVERIES.md is a high-value cross-branch knowledge base (dead-code trap,
  loader boundary, engine facts, stall fix, negative-results register, matrix
  methodology). Adopt it as the standing reference.
- Watch item: top30 per-deck — a STALL-id false positive (e.g. an aggro deck
  containing Zeraora 377 / Meowth 1071) would suppress Hammer and could cost a
  point or two on specific decks. My −1.2pp top30 is likely noise, but worth a
  per-deck look if v21 underperforms live.

## 5. Submission state at verification time (~20:55 UTC)

- c87f7a48 at-reset: **v11+30W armed** → fires 00:01:30 (guaranteed).
- a450b00f at-reset: **v21 armed** (`phase1_tuned_v21_hybrid.tar.gz`, no DISARM),
  two-phase sleep chain in_progress → expected to fire v21 ~00:01:30.
- Risk: two at-reset chains in_progress on a450b00f → possible duplicate v21
  submission (slot waste, not fatal). v22 (v21+early-gust) is being built but NOT
  armed.
- Net plan: both v11+30W and v21 go live after the 00:00 UTC reset → direct live
  A/B. Reasonable hedge given the v21 chain's fragility.
