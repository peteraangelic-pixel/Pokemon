# v16 — warstwa analityczna: +1 poziom na grę. Tyle brakuje do 50.

> **Uwaga o nazwie.** `duck-v15` **już istnieje** na `arena/a450b00f-pokemon`
> (commit `8d96c68`): to v14 Gemmy + patch 0007 (eskalacja względna), zweryfikowany
> na r033. **To jest pakiet do wysłania.** Ten dokument nie konkuruje z nim —
> jest **warstwą analityczną**, która mówi, co po nim zmienić i co zmierzyć.

**Data:** 2026-10-30 · **Baza:** v13.2 (`6b10853`) + v14 z `Gemma-konkurs@c4eeb067` (`b38b82e`).
**Kod:** `local/metric.py`, `local/v15_policy.py` (nazwy plików historyczne), testy `local/test_metric.py` (8/8),
`local/test_v15.py` (12/12).

---

## 0. Nagłówek: cel jest mniejszy, niż myślałem

Zmierzone na r018 i przeliczone **poprawną** regułą punktacji:

| | wartość |
|---|---|
| pokrycie dziś | **29,0%** → wynik ~29 |
| pokrycie potrzebne na 50 | **50,0%** |
| brakuje | 21 pkt procentowego |
| to znaczy | **+1,1 poziomu na grę** (3,2 → 4,3) |
| koszt przy naszych 42 akcjach/poziom | **+46 akcji na grę** |
| budżet dziś → potrzebny | 206 → **253 akcji (+22%)** |

**Do 50 nie brakuje 2× przepustowości. Brakuje jednego poziomu na grę.**

I mamy już na to miejsce: **72 akcje na grę idą na próby, które nigdy się nie kończą.**
To 1,7 poziomu przy naszym średnim koszcie. Nie trzeba nowego budżetu — trzeba
zamienić połowę marnowanych prób w jeden ukończony poziom.

To odwraca framing z `MEGA-DIAGNOSIS` §4 („potrzeba 400 akcji"). Tamta liczba
zakładała równą efektywność na wszystkich poziomach; w rzeczywistości **na
ukończonych poziomach jesteśmy 1,7× szybsi od człowieka** (42 vs 71 akcji), więc
jesteśmy pod sufitem 115 i cap ukończenia jest jedynym wiążącym ograniczeniem.

---

## 1. Poprawiona reguła punktacji — moja była błędna, Gemma ma rację

Reguła (`taaf/game.py::_compute_final_score`, za `arc_agi.scorecard v0.9.8`):

```
dla k = 1..n:  w_k = k
               s_k = min(115, (baseline_k / actions_k)² · 100)   jeśli k ≤ ukończone
               s_k = 0                                           w przeciwnym razie
raw   = Σ s_k·w_k / Σ w_k
cap   = 100 · (ukończona waga) / (całkowita waga)
score = min(raw, cap)
```

Weryfikacja na 30 zapisanych `final_score` z `local/benchmarks/`:

| implementacja | zgodność |
|---|---|
| **poprawna: `min(115,…)` + cap ukończenia** | **30/30 dokładnie** |
| moja „poprawka" na cap 1,0 (`1541d08`… `score.rs`) | 9/30 |
| moje stare cap 1,15 | 2/30 |

**Moja zmiana `1,15 → 1,0` z `3269393` pogorszyła metrykę**, a obie wersje
brakowały capa ukończenia. Poprawione w `rust/src/score.rs` (`game_score`,
`level_points` + 6 testów) i w `local/metric.py`.

### 1.1 Konsekwencja, która upraszcza całą strategię

```
score = min(raw, cap) ≤ cap = 100 × pokrycie
```

**Wynik nigdy nie przekroczy 100 × pokrycia.** Bicie człowieka nie pomoże, jeśli
nie ukończysz poziomu. Cała gra to pokrycie.

---

## 2. Co daje v14 z `Gemma-konkurs` — i czego nikt inny nie zauważył

v14 (`b38b82e`) to **v13.2 + cztery zmiany**, wszystkie uzasadnione:

| # | zmiana | ocena |
|---|---|---|
| 1 | `ESCALATE_ACTIONS` **10 → 20** | ✅ **mają lepszy pomiar niż ja.** Na 32 ukończonych poziomach r085: przy 10 dyrektywa odpala **154×** (15,3% puli tokenów gry) i na **31/32** poziomach każe przestać próbować, gdy agent jest na tempie człowieka lub lepszy |
| 2 | hook sondy w `try/except` | ✅ usuwa ryzyko martwego notebooka przed startem |
| 3 | sonda rosteru (po biegu) | ✅ rozstrzyga, czy pamięć win-path jest warta 0 czy +5…15 |
| 4 | sonda budżetu (przed biegiem) | ✅ loguje `cap_over_fair`, którego nikt nie logował |

**Poprawiam swoją rekomendację.** W `V13-1-VERIFICATION.md` §3 pisałem „zejść
z eskalacji 60 → ~8–10". To było oparte na błędnej premii „1 akcja na turę".
Gemma zmierzyła to, czego ja nie zmierzyłem, i **20 jest lepsze niż 10, a zakres
30–60 z mojego §9.3 jest wciąż za wysoki** — względny próg jest właściwym
rozwiązaniem, nie żadna stała.

Ich `PROPOZYCJA-0007` (próg względny `max(20, 1,2 × baseline[poziom])`) daje
**8 wstrzyknięć, 0/32 przedwczesnych**. To jest cel.

### 2.1 ✅ LUKA DOMKNIĘTA — i odpowiedź jest NEGATYWNA

Gemma pisała: *„nie wiem, jak `ToolAgent` się do baseline'u dostaje"*. `duck-v15`
(`8d96c68`) to sprawdził na r033 i **domknął pytanie — negatywnie**:

> *„**Submission-mode behaviour:** the engine hides baselines
> (`base_actions_per_level is None`), so the relative rule degrades to v14's
> absolute 20 + the per-level cap of 2 — the measurable win is local/smoke;
> **the cap is the part that also applies on the rerun**."*

**Czyli: w rerunie baseline'u NIE MA.** Plomby w `game_run` istnieją (30/30
w naszych zapisach), ale silnik je **zeruje w trybie submisji**.

