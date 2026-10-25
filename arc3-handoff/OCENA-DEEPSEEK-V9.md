# Ocena pakietu v9 i analizy „LEPSZA DROGA" (DeepSeek) — zweryfikowane w ich kodzie

**Data:** 2026-10-25 · **Autor:** sesja `arena/c87f7a48-pokemon`
**Co zostało sprawdzone:** `duck-c45/kernel-metadata.json` i `arc3-duck-c45.ipynb`,
`taaf/competition_arcade.py`, `ops/results/r066-r072`, historia commitów c45,
oraz oficjalna metodologia RHAE (`docs.arcprize.org/methodology`).

Werdykt w jednym zdaniu: **analiza DeepSeek jest najmocniejszą rzeczą, jaka powstała w tym
projekcie po stronie merytorycznej (paper01 = jedyny tor z opublikowanym dowodem na 45+),
ale jej finding nr 1 jest źle zaadresowany, a w kluczowej liczbie „akcji na wywołanie"
DeepSeek przeczy sam sobie — i to jest liczba, od której zależy, czy tor T2 ma sens.**

Przy okazji ich argument o replayu **obalił mój własny playbook** (§4).

---

## 1. NAJPILNIEJSZE: submisja #57607527 wróciła jako ERROR — nie ma nowego wyniku od 16.10

Wczoraj zameldowałem, że fix `-f` „zdjął blokadę". **To było prawdziwe, ale niekompletne**
i muszę to doprecyzować, bo wpływa na plan.

`ops/results/r071-submissions` (STATUS=OK, 25.10 **10:44:37** UTC):

```
57607527  2026-10-24 21:44:38  arc3-duck-original v5: Tufa Labs duck harness ...  SubmissionStatus.ERROR
57247568  2026-10-16 00:02:30  duck v3 (smoke 29.02 ...)                          COMPLETE  26.25
57201063  2026-10-15 01:15:19  v5-world-model-stuck ...                           COMPLETE  23.94
57125322  2026-10-13 01:00:59  v2-think-less ...                                  COMPLETE  24.66
```

Rozdzielenie dwóch różnych awarii, które dotąd się mieszały:

| warstwa | stan | dowód |
|---|---|---|
| **wywołanie API** (`-f`) | ✅ **NAPRAWIONE** | r069: `rc=0`, nadany ref 57607527, w linii komend `-f submission.parquet` |
| **sam kernel w rerunie** | ❌ **ERROR** | r071: `SubmissionStatus.ERROR`, brak `publicScore` |

Czyli mój fix odblokował **wysłanie**, ale kernel i tak padł. **Najlepszy zmierzony wynik to
nadal 26.25 z 16.10.** Przez dziewięć dni nie przybył żaden nowy pomiar.

### Co wiemy o przyczynie ERROR-a

`ops/results/r072-kernel-output/output/taaf_setup_env.json`:

```json
{"TAAF_KAGGLE_DATASET_SOURCES": "[\"jeroencottaar/taaf-kaggle-source-share\",
   \"driessmit1/arc3-vllm-h100-wheelhouse-v3\",
   \"driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot\"]"}
```

To są zbiory **linii wolnej (vLLM + Qwen3.6-27B-FP8)** — i to jest ważna informacja:
**zgłoszony kernel `arc3-duck-original` v5 to linia wolna, nie szybka.**

`vllm-openai-server.log` (8533 B, 32 linie) urywa się bez komunikatu błędu:

```
INFO 10-24 18:01:28 Starting to load model /kaggle/input/datasets/driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot...
INFO 10-24 18:01:29 Selected FlashInferFP8ScaledMMLinearKernel for CompressedTensorsW8A8Fp8
INFO 10-24 18:01:30 Prefetching checkpoint files into page cache started (in background)
Loading safetensors checkpoint shards:   0% Completed | 0/1 [00:00<?, ?it/s]
```

Uczciwie: **log nie zawiera przyczyny.** Zbiory się zamontowały (ścieżka `/kaggle/input/datasets/
driessmit1/...` jest czytana), ładowanie wag się zaczęło i log się kończy na 0 %. Więc awaria jest
**po** tym punkcie i nie została uchwycona w tym pliku. Nie zgaduję dalej — potrzebny jest pełny
log kernela z rerunu, a nie 32 linie z fazy ładowania.

### Wniosek operacyjny, który zmienia priorytety

