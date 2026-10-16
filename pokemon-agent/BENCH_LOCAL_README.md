# bench_local — szybki benchmark Rust+Rayon+FFI na Twoje PC (32 wątki, 64GB)

Ten benchmark symuluje dokładnie to co liczy PG v2 w Actions, ale na Twoim sprzęcie — zmierzy `games/sec` i oszacuje czas dla 1.6M gier i dla 600g testu.

## Co mierzy

- **Heuristic mode** (nasz pilot Alakazam simple): `heuristic::decide` w Rust, FFI do `libcg.so`, Rayon `par_iter` po grach, osobna kopia `libcg_{i}.so` per wątek (engine nie jest thread-safe).
- **Policy mode** (na razie fallback do heuristic, ale struktura gotowa pod MLP) — docelowo `policy_rollout` z wagami `policy_alakazam_iter6.json`.

Wydrukuje:
```
games=600 wins=... winrate=0.xxx elapsed=1.5s games_per_sec=400
600g test: 1.5s @ 400 g/s
1.6M games rollout: 4000s = 66 min = 1.11h
With training (8 min per 40k iter): 40 iters = 6.7h
```

## Jak uruchomić na PC (Linux/WSL)

```bash
cd pokemon-agent
# 1. Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 2. Python venv + libcg.so
python3 -m venv .venv
.venv/bin/pip install kaggle-environments jax[cpu] numpy
mkdir -p libs
LIB=$(find .venv -name libcg.so | head -1)
for i in {0..31}; do cp $LIB libs/libcg_${i}.so; done
cp $LIB libs/libcg.so
ls -lh libs/ | head

# 3. Build
cd rust
cargo build --release --bin bench_local
cargo build --release --bin policy_rollout --bin gauntlet_rust
cd ..

# 4. Benchmark heuristic 600g vs Mengfei
./rust/target/release/bench_local --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir /tmp/mengfei --games 600 --jobs 32 --lib-dir libs --card-index assets/card_index.json

# 5. Benchmark heuristic 600g vs trolley_pool (3 decki x200)
./rust/target/release/bench_local --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --games 600 --jobs 32

# 6. Benchmark policy (jeśli masz wagi)
./rust/target/release/policy_rollout --lib-dir libs --card-index assets/card_index.json --weights tools/policy_alakazam_iter6.json --decks decks/trolley_pool --games 600 --jobs 32 --mode eval

# 7. Pełny PG v2 lokalnie (40k x6 iter) — jak druga gałąź
# patrz .github/workflows/policy-iter.yml — rollout + convert + train
```

## Oczekiwane czasy na 32 wątki

Z pomiarów Actions (4 jobs → 70 g/s):

- **600g test**: Actions 8.5s → **Twój PC ~1.5s @400 g/s**
- **40k rollout**: Actions 10 min → **Twój PC ~1.6 min**
- **1.6M rollout**: Actions 6.35h → **Twój PC ~1.1h**
- **1.6M + trening (40 iter x 8 min)**: Actions 23.3h → **Twój PC ~6.7h**

Ale plateau: +0.5pp/40k na początku, potem +0.1pp/80k. Żeby dojść z 0.51 do 0.709 (+20pp) potrzeba 5-10M gier → **30-60h na Twoim PC**, nie 6h.

## Pliki

- `rust/src/bin/bench_local.rs` — benchmark
- `rust/src/engine.rs` — FFI wrapper z mutexem na global state C++
- `rust/src/heuristic.rs` — pilot Alakazam (decide)
- `tools/policy_alakazam_iter6.json` — najlepsza polityka z drugiej gałęzi (iter6, 0.511 vs prev, 0.544 vs seed)

## Szybki test bez Rusta (Python multiprocessing)

Jeśli nie chcesz budować Rusta:

```bash
/tmp/venv/bin/python tools/gauntlet_ffi.py --agent agents/v70_alakazam_endgame.py --our-deck decks/v66_alakazam_simple.csv --opp-dir /tmp/mengfei --games 600 --workers 32
```

Na 4 workers: 100 gier = 3s → 33 g/s. Na 32 workers: ~200 g/s → 600 gier = 3s.