Konsekwencje, które przeformułowują ten dokument:

| twierdzenie | status |
|---|---|
| „governor z baseline'em zamienia zakład w arytmetykę" (§3.1) | **prawdziwe tylko lokalnie/smoke**, nie w rerunie |
| eskalacja względna `max(20, 1.2×baseline)` | **w rerunie degraduje do 20** |
| **per-level cap 2 eskalacje** | **✅ działa w rerunie** — to jedyna część patcha 0007, która przeżywa |
| sonda `baseline=yes/no` | **✅ nadal potrzebna** — potwierdza to na żywo i mierzy `coverage` |

Nie usuwam `baseline_available()` ani `GameGovernor` — bo (a) działają lokalnie
i w smoke, (b) **degradują bezpiecznie** do capa 120 i eskalacji 20, co jest
przetestowane (`test_no_baseline_reproduces_floor_behaviour`). Ale **nie liczę
na nie w rerunie.** Punkt ciężkości przesuwa się na §3.2 i §0.

---

## 3. Co dokłada ta warstwa — trzy rzeczy, każda tania

### 3.1 Governor świadomy baseline'u — **tylko lokalnie i w smoke** (patrz §2.1)

Skoro `score ≤ 100 × pokrycie`, a znamy `baseline_k`, to decyzja „dalej czy
porzucić" **przestaje być zakładem**:

```python
budżet_poziomu   = akcje, przy których poziom wciąż daje ≥ min_marginal punktów
                 = actions_needed_for(min_marginal, baseline_k)
eskalacja        = max(20, 1.2 × baseline_k)      # zamiast stałej
```

Mój symulator z `V14-PLAN.md` §3 dawał widełki **−19,5 … +2,9** właśnie dlatego,
że **nie używał baseline'u**. Z baseline'em to arytmetyka, nie widełki.

**Ale w rerunie baseline'u nie ma** (§2.1), więc ta arytmetyka tyczy się tylko
smoke'ów i lokalnego silnika — tam jest wciąż użyteczna, bo pozwala dobrać
`level_cap_floor` na podstawie prawdziwych kosztów, zamiast zgadywać 120.

Degradacja jest bezpieczna i przetestowana
(`test_no_baseline_reproduces_floor_behaviour`).

### 3.2 Log, który rozstrzyga wszystko — cztery liczby na grę

```
duck-v16 probe: game=<id> levels=<L> completed=<k> coverage=<c> baseline=<yes|no>
           budget=<n> escalate_at=<n> score=<s>   /* log, ktory chcemy zobaczyc */
```

To jest jedyny sposób, by po jednym przebiegu wiedzieć:
1. czy baseline jest w ogóle dostępny w rerunie (`baseline=yes/no`) — **rozstrzyga,
   czy governor jest dokładny czy zgrubny**;
2. ile pokrycia realnie mamy (`coverage`) — **wprost przekłada się na wynik**;
3. czy eskalacja trafia we właściwe poziomy (`escalate_at` vs `baseline`).

