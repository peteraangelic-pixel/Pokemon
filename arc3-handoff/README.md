# ARC-AGI-3 (ARC Prize 2026) — wszystko, co ustaliłem o ich gałęzi i konkursie

Komplet wyników audytu gałęzi `peteraangelic-pixel/Smak-Domu-Konkurs`
@ `arena/5ed750ef-smak-domu-konkurs`, wykonanego **24.10.2026**. Nic tu nie jest
zgadywane: każda liczba ma źródło (plik i linie w ich repo, log z runa, albo mój pomiar
z podaną metodą), a każdy patch jest zweryfikowany przez `git apply` na prawdziwym drzewie.

Ten katalog jest **samowystarczalny dla innej gałęzi / innej sesji**: są tu wnioski, dowody,
kod, testy i narzędzia do odtworzenia wszystkiego od zera (łącznie z instrukcją pobrania
ich drzewa, bo piaskownica nie ma `git clone` do tego repo).

---

## ⏱ STAN ZWERYFIKOWANY NA ŻYWO — 24.10.2026 wieczorem (źródło: oficjalna strona Kaggle)

Pobrane dziś bezpośrednio z `kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview`
i `/leaderboard`. **To nadpisuje wszystkie daty i wyniki z ich notatek (10–16.10) oraz moje
wcześniejsze szacunki w tym katalogu.**

### 1. Deadline: są DWIE różne daty i łatwo je pomylić

| data | co to jest | za ile dni (od 24.10) |
|---|---|---|
| **26 X 2026** | **Entry Deadline** (akceptacja regulaminu, żeby w ogóle móc grać) **+ Team Merger Deadline** (ostatni dzień na łączenie zespołów) | **2 dni** |
| **2 XI 2026** ← właściwy | **Final Submission Deadline** — termin wysłania ostatecznej wersji | **9 dni** |
| 4 XII 2026 | ogłoszenie wyników | — |

**To jest źródło pomyłki „zostały 2 dni”.** Licznik na samej stronie Kaggle pokazuje dziś
„Close — 9 days to go”, a w timeline 26 X jest opisany wyłącznie jako *Entry Deadline* /
*Team Merger Deadline*, nie jako termin submisji. Wszystkie deadline'y to 11:59 PM UTC.

Konsekwencje praktyczne:
- **Entry Deadline nas nie dotyczy** — mamy już 6 punktowanych submisji, więc regulamin jest
  zaakceptowany i warunek spełniony. Do 26 X nie trzeba nic robić.
- **Team Merger Deadline 26 X dotyczy nas TYLKO, jeśli chcemy połączyć siły z innym zespołem.**
  To jedyna rzecz realnie pilna w ciągu 2 dni — decyzja organizacyjna, nie techniczna.
- **Na pracę techniczną jest 9 dni, nie 2.** To zmienia plan: mieści się kilka iteracji
  „jeden lever na submisję”, a nie jedna.

### 2. Live leaderboard (24.10) — i dlaczego „45+” to za mało na nagrodę

| # | zespół | score | submisje |
|---|---|---|---|
| 1 | Tufa Labs | **68.91** | 17 |
| 2 | Yi-Chia Chen | **68.21** | 40 |
| 3 | Team Turducken | 56.02 | 208 |
| 4 | mtg | 50.37 | 78 |
| **5** | **the last dance** | **49.85** ← ostatnie miejsce z pieniędzmi | 90 |
| 6 | Grigoriy Zatravkin | 47.19 | 74 |
| 7 | 復活の混テキスト | 46.82 | 94 |
| 8 | NVARC3 | 45.90 | 45 |
| 9 | artificialagencylab.com | 45.41 | 61 |
| 10 | Majkel1337 | 45.03 | 26 |
| 11 | Vineeth Sai Varikuntla | 40.98 | 72 |
| 15 | **Daniel Franzen (autor Ducka)** | **38.85** | 104 |

**Nagrody pieniężne są TYLKO za top-5** ($75 000: 40k / 15k / 10k / 5k / 5k). Próg to dziś
**49.85**, nie 45 i nie 40.97. Dodatkowo $700 000 bonusu wyłącznie za **100 %** score.

Trzy wnioski, które bolą:
1. **„45+” daje miejsca 8–11 = zero pieniędzy.** Cel trzeba przesunąć na **~50**, czyli między
   moje „+1 poziom na grę” (44.8) a „+2 poziomy” (64.5) — realnie **+1.2 poziomu na grę**.
2. **Ich najlepszy wynik 26.25 → do 5. miejsca brakuje ~23.6 pkt.** To nie jest luka do
   zasypania tuningiem env; to luka klasy „inny harness / inny model”.
3. **Sam autor Ducka (Franzen, 104 submisje) ma 38.85 = 15. miejsce, bez nagrody.** Stockowy
   Duck nie dochodzi do strefy płatnej. Kopiowanie Ducka to sufit ~39, nie ~50.

### 3. Trzy ograniczenia z oficjalnej strony, o których trzeba wiedzieć

- **Publiczny LB liczy ~50 % danych testowych; wynik końcowy jest z DRUGICH 50 %**, więc końcowa
  kolejność może się różnić. Gonienie konkretnej liczby z publicznego LB jest częściowo daremne —
  liczy się odporność na nieznane gry, nie dopasowanie do widocznych.
- **„Uczestnicy uprawnieni do nagrody zostaną USUNIĘCI z konkursu, jeśli nie open-source'ują
  swoich rozwiązań.”** Ich kernele mają `is_private: true`. Żeby nagroda była realna, notebook musi
  być publiczny na permisywnej licencji (CC0 / MIT-0). Wejście do top-5 z prywatnym kernelem
  = utrata nagrody.
- Limit notebooka: **9 h** (CPU i GPU), **internet wyłączony**, zewnętrzne dane i wytrenowane
  modele dozwolone jeśli darmowe i publiczne. Dostępne też **RTX 6000** (`g4-standard-48`),
  wyłącznie dla notebooków tego konkursu.

---

## Od czego zacząć (3 minuty)

1. **`PATCH-0004-I-SEARCH.md`** — najważniejsze: **run-killer** w ich linii `duck-v7`
   (patch 0003 nie nakłada się po patchu Franzena, a cell 9 ma `check=True` → notebook umiera
   przed pobraniem wag), dwa bugi czyniące `v7-abandon` martwym kodem, oraz co dostarczam
   w zamian. Tam jest też gotowe wpięcie do notebooka i rekomendowane env.
2. **`FAKTY-I-POMIARY.md`** — kompendium: silnik, **punktacja z dowodem**, 25 gier, ich
   konfiguracja, serwer, pomiary runów, stan Kaggle, kolejka ops, pułapki narzędziowe, mapa repo.
3. **`FAKTY-I-POMIARY.md` §1bis** — jak naprawdę wyglądają gry click-owe (skan 4096
   współrzędnych), odkrycie wewnętrznego API silnika `_get_valid_actions()` wraz z
   **ostrzeżeniem, że nie wolno go używać w submisji**, i legalny zamiennik na publicznym
   API (kalibracja po efekcie), który odblokował ft09.
4. **`DIAGNOZA-45plus.md`** — dlaczego nie ma 45+ punktów: wypukłość punktacji w głębokości,
   arytmetyka budżetu tokenów, ranking dźwigni, plan na 9 dni, lista „czego nie robić".
   Na końcu sekcja *AKTUALIZACJA 24.10* z trzema poprawkami do tej diagnozy.
5. **`WERYFIKACJA-INNYCH-GALEZI.md`** — CZWARTY dokument: sprawdzenie w **kodzie** ustaleń
   czterech innych sesji (`a450b00f`, `5ed750ef`, dwie gałęzie Gemma). Trzy twierdzenia
   **potwierdzone co do linii** (bug `-f` w `ops.py:459`, z pełnym łańcuchem wywołań
   L459→L463→L136→L140 w ich blobie) i **trzy błędne**, które kosztowałyby slot, gdyby je
   wdrożyć: limit historii to `150` a nie `30`; kompakcja/sumaryzacja **istnieje** i jest
   wyłączona jedną zmienną `ARC3_MEMORY_SECTIONS=off`; klucz rozumowania jest już ustawiony
   na `reasoning_content`. Plus niezależne potwierdzenie mojego twierdzenia o capie
   (17/27 poziomów r019 na 115), kolizja numeracji patchy `0004-*` między gałęziami i
   sprostowanie progu nagród (lider **68.91**, nie 62.96; nagrody są za miejsca, nie za próg).
6. **`EKONOMIA-TOKENOW.md`** — PIĄTY dokument i najważniejszy nowy kierunek: ile kosztuje
   jedna akcja na obu liniach (**841** tok/akcję na szybkiej r019 vs **444** na wolnej r050),
   model wyniku LB jako funkcji ekonomii tokenów (`tools/token_economy_model.py`), kalibracja
   sufitu wobec zmierzonego 26.25, oraz odpowiedź na pytanie **ile tok/akcję trzeba, żeby dojść
   do progu nagród 49.85**. Zawiera: dowód, że cap `LOCAL_ANALYZER_MAX_OUTPUT=12k` jest JUŻ
   w ich cell 9 (więc 12 % puli jest już wydane), potwierdzenie fixa `-f` w produkcji
   (r069, `rc=0`, ref 57607527), i triage które gry opłaca się atakować przy powiększonym
   budżecie akcji (sb26, r11l, tn36, sc25, su15, lp85).
7. **`OCENA-DEEPSEEK-V9.md`** — weryfikacja pakietu v9 i analizy „LEPSZA DROGA" w **ich
   kodzie i logach**. Najpilniejsze: submisja **57607527 wróciła jako ERROR** (r071), więc
   fix `-f` odblokował *wysłanie*, ale kernel padł — **nowego pomiaru nie ma od 16.10**, a linia
   szybka nigdy nie dojechała do COMPLETE. Plus: run-killer c45 był prawdziwy, ale naprawiony
   25.10 10:45 i źle zaadresowany (lista `jeroencottaar/driessmit1` należy do `duck-original` v5);
   **sprzeczność 1.13 vs 5.2 akcji/wywołanie** w ich własnej analizie (rozstrzyga ją komórka
   pomiarowa v9); oficjalna metodologia RHAE potwierdza moją formułę **i wykrywa mój błąd** —
   warunek capu to `a ≤ 0.9325·b`, nie `1.0724·b`; oraz argument o replayu, który **obala mój
   własny playbook** (3.18 to wynik symulatora lokalnego, nie LB).
