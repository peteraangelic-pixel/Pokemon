# Port kit: our-replays win-rate digest (from arena/8560a56a-pokemon)

**Why:** the poller on this branch only fetches μ from the leaderboard. μ is
noisy (±110 μ per submission; same v21 code scored 600/450/385). The only
decision-grade signal is **live win rate from our own episodes**. This kit adds
a second workflow that fetches the last 80 episodes of the two live
submissions, classifies every loss (empty-bench KO / archetype / opponent),
and commits a compact digest — same Kaggle credentials as kaggle-poll.

**What it produces** (committed to `pokemon-agent/kaggle_results/our_replays/`):
- `episodes_table.csv` — one row per episode: sub, opponent, win/loss, turn,
  our/opponent archetype, final boards.
- `loss_snapshots.jsonl` — per loss: final boards, KO'd pokemon, last 25 log
  events, our last 14 decisions (forensics without the raw replay).
- `summary.md` — W-L per submission by archetype and recurring opponent.
- Raw replay JSONs are NOT committed (gitignored); re-fetchable anytime.

## Apply (3 commands + 1 push)

```bash
cd pokemon-agent
cp kaggle_results/port_kit_our_replays/fetch_replays.py    tools/
cp kaggle_results/port_kit_our_replays/summarize_episodes.py tools/
cp kaggle_results/port_kit_our_replays/kaggle_our_replays.yml ../.github/workflows/
# .gitignore additions (repo root):
#   pokemon-agent/kaggle_results/our_replays/episode-*-replay.json
#   pokemon-agent/kaggle_results/our_replays/loss_replays/
git add -A && git commit -m "feat: our-replays win-rate digest (port from 8560a56a)" && git push
# the push fires the workflow (trigger file is part of the kit)
```

## Re-run later

```bash
echo "refetch $(date -u +%FT%TZ)" > kaggle_results/our_replays.trigger
git add -A && git commit -m "poll our replays" && git push
```

## Reading the output

- `summary.md` header gives W-L per ACTIVE submission (win% = the number that
  actually moves rank).
- 90+ episodes ≈ ±5% win-rate resolution — enough to accept/reject a shipped
  agent; <30 episodes is directional only.
- `loss_snapshots.jsonl` lines are JSON: `opp_arch` tags the matchup,
  `our_board`/`opp_board` are the final boards, `our_ko`/`opp_ko` the KO'd
  pokemon lists. A loss with `our_board` length ≤ 1 = board-collapse death
  (the mode we died by 98% of the time in the v11-v22b era, see
  `live_loss_forensics_2026_10_12.md` on the donor branch).

## Requirements

- Secrets: `KAGGLE_API_TOKEN` (or `KAGGLE_USERNAME`+`KAGGLE_KEY`) — same as
  kaggle-poll; already present in the repo.
- No extra pip deps beyond `kaggle` (installed by the workflow).
- The workflow self-heals: one corrupt episode file cannot kill the run
  (per-file try/except + poison-file drop), and fetch/summarize failures are
  loud (no pipe-swallowed exit codes).
