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

## Najważniejsze liczby (skrót)

| fakt | wartość | źródło |
|---|---|---|
| ich najlepszy wynik na LB | **26.25** (duck v3, 16.10) — **nadal aktualny na 27.10 19:39 UTC**, od 25.10 nie wysłano nic | `ops/results/r086-submissions` |
| smoke c45 (10 gier, 48 min, concurrency 10) | **MEAN 26.78**, **32 poziomy**, **2126 akcji = 212.6/grę** | `r085-kernel_output_pick/output-pick/benchmark.json` |
| **OCZEKIWANY wynik c45 po naprawie `concurrency`** | **24 – 29, punktowo ~26.8** (kotwica: zmierzony smoke c45 **26.78**). ~~31.18~~ obalone | `OCENA-CODEX-7Z.md` §4 |
| **ZMIERZONY wynik v11 slot A (ref 57737623, 28.10)** | **23.89** COMPLETE, smoke **18.55** — naprawa `concurrency` **zadziałała** (0.00→23.89) | `DIAGNOZA-23-89-I-PLAN.md` §1 |
| **SZUM wyniku — NAJWAŻNIEJSZA LICZBA** | Franzen M2: **μ=25.77, σ=3.93**, drawy 21.01…35.35; próg istotności **+5 pkt**; wyświetlany wynik = **najlepszy draw** | j.w. §2.1 |
| jedyna zmierzona **dodatnia** dźwignia na naszej bazie | **D′ slot-priority scheduler: 25.77 → ~29.0** | j.w. §3 |
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
