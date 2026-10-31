# v19 — droga do 50. Zmierzona, nie wywnioskowana.

**Data:** 2026-10-31 · **Kod:** `local/road_to_50.py` + `local/test_road_to_50.py` (26/26).

---

## 0. Werdykt w trzech liniach

1. **Pełny łańcuch v13 kosztował 10,61 punktu.** v3 = 26,25 · v11 = 23,89 · **v13.7 = 13,28**.
   Moje rekomendacje z ostatnich czterech tur szły w tę samą stronę, co ta regresja.
   **Wycofuję je.**
2. **Mechanizmem nie są tokeny, a AKCJE NA POZIOM.** Zmierzone na prawdziwych logach
   harnessu: r085 = **66,4** akcji/poziom, r121 (wysłany) = **91,0** (+37%). Tokeny na
   akcję drgnęły o 10%.
3. **50 punktów to 45,8 akcji/poziom.** Model skalibrowany na nagranych runach
   przewiduje prawdziwy wynik rerunu z dokładnością **0,5 punktu**.

---

## 1. Fakt, który przesądza — i moja retrakcja

Z `kaggle/ops/results/r122-submissions/` (odczytane sam, nie z opisu):

| ref | data | konfiguracja | wynik |
|---|---|---|---|
| 57247568 | 16.10 | **duck v3** — najstarszy, najprostszy | **26,25** |
| 57737623 | 28.10 | **v11** — `PLAN_COMMIT=0`, cap45k, conc 10 | **23,89** |
| 57811453 | 30.10 | **v13.7** — 9 patchy: opener-hint, ESCALATE 20+cap2, self-pace, winpath, dead-skip | **13,28** |

**Sprzedał 10,61 punktu** względem tego samego harnessu bez łańcucha.

### 1.1 Co dokładnie wycofuję

| moja teza | stan |
|---|---|
| „opener hint da +22% budżetu → ~50 pkt" | **obalona.** Akcje/wywołanie: r085 **4,51** (bez hinta) → r121 **5,01** (z hintem). To +11%, a v11 **bez hinta** ma **4,94**. Różnica jest w szumie. Hint nie zmienił batchowania. |
| „hint to 24× dźwignia" | **obalona w tej samej walucie**, w której ją policzyłem: liczyłem tanie parametry, a drogi okazał się parametr, którego nie liczyłem — akcje/poziom. |
| „cap 20000 kosztuje 8,06 pkt" | **nieistotne dla 13,28** — w tym biegu `ARC3_LEVEL_TOKEN_CAP="0"`, cap był **inercyjny**. Analiza była poprawna, ale dotyczyła wyłączonego parametru. |
| „bramka `actions_per_call ≥ 6,0`" | **bezużyteczna.** Cel 6,0 jest nieosiągalny: wszystkie 8B runy leżą w 4,51–5,01 i nie zależą od promptu. Bramka byłaby wiecznie czerwona, nic nie mierząc. |

