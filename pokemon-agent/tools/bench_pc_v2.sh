#!/usr/bin/env bash
# bench_pc_v2.sh — PC benchmark for the PG workload, v2 methodology.
#
# What changed vs tools/bench_pc.sh (v1, kept for comparison):
#   * time-boxed measurement (warm-up + repeat batches until MIN_SECONDS),
#     median/min/max per jobs level instead of one fixed-size run
#   * jobs-scaling efficiency column
#   * decisions/sec + rollout size on top of games/sec
#   * two deck profiles: mirror (comparable) and production pool (real PG)
#   * full pipeline timing: rollout -> convert -> train(epoch) -> export,
#     full-loop estimate built from measured stage rates, not a guessed +30s
#   * run validation (valid==games, engine error counters must be 0)
#   * machine/code metadata + JSON report (BENCH_REPORT path)
#
# Usage: bash tools/bench_pc_v2.sh
# Knobs (env):
#   BENCH_JOBS="4 8 16 32"   BENCH_BATCH_GAMES=4000  BENCH_MIN_SECONDS=60
#   BENCH_MAX_BATCHES=8      BENCH_WARMUP_GAMES=1000 BENCH_TRAIN=1 (0=skip)
#   BENCH_POOL=1 (0=skip production-pool profile)    BENCH_REPORT=/tmp/bench_pc_v2_report.json
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
JOBS_LIST="${BENCH_JOBS:-4 8 16 32}"
BATCH_GAMES="${BENCH_BATCH_GAMES:-4000}"
MIN_SECONDS="${BENCH_MIN_SECONDS:-60}"
MAX_BATCHES="${BENCH_MAX_BATCHES:-8}"
WARMUP_GAMES="${BENCH_WARMUP_GAMES:-1000}"
DO_TRAIN="${BENCH_TRAIN:-1}"
DO_POOL="${BENCH_POOL:-1}"
REPORT="${BENCH_REPORT:-/tmp/bench_pc_v2_report.json}"
BIN="rust/target/release/policy_rollout"
DECK="decks/v66_alakazam_simple.csv"
WEIGHTS="tools/policy_alakazam_seed.json"
SEED_NPZ="kaggle_results/policy_alakazam_seed.npz"
CIDX="tools/card_index_empty.json"
WORK=$(mktemp -d /tmp/bench_pc_v2.XXXXXX)
trap 'rm -rf "$WORK"' EXIT

echo "== bench_pc_v2: root=$ROOT =="
echo "jobs=[$JOBS_LIST] batch=$BATCH_GAMES min_seconds=$MIN_SECONDS warmup=$WARMUP_GAMES"

# ---------- environment ----------
if [ ! -x .venv/bin/python ]; then
  echo "== no .venv, running setup.sh (one-time, a few minutes) =="
  bash setup.sh >/dev/null
fi
LIBCG=$(find .venv -name libcg.so | head -1)
[ -n "$LIBCG" ] || { echo "ERROR: libcg.so not found in .venv"; exit 1; }
mkdir -p libs && cp "$LIBCG" libs/libcg.so
command -v cargo >/dev/null 2>&1 || { echo "ERROR: cargo not found (https://rustup.rs; on Windows use WSL2)"; exit 1; }
echo "== cargo build --release --bin policy_rollout =="
(cd rust && cargo build --release --bin policy_rollout 2>&1 | tail -1)

# ---------- rollout helpers ----------
# run_rollout <jobs> <mode> <games> <deckarg> <outfile|-> ; sets R_GAMES R_VALID R_ELAPSED R_GPS R_ERR R_LINE
run_rollout() {
  local jobs=$1 mode=$2 games=$3 deckarg=$4 outfile=$5
  local args=(--lib-dir libs --card-index "$CIDX" --weights "$WEIGHTS"
              --decks "$deckarg" --games "$games" --jobs "$jobs"
              --eps 0.08 --temp 0.7 --mode "$mode")
  [ "$outfile" != "-" ] && args+=(--out "$outfile")
  R_LINE=$("./$BIN" "${args[@]}" 2>&1 | grep '^games=' | tail -1 || true)
  [ -n "$R_LINE" ] || { echo "ERROR: rollout produced no summary (jobs=$jobs mode=$mode)"; exit 1; }
  R_GAMES=$(echo "$R_LINE"  | sed -n 's/.*games=\([0-9]*\).*/\1/p')
  R_VALID=$(echo "$R_LINE"  | sed -n 's/.*valid=\([0-9]*\).*/\1/p')
  R_ELAPSED=$(echo "$R_LINE" | sed -n 's/.*elapsed=\([0-9.]*\)s.*/\1/p')
  R_GPS=$(echo "$R_LINE"    | sed -n 's/.*games_per_sec=\([0-9.]*\).*/\1/p')
  R_ERR=$(echo "$R_LINE" | sed -n 's/.*err\[\(.*\)\].*/\1/p' | grep -o '[0-9]\+' | awk '{s+=$1} END{print s+0}')
}

