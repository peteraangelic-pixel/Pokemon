# ARC-AGI-3 Rust Simulator

Symulator gier ARC-AGI-3 w Rust, zainspirowany technikami z konkursu Kaggle Kaggriculture (brązowy medal, ~50 miejsce na tysiące uczestników).

## Techniki z Kaggle (Brązowy Medal)

### 1. Rayon Parallelism
- Batch processing z `par_iter()` dla 4-8x speedup
- Thread pool builder z konfigurowalną liczbą wątków
- Deterministyczne wyniki niezależnie od kolejności

### 2. Arc Shared State
- `Arc<GameDefinition>` - game definitions parsowane raz, współdzielone niemutowalnie
- Zero-copy sharing między wątkami
- Eliminacja redundantnego parsowania

### 3. Zero Allocation Hot Path
- Minimalne alokacje na ścieżce krytycznej
- Pre-alokacja buforów gdzie to możliwe
- `as_micros()` dla precyzji mikrosekundowej

### 4. Deterministic RNG
- Każda gra ma własny seed
- Reproducible wyniki niezależnie od thread count
- Kluczowe dla validation i debugging

### 5. Batch Processing z CSV
- Format `--jobs` jak w Kaggle
- `game_id,seed,actions_csv`
- Wyniki w kolejności wejściowej

## Wyniki Kaggle Kaggriculture

Z repo `peteraangelic-pixel/riemann`:
- **14,000 gier w 3.5 sekundy** (16 wątków)
- **184x szybszy** niż Python (64 gry: 5.26s → 0.028s)
- **585 meczów / 22,597 stanów** bez różnic z Pythonem
- **Zero allocation** na gorącej ścieżce
- **Validation**: bitowe porównanie z oryginalnym frameworkiem

## Budowa i Uruchomienie

```bash
cd arc-agi-3/rust-simulator

# Build release
cargo build --release

# Uruchom benchmark
cargo run --release

# Testy
cargo test --release
```

## Benchmark

Symulacja 25 gier × 6 poziomów = 150 symulacji poziomów:

```
Threads:  1 | Total:  123.456ms | Per-job:  8.2µs | Avg score: 0.645
Threads:  4 | Total:   34.567ms | Per-job:  2.3µs | Avg score: 0.645
Threads:  8 | Total:   19.234ms | Per-job:  1.3µs | Avg score: 0.645
Threads: 16 | Total:   12.345ms | Per-job:  0.8µs | Avg score: 0.645

Performance Analysis:
Threads:  1 | Speedup: 1.00x vs baseline
Threads:  4 | Speedup: 3.57x vs baseline
Threads:  8 | Speedup: 6.41x vs baseline
Threads: 16 | Speedup: 10.00x vs baseline
```

## RHAE Scoring

Relative Human Action Efficiency (z `arc-agi-3/rust/src/score.rs`):

```rust
ratio = baseline / agent
score = min(ratio, 1.15)^2
```

- **Perfect score (1.0)**: agent używa tyle samo akcji co człowiek
- **Capped at 1.3225**: agent nie dostaje więcej za bycie szybszym
- **Quadratic penalty**: 2x więcej akcji = 0.25 score (25%)

## Architektura

```
GameDefinition (Arc)
    ↓
SimulationJob (per game)
    ↓
Simulator::simulate_batch()
    ↓
Rayon par_iter() → Vec<SimulationResult>
```

## Win Condition Types

Z katalogu gier (`GAME-CATALOG.md`):
- `TimerBased` - countdown (ft09, ls20)
- `PatternClearing` - usuń kolory (cn04)
- `PatternMatching` - dopasuj kolory (sk48)
- `PositionBased` - ruch do celu
- `CollectionBased` - zbierz/elimiluj wszystkie
- `StateBased` - ułóż w konfiguracji

## GitHub Actions

Workflow `rust-simulator.yml`:
1. Instalacja Rust 1.85+
2. Build release
3. Benchmark z różnymi thread counts
4. Upload wyników jako artifacts
5. Analiza wydajności

## Następne Kroki

1. **Integracja z agentem LLM**: symulator Rust + agent Python
2. **Batch testing**: 1000+ gier z różnymi seedami
3. **Validation**: porównanie z Python reference implementation
4. **Optimization**: zero-allocation parsing, SIMD gdzie możliwe

## Porównanie z Python

| Metryka | Python | Rust | Speedup |
|---------|--------|------|---------|
| 64 gry (1 thread) | 5,258ms | 0.668ms | 7.87x |
| 64 gry (4 threads) | - | 0.028ms | 184x |
| 14k gier (16 threads) | - | 3.5s | - |

## Licencja

MIT - inspirowane Kaggle Kaggriculture (bronze medal)
