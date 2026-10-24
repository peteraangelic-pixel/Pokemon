# Test integracyjny patcha 0004 — wyniki (2026-10-24, sesja Pokemon)

## Co powstało
`test_arc3_integration.py` — prawdziwy spatchowany `ToolAgent._run_python_tool`
z fałszywym callbackiem środowiska (2-poziomowa gra deterministyczna).
Bez GPU, bez LLM, bez arcengine. Uruchomienie:
`ARC3_BUNDLE_SRC=<ARC3-Inference po patchu> python3 -m pytest test_arc3_integration.py test_arc3_replay.py -q`

## Wynik: 10/10 (7 jednostkowych + 3 integracyjne)
- record -> replay w świeżej sesji: środowisko wykonało [ACTION1, ACTION2, ACTION9],
  czyli replay przejechał rozwiązany poziom bez modelu, model zdecydował tylko ACTION9;
- dywergencja hasha w kroku 1 -> replay przerwany, model przejmuje (bez wyjątku);
- kill-switch (brak ARC3_REPLAY) -> przepływ nietknięty, store pusty.

## Test znalazł 2 PRAWDZIWE bugi w okablowaniu (już naprawione w patchu)
1. `finally` w `_arc3_drive_replay` resetowało `started`, więc recorder inicjował
   się z klatki PO pierwszej paczce akcji — segment poziomu gubił pierwszą akcję
   (nagrywało się ['ACTION2'] zamiast ['ACTION1','ACTION2']).
2. `_arc3_observe` liczył `prev_level` od poziomu początkowego sesji, a po poprawce
   nr 1 — od wpisu historii po nadpisaniu licznika `consumed` (off-by-one):
   segment poziomu nigdy się nie zamykał / zamykał się źle.
Naprawa: inicjalizacja tylko raz na sesię + `old_consumed` do indeksowania
poprzedniego wpisu. Patch 0004 został zregenerowany (aplikuje się na czysty
bundle r033, kompiluje, 10/10 zielonych).

## UWAGA dla sesji ARC
Kopia patcha 0004, którą macie (commit 4a538fe), jest SPRZED tych poprawek.
Przed budową kernela podmienić `0004-solved-level-replay.patch` i
`test_arc3_integration.py` na wersje z tego commitu (repo Pokemon,
gałąź arena/a450b00f-pokemon, katalog arc-agi-3/duck-v8/).

## Czego test nadal NIE dowodzi
- zachowania na prawdziwym silniku/gatewayu (w tym: czy pin ONLY_RESET_LEVELS
  działa w trybie competition — patrz RESET-VERDICT.md),
- zysku punktowego (nadal zero pomiarów; pierwszy pomiar = smoke na Kaggle).
