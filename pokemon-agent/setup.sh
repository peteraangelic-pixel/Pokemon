#!/usr/bin/env bash
# Rebuild the local dev environment from scratch.
#
# The .venv directory is NOT persisted between sessions, so run this first when
# picking the project back up.  Everything the agent itself needs (card_index.json,
# deck.csv) is committed, so the agent can be tested without re-running the dumps.
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
if [ ! -d .venv ]; then
  echo "==> creating .venv"
  "$PY" -m venv .venv
fi
echo "==> installing kaggle-environments (ships the cabt engine + native libs)"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet kaggle-environments

echo "==> engine self-check"
.venv/bin/python - <<'PY'
from kaggle_environments.envs.cabt.cg.sim import lib          # noqa: F401
from kaggle_environments.envs.cabt.cabt import deck
print(f"cabt engine loaded, sample deck has {len(deck)} cards")
PY

echo "==> deck legality"
.venv/bin/python tools/deck_rules.py

cat <<'MSG'

Ready. Try:
  .venv/bin/python tools/run_match.py --games 100            # heuristic vs random
  .venv/bin/python build_submission.py --smoke               # build + validate bundle
MSG
