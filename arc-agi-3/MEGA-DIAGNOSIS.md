# Dlaczego 23 i jak zrobić 50+ — diagnoza na danych z r013 / r015 / r018

**Data:** 2026-10-29 · **Deadline:** 2026-11-02 · **Źródło liczb:** `benchmark.json` z trzech realnych runów Kaggle (`duck/ops/results/r013-push`, `r015-push`, `r018-push`, gałąź `arena/98ddb59f-pokemon`).

Wszystkie liczby poniżej są policzone z surowych artefaktów runów — pól `base_actions_per_level` (baseline człowieka), `actions_per_level` (nasze akcje), `levels_completed`, `number_of_levels`, `history[]`. Nic nie jest estymowane "na oko".

---

## 0. Streszczenie w pięciu zdaniach

1. **23 to nie regresja.** Między runami mamy sd = 2,47 pkt, a pojedyncza gra skacze średnio o 11,7 pkt. 26,25 → 23 to −1,3 sd. Ten submit po prostu wylosował dolną część własnego rozkładu.
2. **Wynik to pokrycie poziomów × efektywność².** Nasza efektywność na poziomach, które kończymy, to **86–90%** — jesteśmy blisko sufitu.
3. **Pokrycie to 29%** i to jest cały problem: kończymy ~3 z 7 poziomów na grę.
4. **Przy naszym budżecie akcji sufit wynosi 18,7–31,9 pkt.** Jesteśmy na 79–100% tego sufitu. Dalsze strojenie strategii *przy tym samym budżecie* nie da 50 — nie ma z czego.
5. **Przyczyna źródłowa (POPRAWIONA 30.10): budżet jest w tokenach, nie w turach.** Robimy **4,61 akcji na generację** — nie 1,00, poprzednia liczba była artefaktem metody (§4). Na grę mamy **~186 200 tokenów**, a wydajemy **853 tokeny na akcję**. Żeby dojść do 50, trzeba ściąć tokeny na akcję do **~479 (−44%)**. Drugi, mnożnikowy lewar: **tempo silnika** — 15,8 ms/token u nas vs 62,6 ms/token w złym reżimie (3,6×, §4.4).

---

## 1. Formuła wyniku — zweryfikowana dokładnie

Reguła z oficjalnej strony danych:

```
wynik poziomu  = min(akcje_człowieka / akcje_agenta, 1.0)²
wynik gry      = Σ_{l=1..L} (l · wynik_poziomu_l) / Σ_{l=1..L} l     [poziomy nieukończone = 0]
wynik łączny   = średnia po wszystkich grach
```

Weryfikacja na naszych danych (nie zgadujemy — odtwarzamy):

| gra | poziomy | nasz wynik | (1+..+k)/(1+..+L) × efektywność² | harness `final_score` |
|---|---|---|---|---|
| su15 (r013) | 3 / 9 | 13,33 | (1+2+3)/45 = 13,33% × 100% = **13,33** | **13,33** ✅ |
| ka59 (r013) | 3 / 7 | 21,43 | 6/28 = 21,43% × 100% = **21,43** | **21,43** ✅ |
| g50t (r018) | 2 / 7 | 10,71 | 3/28 = 10,71% × 100% = **10,71** | **10,71** ✅ |
| s5i5 (r013) | 3 / 8 | 15,67 | 6/36 = 16,67% × 94% = **15,67** | **16,67** |

Nasza własna implementacja w `rust/src/score.rs` używała cap **1,15** (z arcagibook). Strona konkursu mówi **1,0**. Poprawione: `OFFICIAL_CAP = 1.0`, stare 1,15 zachowane jako `SCALED_CAP` do odtwarzania historii. Cap 1,15 zawyżał każdy poziom, na którym biliśmy człowieka, o do 32%.

**Konsekwencja: nie ma sensu być szybszym niż człowiek.** Po przekroczeniu parytetu każda dodatkowa oszczędność akcji daje zero. Cała gra to *liczba ukończonych poziomów*.

### Wagi są brutalnie zwrócone w stronę końca gry

Dla gry o 7 poziomach mianownik to 1+2+…+7 = 28:

