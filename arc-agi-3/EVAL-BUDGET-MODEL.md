# Budżet akcji w ewaluacji — model i dowód pośredni

**Data:** 2026-10-30 · Uzupełnia `MEGA-DIAGNOSIS.md` §3–§4.

Ten dokument domyka lukę, która została w `MEGA-DIAGNOSIS.md`: tam pisałem „48 minut
na grę", ale **nie wiedziałem, skąd się bierze ten limit w prawdziwej ewaluacji**.
Teraz wiem, bo przeczytałem komórkę konfiguracyjną v13.1 (nr 25) na gałęzi
`arena/a450b00f-pokemon`.

---

## 1. Co naprawdę ustawia submisja

W `arc-agi-3/duck-v13-1/arc3-duck-v13.ipynb`, komórka 25:

```python
if TRUE_SUBMISSION:                       # KAGGLE_IS_COMPETITION_RERUN
    bm.solver.save_request_logs = False
    bm.n_passes = 1
    if USE_PRIORITY_SCHEDULING:           # = True
        bm.solver.concurrency = int(os.environ.get("ARC3_TRUE_CONCURRENCY", "10"))
        bm.solver.max_runtime_s_per_game = 532 * 60      # 31 920 s = 8,87 h
```

Czyli w prawdziwym rerunie:

| parametr | wartość | znaczenie |
|---|---|---|
| `n_passes` | **1** | jedna próba na grę w wpisie rosteru |
| `concurrency` | **10** | 10 równoległych slotów generacji |
| `max_runtime_s_per_game` | **31 920 s** | sufit na JEDNĄ grę |
| `USE_PRIORITY_SCHEDULING` | **True** | gry są kolejkowane przez priority gate i rotowane |
| `soft_end` | **None** | brak miekkiego deadline'u w submisji |

**Kluczowe: 31 920 s na grę to nie jest limit, który każda gra dostaje.** Gdyby
dostawała, roster 110 gier potrzebowałby 110 × 8,87 h = **97 godzin** czasu gry,
przy 10 slotach → 9,7 h ściany. Notebook ma **9 h** (`target.max_runtime_s`
asertowane jako `32400.0` w ścieżce smoke; 532 min ≈ 9 h − 8 min, co potwierdza,
że 532 min wyliczono z budżetu notebooka).

Więc 532 min to „gra może zjeść prawie cały bieg", a nie „każda gra dostanie 8,87 h".
Realny budżet jest **dzielony przez priority gate**:

```
efektywny czas na grę = budżet_notebooka × concurrency / liczba_gier
```

---

## 2. Model: ile akcji dostaje gra

Zmierzone tempo to **14,4 s na akcję** (r013: 2880 s / ~200 akcji; 4,17 akcji/min).

| gier w rosterze | min / grę | akcji / grę | sufit wyniku @ eff=90% |
|---|---|---|---|
| 10 | 540 | 2 250 | 100,0 |
| 25 | 216 | 900 | 87,3 |
| 50 | 108 | 450 | 59,1 |
| **110** | **49** | **205** | **18,7** |

*(sufit liczony na kosztach ludzkich z r018, `local/scheduler.py`)*

---

## 3. Dowód pośredni: roster ma ~110 gier, nie 25

To nie jest założenie — to wniosek z porównania dwóch niezależnych obserwacji:

| obserwacja | wynik |
|---|---|
| smoke na 10 grach, 48 min/gra | 27,21 – 29,02 |
| **prawdziwy leaderboard** | **26,25** |

Te dwie liczby są **praktycznie identyczne**. A to znaczy, że w prawdziwym biegu
graliśmy z takim samym budżetem czasowym na grę jak w smoke (≈49 min), nie 4× dłużej.

Gdyby roster miał 25 gier, każda dostałaby 216 min i ~900 akcji — przy naszej
zmierzonej efektywności 86–90% wynik byłby **znacznie** wyższy niż 26,25.
Nie był. Więc roster jest duży.

