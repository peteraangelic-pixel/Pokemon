# BENCH_WINDOWS.ps1 — szybki benchmark 60s na Windows 11 + PowerShell + Rust + Python
# Uruchom w PowerShell: powershell -ExecutionPolicy Bypass -File BENCH_WINDOWS.ps1
# Wymaga: Python 3.11, Rust (rustup), 32 wątki, 64GB RAM

Write-Host "=== bench_local Windows 11 — min 60s CPU warmup ===" -ForegroundColor Green

# 1. Sprawdź wersje
Write-Host "`n[1] Wersje:" -ForegroundColor Cyan
python --version
cargo --version

# 2. Venv + kaggle-environments
Write-Host "`n[2] Tworzę venv i instaluję kaggle-environments..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\pip install kaggle-environments jax[cpu] numpy

# 3. Znajdź libcg (Windows: .dll, Linux: .so)
Write-Host "`n[3] Szukam libcg..." -ForegroundColor Cyan
$lib = Get-ChildItem -Path .\.venv -Recurse -Filter "libcg*" | Select-Object -First 1
if ($null -eq $lib) {
    Write-Host "Nie znaleziono libcg, szukam w Lib/site-packages..." -ForegroundColor Red
    $lib = Get-ChildItem -Path .\.venv\Lib\site-packages\kaggle_environments -Recurse -Filter "libcg*" | Select-Object -First 1
}
Write-Host "Znaleziono: $($lib.FullName)"

# 4. Przygotuj libs/ z kopiami per wątek (engine nie jest thread-safe)
Write-Host "`n[4] Kopiuję lib per wątek (32+4)..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path libs | Out-Null
for ($i=0; $i -lt 36; $i++) {
    Copy-Item $lib.FullName "libs\libcg_$i.dll" -Force
    Copy-Item $lib.FullName "libs\libcg_$i.so" -Force
}
Copy-Item $lib.FullName "libs\libcg.dll" -Force
Copy-Item $lib.FullName "libs\libcg.so" -Force
Get-ChildItem libs | Measure-Object | ForEach-Object { Write-Host "libs: $($_.Count) plików" }

# 5. Przygotuj decki
Write-Host "`n[5] Przygotowuję decki..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path decks\trolley_pool | Out-Null
Copy-Item decks\v56_trolley.csv decks\trolley_pool\ -Force -ErrorAction SilentlyContinue
Copy-Item decks\v57_trolley34w.csv decks\trolley_pool\ -Force -ErrorAction SilentlyContinue
Copy-Item decks\shaun2024_wall.csv decks\trolley_pool\ -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path C:\tmp\mengfei | Out-Null
Copy-Item decks\top30_live\Mengfei_Li.csv C:\tmp\mengfei\ -Force -ErrorAction SilentlyContinue
Get-ChildItem decks\trolley_pool | ForEach-Object { Write-Host "trolley_pool: $($_.Name)" }

# 6. Build Rust
Write-Host "`n[6] Buduję bench_local (release, lto)..." -ForegroundColor Cyan
Set-Location rust
cargo build --release --bin bench_local --bin policy_rollout --bin gauntlet_rust
Set-Location ..

# 7. Benchmark 60s — CPU warmup
Write-Host "`n[7] Benchmark 60s — heuristic vs trolley_pool (min 60s, 32 wątki)..." -ForegroundColor Green
.\rust\target\release\bench_local.exe --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir decks/trolley_pool --min-seconds 60 --jobs 32 --lib-dir libs --card-index assets/card_index.json

Write-Host "`n[8] Benchmark 60s — vs Mengfei 300 HP wall..." -ForegroundColor Green
.\rust\target\release\bench_local.exe --mode heuristic --our-deck decks/v66_alakazam_simple.csv --opp-dir C:\tmp\mengfei --min-seconds 60 --jobs 32 --lib-dir libs

# 9. Szybki test policy iter6 (3.4M wag)
Write-Host "`n[9] Test policy_alakazam_iter6.json @600g (1.5s)..." -ForegroundColor Green
.\rust\target\release\policy_rollout.exe --lib-dir libs --card-index assets/card_index.json --weights tools/policy_alakazam_iter6.json --decks decks/trolley_pool --games 600 --jobs 32 --mode eval

Write-Host "`n=== KONIEC — wyniki powyżej to po rozgrzaniu CPU (min 60s) ===" -ForegroundColor Green
Write-Host "Jeśli chcesz pełne 1.6M, benchmark już oszacował czas bez liczenia!" -ForegroundColor Yellow