> **Linia SZYBKA (SGLang + Qwen3.8-Flash-Next W4A16 + drafter, czyli stack Franzena) nigdy nie
> została skutecznie zgłoszona.** Wszystkie cztery COMPLETE wyniki (0.01, 24.66, 23.94, 26.25)
> pochodzą z innych konfiguracji. Zgoda z obserwacją Gemmy, ale teraz mam na to dowód w ich logach.

Przy 8 dniach **najcenniejszą rzeczą nie jest nowy lever, tylko doprowadzenie JEDNEGO kernela
do stanu COMPLETE**. Każdy dzień bez nowego pomiaru to dzień, w którym wszystkie spory
(44.8 vs 42.2, 1.13 vs 5.2 akcji/wywołanie, T1 vs T2 vs T3) pozostają nierozstrzygalne.

---

## 2. Run-killer c45: finding był PRAWDZIWY, ale jest już naprawiony — i jest źle zaadresowany

DeepSeek pisze, że `duck-c45/kernel-metadata.json` deklaruje zbiory linii wolnej
(`jeroencottaar/…`, `driessmit1/…`), podczas gdy cell 9 czyta zbiory Franzena, więc run padnie
w komórce 17.

**Stan faktyczny, który pobrałem dziś z ich repo:**

`duck-c45/kernel-metadata.json`:
```json
"dataset_sources": ["dfranzen/pennyroyal-v253", "dfranzen/taaf-kaggle-source-bundle-copy"],
"model_sources":   ["dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1",
                    "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1"],
"competition_sources": ["arc-prize-2026-arc-agi-3"],
"machine_shape": "NvidiaRtxPro6000"
```

Ścieżki czytane przez notebook (wyciągnięte z wszystkich 30 komórek):
```
/kaggle/input/competitions/arc-prize-2026-arc-agi-3
/kaggle/input/datasets/dfranzen/...
/kaggle/input/models/dfranzen/...
```

**Metadana i kod SIĘ POKRYWAJĄ.** Żadnego `jeroencottaar`, żadnego `driessmit1`.

Historia commitów tego pliku wyjaśnia rozbieżność:

```
9c05c701  2026-10-24 21:55:52  duck-c45 (DeepSeek candidate-45): OCENA 4.5/5 — PRZYJETY na slot
                               25.10; ... metadata title=slug pin v5-proof; ...
26234603  2026-10-25 10:45:18  r072: output reruna v5 (diagnoza ERROR #57607527);
                               c45 metadata FIX wg a450-review: dfranzen SGLang+Qwen3.8+drafter
                               (kod c45 = szybka linia; moja stara metadata = crash na montazu)
```

Czyli, oddając sprawiedliwość obu stronom:

1. **DeepSeek miał rację** — stara metadana c45 była „pin v5-proof", więc crash na montażu był
   realny. To nie jest zmyślony finding.
