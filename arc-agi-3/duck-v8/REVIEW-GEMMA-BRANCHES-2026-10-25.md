# Recenzja gałęzi Gemma (c4eeb067 i 6d081d52) ws. ARC-AGI-3

**Data:** 2026-10-25
**Gałąź zapisująca:** `arena/a450b00f-pokemon`
**Czytane gałęzie:**

- `peteraangelic-pixel/Gemma-konkurs` @ `arena/c4eeb067-gemma-konkurs`, recenzja `b5f2eb9`
  (`REVIEWS/2026-10-25-arc3-dwie-galezie-pokemon-i-co-z-tego-wynika.md`),
- `peteraangelic-pixel/Gemma-konkurs` @ `arena/6d081d52-gemma-konkurs`, notatka `678da95`
  (`notes/ARC-AGI-3-cross-branch-update-2026-10-25.md`),
- `peteraangelic-pixel/Pokemon` @ `arena/c87f7a48-pokemon`, tip `6c53d13`,
- `peteraangelic-pixel/Pokemon` @ `arena/a450b00f-pokemon`, tip `33a9f7e` (przed tym commitem),
- `peteraangelic-pixel/Smak-Domu-Konkurs` @ `arena/5ed750ef-smak-domu-konkurs`, tip `9c05c70`.

Zakres tej recenzji: tylko odczyt i przeliczenia na zapisanych artefaktach. Bez Kaggle API,
bez smoke/benchmarku, bez treningu/GPU i bez submissionu.

## Werdykt w skrócie

Tak — w obu opiniach Gemma jest coś nowego, ale nierówno.

Gałąź **6d081d52** jest solidna i ostrożna: dobrze koryguje „efektywność ruchów" na
„głębokość", dobrze podkreśla, że playbook c87 to **3,18 pkt podłogi**, a nie skok do 45+,
i dobrze odnotowuje wycofanie części przeszacowań przez c87. Nie wnosi jednak nowego
mechanizmu.

Gałąź **c4eeb067** wnosi dwie dobre nowe obserwacje liczbowe i jedną dobrą hipotezę, ale
jej najmocniejszy wniosek punktowy jest za mocny. Ma też jedną pomyłkę lineage/metadata,
która ma praktyczne znaczenie dla slotu `duck-c45`.

## Co jest naprawdę nowe i potwierdzone

### 1. `r069` domyka sprawę `-f`

Na gałęzi Smak, `arc-agi-3/kaggle/ops/results/r069-auto-submit/SUMMARY.md` pokazuje
faktyczny submit:

- komenda z `-f submission.parquet`,
- `rc=0`,
- `Submission ref: 57607527`.

Czyli root cause z a450/DeepSeeka/c87 — `ops.py:459` podawał ścieżkę zamiast nazwy pliku
wyjściowego — jest już potwierdzony nie tylko z kodu i statystyki 12:2, ale udanym submitem.

### 2. c87 w nowych commitach sama wycofuje część optymizmu