median_of() { for v in $1; do echo "$v"; done | sort -n | awk '{a[NR]=$1} END{if(NR)printf "%.1f",(NR%2?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2)}'; }
min_of() { for v in $1; do echo "$v"; done | sort -n | head -1; }
max_of() { for v in $1; do echo "$v"; done | sort -n | tail -1; }

# ---------- sweep: mirror profile ----------
echo
echo "== profile MIRROR ($DECK), train mode with decision logging =="
run_rollout "${JOBS_LIST%% *}" train "$WARMUP_GAMES" "$DECK" -   # warm-up, discarded
echo "warm-up ok (${R_GPS} g/s)"
JOBS_TSV="$WORK/jobs.tsv"; : > "$JOBS_TSV"
BASE_JOBS=""; BASE_GPS=""; BEST_GPS=0; BEST_JOBS=0; BEST_FILE=""
printf "%5s %7s %9s %9s %9s %9s %8s %6s\n" jobs batches agg_g/s med_g/s min max effic valid
for J in $JOBS_LIST; do
  vals=""; tot_g=0; tot_t=0; nb=0; errs=0; last_file=""
  while :; do
    nb=$((nb+1))
    last_file="$WORK/roll_j${J}_b${nb}.bin"
    run_rollout "$J" train "$BATCH_GAMES" "$DECK" "$last_file"
    vals="$vals $R_GPS"; tot_g=$((tot_g + R_GAMES)); errs=$((errs + R_ERR))
    tot_t=$(awk -v a="$tot_t" -v b="$R_ELAPSED" 'BEGIN{printf "%.2f", a+b}')
    [ "$R_VALID" = "$R_GAMES" ] || echo "WARN: jobs=$J valid=$R_VALID != games=$R_GAMES"
    awk -v t="$tot_t" -v m="$MIN_SECONDS" 'BEGIN{exit !(t>=m)}' && break
    [ "$nb" -ge "$MAX_BATCHES" ] && break
  done
  agg=$(awk -v g="$tot_g" -v t="$tot_t" 'BEGIN{printf "%.1f", g/t}')
  med=$(median_of "$vals"); mn=$(min_of "$vals"); mx=$(max_of "$vals")
  if [ -z "$BASE_JOBS" ]; then BASE_JOBS=$J; BASE_GPS=$agg; eff="1.00x"; else
    eff=$(awk -v a="$agg" -v b="$BASE_GPS" -v j="$J" -v bj="$BASE_JOBS" 'BEGIN{printf "%.2f", (a/b)/(j/bj)}')
  fi
  printf "%5s %7s %9s %9s %9s %9s %7s %6s\n" "$J" "$nb" "$agg" "$med" "$mn" "$mx" "$eff" "$([ "$errs" = 0 ] && echo OK || echo "ERR=$errs")"
  echo -e "$J\t$nb\t$tot_g\t$tot_t\t$agg\t$med\t$mn\t$mx\t$errs" >> "$JOBS_TSV"
  if awk -v a="$agg" -v b="$BEST_GPS" 'BEGIN{exit !(a>b)}'; then
    [ -n "$BEST_FILE" ] && rm -f "$BEST_FILE"
    BEST_GPS=$agg; BEST_JOBS=$J; BEST_FILE=$last_file
  else
    rm -f "$last_file"
  fi
done
echo "best: ${BEST_GPS} g/s @ ${BEST_JOBS} jobs"

# ---------- eval (gate-like) at best jobs ----------
run_rollout "$BEST_JOBS" eval 4000 "$DECK" -
EVAL_GPS=$R_GPS
echo "eval @best jobs: ${EVAL_GPS} g/s (600-game gate = $(awk -v g="$EVAL_GPS" 'BEGIN{printf "%.1f",600/g}') s)"