| poziom | waga | udział |
|---|---|---|
| 1 | 1 | 3,6% |
| 3 | 3 | 10,7% |
| 5 | 5 | 17,9% |
| 7 | 7 | 25,0% |

Ukończenie pierwszych 3 poziomów gry 7-poziomowej = **21,4%**. Ostatnie dwa poziomy są warte więcej niż pierwsze trzy razem.

**Wniosek: krzywa wartości jest wypukła — opłaca się dokończyć grę, a nie zaczynać kolejną.**

---

## 2. Rozkład naszego wyniku

r018 (najnowszy pełny run), średnia = **25,09**:

| gra | L | k | pokrycie | efektywność | wynik |
|---|---|---|---|---|---|
| tn36 | 7 | 1 | 3,6% | 100,0% | 3,57 |
| m0r0 | 6 | 3 | 28,6% | 98,0% | 27,99 |
| cn04 | 6 | 4 | 47,6% | 95,2% | 45,32 |
| dc22 | 6 | 4 | 47,6% | 86,3% | 41,08 |
| ka59 | 7 | 3 | 21,4% | 75,8% | 16,24 |
| sc25 | 6 | 4 | 47,6% | 79,0% | 37,62 |
| s5i5 | 8 | 3 | 16,7% | 94,0% | 15,67 |
| ls20 | 7 | 1 | 3,6% | 91,5% | 3,27 |
| su15 | 9 | 7 | 62,2% | 79,4% | 49,42 |
| g50t | 7 | 2 | 10,7% | 100,0% | 10,71 |
| **średnio** | | | **29,0%** | **89,9%** | **25,09** |

**Efektywność 89,9% przy pokryciu 29,0%.** Gdybyśmy mieli pokrycie 55% przy tej samej efektywności, wynik wynosiłby **49,5**.

To jest cała diagnoza w jednej linijce: **nie jesteśmy nieefektywni, jesteśmy niekompletni.**

---

## 3. Sufit — ile da się wycisnąć z danego budżetu akcji

Symulacja: dla każdej gry idziemy poziom po poziomie, dopóki budżet akcji pozwala, przy założonej efektywności. Uśrednione po 10 grach r018.

| akcji / grę | sufit @ eff=100% | sufit @ eff=90% |
|---|---|---|
| 150 | 13,0 | 8,6 |
| 200 | 21,6 | 15,2 |
| **206 (nasz r018)** | **22,4** | **18,7** |
| **275** | **35,4** | 28,3 |
| **400** | **56,9** | **51,3** |
| 600 | 69,2 | 52,7 |
| 900 | 94,3 | 70,7 |

Nasze 25,09 przy budżecie 206 akcji/grę jest **powyżej** modelu (18,7–22,4), bo na łatwych poziomach bijemy człowieka (np. tn36 poziom 1: my 20 akcji, człowiek 32). Model jest więc konserwatywny — ale rząd wielkości jest niepodważalny.

**Przy ~206 akcjach na grę wynik 50 jest matematycznie niemożliwy. Nawet z idealną grą.**

Żeby dojść do 50, potrzeba **~400 akcji na grę** (przy naszej efektywności 90%).

---

## 4. Przyczyna źródłowa — ⚠️ SEKCJA PRZEPISANA 30.10 (poprzednia miała błąd metody)

> **POPRZEDNIA WERSJA BYŁA BŁĘDNA.** Twierdziłem: „6034 akcje / 6034 decyzje =
> 1,00 akcji na decyzję", licząc decyzje ze **wzrostu `wallclock_seconds`**.
> To był test tautologiczny: `wallclock_seconds` to **kumulatywny czas wykonania**
> i rośnie przy **każdej** akcji, więc metoda z definicji zwracała 1,00.
> Poprawny wskaźnik generacji LLM to `generated_tokens > 0`.

### 4.1 Ile naprawdę jest akcji na generację

Policzone na tych samych 6034 akcjach z 30 gier (`local/benchmarks/`):

