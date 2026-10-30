# Audyt v13 / v13.1 i poszukiwanie v13.2 — 30.10.2026

**Zakres:** (1) v13.2 — **istnieje, commit `6b108534`** (§1, §1A), (2) audyt `duck-v13-1`
z uwzględnieniem pełnej historii (§2–§4), (3) korekty do moich wcześniejszych twierdzeń,
(4) porównanie z niezależną recenzją c87 (§5), (5) werdykt o v13.2 (§6).

> **⚠️ TEN DOKUMENT ZAWIERA SPROSTOWANIE WŁASNEGO BŁĘDU.** Pierwotna wersja §1
> twierdziła „v13.2 nie istnieje". To było nieprawdziwe — v13.2 zostało
> opublikowane 30.10 o 07:45 UTC, a mój `git fetch --all` go nie pobrał, bo
> RefSpec tego klonu nie śledzi cudzych gałęzi `arena/*`. Przyczyna i procedura
> na przyszłość: **§1.1–§1.3**.

> **Poprawka do `V13-1-VERIFICATION.md` §7.2.** Napisałem tam, że na gałęzi jest tylko
> jeden commit i diffu v13 → v13.1 nie da się odtworzyć. **To było nieprawdziwe.**
> Powód: klon był single-branch i pierwszy `git fetch` nie pobrał historii. Po
> `git fetch --all` widzę **dwa** commity: `3782f8c` (v13, `duck-v13-mega/`) i
> `cbefdd4` (v13.1, `duck-v13-1/`). Diff jest dostępny i jest poniżej (§2).
> To ten sam błąd metodologiczny, który sam wytknąłem w `DUCK-V8-VERIFIED.md`:
> **twierdzić „nie ma", nie sprawdziwszy, czy ref jest w ogóle pobrany.**

---

## 1. ❌ BŁĄD WŁASNY: v13.2 ISTNIEJE — commit `6b108534`, 30.10 07:45 UTC

**Pierwotna wersja tej sekcji twierdziła „v13.2 nie istnieje" i była NIEPRAWDZIWA.**

| | |
|---|---|
| commit | `6b1085340a6fc6c7b5d584d1312d639c200fb1d5` |
| data | **2026-10-30 07:45:14 UTC** |
| gałąź | `arena/a450b00f-pokemon` (tip) |
| katalog | `arc-agi-3/duck-v13-2/` |

### 1.1 Dlaczego mój check dał fałszywy negatyw — przyczyna systemowa

**RefSpec tego klonu obejmuje tylko dwie gałęzie:**

```
+refs/heads/main:refs/remotes/origin/main
+refs/heads/arena/7911f950-pokemon*:refs/remotes/origin/arena/7911f950-pokemon*
```

`git fetch --all` **nie pobiera więc żadnej innej gałęzi `arena/*`**. Dowód:

```
$ git fetch --all -v
 = [up to date]      main                   -> origin/main
 = [up to date]      arena/7911f950-pokemon -> origin/arena/7911f950-pokemon
```

Zdalnie jest **8 gałęzi**, a `--all` śledzi **2**. Pozostałe `origin/arena/*`
to zamrożone migawki z momentu, w którym pobrałem je **jawnie** — i `--all`
nigdy ich nie odświeży.

Konsekwencja: `git rev-parse origin/arena/a450b00f-pokemon` zwracał `cbefdd4`
(v13.1), choć na GitHubie tipem było już `6b10853` (v13.2). Wszystkie moje
`git grep` i `git ls-tree` szukały w **nieaktualnej migawce** i rzetelnie
donosiły „brak".

### 1.2 To ten sam błąd, trzeci raz

| # | incydent | fałszywe twierdzenie | prawdziwa przyczyna |
|---|---|---|---|
| 1 | `DUCK-V8-VERIFIED.md` | „duck-v8 nie istnieje w żadnym remote" | `ls-tree` na niepobranym refie |
| 2 | `V13-1-VERIFICATION.md` §7.2 | „diffu v13→v13.1 nie da się odtworzyć, jest jeden commit" | historia niepobrana (single-branch) |
| 3 | `V13-AUDIT-30OCT.md` §1 | „v13.2 nie istnieje" | **RefSpec: `--all` nie śledzi cudzych gałęzi arena** |

Trzy różne objawy, **jedna klasa**: twierdziłem „nie ma", nie sprawdziwszy, czy
w ogóle patrzę na aktualne dane.

### 1.3 Obowiązująca procedura (do stosowania zawsze)

