# duck-v8 — korekta mojego błędu i weryfikacja przesłanki

**Data:** 24.10.2026
**Commit pakietu:** `5f397df` na `peteraangelic-pixel/Pokemon`, gałąź `arena/a450b00f-pokemon`
**Pliki:** `arc-agi-3/duck-v8/{arc3_replay.py, test_arc3_replay.py, 0004-solved-level-replay.patch, PLAN-V8.md, variant.json}`

---

## 1. Mój błąd — sprostowanie

Napisałem w `REVIEW-24OCT-CONSOLIDATED.md`, że commit `5f397df` „nie istnieje w żadnym
remote". **To było nieprawdziwe.** Commit istnieje, z pięcioma plikami, z datą
2026-10-24 14:11:18.

**Skąd się wzięło:** sprawdzałem tak:

```bash
git ls-tree -r --name-only origin/$b 2>/dev/null | grep -c "..."
```

dla gałęzi, których **nie miałem pobranych lokalnie**. `git ls-tree` kończyło się
wtedy błędem, `2>/dev/null` go ukrywało, `grep -c` na pustym wejściu zwracało `0`,
a mój filtr `grep -v ": 0"` wycinał ten wynik. **„Gałąź niepobrana" i „katalog nie
istnieje" dawały identyczny rezultat** — a ja zaraportowałem to drugie.

Poprawna wersja to `git fetch` **wszystkich** gałęzi przed sprawdzaniem, albo
`git ls-remote` + `git cat-file` po pobraniu. Wnioski wyciągnięte z nieistniejących
danych są gorsze niż brak wniosku — przepraszam.

---

## 2. Co zweryfikowałem w pakiecie

### 2.1 Testy jednostkowe: 7/7 zielone — POTWIERDZONE