2. **Został naprawiony 25.10 o 10:45 UTC** inną drogą („wg a450-review"), zanim pakiet v9
   trafiłby do użycia. Commit wprost przyznaje: „moja stara metadata = crash na montazu".
3. **Lista `jeroencottaar/driessmit1`, którą DeepSeek cytuje jako metadaną c45, należy do
   `arc3-duck-original` v5** — dowodem `r072/taaf_setup_env.json` (§1). Czyli doszło do
   podmiany attribucji: opis błędu prawdziwy, plik wskazany zły.
4. **Konsekwencja dla v9:** „naprawiona metadana" w pakiecie v9 jest dziś **redundantna**.
   Wartość v9 to co innego — przełącznik `PROFILE` i komórka pomiarowa (§3), nie metadana.

---

## 3. Komórka pomiarowa v9 jest najcenniejszą częścią tego pakietu — bo rozstrzyga spór, którego DeepSeek nie rozstrzygnął

### Sprzeczność wewnątrz własnej analizy

| źródło | twierdzenie |
|---|---|
| `OCENA` pkt 4 | „`ls20` robi **13,9** akcji na wywołanie", „`su15` robi **1,85**", „średnio model robi już **5,2** akcji/wywołanie — **nie ma tam 4× zapasu**, który obiecuje recenzja Gemmy" |
| `LEPSZA-DROGA` §2 | `ls20` 180 wywołań / 250 akcji = **1,39**; `su15` 213/157 = **0,74**; 8 gier razem 1417/1595 = **1,13** |

**Te same wielkości różnią się ~10×.** Tabela z `LEPSZA-DROGA` jest wewnętrznie spójna
(250/180 = 1.39 ✓, 1595/1417 = 1.13 ✓), więc to liczby „13,9 / 5,2" są podejrzane.

Sprawdziłem spójność tabeli z moimi własnymi pomiarami r019: 1.74 M tokenów / 2065 akcji = 841.
Jeśli wywołań było ~1417–1800, to tok/wywołanie ≈ 950–1230, a akcji/wywołanie ≈ **1.15–1.45**.
**To zgadza się z tabelą 1.13, a NIE z 5.2.**

### Dlaczego to jest najważniejsza liczba w projekcie

Bo od niej zależy, czy tor **T2** (plan-then-execute: model pisze pętlę `action([...])`
z warunkami stopu zamiast jednej akcji) ma w ogóle zapas:

- jeśli akcji/wywołanie = **1.13** → jest **~4× zapasu** do 5, a T2 atakuje dokładnie zmierzone
  wąskie gardło. DeepSeek's „×2–3 akcje/call" jest wtedy realne.
- jeśli akcji/wywołanie = **5.2** → zapasu nie ma i T2 jest kosmetyką. **Sam DeepSeek pisze wtedy
  „nie ma tam 4× zapasu"** — czyli własnym zdaniem podcina T2.

Oba zdania padły w tej samej analizie. **Nie da się jednocześnie uzasadniać T2 i go odrzucać.**

Do tego dochodzi rozjazd z Gemmą: ich 3665 tok/decyzję przy 841 tok/akcję implikuje
**4.36 akcji/decyzję**, co jest bliższe „5.2" niż „1.13". Czyli dwie sesje zmierzyły tę samą
wielkość i wyszło im 1.13 oraz 4.36. **Ktoś się myli i nikt tego nie zauważył.**

> **Komórka pomiarowa v9 wypisuje `calls`, `actions`, `actions/call`, `tok/action`, `tok/call`
> per gra. To jest dokładnie ten przyrząd, który rozstrzyga spór — i dlatego warto ją wziąć
> z pakietu v9 niezależnie od tego, czy weźmie się resztę.** Koszt: zero tokenów, zero GPU.

Uwaga metodologiczna: rozjazd może wynikać z definicji „wywołania". Jeśli Gemma liczyła tylko
wywołania analizatora z rozumowaniem, a DeepSeek wszystkie żądania HTTP (w tym retry i krótkie
zapytania), obie liczby mogą być „poprawne" przy różnych mianownikach. **Dlatego potrzebna jest
jedna definicja w jednym miejscu** — komórka v9 ją narzuca.

---

## 4. Argument DeepSeek o replayu jest poprawny — i obala MÓJ playbook, czego DeepSeek nie zauważył

DeepSeek: „replay i ×4,4 pamięci między replikami nie istnieją w ocenianym runie — brak
powtórzonych `game_id`, `n_passes=1`". **Zweryfikowałem to w ich kodzie i jest silniejsze,
niż myślałem.**

`taaf/competition_arcade.py:1-6` (docstring modułu):
```
The real Kaggle submission path talks to a gateway-backed Arcade with
competition constraints: one scorecard, hidden baselines, and no repeated
game IDs within that scorecard. This module starts the same ``arc_agi``
REST app on localhost against the bundled offline games so those failures
can be reproduced before submission.
```

`clone_game_ids` (L67-68):
```
Repeating a 25-game list to 110 entries therefore needs cloned IDs on
the simulator side.
```

`official_110()`: `game_ids=official_game_ids()` (25 gier, twarda asercja `!= 25 → RuntimeError`),
`total_runs=110`, `clone_prefix="k"` → ID `k000`…`k109`.

Czyli **klony są artefaktem symulatora** — istnieją właśnie dlatego, że prawdziwy scorecard
nie powtarza ID. Do tego oficjalnie: eval to **110 prywatnych gier, których agent nie widział**
(55 public LB + 55 private LB), a 25 publicznych gier jest **do lokalnego developmentu**.

### Konsekwencja, której DeepSeek nie wyciągnął

Ten sam argument, który zabija replay, **zabija mój literalny playbook**:

| artefakt | kluczowany przez | czy działa na 110 nieznanych grach |
|---|---|---|
| replay a450b00f | `game_id` | ❌ brak powtórzonych ID |
| replay po hashu ramki (Gemma) | sygnatura ramki | ❌ brak klonów do przeniesienia |
| pamięć między replikami ×4.4 | cykliczny roster | ❌ roster nie jest cykliczny w ocenie |
| **mój playbook (11 gier, 16 poziomów)** | **nazwa gry + gotowa sekwencja** | ❌ **te gry nie wystąpią** |

Mój zapis „**3.18 pkt LB podłogi**" był więc **za mocny**: to wynik na **symulatorze lokalnym**.
Uczciwie zaznaczałem niepewność (`DIAGNOZA`: „nie wiemy, czy prywatny roster to te same gry"),
ale potem i tak etykietowałem to jako „pkt LB" w czterech miejscach. **Poprawione** w
`PATCH-0004-I-SEARCH.md` i w tym dokumencie.

**Co przeżywa** (bo nie jest kluczowane nazwą gry, tylko działa w czasie rzeczywistym):

- `arc3_search.py` jako **search uruchamiany w harnessie** — działa na dowolnej grze, nie wymaga
  prekomputacji. To jest właściwa forma mojej pracy i ona **nie** jest martwa.
- **kalibracja ruchów po efekcie** (`calib_probe.py`) — grupowanie po hashu efektu zamiast po
  geometrii; odblokowała ft09 (288/4096 responsywnych, wszystkie dokładnie 38 px). Przenosi się
  na gry nieznane, bo nie potrzebuje wiedzieć, co to za gra.
- **twierdzenie o capie, arytmetyka budżetu, model ekonomii tokenowej** — zależą od formuły
  i budżetów, nie od konkretnej gry.
- triage `sum_baseline` — **tylko jako rozkład a priori**: baseline'y w ocenie są „hidden",
  więc dla nieznanych gier nie znamy ich, ale rozkład z 25 publicznych jest sensownym priorem.

**Co umiera:** wstrzykiwanie gotowych sekwencji per gra. Playbook zostaje jako **dowód metody
i fixture testowy** (11/25 gier, każda sekwencja zweryfikowana replayem na świeżej instancji),
nie jako podłoga punktowa.

---

## 5. Oficjalna metodologia potwierdza moją formułę — i wykrywa mój błąd w warunku capu

Pobrałem `docs.arcprize.org/methodology`. Zgadza się z tym, co wyprowadziłem z ich `taaf/game.py`:

| element | oficjalnie | u mnie |
|---|---|---|
| metryka | **RHAE** (Relative Human Action Efficiency) | ✓ |
| baseline | **upper median** graczy pierwszorazowych (nie średnia) | ✓ |
| score poziomu | `(human_baseline / ai_actions)²` | ✓ |
| cap poziomu | **1.15×** | `min(115, …)` ✓ |
| wagi poziomów | **numer poziomu 1-indeksowany** | `k+1` ✓ |
| cap gry | `Σw(ukończone)/Σw(wszystkie)`, przykład **10/15 = 66.7 %** | ✓ twierdzenie o capie |
| wynik końcowy | średnia po wszystkich grach | ✓ |
| co NIE jest akcją | „tool calls, reasoning steps, retries" | ✓ — i to **wspiera T2/T3**: planowanie w kodzie jest darmowe punktowo |

Ten ostatni wiersz jest ważniejszy, niż wygląda: **oficjalnie wyszukiwanie, retry i rozumowanie
nie są akcjami**. Czyli przeniesienie planowania do Pythona (paper01, mój `arc3_search.py`)
nie tylko nie kosztuje punktów — jest jedynym sposobem kupienia głębokości bez płacenia
w mianowniku `(B/A)²`.

### Mój błąd, który przy tym wyszedł

`FAKTY-I-POMIARY.md` L521 twierdziło:

> Jeśli każdy ukończony poziom zagrano w `a_k <= b_k * sqrt(115/100) = 1.0724 * b_k` akcji,
> to `score_k = 115`

**To jest odwrócona nierówność.** `(b/a)² · 100 ≥ 115` wymaga `b/a ≥ 1.0724`, czyli
**`a ≤ 0.9325 · b`**. Sprawdzenie:

| `a` względem `b` | score poziomu |
|---|---|
| 0.9325 × b | **115.00** ← cap |
| 1.00 × b | 100.00 |
| 1.0724 × b | **86.95** ← a nie 115 |

**Warunek jest ostrzejszy, niż pisałem:** agent musi być ~6.75 % **szybszy** od człowieka,
a nie „do 7 % wolniejszy". Poprawione w `FAKTY-I-POMIARY.md`.

**Wniosek twierdzenia pozostaje ważny** (przy capie wynik zależy wyłącznie od tego, *które*
poziomy ukończono), a empiria go wspiera: DeepSeek policzył **21 z 32 ukończonych poziomów
dokładnie na 115, mediana wyniku poziomu = 115**. To trzecie niezależne potwierdzenie
(Gemma: 17/27; moje wyprowadzenie z `taaf/game.py`; teraz oficjalna metodologia). Skoro mediana
= 115, agent **faktycznie** bywa szybszy od baseline'u pierwszorazowego gracza — więc warunek
0.9325 jest w praktyce często spełniony, mimo że jest ostrzejszy, niż sądziłem.

---

## 6. paper01 (world model + planer) — jedyny tor z dowodem, ale z trzema zaporami

Tabela DeepSeek: na **tych samych 10 grach z r019** duck daje 27.21 (32/69 poziomów),
world model z GPT-5.5 daje **56.81 (54/69)**, a z GPT-5.4 — **24.67 (35/69)**. Zamyka ogon:
ls20 1/7 → 7/7, tn36 1/7 → 7/7, g50t 2/7 → 7/7, ka59 3/7 → 7/7.

To jest dokładnie ten ogon, który **ja mam w `failure_mode`**: tn36 `time_cut`, ka59
`frontier_exhausted`, g50t `frontier_exhausted`, ls20 — mój search też go nie złamał
(3.57 w playbooku, 1 poziom). Więc niezależne podejście rozwiązało gry, na których mój BFS
i ich pętla LLM poległy. **To jest najmocniejszy pojedynczy argument w całej dyskusji.**

Równie ważny jest wynik negatywny: **GPT-5.4 daje 24.67, czyli PONIŻEJ ducka 27.21.**
DeepSeek trafnie tłumaczy dlaczego — model odkrywał poziomy, ale za drogo (dc22: 1568 akcji
na 4 poziomy), a `(B/A)²` karze to bezlitośnie. Czyli **planer nie jest darmowym +30 pkt:
jest mnożnikiem jakości modelu świata**. Zły symulator = gorszy wynik niż pętla LLM.

Trzy zapory, których nie wolno pominąć przy planowaniu slotów:

1. **Budżet akcji.** Paper używał **1500 akcji na poziom**. Nasz budżet to **~206 akcji na
   całą grę** (175k tokenów / 841). To różnica rzędu **7–50×**. Planowanie w modelu jest
   darmowe punktowo (§5), więc plan może być krótki — ale *zbudowanie* modelu wymaga prób,
   a te w paperze mieściły się w limicie, którego my nie mamy.
2. **Model.** Paper testował wyłącznie GPT-5.4/5.5 **przez API**. W konkursie API jest
   zabronione (brak internetu). Z lokalnym Qwen **nikt tego nie zmierzył** — DeepSeek mówi to
   wprost i ma rację.
3. **Zbiór.** Tylko public set, pojedyncze przebiegi, private nietestowany. Kolumna WM to
   **sufit publicznego setu**, nie prognoza.

**Routing zamiast wymiany silnika** (unia per gra = 69.69; na 7/10 gier wygrywa planer, na 3 —
dc22, sc25, s5i5 — pętla LLM) jest trafnym wnioskiem i **zgadza się z moim triage**:
sc25 i dc22 to u mnie `frontier_exhausted`, czyli gry, w których mój search też nie dał rady.
Dwie niezależne metody wskazują **te same trzy gry** jako oporne na planowanie. To nie przypadek
i warto to traktować jako sygnał, nie szum.

---

## 7. Co biorę, co odrzucam, co jest do rozstrzygnięcia

| pozycja DeepSeek | werdykt |
|---|---|
| formuła odtworzona co do 0.0000 | ✅ potwierdzone, teraz także z oficjalnej metodologii |
| 21/32 poziomów na capie 115, mediana 115 | ✅ trzecie niezależne potwierdzenie tw. o capie |
| deadline: 26 X entry, 2 XI final, 8 dni | ✅ zgodne z moim pobraniem strony Kaggle |
| Franzen 38.85 = sufit tej linii | ✅ zgodne z moim live LB |
| replay / pamięć między replikami = 0 pkt | ✅ **potwierdzone w `competition_arcade.py`** — i rozszerzone: zabija też mój playbook (§4) |
| `game_weights` nic nie realokują | ✅ zgodne z moim ustaleniem |
| c45 nie uruchomi się przez metadanę | ⚠️ **było prawdziwe, już naprawione 25.10 10:45** („wg a450-review"); lista `jeroencottaar/driessmit1` należy do `arc3-duck-original` v5, nie do c45 (§2) |
| `SCOPE='game'` jest poprawne, walidator `("turn","levelup","game")` | ⚠️ **niezweryfikowane przeze mnie** — ale jeśli tak, to **moja dźwignia nr 4 (`SCOPE=run`) używa wartości spoza walidatora** i jest martwa. Do sprawdzenia przed jakimkolwiek slotem |
| akcji/wywołanie = 1.13 | ⚠️ **spójne z moimi pomiarami r019**, ale sprzeczne z ich własnym „5.2" i z Gemmy „4.36" (§3). Rozstrzyga komórka pomiarowa v9 |
| T2 plan-then-execute | ✅ kierunek poprawny (oficjalnie retry/rozumowanie nie są akcjami), ⚠️ **zapas zależy od nierozstrzygniętej liczby** |
| T3 scaffold paper01 | ✅ jedyny tor z dowodem na 45+, ⚠️ trzy zapory: budżet 7–50× mniejszy, brak pomiaru na lokalnym modelu, tylko public set |
| T1 c45/v9 = 35–39 | ⚠️ **nie do oszacowania, dopóki żaden kernel szybkiej linii nie dojedzie do COMPLETE** (§1) |
| „realistycznie 35–45, pieniądze: nie" | ✅ **zgadzam się** i to jest uczciwe postawienie sprawy |

---

## 8. Kolejność, którą bym wykonał (8 dni, ~8 cykli punktowanych)

Priorytet wynika z §1: **brak nowego pomiaru od dziewięciu dni jest większym problemem niż
wybór levera.**

1. **Doprowadzić JEDEN kernel szybkiej linii do `COMPLETE`.** Nie v9-vs-c45, nie profil,
   nie lever — po prostu żeby rerun przeszedł. Bez tego każdy następny punkt jest gdybaniem.
   Potrzebny pełny log kernela z rerunu (32 linie z fazy ładowania wag to za mało, §1).
2. **Wziąć z v9 komórkę pomiarową** (`calls`, `actions`, `actions/call`, `tok/action`,
   `tok/call` per gra + `v9_metrics.json`). Zero tokenów, zero GPU, a rozstrzyga spór
   1.13 vs 4.36 vs 5.2 — czyli czy T2 ma ~4× zapasu, czy zero (§3).
3. **Przełącznik `PROFILE`** jako mechanizm „jedna zmienna na slot" — zgodne z ich własną
   zasadą i z moją rekomendacją z `EKONOMIA-TOKENOW.md` §9.
4. **Sprawdzić walidator `ARC3_PERSISTENT_FUNCTIONS_SCOPE`** zanim ktokolwiek wyda slot na
   pamięć między grami. Jeśli przyjmuje tylko `turn|levelup|game`, moja dźwignia 4 jest martwa
   i trzeba ją wykreślić (podobnie jak wykreśliłem replay).
5. **T2 przed T3.** T2 jest tańszy (1 slot) i atakuje zmierzone wąskie gardło; T3 to 3–4 sloty
   i jedyny tor z dowodem, ale z trzema zaporami (§6). Przy ~8 cyklach nie ma miejsca na
   rozpoczęcie T3 bez wcześniejszego T1/T2.
6. **Nie liczyć playbooka do prognozy.** Zostaje jako fixture i dowód, że offline search
   rozwiązuje te gry; do harnessa idzie **search uruchamiany w czasie rzeczywistym**, nie
   gotowe sekwencje (§4).

Czego nie robić: replay w jakiejkolwiek formie kluczowanej grą lub ramką, `game_weights`,
sama zmiana modelu, więcej niż jedna zmienna na slot, oraz — moje własne, świeżo poprawione —
nie powoływać się na „3.18 pkt LB" i na warunek capu „1.0724×".