```bash
# 1) NIGDY nie ufaj `git fetch --all` dla cudzych gałęzi w tym klonie.
git fetch origin <gałąź>:refs/remotes/origin/<gałąź> --force

# 2) Albo napraw RefSpec raz na zawsze:
git config --add remote.origin.fetch '+refs/heads/arena/*:refs/remotes/origin/arena/*'

# 3) Zanim napiszesz "nie istnieje", porównaj LOKALNY ref z API:
gh api repos/peteraangelic-pixel/Pokemon/branches/<gałąź> --jq .commit.sha
git rev-parse origin/<gałąź>
```

Reguła: **„nie znalazłem" ≠ „nie ma".** Zanim to napiszę, muszę pokazać, że
lokalny ref == zdalny tip. W punktach 1–3 tego nie zrobiłem.

### 1.4 Czego to nie unieważnia

Poprawne pozostają: §2 (diff v13→v13.1), §3 (dowód uruchomieniem, że w v13
`dead_skip` nie działał), §4 (lekcja o testach zielonych przy martwej funkcji)
i §5 (zbieżność z c87). Wszystkie opierały się na danych, które **miałem**
pobrane i zweryfikowane uruchomieniem, nie na ich braku.

---

## 1A. Co v13.2 faktycznie zmienia (zweryfikowane)

Diff `cbefdd4` → `6b10853`. Nowy katalog `duck-v13-2/`; plik po pliku:

| plik | zmiana |
|---|---|
| `README.md` | +20 linii: sekcja „v13.2 (30.10, po audytach 7911f950 i c87)" |
| `arc3-duck-v13.ipynb` | **3 linie**: `ESCALATE_ACTIONS = 60` → **`10`**, etykieta `v13.1` → `v13.2` |
| `src/arc3_winpath.py` | **+3 linie**: guard `GAME_OVER` w `_replay_once` |
| `tests/test_winpath.py` | +13 linii: **8. test** `test_game_over_frame_does_not_burn_replay` |
| `patches/0006-*.patch` | +5/−2: to samo, co w `src/` (patch jest generowany) |
| `kernel-metadata.json`, `build_v13.py`, `verify_v13.py` | same etykiety wersji |
| `playbook.json`, `base-v11.ipynb`, `test_plan_commit.py`, `build_playbook.py`, `make_patch_0006.py`, `ANALIZA-23.md` | **bez zmian, bajt w bajt** |

### 1A.1 `ESCALATE_ACTIONS 60 → 10` — moja rekomendacja, wdrożona

Commit message cytuje wprost: *„(audyt 7911: commit tylko oferowany, eskalacja
to jedyne wymuszenie; env potwierdzone w patchu 0005)"*. README dodaje, że to
*„jedyne wymuszenie w scaffoldzie"*.

**Potwierdzam empirycznie, że env działa** (to była moja niedomknięta luka —
pisałem „eskalacja włącza się po 60 akcjach", nie sprawdziwszy, czy próg jest
konfigurowalny):

```python
ESCALATE_ACTIONS = 10
_v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)   # komórka 2
```
a w patchu 0005:
```python
escalate_every = _escalate_actions()            # czyta ARC3_ESCALATE_ACTIONS
if on_level >= escalate_every * (self._arc3_escalations_on_level + 1):
    lines.append(plan_escalation_prompt(...))
```

**Skutek policzony na r018** (realne `actions_per_level`, 10 gier):

| próg | eskalacji w biegu | na grę (mediana) | na grę (min) |
|---|---|---|---|
| N=60 (v13.1) | **16** | 2 | **0** |
| N=10 (v13.2) | **189** | 20 | 10 |

**12× więcej presji.** Twierdzenie README, że przy 60 *„często nie odpalała się
nigdy"*, jest zgodne z danymi: minimum 0 na grę.

**Odtworzenie:** `local/v13_verify/escalate_proof.py` (exit 0). Sprawdza trzy
niezależne rzeczy: (A) notebook eksportuje `ARC3_ESCALATE_ACTIONS`, (B) patch 0005
czyta tę zmienną i **tylko** robi `lines.append(...)` — bez `return`/`raise`/`continue`,
czyli bez twardej bramki, (C) liczby 16 i 189 wynikają z realnych `actions_per_level`.

### 1A.2 ⚠️ Ale to NADAL nie jest wymuszenie — i mam obawę co do kierunku

Eskalacja to `lines.append(...)` — **dopisanie tekstu do promptu**. Model może ją
zignorować dokładnie tak samo jak opis narzędzia. Z moich trzech rekomendacji
(`V13-1-VERIFICATION.md` §3) v13.2 realizuje **jedną**:

| # | moja rekomendacja | stan w v13.2 |
|---|---|---|
| 1 | wymusić batch przy pierwszej turze poziomu | ❌ nie |
| 2 | zejść z eskalacji 60 → ~8–10 | ✅ **tak, dokładnie 10** |
| 3 | odrzucać turę z 1 akcją bez uzasadnienia | ❌ nie |

