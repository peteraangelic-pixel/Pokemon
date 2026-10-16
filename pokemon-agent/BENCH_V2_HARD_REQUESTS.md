# bench_local_v2 — 3 twarde żądania drugiej gałęzi (ARC lessons)

## 3 żądania
1. Selekcja na szumie H2H — żadnej decyzji <10-20k gier per matchup, CI nie punkt. 600g smoke ±4pp, 24k ±0.6pp.
2. Parowanie seedów — te same seedy per (our,opp,game_idx) — hash.
3. Pula ważona pool-v3 — ważona live-meta, wersjonowana, nie mieszać maszyn.

## Uruchomienie Windows 11 PowerShell
```powershell
.\rust\target\release\bench_local_v2.exe --our-deck decks/v66_alakazam_simple.csv --opp-dir decks/pool_v3 --games-per-matchup 10000 --min-seconds 60 --jobs 32 --lib-dir libs --paired true
```
Wynik: per deck winrate ±CI, overall ±CI, weighted.

10-20k per matchup = 220k gier @400 g/s = 9 min — szybki ale nie smoke.