### 3.3 Zamiana marnowanych prób w poziom — polityka „+1"

Z 72 akcji na grę idących na nieukończone próby, governor wybiera **jeden**
poziom do dokończenia zamiast rozpraszać wysiłek:

```
priorytet_poziomu = (waga_poziomu / całkowita_waga) / koszt_poziomu
```

gdzie koszt = `baseline_k` (znany) albo `median(koszt ukończonych w tej grze)`.
To ta sama arytmetyka co `local/scheduler.py`, ale **wewnątrz gry i z baseline'em**,
a nie między grami bez wiedzy o kosztach.

---

## 4. Uczciwa ocena: v13.2 vs v14 (Gemma) vs duck-v15 vs ta warstwa

| | v13.2 | v14 (Gemma) | **ta warstwa** |
|---|---|---|---|
| reguła punktacji poprawna | nie (nasze narzędzia) | ✅ 30/30 | ✅ 30/30 + `metric.py` |
| `ESCALATE_ACTIONS` | 10 (za nisko, zmierzone) | **20** (zmierzone) | **względny `max(20,1.2×baseline)`** z fallbackiem 20 |
| porzucanie poziomu | brak | brak | **arytmetyka, nie zakład** (gdy baseline) |
| sonda rosteru | brak | ✅ | ✅ (dziedziczona) |
| sonda budżetu | brak | ✅ | ✅ (dziedziczona) |
| sonda baseline'u | brak | brak | ✅ **nowa, rozstrzyga dokładność** |
| log pokrycia | brak | brak | ✅ **nowa, wprost = wynik** |
| baseline w rerunie | — | **None** (zmierzone) | **None** (potwierdzone sondą) |
| prognoza | 28–38 | 26–31 | **28–33** (sam governor), **45–55** (z +22% budżetu, §0) |

**v16 nie jest skokiem na 50 przy obecnym budżecie.** Jest warstwą, która:
(a) naprawia metrykę po naszym błędzie, (b) przyjmuje lepszy pomiar Gemmy,
(c) dodaje jedyne narzędzie, które może zamienić zakład w decyzję,
(d) mierzy dokładnie to, czego brakowało.

**Skok na 50 wymaga +22% budżetu akcji** (§0) — czyli ~253 akcji/gę, czyli
~716 tokenów na akcję zamiast 853. To cięcie A z `V14-PLAN.md` §2.1.

---

## 5. Uczciwy rejestr: co ten dokument prostuje

| # | moje wcześniejsze twierdzenie | prawda |
|---|---|---|
| 1 | cap 1,15 → 1,0 to „poprawka" | **odwrotnie** — 1,15 było bliżej; właściwa reguła ma `min(115,…)` **i** cap ukończenia (30/30) |
| 2 | „potrzeba ~400 akcji na 50" | **~253 akcji** (+22%), bo na ukończonych poziomach jesteśmy 1,7× szybsi od człowieka |
| 3 | „eskalacja 60 → 8–10" | **20 ma lepsze uzasadnienie pomiarowe** (Gemma, 32 poziomy r085); docelowo próg względny |
| 4 | „porzucanie = zakład −19,5…+2,9" | **tak — i tak zostaje w rerunie**, bo baseline jest tam `None` (§2.1) |
| 5 | „baseline pozwoli policzyć decyzje dokładnie" | **nie w rerunie**; `duck-v15` zmierzył `base_actions_per_level is None` w trybie submisji |

---

## 6. Kolejność wdrożenia

1. **Wysłać v13.2 albo v14 Gemmy z samą sondą** (1 slot) — żeby dostać
   `baseline=yes/no` i `coverage`. Bez tych dwóch liczb każda dalsza decyzja
   jest zgadywaniem.
2. **Governor** — po sondzie. W rerunie działa jako stały cap; w smoke z baseline'em.
3. **Cięcie tokenów** (`V14-PLAN.md` §2.1 cięcie A: `expect` tylko na kluczowych
   krokach) — to jedyna droga do +22% budżetu, a więc do 50.

**Co wysłać:** `duck-v15` z `a450b00f` (`8d96c68`) — jest zweryfikowany na r033
i zawiera wszystko, co ma sens w rerunie (20 + cap 2 + sondy + guard GAME_OVER).
Mój wkład to §0 (metryka i cel +1 poziom), §5 (rejestr) i §3.2 (log pokrycia).

**Czego nie zrobiłem:** nie tknąłem `arena/a450b00f` ani `Gemma-konkurs`, nie
wysłałem submitu, nie mam bundla r033, więc żadnego patcha nie mogę zweryfikować
`git apply`. Specyfikacja patcha jest w §3, kod polityki jest przetestowany.
