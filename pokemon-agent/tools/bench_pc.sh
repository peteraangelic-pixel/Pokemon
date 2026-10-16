#!/usr/bin/env bash
# bench_pc.sh — measure THIS machine's speed on the exact PG workload:
# Rust+Rayon policy_rollout (FFI libcg.so) generating self-play games,
# plus one JAX training epoch. Prints games/sec per thread count and
# extrapolations for 240k / 1.6M games and full PG iteration loops.
#
# Usage:  bash tools/bench_pc.sh
# Knobs:  BENCH_JOBS="4 8 16 32"  BENCH_GAMES=8000  BENCH_TRAIN=1 (0=skip)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
GAMES="${BENCH_GAMES:-8000}"
JOBS_LIST="${BENCH_JOBS:-4 8 16 32}"
BIN="rust/target/release/policy_rollout"
DECK="decks/v66_alakazam_simple.csv"
WEIGHTS="tools/policy_alakazam_seed.json"
CIDX="tools/card_index_empty.json"
ROLLOUT_NPZ="kaggle_results/policy_alakazam/rollout.npz"

echo "== bench_pc: root=$ROOT games/sweep=$GAMES jobs=[$JOBS_LIST] =="

# --- python env (for libcg.so + optional train timing) ---
if [ ! -x .venv/bin/python ]; then
  echo "== no .venv, running setup.sh (one-time, a few minutes) =="
  bash setup.sh >/dev/null
fi
LIBCG=$(find .venv -name libcg.so | head -1)
[ -n "$LIBCG" ] || { echo "ERROR: libcg.so not found in .venv"; exit 1; }
mkdir -p libs
cp "$LIBCG" libs/libcg.so
echo "engine lib: $LIBCG"

# --- build the Rust rollout (Rust+Rayon, FFI to libcg) ---
if ! command -v cargo >/dev/null 2>&1; then
  echo "ERROR: cargo not found. Install Rust: https://rustup.rs  (on Windows use WSL2)"
  exit 1
fi
echo "== cargo build --release --bin policy_rollout =="
(cd rust && cargo build --release --bin policy_rollout 2>&1 | tail -2)

run_rollout () {  # $1=jobs $2=mode $3=games -> echoes games_per_sec
  local jobs=$1 mode=$2 games=$3 out
  out=$(mktemp /tmp/bench_rollout.XXXXXX.bin)
  local log
  log=$("./$BIN" --lib-dir libs --card-index "$CIDX" --weights "$WEIGHTS" \
        --decks "$DECK" --games "$games" --jobs "$jobs" \
        --eps 0.08 --temp 0.7 --mode "$mode" --out "$out" 2>&1 | tail -1)
  rm -f "$out"
  echo "$log" | sed -n 's/.*games_per_sec=\([0-9.]*\).*/\1/p'
}

echo
echo "== rollout sweep (train mode = real PG data generation, mirror $DECK) =="
BEST=0; BESTJ=0
printf "%6s %12s %14s %14s\n" jobs games/s "240k games" "1.6M games"
for J in $JOBS_LIST; do
  GPS=$(run_rollout "$J" train "$GAMES")
  [ -n "$GPS" ] || { echo "jobs=$J FAILED"; continue; }
  read -r T240 T16 <<<"$(awk -v g="$GPS" 'BEGIN{printf "%.1f %.1f", 240000/g/60, 1600000/g/60}')"
  printf "%6s %12s %11s min %11s min\n" "$J" "$GPS" "$T240" "$T16"
  awk -v g="$GPS" -v b="$BEST" 'BEGIN{exit !(g>b)}' && { BEST=$GPS; BESTJ=$J; }
done
echo "best rollout: ${BEST} games/s @ ${BESTJ} jobs"

echo
echo "== eval mode (gate-like, argmax) @ best jobs =="
GPS_EVAL=$(run_rollout "$BESTJ" eval 4000)
echo "eval: ${GPS_EVAL} games/s  (600-game test = $(awk -v g="$GPS_EVAL" 'BEGIN{printf "%.1f", 600/g}') s)"

# --- optional: time one PG training epoch (JAX, CPU) ---
TRAIN_EP=""
if [ "${BENCH_TRAIN:-1}" = "1" ] && [ -f "$ROLLOUT_NPZ" ]; then
  echo
  echo "== training timing: 1 epoch PG on $ROLLOUT_NPZ (this takes minutes) =="
  TLOG=$(.venv/bin/python tools/train_policy.py --data "$ROLLOUT_NPZ" \
    --init kaggle_results/policy_alakazam_seed.npz --out /tmp/bench_train.npz \
    --epochs 1 --lr 8e-4 --mode pg --entropy 0.01 2>&1 | grep "ep0:" | tail -1)
  echo "$TLOG"
  TRAIN_EP=$(echo "$TLOG" | sed -n 's/.*(\([0-9]*\)s).*/\1/p')
fi

echo
echo "================ SUMMARY (paste this back) ================"
echo "machine jobs sweep above; best rollout = ${BEST} g/s @ ${BESTJ} jobs"
awk -v g="$BEST" 'BEGIN{
  printf "rollout only: 240k games = %.1f min | 1.6M games = %.2f h\n", 240000/g/60, 1600000/g/3600}'
if [ -n "$TRAIN_EP" ]; then
  awk -v g="$BEST" -v ep="$TRAIN_EP" 'BEGIN{
    per_iter = 40000/g + 3*ep + 30;           # rollout + 3 epochs + convert/misc (s)
    printf "train: 1 epoch = %ds -> est. full PG loop (40k-game iters):\n", ep;
    printf "  240k total (6 iters)  = %.1f h\n", 6*per_iter/3600;
    printf "  1.6M total (40 iters) = %.1f h\n", 40*per_iter/3600;
  }'
else
  echo "train timing skipped/unavailable — full-loop estimate needs BENCH_TRAIN=1"
fi
echo "==========================================================="