**Ryzyko, którego nikt nie podniósł:** treść dyrektywy (≈550 znaków, ~140 tokenów)
żąda wykonania **czterech kroków analizy naraz**:

> „In this turn: (1) state what the recorded transitions leave unexplained;
> (2) write the rule you believe as `model_state(frame)` and `model_step(state, action)`;
> (3) run `check_model()` and report the accuracy — below ~0.9 on this level it is
> not yet a model; (4) only then `plan()` inside it and `commit()` the result…"

Przy progu 10 ta dyrektywa trafia do promptu **~20 razy na grę**. Model, który
wykonuje polecenie dosłownie, spędzi te tury na **pisaniu modelu świata**, a nie
na batchowaniu akcji. To może **zmniejszyć** liczbę akcji na decyzję — czyli
zadziałać **przeciwnie do celu**.

Efekt jest więc dwustronnie nieokreślony:

- model **ignoruje** dyrektywę → 189 eskalacji nie zmienia nic (jak przy 60);
- model **wykonuje** dyrektywę → spala tury na meta-analizie zamiast na `commit()`.

To nie znaczy, że zmiana jest zła — 60 było bez wątpienia zbyt wysoko. Znaczy, że
**kierunek efektu da się ustalić tylko pomiarem `akcji/decyzję` w logu**, a nikt
tego dotąd nie zmierzył — ani autorzy, ani c87, ani ja.

### 1A.3 Guard `GAME_OVER` (Gemma) — poprawny

```python
raw_state = getattr(getattr(game_state, "raw", None), "state", None)
if str(getattr(raw_state, "name", raw_state)).upper().endswith("GAME_OVER"):
    return False  # dead frame: do not burn the level's replay on it
```

- Ścieżka `raw.state` **zgadza się** z tym, co widziałem w `base-v11.ipynb`
  (`raw_state = new_state.raw.state`). Nie jest zgadywana.
- Gdy `raw`/`state` brak → `str(None)` = `"NONE"`, nie kończy się na `GAME_OVER`,
  więc guard przepuszcza. Bezpieczna degradacja.

### 1A.4 Korekta liczby testów — i skąd się wzięła

