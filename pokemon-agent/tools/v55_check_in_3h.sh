#!/bin/bash
# One-shot delayed fetch: after 3h, trigger Kaggle poll + our-replays so the
# bot commit-back lands fresh v55 results/replays in the repo for analysis.
LOG=/home/user/Pokemon/pokemon-agent/kaggle_results/v55_check_3h.log
echo "[check3h] start $(date -u +%FT%TZ), sleeping 3h" >> "$LOG"
sleep 10800
cd /home/user/Pokemon || exit 1
echo "[check3h] waking $(date -u +%FT%TZ)" >> "$LOG"
git fetch -q origin arena/a450b00f-pokemon >> "$LOG" 2>&1 || true
git pull --rebase -q origin arena/a450b00f-pokemon >> "$LOG" 2>&1 || true
date -u +%FT%TZ > pokemon-agent/kaggle_results/poll.trigger
date -u +%FT%TZ > pokemon-agent/kaggle_results/our_replays.trigger
git add pokemon-agent/kaggle_results/poll.trigger pokemon-agent/kaggle_results/our_replays.trigger >> "$LOG" 2>&1 || true
git commit -q -m "auto: 3h check v55 results (user-scheduled)" >> "$LOG" 2>&1 || true
git push -q origin arena/a450b00f-pokemon >> "$LOG" 2>&1 || echo "[check3h] PUSH FAILED" >> "$LOG"
echo "[check3h] triggers pushed $(date -u +%FT%TZ); waiting 7 min for bot commit-back" >> "$LOG"
sleep 420
git fetch -q origin arena/a450b00f-pokemon >> "$LOG" 2>&1 || true
git log --oneline -3 origin/arena/a450b00f-pokemon >> "$LOG" 2>&1 || true
echo "[check3h] done $(date -u +%FT%TZ) - results should be in kaggle_results/summary.md" >> "$LOG"
