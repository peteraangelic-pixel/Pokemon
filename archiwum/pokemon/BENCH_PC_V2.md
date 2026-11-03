# Benchmark PC v2 — Rust + Rayon + FFI (metodologia v2)

Stara wersja `tools/bench_pc.sh` zostaje w repo bez zmian — możesz
uruchomić obie i porównać wyniki. Wersja v2 (`tools/bench_pc_v2.sh`)
mierzy ten sam rzeczywisty workload PG (policy_rollout + konwersja +
trening), ale z poprawioną metodologią:

| aspekt | v1 (stary) | v2 (ten) |
|---|---|---|
| pomiar per jobs | 1 bieg, stałe 8000 gier | warm-up + partie do min. 60 s, mediana/min/max |
| skalowanie | same g/s | g/s + efektywność vs baza |
| obciążenie | mirror jednej talii | mirror + produkcyjna pula PG |
| miara pracy | gry/s | gry/s + decyzje/s + MB rolloutu |
| koszt loopa | epoka + zgadywane +30 s | zmierzone etapy: rollout→convert→train→export |
| walidacja | brak | valid==games, liczniki błędów silnika == 0 |
| raport | tekst | tekst + JSON z metadanymi maszyny i kodu |

## Uruchomienie

Linux / WSL2:

```bash
cd Pokemon/pokemon-agent
bash tools/bench_pc_v2.sh
```

Windows (PowerShell, wymaga WSL2 — `libcg.so` to linuksowy ELF):

```powershell
.\Pokemon\pokemon-agent\tools\bench_pc_v2.ps1
```

Czas: typowo 10–20 minut (sweep wątków + trening jednej epoki).
Szybki wariant:

```bash
BENCH_JOBS="16 32" BENCH_MIN_SECONDS=30 BENCH_POOL=0 bash tools/bench_pc_v2.sh
```

## Zmienne

| zmienna | domyślnie | znaczenie |
|---|---|---|
| `BENCH_JOBS` | `4 8 16 32` | testowane liczby wątków Rayona |
| `BENCH_BATCH_GAMES` | 4000 | gier na partię pomiarową |
| `BENCH_MIN_SECONDS` | 60 | min. czas pomiaru na poziom jobs |
| `BENCH_MAX_BATCHES` | 8 | limit partii na poziom jobs |
| `BENCH_WARMUP_GAMES` | 1000 | rozgrzewka (odrzucana) |
| `BENCH_POOL` | 1 | profil produkcyjnej puli decków |
| `BENCH_TRAIN` | 1 | timing epoki treningu (0 = pomiń) |
| `BENCH_REPORT` | `/tmp/bench_pc_v2_report.json` | ścieżka raportu JSON |

## Jak porównać v1 vs v2

Uruchom obie na tej samej maszynie, w podobnych warunkach:

```bash
bash tools/bench_pc.sh
bash tools/bench_pc_v2.sh
```

Różnice w g/s między wersjami wynikają z metodologii (v2 mierzy
dłużej, po rozgrzewce, z zapisem decyzji we wszystkich partiach).
Do decyzji „ile zajmie 1,6 mln gier” używaj oszacowania v2
`full PG loop`, bo uwzględnia konwersję i trening zmierzone na tej
samej maszynie.

Wynik, który warto nam wkleić: blok `SUMMARY bench_pc_v2` albo cały
plik JSON z `BENCH_REPORT`.