| run | akcji | generacji (`gen>0`) | **akcji / generację** | **tok / akcję** |
|---|---|---|---|---|
| r013 | 2331 | 452 | **5,16** | 689 |
| r015 | 1638 | 382 | 4,29 | 1100 |
| r018 | 2065 | 474 | 4,36 | 841 |
| **razem** | **6034** | **1308** | **4,61** | **853** |

**Robimy 4,61 akcji na jedno wywołanie modelu — nie 1,00.** Batchowanie już
działa. Model generuje ~3933 tokeny na generację, a z tego wychodzi ~4,6 akcji.

### 4.2 Właściwy budżet jest w TOKENACH, nie w turach

Model jest ograniczony przepustowością dekodowania, nie liczbą tur:

```
czas na grę (EVAL-BUDGET-MODEL.md §2)   = 2 945 s
zmierzone tempo (nasze runy)            = 15,8 ms/token
────────────────────────────────────────────────────────
budżet tokenów na grę                   = 186 392 tok
przy dzisiejszych 853 tok/akcję         = ~218 akcji/grę
```

Sprawdzenie: tn36 wygenerowało 170 400 tokenów × 15,8 ms = **2693 s** z 2880 s
dostępnych — czyli **93% budżetu to dekodowanie**. Model nie „myśli długo między
ruchami"; **generuje dużo tokenów na każdą akcję**.

### 4.3 Prawdziwa dźwignia: tokeny na akcję, nie akcje na turę

| akcji/grę | wymagane tok/akcję | vs dziś (853) | wynik (sufit, §3) |
|---|---|---|---|
| 218 (dziś) | 853 | 1,00× | ~19–31 |
| **389** | **479** | **0,56×** | **~51** |
| 600 | 310 | 0,36× | ~62 |
| 736 | 253 | 0,30× | ~75 |

*(liczby odtwarza `local/token_budget.py`; tn36 osobno miał 170 400 tok / 234 akcje
= 728 tok/akcję, więc rozrzut między grami jest realny)*

**Żeby dojść do 50, trzeba ściąć tokeny na akcję o ~44%** — z 853 do ~479.
Nie przez „więcej ruchów na turę" (mamy 4,6), ale przez **mniej tokenów na ruch**:
albo więcej akcji z tej samej generacji, albo krótsze rozumowanie na generację.

### 4.4 Drugi, mnożnikowy lewar: tempo silnika (3,6×)

Niezależny audyt (`arena/c87f7a48-pokemon`, `AUDYT-4-GALEZI-30-10.md` §2) znalazł
ten sam model 8B przy **17,2 ms/token** w r085 i **62,6 ms/token** w r110 — różnica
**3,6×**, niepochodząca z modelu ani promptu. Mechanizm (ich hipoteza, z arytmetyką):
pula KV 1 011 264 tok przy 10 grach × 131 072 tok = 1 310 720 → **pula się nasyca**,
żądania kolejkują po miejsce w cache, a trim odpala dopiero przy 118k.

**Nasze runy są w szybkim reżimie: 15,8 ms/token** (zmierzone wyżej, z `history[]`).
To dobra wiadomość i zarazem **ryzyko**: przy 62,6 ms/token budżet spada do
47 045 tok → ~65 akcji/grę → wynik rzędu 7–10.

Dźwignia mnoży się z poprzednią:

```
akcje/gę = (budżet czasu / ms na token) × (1 / tokeny na akcję)
            ↑ lewar silnika 3,6×        ↑ lewar 4.3 (potrzebne 1,5×)
```

**Uwaga na uczciwość:** hipoteza KV/prefix-cache to hipoteza c87, nie moja —
nie zweryfikowałem jej. Ale **liczby 17,2 i 62,6 ms/token są z ich pomiaru**,
a moje 15,8 ms/token jest moim własnym, niezależnym pomiarem z `history[]`.

### 4.5 Co to znaczy dla v13.2 (`ESCALATE_ACTIONS` 60→10)

