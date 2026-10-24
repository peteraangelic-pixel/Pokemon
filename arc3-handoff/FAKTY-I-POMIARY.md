# ARC-AGI-3 (ARC Prize 2026) — kompendium faktów zmierzonych i zweryfikowanych

Stan: **24.10.2026, ~16:45 UTC**. Gałąź źródłowa: `peteraangelic-pixel/Smak-Domu-Konkurs`
@ `arena/5ed750ef-smak-domu-konkurs` (492 bloby — migawka w `results/their_tree_snapshot.tsv`).

Zasada tego pliku: **każda liczba ma źródło** (plik+linie w ich repo, log z runa, albo mój
pomiar z podaną metodą). Rzeczy niepewne są oznaczone jako EKSTRAPOLACJA. Nic tu nie jest
zgadywane — a tam, gdzie wcześniej zgadywałem, jest jawna poprawka (szukaj „POPRAWKA").

Spis: 1 silnik · 2 punktacja · 3 gry · 4 harness/config · 5 serwer · 6 pomiary runów ·
7 stan Kaggle · 8 kolejka ops · 9 bugi ich patchy · 10 pułapki narzędziowe · 11 mapa repo

---

## 1. Silnik `arcengine` (pomierzone lokalnie)

Instalacja w piaskownicy (PEP 668 — bez tych flag nie działa):

```bash
python3 -m pip install --user --break-system-packages -q numpy pydantic pillow
python3 -m pip install --user --break-system-packages -q --no-deps --ignore-requires-python arcengine
```

`arcengine 0.9.3` na python 3.11. `--no-deps --ignore-requires-python` jest konieczne, bo
pakiet ciągnie zależności, których tu nie ma, a sam potrzebuje tylko numpy/pydantic/pillow.

### API

```python
from arcengine import ActionInput, GameAction
game = Ls20()                                    # klasa z <game>.py, dziedziczy ARCBaseGame
fd = game.perform_action(ActionInput(id=GameAction.from_id(0)))     # 0 = RESET
fd.game_id, fd.frame, fd.state, fd.levels_completed, fd.win_levels
fd.action_input, fd.guid, fd.full_reset, fd.available_actions
```

`GameAction`: `RESET=0`, `ACTION1..ACTION5` (klawiatura), `ACTION6` = `ComplexAction(x,y)`,
x/y ∈ 0..63 (klik), `ACTION7`.

### Pułapki (każda kosztowała mnie realny czas — wszystkie potwierdzone)

| pułapka | objaw | rozwiązanie |
|---|---|---|
| `GameAction(1)` | `ValueError: 1 is not a valid GameAction` — `_value_` jest ustawiany w `__init__`, ale lookup po wartości nie działa, bo `value` to **krotka** | `GameAction.from_id(i)` / `from_name(n)` |
| klatka animacji | `fd.frame` ma shape `(k,64,64)` → `cannot reshape array of size 24576 into shape (64,64)` | `while a.ndim > 2: a = a[-1]` |
| klatka płaska/1-D | tn36, sb26 zwracają `(1,64,64)` → po `a[-1]` bywa 1-D → `h, w = frame.shape` → `ValueError: not enough values to unpack (expected 2, got 1)` | reshape po pierwiastku z `size` (patrz `frame_of` w `arc3_search.py` i `tools/sweep.py`) — **POPRAWKA**: pierwsza wersja searcha padała na tym dla 2 z 25 gier |
| `pickle.dumps(game)` | `PicklingError: Can't pickle <class 'g.Ls20'>` (klasa z dynamicznie ładowanego modułu) | `copy.deepcopy` działa |
| `Camera.render()` | wymaga argumentu `sprites` | nie używać — `fd.frame` wystarczy |
| dtype | `frame` to `int64`, nie `uint8` | `.astype(np.uint8)` przed hashem/porównaniem |

### Koszty (zmierzone na ls20, 1 rdzeń)

| operacja | czas |
|---|---|
| `perform_action` | **4.36 ms** |
| `copy.deepcopy(game)` (snapshot) | **16.9 ms** |
| `level_reset()` | **1.82 ms** |
| instantiacja gry + RESET | **17.2 ms** |

→ BFS/beam robi **~31 węzłów/s** na jednym rdzeniu (snapshot dominuje, nie sama akcja).
Praktyczny wniosek: 12 000 węzłów ≈ 6 min, 25 gier × 300 s ≈ 45 min na 2 rdzeniach.
Pickle odpada, więc równoległość musi być przez `multiprocessing` z **osobną instancją gry
w każdym workerze** (stanu nie da się przesłać przez pipe).

### Determinizm — POTWIERDZONY

12 sekwencji znalezionych przez search odtworzonych **na świeżej instancji gry, 2× każda**,
wszystkie ukończyły dokładnie te same poziomy (`tools/build_playbook.py::replay`).
Silnik jest deterministyczny → playbook da się odtworzyć w harnessie co do akcji, bez LLM.

### `available_actions` na poziomie 0 (wybrane, zmierzone)

| gra | dostępne akcje | uwaga |
|---|---|---|
| tn36 | `[6]` | tylko klik — 4096 współrzędnych do przeszukania |
| sb26 | `[5, 6, 7]` | występuje `ACTION7` (nie ma go w mojej liście ruchów klawiaturowych) |
| ft09 | `[6]` | **POPRAWKA do mojego własnego wpisu**: wcześniej zapisałem tu „puste / 1 element" — to nie był pomiar, tylko wnioskowanie z faktu, że search umarł po 56 węzłach w 0.7 s. Pomiar (skan 4096 współrzędnych) daje: 288 responsywnych (7%), wszystkie w x,y ∈ [36,57], wszystkie zmieniają **dokładnie 38 px** → 8 przycisków na siatce co 8 px. Search umierał, bo segmentacja blobów nie trafiała w żaden z nich. Rozwiązane w §1bis |

Model **nie może** sam krokować silnika: `inference/agent/python_tool_sandbox.py` wystawia
mu tylko `current_frame` (`.ascii/.step/.level/.shape/.segmentation`) i `history`. Dlatego
każdy search musi żyć w harnessie, nie w piaskownicy modelu.

---

## 1bis. Jak naprawdę wyglądają gry click-owe (skan 4096 współrzędnych) i dlaczego to ważne

Pierwsza wersja searcha (`tools/sweep.py`) generowała kandydatów kliknięcia z segmentacji
blobów 4-spójnych (centroidy + skraje obiektów). Pomiar pokazał, że dla części gier ten
generator jest **ślepy**. Przeskanowałem wszystkie 4096 współrzędnych na trzech grach,
izolując każdy test przez `level_reset()` (1.82 ms — 9× taniej niż `deepcopy` 16.9 ms):

| gra | `available_actions` | responsywne współrzędne | zmiana pikseli | interpretacja |
|---|---|---|---|---|
| **ft09** | `[6]` | **288 / 4096 (7%)**, wszystkie w `x,y ∈ [36,57]` | **dokładnie 38** (min=mediana=max) | 8 przycisków na siatce co 8 px; klik w dowolny punkt przycisku daje ten sam efekt |
| **sc25** | `[1,2,3,4,6]` | **0 / 4096** | — | żaden klik nie zmienia ramki *od razu* — efekt odroczony/niewidoczny w ramce |
| **tn36** | `[6]` | **4096 / 4096 (100%)** | **1–4** (mediana 1) | to kursor podążający za klikiem, nie zmiana stanu → heurystyka „liczba zmienionych pikseli" jest tu bezużyteczna |

Trzy różne patologie, trzy różne wnioski:
1. **ft09** — segmentacja blobów nie trafiła w ŻADEN z 288 punktów, więc search miał 28
   martwych ruchów, frontier wysechł po 56 węzłach w 0.7 s. (Wcześniej zapisałem, że ft09 ma
   „puste `available_actions`" — to było wnioskowanie, nie pomiar; sprostowane wyżej.)
2. **sc25** — kryterium „ramka się zmieniła" w ogóle nie wykrywa legalnych ruchów. Grupa gier
   z odroczonym efektem; wymaga porównywania stanów po 2–3 akcjach (niezrobione, patrz niżej).
3. **tn36** — sygnał nowości jest czystym szumem (kursor). Tu potrzebna inna heurystyka.

### Odkrycie: silnik ma wewnętrzne API z gotową listą ruchów — i NIE WOLNO go używać

Przy okazji diagnostyki wyszło, że obiekt gry wystawia dużo więcej niż `perform_action`:

```
_get_valid_actions()            -> DOKŁADNA lista legalnych ActionInput ZE WSPÓŁRZĘDNYMI klików
_get_valid_clickable_actions()  -> same klikalne
_get_valid_placeble_actions()   -> miejsca do umieszczenia sprite'u
_score, _win_score              -> postęp i próg wygranej (np. ft09: 0 / 6)
_current_level_index, _action_count, _seed
get_pixels(x, y, width, height) -> fragment ramki bez wykonywania akcji
full_reset(), handle_reset(), is_last_level(), complete_action()
```

Dla ft09 `_get_valid_actions()` zwraca **8** klików: `(36,36), (44,36), (52,36), (36,44),
(52,44), (36,52), …` — dokładnie ten obszar, który znalazłem skanem. Dla sc25: 4 klawisze
+ 9 klików w siatce 3×3 od `(24,49)`. Dla tn36: 11 klików od `(20,42)`.

**Ale docstring tej metody mówi wprost:**

> `Note: This method is for internal use only, the data here is never exposed via the API
> or to Users/Agents.`

Czyli to informacja, którą silnik **celowo ukrywa przed agentem** (`FrameData.available_actions`
dostaje tylko numery akcji — dla ft09 `[6]`, bez współrzędnych; agent ma je wywnioskować
z ramki, i o to chodzi w tym benchmarku). Rekomendacja jest jednoznaczna:

> **NIE używać `_get_valid_actions()` / `_score` / `_win_score` w niczym, co idzie do submisji.**
> Przy $75k nagród i top-5 to ryzyko dyskwalifikacji, a nie przewaga. Używać wyłącznie
> OFFLINE jako wyroczni do sprawdzania, czy heurystyki na publicznym API działają.

### Zamiennik na publicznym API: kalibracja po EFEKCIE (działa, zmierzone)

Ta sama informacja jest dostępna legalnie — przez `perform_action` i porównywanie ramek.
Kluczowa zmiana względem pierwszej wersji: **grupować próby po efekcie (hash ramki po kliku),
nie po położeniu**.

```
dla każdej współrzędnej z siatki co 4 px (256 prób):
    level_reset()                      # 1.82 ms, przywraca poziom (ONLY_RESET_LEVELS)
    fd = perform_action(klik(x,y))
    jeśli ramka się zmieniła: effects[hash(frame)].setdefault((x,y))
reprezentanci = po jednej współrzędnej na RÓŻNY efekt
```

Wynik na ft09: **8 różnych efektów → rozgałęzienie 8** — dokładnie tyle, ile mówi ukryte
`_get_valid_actions()`, ale uzyskane wyłącznie publicznym API. I search natychmiast rozwiązał
poziom 0 w **4 akcjach** (przedtem: 0 poziomów, 56 węzłów, ślepy generator).

Koszt: 256 prób ≈ 0.5 s (pomierzone 544 próby/s dla ft09 i tn36, ale **115/s dla sc25** —
`perform_action` potrafi blokować na animacji, więc koszt akcji różni się między grami ~5×;
to samo wyjaśnia, dlaczego lf52 w głębokim przebiegu nie skończył się w `sec_cap=300`).

Druga poprawka z tego samego pomiaru: **pruning ruchów nigdy nie może zwrócić pustej listy**.
Dla sc25 żaden ruch nie zmienia ramki od razu, więc pruning zerował cały zestaw i search
stawał w miejscu (`brak efektywnych ruchów po kalibracji`). Teraz przy braku trafień wracamy
do pełnej listy i raportujemy `pruned_fell_back` — żadna gra nie zostaje z pustą ławką ruchów.

### Co naprawdę blokuje pozostałe 15 gier (pomiary z 24.10, wieczór)

**(a) Hipoteza „długi baseline = nie do rozwiązania" jest FAŁSZYWA — obalona pomiarem.**
Podejrzewałem, że blind search radzi sobie tylko z poziomami o krótkim `baseline_actions[0]`.
Zestawienie wszystkich 25 gier:

| grupa | gier | mediana `base[0]` | skrajne `base[0]` |
|---|---|---|---|
| rozwiązane (≥1 poziom) | 10 | **30** | min 7 (vc33), **max 55 (cd82)** |
| nierozwiązane | 15 | **32** | **min 18 (sb26)**, max 78 (g50t) |

Rozkłady się pokrywają: sb26 z `base[0]=18` jest czarna, a cd82 z `base[0]=55` rozwiązana
w 5 akcjach. **Nie planować selekcji gier po długości baseline.** (To już trzecia moja
niezweryfikowana intuicja w tej sesji, która nie przeżyła kontaktu z pomiarem — stąd ta
sekcja istnieje w tej formie.)

**(b) Nasze rozwiązania są KRÓTKIE — i to jest prawdziwy predyktor.** 15 rozwiązanych
poziomów: mediana **12 akcji**, max **28** (sp80). Przy capie 12 000 węzłów i rozgałęzieniu
`b` BFS sięga głębokości ≈ `log_b(12000)`: dla `b=8` (ft09) to 4.5 ruchu, dla `b=5` (ar25)
5.8, dla `b=11` (cn04) 3.9. Wszystkie trzy padły **dokładnie w tym zasięgu** (4, 15, 13 akcji
— cn04 i ar25 beamem, który nie jest ograniczony capem tak sztywno). Wniosek operacyjny:
**zwiększanie capa nie dokłada poziomów w grach o dużym rozgałęzieniu** — dokłada je dopiero
lepsza heurystyka albo redukcja rozgałęzienia.

**(c) tn36 to NIE gra kursorowa, tylko kombinatoryczna gra rysowania.** Poprawka do mojego
własnego opisu niżej („zmiana 1–4 px to ruch kursora"). Trzy pomiary:

1. *Struktura ramki* (render ASCII 64×64): duży pusty prostokąt `x∈[13,50], y∈[8,41]`
   = **płótno**, a pod nim rząd 5 bloków w `y∈[42,46]` = **paleta**. Dokładnie pokrywa się
   to ze zbiorem responsywnych współrzędnych ze skanu 4096 (`x∈[20,42], y∈[42,52]`).
2. *Kliki są ADDYTYWNE, nie przesuwają kursora*: klik w `(20,42)` dwa razy z rzędu zmienia
   ramkę o 4 px **za każdym razem** (zero powrotu do bazy), a „zaparkowanie" kursora
   kliknięciem referencyjnym NIE odtwarza ramki bazowej — 0 z 8 sekwencji wróciło do bazy,
   wszystkie dały dokładnie 8 px różnicy. Testowałem tę hipotezę, bo gdyby kursor był
   odwracalny, dałoby się go wyłączyć z klucza stanu i deduplikacja zaczęłaby działać.
   **Nie da się — parkowanie kursora jest ślepą uliczką.**
3. *Kliki są PRZEMIANNE*: `A potem B` vs `B potem A` → **0 px różnicy**, a zbiory zmienionych
   pikseli się **nie nakładają** (4 px + 4 px, część wspólna 0).

Konsekwencja: stan tn36 to **zbiór nałożonych znaczników**, więc przestrzeń przeszukiwania
jest kombinatoryczna `C(n,k)` w liczbie klików — deduplikacja po hashu ramki zwija
permutacje (to już działa), ale nie zmniejsza przestrzeni. Przy `base[0]=32` i ~33 różnych
efektach kliku potrzebna głębokość jest poza zasięgiem capu 12 000 węzłów. **Te gry wymagają
heurystyki pochodzącej z treści ramki** (np. „wypełniaj płótno według wzoru"), nie większej
mocy przeszukiwania. tn36 to przy okazji największy wyciek tokenów w ich r019 (86%).

**(d) `--min-moves`: próg fallbacku pruningu (naprawione i zmierzone).** Fallback działał
tylko gdy pruning zostawiał ZERO ruchów, więc gry z 1–2 ruchami po pruningu dostawały
zdegenerowany search. g50t: efektywne rozgałęzienie **2** i search kończył się w **0.2 s**
(cała osiągalna przestrzeń mieściła się w kilku węzłach — frontier wysychał natychmiast).
Po wprowadzeniu progu (`--min-moves 3`, przy mniejszej liczbie zachowujemy pełny zestaw):

| gra | rozgałęzienie | czas | poziomy |
|---|---|---|---|
| g50t | 2 → **5** | 0.2 s → **60.5 s** | 0 |
| sb26 | **5** | 18.7 s | 0 |
| sc25 | **32** (`dead_clicks`) | 90.5 s | 0 |

Czyli poprawka **usuwa natychmiastową śmierć searcha**, ale tych gier nie rozwiązuje —
potrzebują głębszego przeszukiwania lub innej heurystyki, nie szerszego zestawu ruchów.
Warto ją jednak mieć, bo bez niej gra znika z wyników w 0.2 s i wygląda na „pustą",
a nie na „nieprzeszukaną" — dokładnie ten błąd interpretacji popełniłem przy ft09.

### (e) Taksonomia `signal_quality` NIE przewiduje rozwiązywalności — obalone na 25 grach

Wprowadziłem pole `signal_quality` ∈ {`dead_clicks`, `cursor_only`, `ok`} i używałem go jak
wyjaśnienia „dlaczego ta gra jest czarna". Dokończyłem pomiar na wszystkich 25 grach nową
sondą `tools/calib_probe.py` (kalibracja bez searcha, 0.5–8 s na grę, importuje te same
funkcje co `sweep2.play_game`, więc metoda identyczna) i taksonomia się **nie broni**:

| `signal_quality` | rozwiązane | nierozwiązane |
|---|---|---|
| `cursor_only` | **3** | 7 |
| `dead_clicks` | **2** | 2 |
| `ok` | **5** | 6 |

Prawie idealny rozkład losowy. Kontrprzykłady, które to rozstrzygają:

- **vc33** — `cursor_only`, mediana zmiany **1 px**, 3 różne efekty kliku — a dała **2 poziomy
  = 10.71 pkt**, nasz drugi najlepszy wynik po tu93.
- **sp80** — `cursor_only`, **1** różny efekt kliku, a rozwiązana (28 akcji).
- **cd82** — `cursor_only`, rozwiązana w 5 akcjach.
- **sb26** — `ok`, rozgałęzienie **5** (niskie, czyli teoretycznie łatwe dla BFS), a czarna.
- **re86 / tr87 / wa30 / g50t** — wszystkie `ok` z rozgałęzieniem 2–5, wszystkie czarne.
- **r11l** — **198** różnych efektów kliku (najwięcej z 25 gier), a 0 poziomów.

Rozgałęzienie też nie przewiduje: przy 4 rozwiązane 3 / czarne 2, przy 19 — rozwiązane 2 /
czarna 1, przy 18 — rozwiązane 0 / czarne 3.

**Wniosek operacyjny (ważniejszy niż sama taksonomia):** tych pól wolno używać wyłącznie do
**diagnozowania, dlaczego konkretny przebieg umarł** (`effective_branch=0` → brak ruchów;
`dead_clicks` → kryterium „ramka się zmieniła" nie widzi legalnych ruchów). **Nie wolno**
nimi selekcjonować gier do przeszukania ani prognozować wyniku. Kto tak zrobi, pominie vc33
(10.71 pkt!) i zmarnuje czas na sb26.

Jedyny wzorzec, który przeżył pomiar, to punkt (b): **nasze rozwiązania są krótkie**
(mediana 13 akcji, max 29), a BFS przy capie 12 000 sięga `log_b(12000)` ruchów. Predyktorem
jest długość minimalnego rozwiązania — której z góry nie znamy i której żadna mierzalna
własność ramki nie ujawnia. Dlatego uczciwa odpowiedź na „które gry da się rozwiązać
offline" brzmi: **trzeba po prostu przeszukać**, a nie triage'ować.

Komplet diagnostyki per gra (25/25): `results/game_metadata.json`, klucze `signal_quality`,
`effective_branch`, `calib_distinct_effects`, `calib_median_delta`, `calibration`,
`calibration_source`, plus podsumowanie w `_diagnostics_predictivity`.


### (f) DWA różne tryby porażki — i tylko jeden z nich leczy się budżetem

Wynik „0 poziomów" sam w sobie **nie mówi nic**. Dopiero zestawienie liczby rozwiniętych
węzłów z capem i liczby różnych stanów rozdziela dwie przyczyny (pomiary z 4 przebiegów,
kolumna `stany/węzeł` to wydajność deduplikacji):

**UWAGA — ta taksonomia została UZUPEŁNIONA po przebiegu z capem 60 000 (punkt (g) niżej).**
Poniższe dwa tryby są prawdziwe, ale niekompletne: okazało się, że trybów jest **TRZY**
(doszło ucięcie **czasem**, a nie węzłami) i że przypisanie gry do trybu **zależy od budżetu**,
więc nie jest stałą cechą gry. Czytaj razem z punktem (g).

**Tryb 1 — UCIĘTE CAPEM** (frontier miał jeszcze stany, budżet przerwał). Te gry **mogą**
zyskać na większym budżecie:

| gra | rozg. | węzły | różne stany | stany/węzeł | cap |
|---|---|---|---|---|---|
| s5i5 | 14 | 12 012 | 1 941 | 0.16 | 12 000 |
| dc22 | 18 | 12 006 | 2 031 | 0.17 | 12 000 |
| ka59 | 18 | 12 006 | 1 273 | 0.11 | 12 000 |
| re86 | 5 | 12 000 | 4 611 | 0.38 | 12 000 |
| sc25 | 18 | 12 000 | 1 814 | 0.15 | 12 000 |
| sk48 | 3 | 12 000 | 4 866 | 0.41 | 12 000 |
| tr87 | 4 | 12 000 | 6 792 | 0.57 | 12 000 |
| wa30 | 4 | 12 000 | 3 271 | 0.27 | 12 000 |

**Tryb 2 — WYCZERPANY FRONTIER** (przestrzeń stanów się zawaliła przez deduplikację).
Tu **większy budżet nie może pomóc z definicji** — nie zostało nic do rozwinięcia:

| gra | rozg. | węzły | różne stany | stany/węzeł |
|---|---|---|---|---|
| g50t | 2 | **36** | 17 | 0.47 |
| bp35 | 17 | **357** | 139 | 0.39 |
| sb26 | 5 | 1 982 | 66 | 0.03 |
| lf52 | 19 | 2 150 | 94 | 0.04 |
| r11l | 14 | 2 758 | 770 | 0.28 |
| su15 | 14 | 5 404 | 385 | 0.07 |

g50t jest skrajnym przypadkiem: **36 węzłów w 0.2 s** — cała osiągalna przestrzeń stanów
tej gry mieści się w 17 różnych ramkach. Żaden cap tego nie zmieni; zmienia to dopiero inny
zestaw ruchów (dlatego `--min-moves` podniósł ją z 2 do 5 rozgałęzień i z 0.2 s do 60.5 s —
ale poziomów nadal 0, patrz punkt (d)).

**Kolumna `stany/węzeł` jest tu najlepszym pojedynczym wskaźnikiem.** Niska (0.03–0.11:
sb26, lf52, su15, vc33, m0r0) oznacza, że deduplikacja zjada prawie wszystko, co generuje
search — czyli ruchy są w dużej mierze odwracalne albo prowadzą do tych samych stanów.
Wysoka (0.38–0.57: re86, sk48, tr87, g50t) oznacza realnie rosnącą przestrzeń.

Wniosek operacyjny: **zanim ktokolwiek podniesie cap, ma sprawdzić, w którym trybie jest
gra.** Podnoszenie capa grze z trybu 2 to czyste marnowanie CPU; z kolei tryb 1 to jedyna
kategoria, w której „więcej mocy" cokolwiek da — i dokładnie te 8 gier poszło do przebiegu
z capem 60 000 (wynik: `results/sweep3_bigcap.jsonl`).

Przy okazji prostuje to moją własną tezę z punktu (b), która była **niepełna**: napisałem
„zwiększanie capa nie dokłada poziomów przy dużym rozgałęzieniu". To prawda dla gier, które
wyczerpały frontier, ale 8 z 15 czarnych gier zostało uciętych **w połowie** — dla nich
cap był realnym ograniczeniem, nie heurystyka. Poprawne sformułowanie: *cap nie pomaga
grom z trybu 2 i grom, których minimalne rozwiązanie jest dłuższe niż `log_b(cap)`;
pomaga wyłącznie grom z trybu 1, których rozwiązanie mieści się w zasięgu po zwiększeniu
budżetu.*


### (g) Przebieg z capem 60 000: hipoteza POTWIERDZONA, taksonomia ROZSZERZONA do trzech trybów

Punkt (f) kończył się wnioskiem, że 8 gier zostało uciętych capem i dla nich większy budżet
może coś dać. Uruchomiłem dokładnie ten test: cap **60 000** węzłów (5×), **600 s** na grę,
1 worker, `--min-moves 3`, tylko na tej ósemce. Wynik: `results/sweep3_bigcap.jsonl`.

**Hipoteza potwierdzona — s5i5 rozwiązana.** Ucięta przy 12 012 węzłach, rozwiązana przy
**45 377** węzłach: 1 poziom w **21 akcjach**, replay OK. Czyli cap 12 000 był realnym
blokerem, nie heurystyka. Playbook rośnie z 10 do **11 gier / 16 poziomów / 3.18 pkt LB**.

Ale pełny obraz jest ciekawszy i **prostuje punkt (f)**:

| gra | węzły | różne stany | sekundy | co przerwało | s/węzeł |
|---|---|---|---|---|---|
| s5i5 | 45 377 | 9 504 | 211.3 | **ROZWIĄZANA** | 0.005 |
| ka59 | 60 012 | 5 983 | 132.4 | limit węzłów 60 000 | 0.002 |
| re86 | 60 000 | 19 572 | 160.2 | limit węzłów 60 000 | 0.003 |
| sk48 | 42 396 | 16 127 | 600.0 | **limit CZASU** 600 s | 0.01 |
| tr87 | 22 112 | 10 398 | 602.1 | **limit CZASU** 600 s | 0.03 |
| wa30 | **940** | 338 | 601.2 | **limit CZASU** 600 s | **0.64** |
| dc22 | 37 548 | 4 278 | 272.7 | frontier wyczerpany | 0.007 |
| sc25 | 29 952 | 3 168 | 324.1 | frontier wyczerpany | 0.011 |

Trzy wnioski, z których dwa są korektą mojego własnego wpisu:

**1. Trybów jest TRZY, nie dwa.** Doszło `time_cut` — gra przerywa na limicie czasu z
nieprzerobionym frontierem. To nie jest to samo co `node_cap_cut`, bo leczy się inaczej:
sk48 i tr87 robiły 0.01–0.03 s/węzeł, więc potrzebują **więcej czasu** (i wtedy automatycznie
więcej węzłów), a wa30 robi **0.64 s/węzeł** — jej nie pomoże ani większy cap węzłów, ani
nawet większy czas w rozsądnej skali, bo jeden węzeł kosztuje tyle, co w innych grach 200.
Przy 60 000 węzłów wa30 potrzebowałaby **10.7 godziny**.

**2. Przypisanie trybu ZALEŻY OD BUDŻETU — nie jest stałą cechą gry.** dc22 i sc25 przy capie
12 000 wyglądały na „ucięte capem" (dokładnie 12 006 i 12 000 węzłów), a przy 60 000 okazały
się **wyczerpane** (37 548 i 29 952 — frontier się skończył przed capem). Czyli podniesienie
budżetu może grę **przeklasyfikować** z trybu 1 do trybu 2 i to jest właśnie wartość tego
przebiegu: uczciwa odpowiedź „tu już nie ma czego szukać" zamiast „może kiedyś".

**3. Kolejność sprawdzania warunków ma znaczenie.** Klasyfikacja musi iść: **najpierw czas,
potem węzły, na końcu wyczerpanie**. Przy blokadzie na animacji (wa30, bp35, lf52) węzły nigdy
nie dochodzą do capa, więc sprawdzanie najpierw węzłów oznaczyłoby je jako „wyczerpane",
czyli dokładnie odwrotnie niż prawda. bp35: 357 węzłów w 300 s = 1.35 s/węzeł — to gra
zablokowana na animacji, nie gra z małą przestrzenią stanów.

Rozkład po wszystkich 25 grach (pole `failure_mode` w `results/game_metadata.json`):
**`time_cut` 6, `frontier_exhausted` 6, `node_cap_cut` 2** (ka59, re86 — jedyne dwie, dla
których dalsze podnoszenie capa węzłów ma jeszcze sens).

**Wniosek operacyjny, zaktualizowany:** zanim podniesiesz jakikolwiek budżet, odczytaj
`failure_mode` i `stopped_by` z `game_metadata.json`. Dla `frontier_exhausted` nie rób nic
(zmieniaj generator ruchów, nie budżet). Dla `time_cut` sprawdź `s/węzeł`: poniżej ~0.05
warto dać więcej czasu, powyżej ~0.5 gra jest zablokowana na animacji i żaden budżet nie
pomoże. Dla `node_cap_cut` podnieś cap.


### (h) Prawdziwym ograniczeniem searcha jest PAMIĘĆ FRONTIERU, nie cap węzłów

Zmierzone przez `resource.getrusage(RUSAGE_SELF).ru_maxrss` na 300 `deepcopy` stanu gry:

| gra | MB / stan | 10 000 stanów | 60 000 stanów | tryb searcha |
|---|---|---|---|---|
| **re86** | **0.190** | 1.9 GB | **11.1 GB** | bfs (frontier nieograniczony) |
| ka59 | ~0.000 | ~0 GB | ~0 GB | beam (frontier i tak ograniczony szerokością) |

Dostępny RAM w sandboxie: **3 939 MB** (`free -m`).

Konsekwencje — i to jest wyjaśnienie dwóch awarii, które wcześniej tylko opisałem jako
„presja pamięci", nie znając przyczyny:

1. **Przebieg v3 na re86 był na samej krawędzi OOM.** Zrobił 19 572 różne stany × 0.190 MB
   = **~3.7 GB** przy 3.9 GB dostępnych. Przeżył, ale przypadkiem.
2. **Zapaść przy 2 workerach** (kswapd0 100%, powłoka przestała odpowiadać, `bash` zwracał
   puste timeouty) to nie była „ogólna presja" — to dwa procesy BFS z nieograniczonym
   frontierem, każdy po kilkaset MB na stan w grach typu re86.
3. **Frontier BFS rośnie nieograniczenie z definicji**, bo `search_level` w trybie `bfs`
   dokłada każdego nowego potomka i nigdy niczego nie usuwa. Tryb `beam` ma ograniczenie
   (`beam_width`), więc jest bezpieczny — dlatego ka59 kosztuje ~0 MB/stan.

**Lekarstwo (wprowadzone):** `sweep2.py --frontier-cap N` — w trybie BFS, gdy frontier
przekroczy N stanów, tnie po nowości ramki. To zamienia BFS w best-first (traci
zupełność, ale BFS z capem węzłów i tak nie jest zupełny), za to pozwala podnieść cap węzłów
o rząd wielkości bez OOM. `--frontier-cap 0` = stare zachowanie.

**Reguła dla każdego, kto będzie to uruchamiał:** przy grach z trybem `bfs` i dużym capie
węzłów ZAWSZE ustawiaj `--frontier-cap`. Orientacyjnie: `frontier_cap × MB_na_stan < 0.5 ×
dostępny RAM`. Dla re86 (0.190 MB/stan) i 3.9 GB RAM daje to `frontier_cap ≤ 10 000`;
użyłem 4 000 dla zapasu.

Przy okazji: to jest ten sam mechanizm, który w ich harnessie ogranicza liczbę gier
równoległych — `ARC3_MAX_ACTIVE_STREAMS=10` przy puli KV 1 011 264 tokenów. U nas
ograniczaczem jest RAM na stany gry, u nich VRAM na kontekst, ale struktura problemu
identyczna: **wąskim gardłem jest pamięć na stan, nie moc obliczeniowa**.


### (i) Przebieg v4 z `--frontier-cap`: ka59 domknięta, re86 nadal otwarta

Test rozstrzygający dla dwóch gier, które po v3 miały `failure_mode = node_cap_cut` — czyli
jedynych, dla których dalsze podnoszenie budżetu miało w ogóle sens. Parametry: cap
**200 000** węzłów (16× więcej niż v1), **900 s** na grę, `--frontier-cap 4000`, 1 worker.

| gra | węzły | różne stany | sekundy | s/węzeł | werdykt |
|---|---|---|---|---|---|
| ka59 | 115 740 | 10 643 | 250.1 | 0.002 | **frontier WYCZERPANY** — nie doszła ani do capa węzłów (200 000), ani do limitu czasu (900 s) |
| re86 | **200 000** | **94 405** | 678.7 | 0.003 | nadal `node_cap_cut` |

Trzy wnioski:

**1. ka59 jest domknięta — budżet jej nie pomoże, kropka.** W v3 wyglądała na uciętą capem
(60 012 węzłów), ale przy 200 000 skończyła na 115 740 z wyczerpanym frontierem. To drugi
przypadek (po dc22 i sc25) przeklasyfikowania z trybu 1 do trybu 2 po podniesieniu budżetu —
i dokładnie dlatego warto było ten przebieg zrobić: zamienia „może kiedyś" w zmierzone „nie".

**2. `--frontier-cap` działa i to on umożliwił ten przebieg.** re86 rozwinęła **94 405
różnych stanów** (w v3: 19 572) przy szczycie RAM **1 066 MB z 3 939 MB**. Bez ograniczenia
frontieru te 94 405 stanów × 0.190 MB = **17.9 GB** — czyli przebieg byłby fizycznie
niemożliwy w tym sandboxie. Kluczowe rozróżnienie, które to umożliwia: zbiór `seen` trzyma
tylko **hashe** ramek (~8 B każdy, 94 405 × 8 B ≈ 0.75 MB), a frontier trzyma **obiekty gry**
(0.190 MB każdy). Tniemy więc to, co drogie, zostawiając to, co tanie — dzięki temu deduplikacja
pozostaje pełna nawet przy ograniczonym frontierze.

**3. re86 zostaje jedyną grą z `node_cap_cut`** i jedyną, dla której dalsze podnoszenie capa
ma jeszcze jakikolwiek sens. Uczciwy rachunek kosztu: 200 000 węzłów = 679 s, więc podwojenie
to ~23 min na jedną grę, a w runie konkursowym jest 110 gier i budżet 532 min/grę **łącznie
z pracą modelu**. Czyli search tej głębokości nie zmieści się w runie jako fallback —
nadaje się wyłącznie do przygotowania playbooka offline, co zresztą jest dokładnie tym,
do czego go używamy.

Rozkład `failure_mode` po 25 grach i 6 przebiegach: **`time_cut` 6, `frontier_exhausted` 7,
`node_cap_cut` 1** (re86). Dane per gra: `results/game_metadata.json`, pola `failure_mode`
i `stopped_by`; surowe przebiegi: `results/sweep4_memcap.jsonl` (ka59 + przerwany re86)
i `results/sweep4_re86.jsonl` (re86 po naprawie buga).

**Bug znaleziony przy tym przebiegu:** `--frontier-cap` w pierwszej wersji wołał
`frontier.sort(...)`, ale w trybie `bfs` frontier jest typu `deque`, który **nie ma** `.sort()`
→ `AttributeError` i cały przebieg re86 przepadł (ka59 przeszła, bo idzie `beam`, gdzie
frontier jest listą). Naprawione przez `frontier = deque(sorted(frontier, ...)[:frontier_cap])`.
Reguła: **ten sam kod ścieżki BFS i beam operuje na różnych typach kontenera** (`deque` vs
`list`), więc każda nowa operacja na frontierze musi być sprawdzona w OBU trybach — test na
jednej grze `beam` tego nie wykryje.


### Czego wciąż nie umiemy (uczciwie)

- **sc25 i gry z odroczonym efektem**: legalne ruchy nie zmieniają ramki natychmiast, więc
  ani kalibracja, ani heurystyka nowości ich nie widzą. Potrzebne porównywanie stanów po
  sekwencji 2–3 akcji (koszt ×branching² — dla 13 ruchów to 169 prób na stan, wciąż tanie).
- **tn36 i gry addytywne**: POPRAWKA — to nie kursor, tylko nakładane znaczniki (punkt (c)
  wyżej: przemienne, addytywne, nieodwracalne). Bez heurystyki czytającej treść ramki beam
  idzie w ślepe uliczki, a przestrzeń jest kombinatoryczna w liczbie klików.

---

## 2. Punktacja — formuła, dowód i twierdzenie o capie

Źródło: `taaf/game.py:381-413` w ich gałęzi (przepisane, nie zgadnięte).

```
poziom k : score_k = min(115, (baseline_k / actions_k)^2 * 100)   jeśli ukończony, else 0
waga     : w_k = k + 1
gra      : score = Sum(score_k * w_k) / Sum(w_k po WSZYSTKICH poziomach)
           z capem = Sum(w_k ukończonych) / Sum(w_k) * 100
LB       : średnia po 110 runach
```

**110 runów to nie 110 różnych gier.** `taaf/competition_arcade.py`:
`OFFICIAL_110_RUN_COUNT = 110`, a `official_110()` buduje cykliczne klony 25 oficjalnych gier
(`clone_prefix='k'`, `i % len(source_ids)`). Publiczny notebook `arc3-arena-hero-v2-runb`
opisuje to jako „110 independent cyclic replicas of the 20 public games, 1800 s of gameplay".
→ **średnia po 110 runach ≈ średnia po 25 grach**, więc wartość playbooka liczę jako
`Sum(score_gier) / 25`.

### Weryfikacja co do setnej (na ich własnym smoke r019)

| gra | poziomy | opublikowane | formuła odwrotna daje | rachunek w przód |
|---|---|---|---|---|
| tn36 | 7, ukończony 1 | **3.57** | 32.0 akcji przy baseline 32 | 100 · 1/28 = **3.57** ✓ |
| ls20 | 7, ukończony 1 | **3.27** | 23.0 akcji przy baseline 22 | 91.5 · 1/28 = **3.27** ✓ |

`tools/score_formula.py --verify` robi dokładnie ten rachunek. Skoro formuła odtwarza ich
wyniki, można nią liczyć wartość czegokolwiek przed wydaniem tokena.

### TWIERDZENIE: cap zawsze wiąże przy grze ≤1.07× baseline

Niech gra ma poziomy o wagach `w_k`, ukończono zbiór `S`. Wtedy

```
num/tot = Sum_{k in S} min(115, (b_k/a_k)^2*100) * w_k / Sum(w)
cap     = 100 * Sum_{k in S} w_k / Sum(w)
```

Jeśli każdy ukończony poziom zagrano w `a_k <= b_k * sqrt(115/100) = 1.0724 * b_k` akcji,
to `score_k = 115` i `num/tot = 115 * Sum(w_S)/Sum(w) > cap`, więc `min(...) = cap`:

> **score_gry = 100 · Sum(w ukończonych poziomów) / Sum(w wszystkich poziomów)**

Czyli: **przy dostatecznie dobrej efektywności wynik zależy WYŁĄCZNIE od tego, KTÓRE poziomy
się ukończyło — a nie od tego, iloma akcjami.** Wszystko poniżej progu 1.07× baseline jest
warte dokładnie zero.

Potwierdzenie z moich pomiarów: tu93 z 5 poziomami (18/19, 10/16, 19/34, 17/42, 29/123 akcji
— każdy ≤ baseline) wyszedł **33.33 = 100·(1+2+3+4+5)/(1+…+9) = 100·15/45**, czyli *dokładnie*
w capie. ls20 (13 akcji przy baseline 22) → cap `100·1/28 = 3.57`, i tyle wyszło.

Trzy konsekwencje, które zmieniają priorytety:

1. **Głębokość jest jedyną dźwignią.** Jeden poziom w 7-poziomowej grze jest warty **maksymalnie
   3.57 pkt**, nawet za 1 akcję. Pięć poziomów w 9-poziomowej = 33.33. Stosunek 9.3×.
2. **Optymalizacja liczby akcji jest prawie darmowa.** Ich r019: sufit z głębokości **29.0** vs
   pomierzone **27.21** → cała strata z nieefektywnego grania to **1.75 pkt** na cały leaderboard.
   Nie warto oddawać za to ani jednego slota.
3. **Porzucony poziom to 0, ale jego waga zostaje w mianowniku.** Stąd 35% tokenów wydanych
   na poziom, który nigdy nie pada (§6), jest tak kosztowne: nie dość, że nic nie daje, to
   jeszcze odbiera przepustowość poziomom, które by coś dały.

Pełne sufity per gra: `results/game_metadata.json` → `depth_ceiling_1_level`,
`depth_ceiling_all`, oraz `summary.if_every_game_got_1_more_level_lb_points = 7.67`.

---

## 3. 25 oficjalnych gier (baseline z ich `metadata.json`)

`Lv` = liczba poziomów, `ΣBas` = suma baseline_actions (ile akcji potrzeba na całą grę
przy referencyjnej rozgrywce), `sufit L1` = max punktów za sam poziom 0.

| gra | Lv | ΣBas | tagi | search: poziomy | score | sufit L1 |
|---|---|---|---|---|---|---|
| **tu93** | 9 | 462 | keyboard_click | **5** | **33.33** | 2.22 |
| **vc33** | 7 | 447 | click | **2** | **10.71** | 3.57 |
| cd82 | 6 | 171 | keyboard_click | 1 | 4.76 | 4.76 |
| m0r0 | 6 | 1107 | keyboard_click | 1 | 4.76 | 4.76 |
| sp80 | 6 | 518 | keyboard_click | 1 | 4.76 | 4.76 |
| ls20 | 7 | 776 | keyboard | 1 | 3.57 | 3.57 |
| lp85 | 8 | 388 | click | 1 | 2.78 | 2.78 |
| ar25 | 8 | 748 | keyboard_click | **1 (15 akcji)** | **2.78** | 2.78 |
| bp35 | 9 | 651 | keyboard_click | 0 | — | 2.22 |
| cn04 | 6 | 789 | keyboard_click | **1 (13 akcji)** | **4.76** | 4.76 |
| dc22 | 6 | 1228 | keyboard_click | 0 | — | 4.76 |
| ft09 | 6 | 208 | *(brak tagu)* | **1** (sweep2, 4 akcje) | 4.76 | 4.76 |
| g50t | 7 | 879 | keyboard | 0 | — | 3.57 |
| ka59 | 7 | 730 | keyboard_click | 0 | — | 3.57 |
| lf52 | 10 | 1339 | click | 0 | — | 1.82 |
| r11l | 6 | 233 | click | 0 | — | 4.76 |
| re86 | 8 | 1255 | keyboard_click | 0 | — | 2.78 |
| s5i5 | 8 | 638 | click | **1** (sweep3, 21 akcji) | **2.52** | 2.78 |
| sb26 | 8 | 213 | keyboard_click | 0 | — | 2.78 |
| sc25 | 6 | 350 | keyboard_click | 0 | — | 4.76 |
| sk48 | 8 | 1070 | keyboard_click | 0 | — | 2.78 |
| su15 | 9 | 361 | click | 0 | — | 2.22 |
| tn36 | 7 | 317 | click | 0 | — | 3.57 |
| tr87 | 6 | 414 | keyboard | 0 | — | 4.76 |
| wa30 | 9 | 1843 | keyboard | 0 | — | 2.22 |

Statystyki: średnio **7.32** poziomu/grę, średnia `ΣBas` **685.4**, mediana **638**,
min **171** (cd82), max **1843** (wa30). Tagi: 4 keyboard / 7 click / 13 keyboard_click / 1 brak.

**Stan naszego przeszukiwania offline (0 tokenów LLM, 3 przebiegi scalone po najlepszym
wyniku na grę): 11/25 gier, 16 poziomów, 3.18 pkt LB podłogi**, każda sekwencja
zweryfikowana replayem na świeżej instancji (2×). Rozbicie: tu93 5 poziomów (33.33 pkt),
vc33 2 (10.71), a po 1 poziomie: cd82, cn04, ft09, m0r0, sp80 (po 4.76), ls20 (3.57),
ar25, lp85 (po 2.78). Trzy gry (ar25, cn04, ft09) doszły dopiero po zmianie generatora
ruchów na kalibrację po efekcie — §1bis.

Nierozwiązane (14): bp35, dc22, g50t, ka59, lf52, r11l, re86, sb26, sc25, sk48,
su15, tn36, tr87, wa30. Wzorzec: `signal_quality=cursor_only` (klik zmienia 1-4 px = kursor,
więc heurystyka nowości jest szumem) albo gry z odroczonym efektem (sc25: 0 z 4096 klików
zmienia ramkę od razu). Osobny przypadek: **g50t ma efektywne rozgałęzienie 2 i search
kończy się w 0.2 s** — frontier wysycha natychmiast, więc tam brakuje nie mocy, a ruchu,
który zmienia stan w widoczny sposób.

Komplet danych per gra (baseline, `available_actions`, efektywne rozgałęzienie, jakość
sygnału, liczba różnych efektów kliku, wynik, sufity głębokości): **`results/game_metadata.json`**.

Wniosek operacyjny: `ΣBas ≈ 685` akcji na grę, a realny budżet to ~208 akcji/grę (§6) =
**30% tego, co potrzeba na całą grę**. Nikt nie przechodzi gier w całości — wygrywa ten,
kto najtaniej kupuje **głębokość**, a nie ten, kto gra najdokładniej.

---

## 4. Ich harness i konfiguracja (duck-v7 `arc3-duck.ipynb`, 30 komórek)

| komórka | co robi |
|---|---|
| 1 | `ARC3_VARIANT` (env + `patch_files`) + **preflight**: sprawdza GPU (`RTX PRO 6000`) i 5 inputów, rzuca `RuntimeError` — ale **tylko gdy nie rerun** (`if _pf_errors and not _pf_rerun`), więc w prawdziwym submitcie preflight nigdy nie ratuje |
| 4 | `%%writefile /kaggle/harness-changes.patch` — patch Franzena, 498 KB, 16 plików |
| 5,6,7 | patche 0001/0002/0003 jako stringi w `_P(...).write_text(...)` |
| 9 | `rm -Rf $BUNDLE_DIR; cp -a $ORIG_BUNDLE_DIR $BUNDLE_DIR`, potem `git apply --include=ARC3-Inference/* ... check=True` dla patcha Franzena **i** dla każdego z `patch_files`; dalej cały `setup_env` |
| 17 | launcher SGLang z CFG |
| 21 | customization hook (smoke vs TRUE_SUBMISSION) |
| 25 | run benchmarku |
| 29 | smoke verdict |

Config z cell 9 (wartości dosłowne):

```
LOCAL_ANALYZER_CONTEXT_WINDOW = (116+12)*1024      LOCAL_ANALYZER_MAX_OUTPUT = 12*1024
ARC3_CONTEXT_DRAIN_TOKENS     = 58*1024            ARC3_HISTORY_ASSISTANT_TURNS = 150
ARC3_MEMORY_SECTIONS          = 'off'              ARC3_PERSISTENT_FUNCTIONS = 1, scope='game'
ARC3_EXPOSE_UNDO              = 'on'               MULTIMODAL_UPSCALE = 10
ARC3_MAX_ACTIVE_STREAMS       = 10                 TAIL_LOOKUP='remaining', SCORE_NORMALIZATION=1
ONLY_RESET_LEVELS             = 'true'   <- RESET NIE kasuje ukończonych poziomów
TAAF_RUN_AS_SUBMISSION / TAAF_MINIMAL_DIAGNOSTICS = 1 gdy KAGGLE_IS_COMPETITION_RERUN
LOCAL_ANALYZER_TEMPERATURE=0.7 TOP_P=0.95 TOP_K=20 ENABLE_THINKING=true TOOL_STEPS=0 TOOL_TIMEOUT=30
```

Cell 21: smoke = **10 gier × 48 min, concurrency 10**; `TRUE_SUBMISSION` = `n_passes=1`,
`concurrency=120`, `max_runtime_s_per_game=532*60`; budżet notebooka **32400 s**.

Cell 17 (SGLang): `CTX=(116+12+8)*1024`, `MEMFRAC=0.96`, `MAXREQ=10`, `CUDAGRAPH_MAXBS=10`
(assert `CUDAGRAPH_MAXBS >= MAXREQ`), `MAMBA_CACHE=60`, `CHUNK=8192`, `MAX_PREFILL=16384`,
`SPEC=True SPEC_STEPS=3`, `KVDTYPE=fp8_e4m3`; modele `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround`
+ drafter `dfranzen/albucino-qwen3-8-flash-next-drafter`, dataset `dfranzen/pennyroyal-v253`,
maszyna `NvidiaRtxPro6000`.

Istotne dla nas: `solver.py` ma już `_execute_auto_reset()` (L1228) wołające
`_execute_action(ActionInput(id=GameAction.RESET), generated_tokens=0, automatic=True)` —
czyli **darmowy reset poziomu istnieje w harnessie** i razem z `ONLY_RESET_LEVELS=true`
nie kasuje postępu. Na tym opiera się patch 0004.

Drugi kernel — `duck-original` (to z niego idzie V8): notebook
`tufa-labs-duck-harness-june-30-milestone-winner.ipynb`, **17 komórek, ZERO patchy**
(ani `patch_files`, ani `harness-changes`, ani `git apply`). Customization hook = cell 12
(`bm`, `bm.games`, `bm.solver`). `_HarnessGameSession` istnieje też w czystym bundle (L168),
więc monkeypatch `should_stop` jest tam możliwy — ale bez mechanizmu patchy nie da się
wstrzyknąć darmowego RESET-u w pętlę `play()`.

---

## 5. Serwer (z `serve.log` runa r019, 1.13 MB)

| pozycja | wartość |
|---|---|
| wagi modelu | **69.85 GB** INT4 (`Qwen4ExpForConditionalGeneration`, auto-round bits=4) |
| drafter | 3.79 GB |
| mamba cache (60 slotów) | 3.35 GB |
| KV cache | 11.6 GB → **1 011 264 tokenów** |
| dostępne po załadowaniu | 4.25 GB |
| `max_running_requests` | **10** |
| `context_len` | 139264 |

Decode throughput w zależności od batcha: `1→179`, `5→496`, `7→673`, `9→753`, `10→792` tok/s
(max zaobserwowane 930). ms/krok rośnie `16 → 33` przy batchu 1→10.

Wykorzystanie: `full token usage` mediana **0.71**, max **0.99** (→ **KV jest limitem**, nie mamba);
`mamba usage` **0.60** (ma zapas). `accept len` 2.65 z 4, `accept rate` 0.55.
Prefix cache: **61.7M cached vs 4.54M new = 93.2%** trafień.

EKSTRAPOLACJA (nie pomiar): `MAXREQ` 10→16-20 dałoby ~+45% poolu KV przy ms/krok 27→33,
ale wymaga ścięcia `CONTEXT_WINDOW` 128k→~52k, `ARC3_CONTEXT_DRAIN_TOKENS` 58k→~24k,
podniesienia `MAMBA_CACHE` 60→~80 i `CUDAGRAPH_MAXBS >= MAXREQ`. To lever #3, nie #1 —
kosztuje 1 smoke i może popsuć jakość przez krótszy kontekst.

---

## 6. Pomiary runów

### r019 — smoke duck-v7 (10 gier × 48 min), **wszystkie gry `gave_up`**

| metryka | wartość |
|---|---|
| średni score | **27.21** |
| sufit z osiągniętej głębokości | **29.0** |
| +1 poziom w każdej grze | **44.8** |
| +2 poziomy w każdej grze | **64.5** |
| tokeny razem | **1.74 M** |
| akcje razem | **2065** |
| **tokeny na akcję** | **841** |
| **udział tokenów i akcji na poziomie, który nigdy nie został ukończony** | **35%** |

Per gra (wyciek na niedokończonym poziomie): **tn36 86%** (L=1, score 3.57), **ls20 91%**
(L=1, 3.27), ka59 46%, g50t 49%. Najlepsza gra: **su15 L=7/9, score 56.42**.

Arytmetyka budżetu (z tych liczb, nie z ich krzywej):
`755 tok/s × 532 min / 110 gier = 219k` tokenów/grę, × 0.80 realnej sprawności =
**~175k tokenów/grę**; ÷ 841 tok/akcję = **~208 akcji/grę**, wobec `ΣBas ≈ 685` potrzebnych
na całą grę. Ale gdy agent raz zrozumie mechanikę, kończy poziomy w 0.3–0.9× baseline
(cn04: 145 akcji na 4 poziomy przy baseline 468) — więc **4–5 poziomów JEST w zasięgu**,
o ile nic nie jest marnowane.

### r050 — `arc3-duck-original` (Tufa vLLM, Qwen3.6-27B-FP8)

1 gra (sk48), 1 pass, 2h12m, **521 akcji, 231k tokenów, 29.21 tok/s wallclock, 0/8 poziomów,
score 0.00**. To jest dowód, że sam harness Tufy bez naszego mózgu nie punktuje wcale —
i że 231k tokenów można przepalić na zero.

### POPRAWKA: ich krzywa tokenowa nie istnieje

`FINDINGS-2026-10-13.md` (15.10) podaje: `100k→24.7`, `175k→27.2`, `200k→41.8`, `300k→45.7`
i plan `v7-abandon` z oczekiwanym wynikiem **31–34**. Punkty 200k i 300k **sprzeczają się z ich
własnym pomiarem**: realny run daje ~175–219k tokenów/grę, czyli 26–27 LB. Skoku 27.2→41.8
między 175k a 200k nie da się obronić żadnym mechanizmem, a `v7-abandon` jest martwym kodem
(§9). **Nie planować na tej krzywej.**

---

## 7. Stan Kaggle (na 24.10)

**Submisyje** (z `ops/results/r062-submissions`): najlepsza **26.25** (duck v3, z 16.10,
smoke 29.02), 24.66 (v2-think-less), 23.94 (v5-world-model), 0.01 (placeholder), dwie `t4`
z błędem. Brak submisyji 17–23.10 (wyczerpany GPU quota).

**Leaderboard** (stan 10.10, `public_leaderboard.csv`): Yi-Chia Chen 62.96, Tufa Labs 56.52,
mtg 45.00, Majkel1337 42.66, the last dance 42.55, **NVARC3 40.97 = 5. miejsce / próg
nagrody**; mediana 38.17. Nagrody: **$75k za top-5** (40/15/10/5/5k USD), write-up niewymagany.

Czyli próg nagrody 40.97 to dokładnie scenariusz „**+1 poziom w każdej grze**" (r019: 44.8).
Z 26.25 brakuje ~14.7 pkt — to jest ~4 poziomy w tu93-podobnych grach albo +1 poziom
w połowie stawki. Nie da się tego dokupić efektywnością (warta 1.75 pkt, §2).

**GPU quota**: „Maximum weekly GPU quota of 30.00 hours reached" — wyczerpana 16.10.
**API submit zwraca `400 CreateCodeSubmission`** dla v5/v7 → potrzebny klik w UI (ich ops
ma `fallback_submit: true`, ale to nie obchodzi błędu API).

**Terminy**: entry deadline **26 X 2026** (już spełniony, 6 zaliczonych submisyji);
**final submission deadline 2 XI 2026** (~9 dni, ~8 slotów przy 1/dzień); wyniki **4 XII**.
Uwaga: „2 dni do deadline", o których była mowa, to był deadline **zgłoszenia**, nie wyników.

---

## 8. Kolejka ops (stan 24.10 ~16:20 UTC)

`arc-agi-3/kaggle/ops/request.json` = **r065**, op `chain`:

```
sleep 1 min → midnight-launch {kernel: petersharps/arc3-duck-original, dir: duck-original,
              version_hint: 8, poll_max_iters: 18}
            → next: r066 auto-submit {kernel: ...duck-original, confirm: true, version: 8,
              file: arc-agi-3/kaggle/results/submission.parquet, max_poll_minutes: 90,
              fallback_submit: true, message: "arc3-duck-original v8 (=v5 config, dowod COMPLETE)"}
```

Runy `.github/workflows/arc3-ops.yml`:

| SHA | status | od |
|---|---|---|
| `ad8b804` (commit „V8 (slot 24.10)") | **pending** | 14:02:06 |
| `42bb78b` (r063: output v7, log crashu ~25 min) | **in_progress** | 13:48:55 |
| `97fe360` (r062: submissions) | completed/success | 13:47:38 |

Zasady operacyjne (ich własne, potwierdzone bolesnym doświadczeniem r057):
- **nie pushować `request.json`, dopóki wisi run** — push kasuje oczekujące runy;
- `gh run view --log` i pobieranie artefaktów są **zablokowane** — jedyny kanał wyników to
  commity do `ops/results/<id>-<op>/SUMMARY.md`;
- jedna dźwignia na submisję, nie prowadzić dwóch torów naraz;
- nie submitować bez `ARC3_SMOKE_OK`.

**Kernel V8 to `duck-original`, więc run-killer z §9 go NIE dotyczy** — ale dotyczy każdej
następnej próby linii `duck-v7`, która dała ich najlepszy wynik (26.25).

---

## 9. Bugi ich patchy (dowody w `PATCH-0004-I-SEARCH.md` i `results/verification_output.txt`)

### 9.1 Run-killer: patch 0003 nie nakłada się po patchu Franzena

`duck-extra-02.patch` ma nagłówek `index 0b69d62..65f1b60`. `0b69d62` to **dokładnie** blob
oryginalnego `solver.py` z bundle r033 (porównałem SHA). Patch oczekuje kontekstu
`from inference.agent.tool_agent import ToolAgent` (jedna linia, L37 oryginału) i
`@@ -258,6 +259,13 @@ class _HarnessGameSession:` (L258 oryginału, klasa na L168).

Patch Franzena zmienia ten import na wielolinijkowy (`_PRIORITY_UNTRIMMED_BASE, ToolAgent,
_priority_gate`) i przesuwa `_HarnessGameSession` z L168 na **L469**. Cell 9 nakłada Franzena
**pierwszego**, a potem `patch_files` z `check=True`:

```
OK   franzen → OK 0001 → OK 0002 → FAIL duck-extra-02: patch does not apply (solver.py:35)
→ CalledProcessError → notebook umiera w cell 9, przed pobraniem 69.85 GB wag
```

Zero zmarnowanego GPU (umiera w ~2 min), ale zero wyniku i zero diagnostyki.

### 9.2 `v7-abandon` jest no-opem z dwóch niezależnych powodów

**Bug A — zły licznik tokenów.** Hook przekazuje
`_analyzer_reported_tokens(self.analyzer) - int(getattr(self, "token_baseline", 0))`.
Ale `token_baseline` to kursor **per krok** — dokumentuje to sam solver.py (L485-489:
*„token_baseline is a cursor: it is dragged forward after every step"*) i robi to w L1249
(`self.token_baseline = current_tokens`). Przy `LOCAL_ANALYZER_MAX_OUTPUT = 12*1024`
pojedynczy krok nigdy nie wygeneruje 60 000 tokenów → `should_abandon` zawsze False.
Poprawny licznik to **`game_token_baseline`** (ten sam, którego używa `token_limit_reached()`).

**Bug B — guard chroni największych marnotrawców.**
`if levels_completed > min_levels(): return False` przy `ARC3_ABANDON_MIN_LEVELS=0` oznacza:
gra z ≥1 ukończonym poziomem nigdy nie zostanie porzucona. W r019 **nie było ani jednej gry
z L=0**, a największe wycieki to tn36 (L=1, 86% tokenów) i ls20 (L=1, 91%). Feature jest
więc wyłączony dla 100% populacji, która cieknie.

Razem: `v7-abandon` = **0 zmian** względem v2/v3, a planowane z niego 31–34 pkt nie ma podstaw.
Testy: `tests/test_arc3_level_budget.py::TestPatch0003Bugs` (oba bugi odtworzone).

### 9.3 Lekarstwo (dostarczone, zweryfikowane)

- `patches/0003b-early-abandon-rebased.patch` — ich 0003, logika 1:1, poprawny kontekst;
- `patches/0004-level-token-cap.patch` — budżet poziomu (wymaga 0003b);
- `patches/0004-standalone-level-token-cap.patch` — **zalecane**, bez zależności od 0003;
- `arc3_level_budget.py` + 16 testów jednostkowych (offline, bez GPU/arcengine/slota).

---

## 10. Pułapki narzędziowe (żeby nikt nie powtarzał moich błędów)

### `git apply --include=<pełna/ścieżka/pliku>` cicho skipuje WSZYSTKO

Git dopasowuje wzorzec `--include` **względem korzenia repozytorium, nie CWD**. Uruchomione
z podkatalogu repo z wzorcem `ARC3-Inference/inference/framework/solver.py` daje
`Skipped patch '...'` dla każdego pliku i **exit code 0** — wygląda na sukces, nic nie robi.
Straciłem na tym dwa przebiegi (fałszywie zielony „OK franzen" + pusty commit).

Ich `--include=ARC3-Inference/*` działa, bo cell 9 odpala apply z `$BUNDLE_DIR/src`, które
korzeniem repo **nie jest** (repo to `src/ARC3-Inference`). Odtwarzając to lokalnie, trzeba
albo zrobić `git init` w `src/`, albo odpalać `git apply` poza jakimkolwiek repo.

### Limit czasu jest NIEWYMUSZALNY z wnętrza pętli, gdy `perform_action` blokuje

lf52: `--sec-cap 300`, a proces mielił **1783 s** (52% CPU) i został zabity ręcznie.
Powód: sprawdzenie `time.monotonic() > sec_cap` wykonuje się **między** węzłami, więc jeśli
pojedyncze `perform_action` nie wraca (gra czeka na animację), pętla nigdy nie dochodzi do
sprawdzenia. To nie jest teoria — wcześniejszy przebieg v1 też nie dokończył lf52, a bp35
przekroczył cap 240 s i zameldował 358.6 s (potem 482.5 s przy capie 300 s).

Reguła dla każdego searcha w harnessie: **budżet czasu musi być egzekwowany Z ZEWNĄTRZ**
(osobny proces / `signal.alarm` / wątek z twardym kill), nie przez porównanie znacznika czasu
w pętli. Dotyczy to też ich `max_runtime_s_per_game=532*60` w komórce 21 — jeśli gra zablokuje
się w `perform_action`, budżet harnessa również nie odpowie w przewidywalnym momencie.
Przepustowość akcji jest przy tym bardzo nierówna: 115/s (sc25) do 568/s (ft09, tn36),
czyli **5×** różnicy między grami — planowanie „N akcji na grę" bez pomiaru konkretnej gry
jest nieuzasadnione.


### `git apply` mówi „corrupt patch", choć patch jest sprawny — brak końcowego newline

Przy wydobywaniu patcha Franzena z komórki `%%writefile /kaggle/harness-changes.patch`
zgubiłem końcowy znak nowej linii: **498 779 B zamiast 498 780 B**. Efekt:

```
error: corrupt patch at line 10086
```

Linia 10086 to ostatnia linia pliku (`"children": children[cid],`). `git apply` wymaga albo
końcowego newline, albo jawnego znacznika jego braku — bez jednego z dwóch traktuje plik jak
ucięty. **Diagnoza po rozmiarze, nie po treści**: `diff` dwóch wersji pokazał wyłącznie ten
jeden znacznik. Reguła przy przepakowywaniu patcha przez notebook:
`text if text.endswith("\n") else text + "\n"`.

Druga pułapka w tym samym miejscu: komórki 5–8 trzymają treść patcha jako literal w
`_P('/kaggle/duck-extra-00.patch').write_text("...")` — **ścieżka jest w APOSTROFACH, treść
w cudzysłowach**. Regex wymagający cudzysłowów po obu stronach cicho pomija duck-extra-00
i duck-extra-01 i wygląda, jakby notebook miał 3 patche zamiast 5. Przyjmuj oba rodzaje
cudzysłowów i sprawdzaj LICZBĘ wydobytych patchy, nie tylko to, że coś się wydobyło.

### Nasz 0004 NIE nakłada się PO 0003b — musi go ZASTĄPIĆ, nie iść za nim

Zmierzone na pristine drzewie ARC3-Inference (dowód: `results/verification_notebook.txt`):

| łańcuch | wynik |
|---|---|
| franzen → 0001 → 0002 → **0003b** → **0004-standalone** | **FAIL** `patch failed: solver.py:46` |
| franzen → 0001 → 0002 → **0004-standalone** | **OK** 4/4, `py_compile` 3/3 OK, testy 16/16 OK |

Oba patche wchodzą w ten sam rejon `solver.py`, więc kontekst hunka się rozjeżdża.
Poprawne wpięcie do ich notebooka: **podmienić TREŚĆ `/kaggle/duck-extra-02.patch`** na
0004-standalone, a NIE dokładać czwartego pliku do `patch_files`. To robi
`tools/make_notebook_patch.py` i tak dokładnie został zweryfikowany: skróty SHA patchy
wydobytych z wygenerowanego notebooka są IDENTYCZNE ze źródłowymi (`harness-changes`
bit-w-bit = oryginał Franzena), `patch_files` bez zmian, a w `patches` nazwa
`0003-early-abandon.patch` → `0004-level-token-cap.patch`.

Skutek uboczny, o którym łatwo zapomnieć: po usunięciu 0003 zmienne `ARC3_ABANDON_TOKENS`
i `ARC3_ABANDON_MIN_LEVELS` są **OSIEROCONE** — modułu `arc3_abandon` nie ma już w drzewie
(sprawdzone: 0 referencji w `solver.py`, 8 referencji `arc3_level_budget`). Generator zeruje
te zmienne celowo, żeby inna gałąź nie wyczytała z `ARC3_VARIANT`, że abandon działa na
60 000 tokenów. W `env` zostają `ARC3_LEVEL_TOKEN_CAP=45000`, `ARC3_LEVEL_RESETS_MAX=1`,
`ARC3_LEVEL_MIN_DONE=0` (kill-switch: cap 0 = zachowanie stockowe).


### `git checkout <commit> -- .` nadpisuje też INDEKS

Potem zwykłe `git checkout .` przywraca z **indeksu** (czyli z tamtego starszego commitu),
nie z HEAD — i `git clean -fd` nie usunie plików, które w HEAD są śledzone. W efekcie
dostałem „patch does not apply" na własnym drzewie testowym. Bezpiecznie: `git reset --hard HEAD`.

### `gh api .../contents/<path>` zwraca pusto dla plików >1 MB

`serve.log` (1.13 MB) trzeba brać przez `git/trees?recursive=1` (SHA) → `git/blobs/<sha>`
z `Accept: application/vnd.github.raw+json`. `raw.githubusercontent.com` i `codeload.github.com`
są zablokowane (SSL_ERROR_SYSCALL / timeout) — dozwolone tylko `github.com` i `api.github.com`.

### `/tmp` i `$HOME/.local` nie przetrwają między turami agenta

Scratch musi być w workspace (`/home/user`), a numpy/pydantic/pillow/arcengine trzeba
reinstalować **w każdej turze**. Straciłem przez to całą analizę z jednej tury
(`/tmp/smk` zniknął) — dlatego ten katalog to `arc3-scratch` pod workspace, a wyniki
są commitowane do repo.

### Lokalna branch bywa cicho resetowana do `ca72e32 Initial commit`

Zdarzyło się **dwa razy** w tej sesji (jest też opisane w ich `STATUS.md`). Skutek: commit
złym rodzicem → push odrzucony (non-fast-forward) → a `git reset --hard FETCH_HEAD`
**kasuje** pliki śledzone w bieżącym HEAD, których nie ma w celu. Procedura, która działa:

```bash
git fetch origin arena/c87f7a48-pokemon
[ "$(git rev-parse HEAD)" = "$(git rev-parse FETCH_HEAD)" ] || {
    cp -a <nowe_pliki> /tmp/backup/       # 1. zabezpiecz NOWE pliki
    git reset --hard FETCH_HEAD           # 2. wyrównaj do origin
    cp -a /tmp/backup/. <docelowo>        # 3. przywróć
}
git add <tylko swoje katalogi> && git commit && git push origin arena/c87f7a48-pokemon
```

Dodatkowo: `git status` pokazuje jako **untracked** pliki, które w `FETCH_HEAD` są śledzone
(bo lokalny HEAD był zresetowany) — `diff -rq` przed `cp -a`, żeby nie nadpisać nowszej pracy
innej sesji starszą kopią z dysku (miałem tak z `pokemon-agent/tools/gauntlet_ffi.py`:
wersja z HEAD była nowsza niż ta z dysku).

---

## 11. Mapa ich repozytorium (kluczowe ścieżki)

Pełna migawka 492 blobów z SHA i rozmiarem: **`results/their_tree_snapshot.tsv`**
(format: `sha<TAB>size<TAB>path`). Najważniejsze:

```
arc-agi-3/kaggle/duck-v7/arc3-duck.ipynb              635 KB, 30 komórek - główna linia (v3 = 26.25)
arc-agi-3/kaggle/duck-v7/variant.json                 wariant v7-abandon (env + lista patchy)
arc-agi-3/kaggle/duck-original/tufa-labs-duck-harness-june-30-milestone-winner.ipynb
                                                      29 KB, 17 komórek - kernel V8, ZERO patchy
arc-agi-3/kaggle/ops/request.json                     kolejka (r065)
arc-agi-3/kaggle/ops/ops.py + .github/workflows/arc3-ops.yml   kanał operacyjny
arc-agi-3/kaggle/ops/results/r019-kernel-output/output/{benchmark.json,serve.log}
                                                      520 KB + 1.13 MB - surowe liczby z §5, §6
arc-agi-3/kaggle/ops/results/r033-recon-bundle/bundle/src/ARC3-Inference/...
                                                      42 pliki, stan PRE-patch (solver.py = blob 0b69d62)
arc-agi-3/kaggle/ops/results/r050-kernel-output/output/{summary.txt,benchmark.json}
arc-agi-3/kaggle/ops/results/r062-submissions/        stan submisyji
arc-agi-3/games/environment_files/<g>/<g>/<g>.py      25 gier (3.9 MB) + metadata.json
arc-agi-3/FINDINGS-2026-10-13.md                      572 linii - ich analiza (krzywa tokenowa BŁĘDNA, §6)
arc-agi-3/kaggle/results/PUBLIC_APPROACHES.md          co robi publiczna czołówka
MY-WORK-STATUS.md, STATUS.md, COMPARISON-V7_0-2026-10-14.md, EXECUTE-TODAY-2026-10-15.md
```

Z `PUBLIC_APPROACHES.md`: sovereign-agent, cprs v22/v23 („Proven 31.93 Base"), m2-top-submission
— wszystkie trzy wymieniają `bfs, beam, replay, cache, precompute, offline`. Pennyroyal SGLang
v2.5.3, BF16 host offload, 128k kontekst, 10 slotów dopasowane do `MAXREQ`, priority scheduling,
action guards. **Czyli czołówka robi dokładnie to, co my dopiero zbudowaliśmy w §2/§3 —
offline'owe przeszukiwanie z replayem — a oni mają to wyłączone.**
