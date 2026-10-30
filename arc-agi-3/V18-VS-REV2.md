# Czy moja wersja jest lepsza od rev2? — **Nie.**

**Data:** 2026-10-30 · **Kod:** `local/budget_sim.py` + `local/test_budget_sim.py` (13/13).

---

## 0. Odpowiedź w jednym zdaniu

**Nie. rev2 (`duck-v13-7-final`, `3945d72`) jest lepszy od wszystkiego, co zbudowałem**
— i to nie jest kwestia opinii: ma 10 patchy zweryfikowanych na czystym r033,
41 komórek, i **zawiera wszystko, co zaproponowałem**, plus dwa patche, których
nie miałem. Mój „v17" został zbudowany przez nich jako `duck-v13-4-unified`
**o 08:15**, pięć godzin przedtem, zanim napisałem `V17-COMPARE.md`.

Co więcej — **rev2 cytuje moją pracę**: w komórce 2 stoi

> „Batching leverage is 24x the whole escalation debate (7911 cad326c): keep
> escalating at 20, watch the a/call print." … „gate 7911 >= 6.0 (253 actions/game
> = the 50-point boundary)".

Gałęzie się zbiegły. To, co u mnie było analizą, u nich jest już zbudowane
i zmierzone.

---

## 1. Sprostowanie: **v13.4 ISTNIEJE — myliłem się**

W `V17-COMPARE.md` §0 napisałem „v13.4 nie istnieje", sprawdzone „czterema
metodami". To było nieprawdziwe, a sposób sprawdzenia był wadliwy:

```
gh api .../git/trees/$b?recursive=1 | grep -iE "arc3|duck|v13" | head -20
                                                                  ^^^^^^^^
```

`head -20` **uciekł wynik**. `duck-v13-4-unified` była w drzewie Smaka **już pod
`f04c3e7`** — potwierdzone bezpośrednio:

```
git cat-file -e f04c3e7:arc-agi-3/duck-v13-4-unified   ->  TAK
```