Skoro **już** robimy 4,61 akcji na generację, premisa mojej rekomendacji
(„model robi jedną akcję na turę, trzeba go zmusić do batchowania") **była
oparta na błędnej liczbie**. Eskalacja może więc nie mieć czego naprawiać.

Nie wycofuję samej rekomendacji — przy 60 eskalacja odpalała się 16 razy w biegu
(`V13-AUDIT-30OCT.md` §1A.1), czyli była praktycznie martwa, więc 10 jest lepsze
niż 60. Ale **uzasadnienie się zmienia**: nie „wymuś batchowanie", tylko „wymuś
przemyślenie strategii na poziomie, gdy akcje nie posuwają sprawy".

**Priorytetem jest teraz 4.3, nie 4.5.**

### Co to znaczy dla sufitów

| akcji / decyzję | akcji / grę | sufit @ eff=90% |
|---|---|---|
| **1 (nasze)** | 200 | **18,7** |
| 2 | 400 | **51,3** |
| 4 | 800 | **77,6** |
| 8 | 1600 | 100,0 |

**Podwojenie akcji na decyzję podnosi sufit z 18,7 do 51,3.** To jest jedyny lewar o właściwej skali. Wszystko inne (lepsze prompty, więcej poziomów notatek, world model) przesuwa nas o pojedyncze punkty w obrębie tego samego sufitu.

Dlaczego czołówka ma 75,56 przy podobnym limicie czasu i podobnym modelu? Bo zamienia te same ~96 decyzji na ~10× więcej akcji. Publiczne notatniki (maks 35,35) to warianty Ducka z akcją na turę — i dokładnie w tym samym miejscu, w którym my jesteśmy.

---

## 5. Drugi lewar: przydział akcji między gry (darmowy)

Skoro wynik to średnia po grach, a waga poziomu `l` w grze o `L` poziomach to `l / (1+…+L)`, to **wartość krańcowa ukończenia poziomu jest różna o rząd wielkości między grami**:

| gra | L | waga 1. poziomu | wartość 1. poziomu | wartość ostatniego |
|---|---|---|---|---|
| 4-poziomowa | 4 | 1 z 10 | **1/10 = 10,0%** | 4/10 = 40,0% |
| 7-poziomowa | 7 | 1 z 28 | **1/28 = 3,6%** | 7/28 = 25,0% |
| 9-poziomowa | 9 | 1 z 45 | **1/45 = 2,2%** | 9/45 = 20,0% |

**Ukończenie 1. poziomu gry 4-poziomowej jest warte 4,5× więcej niż 1. poziomu gry 9-poziomowej.**

> Poprawka 30.10: poprzednia wersja tej tabeli miała off-by-one — podawała
> 2/10 i 5/10, czyli wartość *drugiego* poziomu, nie pierwszego. Stosunek 4,5×
> był przypadkiem poprawny (2/10 ÷ 2/45 = 4,5), więc wniosek się nie zmienia,
> ale liczby bezwzględne były zawyżone. Odtworzenie: `local/test_v14.py`.

My rozdzielamy czas **równo** — wszystkie 30 gier skończyło dokładnie na 2880 s (10/10 przy limicie). To jest dokładnie odwrotność tego, co optymalne.

Symulacja na kosztach z r018. Polityka „równo" = każda gra dostaje tyle samo akcji. Polityka „greedy" = akcje idą do gry o najwyższej wartości krańcowej na akcję, gdzie koszt następnego poziomu szacujemy **wyłącznie z obserwacji** (prior C0 dla 1. poziomu, potem średni zaobserwowany koszt).

| budżet / grę | równo | greedy (C0=45) | greedy (C0=30) | zysk |
|---|---|---|---|---|
| 206 (nasze) | 18,7 | 24,2 | 22,9 | +5,5 |
| **275** | 28,3 | 36,3 | **40,3** | **+8,0** |
| 300 | 32,3 | 36,3 | 43,3 | +4,0 |
| **400** | **51,3** | **46,1** | 52,8 | **−5,1 … +1,5** |
| 600 | 65,1 | 72,4 | — | +7,3 |
| 900 | 87,3 | 100,0 | — | +12,7 |

### Trzy zastrzeżenia, które trzeba powiedzieć wprost

**1. Efekt jest wtórny i kruchy.** Zysk waha się od −5,1 do +12,7 w zależności od budżetu i przyjętego prioru. Mediana kosztu pierwszego poziomu w r018 wynosi **30** (mediana kosztu dowolnego poziomu: 72), więc C0=30 jest najbardziej obronny — ale przy C0=45 zysk przy budżecie 400 zmienia znak. **To lewar, który trzeba zmierzyć A/B, a nie założyć.**

**2. Greedy jest niemonotoniczny.** Przy 400 wypada gorzej niż przy 300 w wersji optymistycznej, bo potrafi przepalić budżet na poziomie, którego koszt zaniżył. Wariant pesymistyczny (koszt = maks. zaobserwowany) jest stabilniejszy przy niskich budżetach (wynik 29,2 przy 206, cap 2× średniej) i gorszy przy wysokich (37,9 przy 400).

**3. Scheduler sam nie zrobi 50.** Najlepszy wynik, jaki daje którakolwiek wersja przy budżecie 275, to 40,3. Resztę musi dowieźć lewar nr 1.

**Wniosek operacyjny:** wdrażać scheduler z C0=30 i pesymistyczną estymacją kosztu, ale **traktować go jako +0 do +8, nie +12**. Priorytetem pozostaje liczba akcji na decyzję.

---

## 6. Dlaczego ostatni submit dał 23

Nie znajduję w repozytorium logu tego submita (`kaggle-results/submissions.csv` kończy się na duck v3 = 26,25). Ale rozrzut własny jest zmierzony i wystarcza do wyjaśnienia:

| run | wynik (te same 10 gier) |
|---|---|
| r013 | 29,02 |
| r015 | 23,10 |
| r018 | 27,21 |
| **średnia** | **26,44** |
| **sd między runami** | **2,47** |

Pojedyncza gra potrafi skoczyć o dziesiątki punktów:

| gra | r013 | r015 | r018 | sd |
|---|---|---|---|---|
| tn36 | 42,8 | 29,9 | 3,6 | **16,3** |
| su15 | 13,3 | 13,3 | 56,4 | **20,3** |
| cn04 | 47,6 | 13,5 | 47,6 | 16,1 |
| m0r0 | 14,3 | 47,6 | 28,6 | 13,7 |

**23 = −1,3 sd od 26,25.** Statystycznie nierozróżnialne od „działa tak samo". Nie ma tu czego naprawiać w kodzie — jest co naprawiać w architekturze (§4).

(Zastrzeżenie: jeśli submit rzeczywiście był „atrapą", jak twierdzi post-mortem z commita `b64f580`, to 23 jest *zawyżone* — atrapa dostałaby 0. Wartość 23 wskazuje, że agent grał normalnie.)

---

## 7. Plan „MEGA" — kolejność wg stosunku zysku do ryzyka

### Krok 1 — akcje na decyzję: 1 → 3–4 (główny lewar, sufit 18,7 → 68–77)

Trzy warianty, w kolejności od najmniejszego ryzyka:

1. **Batch jawny** — model w jednej turze emituje listę ruchów (np. `RIGHT×4`, `ACTION6(12,30)`). Zero nowej infrastruktury; zmiana w formacie odpowiedzi i pętli wykonawczej.
2. **Powtórzenie do zmiany klatki** — jeśli akcja nie zmieniła klatki, wysyłamy ją ponownie *bez pytania modelu*. Koszt: 0 tokenów. Zysk zależy od gry, ale w grach z „chodzeniem w ścianę" jest duży.
3. **Planner lokalny (Rust + rayon)** — model podaje cel („dojdź do (x,y)" / „osiągnij stan S"), a planner wyznacza najkrótszą sekwencję akcji na wyuczonym modelu przejść i wykonuje ją, porównując każdą klatkę z predykcją. **Rozjazd predykcji = natychmiastowy powrót do modelu.** To jest wariant StochasticGoose i miejsce, w którym Rust naprawdę zarabia na siebie.

Kluczowa zasada bezpieczeństwa: **batch tylko wtedy, gdy gra jest deterministyczna i obserwowana.** Każde odchylenie od predykcji przerywa batch. Nie wolno palić akcji w ciemno — akcje wchodzą do mianownika.

### Krok 2 — scheduler wartości (darmowy, +0 do +8 pkt — mierzyć, nie zakładać)

Przydział akcji wg wartości krańcowej:

```
wartość_poziomu(k, L) = (k+1) / (L(L+1)/2)
koszt_następnego     = średni koszt ukończonych poziomów w tej grze (prior 45 przy k=0)
priorytet            = wartość / koszt
```

Akcje idą do gry o najwyższym priorytecie. Implementacja: `local/scheduler.py` (czysty Python, testowalny bez GPU).

**Warunek działania: ≥275 akcji/grę.** Dlatego krok 2 dopiero po kroku 1. I dlatego, że efekt przy budżecie 400 potrafi zmienić znak (§5), krok 2 wymaga pomiaru A/B na ≥20 powtórzeniach — inaczej to wróżenie.

### Krok 3 — dokończanie zamiast zaczynania

Krzywa wartości jest wypukła (poziom 7 wart 25% gry, poziom 1 wart 3,6%). Polityka: gdy gra jest blisko progu (np. 5/7), dostaje priorytet przed świeżą grą. To już wynika z kroku 2, ale warto trzymać jako jawną regułę.

### Czego NIE robić

- **Nie forków publicznych notatników.** Sufit publicznych artefaktów to 35,35 i wszystkie są w tym samym miejscu co my (1 akcja na turę).
- **Nie optymalizuj efektywności.** Mamy 86–90%; wyciśnięcie do 100% daje ×1,16 (25 → 29). Batch daje ×2,7.
- **Nie dokładaj poziomów notatek ani world modelu** przed krokiem 1. r015 (v4, +world model) dał 23,10 — czyli nic ponad szum, przy budżecie 206 akcji, gdzie sufit i tak wynosi ~19.

---

## 8. Realna ocena szans

Uczciwie, bo to wpływa na decyzje o czasie:

| scenariusz | wynik | warunek |
|---|---|---|
| nic nie zmieniamy | 23–29 | szum wokół 26 |
| tylko scheduler | 23–29 | nie zadziała bez kroku 1 (§5) |
| batch 2× → 400 akcji/grę, podział równy | **~51** | sufit z §3, wykonalne w ~2 dni |
| batch 2× + scheduler | 46–53 | scheduler może wręcz zaszkodzić (§5) |
| batch 4× → 800 akcji/grę | 60–77 | wymaga, by batch trafiał |

**50+ jest osiągalne, ale wyłącznie przez krok 1 — i tylko jeśli batch będzie trafiał.** Nie przez lepszy prompting, i nie przez sam scheduler.

Uwaga na kolejność: przy 400 akcjach/grę **równy podział jest bezpieczniejszy** (51,3) niż greedy w wersji optymistycznej (46,1). Scheduler wdrażać dopiero po ustabilizowaniu batchingu i tylko po pomiarze.

Ryzyko: batch, który pudłuje, pali akcje i może *obniżyć* wynik. Dlatego wdrażać w kolejności 1a (batch jawny) → pomiar `abtest.py` → 1c (planner), a nie od razu planner.

**Pomiar przed submitem jest obowiązkowy:** próg szumu przy n=20 na 6 grach to 0,30 pkt. Pojedynczy run 10 gier wykrywa tylko efekty ≥ +10. Batch o oczekiwanym zysku +20 widać; scheduler o zysku +7 trzeba mierzyć na ≥20 powtórzeniach na grę, inaczej to wróżenie.

---

## 9. Co jest w repo po tej analizie

| plik | rola |
|---|---|
| `rust/src/score.rs` | cap poprawiony 1,15 → **1,0** (oficjalny), 1,15 zachowany jako `SCALED_CAP`; nowe testy |
| `local/scheduler.py` | scheduler wartości akcji (krok 2), z testem regresyjnym na r018 |
| `rust/src/plan.rs` | planner macro-akcji + model przejść (krok 1c) — **nieskompilowany w sandboxie** |
| `rust/src/bin/lab.rs` | lokalne środowisko testowe: odtwarza epizod z `benchmark.json` i porównuje polityki na CPU (rayon) |
| `rust/BUILD-AND-BENCH.md` | budowa i pomiar na 5950X (16 rdzeni) |