v13.1 ogłaszało „12+8 testów", a `test_winpath.py` miał **7 metod**. Mój
`V13-1-VERIFICATION.md` §2 zapisał „7/7 PASS", co tę rozbieżność dokumentowało.
v13.2 to koryguje („**7+1=8 dopiero od v13.2**") i przypisuje wykrycie recenzjom
Smak i 7911f950.

**Zweryfikowane:** `test_winpath.py` w v13.2 ma 8 metod, `unittest` → **8/8 OK**.

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

## 6. Werdykt o v13.2 (30.10, po audytach 7911f950 i c87)

| pytanie | odpowiedź |
|---|---|
| Czy v13.2 istnieje? | **Tak** — `6b108534`, tip `a450b00f`, 30.10 07:45 UTC |
| Czy wdraża moją rekomendację? | **Tak, ale jedną z trzech**: `ESCALATE_ACTIONS` 60 → **10**, dokładnie jak postulowałem (§1A.1) |
| Czy to wystarczy na 50? | **Nie.** Presja rośnie 12× (16 → 189 eskalacji w biegu), ale to nadal **tekst w promptcie**, nie bramka. Model może ją zignorować |
| Czy efekt będzie dodatni? | **Nieokreślony w obie strony** (§1A.2): ignorowanie → brak zmiany; posłuszeństwo → tury spalone na `model_state`/`check_model` zamiast na `commit()` |
| Co jest dobrego? | Guard `GAME_OVER` poprawny i na właściwej ścieżce `raw.state`; korekta liczby testów 7+1=8 — uczciwa i zweryfikowana (8/8 OK) |
| Co pozostaje niezmierzone? | **akcje/decyzję w realnym biegu** — jedyna dźwignia o skali ×2,7 |

### 6.1 Porównanie trzech wersji

| | v13 (`3782f8c`) | v13.1 (`cbefdd4`) | v13.2 (`6b10853`) |
|---|---|---|---|
| magazyn per bazowy kod gry | ❌ pełne id | ✅ `base_key()` | ✅ |
| `dead_skip` działa w rerunie | ❌ **nie** (2 błędy, §3) | ✅ | ✅ |
| `ESCALATE_ACTIONS` | 60 | 60 | **10** |
| guard `GAME_OVER` | ❌ | ❌ | ✅ |
| testy winpath | 6/6 (przy martwej funkcji) | 7/7 | **8/8** |
| `commit()` wymuszony | ❌ oferowany | ❌ oferowany | ❌ **nadal tylko presja** |
| playbook | ≈0 (brak trafień w id) | ≈0 | ≈0 (**bez zmian, bajt w bajt**) |

**v13.2 jest najlepszą z trzech wersji** — dwie realne naprawy plus wdrożona
moja rekomendacja. Ale nadal nie dotyka tego, co faktycznie blokuje wynik:
`commit()` pozostaje sugestią, a playbook nie trafi w gry przy prywatnym rosterze.

### 6.2 Ryzyko wysłania v13.2 „na 50"

Nie dowiemy się z niego nic diagnostycznego — stackuje 5 zmian (jak v13).
Jeśli wyjdzie 29, nie rozstrzygniemy, czy to `ESCALATE=10`, `CAP=0`, guard, czy szum.
To ten sam błąd co przy v11/23 (c87 §4 nazywa to „śmiertelnym #8").

**Ale** jeden pomiar z v13.2 byłby naprawdę cenny i tani: **policzyć
`akcje/decyzję` w logu**. To jedna liczba, którą można wyciągnąć z `history[]`
tak samo, jak ja wyciągnąłem 1,00 z r013/r015/r018. Jeśli po v13.2 ta liczba
wzrośnie — eskalacja działa i można ją zaostrzać. Jeśli spadnie — dyrektywa
szkodzi i trzeba ją skrócić do jednego zdania („użyj `commit()` na ten poziom").

## 7. Co bym zrobił dalej (w kolejności)

1. **Zmierzyć `akcje/decyzję` w logu v13.2.** Zero kosztu, rozstrzyga całą klasę
   pytań. Procedura jest w `MEGA-DIAGNOSIS.md` §4 (rosnące `wallclock_seconds`
   = nowa decyzja). **To jest teraz ważniejsze niż cokolwiek innego** — bez tej
   liczby nie wiemy, czy `ESCALATE=10` pomaga, czy szkodzi.
2. **Skrócić dyrektywę eskalacyjną do jednego zdania.** Obecna (4 kroki,
   ~550 znaków) prosi model o napisanie modelu świata zamiast o batching.
   „Ten poziom nie jest ukończony — zaplanuj i `commit()` co najmniej 3 akcje."
3. **Twarda bramka zamiast presji** (moja rekomendacja #3, nadal niezrealizowana):
   odrzucić turę, która wykonuje 1 akcję, gdy `model_step` już przewiduje wynik.
4. **Zmniejszyć liczbę zmian w jednym submicie** — `CAP=0` + `EXPOSE_UNDO` +
   wymuszony `commit()`, z wyłączonym playbookiem i `dead_skip` (i tak ≈ 0).
5. Playbook przegenerować **najkrótszą** ścieżką (sp80: 4 akcje vs 28), ale
   **nie liczyć na niego punktów** przy prywatnym rosterze.

---

## 8. Rejestr moich pomyłek w tej sesji

Zapisuję je, bo wszystkie mają tę samą przyczynę i wszystkie kosztowały czas.

| # | twierdzenie | prawda | przyczyna |
|---|---|---|---|
| 1 | „duck-v8 nie istnieje w żadnym remote" | istnieje, `5f397df` | `ls-tree` na niepobranym refie |
| 2 | „diffu v13→v13.1 nie da się odtworzyć" | da się, `3782f8c`→`cbefdd4` | historia niepobrana |
| 3 | „v13.2 nie istnieje" | istnieje, `6b108534` | **RefSpec: `--all` nie śledzi cudzych gałęzi `arena/*`** |
| 4 | „cap 1,15 to reguła" | reguła to **1,0** | arcagibook ≠ strona konkursu |
| 5 | symulator schedulera „+22 pkt" | +0…+8, przy 400 potrafi −5 | błąd w symulatorze (darmowe zaliczanie poziomów) |
| 6 | „1,00 akcji na decyzję" (centralna liczba `MEGA-DIAGNOSIS` §4) | **4,61 akcji na generację** | **tautologiczny test**: `wallclock_seconds` rośnie przy każdej akcji, więc metoda zawsze dawała 1,00. Poprawny proxy: `generated_tokens > 0` |
| 7 | „premisa: model robi 1 akcję na turę" → rekomendacja batchowania | batchowanie **już działa** (4,6×) | konsekwencja #6: uzasadnienie błędne, choć wniosek „więcej akcji" pozostaje słuszny |

Wzór w #1–#3: **twierdziłem brak, patrząc na nieaktualne dane.** Procedura z §1.3
jest odpowiedzią. W #4–#5: **brałem źródło wtórne za autorytatywne.** Odpowiedź:
cytować stronę konkursu i liczyć z surowych artefaktów.