Testy są w stylu pytest (funkcje + `assert`, fixture'y `monkeypatch` / `tmp_path`).
W tym sandboxie nie ma pytest, więc uruchomiłem je własnym runnerem z podstawionymi
fixture'ami:

```
PASS test_env_gating
PASS test_extract_segments_closes_on_level_up
PASS test_extract_segments_keeps_shortest_on_revisit
PASS test_frame_hash_stable_and_level_bound
PASS test_plan_replay_requires_start_hash_match
PASS test_store_roundtrip_shortest_wins
PASS test_verify_step
7/7 przeszlo
```

### 2.2 Stabilność hashy między procesami — POTWIERDZONE

Store replaya jest zapisywany na dysku i czytany w kolejnych sesjach/passach. Jeśli
`frame_hash` zależałby od `PYTHONHASHSEED`, store byłby bezużyteczny. Sprawdziłem
trzy osobne procesy z `PYTHONHASHSEED=random`, ten sam przebieg na `cd82`:

```
08becaaa31fa2423 32f139c2bfda0e05 ba38116b485b6c1d 95ecc62cccf33094 51896ef89479182d bef9fd7f50175ce4
08becaaa31fa2423 32f139c2bfda0e05 ba38116b485b6c1d 95ecc62cccf33094 51896ef89479182d bef9fd7f50175ce4
08becaaa31fa2423 32f139c2bfda0e05 ba38116b485b6c1d 95ecc62cccf33094 51896ef89479182d bef9fd7f50175ce4
```

Identyczne. Store jest przenośny między sesjami.

---

## 3. Przesłanka — POTWIERDZONA na prawdziwym silniku

Pakiet zakłada: *po śmierci poziom resetuje się do stanu początkowego i odtworzenie
nagranej sekwencji przechodzi go ponownie bez wywołań modelu.* Nikt tego nie
smoke'ował. Zrobiłem to lokalnie, na `arcengine`, kosztem 0 GPU.

**Narzędzie:** `local/test_replay_premise.py`

```
silnik: 25 gier | testuje 4 rozwiazan

cd82   OK    5 akcji | poziomy 0->1 | Q1 reset=start: True | Q2 zachowuje poziomy: False | Q3 replay: True
lp85   OK    5 akcji | poziomy 0->1 | Q1 reset=start: True | Q2 zachowuje poziomy: False | Q3 replay: True
sp80   OK    4 akcji | poziomy 0->1 | Q1 reset=start: True | Q2 zachowuje poziomy: False | Q3 replay: True
vc33   OK    3 akcji | poziomy 0->1 | Q1 reset=start: True | Q2 zachowuje poziomy: False | Q3 replay: True

Q1 reset przywraca klatke startowa : 4/4
Q2 reset ZACHOWUJE ukonczone poziomy: 0/4  <-- po smierci gra leci od poziomu 1
Q3 replay odtwarza poziom          : 4/4
Q4 decyzje modelu zaoszczedzone    : 17 na 4 grach

PRZESLANKA v8: POTWIERDZONA
```

Co to znaczy konkretnie:

| pytanie | odpowiedź | znaczenie |
|---|---|---|
| Q1: `RESET` przywraca klatkę startową? | **4/4 tak** | stan jest deterministyczny, więc replay ma co odtwarzać |
| Q2: `RESET` zachowuje ukończone poziomy? | **0/4 nie** | licznik wraca do 0 — po śmierci agent odtwarza **całą** ścieżkę |
| Q3: replay przechodzi poziom ponownie? | **4/4 tak**, hash w hash | mechanizm działa bajt w bajt |
| Q4: ile decyzji modelu oszczędza? | tyle, ile akcji w nagraniu | przy ~1,2 decyzji/min to odzyskany czas |

### 3.1 Q2 jest ważniejsze niż sam replay

`GameAction.RESET` — **to samo, które harness odpala po śmierci** (`_execute_auto_reset`
w `franzen-m2.ipynb`, wywoływane gdy `_is_engine_game_over`) — cofa licznik poziomów
**do zera**. Prompt w harnessie mówi „completed levels are kept", ale to dotyczy
*zapisu wyniku*, nie stanu silnika. Silnik wraca na poziom 1.

Czyli: **każda śmierć kosztuje całą dotychczasową ścieżkę w akcjach.** A akcje
wchodzą do wyniku do kwadratu (`min(H/A, 1.15)²`). To jest dużo droższe, niż
wyglądało, i dokładnie to adresuje replay.

**Otwarte pytanie, które rozstrzygnie pierwszy smoke z logiem:** czy benchmark liczy
`A_l` per poziom z przebiegu końcowego, czy zachowuje najlepszy. Jeśli z końcowego,
replay dodatkowo *poprawia* wynik (odtworzenie jest krótsze niż pierwsze przejście).

---

## 4. Czego nadal NIE zweryfikowałem

| rzecz | status |
|---|---|
| `0004-solved-level-replay.patch` aplikuje się i kompiluje | **nie sprawdzone** — brak bundle'a źródłowego Tufy (r033) w tym sandboxie |
| zachowanie w prawdziwym harnessie (ToolAgent) | nie sprawdzone — wymaga GPU i slotu |
| czy `ARC3_REPLAY=1` nie psuje ścieżki przy braku nagrań | nie sprawdzone; kod deklaruje fail-silent |
| ile punktów to daje | **zero pomiarów** — autor sam tak pisze i ma rację |

Czyli: logika jest sprawdzona, przesłanka jest sprawdzona, **integracja i zysk nie są**.

---

## 5. Rekomendacja

Pakiet jest **realny i dobrze zrobiony**, wbrew temu, co napisałem wcześniej. Ale:

1. **Nie jest to dźwignia na +18 punktów.** Działa na oszczędność decyzji po
   śmierciach; nie zwiększa liczby poziomów, które agent *potrafi* rozwiązać.
2. **Jego wartość skaluje się z liczbą śmierci i z `n_passes`.** Przy `n_passes=1`
   oszczędza tylko powtórki po śmierci. Przy `n_passes>1` (Franzen używa 4) każde
   przejście po znanych poziomach jest darmowe — i dopiero tam robi się duża.
3. **Kolejność:** najpierw notebook Franzena (33,68–34,30 zmierzone), potem replay
   jako dodatek na wierzchu, z `ARC3_REPLAY=1` i odczytem jednej linii loga
   („ile poziomów odtworzono"). Jeśli zero — wyłączyć i nie tracić slotu.

### Czego bym nie robił
Wysyłania v8 jako **pierwszego** ruchu. To nieprzetestowany patch na nieprzetestowanym
harnessie, a mamy 1 submit dziennie. Zmierzony zysk z Franzena jest większy i pewniejszy.

---

## 6. Źródła tej weryfikacji

| fakt | gdzie sprawdzone |
|---|---|
| commit 5f397df + 5 plików | `git fetch` + `git cat-file` / `git ls-tree` |
| 7/7 testów | własny runner z fixture'ami |
| hashe stabilne między procesami | 3× `PYTHONHASHSEED=random` |
| RESET cofa do poziomu 0 | `local/test_replay_premise.py`, 4 gry |
| `_execute_auto_reset` po `_is_engine_game_over` | `duck/notebook/base/franzen-m2.ipynb` na `98ddb59f` |
| „completed levels are kept" dotyczy zapisu, nie silnika | tamże + pomiar Q2 |
