# Audyt v13 / v13.1 i poszukiwanie v13.2 — 30.10.2026

**Zakres:** (1) czy istnieje v13.2, (2) audyt `duck-v13-1` z uwzględnieniem pełnej historii,
(3) korekty do moich wcześniejszych twierdzeń, (4) porównanie z niezależną recenzją c87.

> **Poprawka do `V13-1-VERIFICATION.md` §7.2.** Napisałem tam, że na gałęzi jest tylko
> jeden commit i diffu v13 → v13.1 nie da się odtworzyć. **To było nieprawdziwe.**
> Powód: klon był single-branch i pierwszy `git fetch` nie pobrał historii. Po
> `git fetch --all` widzę **dwa** commity: `3782f8c` (v13, `duck-v13-mega/`) i
> `cbefdd4` (v13.1, `duck-v13-1/`). Diff jest dostępny i jest poniżej (§2).
> To ten sam błąd metodologiczny, który sam wytknąłem w `DUCK-V8-VERIFIED.md`:
> **twierdzić „nie ma", nie sprawdziwszy, czy ref jest w ogóle pobrany.**

---

## 1. v13.2 nie istnieje

Sprawdzone, nie założone:

| gdzie szukałem | wynik |
|---|---|
| `git grep -il "v13.2\|v13-2\|v132"` na **wszystkich** gałęziach zdalnych | brak trafień |
| `git log --all --grep="v13.2"` | brak trafień |
| katalogi `arc-agi-3/duck-v13*` na `a450b00f` | tylko `duck-v13-1` i `duck-v13-mega` |
| najnowszy commit `a450b00f` | `cbefdd4` = v13.1, brak nowszego |

Dwa commity z „v13" w treści (`3d094e7`, `c78439e`) należą do **innego projektu** na
gałęzi `8560a56a` (v14, gust, retrieval — nie ARC-AGI-3).

**Wniosek: v13.2 nie zostało opublikowane na żadnej gałęzi.** Jeśli miało powstać,
to nie powstało. Nie będę zgadywał, co miało zawierać.

---

## 2. Co realnie zmieniło v13 → v13.1

Diff `3782f8c` → `cbefdd4`. Zmienione 8 z 14 plików, ale **w kodzie tylko dwie rzeczy**:

### 2.1 `_sanitize(game_id)` → `base_key(game_id)` przy ścieżce magazynu

```python
# v13
self.path = winpath_dir() / (_sanitize(game_id) + ".json")
# v13.1
self.path = winpath_dir() / (base_key(game_id) + ".json")
```

`base_key("ls20-9607627b")` → `"ls20"`, więc **wpisy tej samej gry dzielą jeden magazyn**
zamiast zakładać osobny plik na każdy sufiks hasha.

### 2.2 `dead_skip` bez bramki `pass_index`

```python
# v13
if int(getattr(session, "pass_index", 0)) < _env_int("ARC3_DEAD_MIN_PASS", 4):
    return False
# v13.1: bramka usunięta, decydują liczniki magazynu
```

### 2.3 Reszta to dokumentacja i metadane

`ANALIZA-23.md`, `README.md`, `kernel-metadata.json` (id/title), `tools/build_v13.py`,
`tools/verify_v13.py`, osadzony patch w notebooku + etykieta `v13 profile` → `v13.1 profile`.

**Bez zmian (bajt w bajt):** `playbook.json`, `src/base-v11.ipynb`, `tests/test_plan_commit.py`,
`tools/build_playbook.py`, `tools/make_patch_0006.py`.

Czyli **v13.1 nie dotknął ani playbooka, ani bazy, ani patcha 0005** — tylko magazyn
winpath i dead-skip. To ważne: cała dyskusja „czy playbook jest coś wart" dotyczy
obu wersji identycznie.

---

## 3. Dowód empiryczny: w v13 obie dźwignie były martwe, i to nie z jednego powodu

Uruchomiłem **prawdziwy kod v13** i **prawdziwy kod v13.1** na tym samym scenariuszu:
gra, która przez 10 wpisów nie ukończyła ani jednego poziomu.

```
v13   pass_index=0: dead_skip=False
v13   pass_index=1: dead_skip=False
v13   pass_index=4: dead_skip=False     ← nawet przy 4!
v13.1 pass_index=0: dead_skip=True
v13.1 pass_index=1: dead_skip=True
v13.1 pass_index=4: dead_skip=True
```