Wspólny błąd wszystkich czterech: **optymalizowałem koszt tokenowy, gdy kosztem był ruch.**
Model w `V16-PLAN.md` §0 („206 → 253 akcji, +22%") miał właściwy kierunek i **niewłaściwą
zmienną** — akcje/gę rosną nie przez tańsze tokeny, a przez tańsze poziomy.

---

## 2. Zmierzony mechanizm

Oba runy: ten sam harness, te same 10 publicznych gier, ten sam budżet 48 min.
Policzone z `history` (pole `generated_tokens` na każdą akcję) i `actions_per_level`:

| | **r085** (c45) | **r121** (v13.7, wysłany) | zmiana |
|---|---|---|---|
| poziomy/grę | **3,20** | **2,50** | −22% |
| akcji/grę | 213 | 228 | +7% |
| **akcji/poziom** | **66,4** | **91,0** | **+37%** |
| tok/akcja | 667 | 733 | +10% |
| akcji/wywołanie | 4,51 | 5,01 | +11% |
| wall-clock/grę | 46,0 min | 45,8 min | ±0 |

Akcje na grę są **przypięte zegarem** (48 min), więc `poziomy/grę = 220 ÷ akcji/poziom`.
Łańcuch nie spowolnił modelu — **kazał mu marnować ruchy**.

---

## 3. Model — skalibrowany na prawdziwym wyniku, nie na opinii

`score = min(raw, cap)` i na zamykanych poziomach przekraczamy sufit 115, więc
`score ≈ 0,93 × pokrycie`. Waga poziomu to `k`, więc pokrycie zależy od **rozkładu**,
nie od średniej.

Kalibracja na dwóch nagranych smoke'ach (błąd < 1 pkt):

| run | poziomy/grę | dokładne pokrycie | model | zapisany |
|---|---|---|---|---|
| r085 | 3,20 | 29,8% | **27,7** | **26,78** |
| r121 | 2,50 | 23,5% | **21,9** | **22,59** |

**Test modelu na wyniku, którego nie użyłem do kalibracji:** 91,0 akcji/poziom
→ model daje **12,8 pkt**. Prawdziwy rerun: **13,28**. Błąd **0,5 punktu**.

To znaczy, że jedna liczba — akcje na poziom — wyjaśnia całą różnicę 26,25 → 13,28.

---

## 4. Zjawisko, którego nikt w tej kampanii nie policzył: koncentracja

Waga gry to `k(k+1)/2` — **wypukła**. Przy tej samej średniej głębokości **nierówny
rozkład daje wyższe pokrycie**:

| run | rozkład poziomów | dokładne | równe | zysk |
|---|---|---|---|---|
| r085 | 1,4,5,3,5,3,2,3,3,3 | 29,8% | 26,1% | **1,14×** |
| r121 | 0,5,1,2,3,5,4,2,3,0 | 23,5% | 17,3% | **1,36×** |

**Dwie gry na zerze w r121 kosztowały ~6 punktów pokrycia.** Gra, która dostanie zero,
ma wagę **0 w liczniku i pełną w mianowniku**.

Wniosek operacyjny, którego nie ma w żadnym z audytów: **ochrona przed zerem jest warta
więcej niż pogłębianie najlepszej gry.** To także argument przeciw capom poziomu —
cap 45k ucina pierwszy poziom grom wolnym, ale zdolnym, czyli tworzy dokładnie te zera.

---

## 5. Dwie drogi do 50

### 5.1 Sam LLM

| akcji/poziom | poziomy/grę | wynik |
|---|---|---|
| 91,0 (wysłane) | 2,42 | **12,8** |
| **66,4** (r085) | 3,31 | **27,7** |
| 60,0 | 3,67 | 27,7 |
| 55,0 | 3,98 | **34,6** ← sufit publicznych notebooków |
| 51,0 | 4,24 | 41,6 |
| **45,8** | 4,60 | **~47–50** |

**50 = 45,8 akcji/poziom: −31% względem najlepszego, co kiedykolwiek zmierzyliśmy.**
Nigdzie w tej kampanii nie ma pomiaru, który by taki zysk pokazał. Wszystkie zmierzone
zmiany szły w drugą stronę (85,7 i 91,0 przy 66,4).

### 5.2 Ścieżka symboliczna — jedyna zmierzona rzecz o takiej skali

Kontroler Codexa: **3 poziomy w 25 akcjach = 8,3 akcji/poziom**, czyli **8×** lepiej niż LLM.
Problem: odpala na **1/25** gier publicznych (4%).

Model zbiorczy — 110 gier × 220 akcji, gry symboliczne zużywają ~50 akcji i dają pełne pokrycie;
zwolnione akcje wracają do reszty:

| udział gier na ścieżce symbolicznej | akcji/grę dla LLM | **wynik** |
|---|---|---|
| 0% | 220 | 27,7 |
| 4% (zmierzone na publicznych) | 227 | **30,3** |
| 8% | 235 | 32,9 |
| 12% | 243 | **35,5** |
| 16% | 252 | 38,1 |
| 20% | 263 | 40,8 |
| 25% | 277 | **49,2** |
| 30% | 293 | **52,1** |

**50 punktów wymaga ~24% rostera na ścieżce symbolicznej.** Mamy 4%.

Zysk z tego, co już istnieje, to **+2,6 punktu** — tyle, ile wynosi szum między dwoma
smoke'ami. Czyli kontroler w obecnej postaci **nie jest drogą do 50**, ale jest jedyną
rzeczą w całej kampanii, która ma właściwy rząd wielkości (8,3 vs 66,4 akcji/poziom).

---

## 6. Rekomendacja na 2 pozostałe sloty

**1.11 — dokładny rerun v3 (26,25).** Artefakt odzyskany, najmniej ruchomych części.
**2.11 — v11-exact (`PLAN_COMMIT=0`, 23,89).** Druga próbka rodziny mistrza.

**Nie wysyłać niczego z łańcuchem v13 ani z pochodnymi v18.** Nie z ostrożności — z pomiaru:
ten łańcuch to −10,61 punktu, a mechanizm jest znany (akcje/poziom +37%).

**Czego NIE robić w tych dwóch dniach:** budować kolejnych zdolności symbolicznych.
Z 4% na 24% to sześć rodzin reguł; przy dwóch slotach nie ma jak zmierzyć ani jednej.

---

## 7. Czego nie wiem — i co by to zmieniło

1. **Nie wiem, ile z 66,4 → 91,0 to łańcuch, a ile wariancja między runami.** Ten sam
   wariant rodzinny (v11) dał 85,7 w innym smoke'u. Trzy runy nie rozdzielają tych dwóch.
   **Warunek, który by to rozstrzygnął:** dwa biegi tego samego notebooka.
2. **Nie wiem, czy alokacja czasu w rerunie jest sprawiedliwa.** Cap 532 min vs uczciwy
   udział 49 min (audyt Codexa) — jeśli scheduler nie pilnuje podziału, to nie „efektywność"
   decyduje o wyniku, a kolejka. **Żaden log tego nie zawiera.**
3. **Nie wiem, jaka jest częstość rodzin reguł w ukrytych 110 grach.** 1/25 na publicznych
   to jedyna próbka i jest to gra rozwojowa modułu.

**Czego nie zrobiłem:** nie tknąłem gałęzi `codex/*` ani `Smak`, nie wysłałem submitu,
nie mam bundla r033 ani dostępu do Kaggle. Wszystkie liczby powyżej pochodzą z plików
w repo Smaka (`kaggle/ops/results/*/benchmark.json`, `r122-submissions/`) i z moich
trzech runów lokalnych.
