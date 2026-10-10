# ARC-AGI-3 — novelty-explorer baseline

This directory is the ARC-AGI-3 workstream for the [ARC Prize 2026
competition](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3).
It contains a **deterministic, dependency-light baseline**, not a claim of a
competitive or solved agent.

The baseline replaces random actions with a small state graph and visual
novelty policy:

- it uses only the action IDs advertised by each environment;
- it ranks `ACTION6` click coordinates by non-background colour rarity,
  component size, and recently changed pixels;
- it tracks visible change, level progress, game-over outcomes, and revisited
  states;
- for standard directional controls, it first verifies the inverse move and
  schedules reachable shallow frontiers before descending farther;
- when a 5×5 striped-tile maze is visually recognized, it learns failed moves
  as obstacles, generalizes only confirmed uniform wall styles, and replans to
  visible interior landmarks;
- under a stricter visual contract, it matches a framed 2× edge badge to a
  board glyph under quarter-turn and one-to-one palette relabeling, learns from
  badge frames whether a compact control changes orientation or appearance,
  learns a repeated depleting paired-pixel edge meter, retains an already
  verified token/control relation (and only such a relation) through one
  transient unreadable frame or a visually revalidated spatial displacement,
  retains a landing tile that has ended the current level in GAME_OVER as a
  guarded obstacle until that level changes, and treats framed ring glyphs as
  one-use resources when they are reached, lie on an equally short learned
  route, or (between demonstrated stages of a multi-control response) are
  reachable before a meter-tight control/target leg; and
- it never retries the same click in an unchanged visual state.

This is an appropriate starting point for reliable plumbing and ablation. It
has no network inference, provider API, or model dependency, which is
important because competition evaluation runs without internet access.

## Current status — 3 September 2026

- Milestone #2 is **30 September 2026**.
- The public leaderboard is not a local-development metric; use local runs to
  catch regressions, then make deliberate Kaggle submissions.
- Kaggle permits **one official submission per day**. `make submit` only pushes
  a notebook for Kaggle's Save & Run All phase; it does not click the final
  **Submit to Competition** action.
- The tracked kernel metadata is private by default. Before a prize-eligible
  milestone, publish the notebook and source as required by the competition
  rules.

## Prerequisites

1. Python **3.12+** (required by the official `arc-agi` package).
2. A Kaggle account that has joined and accepted the ARC-AGI-3 competition
   rules.
3. A local Kaggle token. This repository's root `kaggle.json` is ignored and
   can be copied safely into this project's ignored `.kaggle/access_token`.
4. Optionally, an ARC platform API key in a local `.env` file for access to all
   public environments. Never commit it.

## Quick start

```bash
cd arc_agi3

# Copies ../kaggle.json to .kaggle/access_token with mode 600.
# It never prints the token.
make configure-kaggle

# Creates an ignored venv, installs the SDK and clones the official,
# MIT-licensed reference framework into ignored vendor/.
make setup

# Pure unit tests: no network, model, Kaggle token, or GPU needed.
make test

# First real-environment smoke run. The SDK caches public environment files
# below environment_files/ for later offline use. JSONL trajectories and a
# compact frame-free outcome report stay in ignored recordings/.
make verify-local

# Build, but do not upload, a Kaggle notebook.
make notebook
```

To use a GPU later, regenerate the notebook with, for example:

```bash
make notebook ACCELERATOR=rtx6000
```

Only after local validation should you push the notebook:

```bash
make submit
make status
```

Then inspect the Kaggle run. The final leaderboard submission is a separate,
deliberate action in Kaggle's UI and should only be used for a validated
candidate.

## GitHub Actions

`.github/workflows/arc-agi3.yml` runs the offline policy and notebook tests on
ARC source changes. The real public-game smoke job is never scheduled: run it
through **Run workflow** with `local_smoke=true`, or push an explicit commit
whose message contains `[arc-smoke]`. The latter is useful where the GitHub API
cannot create a workflow-dispatch event. It uses no Kaggle or ARC credential.

A separate bounded public evaluation runs 400 actions per selected public game:
use **Run workflow** with `public_eval=true`, push an explicit `[arc-eval]`
commit, or run `make evaluate-public EVAL_STEPS=400` locally. It is likewise
never scheduled and is an experiment—not a Kaggle submission. Each explicit
smoke/evaluation exposes a compact outcome table, action evidence, early and
checkpointed frame-derived avatar-tile geometry, and first/final public-frame
sketches in the check details; full public JSONL recordings remain an expiring
14-day artifact.

## Layout

```text
arc_agi3/
├── agent/
│   ├── policy.py              # Pure deterministic policy and perception helpers
│   └── my_agent.py            # ARC SDK adapter / MyAgent contract
├── scripts/
│   ├── configure_kaggle.py    # Secure local token handoff
│   ├── prepare_framework.py   # Prepares generated reference framework
│   ├── play_local.py          # Local public-game runner
│   ├── summarize_recordings.py # Frame sketches for CI/replay inspection
│   ├── publish_check_summary.py # Publishes safe run evidence to a check
│   └── build_notebook.py      # Creates Kaggle deployment artifact
├── tests/test_policy.py       # Offline regression tests
├── notebooks/kernel-metadata.json
└── Makefile
```

Generated resources are deliberately excluded from Git:

- `.kaggle/` and `.env` — credentials;
- `.venv/`, `vendor/` — local dependencies;
- `environment_files/`, `recordings/` — competition/game data and runs;
- `notebooks/submission.ipynb` — reproducible deployment artifact.

## Compatibility and attribution

`make setup` clones the official
[`ARC-AGI-3-Agents`](https://github.com/arcprize/ARC-AGI-3-Agents) framework
into `vendor/`; it is not committed here and remains under its MIT license.
The source in this directory is independently maintained and is licensed under
[CC BY 4.0](LICENSE), matching the ARC Prize winner-license requirement.

## Next technical step

Use recordings from `make verify-local` to identify the first recurring game
mechanics. Add narrowly scoped, test-covered primitives to `policy.py` only
when they improve a held-out public-game run. Do not hardcode private-game
information or rely on internet/model APIs in the deployed agent.
