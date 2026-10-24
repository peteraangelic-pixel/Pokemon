# PLAN v8 — co naprawdę blokuje 45+ (weryfikacja na kodzie źródłowym Tufy, 2026-10-24)

## Korekta leaderboardu
- Nasz `public_leaderboard.csv` jest z **11.10** (Chen 62.96, Tufa 56.52). Już 14.10 w CHAT-LOG
  sami zapisaliśmy: **Tufa ma nowszą pracę na 68.91, Chen 67.49**. Lider >68 — potwierdzone.
- Próg nagród z 11.10 (NVARC3 40.97, miejsce 6) też już nieaktualny; przy liderze 68.91
  realny próg jest wyżej. Cel "45+" to dziś okolice miejsc 5-8, nie podium.

## Dlaczego stoimy na 26.25 (trzy warstwy)
1. **Operacyjnie (najważniejsze):** od 16.10 żadne zgłoszenie nie doszło. Quota GPU 30h/tydz.
   zablokowała push v7; submit API zwraca trwałe 400 (CreateCodeSubmission) — działa tylko
   ręczny "Submit to Competition" w UI; UI-submit v5 nie widnieje na liście (r062, dziś 13:48);
   log crasha v7 po 25 min (r061) nigdy nie pobrany. Kernel 26.25 ma 8 dni.
2. **Ekonomia tokenów:** zweryfikowane w bundle (r033): solver `HarnessSolver`,
   `concurrency=28`, `max_runtime_s_per_game=7920`, okno 9h, ~110 gier na żywo, serwer
   ~36,5k tok/min łącznie → ~160-180k tok/gra. Punkty = (baseline/akcje)^2, więc każda
   akcja zmarnowana na ponowne odkrywanie rozwiązanego poziomu boli podwójnie.
3. **Brak pamięci:** `_ensure_session` zeruje wiedzę przy zmianie katalogu sesji (per gra),
   a stock Duck nie pamięta rozwiązań poziomów między próbami (game-over → poziom od nowa
   liczony od zera akcji wiedzy, choć silnik liczy akcje dalej).

## Zweryfikowane mity (nie budować na nich)
- **`game_weights` NIE realokuje budżetu** — w tym kodzie wpływa tylko na agregację
  diagnostyki HTML (benchmark.py: "Weight 0 excludes a game from cross-game diagnostics").
  Dźwignia #1 z PLAN-GENIUS jest martwa jako mechanizm punktowy.
- **`n_passes` jest wymuszone =1** w komórce 14 notebooka (nadpisuje hook z komórki 12);
  benchmark gra passy jednym solverem (deepcopy gier, passes-major). Agregacja wyników
  między passami po stronie Kaggle NIE jest znana → v8 zostaje przy n_passes=1, a replay
  zarabia wewnątrz pojedynczego runu (game-over, reset sesji analizatora). Dopiero po
  smoke'u z replayem warto testować n_passes=2 osobnym slotem.
- World model szkodzi (v5 23.94 < v2 24.66) — zostaje wyłączony.

## Co robi czołówka (PUBLIC_APPROACHES)
- Franzen M2 = **47.25**: ten sam Duck + patch + **Qwen3.8-Flash-Next** (Intel AutoRound
  W4A16) + drafter MTP pod SGLang. Czyli +21 pkt głównie za szybszy/silniejszy model
  i większą liczbę tokenów na minutę.
- Warianty "Apex" dokładają: scheduler priorytetowy (10 slotów = MAXREQ), pamięć
  epizodyczną rozwiązanych poziomów, audyty anty-pętlowe. Nasz 0004 to mocniejsza
  wersja ich "episodic memory" (pełny replay akcji z weryfikacją hashy, nie tylko notatki).

## v8 = duck-v7 + 0004 (gotowe w tym katalogu)
- `arc3_replay.py` — czysta logika (store JSONL, segmentacja poziomów, plan/weryfikacja),
  testy: `test_arc3_replay.py` (7/7 zielone offline).
- `0004-solved-level-replay.patch` — dodaje moduł + okablowanie w
  `ToolAgent._run_python_tool`/`_handle_action` (nagrywanie przez `_arc3_observe`,
  odtwarzanie przez `_arc3_drive_replay` przed pierwszą decyzją modelu w sesji;
  wszystko za `ARC3_REPLAY=1`, fail-silent — wyjątek wyłącza ficzer, nie agenta).
  Patch zweryfikowany: aplikuje się na czysty bundle z r033 i kompiluje.
- Do potwierdzenia na pierwszym smoke'u (jedna linijka loga): `game_id` odtwarzane
  z nazwy pliku stanu (`{stem}_p{pass}_tool_runtime_state.json`) — poprawne wg
  solver.py:1252, ale zobaczyć w realnym artifacts_dir.

## Kolejność działań na ostatnie ~48h
1. **Odblokować zgłoszenia (godzina 0-2):** quota tygodniowa po 16.10 już się odnowiła.
   UI-submit znanej wersji (ta od 26.25) i potwierdzić nowy ref na liście. Bez tego
   dalsza praca nie ma wartości.
2. **Pobrać w końcu log crasha v7** (kernel output wersji, która padła po 25 min).
   Jeśli winny jest patch 0003, do finału idzie sam `game_weights`-less abandon
   po poprawce — nie zgadujemy.
3. **Zbudować v8** (v7 + 0004), smoke na 10 grach z variant.json (lokalnie CPU przez
   play.py do logiki; pełny smoke na Kaggle). Warunek slotu: smoke RHAE bije 29.02
   (kalibracja -2.8 pp do LB).
4. **Równolegle przez kanał ops: polowanie na model.** Pobrać metadane publicznego
   kernela Franzena (dataset_sources) — jeśli dataset z Qwen3.8-Flash-Next W4A16 jest
   publiczny, podmiana to: dołączyć dataset do kernela + w komórce 2 ustawić
   `TAAF_KAGGLE_INPUT_PATHS` tak, by slug modelu Tufy mapował na nowy snapshot
   (setup_commands rozwiązuje ścieżkę najpierw z tej mapy). Uwaga: nasz serwer to
   vLLM 0.19 z wheelhouse Tufy, Franzen używa SGLanga — zweryfikować ładowanie
   architektury na smoke'u PRZED slotem; drafter MTP opcjonalny (osobny dataset).
5. **Budżet:** maks. 2 pełne zgłoszenia do końca; każde poprzedzone smoke'iem >29.02.
   Żadnych eksperymentów "na czuja" — szum run-to-run jest ogromny (publiczne studium
   wariancji Ducka), jedna gra niczego nie dowodzi.
