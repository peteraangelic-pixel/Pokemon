# bench_local — SZYBKI benchmark (1.5s), nie 6h!

**Ważne:** sam benchmark trwa **1.5 sekundy** (600 gier). 6.7h to tylko **szacowany czas** gdybyś chciał policzyć pełne 1.6M gier + trening — benchmark tego NIE liczy, tylko szacuje.

## Szybki benchmark (3 sekundy)

```bash
# Python — 100 gier, 3s, od razu szacuje 1.6M
/tmp/venv/bin/python tools/bench_quick.py --agent agents/v69_tunable.py --deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --games 100 --workers 32

# Rust — 600 gier, 1.5s @400 g/s, od razu szacuje 1.6M
./rust/target/release/bench_local --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --games 600 --jobs 32 --lib-dir libs
```

Wydruk:
```
Zmierzone: 300 gier w 0.8s = 375 g/s
600g test: 1.6s
40k rollout: 106s = 1.8 min
1.6M rollout: 4266s = 1.18h
1.6M + trening: 6.7h
To jest SZYBKI benchmark — sam trwa 0.8s, a szacuje 1.6M bez liczenia!
```

## Co mierzy bench_local

- Heuristic: `heuristic::decide` Rust + FFI `libcg.so` + Rayon `par_iter`, kopie `libcg_{i}.so` per wątek
- Policy: `policy_rollout` z wagami `policy_alakazam_iter6.json` 3.4M
- Mierzy `games/sec` i winrate, potem liczy estymaty

## Pełne czasy (estymaty, nie liczone)

Z Actions (4 jobs → 70 g/s):
- 600g: 8.5s
- 40k: 10 min
- 1.6M rollout: 6.35h
- 1.6M + trening: 23.3h

Na Twoim PC 32 wątki @400 g/s:
- **600g: 1.5s** ← to jest benchmark
- 40k: 1.6 min
- 1.6M rollout: 1.1h
- 1.6M + trening: 6.7h ← to jest gdybyś chciał pełny trening, nie benchmark

Ale plateau: iter4 0.510 → iter6 0.511 (+0.1pp/80k). Do 0.709 potrzeba 5-10M → 30-60h.

## Jak zbudować

```bash
cd pokemon-agent
python3 -m venv .venv && .venv/bin/pip install kaggle-environments jax[cpu] numpy
mkdir -p libs && LIB=$(find .venv -name libcg.so)
for i in {0..31}; do cp $LIB libs/libcg_${i}.so; done; cp $LIB libs/libcg.so
cd rust && cargo build --release --bin bench_local --bin policy_rollout && cd ..
```

## Pliki

- `rust/src/bin/bench_local.rs` — benchmark 1.5s
- `tools/bench_quick.py` — benchmark 3s Python
- `tools/policy_alakazam_iter6.json` — polityka iter6 (0.511 vs prev, 0.544 vs seed)
