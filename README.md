# Pokemon

PTCG AI Battle Challenge (Kaggle playground) — agent + deck research repo.

## Read this first (cross-branch knowledge)

- **`pokemon-agent/DISCOVERIES.md`** — consolidated, cross-branch knowledge base:
  dead-code trap, Kaggle loader boundary, engine/observation facts, the
  draws→wins stall fix, v21 hybrid spec (+1.10pp over 43.6k paired games),
  negative-results register, testing methodology + Actions-matrix pattern,
  submission logistics, harness traps.
- `pokemon-agent/SUBMISSION_LOG.md` — chronological decision log (all branches append their entries here after merges).
- `pokemon-agent/kaggle_results/comparison_m3v18/RESULTS.md` — A/B tables (v11/v13/v18/v19/v19b/v11m3*/v20*/v21) with raw logs.
- `pokemon-agent/kaggle_results/hybrid_verify/` — the 43.6k paired Actions-matrix results.

## Current best

- Baseline: **v11 agent + `decks/v12_30_boss4.csv` (30W)** — `bundles/phase1_tuned_v15_30_boss4_v11.tar.gz`
- Best verified candidate (2026-10-11): **v21 archetype-scan hybrid** — `bundles/phase1_tuned_v21_hybrid.tar.gz` (statistically +1.10pp over v11; see DISCOVERIES.md §5)

## Day-to-day

- Environment: `cd pokemon-agent && bash setup.sh` (~60 s, builds .venv with the cabt engine).
- Fast eval: `.venv/bin/python tools/gauntlet_ffi.py --agent agents/<x>.py --our-deck decks/v12_30_boss4.csv --opp-dir decks/<pool> --games N --workers 3`
- GitHub Actions workflows are trigger-file driven (`kaggle_results/*.trigger`) — the sandbox has no direct route to kaggle.com.
