# Benchmark 60s — Windows 11 PowerShell (rozgrzane CPU)

**To jest SZYBKI benchmark, ale działa min 60s żeby CPU się rozgrzało** — nie 1.5s, nie 6h.

## Instalacja (raz)

PowerShell jako Administrator:

```powershell
# Python 3.11 + Rust już masz
python --version
cargo --version

cd C:\path\to\Pokemon\pokemon-agent

# venv
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install kaggle-environments

# lib per wątek
$lib = Get-ChildItem -Path .\.venv -Recurse -Filter "libcg*" | Select-Object -First 1
Write-Host "lib: $($lib.FullName)"
New-Item -ItemType Directory -Force -Path libs | Out-Null
for ($i=0; $i -lt 36; $i++) {
    Copy-Item $lib.FullName "libs\libcg_$i.dll" -Force
    Copy-Item $lib.FullName "libs\libcg_$i.so" -Force
}
Copy-Item $lib.FullName "libs\libcg.dll" -Force
Copy-Item $lib.FullName "libs\libcg.so" -Force

# decki
New-Item -ItemType Directory -Force -Path decks\trolley_pool | Out-Null
Copy-Item decks\v56_trolley.csv, decks\v57_trolley34w.csv, decks\shaun2024_wall.csv decks\trolley_pool\ -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path C:\tmp\mengfei | Out-Null
Copy-Item decks\top30_live\Mengfei_Li.csv C:\tmp\mengfei\ -Force

# build Rust (release + lto)
cd rust
cargo build --release --bin bench_local --bin policy_rollout --bin gauntlet_rust
cd ..
```

## Benchmark 60s (rozgrzane CPU)

```powershell
# 1. Heuristic vs trolley_pool — min 60s, 32 wątki
.\rust\target\release\bench_local.exe --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --min-seconds 60 --jobs 32 --lib-dir libs --card-index assets/card_index.json

# 2. Heuristic vs Mengfei 300 HP wall — min 60s
.\rust\target\release\bench_local.exe --our-deck decks/v66_alakazam_simple.csv --opp-dir C:\tmp\mengfei --min-seconds 60 --jobs 32 --lib-dir libs

# 3. Python fallback jeśli Rust nie działa — też min 60s
.\.venv\Scripts\python tools\bench_quick_windows.py --games 0 --min-seconds 60 --workers 32 --opp-dir decks/trolley_pool

# 4. Policy iter6 z drugiej gałęzi @600g (1.5s, ale po rozgrzaniu)
.\rust\target\release\policy_rollout.exe --lib-dir libs --card-index assets/card_index.json --weights tools/policy_alakazam_iter6.json --decks decks/trolley_pool --games 600 --jobs 32 --mode eval
```

## Co zobaczysz

```
=== bench_local Rust+Rayon+FFI — min 60s to warm CPU ===
lib copies ready: 36 copies
card_index: 1431 cards
opp decks: 3 from decks/trolley_pool
[batch 1] 24000/24000 games, 62.3s elapsed, 385.2 g/s

=== RESULT (CPU warmed) ===
games=24000 wins=... winrate=0.xxx elapsed=62.3s games_per_sec=385.2
=== ESTIMATES FOR YOUR PC (32 threads, warmed) ===
600g test: 1.6s @ 385.2 g/s
40k rollout: 103.8s = 1.7 min
1.6M rollout: 4154s = 69.2 min = 1.15h
40 iters (1.6M) + trening: 6.8h
```

Czyli sam benchmark **trwa 60s** (rozgrzewka), a od razu szacuje 1.6M bez liczenia 6h.

## Dlaczego 60s a nie 1.5s?

1.5s to za mało — CPU nie wejdzie na boost, cache nie rozgrzany, wyniki zaniżone. 60s daje stabilne `games/sec`.

## Pliki

- `rust/src/bin/bench_local.rs` — teraz z `--min-seconds 60` i pętlą batchy do rozgrzania
- `BENCH_WINDOWS.ps1` — pełny skrypt PowerShell
- `tools/bench_quick_windows.py` — Python wersja min 60s