# ---------- production pool profile at best jobs ----------
POOL_GPS=""; POOL_ERR=""
if [ "$DO_POOL" = "1" ]; then
  POOL_DIR="$WORK/policy_pool"; mkdir -p "$POOL_DIR"
  for f in decks/top30_live/YumeNeko.csv decks/v57_trolley34w.csv decks/shaun2024_wall.csv \
           kaggle_results/our_replays/opp_decks_v59/opp_15.csv; do
    [ -f "$f" ] && cp "$f" "$POOL_DIR/" 2>/dev/null || true
  done
  cp decks/live_v56t/*.csv "$POOL_DIR/" 2>/dev/null || true
  run_rollout "$BEST_JOBS" train "$BATCH_GAMES" "$POOL_DIR" "$WORK/pool.bin"
  POOL_GPS=$R_GPS; POOL_ERR=$R_ERR
  echo "profile POOL ($(ls "$POOL_DIR" | wc -l) decks) @best jobs: ${POOL_GPS} g/s, errors=$POOL_ERR (single batch)"
fi

# ---------- pipeline stages on the kept best-jobs rollout ----------
echo
echo "== pipeline stages (kept rollout from best jobs: $BATCH_GAMES games) =="
BIN_MB=$(awk -v b="$(stat -c%s "$BEST_FILE" 2>/dev/null || stat -f%z "$BEST_FILE")" 'BEGIN{printf "%.1f", b/1048576}')
t0=$(date +%s.%N)
.venv/bin/python tools/convert_rollout.py --max-dec 2500000 "$BEST_FILE" "$WORK/bench_rollout.npz" > "$WORK/convert.log" 2>&1
t1=$(date +%s.%N)
CONVERT_S=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
DECISIONS=$(grep -o 'converted [0-9]* decisions' "$WORK/convert.log" | grep -o '[0-9]*' | head -1)
DECISIONS=${DECISIONS:-0}
DPG=$(awk -v d="$DECISIONS" -v g="$BATCH_GAMES" 'BEGIN{printf "%.1f", (g>0? d/g : 0)}')
echo "convert: ${CONVERT_S}s, decisions=$DECISIONS (${DPG}/game), rollout file=${BIN_MB} MB"

TRAIN_EP_S=""; EXPORT_S=""
if [ "$DO_TRAIN" = "1" ] && [ "$DECISIONS" != "0" ]; then
  .venv/bin/python tools/train_policy.py --data "$WORK/bench_rollout.npz" \
    --init "$SEED_NPZ" --out "$WORK/bench_train.npz" \
    --epochs 1 --lr 8e-4 --mode pg --entropy 0.01 > "$WORK/train.log" 2>&1
  TRAIN_EP_S=$(grep 'ep0:' "$WORK/train.log" | tail -1 | sed -n 's/.*(\([0-9]*\)s).*/\1/p')
  t0=$(date +%s.%N)
  .venv/bin/python tools/export_policy_json.py "$WORK/bench_train.npz" "$WORK/bench_train.json" >/dev/null 2>&1
  t1=$(date +%s.%N)
  EXPORT_S=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
  echo "train: 1 epoch = ${TRAIN_EP_S}s on $DECISIONS decisions (incl. JAX start-up); export = ${EXPORT_S}s"
fi

# ---------- metadata + summary + JSON ----------
CPU_MODEL=$( (lscpu 2>/dev/null | awk -F: '/Model name/{sub(/^ +/,"",$2); print $2; exit}') || sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)
CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "?")
RAM_GB=$(awk '/MemTotal/{printf "%.0f", $2/1048576}' /proc/meminfo 2>/dev/null || echo "?")
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
DECK_SHA=$(sha256sum "$DECK" 2>/dev/null | cut -c1-12 || echo "?")
W_SHA=$(sha256sum "$WEIGHTS" 2>/dev/null | cut -c1-12 || echo "?")

export BENCH_JOBS_TSV="$JOBS_TSV" BENCH_REPORT="$REPORT"
export M_CPU="$CPU_MODEL" M_CORES="$CORES" M_RAM="$RAM_GB" M_GIT="$GIT_SHA" M_DECK="$DECK_SHA" M_W="$W_SHA"
export R_BEST_GPS="$BEST_GPS" R_BEST_JOBS="$BEST_JOBS" R_EVAL_GPS="$EVAL_GPS" R_POOL_GPS="$POOL_GPS"
export R_DEC="$DECISIONS" R_DPG="$DPG" R_BIN_MB="$BIN_MB" R_CONVERT_S="$CONVERT_S" R_TRAIN_EP="$TRAIN_EP_S" R_EXPORT_S="$EXPORT_S"
.venv/bin/python - <<'PYEOF'
import json, os, platform, datetime
rows = []
try:
    for ln in open(os.environ["BENCH_JOBS_TSV"]):
        p = ln.rstrip("\n").split("\t")
        if len(p) == 9:
            rows.append({"jobs": int(p[0]), "batches": int(p[1]), "games": int(p[2]),
                         "elapsed_s": float(p[3]), "agg_gps": float(p[4]), "median_gps": float(p[5]),
                         "min_gps": float(p[6]), "max_gps": float(p[7]), "errors": int(p[8])})