8. **`OCENA-V10.md`** — weryfikacja pakietu `arc-v10` z sesji `e499c604` (17 plików, 2.26 MB).
   Ich główne znalezisko („v9 i v7 w ogóle by nie ruszyły, patch urwany w środku hunka") jest
   **OBALONE dowodem produkcyjnym**: c45 ma `KernelWorkerStatus.COMPLETE` (r075) i zostawił
   `.per_game_cards.pkl` + logi **10 gier** (r076). Mechanizm zmierzony na IPython 9.17.1:
   `%%writefile` w pełnym potoku **dopisuje** końcową nową linię, a `git apply --check` na surowym
   `source` z JSON-a jej nie ma — cały błąd to jedna nowa linia, nie urwany hunk. Do tego w patchu
   jest **0 plików spoza `ARC3-Inference/`**, a cell 9 aplikuje z `--include=ARC3-Inference/*`,
   więc „brakujące `viewer/*`" jest bez znaczenia przez konstrukcję. **Do wzięcia:** `commit(plan)`
   z weryfikacją `expect` per krok (najlepsza odpowiedź na odwrotną korelację `a/call`↔score),
   `ARC3_ESCALATE_ACTIONS` (mocniejsze niż mój `RESET_LEVEL`) i chunkowanie patcha z sha256.
   Niezależne potwierdzenie mojej korekty o rosterze: „playbook i triage budżetu warte zero".
9. **`POROWNANIE-V11.md`** — v11 (`arc3-duck-v11-plan-safe`, Codex + certyfikacja Arena)
   kontra moja wersja agenta. **Zweryfikowana w źródle przyczyna 0.00**: c45 cell 21 ma
   `concurrency = 120` na ścieżce `TRUE_SUBMISSION` przy `MAXREQ=10` (cell 17) i
   `ARC3_MAX_ACTIVE_STREAMS: 10` (cell 9), podczas gdy ścieżka SMOKE ma `concurrency = 10` —
   dlatego smoke przechodził, a rerun dał **0.00** (ref 57629847). Bramka `ARC3_SMOKE_OK` jest
   **strukturalnie ślepa** na tę klasę buga; podaję 3-liniowy preflight spójności warstw.
   **Mój własny błąd:** `FAKTY` L629/L636/L638 mają wszystkie trzy liczby osiem linii od siebie
   i nigdy ich nie porównałem, a mój `notebook/arc3-duck-fixed.ipynb` ma ten sam `concurrency=120`
   — więc też dałby 0.00. Do tego `FAKTY` L677 proponował podniesienie `MAXREQ` jako lever #3,
   czyli dźwignię **odwrotną** do właściwej. Tabela co v11 ma a ja nie, co ja mam a v11 nie,
   i co moje już w v11 jest (`level-token-cap 45k`, roster probe). Rekomendacja slotu:
   **`PROFILE="c45"`**, nie `plan` — bo nigdy nie było czystego pomiaru szybkiej linii,
   kalibracja smoke→LB była mierzona na innej konfiguracji, a nowa warstwa potrafi kosztować
   (ich własne v6 23.94 < v2 24.66).

10. **`EKONOMIA-TOKENOW.md` §11** — **CZYTAJ PRZED OTWARCIEM LEADERBOARDA.** Oczekiwany wynik
   `PROFILE=c45` po naprawie `concurrency`: ~~26 – 31 pkt, główny szacunek 31.18~~ ❌ **OBALONE
   przez pomiar — aktualna liczba to 24–29, punktowo ~26.8, patrz wpis 11 niżej**. Wyprowadzone
   z trzech kotwic (r019 27.21 / ich LB 26.25 / sufit modelu 31.70) i **zmierzonego** wycieku
   tokenów (`FAKTY` L697-699: agregat 35 %, tn36 86 %, ls20 91 %). Naprawa usuwa strukturalne
   zero, nie dodaje zdolności ⇒ ścieżka submisji = ścieżka smoke = zmierzona. Dwa twierdzenia
   do sprawdzenia zamiast zgadywania: **kap 45k nie robi nic poniżej 25.7 % puli na skazany
   poziom**, i ~~sam kap jest wart ~+4.9 pkt~~ ❌ **kap jest zmierzony UJEMNIE: −0.43 wobec r019
   i −2.24 wobec v3** (wpis 11). **Werdykt: naprawa warta slota, ale ona ODZYSKUJE ~26.8, nie
   podnosi wynik; luka do progu 50.37 zostaje ~21–24 pkt.**
   Plus §12: dwie domknięte niewiadome — walidator `ARC3_PERSISTENT_FUNCTIONS_SCOPE` (moja
   dźwignia 4 **martwa w połowie**, `run` nie istnieje i degraduje **cicho**) oraz leaderboard
   chunk 1/2 (miejsca 29–49, 4912 wpisów, pole ~0.075 pkt/miejsce).

11. **`OCENA-CODEX-7Z.md`** — **NAJNOWSZE I NAJWAŻNIEJSZE (27.10).** Ocena archiwum
   `arc-agi-3.7z` (522 pliki, 46 MB) z osiągnięciami Codex, i **czwarta korekta mojego własnego
   błędu**: surowy smoke c45 (`r085/output-pick/benchmark.json`) daje **MEAN 26.78 / 32 poziomy**,
   czyli **mój kap 45k jest zmierzony UJEMNIE** (−0.43 wobec r019, −2.24 wobec v3), a nie +4.93
   jak oszacowałem w §11.2. Błąd: statystyka `w` o poziomach **skazanych** zastosowana do
   **wszystkich** poziomów; `su15` stracił −43.1 pkt na poziomie, który inaczej by się ukończył.
   **ALL-CLEAR:** `ARC3_LEVEL_TOKEN_CAP=0` znaczy *wyłączone*, nie „zero tokenów" — ale ponieważ
   `enabled = cap > 0`, wyłączenie capa **wyłącza cały patch 0004** wraz z `RESET_LEVEL`.
   Plus: ich `sweep2.py` na PC (16 workerów, cap 90 s) = 14 poziomów vs moje 16, **unia 17**,
   jedyna nowa gra `m0r0`; cap 90 s kosztował `ar25`/`s5i5`/`tu93` — **maszyna nie była
   ograniczeniem, był nim cap**. Roster probe **NIE** rozstrzygnął rostru (odpalił się w smoke
   na 10 grach publicznych, nie na gatewayu). Sprzęt potwierdzony: **5950X 16C/32T + 64 GB RAM**
   ⇒ mój bloker `re86` (17.9 GB) mieści się z 3.5× zapasem.
   **Trzy wnioski w §8: (1) wyłączyć kap, (2) naprawa concurrency odzyskuje ~26.8 a nie podnosi,
   (3) podnieść cap w `sweep2.py` do 300–600 s i powtórzyć — 0 GPU, 0 tokenów, 0 slotów.**

14. **`OPINIE-3-GALEZI-O-V13.md`** — ❗**NAJNOWSZE (30.10 ~07:20 UTC). TRZY GAŁĘZIE, JEDEN WNIOSEK.**
   Przeczytane read-only: `Gemma-konkurs@arena/c4eeb067` (HEAD `cded50d0`, 30.10 07:09),
   `Smak-Domu-Konkurs@arena/5ed750ef` (HEAD `9e59a473`, 30.10 07:05), `Pokemon@arena/7911f950`
   (HEAD `3269393d`, 29.10 17:04).
   **KONWERGENCJA: 50+ jest funkcją PRZEPUSTOWOŚCI (akcji na grę), nie „mądrzejszego modelu"
   i nie playbooka.** Trzy niezależne modele dają **ten sam próg ~300 akcji/grę** (obecnie 212,6):
   7911f950 „podwojenie akcji na decyzję → sufit **51,3**" · Gemma „**300 akcji → 59,5**" ·
   mój `token_economy_model.py` „500 tok/akcję → 350 akcji → **54,12**".
   ✅ **Gemma NIEZALEŻNIE ode mnie**: *„dwie z trzech dźwigni patcha 0006 są w konfiguracji
   submisyjnej **martwe**"* (trzecia konwergencja tej sesji po `EXPOSE_UNDO` i `CAP=0`).
   ✅ **Gemma policzyła wartość playbooka — liczba, której brakowało**: 14/14 poziomów i
   **184/184 hashy** odtworzone na prawdziwym silniku (także seed 1/2/7/42) = **72,61 pkt
   sumarycznie = średnio 2,90 na 25 grach publicznych**. *„Na rosterze prywatnym, jeśli nie ma
   w nim gier publicznych — **0**. Widełki „35–50+" z README **nie mają pokrycia w artefaktach**."*
   **Nawet w najkorzystniejszym wariancie (110 klonów) średnia po 110 wpisach jest TA SAMA 2,90.**
   ❌ **OBALONE: twierdzenie Smaka „roster = 110 round-robin klonów 25 gier, POTWIERDZONE W KODZIE
   FRAMEWORKU (nie hipoteza!)"**. Sprawdziłem cytowane źródło: `taaf/competition_arcade.py`
   (blob `1293db68`), docstring L1-8 dosłownie: *„**Local** competition-mode ARC-AGI Arcade
   **simulator** … The **real Kaggle submission path** talks to a **gateway-backed Arcade** …
   hidden baselines, and no repeated game IDs … This module starts the same REST app **on localhost
   against the bundled offline games** so those failures can be reproduced **before submission**."*
   `official_110()` klonuje 25 gier, żeby **lokalny symulator** miał **kształt** prawdziwej karty
   (L151: *„submission-**shaped** benchmark"*, L67: klony „on the **simulator side**").
   **To ta sama klasa błędu co `SCOPE=run` i `concurrency=120`: czytanie NAZWY zamiast docstringu.**
   ⇒ **GO#1 Smaka (v13-MEGA na slot 30.10, „sufit 45-55") ma przesłankę, która nie istnieje.**
   ✅ **ROZSTRZYGNIĘCIE SPORU O ROSTER JEST DARMOWE**: `roster_probe` w logu **rerunu ref 57737623**
   (v11 już leciał i dał 23.89). W `r085` probe odpalił się w **smoke** na bundlu offline, więc
   pokazał gry publiczne. **Log rerunu jest tylko w przeglądarce właściciela konta** → do pobrania
   przez usera: Kaggle → Submissions → 57737623 → Output. Zero kosztu, zero slotu.
   ❌ **OBALONE: cap per-poziom = 1.0** (7911f950). Poprawnie **1.15/115** — `docs.arcprize.org/
   methodology`, `taaf/game.py::_compute_final_score` (mirror `EnvironmentScoreCalculator` v0.9.8)
   i regresja Gemmy **32/32** na prawdziwych `final_score`. **Ich walidacja nie rozróżnia 1.0 od
   1.15**: we wszystkich czterech wierszach ich tabeli wiąże **cap UKOŃCZENIA** (`100·Σw_uK/Σw_all`)
   — su15 6/45=13,33 · ka59 6/28=21,43 · g50t 3/28=10,71 · s5i5 6/36=**16,67** (ich formuła dała
   15,67, harness 16,67). Zweryfikowali formułę na danych, które nie rozróżniają kandydatów.
   **Ich WNIOSEK („nie ma sensu być szybszym niż człowiek") jest prawdziwy, ale z INNEGO powodu**:
   nie cap 1.0, tylko **cap ukończenia** wiąże niemal zawsze. Gemma mierzy tę resztkę jako **+3,0 pkt**.
   ⚠️ **TO ODWRACA CZĘŚĆ MOJEJ REKOMENDACJI**: w `OCENA-V13-MEGA.md` §7 dałem `PLAN_COMMIT="0"` na
   najbliższy slot. Skoro bottleneck to akcje/decyzję, **`commit(plan)` jest JEDYNĄ dźwignią, która
   w niego celuje** (plan 20 akcji ≈ 3 s wobec ~14,4 s na pojedynczy ruch = ~5× tańsza akcja;
   12/12 testów na spatchowanym drzewie). Przeciw: niezmierzone na Kaggle, ich v6 23.94 < v2 24.66,
   jeden slot nie rozstrzygnie przy σ≈2,5–3,9 → **dlatego DWA sloty na tę samą konfigurację**.
   ⚠️ **1,00 akcji/decyzję dotyczy STAREJ linii** (r013/r015/r018). Nasza szybka linia (r019):
   **4,357** ważone / 5,204 średnia, 841,2 tok/akcję. Kierunek i wniosek zostają.
   ❌ **27B zmierzone i SKREŚLONE**: slot B = **1,18**, v14-27b-long smoke = **0,27**; mediana
   116 akcji przy **47,0 s/akcję** (8B: 12,9 s/akcję), 8/10 gier z zerem poziomów. *„Większy model
   nie był za głupi — **był za wolny**."* Sygnał zapętlania: cn04 130 ruchów z **6 różnymi** akcjami.
   **PLAN NA 4 SLOTY (§6): 30.10 `PLAN_COMMIT="1"` + `CAP=0` + `WINPATH="0"` + `DEAD_SKIP="0"` +
   `EXPOSE_UNDO="on"` + conc 10 · 31.10 TO SAMO ponownie (drugi draw) · 1.11 lepsza z dwóch albo
   kontrola `PLAN_COMMIT="0"` · 2.11 select best.** Przed 30.10 trzy rzeczy darmowe: log rerunu
   (roster), `analyze_run.py` na `benchmark.json` rerunu (bramka: mediana akcji <300 → przepustowość),
   PC sweep 600 s **tylko jeśli roster wyjdzie na klonach**.
   **Cel pozostaje ~29–30, srebro ≈32.33. `PLAN_COMMIT="1"` to jedyna dźwignia z realną szansą
   na ~35+.**

15. **`OCENA-V13-1-TRZY-RECENZJE.md`** — ❗**NAJNOWSZE (30.10 ~07:35 UTC). v13.1 powstał ~9 minut
   po mojej recenzji i uwzględnia ją wprost** (commit `cbefdd4e`: *„korekty po 3 recenzjach
   (Gemma/**c87**/Smak)"*; README v13.1: *„`SERVER_STARTUP_TIMEOUT` (12 min) **celowo bez zmian —
   recenzja c87 domknęła, że nie przerywa biegu**"*). Widełki oczekiwań zmienione **35–50+ → 28–38**.
   **FAKT 1 — gałąź Smak ZAPRZECZA SAMEJ SOBIE o roster, 5 dni apart, na tym samym pliku.**
   Ich `duck-c45/OCENA-V9-LEPSZA-DROGA.md` (25.10 12:25), tabela „wszystko potwierdzone":
   *„Replay/×4.4 pamięć = **0** w prawdziwym scorecardzie (brak powtórzonych game_id;
   **`official_110` = lokalny symulator**) · **zgodne z `competition_arcade.py`** · ✅
   (**sonda rosteru w c45 i tak dowozi dane za darmo — koszt 0**)"*. A 30.10 ta sama gałąź:
   *„roster **POTWIERDZONY W KODZIE (nie hipoteza!)**"* i w `OCENA-ARENA-V13-1.md` pkt 4 nadal
   *„~4.4 klony … mnożnik replay zrobiony właściwie"*. **Czytali ten sam plik co ja i 25.10
   wyciągnęli TEN SAM wniosek co ja.** Gemma znalazła ten cytat niezależnie (wiersz 12) i pisze:
   *„v13.1 naprawia dźwignię, o której **sami piszą, że prawdopodobnie nie zadziała**"*.
   **FAKT 2 — `PLAN_COMMIT="1"` jest TYLKO OFEROWANE MODELOWI, NIE WYMUSZANE** (7911f950,
   `V13-1-VERIFICATION.md` §3): patch **tylko dopisuje narzędzie do opisu**
   (`_PYTHON_TOOL_DESCRIPTION += " Also available: commit(plan)…"`, `prompt += PLAN_COMMIT_TOOL_ADDENDUM`),
   *„Nie ma żadnego wymuszenia. Model prawdopodobnie będzie wykonywać jedną akcję na turę.
   Eskalacja włącza się dopiero po `ESCALATE_ACTIONS = 60` … czyli **po 60 zmarnowanych decyzjach**"*.
   ❌ **ÓSMA KOREKTA MOJEGO WNIOSKU, pierwsza dotycząca rekomendacji wydanej wczoraj**: policzyłem
   wartość z MOŻLIWOŚCI mechanizmu, nie z tego czy cokolwiek zmusza model do użycia go. To ten sam
   błąd co `SCOPE=run`, `EXPOSE_UNDO`, `official_110` — reguła „**narzędzie zareklamowane w prompt
   ≠ narzędzie użyte**". Bez wymuszenia rozkład to najczęściej ~0, czasem **ujemne** (dodatkowa rada
   w prompt = −2.3/−3.4 zmierzone). **Poprawka tania: `ARC3_ESCALATE_ACTIONS` 60 → 8–12**
   (⚠️ najpierw sprawdzić, czy to env — nie zgaduję).
   ✅ **Naprawa v13.1 jest PRAWDZIWA — trzy recenzje zgodnie.** Gemma **end-to-end na prawdziwym
   silniku** (`winpath_sim.py`, 198 ln, importuje ich moduł bez zmian): poziom z wpisu 1 odtworzony
   we wpisie 2 **za 0 tokenów** (18/18, 3/3, 15/15, 13/13 na tu93/vc33/m0r0/cn04); `DEAD_SKIP`
   odpala od 4. wpisu. 7911f950: `test_winpath` **7/7** ze stubem, `grid_key` **identyczny** w obu
   plikach, przełączniki **naprawdę eksportowane**. Smak: diff **chirurgiczny** (kom. 2+11),
   `playbook.json` **bajt-identyczny** ⇒ 14/14 na silniku dalej ważne.
   **WARTOŚĆ JEST WARUNKOWA — i warunek jest nierozstrzygnięty.** Gemma: **+5…+15 pkt JEŚLI roster
   cykliczny, 0 jeśli nie** (okno 2 945 s/wpis, ~226 akcji; kopia odtwarza poziomy 1..d za 0 tokenów
   i **cały budżet zostawia na poziom d+1**; z r085 `ls20`: 414 z 427 akcji na poziomy 1–3 ⇒
   przejście 3→4 na grze 7-poziomowej = **+16,4 pkt na grze**). 7911f950: **+2,3 na 10 grach,
   ~+0,6 na rosterze 110**. **Uzgodnienie: oba poprawne przy różnych rosterach** — 72,61/25 = 2,90
   (cykliczny) vs 72,61/110 = **0,66** (prywatny). Gemma znalazła mechanizm: `competition_arcade.py:100`
   → **`source_infos[i % 25]`**. Jej epistemika jest wzorem: *„to cytat z dokumentacji gałęzi, nie
   mój pomiar — dlatego nazywam to **warunkiem, nie faktem**"*.
   **7911f950 znalazł realną stratę:** `sp80` — ich niezależny solver ma **4 akcje**, playbook v13.1
   **28** (7× dłuższa, przy kwadratowej karze RHAE to strata); `vc33` różnica 1 piksela;
   `cd82`/`lp85` **identyczne**. Rekomendacja: przegenerować playbook biorąc **najkrótszą** ścieżkę
   ze wszystkich źródeł. ⚠️ Ale przy capie ukończenia to **kosmetyka** (~3 pkt łącznie), nie dźwignia.
   **DROGA DO 50+ ISTNIEJE I JEST PRZYJĘTA przez gałąź Smak** (`OCENA-V9-LEPSZA-DROGA.md`, „Strategiczny
   PIVOT"): **T3 = world-model + planer (paper01, MIT)** — agent-koder pisze wykonywalny model gry,
   weryfikacja na przejściach, **BFS szuka ciągu akcji W MODELU**, wykonanie + porównanie klatek.
   *„**Jedna decyzja LLM kupuje dziesiątki–setki akcji**."* Zamyka dokładnie nasz ogon: **ls20
   1/7→7/7, tn36 1/7→7/7, g50t 2/7→7/7, ka59 3/7→7/7**; routing per gra: WM wygrywa 7/10, nasza
   pętla 3/10, **unia = 69.69**. Ich weryfikacja paper01 co do 0,01: **WM GPT-5.5 = 56.81** na
   naszych 10 grach, pełny set 58.12%, 15/25 gier 100%. **T2 (tanie ~T3) = plan-then-execute** —
   ta sama metryka (akcje/decyzję) za 1 slot.
   ⚠️ **ALE POMIAR PRZECIWKO: WM GPT-5.4 = 24.67 < nasze 27,21.** Czyli w tym samym scaffoldzie
   słabszy model dał mniej niż nasza pętla ⇒ **56.81 to w dużej części zasługa GPT-5.5, nie
   architektury**. Qwen3.8-Flash-Next W4A16 jest znacznie słabszy niż GPT-5.4. Ich własne
   *„NIEZMIERZONE na open-weights"* jest uczciwe — i nie do zweryfikowania w 4 slotach przy σ≈2,5–3,9.
   **PLAN POPRAWIONY (§5): 30.10 = v13.1 z `PLAN_COMMIT="0"` · `CAP=0` · `WINPATH="1"` ·
   `DEAD_SKIP="1"` · `EXPOSE_UNDO="on"` · conc 10 · `roster_probe` ODZYSKANY — jedno zadanie:
   ROZSTRZYGNĄĆ ROSTER.** 31.10 = rozgałęzienie **pomiarem**: cykliczny → to samo ponownie
   (pamięć warta +5…15); prywatny → `WINPATH="0"` + `ESCALATE_ACTIONS` 8–12. 1.11 = najlepsza lub
   kontrola. 2.11 = select best. **Trzy recenzje zbiegają na to samo co ja** — Gemma: *„jedyna
   sensowna rekomendacja na slot 30.10 to **zabrać ze sobą sondę rosteru (koszt 0)** — jedna lista
   110 `game_id` rozstrzyga, czy pamięć między wpisami jest warta 0 czy +15"*.
   ❗**NAJTAŃSZA RZECZ DOSTĘPNA, DO ZROBIENIA PRZEZ USERA DZIŚ:** log rerunu **ref 57737623**
   (Kaggle → Submissions → v11 → Output) zawiera **prawdziwe 110 `game_id`** — v11 już leciał
   i dał 23.89. Zero kosztu, zero slotu, zero GPU. Ich własna notatka z 25.10: *„sonda rosteru
   dowozi dane za darmo — koszt 0"*.
   **Oczekiwanie: 26–31 (Gemma) / ~27–29 (mój) / 28–38 (ich README) — trzy przedziały zachodzą
   na siebie wokół ~28–30.** Cel: srebro ≈32.33.

16. **`AUDYT-4-GALEZI-30-10.md`** — ❗**NAJNOWSZE (30.10 ~07:45 UTC). RETRAKCJA SMaka + LICZBA
   WARTA WIĘCEJ NIŻ CAŁY SPÓR O v13.**
   **✅ SMak WYDAŁ RETRAKCJĘ nr 3** (SYNC §15, `43c8d9ff` 07:35): *„„roster = 110 klonów 25 gier
   POTWIERDZONY W KODZIE" — **FAŁSZYWE** … `official_110()` = **KSZTAŁT** submisji na symulatorze
   LOKALNYM, **NIE roster punktowany** … playbook **EV ≈ 0** … **„sufit 45-55" RETRAKTOWANY** …
   replay między wpisami = **martwe** … **lekcja c87, trzeci raz: czytać DOCSTRING, nie nazwę
   funkcji**."* Zachowali moją „formalną szczelinę" i dodali: *„**ROZSTRZYGNIĘCIE ZA DARMO**:
   probe z outputu dzisiejszego runa albo log reruna #57737623"*. W §16 przyznają wprost:
   *„moja sesja to poprawnie ustaliła 25.10 i **sama sobie zaprzeczyła 30.10**"*.
   **KONWERGENCJA 4 SESJI** — ich własna tabela (§1.1): martwe 2 z 3 dźwigni (Gemma+c87) · 23.89 =
   draw (7911 sd=2.47 + c87 σ=3.93) · głębokość ~96% brakujących punktów (3 sesje) · 50+ =
   przepustowość (3 modele) · **cap = 1.15** (c87) · playbook 14/14 (3 reprodukcje).
   Przyjęli też od 7911: **`commit(plan)` tylko OFEROWANY** ⇒ *„bez wymuszenia v13.1 gra jak
   v11+playbook (~28-30)"*, naprawy `ESCALATE_ACTIONS` 60→8-10 i **wymagać linii logu o replay**
   (cicha awaria `try/except pass`). Ich kontrola **serving-parity v13.1 == c45** (kom.21==kom.17,
   MAXREQ=10/cuda-graph/chunked identycznie) to **dokładnie ten rodzaj sprawdzenia międzywarstwowego,
   którego zabrakło przy `concurrency=120`**.
   ❗**NAJWAŻNIEJSZA LICZBA AUDYTU — `MEGA-CONFIG.md` Gemmy §1. Ten SAM model 8B:**
   | run | ms/token | tok/akcję | s/akcję | **akcje/grę (49 min)** |
   |---|---|---|---|---|
   | **r085** (bez capa) | **17,2** | 647 | 12,9 | **228** |
   | **r110** (v13 cap 45k) | **62,6** | 572 | 36,0 | **82** |
   | r118 (27B) | 63,1 | 686 | 47,0 | 63 |
   **3,6× różnicy, która — cytuję Gemmę — „nie pochodzi z modelu ani z promptu".** I uwaga:
   **r110 ma MNIEJ tokenów na akcję (572 vs 647), a 2,8× MNIEJ akcji na grę** ⇒ „mózg treściwszy"
   **nie pomógł**, zjadł go silnik. **To obala intuicję, że oszczędzanie tokenów/akcję jest główną drogą.**
   Z projekcji Gemmy: 200 akcji → 35,6 · **300 → 59,5** · 400 → 72,3. Czyli **odzyskanie 3,6× to
   82 → 228 akcji = ~18,7 → ~35,6 pkt BEZ zmiany modelu, promptu, playbooka czy schedulera.**
   **To ~10× więcej niż cały spór o v13** (playbook 0–2,9 · CAP=0 +0,4…2,2 · PLAN_COMMIT ~0).
   **MOJA HIPOTEZA MECHANIZMU (§3), z arytmetyką, sprawdzalna za darmo:** pula KV = **1 011 264**
   tokenów, kontekst harnessa **131 072**, gier współbieżnych **10** ⇒ `10 × 131 072 = 1 310 720 >
   1 011 264` ⇒ przy pełnym kontekście mieści się **7,7 gry**; pula nasyca się, gdy średni kontekst
   > **101 126**, a **trim odpala dopiero przy 118 000** ⇒ nasycenie jest **OCZEKIWANE, nie wyjątkowe**.
   Dokładnie ten mechanizm opisał **rellik13 (25. miejsce)**: *„kv pool sat **91-97% full** and
   requests **queued for cache space** — memory was the actual limit"*. ⚠️ **Uczciwie: hipoteza
   NIE wyjaśnia, dlaczego r110 (też smoke-like, 10 gier) ma 62,6 — jeśli prefix-cache ma być
   wyjaśnieniem, trzeba innego mechanizmu. NIE DOMKNALEM bez przeczytania r110.**
   **ROZSTRZYGNIĘCIE: sparsować `serve.log`** — `r085` **986 600 B** (run z 17,2), `r093`
   **1 143 523 B**, `r110/output-pick` (run z 62,6; **istnienie potwierdziłem**, zawartości nie
   czytałem). Policzyc: % obłożenia puli KV w czasie, kolejki po cache, trafialność prefix-cache
   (r085 ma zmierzone **93,2%**), ms/token per gra. **0 GPU, 0 slotów, PC usera.**
   **ARYTMETYKA PRAWDZIWEGO SUBMITU (Gemma §2.2, z komórki 25 v13.1):** budżet **32 400 s** (asercja
   w kodzie) · roster **110** · concurrency **10** · **fal = 11** · efektywny czas na grę
   **32 400/11 = 2 945 s ≈ 49 min** ⇒ **cap `532*60` min NIGDY NIE WIĄŻE, wiąże liczba fal.**
   `USE_PRIORITY_SCHEDULING = True` **potwierdza ostatecznie** moją korektę §2.3. Gemma przy tym
   **retraktuje własny błąd**: *„pierwotna wersja twierdziła, że dźwignią jest podniesienie
   `max_runtime_s_per_game` … **To było błędne** i wynikało z **czytania dev-smoke'a jako submitu**"*
   — **to DOKŁADNIE ten sam błąd, który ja zrobiłem i wycofałem.** Reguła do `FAKTY`: komórka
   konfiguracyjna ma DWA bloki (smoke i `TRUE_SUBMISSION`); czytanie pierwszego jako drugiego daje
   fałszywy model budżetu.
   **`6d081d52` (nieaktualizowana od 25.10) zawiera AUDYT MOJEJ GAŁĘZI na tipie `6c53d13`:**
   formuła punktacji *„zgodna co do setnej z r019"* (**4. niezależne potwierdzenie capu 115**),
   moje **1,75 pkt** potwierdzone ich rachunkiem (sufit głębokości 29,0 vs zmierzone 27,21),
   moja **kalibracja kliknięć po efekcie** uznana za *„najbardziej transferowalny wynik metodyczny"*,
   moja retrakcja +7–17 pkt odnotowana, **`n_passes` nadpisywane do 1 w komórce 14 — niezależne
   potwierdzenie już 25.10**, `game_weights` nie realokuje budżetu, kompakcja pamięci istnieje
   (`ARC3_MEMORY_SECTIONS=off`, `HISTORY_ASSISTANT_TURNS=150` nie 30).
   ⚠️ **FLAGA ZGODNOŚCI DOTYCZĄCA MOJEGO KODU — PRZYJMUJĘ:** *„Wewnętrzne `_get_valid_actions()`/
   `_score`/`_win_score` zostały w audycie oznaczone jako **niedozwolone w submissionie**; używać
   publicznego API i kalibracji po skutku."* Dotyczy `arc3_search.py`. Praktyczny skutek żaden
   (search offline wycofany), ale **wzorzec nie może przeniknąć do submisji**.
   **7911f950 `EVAL-BUDGET-MODEL.md`: DOBRY dowód pośredni na ~110 gier** (smoke 10×48 min =
   27,21–29,02 ≈ LB **26,25** ⇒ ten sam budżet na grę ≈49 min, nie 4× dłuższy), **ale odpowiada
   na pytanie (a) „ile gier", NIE na (b) „czy to klony 25 publicznych" — a tylko (b) decyduje o
   playbooku.** ⚠️ **NAPIĘCIE WEWNĘTRZNE W ICH WŁASNEJ TABELI:** sufit dla 110 gier = **18,7**,
   a zmierzony LB = **26,25** — czyli **wynik POWYŻEJ ich własnego sufitu**. Tempo 14,4 s/akcję
   wzięte z **r013 (stara linia)** wobec 12,9 s/akcję dla naszej szybkiej daje 205 → 228 akcji
   (+11%), co **nie** zamyka luki 18,7 → 26,25. Nie rozstrzygnę bez `scheduler.py` i r018 —
   **zaznaczam, bo obie liczby są cytowane w SYNC §16 jako ustalenia.** To ten rodzaj niespójności
   między dwiema liczbami w jednym dokumencie, który u mnie spowodował `concurrency=120`.
   **PLAN PO PRZELICZENIU WARTOŚCI — ZMIENIONY (§6.2): (1) sparsować `serve.log` — 0 GPU, 0 slotów,
   potencjalnie ~18,7 → ~35,6 · (2) pobrać log rerunu 57737623 — 110 `game_id`, kończy spór o roster ·
   (3) sprawdzić czy `ARC3_ESCALATE_ACTIONS` jest env i przygotować 60→8-10 · (4) slot 30.10 =
   v13.1 + probe ON + `CAP=0` + `EXPOSE_UNDO="on"` + `PLAN_COMMIT="0"` · (5) slot 31.10 =
   rozgałęzienie pomiarem · (6) 1.11/2.11 = drugi draw + select best.**
   Przez trzy dni spieraliśmy się o dźwignie warte **0–2,9 pkt**, podczas gdy w artefaktach leży
   **3,6× w ms/token** warte **82 → 228 akcji/grę**. Nikt jej nie zbadał, bo **nikt nie sparsował
   `serve.log`**. Ta sama lekcja co `concurrency=120` i `EXPOSE_UNDO`: **liczby leżą obok siebie
   w artefaktach i czekają, aż ktoś je porówna.**

17. **`OCENA-V13-2.md`** — ❗**NAJNOWSZE (30.10 ~08:00 UTC) I UNIEWAŻNIA CZĘŚĆ WPISÓW 15–16.**
   **v13.2 ISTNIEJE**: `Pokemon@a450b00f` commit **`6b108534`** (07:45:14), `arc-agi-3/duck-v13-2/`.
   Dwie zmiany, obie z audytów innych gałęzi: **`ESCALATE_ACTIONS` 60 → 10** (audyt 7911: commit
   tylko oferowany, eskalacja to jedyne wymuszenie) + **guard `GAME_OVER` w replayu** (drobiazg
   Gemmy) + korekta liczby testów (**7+1=8** dopiero od v13.2; opis v13.1 „12+8" był o jeden za duży).
   ✅ **DOMKNĄŁEM SWOJĄ LUKĘ SAM, nie na deklaracji**: `duck-v13-2/arc3-duck-v13.ipynb` (714 156 B),
   komórka 2 → `ESCALATE_ACTIONS = 10` i **`_v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(...)`**,
   a patch 0005: *„ESCALATE_ACTIONS: actions on one level before the escalation directive"* oraz
   *„escalation directive **every** ESCALATE_ACTIONS actions"*. **Cztery potwierdzenia: próg JEST
   z env · wartość 10 · dyrektywa POWTARZA SIĘ co N akcji (lepiej niż zakładałem) · wartość jest
   LOGOWANA** (`escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}`) ⇒ weryfikowalna
   z logu rerunu. **Pierwszy raz w tym konkursie dźwignia spełnia wszystkie trzy warunki reguły
   `SCOPE=run`: czytana z env, ma ścieżkę wymuszenia, loguje wartość.**
   ❗**DZIEWIĄTA KOREKTA MOJEGO WNIOSKU — PIERWSZA NA KORZYŚĆ DŹWIGNI.** Moje trzy stanowiska
   wobec `PLAN_COMMIT`: `OCENA-V13-MEGA.md` §7 → **`"0"`** (niezmierzone) · `OPINIE-3-GALEZI` §5 →
   **ODWRÓCONE na `"1"`** (bottleneck = akcje/decyzję) · `OCENA-V13-1` §2 → **ODWRÓCONE Z POWROTEM
   na `"0"`** (7911: tylko dopis do promptu, *„nie ma żadnego wymuszenia"*, eskalacja po 60) ·
   **teraz → `"1"` + `ESCALATE=10` jest spójną konfiguracją testującą bottleneck.**
   **To nie flip-flopping, tylko konwergencja: każde odwrócenie wymusił NOWY FAKT Z KODU.**
   Stanowisko (3) było **poprawne dla v13/v13.1** (tam próg 60 > długość poziomu ~24–35 akcji,
   więc **nie odpalał się nigdy**); (4) jest poprawne **dla v13.2**. **Reguła do `FAKTY`:
   „dźwignia niezmierzona", „niewymuszona" i „wymuszona" to TRZY RÓŻNE STANY — nie wolno
   przenosić werdyktu między wersjami bez przeczytania diffu.**
   ❌ **AUDYT 7911f950 MÓWI „v13.2 NIE ISTNIEJE" — NIEAKTUALNE O 10 MINUT.** Ich `V13-AUDIT-30OCT.md`
   §1 (commit `57d04aa0`, **07:55:27**): *„git grep na wszystkich gałęziach — brak; najnowszy commit
   `a450b00f` = `cbefdd4`, brak nowszego"*. **Fakt: v13.2 = `6b108534`, 07:45:14, katalog
   `duck-v13-2/` (14 plików).** Ich `git fetch` był przed 07:45. **To nie zarzut nieuwagi, tylko
   race condition — ale w PRZEDMOWIE TEGO SAMEGO DOKUMENTU wytknęli sobie DOKŁADNIE ten błąd:**
   *„Napisałem, że diffu v13→v13.1 nie da się odtworzyć. **To było nieprawdziwe** … klon był
   single-branch i pierwszy `git fetch` nie pobrał historii … **twierdzić „nie ma", nie
   sprawdziwszy, czy ref jest w ogóle pobrany**"* — **czyli zdiagnozowali klasę błędu i 20 linii
   niżej popełnili ją ponownie.** Konsekwencja merytoryczna: **ich audyt wykluczył z zakresu wersję,
   która naprawia wadę, którą sami znaleźli.**
   ✅ **Reszta ich audytu wartościowa — diff v13→v13.1 to DOKŁADNIE DWIE zmiany w kodzie**
   (`_sanitize(game_id)` → `base_key(game_id)`; usunięcie bramki `pass_index < 4` w `dead_skip`),
   co jest **kodowym potwierdzeniem mojego §2.3**: w v13 `dead_skip` przy `pass_index` **zawsze 0**
   ⇒ `0 < 4` ⇒ `return False` ⇒ **nie odpalał nigdy**.
   ❗**NAJWAŻNIEJSZA NOWA LEKCJA (7911): „TESTY 6/6 ZIELONE PRZY MARTWEJ FUNKCJI".** v13 miał
   `ALL CHECKS PASSED`, 6/6 patchy, 12/12+6/6 testów **na spatchowanym drzewie**, przełącznik w obie
   strony — **a dwie z trzech dźwigni były martwe w konfiguracji submisyjnej**. Powód:
   `test_winpath.py` używa **mocka solvera**, w którym `pass_index` przyjmuje 1,2,3,4 — **wartości,
   których rerun nigdy nie produkuje** (`n_passes=1` ⇒ zawsze 0). **W `OCENA-V13-MEGA.md` §5.2
   pochwaliłem tę dyscyplinę jako lepszą od mojej — i słusznie, ale ona NIE WYSTARCZYŁA.**
   **PEŁNA TAKSONOMIA KLASY BŁĘDU (6 instancji, §5):** `SCOPE=run` (walidator, cicha degradacja) ·
   `concurrency=120` (spójność międzywarstwowa) · `EXPOSE_UNDO` (domyślne legacy) · `official_110`
   (nazwa vs docstring) · `commit(plan)` (prompt vs zachowanie) · **`dead_skip` (MOCK TESTU vs
   KONFIGURACJA SUBMISJI)**. **REGUŁA NAJWYŻSZEGO RZĘDU: ZIELONE TESTY MODUŁU NIE DOWODZĄ, ŻE
   FUNKCJA WYKONUJE SIĘ W KONFIGURACJI SUBMISYJNEJ.** Brakująca warstwa to **test OSIĄGALNOŚCI**,
   nie poprawności: *„przy `TRUE_SUBMISSION=1` i `n_passes=1`, czy ten kod w ogóle zostanie
   osiągnięty?"* — **nikt w czterech gałęziach go nie ma.** Propozycja (§5): krok w `verify_v13.py`
   wypisujący **ścieżkę warunków** od `TRUE_SUBMISSION` do efektu każdej dźwigni i flagujący
   zmienne **stałe w rerunie**. Złapałby `dead_skip` w v13 **automatycznie, bez trzech recenzji**.
   ⚠️ **NOWE PODEJRZENIE, KTÓREGO NIKT NIE SPRAWDZIŁ: `DEAD_SKIP` W v13.1/v13.2 PRAWDOPODOBNIE
   ZNOWU JEST MARTWY** — licznik `passes_completed` per `base_key` nigdy nie dojdzie do 3, jeśli
   każda gra występuje w rosterze **RAZ**. Gemma testowała dead-skip na **5 powtarzanych wpisach
   `ar25`**, czyli **w scenariuszu wykluczonym przez retrakcję Smaka §15**. **Czwarta instancja
   testowania na założeniu, które odpadło.**
   ❗**ARYTMETYKA, KTÓRA ZMIENIA KOLEJNOŚĆ (§6).** Wzór Gemmy `akcje/grę = 2945 s / (s na akcję)`,
   a `s/akcja` liniowe w ms/token (r=0,99–1,00) ⇒ **`akcje/grę = 2945 × 1000 / (ms/token × tok/akcję)`**:
   · r085: 17,2 × 647 = 11 128 → **265** (Gemma mierzy 228, rząd zgodny) · r110: 62,6 × 572 = 35 807
   → **82** ✓ dokładnie jej pomiar · **CEL 400 akcji wymaga `ms/token × tok/akcję ≤ 7 362`**, czyli
   przy 17,2 ms/tok → tok/akcję ≤ **428**, albo przy tok/akcję 400 → ms/tok ≤ **18,4**.
   **SAM BATCHING PRZY 62,6 ms/TOKEN DAJE 2945×1000/(62,6×400) = 118 AKCJI — NADAL PONIŻEJ 228
   Z r085 BEZ BATCHINGU.** ⇒ **`ESCALATE_ACTIONS=10` bez naprawy silnika NIE DAJE 400 akcji, a może
   być GORSZY od r085.** **Dwie dźwignie są MULTIPLIKATYWNE: `commit(plan)` mnoży akcje/wywołanie,
   luka silnika mnoży wywołania/sekundę. MULTIPLIKATOR RAZY ZERO DAJE ZERO.**
   ⚠️ **Ich uzasadnienie liczbowe używa STAREJ linii**: README v13.2 *„dziś **1,0 akcji/decyzję** →
   sufit ~19–31; 2,0 → ~51"* to liczby 7911 z **r013/r015/r018**. **Nasza szybka linia (r019) ma
   4,357 akcji na wywołanie** — czyli **nie startujemy z 1,0**. Zmiana jest słuszna i darmowa, ale
   **projekcja „sufit ~51" nie jest naszą podstawą decyzji.** Rozróżnienie trzech metryk (§6):
   **akcje/grę 212,6** (budżet czasu) · **akcje/wywołanie 4,357** (batching) · **„akcje/decyzję"
   1,00** (stara linia) — **nie są zamienne.**
   **PLAN AKTUALNY (§7.2) — pkt 1 AWANSOWAŁ NA WARUNEK KONIECZNY:**
   **1** ❗sparsować `serve.log` (r085 986 600 B = 17,2 ms/tok · r110 = 62,6 · r093 1 143 523 B):
   obłożenie puli KV w czasie, kolejki po cache, prefix-cache (r085: 93,2%), ms/tok **per gra** —
   **0 GPU, 0 slotów, PC usera** · **2** pobrać log rerunu **57737623** → 110 `game_id` ·
   **3** test OSIĄGALNOŚCI w `verify_v13.py` (§5) · **4** slot 30.10 **decyzja PO pkt 1**: silnik
   ~17 ms/tok → **v13.2 + probe ON**; silnik ~60 ms/tok → **v13.2 z `ESCALATE_ACTIONS` 20–25** albo
   **v11 + `CAP=0`** (nie dokładać batchingu do zduszonego silnika) · **5** slot 31.10 = drugi draw ·
   **6** 1.11/2.11 = najlepsza + select best.
   **Wysyłanie v13.2 przed zmierzeniem silnika to powtórzenie błędu v11: zmiana bez pomiaru zasobu,
   który ją ogranicza.**
   ❌ **NOWE „NIE ROBIĆ":** `PLAN_COMMIT="1"` **przy `ESCALATE_ACTIONS=60`** (nie odpala nigdy) ·
   **wysyłanie v13.2 przed sparsowaniem `serve.log`** · traktowanie **zielonych testów modułu** jako
   dowodu, że dźwignia wykonuje się w submisji.
   **Oczekiwanie ~28–30 · cel srebro ≈32.33 · ścieżka do 40+ JEDNA i niezmieniona: odzyskać
   17,2 ms/token.** v13.2 dokłada do tego **multiplikator**, ale multiplikator razy zero daje zero.

18. **`POMIAR-SERVE-LOG-I-V15.md`** + **`tools/parse_serve_log.py`** — ❗**NAJNOWSZE (30.10 ~08:20 UTC).
   DZIESIĄTA KOREKTA: „3,6× luka silnika" NIE ISTNIEJE, a moja hipoteza KV jest OBALONA moim własnym
   pomiarem.** Napisałem parser i uruchomiłem go na **prawdziwych** `serve.log` (r085 986 600 B,
   r093 1 143 523 B, pobrane przez `gh api`).
   ❌ **HIPOTEZA NASYCENIA KV OBALONA:** obłożenie puli średnio **0,6042 / 0,5258**, próbek **≥0,91
   tylko 3,53 % / 2,53 %** (nie „91-97% full"), `#queue-req>0` w **4,72 % / 3,33 %**, **mediana
   kolejki 0,0 W KAŻDYM OKNIE CZASU**, korelacja obłożenie↔throughput **DODATNIA** (+0,0921/+0,3773),
   throughput przy TU≥0,91 **WYŻSZY** (752,1 vs 654,5 tok/s). Moja arytmetyka `10 × 131 072 > 1 011 264`
   mnożyła **MAKSYMALNY** kontekst — a kontekst jest przycinany (118k→~59k), więc pula ma ~40 %
   zapasu. **To ten sam błąd co przy capie 45k: poprawna arytmetyka, zła populacja.** Mechanizm
   rellik13 jest prawdziwy, ale **nie dotyczy naszej konfiguracji** (on: 16 strumieni/69 632; my: 10/131 072).
   ✅ Produkt uboczny: `EKONOMIA-TOKENOW.md` §1bis miało „603 tok/s" — zmierzone **663 (r085)** i
   **584 (r093)**, czyli **603 leży dokładnie między nimi, co do 10 %**.
   ❌ **„3,6× LUKA SILNIKA" NIE ISTNIEJE — wiersz tabeli `MEGA-CONFIG.md` jest BŁĘDNIE ZAETYKIETOWANY.**
   `r110` opisany jako „8B, v13 cap 45k" to w rzeczywistości **27B/vLLM**: log `arc3-duck-v13-27b.log`,
   serwer `vllm-openai-server.log` (nie SGLang-owy `serve.log`), w treści **742× „vllm", 17× „27b",
   0× „sglang"/„flash-next"**; `summary.txt`: mean **0,73**, 926 akcji, 155,46 tok/s, 48m6s.
   **Skoro `r110` (62,6) i `r118` (63,1) to OBA 27B, są zgodne — a różnica 17,2→62,6 to 8B vs 27B,
   czyli DOKŁADNIE różnica modelu**, o której Gemma napisała, że z niego „nie pochodzi".
   **Linia 8B JUŻ JEST w dobrym stanie. Nie ma czego odzyskiwać.**
   ❗**DZIESIĄTA KOREKTA, NAOSTRZEJSZA: zweryfikowałem ISTNIENIE artefaktu, nie jego TOŻSAMOŚĆ** —
   napisałem *„sprawdziłem, że r110 istnieje… zawartości nie czytałem"* i na tej podstawie awansowałem
   parsowanie `serve.log` na dźwignię nr 1 „wartą 20–40 punktów" oraz uczyniłem je **warunkiem
   koniecznym** decyzji o slocie. **Awans WYCOFANY.** Złamałem własną regułę w momencie, w którym ją
   cytowałem. **NOWA REGUŁA DO `FAKTY`: CYTOWANA TABELA JEST ARTEFAKTEM WTÓRNYM — przed zbudowaniem
   na niej priorytetu trzeba pobrać artefakt PIERWOTNY i sprawdzić jego TOŻSAMOŚĆ (nazwa pliku,
   serwer, model, znacznik czasu), nie tylko ISTNIENIE.**
   ✅ **Co zostaje prawdziwe:** arytmetyka `akcje/grę = 2945×1000/(ms/token × tok/akcję)`; a skoro
   silnik 8B jest już dobry (17,2 ms/token), **JEDYNYM czynnikiem do ruszenia jest `tok/akcję` = 647**.
   Cel Gemmy: 400+ akcji/grę wymaga ~370 tok/akcję. **CZYLI BATCHING JEST WŁAŚCIWĄ DŹWIGNIĄ** —
   stan ostateczny po czterech odwróceniach: `OPINIE-3-GALEZI` §5 (tak) → `OCENA-V13-1` §2 (nie) →
   `OCENA-V13-2` §3 (tak) → §6 (nie) → **TERAZ: TAK, i silnik nie jest przeszkodą.**
   ⚠️ **Dodatkowo `r110` potwierdza coś innego:** każda gra dostała **~45k tokenów** (45 247 / 45 775 /
   45 411 / 44 850 / 45 276 / 44 582 / 42 317 / 44 385 / 45 769 / 45 170) przy wyniku **0,73** —
   czyli cap 45k **wiązał w każdej grze**. Niezależny dowód przeciwko mojemu patchowi 0004.
   ✅ **GEMMA ZMIERZYŁA PRÓG ESKALACJI (`escalation_audit.py`, r085, 32 ukończone poziomy):**
   próg **10** → **154** wstrzyknięcia, 22 330 tokenów = **15,3 % puli gry**, odpala **PRZED** ludzkim
   baseline'em na **31/32** poziomów (`cn04/4` „przestań próbować" po 41 akcjach, gdy człowiek
   potrzebuje 300) · próg **20** → **60**, 6,0 %, ~25/32 · próg 60 → 12, 1,2 %, 7/32 ·
   **`max(20, 1,2×baseline[poziom])` → 8, 0,8 %, 0/32.** Czyli **`ESCALATE_ACTIONS=10` z v13.2 jest
   19× ZA CZUŁE.** Ich argument: *„kosztowna jest POSŁUSZNOŚĆ, nie tekst"* (każda zachęta prosi o turę
   modelarską; co czwarta → ~12 tys. tokenów = 8 % puli) oraz efekt drugiego rzędu: priority gate
   szereguje gry wg `priority_pace_reference.json` (poziom 1 = 27 tys. tokenów, fallback 45,9 tys.),
   więc **gra, która napompuje tokeny, wpada do gorszej bandy kolejki — eskalacja @10 może sama
   wypychać grę z kolejki.**
   ⚠️ **Gemma precyzuje mój §2 z `OCENA-V13-2`: dyrektywa jest PRZYPOMNIENIEM, NIE WYMUSZENIEM**
   (*„commit() zostaje opcją modelu"*). **Uzupełniam taksonomię stanów dźwigni: zareklamowana →
   PRESJA OKRESOWA → wymuszona.** v13.2/v13.3/v15 są na środkowym.
   ❗**INTERAKCJA, KTÓRĄ WYŁAPAŁA GEMMA (argument za 20, nie za 10):** v13.3 dokłada hint „batchuj",
   więc działają **DWA NACISKI NARAZ** — „wykonuj więcej akcji na turę" i „przestań działać, zbuduj
   model". **Przy progu 10 drugi WYGRYWA na pierwszych ~10 akcjach każdego poziomu**; przy 20 hint ma
   czas zadziałać. **Dwie zmiany, każda osobno uzasadniona, razem się znoszą.**
   **v13.3-arena (Smak `5548d35`)** dokłada dwie rzeczy, których brakowało: **`ARC3_OPENER_COMMIT_HINT=1`**
   (batch na **1. turze** poziomu — atakuje `tok/akcję` od początku, zamiast czekać na próg) oraz
   **patch 0007 = log zdarzeń win-path** (odpowiedź na „cichą awarię replay bez logu" od 7911).
   **duck-v14** (`b38b82eb`) = v13.2 + próg **20** + **guard hooka sondy c45** (bo
   `_orig_play = _S._HarnessGameSession.play` stało **POZA** jakimkolwiek `try` w komórce ustawiającej
   `bm.solver.*` ⇒ brak atrybutu w innym revision bundla = **martwy notebook przed startem** — ósma
   instancja klasy „awaria na ścieżce submisji, niewidoczna dla smoke") + **sonda rosteru** + **sonda budżetu**.
   **duck-v15** (`07bf05e0`) = **v13.3-arena + 3 rzeczy z v14, które są env-only albo read-only.
   ZERO nowych patchy** ⇒ certyfikacja v13.3 (**7/7 na czystym r033, 11/11 winpath, standalone ==
   patched, playbook 14/14 na silniku**) **przenosi się bez zmian**. **Diff v15 vs v13.3 to DOKŁADNIE
   komórki 1, 2, 26, 30 i nowa 37. Nic więcej.**
   **SONDA ROSTERU v15 (komórka 37) ROZSTRZYGA SPÓR, O KTÓRY PROSZĘ OD DWÓCH TUR — LEPIEJ NIŻ MÓJ
   POMYSŁ Z PRZEGLĄDARKĄ:** czyta `bm.game_runs` po biegu, pisze `roster_probe.jsonl`, drukuje werdykt
   o powtarzalności bazowych kodów gier (czy pamięć win-path jest warta **0** czy **+5…15**) —
   **plus ALARM `actions_per_call < 1,5` → batch pressure nie działa.** Czyli **w jednym biegu**
   rozstrzyga roster **i** mierzy, czy jedyna dźwignia zadziałała. Moja baza porównawcza: **4,357
   akcji/wywołanie** z r019.
   ⚠️ **JEDEN SPÓR FAKTUALNY, KTÓRY v15 ROZSTRZYGNIE:** v14/v15 twierdzą *„we wszystkich trzech
   zapisanych runach każda gra kończy się DOKŁADNIE na capie (`max == min == 48/48/90 min`), gra nie
   zatrzymuje się sama, więc cap jest przydziałem akcji"*. **To sprzeczne z moim pomiarem z surowych
   `benchmark.json`: r093 (v11) → 3 z 10 gier skończyły się WCZEŚNIEJ (`g50t` 1499 s, `cn04` 1609 s,
   `tn36` 1692 s przy 2871–2893 s pozostałych); r085 (c45) → `tn36` 2166 s przy 2880–2885 s reszty.**
   Oznaczam jako **rozbieżność, nie obalenie** (nie znam ich zestawu trzech runów). **Znaczenie:** jeśli
   gry mogą kończyć się wcześnie, cap NIE jest jedynym przydziałem, a mój bug `min_done=0`/`ABANDON`
   jest realny (3 gry × 1188–1381 s = 3840 s i ~243 600 tokenów oddanych). **Sonda budżetu v15 to
   zmierzy — nie muszę rozstrzygać przed slotem.**
   ✅ **Gemma znalazła SIÓDMĄ instancję klasy „zielony test przy martwym kodzie":** *„guard czyta
   `game_state.raw.state`, a **mój pierwszy symulator nie miał atrybutu `raw`** — guard MILCZAŁBY i
   test certyfikowałby ścieżkę, której nie ma. To dokładnie ten rodzaj błędu, który daje fałszywe
   ALL CHECKS PASSED."* Uzupełniam taksonomię z `OCENA-V13-2.md` §5: obok „mock karmi wartości, których
   rerun nie produkuje" (`pass_index`) jest **„mock NIE MA POLA, które czyta guard"**. **Reguła: mock
   musi być walidowany przeciwko KONTRAKTOWI (np. `assert hasattr(state, "raw")`), nie tylko przeciwko
   temu, co test chce zobaczyć.**
   ❌ **ODPOWIEDŹ NA „A MOŻE SAM ZROBISZ LEPSZĄ WERSJĘ, KTÓRA DOGONI LIDERÓW": NIE — i to nie jest
   skromność, tylko trzy twarde powody.** (1) **Nie mogę jej zweryfikować**: certyfikacja wymaga
   `verify_v13.py --bundle <r033>` na czystym bundlu Franzena, a ja **nie mam bundla r033, nie mam
   `arcengine`, nie mam GPU, nie mam `cargo`** (2 CPU / 3,9 GB); 3 z 12 testów `test_plan_commit.py`
   wymagają `inference.agent.python_tool_sandbox` z bundla (potwierdził to 7911f950 niezależnie).
   (2) **Nie mogę jej przetestować przed spaleniem slotu**, a zostały **3** (31.10, 1.11, 2.11) przy
   σ≈2,5–3,9 i progu +5 pkt. (3) **v15 JUŻ JEST LEPSZY I ZWERYFIKOWANY**: diff 5 komórek, dziedziczy
   certyfikację 7/7, zawiera obie rzeczy, które sam bym dodał (sonda rosteru, sonda budżetu), plus
   dwie, na które bym NIE wpadł (guard hooka poza `try`; interakcja opener-hint ↔ eskalacja).
   **Zbudowałbym rzecz niezweryfikowalną i zużył na nią slot, którego nie ma.**
   ❌ **„DOGONIĆ LIDERÓW" = 50+ — PODTRZYMUJĘ, ŻE NIEOSIĄGALNE, i mam jeden dowód więcej.** Próg top-5
   **51,04**, Chen **75,56**; nasza baza μ **25,77**, σ **3,93**, najlepszy draw **35,35** ⇒ **+25,3 pkt
   = +6,4 σ**. **Nowy dowód: jedyną dźwignią o właściwej skali jest `tok/akcję` (647 → ~370), a
   zmierzony koszt SAMEJ DYREKTYWY eskalacyjnej przy złym progu to 15,3 % puli** — czyli dźwignia,
   która ma **obniżyć** zużycie tokenów, przy złym progu je **podnosi**. Do tego **WM GPT-5.4 = 24.67
   < nasze 27,21**, więc scaffold paper01 bez GPT-5.5 nie daje 56.81.
   **RANKING PO TEJ TURZE:** **1** wysłać **v15** (nie v13.2, nie v14) — ~28–31 **i rozstrzyga
   roster + mierzy `actions_per_call` w tym samym biegu** · **2** przeczytać z logu: `roster_probe.jsonl`,
   `budget_probe.json`, `actions_per_call` · **3** test osiągalności + asercja kontraktu mocka ·
   **4** parser `serve.log` jako **STRAŻNIK REGRESJI** na każdym nowym runie (~5 min) · **5** 31.10 =
   **DRUGI DRAW v15**, nie inna konfiguracja · **6** 1.11 rozgałęzienie z pkt 2, 2.11 select best.
   ❌ **WYCOFANE Z POPRZEDNIEGO PLANU:** ~~parsowanie `serve.log` jako dźwignia nr 1~~ (hipoteza
   obalona) · ~~„odzyskać 17,2 ms/token"~~ (nie ma czego odzyskiwać) · ~~`ESCALATE_ACTIONS=10`~~
   (19× za czułe, kontrowało opener hint).
   ➕ **NOWE „NIE ROBIĆ":** budowanie priorytetu na **cytowanej tabeli** bez sprawdzenia tożsamości
   artefaktu · przenoszenie **mechanizmu** z cudzej konfiguracji bez przeliczenia · **hooki poza `try`**
   w komórce ustawiającej `bm.solver.*`.
   **Oczekiwanie ~28–31 · cel srebro ≈32.33 · do liderów droga nie istnieje w 3 slotach — i wolę to
   powiedzieć dziesiąty raz, niż obiecać jedenaście.**

23. **`AUDYT-PAKIET-31-10-I-WYNIK-13-28.md`** — ❗**NAJNOWSZE (31.10 ~15:20 UTC). NAJWAŻNIEJSZE
   DECYZYJNIE OD TYGODNIA: v13.7-final ZOSTAŁ ZGŁOSZONY I DOSTAŁ 13.28.** Zgłoszenie **57811453**,
   COMPLETE (Actions + own-submissions.csv): **−10.61 vs v11 (23.89), −12.97 vs mistrz v3 (26.25)**;
   smoke 22.59 ⇒ luka smoke→rerun **−9.31** (u v11 było **+5.34** — smoke nie predykuje nawet
   kierunku). Przy σ≈3.9 to **≈2.7σ ⇒ regresja konfiguracji, nie los**. **Rekomendacja GO dla
   v13.7 wycofana przez autorów; ja wycofuję swoje wczorajsze „ZGODA bezwarunkowa"
   (self-korekta 19): poparcie dotyczyło konfiguracji BEZ ani jednego pomiaru rerun.**
   **Degraduję też a/call z „bramki" do diagnostyki (self-korekta 20)** — „próg 6.0" był
   zapożyczoną implikacją wystarczalności, nie predyktorem; pakiet ma rację.
   **Audytowany pakiet (kontroler symboliczny, gałąź `codex/arc-local-lab-v18-20261030`, komity
   `f730639`/`aec6c3e`/`91f1ce9`):** notebook SHA256 `550eb185…d5fa` **co do znaku** ✓ · ich
   **35/35 testów** (moje pierwsze 33 porażki = MÓJ brakujący fixture) ✓ · **pierwsza zanotowana
   akcja odtworzona z pierwszej klatki** (`infer_copy_action` → `(6,39,39, expected=8)`) ✓ ·
   arytmetyka RHAE: 3/6 poziomów ft09 = 6/21 = **28.5714 %** = ich `score_delta` ✓ · obserwacje
   CZYSTE (piksele + legalne akcje + publiczny numer poziomu; brak ID/baseline/silnika/scoringu) ✓ ·
   fallback = oryginalny `analyze` ✓ · izolacja per-ścieżka runtime ✓ · **samounieważniająca się
   predykcja** (jedna niezgodność ⇒ moduł wychodzi z poziomu) ✓.
   **Mój własny pomiar fałszywych rozpoznań: 0/60** na wabikach o geometrii ft09 z losowym
   przemalowaniem 10 % pikseli; abstynencja na planszy zgodnej z regułą i na sprzecznym mapowaniu ✓.
   **❗ MÓJ ZARZUT WYKONAWCZY: pętla stall NIEOGRANICZONA** — oscylująca komórka daje **60 akcji
   w 60 klatkach**, bo w `TemplateTransfer.act` ani w hooku **nie ma limitu akcji na poziom**;
   w RHAE akcje są mianownikiem, więc na ukrytej grze z oscylującym elementem moduł spali cały
   poziom na klikach, które „walidują się" co klatkę. Naprawa = jedna linia; **warunek przed
   jakąkolwiek promocją**.
   **Wartość: +28.5714 na JEDNEJ grze = +1.14 pkt na 25 publicznych i +0.26 na 110 ukrytych,
   a poza grą rozwojową dopasowanie 0/24 ⇒ estymator punktowy na ukrytych ≈ 0.** Dwa rzędy
   wielkości mniej niż zmierzona regresja −10.61. „Hybryda 3 vs 0" = „kontroler 3" **+ „słaby
   lokalny Qwen 0"** (56 wywołań, 0 akcji) — drugi człon to pomiar słabości fallbacku, nie siły
   modułu; A/B na docelowym Flash-Next **nie wykonane**. Rust 33.4× i 75/75 śladów: **przyjęte
   z JSON, nieodtworzalne u mnie** (brak `rustc`, arcengine ≥3.12).
   **REKOMENDACJA: zgłoszenie finalne i slot 31.10 = ZMIERZONY MISTRZ duck v3 (26.25)** — jedyna
   konfiguracja z dobrym rerunem (μ≈25.8, σ≈3.9). **NIE linia v13.x (13.28). NIE hybryda template
   jako zgłoszenie** (≈0 pkt oczekiwane, n=1; notebook nie idzie na Kaggle bez osobnej zgody —
   zbieżnie z pakietem i z BEZPIECZNIKIEM). Kontroler = kierunek badawczy + limit akcji na poziom.
   **Obrazek dołączony do zlecenia NIE jest leaderboardem ARC-AGI-3** (skala 1000+, zespoły
   YumeNeko/Schott/Totsuka… nieobecne w odczycie Kaggle ani w 40 handle'ach `read_top10.py`;
   kolumny Agents/Join i ranking ~Elo pasują do areny agent-vs-agent) — **nierozpoznany,
   nieużyty jako dowód**; progi i deadline pozostają ze strony konkursu, nie ze zrzutu.
   **RESET WORKSPACE #14 w tej turze** (HEAD→`ca72e320`, 247 plików z dysku): odzysk przez
   rescue→fetch→`reset --hard FETCH_HEAD`; 7 różniących się plików `pokemon-agent/` znów starsze
   niż REMOTE. **BEZPIECZNIK: nic nie zgłoszone, notebook nietknięty.**

22. **`AUDYT-V13-7-I-CZTERY-OPINIE.md`** (644 ln) — (30.10 ~14:40 UTC). Fala
   13:40–14:19: `duck-v13-7-final` Smak rev1 `402b3475` + rev2 `72761737`, 7 komitów a450
   (`f7a08aa8`…`c4dc99c9`), audyt Gemmy c4eeb067 `4ac0a5c9` i opinia Gemmy 6d081d52 (wypchnięta
   w trakcie tury jako `8799b6c4`/`9f2b4e63`). Cztery sesje zeszły się w 39 minut na tym samym
   wniosku operacyjnym.**
   ✅ **BUNDEL r033 JEST W REPO** (`arc-agi-3/kaggle/ops/results/r033-recon-bundle/`, 74 pliki,
   1,7 MB) ⇒ **uruchomiłem pełny certyfikat SAM**: `51 OK / 1 FAIL`, a jedyny FAIL to winpath
   (8 × `ModuleNotFoundError: arcengine`, które wymaga Pythona ≥ 3.12; sandbox ma 3.11.2) —
   **limit środowiska, nie wada pakietu**. Wymaga `requests`+`numpy`+`pillow`. **To obala moje
   własne twierdzenie z dwóch tur, że zgodność moich poprawek z certyfikatem potwierdzi tylko
   posiadacz bundla.**
   ✅ **PYTANIE NIESIONE PRZEZ DWIE TURY ROZSTRZYGNIĘTE: moje FIX 4/5/6 NIE łamią certyfikatu.**
   `duck-v13-7-final-c87f` daje **identyczny zestaw kontrol** (diff etykiet różni się tylko nazwą
   katalogu tymczasowego), bramka **4 ustalenia / 0 KRYTYCZNYCH** (z 5/1 na surowym v13.7),
   `--strict` **EXIT=0 bez potoku** (pierwszy raz — wcześniej każdy bieg był przez `grep`),
   różnią się **tylko komórki [14, 39]** z 41, a build ×3 jest **bajt w bajt** (punkt stały).
   ✅ **Tożsamość łańcucha udowodniona z MOJEGO patcha**: `0004-level-token-cap.patch` (142 ln)
   + `git apply 0010` → **bajt w bajt** ich `src/arc3_level_budget_v13_2.py` (md5 `9c184195`),
   `-R --check` przechodzi. **Patch 0010 to upgrade MOJEGO modułu 0004.** md5 `7194ab32` (a450)
   **i** sha256 `736b09cf64ec` (6d081d52) — obie gałęzie miały rację.
   ✅ **rev2 to zmiana WYŁĄCZNIE KOMENTARZA**: diff rev1→rev2 = komórka **[2]**, a `ARC3_VARIANT`
   nadal ma `"ARC3_LEVEL_TOKEN_CAP": "0"`. Komunikat „arming 20000 (nie 60000)" opisuje
   rekomendację, nie konfigurację — **dla slotu 30.10 to dobra wiadomość**.
   ✅ **Cytat 6d081d52: 12 potwierdzonych, 3 z zastrzeżeniem, 1 nie do odtworzenia, 0 obalonych**
   — najdokładniejsza zewnętrzna opinia tej kampanii. Odtworzyłem: 41 komórek / 758 240 B / md5
   `0be69523` · cell-diff **{1,2,12,14,15,33,40} DOKŁADNIE** · `>45k: 14` i `>60k: 13` · **@60000
   aktywny w 16/40, 15 luźniej / 0 ciaśniej** · marnotrawstwo pool **64,5 % / max 100 %** ·
   ls20 na r085 **10,69 %** · drabina po clampie → **225 000 > cap_max** · 16/16 testów dyn.
   ⚠️ Rozbieżności: **max kosztu = 91 043** (a450 i ja), nie 88 114 (cytat); mediana capa
   **129 372** vs 128 612 (0,6 %) — ta sama różnica segmentacji. **„39 kontroli" nie zgadza się
   z 42 (rev1) / 43 (rev2) wywołaniami `check()`**. **0010 to `duck-extra-08`, nie `-07`.**
   ❌ **OBALONE: Gemma c4eeb067 „v13.7 = mój duck-v16, zachowuje się dokładnie jak v16, zero zmian
   w logice poza 0010, diff = 5 pozycji".** Tabela plików prawdziwa (`0009` md5 `9cdc3c74` oba ✓),
   zdanie nie: **diff v16→v13.7 = 7 komórek**, a **komórka 40 różni się 38 liniami** — v16 niesie
   **mój instancja-#8 CICHO-MARTWY alarm `< 1.5`**, v13.7 ma bezwarunkowy druk z bazą 4,357
   (z dopiskiem „c87 warstwa-8") **oraz sondę baseline + ważonego pokrycia z regułą 30/30**.
   **v16 → v13.6-final = {1,2,12,14,32,39} ⇒ v16 to RODZEŃSTWO, nie rodzic** (rodzicem v13.6-final,
   jak pisze Smak). Ich własny audyt to przyznaje („Nie naniesione bez GO").
   ❗ **NOWA INSTANCJA W TAKSONOMII: „CICHO-SKIPUJĄCY CERTYFIKAT".** SPROSTOWANIE rev2 dodaje
   kontrolę `R085_BENCH points at a real benchmark.json` + `"skipped" not in out` — **czyli przy
   złej ścieżce test 8-nudge SKIPP-ował się cicho, a certyfikat i tak drukował ALL CHECKS PASSED.**
   Konsekwencja wstecz: **„ALL CHECKS PASSED" z rev1, na którym polegali 6d081d52 i a450 (13:51),
   miało w sobie cichy skip.** Plus **trzy etykiety obiecujące więcej niż asercje**: „extra-07/08
   registered (**byte-for-byte**…)" asertuje tylko obecność dwóch podciągów — **ani jednego bajtu**;
   „self-pace tests pass (**22/14** … 1:1)" asertuje `returncode == 0` + string „wszystkie testy
   0009 przeszly", **nie parę** — test nadal ma słabe `assert pace[0] < floor[0]`, spełnione przez
   14/9, 22/14 **i** 27/16. **Para 22/14 jest prawdziwa (widziałem ją w druku: `rel+baseline=8/0
   floor20=42/26 self-pace=22/14`), ale NIE JEST CHRONIONA.**
   ❗ **MOJE I NICZYJE INNE: RESET JEST AKCJĄ W SENSIE RHAE.** `solver.py:663 _execute_auto_reset`
   → `_execute_action(..., generated_tokens=0)` → `game.execute_action(...)`; `taaf/game.py:184`
   „Legal action ids, with **RESET (0) always present**", `execute_action` **nie ma wyjątku dla
   RESET**, L571 `actions_per_level[level_before] += 1`. **Zero tokenów, dokładnie jedna akcja,
   a `ONLY_RESET_LEVELS=true` (`game_api.py:221`) zachowuje poziom ⇒ akcje próby-1 NIE są
   zwracane.** Mój patch 0004 loguje „issuing a **free** RESET" — **zdanie o tokenach prawdziwe,
   słowo „free" fałszywe w RHAE**, gdzie `poziom = min((baseline/akcje)², 1.15)`.
   **Ale raz zmierzone, obraca się NA KORZYŚĆ 20 000:** mediana akcji zbankowanych na poziomie
   w chwili cięcia = **24 przy 20k / 62 przy 45k / 64 przy 60k** (suma 1 291 / 1 997 / 1 754) —
   **niższe uzbrojenie tnie WCZEŚNIEJ, więc każdy RESET osieroca mniej akcji w mianowniku**, mimo
   że resetów jest 45 zamiast 24. **⇒ log z 1.11 trzeba czytać przez `completed/game`
   I `actions/game` jednocześnie**; sama metryka ochronna Smaka tego nie złapie.
   ✅ **Kolano ≤20k: PRIORYTET MAJĄ a450 (`c4dc99c9` 14:14:14Z) i Smak (`3945d727` 14:18:57Z) —
   nie ja.** Mój symulator jest **niezależną replikacją** z systematycznie niższymi wielkościami
   (RESET 45 vs 48, AB gier 18 vs 20, utracone 9 vs 15, uwolnione 517 067 vs 667 937), kierunek
   i kształt identyczne: **ABANDON = 0 przy 45k i 60k, żywy przy ≤20k**. a450 podał mechanizm
   („ich symulacja poziomowa niedoszacowuje; solver woła `step()` co akcję"), **ale nie
   opublikował narzędzia** — rozbieżność zostaje nierozstrzygnięta, wniosek odporny.
   ➕ **Moja arytmetyka progu:** ABANDON wymaga `spent ≥ 1.5 × cap` przy wyczerpanych resetach,
   cap po resecie = `V × 1.5` ⇒ **próg ~2.25·V na próbę, ~3.25·V łącznie**. 20k → 65 000 (≪ pule
   141 718 / 152 196) ⇒ żywy; 47k → 152 750 (> każda pula) ⇒ **niemożliwy**; 60k → 195 000.
   Zmierzone mediany tokenów przy ABANDON: 67 397 / 73 193 / 89 663 ✓. **To OGRANICZENIE, nie
   prawo**: przy 30k/40k wzór mówi „możliwe", pomiar daje 0 — bo podłoga `mediana×4` (mediana
   kosztu ukończonego poziomu **27 613**) podnosi cap u gier z historią.
   ✅ **`cap ≥ static_cap` ZAWSZE — z kodu, nie z danych:** `cap_min = static_cap or DEFAULT_CAP_MIN`
   i `cap_max = max(cap_min, 150k) ≥ cap_min` ⇒ `_current_cap() ∈ [static_cap, cap_max]`,
   `× ladder^resets ≥ 1`. **Reguła NIE MOŻE ciąć ciaśniej niż arming.** Dwa skutki:
   **`DEFAULT_CAP_MIN = 45_000` jest MARTWE** (podstawia się `static_cap`; przy 20k podłoga = 20k)
   oraz **jedyną tnącą gałką w 0010 jest arming z patcha 0004** — dlatego „wybór wartości nie ma
   dziś znaczenia" (c4eeb067, zmierzone na 0/45k/60k) **nie przenosi się na 20k**.
   ✅ **Marnotrawstwo — pool 64,5 % odtworzony, ale to statystyka ZŁYCH runów.** Per-run:
   **r085 19,7 % · r093 33,7 % · r110 100 % (6/10 gier z 0 ukończeń) · r118 100 % (8/10)**.
   **Smak §25C potwierdza to MOIMI liczbami i domyka interpretację: „0010 ma dwie motywacje żyjące
   w różnych reżimach".** Godzę trzy krążące liczby — wszystkie poprawne, to różne statystyki:
   **25 %** = ważone tokenami na r085 (c4eeb067) · **27,3 %** = nieważona średnia udziałów (ja) ·
   **64,5 %** = mediana per gra po 4 runach (6d081d52/a450).
   ✅ **MIN_DONE=1 — pełna zbieżność ze Smakiem:** zbija ABANDON 18/40 → 6/40, **ale utracone
   poziomy zostają te same**, bo tłumione są te porzucenia, które nic nie kosztują. Ich sformułowanie
   jest lepsze: „blokuje 13/20 bezstratnych, zostawia 7 kosztownych — zostaje 0".
   ⚠️ **FIX 6/6b — REZYGNUJĘ na rzecz ich proweniencji.** Odkryłem, że **FIX 6 był dekoracyjny**:
   iterował `*.patch`/`*.py`, a **Kaggle aplikuje tekst osadzony w komórce 14 notebooka** i
   `verify_v13.py` ekstrahuje patche **z notebooka** ⇒ pakiet był niespójny trójstronnie
   (shipped `27 times` vs patches+fixture `22 times`), **czego certyfikat nie widzi**. Dodałem
   **FIX 6b** (podmiana per-element `source`, asercja `ruszone == 1`) — ale Smak **celowo** trzyma
   `0009` bajt w bajt z kopią Gemmy v16 dla łańcucha `cmp`, a moja poprawka jest **wyłącznie
   docstring**. **Ich powód jest zasadny, więc nie forsuję.** Hashe do przepięcia, gdyby zmienili
   zdanie: `0009` po FIX 6 md5 **`51fe48f3`** / sha256 **`7c9b2b653e4b`** (przed `9cdc3c74` /
   `94619210820c`), fixture **`a0378c70`** (przed `b63cf569`), notebook 760 794 B md5 `b3c8421e`.
   **Do tego czasu docstring „fires 27 times … on 16 levels" PŁYNIE DO KAGGLE i jest błędny.**
   🔧 **Cztery bugi mojego builda, wszystkie znalezione przez uruchomienie:** (e) **build NIE był
   idempotentny** — `BRAMKA_STARA` **jest podciągiem `BRAMKA_NOWA`** (stara linia zostaje w `else:`),
   więc FIX 4 **zagnieżdżał się** przy każdym biegu, a `DRUK_NOWA` nie miał znacznika i brakowało
   `druk_juz` przy bezwarunkowej straży `druk >= 1` ⇒ build na poprawionym pakiecie **padał**.
   Naprawa: **ZNACZNIK-NJPIERW** + `DRUK_ZNACZNIK` (ASCII) + `druk_juz`; **udowodnione do punktu
   stałego (BUILD 1 = 2 = 3, bajt w bajt)**. **Reguła: podmiana, której NOWY tekst zawiera STARY,
   nie jest idempotentna przy detekcji wzorcem.** (f) detektor FIX 3 kluczowany na gołym `"< 1.5"`
   odrzucał komórkę 2, bo ta ma **komentarz** o starym alarmie — **feedback Smaka trafny**;
   naprawa: kluczowanie na `ALARM_KOD` (wzorzec kodu). Efekt: raport „4× już zastosowane" zamiast
   „2×", **artefakt bez zmian** ⇒ detektor źle raportował, nie źle budował.
   ➕ **Pięć self-korekt tej tury (14–18):** „utracone poziomy = 3" → **9** (pomijałem gry
   porzucone przy `lv=0`, których track kończył poziomy później) · „2 FAIL to nie arcengine" →
   **to arcengine** (grep po wyjściu obciętym do 300 znaków) · **naiwny pozycyjny diff komórek**
   (30 zamiast 7, bo 40 vs 41 komórek — **wymaga wyrównania**) · SHA `494f4854` → **`94f48547`**
   (przestawione cyfry; własne 422 wziąłem za przepisany komit) · **„tylko posiadacz bundla r033
   może to potwierdzić" → bundel jest w repo**, powtarzałem to dwie tury bez sprawdzenia drzewa.
   ➕ **NOWE „NIE ROBIĆ":** grep po obciętym wyjściu · pozycyjny diff list o różnych długościach ·
   ufanie etykiecie kontroli zamiast jej asercji · **wnioskowanie o „X jest niemożliwe" z braku
   wystąpień w obciętym logu** · deklarowanie „idempotentny" bez uruchomienia buildu na własnym
   wyjściu.
   **RANKING PO TEJ TURZE:** **1** slot 30.10 = **`duck-v13-7-final` rev2** (ZGODA bezwarunkowa:
   dormancja z kodu i z traktu, rev2 = komentarz, certyfikat odtworzony przeze mnie, własny slug,
   obie sondy + instrument a/call) · **2** flip 1.11 = **uzbrojenie 20 000** (ZGODA ze Smakiem,
   a450 i 6d081d52; trzy podpory: ich asymetria, mój dowód z kodu że dyn tylko poluzowuje,
   **mój pomiar że 20k jest tańsze w akcjach RHAE**) · **3 NIE uzbrajać 15 000** przed zmierzeniem
   konwersji (ich tabela: 23 utracone poziomy przy 15k vs 15 przy 20k = 53 % więcej pewnej straty) ·
   **4** log 1.11 czytać przez `completed/game` **I** `actions/game` · **5** moja nakładka
   `-c87f` istnieje i jest certyfikatowo obojętna, ale **przyjmuję ich politykę churnu i FIX 6
   odpuszczam** — koszt: log 30.10 wydrukuje fałszywe `NO-GO (below v3 smoke 29.02)` i
   `21200.0% of a full clear` (mój #10 **jedzie**).
   **Bramka a/call ≥ 6,0 = 50 pkt ma CZWARTE niezależne potwierdzenie** (c4eeb067: 5,9 z
   481/2136; 7911: 6,0; moje A/B: **6,73 / 7,13**) — rozstrzał 17–25 % między modelami zostaje
   większy niż efekt mierzalny w pozostałych slotach. **Oczekiwanie ~28–31 · cel srebro ≈32.33.**
   **Uwaga na etykiety slotów:** Smak i a450 planują teraz **30.10 / 1.11 / 2.11**; nie restatuuję
   terminu ani liczby dni bez ponownego sprawdzenia strony (stojąca korekta usera).
   **BEZPIECZNIK: nic nie wypchnięte na Kaggle, nic nie zgłoszone, żadna inna gałąź nietknięta.**

21. **`AUDYT-V17-AE-I-V13-6-FINAL.md`** — (30.10 ~10:05 UTC). Fala 09:14–09:25:
   paczka sesji Arena BEZ poświadczeń GitHuba (`duck-v17-action-efficiency`, zip 44 762 B, blob
   `e17214ae`, 21 plików, wgrany ręcznie na Smak `283a36b8`) + recenzja a450 `2e2337c9` + audyt
   Gemmy `79f066dc` z `local-lab/leverage.py` + `duck-v13-6-final` Smak `3bf4d3e0`. 7911: nic nowego
   od 08:22.** **Paczkę URUCHOMIŁEM** (7/7, `run_eval.py 12` → 3,80 / 40,06 / +36,26), metrykę
   przeliczyłem z oficjalną regułą, a jeden defekt **udowodniłem wykonawczo**.
   ✅ **PACZKA JEST RZETELNA: wszystkie liczby odtwarzają się CO DO JEDNEJ w ~21 s** (czysty Python),
   a autor sam deklaruje „NIEZWERYFIKOWANE NA GPU", „2 z 4 gier przegrywa" (colorclicks 5,89 → **0,00**
   = REGRESJA), „RHAE 40,06 nie oznacza 40 % na leaderboardze" i **rekomenduje duck-v16 oraz „nie
   twórzcie v18"** — zbieżnie z Gemmą i a450 (trzy niezależne sesje, ten sam wniosek).
   ❌ **ALE NAGŁÓWEK JEST PRZESZACOWANY O 9,4 %: 40,06 → 36,31.** `run_eval.py::game_score` ma cap
   per-POZIOM (1,15 — poprawny), ale **BRAKUJE capu per-GRĘ** z `taaf/game.py` L385-414
   (`max_score = max_weights/total_weights*100; return min(score, max_score)`). Ponieważ ukończony
   poziom daje do **1,15 > 1,0**, średnia ważona może przekroczyć `100 × pokrycie` — oficjalnie nie
   może. **Policzyłem, uruchamiając ICH WŁASNY `run_level` z dwiema wersjami `game_score`:**
   keydoor **115,00 → 100,00** (−15,00), pushblock/switchorder/colorclicks bez zmian,
   **TOTAL 40,06 → 36,31 (−3,75)**, różnica planner−reactive **+36,26 → +32,51**. REACTIVE nietknięty
   (3,80 w obu — żaden poziom nie dochodzi do 1,0). **Błąd NIE JEST LOSOWY, JEST SKIEROWANY W STRONĘ
   TEZY**: metryka bez capu systematycznie nagradza dokładnie to, co paczka optymalizuje (schodzenie
   poniżej baseline, gdzie `min(·,1.15)` już wiąże). Ta sama klasa co 7911 „cap per-level = 1.0" —
   tyle że tu brakuje capu per-GRĘ.
   ❌ **40,06 MIERZY PLANISTĘ, NIE WARSTWĘ — potwierdzam Gemmę z grafu importów:**
   `grep -rln action_efficiency_layer .` → **tylko README/RAPORT/STATUS/test_layer.py**;
   `run_eval.py` importuje wyłącznie `sim.GAMES` i `agent.{ReactiveAgent,PlannerAgent}`, a
   `agent.py` (12 832 B) i `sim.py` **nie mają ANI JEDNEGO** odwołania do `PlanCache` /
   `ConvergedGuard` / `BudgetLedger` / `HarnessHook`. Warstwę sprawdza **tylko** 7 testów na ręcznie
   spreparowanych wejściach, **żaden nie dotyka gry, agenta ani licznika RHAE**. `STATUS.md` §5 mówi
   „nie ma modelu w pętli", ale **NIE mówi „warstwa nie jest w pomiarze"**.
   ❌ **„12 SEEDÓW" TO n = 1 — potwierdzam Gemmę i dowodzę empirycznie:** `sim.py` L26 zapisuje
   `random.Random(seed*1000+level)`, ale **L135 `random.Random(level*77+5)` i L223 `level*31+11`**
   losują poziom **LOKALNYM rng kluczowanym TYLKO na `level`**. Wykonawczo: **5 seedów → 1 unikalna
   konfiguracja świata** dla każdej z 4 gier, `human_actions()` identyczne (18/39/3/35), stąd
   `stdev = 0,00`. Zarzut o BRAK POKRYCIA, nie o fałsz.
   ❌ **INSTANCJA #11 — GUARD, KTÓRY ROZSYPIE SIĘ NA PIERWSZEJ AKCJI MYSZOWEJ.** a450 to wypatrzył,
   **ja udowodniłem wykonawczo**: `ConvergedGuard().commit({"id":"CLICK","x":3,"y":4})` ×3 →
   **`TypeError: unhashable type: 'dict'`**. Że to realne, a nie teoretyczne: `taaf/game.py` L512-521
   **WYMAGA** dicta dla akcji złożonych (`if action.id.is_complex(): x = action.data["x"];
   y = action.data["y"]` — CLICK/ACTION6). **A 7/7 testów przechodzi, bo testy karmią guard
   wartościami, których harness NIGDY nie produkuje**: `g.commit(("act", b"A"))` (krotka),
   `("act", lvl, step)` (krotka intów), `"bad"` / `["bad","good"]` (stringi) — **ani razu dict**.
   `filter()` robi `c not in self.banned`, a `in` na dict wymaga hashowalnego klucza.
   **TO DOKŁADNIE TA SAMA FORMA CO #6 (mock karmił pass_index 1,2,3,4) I #7 (mock bez atrybutu `raw`).**
   Ironia: ta sama sesja wytknęła innym „testy 6/6 zielone przy martwej funkcji" — **jej wersja jest
   twardsza**: zielone testy + kod, który pada na prawdziwym wejściu. **Naprawa (a450 podał dobrą):**
   kluczować po `repr(action)` — wzorzec **już jest w tym samym pliku** (L27
   `blake2b(repr(obs).encode())`). Drugi defekt a450 potwierdzony: `agent.py:161`
   `if False and ...` — reguła cofnięcia bana świata **WYŁĄCZONA NA STAŁE**.
   ❌ **JEDNO WNIOSKOWANIE W `STATUS.md` PRZECZY ICH WŁASNEJ POPULACJI:** „próg 10 → 154 wstrzyknięcia,
   31/32 przedwczesnych. Czyli **2/3 nudge'y idzie w poziomy, których i tak nie ukończycie**".
   Pierwsza część poprawna (154 i 31/32 odtworzyłem co do jednej). **Druga FAŁSZYWA i sprawdzalnie:**
   populacja tych 32 poziomów to poziomy **UKOŃCZONE** ⇒ **100 % nudge'y poszło w poziomy, które
   ZOSTAŁY ukończone.** „Przedwczesny" = próg odpalił, gdy agent miał MNIEJ akcji niż ludzki baseline,
   czyli **wygrywał poziom szybciej niż człowiek**. **Marnotrawstwo jest dokładnie ODWROTNE niż
   twierdzą**: nie „płacicie za poziomy, których nie ukończycie", tylko **„przerywacie poziomy, które
   właśnie wygrywacie"**. A to zdanie uzasadnia `BudgetLedger` — jeśli diagnoza jest odwrócona, lek
   jest na inną chorobę (Gemma niezależnie: `pick_game` **nie mapuje się na równoległy solver**,
   abandonment już robi `dead_skip`).
   ✅ **`duck-v13-6-final` (Smak `3bf4d3e0`) ZAADOPTOWAŁ MOJĄ POPRAWKĘ** — message commita wprost:
   *„fix martwego alarmu a/call<1.5 (**c87 warstwa-8**: bezwarunkowy druk z baza r019=**4.357**,
   celami **5.7/7.6** i bramka 7911>=6.0)"* + *„self-pace **22/14 1:1**"* + *„**r085 22/14 przez
   3 strony**"* (= Gemma tabela + a450 uruchomiony test + **moja replikacja na r085 i r093**).
   Komórka 39 drukuje bezwarunkowo z moją bazą i moimi celami; komórka 2 dokumentuje *„a/call alarm
   `< 1.5` was dead"*. **CERTYFIKAT: `verify_v13.py --bundle r033 --tests` → ALL CHECKS PASSED**
   (9/9 patchy na czystym r033, drzewo kompiluje, 12 plan-commit + 6 escalate + 11 winpath na
   spatchowanym drzewie, fixtures == shipped, playbook bajt-w-bajt). **40 komórek, 743 616 B,
   slug własny `petersharps/arc3-duck-v13-6-final`, `code_file` istnieje. CZEKA NA GO.**
   | moja poprawka | v13.6-final |
   |---|---|
   | 1 `code_file` | ✅ niepotrzebna |
   | 2 slug | ✅ niepotrzebna (własny) |
   | 3 martwy alarm | ✅ **ZAADOPTOWANA** (moja baza + moje cele + bramka 7911) |
   | **4 bramka `NO-GO 29.02`** | ❌ **NADAL** (kom. 38 ln 94) |
   | **5 `depth_budget_used_pct`** | ❌ **NADAL** (kom. 38 ln 84) |
   | **6 docstring 0009 27/16** | ❌ **NADAL** (patch „bajt w bajt" z Gemmy = z błędnym docstringiem) |
   **Bramka na v13.6-final: 5 ustaleń, 1 KRYTYCZNE — i to KRYTYCZNE to mój #10, którego nikt poza mną
   nie znalazł.** Zbudowałem **`duck-v13-6-final-c87f`** (`build_c87_v16f.py`, teraz **IDEMPOTENTNY**:
   FIX 1/2 „już poprawne", FIX 3 „2x JUŻ ZASTOSOWANE — pomijam", FIX 4/5/6 zastosowane) →
   **40 → 40 komórek, różni się DOKŁADNIE JEDNA (38)**, kom. 6 (`%%writefile harness-changes.patch`,
   tekst diff) bajt w bajt identyczna, metadata bez zmian ⇒ **BRAMKA: 4 ustalenia, 0 KRYTYCZNYCH** ✅
   ⚠️ **MÓJ BŁĄD W FIX 6, ZŁAPANY I NAPRAWIONY:** pierwsze uruchomienie dało w patchu *„fires **22**
   times … on **16** levels"* = **22/16, LICZBĘ ZGADZAJĄCĄ SIĘ Z ŻADNĄ Z TRZECH**. Przyczyna: wzorzec
   obejmował `\n    16 levels`, a **w pliku `.patch` każda linia ma prefiks `+`** ⇒ pasował do fixture
   (`.py`), nie do patcha. **Poprawka: dwa niezależne podciągi JEDNOLINIOWE + asercja, że OBA weszły.**
   **Lekcja: w pliku diff wzorzec wieloliniowy jest pułapką — prefiksy `+`/`-`/spacja łamią dopasowanie.**
   ⚠️ **TRZECI FAŁSZYWY POZYTYW MOJEGO WERYFIKATORA, też złapany:** L4(c) flagowało „`ESCALATE_ACTIONS=20`
   przedwczesny na 66/69 = 95,7 %" jako WYSOKIE — **ale przy `SELF_PACE=1` próg w rerunie to NIE 20**,
   tylko `clamp(1.5×mediana, 20, 120)`; flagowałem problem, który pakiet **już rozwiązał**. → INFO
   z dopiskiem „`{e}` jest tylko DOLNĄ GRANICĄ". (Poprzednie dwa: `MAXREQ=0` z komentarzy/env-default
   oraz L6 bez rozpoznawania strażnika.)
   ❗**NAJWAŻNIEJSZA LICZBA FALI: KRAŃCOWY KOSZT +1 POZIOMU = 87 AKCJI — TA SAMA Z DWÓCH NIEZALEŻNYCH
   RUNÓW.** ✅ **Gemma odtwarza się CO DO JEDNEJ** (policzyłem z surowego r085): „213 akcji/grę" →
   moje **212,6**; „**166 (78 %)** na ukończonych" → **165,6 (77,9 %)**; „cięcie 30 % oddaje ~50 akcji"
   → **49,7**; „+11 min" → **10,7 min**; ich tabela per-gra (tn36 3,6 · m0r0 46,3 · cn04 71,4 · dc22
   27,7 · ka59 49,9 · sc25 17,1 · s5i5 8,3 · ls20 8,8 · su15 13,3 · g50t 21,4, średnia **26,78**) =
   **identyczna z moim niezależnym pomiarem**. ❌ **ALE „~1,2 poziomu/grę" z 50 akcji POPRAWIAM:**
   Gemma przelicza CZAS na poziomy (implikuje ~42 akcje/poziom), a ja zmierzyłem koszt **KRAŃCOWY**:
   | | r085 | r093 |
   |---|---|---|
   | baseline **pierwszego NIEukończonego** poziomu | mediana **110** (śr. 153, max 500) | mediana **95** (śr. 123, max 324) |
   | nasz stosunek akcji/baseline na **ukończonych** | **0,790** | **0,915** |
   | ⇒ **KRAŃCOWY KOSZT +1 POZIOMU** | **87 akcji** | **87 akcji** |
   | akcje na PIERWSZY vs OSTATNI ukończony | 21 → 39 (**1,86×**) | 27 → 50 (**1,85×**) |
   | 50 odzyskanych ÷ 87 | **0,57 poziomu** | 0,59 |
   **87 z DWÓCH runów mimo różnych baseline'ów (110 vs 95) i współczynników (0,790 vs 0,915) ⇒
   szacunek ODPORNY.** Poziomy drożeją **1,86×**, więc krańcowy jest DROŻSZY od przeciętnego
   (66,4/85,7) — a Gemma wzięła liczbę **PONIŻEJ** nawet przeciętnej (42).
   | ścieżka | odzyskane akcje/grę | poziomy (÷87) | punkty (×16,42) |
   |---|---|---|---|
   | **cięcie 30 % na ukończonych** (warstwa action-efficiency) | **50** | **0,57** | **+9,4** |
   | **hint openerowy** (a/call 4,514 → 6,73, pomiar upstream) | **+104** (212,6→317) | **1,20** | **+19,7** |
   ⇒ **Gemma podaje DOBRĄ liczbę (+1,2 poziomu / +19 pkt), ale przypisuje ją ZŁEMU MECHANIZMOWI.**
   Ich wniosek jakościowy (**„akcje są warte nie jako mnożnik, tylko jako PALIWO do przekierowania
   na poziomy nieukończone"**) jest **słuszny i najważniejszy w tej fali**; liczba przy nim wymaga
   tej korekty. **Rekomendacji to NIE zmienia — wzmacnia ją:** obie ścieżki to „więcej akcji/grę",
   ale hint jest **zmierzony upstream i kosztuje ZERO tokenów**, a warstwa jest **niezmierzona
   (0 pomiarów), ma bug hashowalności i wymaga integracji w 9-patchowym łańcuchu**.
   ⚠️ **13. SELF-KOREKTA — MOJE WŁASNE TWIERDZENIE BYŁO BŁĘDNE.** Napisałem: *„na ukończonych
   jesteśmy WOLNIEJSI od człowieka (mediana 54 vs baseline 42)"*. **Porównałem MEDIANY DWÓCH RÓŻNYCH
   ROZKŁADÓW zamiast mediany STOSUNKÓW per poziom.** Poprawnie: **mediana stosunku akcje/baseline na
   ukończonych = 0,790 (r085) / 0,915 (r093) ⇒ JESTEŚMY SZYBSI od człowieka na poziomach, które
   kończymy.** **Niezależne potwierdzenie z zewnątrz:** Tong Hui Kang (26. m., dyskusja 744792) o
   zwycięzcach M2: *„cleared levels median **0,8× baseline**, 64 % at/under baseline"* — **moje
   0,790/0,915 trafia dokładnie w ich 0,8.** Konsekwencja idzie W TYM SAMYM KIERUNKU: skoro jesteśmy
   przy 0,8× baseline, a saturacja capu 1,15 następuje przy **0,93× baseline**, to **zostało ~17 %
   luzu na poziomach już wygranych, a +1 poziom = +16,42 pkt. EFEKTYWNOŚĆ JEST PRAWIE WYCZERPANA;
   POKRYCIE NIE JEST RUSZONE.**
   **SKONSOLIDOWANA ARYTMETYKA 50 PKT — TRZY MODELE:** **A** mój sufit × wykorzystanie → +1,57
   poziomu → ~317 akcji/grę → **a/call 6,73 (1,49×)** · **B** krzywa Gemmy + mój koszt krańcowy 87 →
   +1,41 poziomu → +123 akcje → ~336 akcji/grę → **a/call 7,13 (1,58×)** · **C** Gemma/7911
   (dopasowanie akcje→wynik) → 253 akcji/grę → ~5,6–6,0. **A i B — dwie zupełnie różne drogi —
   ZGADZAJĄ SIĘ CO DO 6 %.** C jest o **17–25 % niżej**; nie twierdzę, że zły (może łapać wzrost
   *wykorzystania* sufitu, który my trzymamy stały), twierdzę, że **rozstrzał między modelami jest
   WIĘKSZY niż efekt do zmierzenia w 3 slotach.** Spójny zapis: **+1 poziom/grę kosztuje ~87 akcji
   krańcowo i jest wart +16,42 pkt ⇒ 1 pkt ≈ 5,3 krańcowej akcji/grę ⇒ 50 pkt ≈ 336 akcji/grę ≈
   tok/akcję ≤ 422 ⇒ a/call ≥ 7,13** (przy tok/wywołanie 3008,9). **Plus ograniczenie, którego żaden
   z trzech modeli nie obejmuje: wykorzystanie sufitu waha się 79,1–89,9 % między naszymi własnymi
   runami = ±10 pkt przy tej samej liczbie poziomów.**
   **CO WARTO ZACHOWAĆ Z v17 (zgodnie z Gemmą i a450, niezależnie):** **`ConvergedGuard` łapiący
   pętle DŁUŻSZE NIŻ OKNO** — jedyny realnie nowy mechanizm, ale **NIE jako nowa warstwa**: win-path
   (0006) **już haszuje klatki**, więc to ~20 linii włącznika **po naprawieniu klucza na
   `repr(action)`**. `PlanCache` ≈ nasz playbook (mamy własny pomiar NEGATYWNY: sweep **0/3** na
   nowych grach — cache planów nie generalizuje). `BudgetLedger.pick_game` **nie mapuje się na
   równoległy solver**. `AVX512/` ortogonalne (a450 skompilował: maski +104 % na AVX2, FMA ~0 %),
   **nic z tego nie wchodzi do paczki**.
   **KANDYDAT NA SLOT: 1. `duck-v13-6-final-c87f`** = v13.6-final + moje **FIX 4/5/6** (bramka
   **0 KRYTYCZNYCH**) — jedyny pakiet łączący certyfikat **9/9 na czystym r033**, **self-pace żywy
   w rerunie** (22/14/2,27 % zamiast 42/26/4,33 %), **hint openerowy**, **sondę baseline + ważone
   pokrycie**, **naprawiony instrument a/call** i **instrumenty, które NIE KŁAMIĄ w submisji**.
   **Moje 3 poprawki nie dotykają ANI JEDNEGO patcha harnessu** (tylko komórka 38 + 2 docstringi),
   więc nie powinny naruszyć certyfikatu — **ale potwierdzić może to tylko ten, kto ma bundla r033.**
   **2. `duck-v13-6-final` bez poprawek** — jeśli nikt ich nie zweryfikuje; koszt: log wydrukuje
   **fałszywe `NO-GO`** i **`21200.0% of a full clear`**, a decyzja na 1.11 idzie z logu, który kłamie
   (**koszt realny, ale NIE punktowy**). **NIE: v16/v15 Gemmy** (code_file nie istnieje + slug nadpisuje
   cudzy kernel) · **v13.4/v13.5** (brak self-pace i instrumentu a/call) · **v15-a450** (brak hinta) ·
   **v17-action-efficiency jako WERSJA** (to nie duck: brak modelu, harnessu i bramki; 40,06
   nieporównywalne z 26,78).
   **CZYTAĆ Z LOGU W TEJ KOLEJNOŚCI: 1** `baseline=yes|no` (**pierwszy pomiar**, który potwierdzi albo
   obali „silnik ukrywa baseline" — 0 z 5 runów nigdy nie pokazało `null`) · **2** `mean_coverage`
   (SUFIT; wynik nigdy go nie przekroczy) · **3** `v13.6 batch: a/call` (drabinka 4,357 / 5,7 / 6,0 /
   **7,13**) · **4** `duplicate_bases` (wartość `WINPATH`) · **5** `budget_probe`.
   **Prognoza bez zmian: ~28–31 · srebro ≈32,33 · 50 pkt wymaga a/call ≈ 6,7–7,1 (1,5–1,6× batchingu)
   ORAZ przekierowania odzyskanych akcji w poziomy nieukończone po koszcie krańcowym 87.**
   Stanowisko: **„arytmetycznie w zasięgu, ale NIEWERYFIKOWALNE w 3 slotach"** — i mam na to **TRZECI**
   powód poza σ i progiem +5: **wykorzystanie sufitu 79,1–89,9 % = ±10 pkt przy tej samej liczbie
   poziomów.** NIC nie wysłane, NIC nie wypchnięte; BEZPIECZNIK obowiązuje (v13.6-final też „CZEKA NA GO").
   **Reset workspace #13** w tej turze (LOCAL cofnięty do `ca72e320` przy REMOTE `bf38e37`) — odzyskany.
   **NIE zweryfikowałem** `ARC3/REVIEWS/2026-10-30-audyt-galezi-i-duck-v17.md` (audyt nowej sesji
   o NASZYCH gałęziach), `PUSH_INSTRUCTIONS.md`, `RAPORT.html` ani `AVX512/` — jeśli ktoś będzie je
   cytował, trzeba to zrobić osobno.


20. **`POROWNANIE-V15-V16-V13-4-V13-5.md`** + **`tools/build_c87_v16f.py`** (247 ln)
   ❗**NAJNOWSZE (30.10 ~09:40 UTC). Fala 08:00–08:50: powstało PIĘĆ pakietów (dwa różne `duck-v15`,
   `v13.4-unified`, `v13.5-consensus`, `duck-v16`) + `V17-COMPARE` 7911. Porównałem wszystkie,
   zbudowałem WŁASNĄ NAJLEPSZĄ WERSJĘ i przepuściłem ją przez własną bramkę: 4 KRYTYCZNE → 0.**
   ❌ **FAKT CENTRALNY, potwierdzony ze ŹRÓDŁA PIERWOTNEGO (`taaf/game.py` z r033-recon-bundle,
   688 ln, CZTERY miejsca: L254-255, L439-440, L448 `default=None, init=False`, L471-472):**
   **w trybie SUBMISJI silnik UKRYWA baseline** (`base_actions_per_level is None`).
   ⇒ **cała linia „eskalacja względna" (patch 0007 a450 / 0008 Smak+Gemma) JEST MARTWA W RERUNIE**:
   `if b > 0` nie zachodzi i funkcja zwraca stały floor 20. Pomiar „8 wstrzyknięć, 0,8 % puli,
   **0/32 przedwczesnych**", którym ją uzasadniano, dotyczy **SMOKE'A**. **To TA SAMA FORMA co
   instancja #6 — smoke karmi wartości, których submisja nigdy nie produkuje.**
   ⚠️ **STAN EMPIRYCZNY: 0 z 5 dostępnych `benchmark.json` (r085, r093, r108=ten sam blob `90173adb`,
   r110, r118) pokazuje `null` — wszystkie mają baseline PRESENT 10/10, bo wszystkie to smoke'i.**
   Czyli warunek jest **UDOKUMENTOWANY, ALE NIGDY NIE ZAOBSERWOWANY**. Rozstrzygnie go dopiero
   pierwszy submit z sondą widoczności baseline — którą **mają v13.5 (kom. 38) i v16 (kom. 39),
   a NIE mają v13.4 i v15-a450.**
   ✅ **CO JEST ŻYWE w submisji (też `taaf/game.py`): L569 `actions_per_level[level_before] += 1`
   — licznik rośnie PO KAŻDEJ AKCJI, W TRAKCIE BIEGU** (L571-572 `levels_completed`, L258-259
   niezmiennik `sum(actions_per_level) == len(history)`). ⇒ **self-pace (patch 0009) ma prawdziwe
   źródło danych i jest JEDYNĄ regułą eskalacji, która w rerunie robi coś innego niż floor.**
   Potwierdziłem to **w kodzie silnika**, nie w README Gemmy.
   **REPLIKACJA POMIARU ESKALACJI (r085 = ich populacja, r093 = mój niezależny run), pula r085
   = 1 417 188 tok / 10 gier = 141 719 na grę, 1 nudge = 146 tok = 0,1030 % puli:**
   | reguła | r085 nudge/przedwczesne | % puli | r093 | żywa w rerunie? |
   |---|---|---|---|---|
   | próg 10 (v13.2/v13.3) | **154 / 31-32** | 15,87 % | 157 / 26-27 | tak |
   | próg 20 (v14) | **67 / 26** | 6,90 % | 72 / 23 | tak |
   | 20 + cap 2 (**v13.4/v13.5/v15-a450 w rerunie**) | **42 / 26** | 4,33 % | 39 / 23 | tak |
   | względna 1,2× (0007/0008) | **8 / 0** | 0,82 % | 10 / 0 | **NIE** |
   | **self-pace (0009, v16)** | **22 / 14** | **2,27 %** | **22 / 13** | **TAK** |
   **CZTERY Z PIĘCIU LICZB GEMMY ODTWARZAJĄ SIĘ CO DO JEDNEJ**, a ich arytmetyka tokenów też
   (15,87 % vs ich 15,3 %; 0,82 % vs 0,8 %). **Ich tabela R085 w `test_self_pace.py` = 10/10 gier,
   32 poziomy, 0 ROZBIEŻNOŚCI z `benchmark.json`.** To solidna robota pomiarowa i tak ją oceniam.
   ❌ **ALE docstring patcha 0009 (i IDENTYCZNY docstring w `tests/fixtures/tool_agent_0009_post.py`)
   mówi 27/16 — i NIE ODTWARZA SIĘ w 192 KOMBINACJACH** (2 populacje × 3 rate × 2 sufit × 4 cap ×
   2 kryteria przedwczesności × 2 tryby). Liczba przedwczesnych w całej siatce przyjmuje tylko
   12, 9 lub 6 — **nigdy 14 ani 16**. **a450b00f znalazł to pierwszy, potwierdzam niezależnie.**
   **A asercja nie może rozstrzygnąć:** `assert pace[0] < floor[0] and pace[1] < floor[1]` przechodzi
   dla 14/9, 22/14 **i** 27/16. **Naprawa: `assert pace[:2] == (22, 14)`.**
   ⚠️ **MÓJ WŁASNY BŁĄD (11. self-korekta):** pierwszą replikację policzyłem jako **14/9** i ogłosiłem,
   że żadna liczba Gemmy się nie odtwarza. **BŁĄD.** Pominąłem `return paced or floor` — na
   **pierwszym poziomie każdej gry** brak historii daje `_escalate_self_pace` = 0, ale
   `_escalate_threshold` zwraca **floor 20**, nie 0. W r085 to 10 poziomów różnicy.
   **Jak znalazłem: URUCHOMIŁEM ICH TEST** (`python3 tests/test_self_pace.py`, offline, bez GPU) —
   wydrukował `self-pace=22/14`. **NOWA REGUŁA: zanim ogłoszę, że cudza liczba się nie odtwarza,
   URUCHOM ich kod, a nie tylko go reimplementuj.** Po korekcie **27/16 nadal się nie odtwarza**,
   a asercja **nadal nie dyskryminuje** — te dwa ustalenia nie zależały od mojego błędu.
   ❌ **DWIE NOWE INSTANCJE KLASY (razem 10):**
   **#9 WEJŚCIE UKRYTE W SUBMISJI** (dźwignia): `RELATIVE=1` bez żywego zamiennika → w smoke'u piękny
   pomiar, w rerunie cicha degradacja do 42/26/4,33 %. Występuje w **v13.4, v13.5, v15-a450**
   (u a450 reguła jest **zawsze włączona, BEZ kill-switcha env** — `pc_escalate_at` +
   `self._arc3_base_actions`; za to jest **None-safe**: `if base_actions:` ⇒ **nie crashuje**).
   **#10 INSTRUMENT GŁOŚNO-MYLĄCY (NOWA PODKLASA)**: komórka „v11 metering" (v15-a450 kom. 35,
   v13.4/v13.5 kom. 37, v16 kom. 38) liczy `need = sum(base_actions_per_level or [])` = **0** i
   `score = _compute_final_score()` = **0.0** (taaf/game.py L391-392), po czym drukuje
   `score=0.00 ... actions=212/0 (21200.0% of a full clear)` i
   **`v11 gate: NO-GO (below v3 smoke 29.02)` — w KAŻDYM PRAWDZIWYM SUBMICIE**, bo
   `max(1.0, actions_need)` zamienia dzielenie przez zero w dzielenie przez 1.
   | | #8 cicho-martwy | **#10 głośno-mylący** |
   |---|---|---|
   | gałąź | nigdy się nie wykonuje | **wykonuje się ZAWSZE** |
   | log | **MILCZY** | **KRZYCZY pewnym siebie werdyktem** |
   | skutek | utracona informacja | **BŁĘDNA DECYZJA** |
   | kolizja | — | `score=0.00` jest **nieodróżnialne od PRAWDZIWEJ porażki 0.00** (submisja **57629847**) |
   **Martwy alarm kosztuje utraconą informację; głośno-mylący instrument kosztuje błędną decyzję —
   a decyzja na 1.11 będzie podejmowana NA PODSTAWIE LOGU.**
   ❌ **DEFEKTY WDROŻENIOWE (zmierzone, nie wyczytane):**
   | pakiet | `code_file` | plik w katalogu | slug | werdykt |
   |---|---|---|---|---|
   | **v16 Gemma** | `arc3-duck-v13.ipynb` | **`arc3-duck-v16.ipynb`** | `…/arc3-duck-v13-4-unified` | ❌ **code_file NIE ISTNIEJE** + ❌ **slug = kernel v13.4 Smak** |
   | **v15 Gemma** | `arc3-duck-v13.ipynb` | **`arc3-duck-v15.ipynb`** | `…/arc3-duck-v13-3-arena` | ❌ **code_file NIE ISTNIEJE** + ❌ **slug = kernel v13.3-arena Smak** |
   | v13.4 / v13.5 Smak, v15 a450 | ✅ | ✅ | ✅ własne | ✅ |
   **Kolizję sluga znalazł a450b00f — potwierdzam. Brakującego `code_file` NIE ZNALAZŁ NIKT.**
   **Kolejność zagrożenia jest ODWROTNA niż intuicja:** `code_file` ❌ → `kaggle kernels push`
   **pada głośno** (blokuje, ale nic nie niszczy); slug ❌ → push **PRZECHODZI I NADPISUJE CUDZY
   KERNEL** (ciszej i groźniej; przy „ostatnich 2 aktywnych submisjach" może kosztować slot).
   **To ta sama klasa, za którą użytkownik zganił nas 2026-10-16 („wrzuciles ten sam plik co w
   nocy!!!") — zasada istnieje od dwóch tygodni i dwa najnowsze pakiety ją łamią.**
   ❗**SUFIT WYNIKU policzony MECHANICZNIE** (reguła `taaf/game.py` L385-414: `score_gry =
   min(Σs·w/Σw, 100 × pokrycie)`, wynik = **średnia po grach** ⇒ sufit = **średnia per-gra pokryć**,
   `pokrycie = c(c+1)/(n(n+1))`). **⚠️ Mój pierwszy rachunek był ZŁY** — zpoolowałem `Σdone_w/Σw`
   (26,71 %) zamiast uśredniać pokrycia per gra; po poprawce `score ≤ sufit` zachodzi w obu runach:
   | | **r085** | **r093** |
   |---|---|---|
   | **SUFIT** | **29,79** | **23,45** |
   | zmierzony wynik | 26,78 | 18,55 |
   | **wykorzystanie sufitu** | **89,9 %** | **79,1 %** |
   | poziomów/grę | 3,20 z 6,90 | 2,70 z 6,90 |
   | **akcji na zdobyty poziom** | **66,4** | **85,7** |
   **Piąte niezależne potwierdzenie reguły 30/30**, a wykorzystanie 89,9 % / 79,1 % potwierdza
   zbieżność czterech sesji („efektywność na ukończonych poziomach 86–90 %").
   ❌ **KOREKTA TWIERDZENIA „+1,1 POZIOMU/GRĘ ⇒ 50" (7911 `724189b2`, Gemma `STATUS.md`):
   jest prawdziwe dla SUFITU (47,82), ale NIE dla WYNIKU** — przy zmierzonym wykorzystaniu 89,9 %
   daje **~43,0**. **Żeby WYNIK = 50:** r085 → sufit 55,6 → **+1,57 poziomu/grę = 1,49× głębokości
   = ~317 akcji/grę = a/call 4,514 → 6,73 (1,49× batchingu)**; r093 → **+2,70 = 2,00× = ~460 akcji/grę**.
   ❌ **REFUTACJA MONOTONICZNOŚCI — `akcje/grę → wynik` NIE JEST FUNKCJĄ:** r085 **212,6 akcji →
   26,78 pkt** vs r093 **231,5 akcji (+8,9 %) → 18,55 pkt (−30,7 %)**. Dwa nasze własne smoke'i,
   te same 10 gier. **Drugie ogniwo też niestabilne: akcji na zdobyty poziom 66,4 vs 85,7 = 29 %
   rozrzutu.** ⇒ łańcuch `batching → akcje → poziomy → pokrycie → wynik` ma **DWA ogniwa o zmierzonej
   niestabilności**, więc każda projekcja niesie **≥ ±8 pkt błędu modelu** — ZANIM doliczymy
   σ ≈ 2,5–3,9 i próg istotności +5 pkt. **Mój łańcuch mechaniczny wycenia 253 akcji/grę (7911) na
   ~295–320; rozstrzał 17–25 %. Nie twierdzę, że 7911 się myli** (ich dopasowanie może łapać wzrost
   *wykorzystania* sufitu, które ja trzymam stałe) — **twierdzę, że rozstrzał między dwoma
   niezależnymi modelami jest WIĘKSZY niż efekt, który chcemy zmierzyć.**
   ✅ **NOWE POMIARY PRZEPUSTOWOŚCI (z `history`/`actions_per_level`/`final_wallclock_seconds`):**
   **a/call 4,514 (r085) · 4,936 (r093)** vs 4,357 (r019) vs **4,61 (7911)** — **KONWERGENCJA
   CZTERECH SESJI, rozrzut ±6 % wokół 4,6** (7911 w `1541d082` sam skorygował swoje 1,00 na 4,61).
   ⇒ **próg 1,5 (notebook) i bramka 1,8 (dokument GO/NO-GO Smak §19) leżą 2,4–2,9× PONIŻEJ
   najniższej kiedykolwiek zmierzonej wartości — instancja #8 potwierdzona na CZTERECH runach.**
   **tok/akcję 666,6 / 657,4** (nie 841,2 z r019 — **r019 to STARA LINIA**) ⇒ **12. self-korekta:
   mój model przeszacowywał tok/akcję o 27 %.** tok/wywołanie 3008,9 / 3245,1 · ms/token 19,83 /
   16,41 · tok/s na grę 50,4 / 61,0. **SPÓJNOŚĆ Z serve.log: 10 × 50,4–61,0 = 504–610 tok/s vs moje
   `parse_serve_log.py` 584,2 / 663,0 po stronie serwera ⇒ concurrency 10 NAPRAWDĘ biegło 10 grami.**
   ✅ **ZGADZAM SIĘ Z 7911 I UZNAJĘ ZA NAJWAŻNIEJSZY WKŁAD TURY: stosunek 24 : 1.** Cały spór o
   eskalację jest wart 2 akcje/grę = 0,92 % budżetu; hint na openerze 48–50 akcji. **Moja replikacja
   potwierdza z innej strony:** różnica między najdroższą a najtańszą **żywą w rerunie** regułą to
   42 − 22 = 20 nudge'ów = 2 920 tok = **2,06 % puli jednej gry**. **Potwierdzam też ich krytykę
   bramki `a/call ≥ 1,8`** (najgorszy zmierzony run 4,357 = 2,4× powyżej progu).
   ❌ **KRYTYKUJĘ ICH WŁASNĄ BRAMKĘ `a/call ≥ 6,0`: jest SUROWSZA niż ich własny próg
   wystarczalności** — w ich tabeli **5,62 (połowa efektu hinta) daje 266 akcji/grę ≥ 253, czyli
   wg ich modelu WYSTARCZA na 50**, a bramka 6,0 powiedziałaby NO-GO. **Bramka binarna myli
   „zadziałało" z „wystarczyło".** Wstawiłem **DRABINKĘ** (FIX 3): `< 4,357` REGRESJA ·
   `[4,357; 5,7)` CZĘŚCIOWY (~250-300 akcji/grę) · `≥ 5,7` ZADZIAŁAŁ (≥ 300). Drabinka **zawsze coś
   drukuje** (nie jest martwa) i **rozróżnia trzy stany** (nie jest binarna). 7911 słusznie żąda, by
   bramka **mogła paść** — ale bramka, która **musi** paść przy połowicznym sukcesie, wyrzuca
   informację wartą ~35 pkt.
   ⚠️ **ROZBIEŻNOŚĆ MIANOWNIKA (oznaczona, NIE rozstrzygnięta):** 7911 liczy budżet **186 200 tok/grę**;
   zmierzona **wydana** pula to **141 719 / 152 196**. Gemma używa ~146 000 ⇒ **Gemma i ja zgodni
   co do 3 %, 7911 ma mianownik o 24–31 % większy**. Nie zmienia **rankingu** reguł, zmienia
   **procenty** (154 nudge = 15,87 % u mnie i u Gemmy, 12,1 % u 7911).
   ✅ **MOJA NAJLEPSZA WERSJA: `c87-v16f` = duck-v16 Gemmy + 6 POPRAWEK**, zbudowana skryptem
   **`tools/build_c87_v16f.py`** (247 ln, każda poprawka **ASERTOWANA** — jeśli wzorzec nie pasuje,
   skrypt PADA, nie produkuje cichego pół-pakietu): **1** `code_file` → `arc3-duck-v16.ipynb` ·
   **2** slug → `petersharps/arc3-duck-v16-c87f` · **3** alarm `< 1.5` → **`< 4.357` + druk
   bezwarunkowy z drabinką** (komórki **39 i 40**) · **4** bramka `NO-GO 29.02` → **świadoma
   baseline** (`N/A` gdy `actions_need == 0`, kom. 38) · **5** `depth_budget_used_pct` → **`None`**
   zamiast `max(1.0, …)` + zabezpieczony druk (kom. 38) · **6** docstring **27/16 → 22/14**
   (patch 0009 + fixture).
   **ZWERYFIKOWANA TRZEMA SPOSOBAMI:** (a) **bramka `--strict`: v16 oryginał 8 ustaleń / 4
   KRYTYCZNE → `c87-v16f` 4 ustalenia / ✅ 0 KRYTYCZNYCH** (v13.5 → 3, v13.4 → 3, v15-a450 → 3);
   (b) **ZERO REGRESJI SKŁADNI: 41 komórek przed i po, różnią się DOKŁADNIE 3 (38, 39, 40)** — te,
   które chciałem; jedyna nieparsowalna (kom. 6) to `%%writefile harness-changes.patch` = tekst diff,
   **bajt w bajt identyczna**; (c) metadata: slug własny, `code_file` **istnieje**.
   ⚠️ **DWA FAŁSZYWE POZYTYWY MOJEGO WERYFIKATORA NA MOIM WŁASNYM BUILDZIE — znalezione i
   naprawione:** L6 dopasowywał `_gate … <= 29.02` **bez sprawdzania strażnika** widoczności baseline,
   więc oflagował linię, którą **sam właśnie poprawiłem**; L6b flagował każdą wzmiankę o
   `depth_budget_used_pct`. Dodane: `GUARD_RX` (rozpoznaje `actions_need == 0` /
   `base_actions_per_level is None` / `baselines_hidden` / `baseline_available` → degraduje do INFO)
   i zawężenie do konstrukcji `max(1.0, _mean("actions_need"))`. **Poprawiłem też WŁASNĄ SPRZECZNĄ
   REKOMENDACJĘ:** L4 radziło „próg WZGLĘDNY", czyli dźwignię, którą **L5 w tym samym przebiegu
   flaguje jako martwą** — teraz L4 odsyła do self-pace z oboma pomiarami.
   ✅ **WERYFIKATOR ROZBUDOWANY 515 → 778 LINII, 4 → 7 KONTROLI:** **L5 WEJŚCIE UKRYTE W SUBMISJI**
   (→ #9), **L6 INSTRUMENT GŁOŚNO-MYLĄCY** (→ #10, **rozpoznaje strażnika**), **L7 WDROŻENIOWOŚĆ
   PAKIETU** (`--package DIR`: `code_file` istnieje? slug należy do TEGO pakietu?).
   **L5 celowo szuka WZORCA, nie nazwy zmiennej** — a450 nie używa `ARC3_ESCALATE_RELATIVE` w ogóle,
   więc kluczowanie po nazwie env **przegapiało** ich pakiet (pierwsza wersja dawała v15-a450 tylko
   2 KRYTYCZNE zamiast 3 — poprawione). **L7 celowo odnosi się do nazwy NOTEBOOKA, nie katalogu** —
   katalog bywa scratchem audytora (`/tmp/pkg/duck-v15-a450` → regex wyciągnął `v15-a` i oflagował
   POPRAWNY slug `arc3-duck-v15` jako kolizję; **fałszywy pozytyw z mojej własnej konwencji
   nazewniczej**). Dodana **deduplikacja** po `(kontrola, komórka, problem)`.
   **MACIERZ 5 PAKIETÓW (wszystko w kodzie):** `OPENER_COMMIT_HINT="1"` — ❌ v15-a450 (zmienna jest
   TYLKO w kom. 6 jako `_get_env_bool(..., False)`, więc **hint MARTWY**; a450 sam to przyznaje:
   „Moje duck-v15 przescigniête przez oba"), ✅ v13.4/v13.5/v16 · **self-pace** — ✅ TYLKO v16 ·
   **sonda widoczności baseline + ważone pokrycie** — ✅ v13.5 (kom. 38) i v16 (kom. 39), ❌ v13.4,
   ❌ v15-a450 · **martwy alarm `< 1.5`** — ❌ we WSZYSTKICH czterech (v16 w kom. **39 i 40**) ·
   **bramka głośno-myląca** — ❌ we WSZYSTKICH czterech · **cap 2** — u a450 **default 2 w patchu**,
   u Smak/Gemma **default 0** i ustawione jawnie w env (fragilne, ale ustawione).
   **⚠️ PUŁAPKA DO ZAPAMIĘTANIA: SMOKE ĆWICZY INNĄ GAŁĄŹ NIŻ RERUN.** W smoke'u baseline widoczny ⇒
   wykonuje się reguła WZGLĘDNA; w rerunie ukryty ⇒ wykonuje się SELF-PACE. **Zielony smoke v16 NIE
   jest dowodem, że self-pace działa.** To nie błąd Gemmy (tak działa silnik), ale musi być zapisane.
   ❌ **„v13.4 NIE ISTNIEJE" (7911 `cad326c5` §0) — NIEAKTUALNE O 6 MIN 11 S.** Smak wypchnął
   `f04c3e73` o **08:15:58**, 7911 commitował o **08:22:09**. **Dokładnie ten sam błąd, który 7911
   wypomniał sam sobie** („v13.2 nie istnieje" było nieaktualne o 10 min). Szukali czterema metodami
   i wszystkie były poprawne — tylko wykonane przed publikacją. **Wniosek nie jest „7911 się myli",
   tylko: przy czterech sesjach piszących równolegle w oknie 30 minut twierdzenie „X nie istnieje"
   ma okres przydatności liczony w MINUTACH.**
   **SĄ DWA RÓŻNE `duck-v15`** — oba mówią „v15", oba „7 patchy", oba mają patch **0007** o zupełnie
   innej treści (a450: eskalacja względna → `tool_agent.py`+`solver.py`+`plan_commit.py`; Gemma: log
   win-path → `arc3_winpath.py`). **7911 to złapał i miał rację.**
   **REKOMENDACJA NA SLOT 31.10:** **`c87-v16f`**, pod warunkiem że **ktoś z bundlem r033** przepuści
   go przez `verify_v13.py` (9/9 `git apply` + kompilacja + testy na spatchowanym drzewie).
   **Ja tego zrobić NIE MOGĘ i nie udaję, że zrobiłem** — a450b00f zrobił to dla v16
   (`52b709ee`: „9/9 patchy git apply na czystym r033, drzewo sie kompiluje"), a **moje 6 poprawek
   nie dotyka ANI JEDNEGO patcha harnessu** — tylko `kernel-metadata.json`, 3 komórki notebooka i
   2 docstringi. **Ryzyko utraty certyfikacji bliskie zeru, ale „bliskie zeru" ≠ „zweryfikowane".**
   **Jeśli nikt nie zweryfikuje: `v13.5-consensus` jest najlepszym pakietem, który DA SIĘ wypchnąć
   bez poprawek** (własny slug ✅, `code_file` ✅, sonda baseline ✅, pokrycie ✅), kosztem
   **42/26/4,33 %** zamiast **22/14/2,27 %** w rerunie — czyli **2,06 pp puli jednej gry.
   To MAŁA cena i NIE WARTO dla niej ryzykować nieskładanego pakietu.**
   **NIE BRAĆ:** v15-a450 (brak hinta = brak jedynej dźwigni o skali ≥ celu) · v13.4 (brak sondy
   baseline ⇒ po submisji nie dowiemy się, czy reguła względna była martwa) · **v16 i v15 Gemmy bez
   poprawek 1 i 2** (push albo padnie, albo **nadpisze cudzy kernel**).
   **RANKING: 1** wypchnąć `c87-v16f` (albo v13.5) na 31.10 — **po GO użytkownika, BEZPIECZNIK
   obowiązuje** · **2** bramka `verify_config_liveness.py --package --strict` przed każdym pushem
   (~10 s) · **3** naprawić asercję `pace[:2] == (22, 14)` · **4** z logu submisji czytać W TEJ
   KOLEJNOŚCI: `baseline=yes|no` (rozstrzyga §1.1) → `mean_coverage` (sufit) → **`mean_a_per_call`
   z drabinką** (rozstrzyga batching) → `duplicate_bases` (wartość `WINPATH`) → `budget_probe` ·
   **5** 1.11 rozgałęzienie, 2.11 select best.
   **Prognoza: oczekiwanie ~28–31 · cel srebro ≈32,33 · 50 pkt wymaga +1,57 poziomu/grę (1,49×
   głębokości, ~317 akcji/grę, 1,49× batchingu) przy wykorzystaniu sufitu 89,9 % — albo +2,70
   poziomu (2,00×) przy 79,1 %.** Stanowisko bez zmian: **„arytmetycznie w zasięgu, ale
   NIEWERYFIKOWALNE w 3 slotach"** — i §7.2 dodał twardy powód: **błąd modelu (±8 pkt) jest
   WIĘKSZY niż próg istotności (+5 pkt).**


19. **`V14-V15-I-WARSTWA-WERYFIKACJI.md`** + **`tools/verify_config_liveness.py`** (515 linii) —
   ❗**NAJNOWSZE (30.10 ~08:45 UTC). ZBUDOWAŁEM BRAKUJĄCĄ WARSTWĘ WERYFIKACJI i znalazłem w v14/v15
   MARTWY INSTRUMENT, którego nikt w czterech gałęziach nie znalazł.**
   ❌ **ALARM `mean_actions_per_call < 1.5` NIE MOŻE NIGDY ODPALIĆ** — v15 komórka 36 i v14 komórka 35
   (sprawdzone w KODZIE, nie w README). Zmierzona baza to **4,357 akcji/wywołanie** (r019: 474
   wywołania / 2065 akcji), więc próg jest **3× poniżej** wartości, którą już mamy. **To ÓSMA
   instancja klasy „martwy kod przy zielonych testach" i NAJGROŹNIEJSZA: to nie dźwignia, tylko
   INSTRUMENT, który miał powiedzieć, czy dźwignia zadziałała.** Sonda rosteru v15 odpowiada na dwa
   pytania — czy roster się powtarza (wartość `WINPATH`) i **czy batching zadziałał** (wartość
   `OPENER_COMMIT_HINT` + `ESCALATE=20`). **Pierwsza część działa, druga jest martwa.** Czyli po
   submisji dowiemy się o rosterze, ale **NIE dowiemy się, czy jedyna dźwignia o właściwej skali
   zadziałała** — a od tego zależy decyzja na 1.11. **Poprawka: jedna linia, `< 1.5` → `< 4.357`.**
   Próg 1,5 wygląda na przeniesiony ze **starej linii** (7911 mierzy 1,00 akcji/decyzję dla
   r013/r015/r018) — czyli **przeniesienie progu z cudzej konfiguracji bez przeliczenia**.
   **NOWA WARSTWA W TAKSONOMII: INSTRUMENT.** Martwa dźwignia daje wynik neutralny; **martwy miernik
   daje fałszywe poczucie, że wiemy.**
   ✅ **NIEZALEŻNA REPLIKACJA POMIARU GEMMY na innym runie** (r093, surowy `benchmark.json`, blob
   `90173adb`) — Gemma liczyła na r085/32 ukończonych, ja na r093/69 i 27 ukończonych:
   · **`base_actions_per_level` n=69: min 6 · p10 26 · p25 36 · MEDIANA 72 · p75 115 · p90 208 · max 578**
   · przedwczesna eskalacja przy progu **10**: Gemma **31/32 = 96,9 %** vs mój **26/27 = 96,3 %** —
     **ZGODNE CO DO 0,6 pp**. Przy 20: Gemma ~78 % vs moje 92,6 %; przy 60: 22 % vs 37 % — **rozjazd,
     oznaczam go, nie uśredniam** (inne runy, inne podzbiory, Gemma warunkuje dodatkowo na „agent był
     na tempie").
   · **LICZBA WSTRZYKNIĘĆ** (wskaźnik OPERATYWNY, `Σ floor(a_k/próg)`, suma akcji agenta 2315):
     **10 → 211 (9,1 %) · 20 → 96 (4,1 %) · 30 → 58 (2,5 %) · 60 → 21 (0,9 %)**; Gemma (r085):
     154 / 60 / 12 / względny 8. **Stosunki ZGODNE**: Gemma 2,57 i 5,0 vs moje 2,20 i 4,57.
     ⇒ **próg 20 walidowany, próg 10 KRYTYCZNY, optimum jest WZGLĘDNE** (`max(20, 1.2×baseline)`).
   · **Nasze akcje na UKOŃCZONYCH poziomach: n=27, mediana 54** vs mediana baseline dla nich **42**
     ⇒ na ukończonych jesteśmy **wolniejsi** od człowieka. **Suma akcji 2315 vs baseline 7175 = 32 %**
     ⇒ **CZWARTE niezależne potwierdzenie, że problemem jest POKRYCIE, nie efektywność.**
   ✅ **ZBUDOWAŁEM `tools/verify_config_liveness.py`** (515 linii, czysty Python 3, **0 GPU / 0 slotów /
   0 bundla / 0 silnika** — działa na TEKŚCIE, więc uruchamiam go w swoim sandboxie na prawdziwych
   plikach z `gh api`). **Cztery kontrole, każda na jedną instancję z taksonomii:** **L1 ŻYWOTNOŚĆ
   INSTRUMENTU** (czy próg może się wykonać przy zmierzonej bazie → łapie #8) · **L2 DOMYŚLNA
   WARTOŚĆ ENV** (default + walidator każdej zmiennej → #1 #3 #4) · **L3 OSIĄGALNOŚĆ** (warunki
   sięgające po zmienne STAŁE w rerunie: `pass_index=0`, `n_passes=1` → #6) · **L4 SPÓJNOŚĆ
   MIĘDZYWARSTWOWA** (concurrency ≤ MAXREQ · cap vs uczciwy udział · `ESCALATE` vs **zmierzony**
   rozkład baseline i **zmierzona** liczba wstrzyknięć → #2 #5). **Wynik na prawdziwych notebookach:
   v13.2 → 4 ustaleń, 1 KRYTYCZNE (`ESCALATE=10` → 211 wstrzyknięć = 9,1 %); v14 → 4, 1 KRYTYCZNE
   (martwy alarm); v15 → 4, 1 KRYTYCZNE (ten sam).** **Narzędzie NIE krytykuje decyzji Gemmy
   (próg 20 przechodzi: 4,1 % < 6 %) i ŁAPIE to, czego Gemma nie złapała.**
   ⚠️ **UCZCIWIE O NARZĘDZIU:** pierwsze uruchomienie dało FAŁSZYWY POZYTYW (`concurrency=10,
   MAXREQ=0` jako KRYTYCZNE) — bo `MAXREQ=10` występuje w notebookach **TYLKO W KOMENTARZACH**, a
   `ARC3_MAX_ACTIVE_STREAMS` złapałem jako **default** z `_get_env_int(..., 0)`. **Naprawione**
   (odrzuca komentarze, bierze tylko JAWNE ustawienia, a gdy backendu nie da się ustalić statycznie
   raportuje **INFO „nie da się zweryfikować"** z gotową asercją — zamiast zmyślać KRYTYCZNE).
   **Narzędzie, które daje fałszywe pozytywy, jest gorsze niż brak narzędzia.** Granice: mój
   wskaźnik „przedwczesności" jest grubszym sitem niż kryterium Gemmy; `KNOWN_LEGACY_DEFAULTS` jest
   **ręczna** (nowa zmienna z legacy defaultem przejdzie niezauważona); L3 zna tylko dwie zmienne
   stałe; **nie zastępuje `verify_v13.py`** — uzupełnia je o warstwę, której tam brakuje.
   **v13.3-arena zlokalizowany** (`Smak-Domu-Konkurs@5ed750ef`, `arc-agi-3/duck-v13-3-arena/`, m.in.
   `0007-arena-replay-log.patch`, `build_v133_arena.py`, `OCENA-ARENA-V13-3-ARENA.md`). Z komórki 6
   v15: `ARC3_OPENER_COMMIT_HINT` ma **default `False`** (`_get_env_bool(..., False)`) ⇒ **bez
   jawnego `"1"` hint jest MARTWY** (instancja #3, L2 to łapie). **I znalazłem TRZECIĄ dźwignię na
   `tok/akcję`, o której nie wiedziałem: komórka 6 egzekwuje kompaktowość wyjścia narzędzi
   MECHANICZNIE** (`board_print_suppressed_rows`, „Never print or echo full board frames") — czyli
   atakuje `tok/akcję` od strony **wyjścia narzędzi**, nie wyjścia modelu.
   ❗**KOREKTA MOJEGO STANOWISKA O 50+ — z „nieosiągalne" na „nieweryfikowalne w 3 slotach".**
   Arytmetyka: `tok/akcję = tok/wywołanie ÷ akcje/wywołanie = 3664,6 ÷ 4,357 = 841,2` (zgadza się z
   pomiarem). Przy 17,2 ms/tok: **cel 300 akcji/grę wymaga tok/akcję ≤ 571, cel 400 wymaga ≤ 428.**
   Żeby zejść z 647 do 428 przy niezmienionym tok/wywołanie, trzeba **akcje/wywołanie 4,357 → 6,57
   (1,51×)**; do 370 — **→ 9,90 (2,27×)**. `commit(plan)` ma `max_actions=40`, więc **sufit jest
   daleko**. ⇒ **50+ wymaga, żeby model batchował 1,5–2,3× więcej akcji na wywołanie. Pytanie nie
   brzmi „czy się da", tylko „czy model posłucha" — I JEDYNYM INSTRUMENTEM, KTÓRY MIAŁ TO ZMIERZYĆ,
   JEST MARTWY ALARM Z §1.**
   | twierdzenie | stan |
   |---|---|
   | „50+ wymaga +6,4 σ od średniej bazy" | ✅ prawdziwe — **nie da się WYLOSOWAĆ** |
   | „50+ jest nieosiągalne" | ❌ **ZBYT MOCNE, KORYGUJĘ** — arytmetycznie wystarczy batching 1,5–2,3× |
   | „50+ jest osiągalne" | ❌ też nie — **nieweryfikowalne w 3 slotach** przy σ≈2,5–3,9 i progu +5 |
   | **stan właściwy** | ⚠️ **„ARYTMETYCZNIE W ZASIĘGU, ale NIEWERYFIKOWALNE w 3 slotach; obstawianie tego to hazard, nie plan"** |
   Jeśli batching zadziała (a/call 4,36 → 6,6): akcje/grę 228 → 325, projekcja Gemmy ~59,5, a przy jej
   własnym przeszacowaniu ~25 % (przy 228 akcjach projekcja 35,6 vs zmierzone 26,78 = **8,8 pkt /
   25 %**) dostajemy **~45**. **Czyli ~45–50 jest w zasięgu JEDNEGO udanego wdrożenia batchingu.**
   Dlaczego NIE obiecuję: przeszacowanie 25 % to **JEDEN punkt danych**, nie prawo; posłuszeństwo
   modelu **niezmierzone, a instrument martwy**; `ESCALATE` i hint **mogą się znosić**; 3 sloty przy
   σ≈3 nie zweryfikują efektu mniejszego niż +5.
   ❌ **CZY ZBUDUJĘ WŁASNY NOTEBOOK: NIE** (trzy twarde powody: nie mam bundla r033 / `arcengine` /
   GPU / `cargo`; nie przetestuję przed spaleniem slotu, a zostały 3; v15 już dziedziczy certyfikację
   7/7 i ma diff 5 komórek). ✅ **CO MAM LEPSZEGO — trzy rzeczy, wszystkie zweryfikowalne przeze
   mnie:** (1) **poprawka martwego alarmu** — jedna linia, **nikt tego nie znalazł**; (2)
   **`verify_config_liveness.py`** jako bramka przed każdą submisją — łapie **klasę 8 instancji**,
   w tym instrumenty; (3) **zmierzone bazy** (rozkład `base_actions_per_level` n=69 i liczby
   wstrzyknięć 211/96/58/21) — surowe liczby pozwalające ustawić próg **względny** bez zgadywania.
   **PAKIET NA SLOT 31.10 (§6.3): v15 + DWIE poprawki jednowierszowe** (żadna nie wymaga bundla ani
   GPU): alarm `< 1.5` → `< 4.357` + bezwarunkowy druk `a/call` z odniesieniem, oraz
   `assert ARC3_VARIANT["env"].get("ARC3_OPENER_COMMIT_HINT") == "1"` (bo default to `False`).
   Reszta bez zmian: `ESCALATE=20` · `CAP=0` · `WINPATH=1` · `DEAD_SKIP=1` · `EXPOSE_UNDO="on"` ·
   concurrency 10 · obie sondy ON. **Bramka przed pushem: `verify_config_liveness.py --strict` →
   0 KRYTYCZNYCH.**
   **NIE BUDUJĘ, choć rekomenduję** (nie mogę zweryfikować bez bundla r033): próg **względny**
   `max(20, 1.2 × baseline[poziom])` → 8 wstrzyknięć, 0,8 % puli, **0/32 przedwczesnych**
   (Gemma `PROPOZYCJA-0007.md`).
   **RANKING: 1** naprawić martwy alarm · **2** wysłać v15 + 2 poprawki na 31.10 · **3** bramka
   `verify_config_liveness.py --strict` przed każdym pushem · **4** przeczytać z logu
   `roster_probe.jsonl` + `budget_probe.json` + **`mean_actions_per_call`** · **5**
   `parse_serve_log.py` na `serve.log` każdego nowego runu · **6** 1.11 rozgałęzienie, 2.11 select best.
   **Oczekiwanie ~28–31 · cel srebro ≈32,33 · ~45–50 arytmetycznie w zasięgu JEDNEGO udanego
   wdrożenia batchingu — ale tego NIE obiecuję, bo instrument, który miał to potwierdzić, jest martwy.**

   ❌ **NOWE „NIE ROBIĆ": podnoszenie `max_runtime_s_per_game` (cap nigdy nie wiąże) oraz
   oszczędzanie tokenów/akcję jako GŁÓWNA dźwignia (r110: 572 vs 647 tok/akcję i 2,8× mniej akcji).**

12. **`DIAGNOZA-23-89-I-PLAN.md`** — ❗**NAJNOWSZE (28.10 ~23:10 UTC), NAJWAŻNIEJSZE DECYZYJNIE.**
   Submisja **ref 57737623** (`arc3-duck-v11` v1, slot A) = COMPLETE, **publicScore 23.89**.
   Naprawa `concurrency` **zadziałała** (0.00 → 23.89), ale wynik jest poniżej ich 26.25.
   Trzy przyczyny w kolejności pewności:
   **(1) SZUM** — nasza baza (Franzen M2) ma udokumentowany rozkład **μ=25.77, σ=3.93** z drawami
   **21.01** i **35.35**, więc 23.89 mieści się w ±1 SD i **nie dowodzi**, że v11 jest gorszy.
   Zmiana musi dać **~+5 pkt**, żeby jeden draw cokolwiek mówił; wyświetlany wynik notebooka to
   **najszczęśliwszy draw, nie średnia**. **(2) Mój kap 45k + `min_done=0` porzuca gry wcześnie** —
   `g50t` skończył **0/7 poziomów przy 1499 s i 91 902 tokenach**, czyli 23 minuty i 83 k tokenów
   zapasu wyrzucone; trzy gry łącznie oddały **3840 s i ~243 600 tokenów**. Błąd projektowy:
   przy `min_done=0` warunek `levels_completed < 0` nigdy nie jest prawdziwy, więc `ABANDON`
   odpala **na grze z zerem punktów** — dokładnie tej, która najwięcej zyskuje kontynuując.
   **(3) Gramy równym przydziałem czasu**, co ich lista błędów śmiertelnych wymienia jako
   **zakazane** (#6: „Never use uniform time allocation. Priority scheduling (D′) is essential").
   **Wycofuję dwie własne rzeczy:** przypisanie spadku smoke patchowi `0005` (przy rozstrzale
   ~14 pkt/grę jedno porównanie tego nie rozstrzyga; `cn04` 71→4 to swing udokumentowany przez
   inny zespół na IDENTYCZNYM kodzie) oraz **całą linię searchu offline** — zmierzone **0.20**
   (ich ref 57272788, „Game sources don't exist in the rerun") plus **0/113 poziomów na held-out**.
   **50+ jest nieosiągalne: próg top-5 to 51.04, a to +25.3 pkt = +6.4 σ od średniej bazy.**
   Cel realny: **średnia 29–30**, brąz ≈31.04, **srebro ≈32.33** (linie z 27.10, 4904 zespoły).
   Plan na 4 dni w §8: jedna hipoteza na slot, najpierw usunięcie zera z rozkładu (4 safety fixes:
   gateway check, **startup keepalive — gateway kończy bieg po 15 min bez akcji**, start retry,
   30-min gateway wait), potem D′ scheduler. **Rust+rayon i 64 GB NIE dają punktów** (§6) —
   dają ochronę slotów przez lokalny weryfikator i analizę logów.

13. **`RESEARCH-LIDERZY-50PLUS.md`** — ❗**ODPOWIEDŹ NA PYTANIE „JAK LIDER ZROBIŁ 75?" (28.10 ~23:40).**
   **User miał rację, mój argument „+6.4 σ" był wadliwy**: dowodził, że 50 nie da się WYLOSOWAĆ
   na obecnej bazie, **nie** że jest nieosiągalne — liczba wpisów mówi o liczbie losowań, nie o średniej.
   **NAJWAŻNIEJSZA LICZBA: opublikowana czołówka ma 22.53–27.89.** Trzej zwycięzcy Milestone 2
   (wszyscy Duck harness + TAAF + Qwen3.8-Flash-Next) — `discussion/744792`, Tong Hui Kang (26.):
   **dfranzen 27.89 · lordhansolo 23.84 · sirikilohit 22.53**. **MY jesteśmy W TYM PAŚMIE**
   (26.25 / 23.89), a nasz KV pool **1 011 264** jest **identyczny** z dfranzenem. Dostrajanie
   harnessa rozstrzyga o **~5 pkt**, nie o ~50.
   **Chen: 28.34 (28.09) → 59.17 (09.10) → 67.49 → 71.48 → 75.56.** Skok +30.8 w 11 dni jest
   **5.7× większy niż cała opublikowana rozpiętość** (5.4 pkt). **Ona wprost odmówiła
   open-source'u**: *„Given the complexity of the process, I've decided not to open-source"*.
   `mayankraj4728` §7.2b: *„Top ARC-AGI-3 teams (Tufa, Yi-Chia Chen, Turducken, NVARC3) have
   **published nothing**; they release after the deadline."* **Więc: NIE WIEMY i nie ma źródła.**
   ❌ **SZYBKOŚĆ NIE JEST RÓŻNICUJĄCA — zależność ODWROTNA:** dfranzen **946 tok/s** (najwolniejszy)
   → **27.89** (najlepszy); sirikilohit **1 159** (najszybszy) → **22.53** (najgorszy). To
   **zewnętrzne potwierdzenie**, że Rust+rayon nie da punktów. Różnicuje **kontekst ↔ współbieżność**:
   rellik13 *„I thought decode throughput was the bottleneck, so I kept concurrency high. The logs
   showed the **kv pool sat 91-97% full and requests queued for cache space** — **memory was the
   actual limit**"* = **ta sama klasa błędu co nasze `concurrency=120`**.
   ✅ **ZMIERZONA DŹWIGNIA +8 pkt** (rellik13: fp8 KV → trimy 37k→27k zamienione na 57k→45k,
   *„this alone took the score from 14.5 to 22.5"*) — **ale wszyscy trzej i MY mamy już `fp8_e4m3`.
   Dźwignia zużyta.** nvfp4 KV (xz, 4. miejsce) = 4× zamiast 2×, ale xz **sam nie wie**, czy to nie
   psuje efektywności akcji, i nie zwalidujemy tego w 4 dni.
   ✅ **JEDNA DARMOWA RZECZ, KTÓRĄ ZNALAZŁEM:** rellik13 *„harness changes that helped were simply
   to **not mislead the agent**: UNDO instead of ACTION7, 'level restarted' instead of 'game over',
   removing lines that tell the agent to ignore the budget bar"*. Sprawdziłem w naszym patchu:
   **`EXPOSE_UNDO` domyślnie `"tufa"` = „advertise ACTION7 verbatim but REJECT execution (legacy)"**,
   a `to_engine_action` zwraca `None` dla ACTION7/UNDO gdy tryb ≠ `on`. **Nasz dump env (10 zmiennych)
   NIE zawiera `EXPOSE_UNDO` → agent widzi akcję, której harness nie wykona.** Poprawka:
   **`EXPOSE_UNDO="on"`** = jedna zmienna env, zero ryzyka po stronie serwingu. „ignore the budget
   bar" → **0 wystąpień, już czyste** (dfranzen uczy agenta CZYTAĆ pasek: „BAR RULE"). „game over"
   → częściowo zaadresowane (L5653-5655 już wyjaśnia „the current level restarted").
   **To TRZECIA instancja tej samej klasy buga** po `SCOPE=run` i `concurrency=120`: zmienna, której
   **domyślna wartość po cichu zachowuje legacy zachowanie**.
   ⚠️ **SZÓSTA KOREKTA MOJEGO DOKUMENTU:** wycofuję §2.3 diagnozy („gramy równym przydziałem") —
   nasz patch **MA** `priority_scheduler.py` (L261/346/1391/3192), a „10 × 2880 s" to SMOKE, nie
   rerun. Otwarte: czym D′ różni się od dfranzenowskiego schedulera.
   **PLAN POPRAWIONY (§7): slot 1 = c45 − 0005 + `CAP=0` + `EXPOSE_UNDO="on"` + 4 safety fixes.**
   Cel pozostaje **29–30 / srebro ≈32.33**, nie 50+.

## Najważniejsze liczby (skrót)

| fakt | wartość | źródło |
|---|---|---|
| ich najlepszy wynik na LB | **26.25** (duck v3, 16.10) — **nadal aktualny na 27.10 19:39 UTC**, od 25.10 nie wysłano nic | `ops/results/r086-submissions` |
| smoke c45 (10 gier, 48 min, concurrency 10) | **MEAN 26.78**, **32 poziomy**, **2126 akcji = 212.6/grę** | `r085-kernel_output_pick/output-pick/benchmark.json` |
| **OCZEKIWANY wynik c45 po naprawie `concurrency`** | **24 – 29, punktowo ~26.8** (kotwica: zmierzony smoke c45 **26.78**). ~~31.18~~ obalone | `OCENA-CODEX-7Z.md` §4 |
| **ZMIERZONY wynik v11 slot A (ref 57737623, 28.10)** | **23.89** COMPLETE, smoke **18.55** — naprawa `concurrency` **zadziałała** (0.00→23.89) | `DIAGNOZA-23-89-I-PLAN.md` §1 |
| **SZUM wyniku — NAJWAŻNIEJSZA LICZBA** | Franzen M2: **μ=25.77, σ=3.93**, drawy 21.01…35.35; próg istotności **+5 pkt**; wyświetlany wynik = **najlepszy draw** | j.w. §2.1 |
| jedyna zmierzona **dodatnia** dźwignia na naszej bazie | **D′ slot-priority scheduler: 25.77 → ~29.0** | j.w. §3 |
| **PRÓG 50+ — trzy niezależne modele** | **~300 akcji/grę** (obecnie **212,6**): 7911f950 „podwojenie → 51,3" · Gemma „300 → **59,5**" · mój model „500 tok/akcję → 350 → **54,12**" | `OPINIE-3-GALEZI-O-V13.md` §3.3 |
| **wartość playbooka v13** | **2,90 pkt średnio** na 25 grach (72,61 sumarycznie, 14 poziomów); **0** jeśli roster prywatny | j.w. §1.3 |
| `official_110()` / 110 klonów 25 gier | ❌ **LOKALNY SYMULATOR**, nie roster submisji — *„reproduced **before submission**"* | j.w. §2 |
| cap per-poziom | **1.15** (nie 1.0) — `taaf/game.py` + regresja **32/32**; ale wiąże **cap UKOŃCZENIA** | j.w. §3.2 |
| 27B na tej samej bazie | ❌ **1,18** (slot B) i **0,27** (smoke); **47,0 s/akcję** vs 8B **12,9 s/akcję** | j.w. §1.4 |
| szum między runami (drugi, niezależny pomiar) | **sd 2,47 pkt**, pojedyncza gra skacze **11,7 pkt**; 26,25→23 = **−1,3 sd** | j.w. §3.1 |
| progi medali (27.10, 4904 zespoły) | złoto ≈**38.2** · srebro ≈**32.33** · brąz ≈**31.04** | j.w. §5.1 |
| offline source-introspection BFS (`find_game_source`) | **0.20** — „Game sources don't exist in the rerun" | j.w. §4 |
| search strojony na 25 publicznych → test na held-out | **7/70 poziomów → 0/113** | j.w. §4 |
| zmiany parametrów serwingu (strumienie/MEMFRAC/kontekst/temp) | **−7 do −8** na zbiorze ukrytym | j.w. §3.1 |
| **wartość kapa `ARC3_LEVEL_TOKEN_CAP=45000`** | ❌ **−0.43** wobec r019 (27.21→26.78) i **−2.24** wobec v3 (29.02). ~~+4.93~~ **OBALONE pomiarem**. Wyłączenie (`=0`) warte **+0.4 do +2.2** | `OCENA-CODEX-7Z.md` §3 |
| ~~próg 25.7 % puli~~ | ⚠️ **modelowy, niepotwierdzony** — kap strzela do **wszystkich** poziomów, nie tylko skazanych; `su15` stracił **−43.1** pkt na poziomie, który inaczej by się ukończył | `OCENA-CODEX-7Z.md` §3.3 |
| współczynnik kalibracji modelu (para **jednorodna**) | **×0.828** (26.25 / 31.70); ~~×0.718~~ wycofany | j.w. §3 |
| `ARC3_PERSISTENT_FUNCTIONS_SCOPE` — dozwolone wartości | **`turn \| levelup \| game`** tylko; `run` **nie istnieje** i degraduje cicho do `levelup` | `patches/0000-franzen-harness-changes.patch` L3559-3560 |
| leaderboard 25.10 — 5. miejsce (próg nagród) | **50.37** (24.10: 49.85), rośnie ~0.5/dzień | `EKONOMIA-TOKENOW.md` §12.2 |
| leaderboard — pole | **4912 wpisów**, miejsce 49 = 35.68, ~0.075 pkt/miejsce w strefie 29–49 | j.w. §12.2 |
| ~~próg nagrody $40k (5. miejsce)~~ **NIEAKTUALNE** | ~~40.97~~ — snapshot z 10.10; lider to dziś **68.91** (Tufa, 14.10), a nagrody są **za miejsca**, nie za próg | `WERYFIKACJA-INNYCH-GALEZI.md` §7 |
| średni score smoke r019 | **27.21**, sufit z głębokości **29.0** | `r019/benchmark.json` |
| +1 poziom w każdej grze | **44.8** · +2 poziomy → **64.5** | j.w., przeliczone ich formułą |
| tokeny na akcję | **841** (1.74 M / 2065) | j.w. |
| tokeny i akcje na poziomie, który **nigdy nie został ukończony** | **35%** (tn36 86%, ls20 91%) | j.w. |
| realny budżet tokenów na grę | **~175k** = ~208 akcji, przy `ΣBas ≈ 685` potrzebnych | arytmetyka z `serve.log` |
| cała wartość optymalizacji **efektywności** ruchu | **1.75 pkt** (29.0 − 27.21) | §2 FAKTY |
| nasz playbook (search offline, **0 tokenów LLM**) | **11/25 gier, 16 poziomów = 3.18 pkt — W SYMULATORZE LOKALNYM, nie na LB**, każdy replay-verified. Na realnym LB prawdopodobnie **0**: gry ewaluacyjne są nieznane i nie mają powtórzonych ID (`taaf/competition_arcade.py` docstring), więc dosłowne sekwencje nie odpalą. Patrz wycofanie w `PATCH-0004-I-SEARCH.md` | `results/playbook.json` |
| najgłębsze rozwiązanie | **tu93: 5 poziomów = 33.33 pkt** (dokładnie w capie) | j.w. |
| postęp z samej kalibracji ruchów | **+3 gry** (ar25, cn04, ft09), 2.59 → **3.08 pkt LB** | `tools/sweep2.py`, §1bis FAKTY |
| postęp z 5× większego capa | **+1 gra** (s5i5, 21 akcji), 3.08 → **3.18 pkt (symulator lokalny, NIE LB)** — i dowód, że tylko tryb `cap_cut`/`time_cut` leczy się budżetem | `results/sweep3_bigcap.jsonl`, §1bis(g) FAKTY |
| przebieg z `--frontier-cap` | **ka59 domknięta** (frontier wyczerpany, budżet nie pomoże), re86: 94 405 stanów w 1 066 MB RAM | `results/sweep4_*.jsonl`, §1bis(i) FAKTY |

**Najważniejszy wniosek strategiczny** (dowód w `FAKTY-I-POMIARY.md` §2, potwierdzony
oficjalnie na `docs.arcprize.org/methodology`): przy **`akcje ≤ 0.9325 · baseline`**
**cap punktacji zawsze wiąże**, więc
`score_gry = 100 · Σ(wag ukończonych poziomów) / Σ(wag wszystkich)`.

> ⚠️ **Poprawione 27.10 — tu stało `≤1.07× baseline`, czyli nierówność ODWRÓCONA.**
> `1.0724 = √(115/100)` jest **poprawną liczbą, w złym miejscu**: warunek `(b/a)²·100 ≥ 115`
> daje `b/a ≥ 1.0724`, czyli **`a ≤ b/1.0724 = 0.9325·b`**. Przy `a = 1.0724·b` score wynosi
> **86.95**, nie 115. Wniosek strategiczny się nie zmienia, ale warunek jest **surowszy niż
> pisałem**: żeby cap wiązał, agent musi być ~**6.75 % SZYBSZY** od ludzkiego baseline, a nie
> „do 7 % wolniejszy". Ta sama pomyłka siedziała w `FAKTY` L521 i w `WERYFIKACJA-INNYCH-GALEZI.md`
> §5 — poprawiona we wszystkich trzech miejscach.
Czyli wynik zależy **wyłącznie od tego, KTÓRE poziomy się ukończyło** — liczba akcji ponad
ten próg jest warta dokładnie zero. Jeden poziom w 7-poziomowej grze to maksymalnie 3.57 pkt;
pięć poziomów w 9-poziomowej to 33.33. **Głębokość jest jedyną dźwignią.**

## Zawartość katalogu

```
README.md                     ten plik
PATCH-0004-I-SEARCH.md        run-killer + bugi 0003 + patch 0004 + wyniki searcha (GŁÓWNY)
FAKTY-I-POMIARY.md            kompendium zmierzonych faktów z proweniencją (11 sekcji)
DIAGNOZA-45plus.md            diagnoza „dlaczego nie ma 45+" + ranking dźwigni + plan 9 dni
arc3_level_budget.py          czysta logika patcha 0004 (bez harnessa, bez GPU)
arc3_search.py                wyszukiwarka offline: BFS / beam + segmentacja kandydatów kliku

patches/
  0003b-early-abandon-rebased.patch      NASZ: ich 0003, logika 1:1, POPRAWIONY kontekst
  0004-level-token-cap.patch             NASZ: budżet poziomu (wymaga 0003b)
  0004-standalone-level-token-cap.patch  NASZ, ZALECANE: to samo bez zależności od 0003
  # cztery poniżej to ICH patche, skopiowane żeby verify_patch_chains.sh działał bez
  # pobierania ich repo (wydobyte z duck-v7.ipynb przez extract_notebook_patches.py):
  0000-franzen-harness-changes.patch     ich cell 4 (498 KB, 16 plików) - nakładany PIERWSZY
  duck-extra-00.patch                    ich cell 5 = "0001" (tool_agent)
  duck-extra-01.patch                    ich cell 6 = "0002" (world model + nudge, 4 pliki)
  duck-extra-02.patch                    ich cell 7 = "0003-early-abandon" <- RUN-KILLER

tests/
  test_arc3_level_budget.py   16 testów; OK na drzewie z 0003b, OK (skipped=2) na standalone

tools/
  sweep2.py                   PRZEGLĄDARKA v2: kalibracja ruchów po EFEKCIE (hash ramki),
                              pruning martwych ruchów, tryb po efektywnym rozgałęzieniu.
                              To ona rozwiązała ft09 (0 poziomów -> 1 poziom w 4 akcjach).
                              + `--frontier-cap`: ograniczenie PAMIĘCI frontieru BFS.
                              Bez niego frontier trzyma deepcopy każdego stanu (re86:
                              0.190 MB/stan -> 94 405 stanów = 17.9 GB przy 3.9 GB RAM),
                              więc duże capy węzłów były fizycznie niemożliwe. §1bis(h)-(i).
  fetch_repo_artifacts.sh     pobranie ich drzewa przez gh api (25 gier + metadata + 42 pliki
                              bundle + notebooki + migawka 492 blobów) — obejście limitu 1 MB
  extract_notebook_patches.py wydobycie patchy z komórek 4-7 notebooka (dwie różne postaci)

Katalog `notebook/` (osobny, z własnym README) zawiera GOTOWY naprawiony notebook:
  notebook/arc3-duck-fixed.ipynb  ich duck-v7 po naprawie run-killera i z patchem 0004.
                                  Wygenerowany przez tools/make_notebook_patch.py,
                                  zweryfikowany end-to-end (łańcuch z komórki 10: 4/4 OK,
                                  py_compile 3/3 OK, testy 16/16 OK). W README obok są
                                  SHA-256 źródła i wyniku, więc zestarzenie się wykrywalne.
  notebook/README.md              proweniencja, co dokładnie zmieniono (2 rzeczy), czego
                                  NIE ruszono, kill-switch i lista „czego nie robić".
  calib_probe.py              SONDA diagnostyczna BEZ searcha (0.5-8 s/grę): mierzy
                              available_actions, liczbę różnych efektów kliku, medianę
                              zmiany px, efektywne rozgałęzienie i signal_quality.
                              Importuje funkcje sweep2, więc metoda jest identyczna.
                              UWAGA: pomiar na 25 grach obalił używanie signal_quality
                              jako PREDYKTORA - patrz FAKTY §1bis(e)
  make_notebook_patch.py      GENERATOR NAPRAWIONEGO NOTEBOOKA: bierze ich arc3-duck.ipynb,
                              podmienia treść komórki 7 (run-killer 0003) na nasz
                              0004-standalone i aktualizuje ARC3_VARIANT (env + nazwy patchy).
                              Struktura notebooka bez zmian (30 komórek przed i po).
                              Wynik zweryfikowany end-to-end: results/verification_notebook.txt
  verify_patch_chains.sh      DOWÓD: łańcuchy A/B/B'/C + py_compile + testy (patrz niżej)
  score_formula.py            formuła punktacji + weryfikacja na r019 + wartość playbooka
  sweep.py                    przegląd v1 (BFS/beam + segmentacja blobów) — źródło wyników
                              w results/sweep_*.jsonl; zachowany dla odtwarzalności,
                              ale ma ślepy generator klików (patrz §1bis FAKTY)
  build_playbook.py           budowa playbooka + WERYFIKACJA REPLAYEM na świeżej instancji

results/
  playbook.json               11 gier / 16 poziomów, sekwencje akcji, replay-verified, 3.18 pkt
  game_metadata.json          25 gier: baseline, tagi, ΣBas, sufity głębokości, wynik searcha
  sweep_results.jsonl         przebieg płytki (3k węzłów/grę)
  sweep_deep.jsonl            przebieg głęboki v1 (12k węzłów/grę)
  sweep2_results.jsonl        przebieg v2 z kalibracją po efekcie (8/25 gier — proces
                              zabity przez presję pamięci przy 2 workerach z deepcopy)
  sweep2_rest.jsonl           dokończenie v2 na 12 grach (1 worker): 11/12 zapisanych,
                              lf52 zabity po 1783 s — blokada na animacji, patrz FAKTY
                              („Limit czasu jest NIEWYMUSZALNY z wnętrza pętli")
  sweep_merged.jsonl          scalone najlepsze z przebiegów v1
  sweep_best.jsonl            scalone najlepsze ze WSZYSTKICH 6 przebiegów (źródło playbooka);
                              przy remisie bierze przebieg z bogatszą diagnostyką (v4>v3>v2>v1)
  sweep3_bigcap.jsonl         przebieg v3: cap 60 000 węzłów na 8 grach uciętych capem -> +s5i5
  sweep4_memcap.jsonl         przebieg v4: cap 200 000 + --frontier-cap 4000 (ka59 OK, re86 padł
                              na bugu deque.sort - zachowany jako dowód buga)
  sweep4_re86.jsonl           re86 po naprawie buga: 200 000 węzłów, 94 405 stanów, 679 s
  sweep3_bigcap.log, sweep4_memcap.log, sweep4_re86.log   surowe logi
  sweep_shallow.log, sweep_deep.log, sweep2.log, sweep2_rest.log   surowe logi
  their_tree_snapshot.tsv     migawka ich gałęzi: 492 bloby (SHA / rozmiar / ścieżka)
  verification_output.txt     zapisany output verify_patch_chains.sh (dowód run-killera)
  verification_notebook.txt   PRAWDZIWY przebieg weryfikacji WYGENEROWANEGO notebooka:
                              skróty SHA wydobytych patchy, łańcuch z komórki 10 (4/4 OK),
                              py_compile (3/3 OK), testy jednostkowe 16/16 OK
```

## Jak odtworzyć dowody (bez GPU, bez slota Kaggle, ~1 minuta)

Patche ich linii są **skopiowane do `patches/`**, więc dowód run-killera działa od razu,
bez pobierania ich repozytorium:

```bash
cd arc3-handoff/tools
# pristine drzewo PRE-patch (42 pliki ARC3-Inference) - patrz niżej, skąd je wziąć
WORK=/tmp/arc3-verify ./verify_patch_chains.sh <sciezka>/bundle/src ../patches
python3 score_formula.py --verify              # formuła odtwarza tn36 3.57 i ls20 3.27
python3 score_formula.py --playbook ../results/playbook.json
```

`<sciezka>/bundle/src` to stan **przed** jakimkolwiek patchem: `./fetch_repo_artifacts.sh /tmp/arc3`
daje to w `/tmp/arc3/bundle/src` (42 pliki z `r033-recon-bundle`, `solver.py` = blob `0b69d62`).
Do pełnego odtworzenia od zera:

```bash
./fetch_repo_artifacts.sh /tmp/arc3            # 25 gier, metadata, 42 pliki bundle, notebooki
python3 extract_notebook_patches.py /tmp/arc3/bundle/duck-v7.ipynb /tmp/patches   # ich 4 patche
```

`verify_patch_chains.sh` buduje pristine drzewo i nakłada patche **dokładnie komendami z ich
cell 9** (`git apply --include=ARC3-Inference/*`, cwd = `<bundle>/src`), potem raportuje:

| łańcuch | sekwencja | oczekiwane | znaczy |
|---|---|---|---|
| **A** | franzen → 0001 → 0002 → **0003b** → **0004** | OK | nasz pełny zestaw działa |
| **B** | franzen → 0001 → 0002 → 0004 | FAIL `solver.py:47` | 0004 kotwiczy się na imporcie z 0003b |
| **B'** | franzen → 0001 → 0002 → **0004-standalone** | OK | wpięcie zalecane |
| **C** | franzen → 0001 → 0002 → **ich stary 0003** | FAIL `solver.py:35` | **run-killer** |

Zapisany wynik: `results/verification_output.txt`.

## Jak odtworzyć search

```bash
python3 -m pip install --user --break-system-packages -q numpy pydantic pillow
python3 -m pip install --user --break-system-packages -q --no-deps --ignore-requires-python arcengine
python3 tools/sweep.py --games-dir /tmp/arc3/games --node-cap 12000 --sec-cap 300 \
        --max-levels 6 --beam 120 --click-candidates 28 --workers 2 --out /tmp/sweep.jsonl
python3 tools/build_playbook.py /tmp/sweep.jsonl     # + weryfikacja replayem każdej sekwencji
```

~45 min na 2 rdzeniach. `sweep.py` wymaga `metadata`/ścieżek w nagłówku — domyślne ścieżki
są w stałych na górze pliku (`GAMES`, `META` w `build_playbook.py`).

### Pułapka w NASZYM własnym narzędziu (znaleziona i naprawiona 24.10)

`sweep.py` zapisywał numer poziomu jako `base + lvl`, ale `base` **samo rośnie** po każdym
rozwiązanym poziomie (to liczba już ukończonych), więc indeksy wychodziły `0, 2, 4, 6, 8`
zamiast `0, 1, 2, 3, 4`. Objaw: `score_formula.py --playbook` dawał tu93 = **55.56**, a
`--game tu93 --actions 18,10,19,17,29` dawał **33.33** — bo pierwszy czytał pole `level`
z playbooka, a drugi liczył od zera.

`build_playbook.py` używa `enumerate`, więc **wartość playbooka (wtedy 2.59 pkt, dziś 3.18 pkt po kalibracji ruchów po efekcie i przebiegu z capem 60 000) i `expected_game_score`
były poprawne cały czas** — błędne było tylko pole `level` w JSON-ie. Naprawione w `sweep.py`
(`"level": base`), a istniejące artefakty w `results/` zreparowane renumeracją
(`level = indeks kolejny`). Gdyby to zostało, harness kluczujący replay po polu `level`
podstawiłby sekwencje pod złe poziomy.

Wniosek ogólniejszy: **numer poziomu w tych danych zawsze == indeks kolejny wśród
ukończonych**, bo poziomy padały po kolei. Nie licz go z `levels_completed + licznik pętli`.

## Stan operacyjny na 24.10 ~16:45 UTC (żeby nic nie zepsuć)

- **Nie pushować `arc-agi-3/kaggle/ops/request.json`** do ich gałęzi, dopóki wisi run:
  `42bb78b` in_progress od 13:48, `ad8b804` (r065) pending od 14:02. Push kasuje wiszące runy
  (lekcja z ich r057).
- Kolejka r065 idzie na kernel **`arc3-duck-original`**, którego notebook ma **zero patchy** →
  run-killer go nie dotyczy. Dotyczy każdej następnej próby linii **`duck-v7`** (ich 26.25).
- GPU quota 30 h/tydz. wyczerpana 16.10; API submit daje `400 CreateCodeSubmission` → klik w UI.
- **Final submission deadline 2 XI 2026** (**9 dni** od 24.10, zweryfikowane dziś na stronie Kaggle: licznik „9 days to go”), wyniki 4 XII. **26 X to Entry + Team Merger Deadline, NIE termin submisji** — entry mamy spełnione (6 punktowanych submisji).
- Liczba dostępnych slotów: **niezweryfikowana na oficjalnej stronie**, którą pobrałem. Reguły
  Kaggle dla tego konkursu podają limit **5 submisji/dzień**, ale realnym ograniczeniem jest
  **9-godzinny rerun** każdego notebooka oraz (u nich) tygodniowy limit GPU, wyczerpany 16.10 —
  który po 8 dniach powinien już być zresetowany. Mój wcześniejszy szacunek „~8 slotów przy
  1/dzień” był zgadywanką i niniejszym go wycofuję.
  26 X to był deadline **zgłoszenia** (spełniony, 6 zaliczonych submisyji).
- Ich własne zasady, których nie łamać: jedna dźwignia na submisję, nie prowadzić dwóch torów
  naraz, nie submitować bez `ARC3_SMOKE_OK`, nie planować na niezweryfikowanych krzywych,
  nie sumować nakładających się sufitów.
