# Synteza międzygałęziowa 25.10 (Smak × c87 × e499 × ta sesja) i plan

Wszystkie liczby zweryfikowane przeze mnie na surowych artefaktach w tej sesji.
Stan: 25.10 wieczór. **Nic nie jest wysłane; obowiązuje zasada GO usera.**

## 1. Wyniki, od których wszystko zależy

- Najlepszy COMPLETE: **duck v3 = 26,25**. c45 (#57629847): **COMPLETE 0.00**
  (r083) — interaktywny smoke był zdrowy (26,78, 32 poziomy), zginął rerun.
- Przyczyna 0.00 (podejrzany nr 1, mechanizm w kodzie): komórka solvera —
  `if TRUE_SUBMISSION: bm.solver.concurrency = 120` przy serwerze MAXREQ=10.
  Smoke szedł 10 gier na 10 slotów; rerun cisnął ~110 gier przez 10 slotów.
  Komentarze patcha dokumentują patologię („refused connection… wait it out",
  „fourteenth of the rate"). Alternatywy (crash SGLanga na starcie, inne
  zachowanie gier z gatewaya) rozstrzyga tylko log reruna — dostępny wyłącznie
  w przeglądarce usera (Submissions → #57629847 → log). Prośba o niego stoi.
- `submission.parquet` (2648 B) to stub — r019 miał identyczny i wziął 27,21;
  scoring czyta wyniki reruna, nie parquet.

## 2. Spór o „martwy patch" — ZAMKNIĘTY (v10 §1 i wnioski sesji Smak są błędne)

- Komórka patcha 498 799 znaków jest bajt-identyczna w v7/c45/v9 (sha `6fdcd1ae…`).
- Surowa ekstrakcja z JSON-a + `git apply` → `corrupt patch at line 10086/7` (brak
  końcowego `\n`). **Zreplikowałem test c87**: pełny potok IPythona (`run_cell`)
  dopisuje `\n` przy `%%writefile` — plik z notebooka aplikuje się czysto.
- Dowód produkcyjny: log kernela c45 z Kaggle — „harness patch applied
  successfully" + 10 gier (r076). Czyli v9 też by ruszyło; status jego kernela
  v1 jest po prostu nieściągnięty (op `kernel_status` w ops pada — osobny bug).
- Wniosek praktyczny: nie wydajemy slotu na „naprawę" patcha, który działa.
  Z v10 bierzemy mechanizmy (commit, chunkowanie+sha na przyszłość), nie diagnozę.
- Uwaga na przyszłość: `verify_offline.py` (pakiet v9) dawał fałszywy pass, bo
  przy ekstrakcji sam dopisywał `\n`. Weryfikatory mają odtwarzać runtime
  1:1 albo oznaczać normalizację.

## 3. Pakiet v10 (e499c604) — ocena końcowa

- `commit(plan)`: prawdziwy i dobrze bramkowany; testy **12/12** (potwierdzone
  u mnie na dwóch niezależnych drzewach), bench 3,7→148,6 ms/akcję. To jest T2
  zrobione bezpiecznie: batchowanie z weryfikacją zamiast ślepego (bramka dla
  profilu deep = poziomy, nie a/call — odwrotna korelacja w r019).
- Ale: przebudowany patch 660 KB **nie aplikuje się na bundle** (Makefile:40,
  README:1), `PROFILE="plan"` jest domyślny (wbrew ich własnemu planowi),
  a notebook dziedziczy `concurrency=120`. As-is = ryzyko spalenia slotu.
- Dlatego **wariant B (propozycja c87)**: minimalny port na c45 — zrealizowany
  jako pakiet `duck-v11` w tym katalogu (verify: ALL CHECKS PASSED).

## 4. Stan wiedzy wspólny (przyjęty bez rewizji)

- Ekonomia r019 przeliczona z surowych danych: 2065 akcji / 474 wywołania /
  a/call 4,357 (ważone) i 5,204 (średnia) / 841 tok/akcję / pula 173,7k tok/grę.
  Liczby „1,13" nie ma. („21/32 ≤115" DeepSeeka nie odtwarza się: 32/32.)
- Sufit ruchów ~29,0; +1 poziom/grę ≈ 44; próg nagród 49,85 (LB 24.10).
- Roster prywatny może nie być 25 publicznymi grami → playbook i triage
  budżetowy mogą być warte zero (zgodnie: c87, v10 §6, ta sesja).
- `PERSISTENT_FUNCTIONS_SCOPE='game'` jest akceptowane — dźwignia #4 żyje.
- `v9_metrics` miesza średnią z proporcji z agregatowymi baseline'ami —
  bramek nie stawiać na jego a/call bez ujednolicenia (agregat suma/suma).

## 5. Plan slotów (do decyzji usera; quota ~30 h/tyg → realnie ~2 sloty)

1. **(opcjonalnie, 0 kosztu) log reruna z przeglądarki** → potwierdza §1.
2. **Slot A — v11 `PLAN_COMMIT="0"`** (sam fix concurrency): pytanie, czy szybka
   linia w ogóle punktuje w rerunie. Bramka smoke > 29,02 i tak potrzebna,
   ale pamiętamy: smoke nie testuje ścieżki TRUE_SUBMISSION — prawdziwy
   werdykt da dopiero submit. (Uwaga: to jest ten sam dylemat co przy c45.)
3. **Slot B — v11 `PLAN_COMMIT="1"`**: pytanie, czy `commit()` jest wołany
   z `expect` i czy ratuje poziomy. Kill: brak wywołań albo mniej poziomów
   niż slot A.
- `deep`/`wide` tylko jako osobne pomiary, nigdy łączone z `plan`.
- Finalista do 31.10–1.11 jako publiczny notebook (inaczej nagroda przepada).

Kolejność A/B można zamienić, jeśli user woli od razu testować `commit()`
(jeden slot mniej, słabsza atrybucja). Rekomendacja: A potem B.
