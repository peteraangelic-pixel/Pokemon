# Program Rust+Rayon na PC użytkownika (Windows) — plan

## Stan (2026-10-21)
- Kod Rust na obu gałęziach jest DZIŚ identyczny (diff 0). Historia:
  15 paź nasza linia: `policy_rollout` (rollouty RL); 16 paź import z linii
  c87: `gen_bc_data_rust(_mt)`, `engine_mt`, `policy_feats` (pipeline BC);
  19 paź c87 przywróciła crate od nas (`2269086`).
- Silnik gry: oficjalny wheel `kaggle-environments` zawiera **cg.dll**
  (Windows) obok libcg.so/libcg.dylib — natywny build Windows jest możliwy.

## Windows — jak uruchomić (po zbudowaniu .exe przez CI)
1. `pip install kaggle-environments` — cg.dll ląduje w
   `Lib\site-packages\kaggle_environments\envs\cabt\cg\cg.dll`.
2. Skopiuj `cg.dll` obok .exe ALBO wskaż `--lib <ścieżka do cg.dll>`.
3. `policy_rollout` wymaga kopii silnika per wątek: w `--lib-dir` umieść
   kopie `cg_0.dll`, `cg_1.dll`, ... (po jednej na wątek).
4. Opcjonalnie budowa lokalna: rustup + `RUSTFLAGS=-C target-cpu=native`.

## Etapy ulepszeń (wybrany zakres: oba kierunki)
- [x] Etap 1: platformowy wybór biblioteki (cg.dll/libcg.so), build
      windows-latest w CI (.exe do `bin-win/`), smoke `--help`.
- [ ] Etap 2: port PRAWDZIWEJ polityki (scoring championa/v67) do
      `heuristic.rs` — dziś prymityw „first option" + crash `rust_full`
      na ENERGY selectach. Plus bezpieczne opakowanie `Select`
      (shim try/catch), bramki parytetu z PORTING.md.
- [ ] Etap 3: jeden tryb ligi w gauntlecie (macierz agent×deck, przedziały
      ufności, JSON), config TOML zamiast flag, pasek postępu/ETA,
      statystyki porażek (głód, 0 nagród) jak w narzędziach Python.
- [ ] Etap 4: pętla RL na PC bez limitu 6 h Actions: shardy danych
      (BC/PPO) zapisywane przyrostowo przez `gen_bc_data_rust_mt` /
      `policy_rollout`, liga decków i pilotów, log belief pod GRU,
      trening Python równolegle, okresowa ewaluacja checkpointów.

## Znane ograniczenia
- `rust_full` crashuje na ENERGY selectach (wyjątek C++ przez FFI) —
  do naprawy w etapie 2; gauntlety subprocessowe działają.
- Heurystyka natywna gra słabo (nie jest portem championa) — etap 2.

## Uwaga: klonowanie repo na Windows
Pełny `git clone` na Windows pada na nazwach plików talii z niedozwolonymi
znakami NTFS (np. `decks/meta1012/(...<).csv`). Na PC klonuj rzadko:
`git clone --filter=blob:none --sparse ...` i
`git sparse-checkout set pokemon-agent/rust pokemon-agent/decks`,
albo po prostu pobierz same pliki .exe z katalogu `bin-win/`.
