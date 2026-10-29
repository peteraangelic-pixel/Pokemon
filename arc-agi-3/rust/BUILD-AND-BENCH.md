# Lokalne środowisko testowe na 5950X — budowa i pomiar

**Stan: kod nie był kompilowany w sandboxie, w którym powstał** (brak `cargo`).
Poniższe jest instrukcją doprowadzenia go do stanu używalności na Twojej maszynie,
a nie raportem z wykonanego pomiaru. Nie podaję tu żadnej liczby przyspieszenia,
bo jej nie zmierzyłem.

## 1. Budowa

```bash
cd arc-agi-3/rust
rustup update stable          # 1.75+ wystarczy; plan.rs używa let-else
cargo build --release
cargo test --release          # testy plan.rs + score.rs + grid.rs
```

Testy w `plan.rs` pokrywają: uczenie modelu przejść, wykrywanie niedeterminizmu
(ten sam `(stan, akcja)` → dwa różne stany **wyłącza** batchowanie w tym stanie),
BFS najkrótszej ścieżki z limitem głębokości, obcinanie batcha na pierwszym
nieznanym przejściu oraz stabilność `state_id` między procesami.

## 2. Pomiar na nagranych runach (bez GPU, bez sieci)

Artefakty z trzech realnych runów są w `local/benchmarks/`:

```bash
cd arc-agi-3
B=local/benchmarks

./rust/target/release/lab analyze  $B/r018.json
./rust/target/release/lab ceiling  $B/r018.json 200 275 400 800
./rust/target/release/lab policies $B/r018.json 275 400 600
./rust/target/release/lab sweep    $B/r013.json $B/r015.json $B/r018.json
```

`analyze` powinien odtworzyć tabelę z `MEGA-DIAGNOSIS.md` §2 (średnia: pokrycie
29,0%, efektywność 89,9%, wynik 25,09). `policies` z `prior 45` powinien odtworzyć
kolumnę „greedy (C0=45)" z §5. Jeśli nie odtwarza — kod i analiza się rozjechały,
i to jest właśnie sygnał, po który to narzędzie istnieje.

Równoważnik w Pythonie (działa już teraz, zweryfikowany):

```bash
python3 local/test_scheduler.py     # 9/9 PASS, pinuje liczby z dokumentu
```

## 3. Gdzie Rust naprawdę zarabia na siebie

Nie w schedulerze — ten jest tani i równie dobrze działa w Pythonie. Rust ma sens
w plannerze macro-akcji (`src/plan.rs`), bo tam praca jest w pętli interaktywnej:

| operacja | gdzie | czemu Rust |
|---|---|---|
| BFS po wyuczonym modelu przejść | `plan_to_goal` | wywoływane po każdej decyzji LLM, musi być < 1 ms |
| weryfikacja batcha | `safe_prefix`, `validate` | musi przerwać natychmiast przy rozjeździe predykcji |
| równoległe hipotezy modelu | `plan_parallel` (rayon) | 16 rdzeni × kilka hipotez = brak wpływu na budżet czasu |
| hash klatki jako `StateId` | `state_id` | FNV-1a, stabilny między procesami |

**Uwaga na budżet:** na Kaggle liczy się wall clock całego kernela, a ~99% idzie
na inferencję. Planner działa *między* decyzjami i musi być pomijalnie tani —
dlatego BFS jest limitowany głębokością (`max_depth`), a nie czasem.

## 4. Kolejność wdrożenia (z dokumentu §7)

1. **Batch jawny** — model w jednej turze emituje listę ruchów. Najmniejsze ryzyko,
   mierzy się to `local/abtest.py`, nie plannerem.
2. **Powtórzenie do zmiany klatki** — zero tokenów, jeśli akcja nie ruszyła klatki.
3. **Planner z `plan.rs`** — dopiero gdy 1 i 2 są zmierzone. Do tego czasu
   `plan_parallel` i `plan_to_goal` są martwym kodem i tak powinny zostać.

**Nie podłączać plannera do submitu przed pomiarem A/B.** Batch, który pudłuje,
zużywa akcje, a akcje są w mianowniku wyniku. Próg szumu przy n=20 na 6 grach to
0,30 pkt; pojedynczy run 10 gier widzi tylko efekty ≥ +10.

## 5. Czego tu nie ma

- Integracji z harnessem Ducka — to patch w Pythonie i należy do notebooka, nie do
  tej skrzynki.
- Modelu uczenia przejść z klatek (jest tylko tablica `(stan, akcja) → stan`).
  Podłączenie `state_id` + `observe` do realnej pętli to zadanie wdrożeniowe.
- Żadnych pomiarów wydajności. Nie mam `cargo`, więc nie mam prawa ich podawać.