except Exception:
    pass
def f(k):
    v = os.environ.get(k, "")
    try: return float(v)
    except Exception: return v
best = f("R_BEST_GPS"); dec = f("R_DEC"); conv = f("R_CONVERT_S"); ep = f("R_TRAIN_EP")
pool = f("R_POOL_GPS"); gps_loop = pool if isinstance(pool, float) and pool > 0 else best
out = {
  "tool": "bench_pc_v2", "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "machine": {"cpu": os.environ.get("M_CPU"), "cores": os.environ.get("M_CORES"),
              "ram_gb": os.environ.get("M_RAM"), "system": platform.system(),
              "release": platform.release()},
  "code": {"git": os.environ.get("M_GIT"), "deck_sha": os.environ.get("M_DECK"),
           "weights_sha": os.environ.get("M_W")},
  "jobs_sweep": rows,
  "best_gps": best, "best_jobs": os.environ.get("R_BEST_JOBS"),
  "eval_gps": f("R_EVAL_GPS"), "pool_gps": pool,
  "decisions": dec, "decisions_per_game": f("R_DPG"), "rollout_mb": f("R_BIN_MB"),
  "convert_s": conv, "train_epoch_s": ep, "export_s": f("R_EXPORT_S"),
  "estimates": {},
}
if isinstance(best, float) and best > 0:
    out["estimates"]["rollout_only_min"] = {str(n): round(n / best / 60, 1) for n in (240000, 500000, 1600000)}
if isinstance(best, float) and best > 0 and isinstance(dec, float) and dec > 0 \
   and isinstance(ep, (int, float)) and isinstance(conv, (int, float)):
    cap = 2500000.0
    capped = min(float(os.environ.get("R_DPG", 0)) * 40000, cap)
    per_iter = 40000 / gps_loop + conv / dec * capped + 3 * ep / dec * capped \
        + 2000 / max(f("R_EVAL_GPS") or 1, 1)
    out["estimates"]["pg_loop_hours"] = {str(n): round(n / 40000 * per_iter / 3600, 2)
                                         for n in (240000, 500000, 1600000)}
    out["estimates"]["per_iter_s"] = round(per_iter, 1)
with open(os.environ["BENCH_REPORT"], "w") as fh:
    json.dump(out, fh, indent=1)
print(json.dumps(out["estimates"], indent=1))
PYEOF

echo
echo "================ SUMMARY bench_pc_v2 (paste this back) ================"
echo "machine: $CPU_MODEL | cores=$CORES ram=${RAM_GB}GB | git=$GIT_SHA deck=$DECK_SHA weights=$W_SHA"
echo "mirror best: ${BEST_GPS} g/s @ ${BEST_JOBS} jobs | eval: ${EVAL_GPS} g/s | pool: ${POOL_GPS:-n/a} g/s"
echo "decisions/game: $DPG | convert: ${CONVERT_S}s | train epoch: ${TRAIN_EP_S:-n/a}s"
awk -v g="$BEST_GPS" 'BEGIN{printf "rollout only: 240k=%.1f min, 500k=%.1f min, 1.6M=%.2f h\n", 240000/g/60, 500000/g/60, 1600000/g/3600}'
[ -n "$TRAIN_EP_S" ] && [ "$DECISIONS" != "0" ] && .venv/bin/python - <<PYEOF
gps = float("$BEST_GPS"); pool = "${POOL_GPS:-}"
gps = float(pool) if pool else gps
dec, dpg = float("$DECISIONS"), float("$DPG")
per_iter = 40000/gps + float("$CONVERT_S")/dec*min(dpg*40000, 2500000) \
    + 3*float("$TRAIN_EP_S")/dec*min(dpg*40000, 2500000) + 2000/max(float("$EVAL_GPS"),1)
print(f"full PG loop (40k-game iters): 240k={6*per_iter/3600:.1f} h, 1.6M={40*per_iter/3600:.1f} h  (per iter {per_iter/60:.1f} min)")
PYEOF
echo "JSON report: $REPORT"
echo "======================================================================="