**v13 zwraca `False` nawet przy `pass_index=4`.** Gdyby to była tylko bramka
`pass_index`, przy 4 powinno zadziałać. Nie zadziałało, bo **drugi błąd przykrywa pierwszy**:
magazyn kluczowany pełnym id (`dead00-abcdef12.json`) nie widzi danych zapisanych
pod `dead00.json`, więc `passes_completed` czyta się jako 0.

Dwa niezależne błędy, każdy wystarczający, żeby wykoleić funkcję:

| # | błąd v13 | skutek w rerunie |
|---|---|---|
| 1 | `pass_index < 4` | `n_passes=1` → `pass_index` zawsze 0 → **nigdy nie przechodzi** |
| 2 | magazyn per pełne id | `passes_completed` nie kumuluje się między wpisami → **zawsze 0** |

v13.1 usuwa oba. To jest realna, zmierzona poprawka — nie kosmetyka.

**Odtworzenie:** `local/v13_verify/dead_skip_proof.py` (exit 0 = teza potwierdzona).
Skrypt ładuje oba `arc3_winpath.py` jako osobne moduły i sprawdza `pass_index`
∈ {0, 1, 4} na obu. Instrukcja pobrania drzew w nagłówku pliku.

---

## 4. Najważniejszy wniosek metodologiczny: testy były zielone, gdy funkcja była martwa

```
v13   tests/test_winpath.py -> 6/6 OK     (feature dead)
v13.1 tests/test_winpath.py -> 7/7 OK     (feature works)
```

Czemu v13 przechodziło? Bo **test kodował założenie autora, nie warunki płatnego biegu**:

```python
# v13, test_dead_skip_thresholds
late  = FakeSession(game_id="dead00",          pass_index=5)
early = FakeSession(game_id="dead00",          pass_index=2)
```

- `pass_index=5` — w rerunie (`n_passes=1`) **nieosiągalne**;
- `game_id` bez sufiksu — w rosterze **nieosiągalne** (id mają sufiksy hashy).

v13.1 zmienił test na warunki rzeczywiste:

```python
repeat = FakeSession(game_id="dead00-abcdef12", pass_index=0)   # dokładnie jak w rerunie
fresh  = FakeSession(game_id="dead11",          pass_index=0)
```

**To jest lekcja, którą trzeba zastosować do całej naszej roboty, w tym do mojej:**
test, który przechodzi, dowodzi tylko tego, że kod zgadza się z *założeniami testu*.
Jeśli założenia są o smoke'ie, a nie o rerunie — 6/6 zielonych nic nie znaczy.

Zastosowanie do moich plików: `local/test_scheduler.py` pinuje liczby wyliczone
z `r018` (prawdziwy artefakt), a nie z wyobrażenia — to jest właściwa strona tej
granicy. Ale nadal **nie mierzy zachowania w rerunie**, tylko odtwarza arytmetykę.

---

## 5. Zbieżność z niezależną recenzją c87 (`arena/c87f7a48-pokemon`)

Przeczytałem `arc3-handoff/OCENA-V13-MEGA.md` (307 linii) i korektę `a5432da`.

### 5.1 Gdzie się zgadzamy — niezależnie

| teza | ja | c87 |
|---|---|---|
| `n_passes=1` w `TRUE_SUBMISSION` (komórka 25) | tak, `EVAL-BUDGET-MODEL.md` §1 | tak, §2.1 + potwierdzenie z `benchmark.json` r085/r093 |
| gówna dźwignia v13 (replay między passami) jest martwa w rerunie | tak, `V13-1-VERIFICATION.md` §3 (z innego powodu: `commit()` opcjonalny) | tak, §2 (z powodu `n_passes=1`) |
| **playbook jest wart mało albo zero** | +0,62 przy 110 grach, **0 jeśli brak trafień** | **„ograniczona strata, bliski zera zysk"** |
| `commit()`/`PLAN_COMMIT` niezmierzone na Kaggle | tak | tak, tabela §1 pkt 1 |
| `CAP=0` zgodne z pomiarem (26,78 < 27,21 < 29,02) | nie weryfikowałem | tak, zgodne z ich rekomendacją |

**Dwie sesje, różne drogi, ten sam wniosek o martwej dźwigni.** To najsilniejsze
potwierdzenie, jakie mamy.

### 5.2 Gdzie c87 ma lepszy dowód niż ja

