# Benchmark PG na własnym PC (Rust + Rayon + FFI)

Mierzy dokładnie to obciążenie, które liczy nasz łańcuch policy-gradient:
generowanie gier self-play silnikiem `policy_rollout` (Rust, Rayon,
FFI do `libcg.so` z pakietu kaggle-environments) + jedną epokę treningu
JAX. Na końcu wypisuje tabelę `SUMMARY` z czasami dla 240 tys. i 1,6 mln
gier oraz całego loopa PG — tę tabelę wklej nam z powrotem.

## Wymagania

- **Linux albo WSL2** (na Windows tylko przez WSL2 — `libcg.so` to
  linuksowa biblioteka ELF, natywnie pod Windows nie wstanie)
- Rust: https://rustup.rs (`cargo --version` ma działać)
- Python 3.11 (skrypt sam zbuduje `.venv` przez `setup.sh`, jednorazowo
  kilka minut)
- ~4 GB wolnego miejsca (build Rusta + rollout testowy)

## Uruchomienie

```bash
git pull
cd Pokemon/pokemon-agent
bash tools/bench_pc.sh
```

Całość trwa zwykle 5–15 minut (sweep wątków na 8000 gier + 1 epoka
treningu). Można zawęzić:

```bash
BENCH_JOBS="16 32" BENCH_GAMES=12000 bash tools/bench_pc.sh
BENCH_TRAIN=0 bash tools/bench_pc.sh   # tylko rollout, bez treningu
```

## Co mierzymy

- **rollout train-mode** — generowanie danych PG (mirror prostej listy
  Alakazama, polityka BC jako gracz) — to jest ~cały koszt „gier”,
- **eval-mode** — odpowiednik bramek (argmax),
- **1 epoka treningu PG** na prawdziwym `rollout.npz` (91 MB) — z tego
  liczymy koszt iteracji: rollout 40k + 3 epoki + konwersja.

## Jak czytać wynik

- `best rollout = X g/s @ N jobs` — skalowanie Rayona na Twojej maszynie;
  w GitHub Actions mamy ~70 g/s przy 4 jobs.
- `rollout only: 1.6M = T h` — sam czas gier.
- `1.6M total (40 iters) = T h` — realistyczny czas całego PG z
  treningiem. To jest liczba, która mówi, czy „1,6 mln gier” to wieczór,
  czy tydzień — i czy w ogóle ma sens przy obserwowanym plateau bramek.
