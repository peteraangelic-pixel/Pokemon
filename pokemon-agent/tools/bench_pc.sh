#!/bin/bash
# bench_pc.sh — benchmark PG workload: policy_rollout + JAX training, like second branch
# Measures same workload as PG v2, not just heuristic throughput

set -e
cd "$(dirname "$0")/.."
echo "=== bench_pc.sh — PG workload (policy + featurization + log + JAX train) ==="

# find lib
LIB=$(find .venv -name libcg.so 2>/dev/null | head -1)
if [ -z "$LIB" ]; then
  LIB=$(find /tmp/venv -name libcg.so 2>/dev/null | head -1)
fi
if [ -z "$LIB" ]; then
  echo "libcg.so not found, creating venv..."
  python3 -m venv .venv
  .venv/bin/pip install kaggle-environments jax[cpu] numpy
  LIB=$(find .venv -name libcg.so | head -1)
fi
echo "LIB=$LIB"
mkdir -p libs
cp "$LIB" libs/libcg.so
for i in {0..31}; do cp "$LIB" "libs/libcg_${i}.so"; done

# build
cd rust
cargo build --release --bin policy_rollout
cd ..

# weights
if [ ! -f tools/policy_alakazam_iter6.json ]; then
  echo "policy weights not found, using dummy"
  # create dummy
  echo '{"dummy":1}' > /tmp/dummy.json
  WEIGHTS=/tmp/dummy.json
else
  WEIGHTS=tools/policy_alakazam_iter6.json
fi

echo ""
echo "[1] Rollout 10k games — policy + featurization + log"
time ./rust/target/release/policy_rollout --lib-dir libs --card-index assets/card_index.json --weights $WEIGHTS --decks decks/trolley_pool --games 10000 --jobs 32 --mode train --out /tmp/rollout.bin 2>&1 | tail -n 5
ls -lh /tmp/rollout.bin

echo ""
echo "[2] Convert rollout.bin -> rollout.npz"
time .venv/bin/python tools/convert_rollout.py /tmp/rollout.bin /tmp/rollout.npz 2>&1 | tail -n 5
ls -lh /tmp/rollout.npz

echo ""
echo "[3] Train 1 epoch JAX"
time .venv/bin/python tools/train_policy.py --data /tmp/rollout.npz --init kaggle_results/policy_rust.npz --out /tmp/policy_iter.npz --epochs 1 --lr 8e-4 --mode pg --entropy 0.01 2>&1 | tail -n 20

echo ""
echo "=== ESTIMATES ==="
echo "10k rollout time above ×4 = 40k"
echo "40k rollout + 3 epochs train = per iter"
echo "1.6M = 40 iters"