**Playbook: „no repeated game IDs".** c87 cytuje docstring `taaf/competition_arcade.py`
(„one scorecard, hidden baselines, and **no repeated game IDs**") oraz cudzy pomiar
held-out: **0/113 poziomów** na 15 grach odstawionych vs 7/70 na dostrajanych.

**To obniża moją własną estymatę.** W `V13-1-VERIFICATION.md` §5 podałem
„+0,62 pkt przy 110 grach, jeśli te 9 gier jest w zbiorze". Przy dowodach c87
prawdopodobieństwo trafienia jest bliskie zeru, więc **realna wartość playbooka
to ~0, nie +0,62**. Poprawiam to tutaj i nie będę już podawał +0,62 bez tego zastrzeżenia.

*(Uczciwie: nie mogłem zweryfikować ani docstringu `taaf`, ani pomiaru held-out —
brak źródeł harnessu w repo. To dowód c87, nie mój. Oznaczam jako niezweryfikowany.)*

### 5.3 Gdzie **nie** zgadzam się z c87 — mechanizm, nie wniosek

c87 pisze, że replay „RHAE **NIE** poprawia, oszczędność jest tylko w tokenach".

**To nieścisłe.** Replay nie poprawia RHAE, jeśli odtwarza tę samą ścieżkę, którą
agent i tak by przeszedł. Ale playbook odtwarza ścieżkę **krótszą** niż eksploracja LLM:
m0r0 poziom 1 to 15 akcji zapisanych vs 33 akcje, które zużyliśmy w r018. Mniej akcji
= wyższe `(baseline/akcje)²`. **Więc kanał playbooka RHAE poprawia.**

Wniosek c87 (playbook ≈ 0) jest jednak słuszny — tylko z innego powodu: **gra nie
zostanie dopasowana**, więc krótsza ścieżka nigdy nie zostanie użyta.
Zgadzam się z werdyktem, poprawiam uzasadnienie.

### 5.4 Zarzut c87, który uważam za najmocniejszy: 5 zmian naraz = brak interpretowalności

v13.1 stackuje `PLAN_COMMIT=1` + `CAP=0` + patch 0006 + playbook + `DEAD_SKIP=1`.
Przy szumie ±3 pkt **wynik nie będzie diagnostyczny**: 29 pkt nie powie, czy to
`CAP=0`, czy `commit()`, czy szum.

To dokładnie ten sam błąd, przez który 23 do dziś nie jest w 100% zdiagnozowane.
**I to jest argument przeciw wysyłaniu v13.1 „na 50"** — nie dowiemy się z niego nic.

### 5.5 Co c87 zamknął, a ja bym nie zamknął

`SERVER_STARTUP_TIMEOUT` (12 min) **nie przerywa biegu** — tylko przekazuje do
retry/warmup; łączny budżet ~27 min vs ładowanie 25–30 min = **wąski margines,
nie awaria**. c87 sam to skorygował w `a5432da` jako „siódmą korektę, pierwszą,
która osłabia moją rekomendację". Notuję jako zamknięte.

---

## 6. Zaktualizowany werdykt o v13.1

| pytanie | odpowiedź |
|---|---|
| Czy v13.1 naprawia realne błędy v13? | **Tak, dwa niezależne, dowiedzione uruchomieniem** (§3) |
| Czy v13.1 da 50? | **Nie.** Playbook ≈ 0 (brak trafień w id), `commit()` opcjonalne, `n_passes=1` |
| Czy v13.1 jest lepszy od v13? | **Tak, i to nie jest kosmetyka** — w v13 dead-skip i pamięć między wpisami nie działały wcale |
| Czy warto go wysłać? | **Jako pomiar kontrolny — nie jako kandydata na 50.** I tylko z wyłączonymi kill-switchami, żeby wynik dało się zinterpretować (§5.4) |
| Czego nikt nie zmierzył | czy `commit()` realnie podnosi akcje na decyzję — **to jedyna dźwignia o skali, i stoi niezmierzona** |

---

## 7. Co bym zrobił dalej (w kolejności)

1. **Zmienić `commit()` z „oferowane" na „wymuszone"** — inaczej lewar o skali ×2,7
   nigdy nie zagra. Zmiana w `tool_agent.py` + zejście z eskalacji 60 → ~8.
2. **Zmniejszyć liczbę zmian w jednym submicie** — zostawić `CAP=0` + `EXPOSE_UNDO` +
   `commit()` wymuszony, wyłączyć playbook i dead-skip (i tak ≈ 0).
3. **Dodać log `v13 winpath: level=… match=…`** — bez niego nie wiemy, czy replay
   się w ogóle uruchomił. Jedna linia, rozstrzyga całą klasę cichych awarii.
4. Playbook przegenerować **najkrótszą** ścieżką spośród wszystkich źródeł
   (sp80: 4 akcje vs 28), ale **nie liczyć na niego punktów** przy rosterze prywatnym.