To dokładnie ta klasa błędu, przed którą sam ostrzegam („testy 6/6 zielone przy
martwej funkcji"): narzędzie zwróciło sukces, a ja odczytałem go jako dowód
nieistnienia. **Warunek, który by to złapał:** sprawdzać *konkretną ścieżkę*,
nie listę z `head`. Tak robię teraz (`git cat-file -e <rev>:<path>`).

### 1.1 Czego nie zauważyłem, bo gałąź rosła

| wersja | dodana | co wnosi |
|---|---|---|
| `duck-v13-3-arena` | 08:07 | hint na openerze (Smak) |
| **`duck-v13-4-unified`** | **08:15** | **= mój „v17": v13.2 + hint + v14 + patch 0008 eskalacja względna z cap 2** |
| `duck-v13-5-consensus` | 08:27 | — |
| `duck-v13-6-final` | 09:25 | + patch 0009 self-pace (Gemma `duck-v16`, bajt w bajt) |
| **`duck-v13-7-final` = rev2** | **13:49** | + patch 0010 dyn-level-budget, uzbrojenie 20000 |

---

## 2. Co rev2 ma, czego nie ma nic mojego

| element | moje „v17" | rev2 |
|---|---|---|
| hint na openerze | propozycja w dokumencie | **zbudowany, 8/8 na r033** |
| cap 2 eskalacji | propozycja | **zbudowany (0008)** |
| `ESCALATE_ACTIONS=20` | propozycja | zbudowany |
| sondy roster/budżet | propozycja | zbudowane |
| bramka 6,0 | **moja** | **zaadoptowana** |
| **patch 0009 self-pace** | — | **jest** (Gemma `duck-v16`, 22/14 na r085) |
| **patch 0010 dyn-level-budget** | — | **jest** |
| weryfikacja na czystym r033 | **nie mam bundla** | **10/10 patchy, ALL CHECKS PASSED** |
| liczba komórek | 0 | 41 |

**Jedyna rzecz, której rev2 nie ma, a ja mam:** `local/metric.py` z testem
odtwarzającym **30/30** zapisanych `final_score` regułą `min(115, …)` + cap
ukończenia. Sprawdziłem ich drzewo — nie ma tam testu tej reguły.

---

## 3. Gdzie naprawdę mogę coś wnieść: uzbrojenie 20000 w rev2

rev2 zmienia jedną liczbę: `ARC3_LEVEL_TOKEN_CAP` **60000 → 20000**. Ich własne
dane mówią, że @60000 cap jest **inertny** („15 luźniej / 0 ciaśniej") — więc
podnieśli go, żeby cap w ogóle zadziałał. Pytanie brzmi, czy zadziała we
właściwym miejscu.

Odtworzyłem ich politykę wiernie z `arc3_level_budget_v13_2.py`
(`local/budget_sim.py`), łącznie z drabinką:

```
cap(r) = clamp(base, cap_min, cap_max) * 1.5**r      # cap_min = static_cap
base   = static_cap                    gdy zapisano < 2 koszty
base   = max(static_cap, 4*mediana)    gdy zapisano >= 2
spent >= cap(r) i r < 1  ->  RESET (spent=0, r+=1)
spent >= cap(r)*1.5      ->  ABANDON (gra się kończy, `gave_up`)
```

⇒ efektywny budżet poziomu = **3,25 × uzbrojenie** = **65 000** @20000
i **195 000** @60000.

### 3.1 Wynik na 95 ukończonych poziomach z trzech zapisanych runów

| wariant | poziomy | punkty | koszt | oszczędność |
|---|---|---|---|---|
| bez capa (dziś) | **95/95** | **26,44** | 5 144 934 tok | — |
| **rev2 @20000** | **72/95** | **18,38** | 4 153 797 | 991 137 tok = 1 162 akcji |
| @20000 + `MIN_DONE=1` | 86/95 | 22,74 | 4 580 703 | 564 231 tok = 661 akcji |
| rev2 @60000 | 95/95 | 26,44 | 5 144 934 | **0** |

Kontrola: `26,44` to dokładnie średnia zapisanych `final_score` (29,02 / 23,10 / 27,21).

**Uzbrojenie 20000 kosztuje 8,06 punktu** i kupuje 1 162 akcje (19% budżetu).

### 3.2 Dlaczego cap trafia w złe miejsce

| fakt z danych | liczba |
|---|---|
| gier z **zero** ukończonych poziomów | **0/30** |
| mediana kosztu ukończonego poziomu | 31 320 tok |
| ukończonych poziomów droższych niż 20 000 | **64/95 = 67%** |
| poziom 1 droższy niż 45 000 | 8/30 gier |
| gry z poziomem 1 **lub** 2 droższym niż 45 000 | **14/30 = 47%** |
| mediana marnowanych tokenów na ostatnim poziomie | 28 016 tok |
| cap @60000 (195 000) wiąże | **0/30 gier** |

**„Marnotrawcy" jako całe gry w naszych danych nie istnieją** — marnotrawstwo to
*ostatni, nieukończony poziom każdej gry*, mediana 28k tokenów. Cap 195k go nie
dotyka. A przy poziomach 1–2 cap spada do 65k, czyli **poniżej kosztu, który
realnie płacimy za ukończenie poziomu** (mediana 24k/32k, ogon do 135k).

Cap jest więc **inertny tam, gdzie jest marnotrawstwo, i destrukcyjny tam, gdzie
jest pokrycie** — odwrotnie do zamiaru.

### 3.3 Uczciwie: czego ta symulacja NIE obejmuje

1. **Zakłada niezmieniony koszt poziomu.** Darmowy reset daje „one clean
   re-plan" — jeśli świeży kontekst czyni poziom tańszym, strata jest mniejsza.
   To ich hipoteza i **jest mierzalna tylko w biegu**.
2. **Zakłada, że oszczędzone tokeny przepadają.** W rzeczywistości patch 0003
   uwolnione sloty oddaje żyjącym grom („~36,5k tok/min aggregate"), a gry są
   ograniczone **czasem** (48 min), nie tokenami — więc wyższe tok/min = więcej
   akcji w tych samych 48 minutach. To realny mechanizm i może odzyskać część
   z 8 punktów.
3. Więc znak bilansu jest **niepewny** — ale strona straty jest teraz
   skwantyfikowana: **−8,06 pkt za 1 162 akcje**.

### 3.4 Porównanie z hintem — ta sama waluta

| dźwignia | akcje | koszt w punktach |
|---|---|---|
| hint na openerze | **+1 500** (48–50/gę) | **0** |
| cap @20000 | +1 162 | **−8,06** |
| cap @20000 + `MIN_DONE=1` | +661 | −3,70 |

**Hint kupuje więcej akcji za zero punktów.** Cap to dźwignia gorsza i niszcząca.

---

## 4. Rekomendacja dla rev2

**Nie uzbrajać 20000 bez `ARC3_LEVEL_MIN_DONE=1`.**

- `MIN_DONE=1` chroni poziom 1 (16/30 gier ma poziom 1 droższy niż 20k),
  odzyskuje **połowę** straty (18,38 → 22,74) i **wciąż** tnie 661 akcji.
- Sam `MIN_DONE=1` nic nie zmienia przy 60000 (test
  `test_protecting_level_one_is_free_at_60000`) — więc jest darmowym
  bezpiecznikiem, który nic nie psuje.
- Jeśli slot ma być bezpieczny: **zostawić `LEVEL_TOKEN_CAP="0"` (dormant) albo
  uzbroić na 60000** — w obu przypadkach wynik 26,44, bo cap jest inertny.
  Pomiar `completed/game` jest wtedy bezwartościowy (nic się nie zmienia), co
  też jest informacją: *cap nie jest tam, gdzie leży problem*.

**Prawdziwy wniosek:** problemem nie jest brak capa, a **to, że cap mierzy
niewłaściwą rzecz**. Marnotrawstwo jest na *nieukończonym* poziomie, a cap
karze *wszystkie* poziomy po koszcie. Rozdzielenie tych dwóch wymaga sygnału
postępu, nie progu tokenowego — i to jest następny krok, nie kolejne 10000.

---

## 5. Co wysłać

**rev2, ale z `MIN_DONE=1` przy uzbrojeniu.** To jedyna zmiana, którą
rekomenduję, i jest to jedna zmienna środowiskowa w komórce, którą i tak już
zmieniają.

**Czego nie zrobiłem:** nie tknąłem `Smak-Domu-Konkurs`, `a450b00f` ani
`Gemma-konkurs`; nie wysłałem submitu; nie mam bundla r033 (więc nie
zweryfikowałem 10/10 patchy rev2 — przyjmuję ich certyfikat). Symulacja jest
moja i opiera się na **naszych** trzech zapisanych runach, nie na ich 40-poziomowym
benchmarku.