Tip c87 to `6c53d13` („wycofanie przeszacowania level-cap + triage budżetowy").
Doszły m.in. `results/budget_triage.tsv` i korekta rankingu dźwigni:

- wcześniejsze **+7…+17 pkt** przypisywane level-cap/ABANDON jest wycofane jako
  przeszacowanie,
- `ABANDON` pomaga co najwyżej flotowo, przez zwolnienie slotu SGLang innej grze;
  nie „przenosi budżetu" na kolejny poziom tej samej gry, bo poziomy są sekwencyjne,
- jedynym per-gra kandydatem pozostaje darmowy `RESET_LEVEL` i świeża hipoteza od czystej
  ramki — też jeszcze niezmierzony.

Z `budget_triage.tsv` wynika też ograniczenie prostej narracji „+1 poziom wszędzie":
przy budżecie ok. 208 akcji na grę **wszystkie poziomy mieszczą się tylko w `cd82` i `ft09`**;
`sb26` i `r11l` są marginalne. Arytmetyka 27,21 → 44,8 przy +1 poziomie na grę w próbce r019
jest poprawna, ale dla całego rosteru to sufit, a nie plan wykonawczy.

Potwierdza to też `r070-lb`: lider Tufa 68,91, 5. miejsce „the last dance" 49,85.
Wynik 45+ nie jest więc progiem nagrody w tym snapshocie.

### 3. Rozkład kosztu decyzji z c4 jest policzony poprawnie

Przeliczyłem `r019` niezależnie z `benchmark.json` (gałąź Smak,
`arc-agi-3/kaggle/ops/results/r019-kernel-output/output/benchmark.json`):

- 10 gier, 2065 akcji w historii,
- 474 wpisy z `generated_tokens > 0`,
- suma 1 737 255 tokenów,
- **841 tok/akcję**,
- **3665 tok/decyzję** (wpis z tokenami),
- p50 ≈ 2049, p90 = 8046, p95 = 10 947, max = 61 300.

Tabela skutków opisowego przycięcia wpisów na poziomie 8k/12k/16k też jest arytmetycznie
poprawna: cap 12k dotykałby 18/474 wpisów i „oddawał" 12,3% sumy tokenów. To jest dobra
statystyka opisowa. Problem zaczyna się dopiero przy interpretacji jej jako gotowej dźwigni
— patrz niżej.

## Gdzie c4 przecenia wniosek

### „Szybki silnik + terse mózg = 44–64" jest hipotezą, nie wynikiem

Liczby „wolnej linii" pochodzą z `r050`, a `r050` to **jedna gra**:
`sk48-d8078629`, 521 akcji, 173 decyzje, 231 366 tokenów i **0 ukończonych poziomów**.
Niższe tok/akcję (444) nie kupiło tam żadnego poziomu.

Porównanie r019 vs r050 miesza naraz:

- model (Qwen3.8-Flash-Next W4A16 vs Qwen3.6-27B FP8),
- serwer (SGLang + MTP vs vLLM),
- harness/prompty (Franzen + patche Smak vs stock Duck-original),
- dobór gry (10 gier vs jedna gra `sk48`),
- reżim runu (pełny smoke 10 gier vs jeden długi run z martwym guardem).

Dodatkowo pula ok. 175k tokenów na grę jest wyprowadzona z przepustowości szybkiej linii
w pełnym runie 110 gier. Nie można jej automatycznie przenieść na wolny silnik, bo tam
ograniczeniem jest również czas generowania.

Wniosek: „terse mózg na szybkim silniku" warto zmierzyć jako osobny eksperyment, ale
394 akcje z tej arytmetyki nie są obietnicą +1,5–2 poziomów. Więcej akcji pomaga tylko tam,
gdzie gra jest blisko domknięcia kolejnego poziomu; z triage c87 większość gier nie jest.

### Dźwignia `MAX_OUTPUT=12000` w dużej mierze już jest ustawiona

W notebooku c45/duck-v7 komórka 9 ustawia:

```text
LOCAL_ANALYZER_MAX_OUTPUT = 12*1024
```

a `tool_agent.py` czyta tę zmienną jako limit **na jedno wywołanie modelu**
(`max_tokens=self._max_output_tokens`). Skoro mimo to w r019 występuje wpis
61 300 tokenów, oznacza to, że wpis historii agreguje kilka wywołań modelu składających się
na jeden krok/akcję, a nie jedną odpowiedź bez limitu.

Ustawienie 12k jeszcze raz nie odzyska więc opisowych 12,3% puli. Jeśli chcemy ciąć ten
ogon, trzeba capować **całą turę analizatora albo liczbę wywołań narzędziowych**, a to jest
inny mechanizm niż `LOCAL_ANALYZER_MAX_OUTPUT`.

## Replay po hashu ramki — dobry pomysł, ale mniejszy niż ×4,4

C4 ma częściowo rację: `arc3_replay.py` z a450 już weryfikuje `start_hash`, hashe kroków
i `end_hash`, ale store jest trzymany per `game_id` (osobny plik na grę). Zmiana klucza na
sygnaturę ramki poziomu mogłaby łapać klony występujące pod innymi identyfikatorami.

Tylko to nie jest automatyczne „×4,4 darmowych poziomów":

- pierwsze rozwiązanie nadal trzeba zapłacić modelem albo searchem,
- klon musi mieć identyczny start poziomu i tę samą mechanikę,
- replay zużywa akcje liczone do wyniku, choć zwykle jest znacznie tańszy od re-derivacji,
- jeśli gateway zwraca to samo `game_id` dla replik, obecny klucz może trafiać już dziś.

To jest dobra dźwignia **po** potwierdzeniu cykliczności rosteru sondą, nie przed.

## Najważniejszy nowy problem: Smak `duck-c45` ma niespójne metadata

Tego nie widzę wyłapanego w opiniach Gemma, a ma bezpośrednie znaczenie dla slotu.

Na gałęzi Smak notebook `arc-agi-3/kaggle/duck-c45/arc3-duck-c45.ipynb` **kodem** jest
szybką linią Franzen/SGLang: te same komórki co załączony DeepSeek c45, z jedną poprawką
`TAAF_MINIMAL_DIAGNOSTICS=1` na stałe w komórce 9. Ale
`arc-agi-3/kaggle/duck-c45/kernel-metadata.json` ma źródła skopiowane z `duck-original`:

- `jeroencottaar/taaf-kaggle-source-share`,
- `driessmit1/arc3-vllm-h100-wheelhouse-v3`,
- `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot`,

bez datasetów i modeli Franzena (`dfranzen/pennyroyal-v253`,
`dfranzen/taaf-kaggle-source-bundle-copy`, oba modele `dfranzen/...`), których notebook
wymaga w preflight (komórka 1) i po sztywnych ścieżkach `/kaggle/input/...` (komórka 9).

Konsekwencja:

- jeśli kernel pójdzie przez UI z metadanymi zapisanymi w `.ipynb`, jest to szybka linia;
- jeśli pójdzie przez CLI/ops z tym `kernel-metadata.json`, może nie zamontować właściwych
  inputów i paść na brakach jeszcze przed sensownym pomiarem.

Dlatego stwierdzenie c4, że „slot c45 idzie na linię wolną", jest mylące:
**kod jest szybki, metadata są wolne**. Przed jakimkolwiek pushem trzeba ujednolicić
metadata do zgodnych z notebookiem (jak w `duck-v7/kernel-metadata.json`).

## Ocena 6d081d52

Ta opinia jest ostrożniejsza i w większości trafna:

- dobrze koryguje wcześniejsze „efektywność ruchów" na „głębokość jest jedyną dźwignią",
- dobrze podkreśla, że playbook to 3,18 pkt podłogi, a nie podstawa do obietnicy 45+,
- dobrze rozróżnia tryby zatrzymania searcha (`node_cap_cut` / `time_cut` /
  `frontier_exhausted`) i pamięć frontieru jako realny limit BFS,
- dobrze odnotowuje wycofanie przeszacowań przez c87 i to, że `game_weights` nie realokuje
  budżetu.

Nie wnosi nowego mechanizmu. Jedno ma już nieaktualne: pisze o błędzie `ops.py` jak
o prawdopodobnym i wymagającym testu na wersji COMPLETE. Po `r069` jest to potwierdzone
działaniem (`rc=0`, ref 57607527).

## Zaktualizowana rekomendacja

1. **Najpierw metadata `duck-c45`**: ujednolicić `kernel-metadata.json` z notebookiem.
   Bez tego slot może zmierzyć błąd montażu inputów zamiast kandydata.
2. **Nie budować drugiego schedulera i nie „ustawiać" ponownie `MAX_OUTPUT=12000`**.
   Scheduler Franzena już działa; limit 12k na wywołanie już jest w konfiguracji.
3. **W smoke'u logować osobno**: tokeny na wywołanie modelu, tokeny na turę analizatora,
   liczbę wywołań narzędziowych, akcje na grę, ukończone poziomy i `failure_mode` searcha.
   Sama średnia z 10 gier to za mało sygnału.
4. **Eksperyment „terse brain" robić na tej samej szybkiej linii** jako zmianę
   konfiguracji/promptu analizatora, a nie przez porównywanie r019 z jednogramowym r050.
5. **Replay po hashu ramki dopiero po werdykcie sondy rosteru** i dopiero wersją z a450
   po poprawkach integracyjnych (nie starszą kopią w gałęzi ARC).

Podsumowanie: c4 wnosi dobre nowe liczby i jedną dobrą hipotezę, ale jej najmocniejszy
wniosek punktowy (44–64 z samego „terse brain") jest za mocny względem danych.
6d jest mniej odkrywcza, za to bliższa temu, co dziś naprawdę wiadomo. Naj pilniejszą
rzeczą do naprawy przed slotem nie jest nowa dźwignia, tylko niespójne metadata `duck-c45`.