**Wniosek: „48 minut na grę" z mojego smoke okazało się przypadkiem trafne dla
ewaluacji — ale z innego powodu niż myślałem.** Wcześniej pisałem, że to „tylko
nasz smoke, nie limit konkursu". Poprawka: to jest limit konkursu, wynikający
z rotacji rosteru, a nie z `max_runtime_s_per_game`.

Konsekwencja praktyczna: **smoke na 10 grach × 48 min jest dobrym estymatorem
warunków ewaluacji.** Nasze smoke'y i realne submity mierzą to samo.

---

## 4. Co to znaczy dla 50+ — lewar ilościowy

Skoro budżet czasu na grę jest stały (~49 min = ~205 decyzji LLM), to **jedyny
sposób, żeby mieć więcej akcji, to więcej akcji na decyzję**.

| akcji / decyzję | akcji / grę | sufit @ eff=90% |
|---|---|---|
| **1 (nasze dziś)** | 205 | **18,7** |
| **2** | 409 | **53,3** |
| 3 | 614 | 65,1 |
| 4 | 818 | 80,1 |

Ile akcji na grę trzeba na konkretny wynik:

| wynik | akcji / grę | minut jednego slotu |
|---|---|---|
| 50 | **389** (daje 51,3) | 93 |
| 60 | 479 (daje 60,5) | 115 |
| 75 | 736 (daje 75,2) | 177 |

Funkcja jest **schodkowa** — jedna akcja więcej może przekroczyć próg poziomu i podnieść
wynik skokiem (przy 388 akcjach jest 48,4; przy 389 już 51,3). Dlatego podane progi
to pierwszy budżet, przy którym wynik przekracza cel, a nie wartość równa celowi.

**To spina się z `MEGA-DIAGNOSIS.md` §4 co do liczby** (tam wyszło 400 akcji → 51,3;
tu 389 → 51,3), ale teraz ma mechanizm: nie „zagraj lepiej", tylko
**wykonaj 2 ruchy na jedno wywołanie modelu**.

### Sanity check na czołówce

Najlepszy publiczny wynik to **75,56**. Przy rosterze 110 gier i 205 decyzjach
wymaga to ~736 akcji, czyli **~3,6 akcji na decyzję**. To dokładnie ten profil,
który daje `commit(plan)` z patcha 0005 (do 40 akcji na wywołanie).
Czołówka nie ma lepszego modelu — ma **więcej akcji na token**.

Nasze publiczne odpowiedniki (maks. 35,35) siedzą na 1 akcji na decyzję, tak jak my.

---

## 5. Zastrzeżenia

- **9 h to założenie**, ale dobrze podparte: `32400.0` jest asertowane w notebooku,
  a 532 min = 32400 s − 480 s. Jeśli budżet jest inny, przelicz tabelę z §2.
- **Liczba 110 gier** pochodzi ze strony danych konkursu („110 private games").
  Dowód z §3 jest pośredni, nie bezpośredni — nie widziałem rosteru rerunu.
- **Priority gate rotuje gry**, więc 49 min to średnia, nie gwarancja. Część gier
  dostanie więcej, część mniej. To *wzmacnia* argument za schedulerem wartości
  (`local/scheduler.py`), bo przy nierównym przydziale liczy się, które gry
  dostaną czas.
- Model sufitów jest **konserwatywny**: przy 206 akcjach przewiduje 18,7, a my
  realnie mieliśmy 25,09 — bo na łatwych poziomach bijemy człowieka i cap 1,0
  działa na naszą korzyść. Więc liczby z §4 traktuj jako dolną granicę.

---

## 6. Co z tego wynika dla decyzji o submisji

1. **Nie ma sensu czekać na „więcej czasu"** — budżet czasu jest stały i już go znamy.
2. **Każda zmiana, która nie zwiększa akcji na decyzję, przesuwa nas najwyżej
   o kilka punktów** (scheduler, playbook, cap tokenów — wszystko to jest w szumie
   0–3 pkt).
3. **`commit(plan)` jest jedyną dźwignią o właściwej skali** — i w v13.1 jest
   tylko oferowane, nie wymuszane (`V13-1-VERIFICATION.md` §3).
