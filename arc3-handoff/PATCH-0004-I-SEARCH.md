# ARC-AGI-3 — patch 0004 + search bez tokenów (stan 24.10.2026, ~16:30 UTC)

Dwie rzeczy, o które prosiłeś („patch + search równolegle"). Wszystko poniżej jest
**zmierzone albo zweryfikowane przez `git apply`** — nie ma tu ekstrapolacji.

Pliki w tym katalogu:

| plik | co to |
|---|---|
| `patches/0003b-early-abandon-rebased.patch` | ich patch 0003, zrebasowany tak, że **faktycznie się nakłada** |
| `patches/0004-level-token-cap.patch` | mój patch 0004 (wymaga 0003b) |
| `patches/0004-standalone-level-token-cap.patch` | **to samo bez zależności od 0003 — zalecane** |
| `arc3_level_budget.py` | czysta logika 0004 (bez harnessa, bez GPU) |
| `tests/test_arc3_level_budget.py` | 16 testów, wszystkie zielone na obu wariantach |
| `results/playbook.json` | sekwencje akcji z searcha, **zweryfikowane replayem** |
| `tools/sweep.py`, `tools/build_playbook.py` | przeszukiwanie 25 gier + budowa playbooka |
| `results/sweep_results.jsonl`, `results/sweep_shallow.log` | surowe wyniki |

---

## 1. PILNE: ich linia `duck-v7` nie może wystartować (run-killer)

**Fakt, nie prognoza.** Cell 9 notebooka `arc-agi-3/kaggle/duck-v7/arc3-duck.ipynb`:

```python
subprocess.run(["git","apply","--include=ARC3-Inference/*","-v","/kaggle/harness-changes.patch"],
               cwd=f"{BUNDLE_DIR}/src", check=True)          # patch Franzena — pierwszy
for _extra_patch in ARC3_VARIANT.get("patch_files", []):     # potem nasze
    subprocess.run([...], cwd=f"{BUNDLE_DIR}/src", check=True)   # check=True!
```

a cell 1 ma:

```python
"patch_files": ["/kaggle/duck-extra-00.patch", "/kaggle/duck-extra-01.patch", "/kaggle/duck-extra-02.patch"]
```

`duck-extra-02.patch` (= ich 0003-early-abandon) ma w nagłówku `index 0b69d62..65f1b60`,
czyli był wygenerowany względem **oryginalnego** `solver.py` z bundle (blob `0b69d62` —
potwierdziłem, że to dokładnie ten plik). Oczekuje kontekstu:

```
 from inference.agent.tool_agent import ToolAgent      <- jedna linia
```
i `@@ -258,6 +259,13 @@ class _HarnessGameSession:`.

Patch Franzena zmienia ten import na wielolinijkowy i przesuwa klasę z L168 na L469.
Więc po nim kontekst nie istnieje. Zmierzone (łańcuch C poniżej):

```
OK   0000-franzen-harness-changes
OK   duck-extra-00
OK   duck-extra-01
FAIL duck-extra-02   error: patch failed: solver.py:35
                     error: solver.py: patch does not apply
```

`check=True` → `CalledProcessError` → **notebook umiera w cell 9, przed pobraniem wag,
przed SGLang, przed jakąkolwiek grą.** Zero zmarnowanego GPU (umiera w ~2 min), ale zero
wyniku i zero diagnostyki — dokładnie ten kształt awarii, który w ich historii wyglądał
jak „v7 padła ~25 min".

**Zakres:** dotyczy linii `duck-v7`. Nie dotyczy kolejki, która wisi teraz —
`request.json` = r065 → `midnight-launch` kernela `petersharps/arc3-duck-original`
(notebook `tufa-labs-duck-harness-june-30-milestone-winner.ipynb`, 17 komórek,
**zero patchy**: ani `patch_files`, ani `harness-changes`, ani `git apply`). V8 pójdzie
więc czystym bundlem Tufy. Ale każda następna próba `duck-v7` (v3 = 26.25, ich najlepszy
wynik) umrze w cell 9, dopóki 0003 nie zostanie zrebasowany albo usunięty z `patch_files`.

**Naprawa — dwie opcje:**
1. `ARC3_VARIANT["patch_files"]` → wyrzucić `/kaggle/duck-extra-02.patch`, dodać
   `/kaggle/duck-extra-03.patch` z zawartością `0004-standalone-level-token-cap.patch`.
   Jedna zmiana, jeden lever, a przy okazji dostają działający budżet poziomu.
2. Jeśli chcą zachować 0003 dosłownie: podmienić zawartość cell 7 na
   `0003b-early-abandon-rebased.patch` (identyczna logika, poprawiony kontekst).

Uwaga: 0004 **nie** nakłada się razem z 0003b na raz bez 0003b (kotwica importu).
Wybierz albo `0003b + 0004`, albo `0004-standalone`. Zweryfikowałem oba warianty.

---

## 2. v7-abandon jest no-opem z **dwóch** niezależnych powodów

Nawet gdyby 0003 się nałożył, nie zadziałałby nigdy. Oba bugi mam przetestowane
(`tests/test_arc3_level_budget.py::TestPatch0003Bugs`):

**Bug A — zły licznik tokenów.** Hook przekazuje
`_analyzer_reported_tokens(self.analyzer) - int(getattr(self, "token_baseline", 0))`.
Ale `token_baseline` to kursor per **krok**, nie per gra — sam solver.py to dokumentuje
(L485-489: *„token_baseline is a cursor: it is dragged forward after every step"*) i robi
to w L1249: `self.token_baseline = current_tokens`. Przy `LOCAL_ANALYZER_MAX_OUTPUT = 12*1024`
(cell 9) pojedynczy krok **nigdy** nie wygeneruje 60 000 tokenów, więc
`should_abandon(...)` zawsze dostaje ≤12k i zwraca False. Poprawny licznik to
`game_token_baseline` — ten sam, którego używa `token_limit_reached()`.

**Bug B — guard chroni dokładnie tych, co marnują.** `if levels_completed > min_levels(): return False`
przy `ARC3_ABANDON_MIN_LEVELS=0` oznacza: gra z ≥1 ukończonym poziomem nigdy nie zostanie
porzucona. Z r019: tn36 miał L=1 i **86%** tokenów na niedokończonym poziomie (score 3.57),
ls20 L=1 i **91%** (score 3.27). W całym r019 nie było ani jednej gry z L=0 — więc guard
wyłącza feature dla 100% populacji, która cieknie.

Wniosek: `v7-abandon` (wariant, na którym planowali 31–34 pkt) to **0 zmian względem v2/v3**,
niezależnie od awarii z punktu 1. Ich oczekiwana krzywa z FINDINGS 15.10 nie ma podstaw.

---

## 3. Patch 0004 — co robi i dlaczego tak

Jeden lever: **budżet tokenów na bieżący poziom**, liczony od postępu **marginalnego**
(tokeny od ostatniego ukończenia poziomu, względem `game_token_baseline`).

Trzy stany (`arc3_level_budget.py`, logika czysta, testowalna bez harnessa):

| decyzja | kiedy | koszt |
|---|---|---|
| `KEEP_GOING` | poziom mieści się w `ARC3_LEVEL_TOKEN_CAP` | — |
| `RESET_LEVEL` | cap przekroczony, zostały wolne resety | **0 tokenów LLM** |
| `ABANDON` | cap przekroczony i resety wyczerpane | zwalnia slot SGLang |

Kluczowy pomysł: `_execute_auto_reset()` **już istnieje** w solver.py (L1228) i woła
`_execute_action(ActionInput(id=GameAction.RESET), generated_tokens=0, automatic=True)`.
A cell 9 ustawia `ONLY_RESET_LEVELS=true`, więc RESET **nie kasuje ukończonych poziomów**.
Czyli zanim wyrzucimy grę, dostajemy darmową drugą hipotezę: model widzi czystą ramkę
i świeżą historię zamiast mielić tę samą teorię przez kolejne 45k tokenów.

Gdzie wchodzi (3 hunki, wszystkie w `solver.py` + 1 nowy plik):
- `L50` import modułu
- `should_stop()` → **czysty** `peek()` (bez mutacji!). To ważne: `should_stop` jest
  przekazywany analyzerowi jako callback (`should_stop=self.should_stop`) i bywa wołany
  wiele razy na turę — mutujący check zjadłby wszystkie resety bez wykonania ani jednego
  RESET-u. Mam na to test (`test_peek_is_pure_under_repeated_calls`).
- pętla `play()` (zaraz po bloku `_is_engine_game_over`) → mutujący `step()` + wykonanie
  RESET-u / break.

Kill-switch: bez `ARC3_LEVEL_TOKEN_CAP` moduł zwraca `KEEP_GOING` zawsze, a hooki są
martwe (`enabled == False`). Zachowanie stockowe co do bajtu. Test:
`test_cap_zero_never_acts`, `test_disabled_session_plays_forever`.

Bezpieczeństwo unpickle: sesja bywa odpickle'owana ze słownikiem sprzed istnienia pola,
więc hooki robią `getattr(self, "_arc3_level_budget", None)` + leniwe utworzenie — tak samo
jak istniejący kod solvra dla `max_generated_tokens_per_game` (jego komentarz wprost
ostrzega, że zwykły dostęp atrybutu rzuciłby `AttributeError` na pierwszej turze każdej gry).

### Rekomendowane env (jedna zmiana na submit)

```
ARC3_LEVEL_TOKEN_CAP   = 45000
ARC3_LEVEL_RESETS_MAX  = 1
ARC3_LEVEL_MIN_DONE    = 0
```

Arytmetyka: realny budżet to ~175k tokenów/grę (755 tok/s × 532 min / 110 gier × 0.80),
przy 841 tok/akcję z r019. Średnio 35% tego idzie w poziom, który nigdy nie pada (~61k).
Cap 45k + 1 reset = maksymalnie 90k na jeden poziom, potem twardy stop: gra przestaje
jeść slot, a `MAXREQ=10` dzieli się między pozostałe. tn36 potrzebował >170k i **nie**
skończył poziomu — więc 90k to i tak hojny próg, a nie agresywne cięcie.

Efekt ma dwie składowe i nie sumuję ich (wasza zasada):
- **bezpośrednia**: jeśli RESET pomoże dokończyć poziom, to +1 poziom. Dla tn36 (7 poziomów,
  ΣW=28) przejście L=1 → L=2 to 3.57 → ~10.7 pkt w tej grze.
- **pośrednia**: odzyskana przepustowość podnosi tempo tokenów u pozostałych gier.

Do zmierzenia smoke'iem (10 gier × 48 min) i porównania z r019: **27.21** średnia,
29.0 sufit z głębokości, 2065 akcji, 1.74M tokenów. Bez `ARC3_SMOKE_OK` nie submitować.

---

## 4. Weryfikacja (do odtworzenia w 3 minuty)

Zbudowałem prawdziwe drzewo: 42 pliki `ARC3-Inference` z bundle r033 (blob SHA `d5289fe`),
potem nakładałem patche **dokładnie komendami z cell 9** (`git apply --include=ARC3-Inference/*`
z katalogu `src`). Ważny szczegół: `--include` z pełną ścieżką pliku **nie działa** —
git dopasowuje wzorzec względem korzenia repo, a notebook odpala apply z `src/`, które
korzeniem repo nie jest (repo to `src/ARC3-Inference`). Dlatego `--include=ARC3-Inference/*`
w cell 9 jest poprawne, a mój pierwszy test z dokładną ścieżką cicho skipował wszystko.

```
ŁAŃCUCH A  franzen → 0001 → 0002 → 0003b → 0004
  OK OK OK OK OK   + py_compile solver.py OK   + hooki na L50/610/616/690/692/697/708
ŁAŃCUCH B  franzen → 0001 → 0002 → 0004          (bez 0003b)
  FAIL solver.py:47  → dlatego istnieje wariant standalone
ŁAŃCUCH B' franzen → 0001 → 0002 → 0004-standalone
  OK OK OK OK  + py_compile OK  + 16/16 testów
ŁAŃCUCH C  franzen → 0001 → 0002 → stary 0003
  FAIL solver.py:35  → dowód run-killera z punktu 1
```

Testy: `python3 tests/test_arc3_level_budget.py` → `Ran 16 tests ... OK`
(na drzewie z 0003b) i `OK (skipped=2)` (na standalone, gdzie `arc3_abandon` nie istnieje —
import jest warunkowy). Zero GPU, zero arcengine, zero slota Kaggle.

---

## 5. Search bez tokenów: co realnie wyszło

Przeszukiwanie offline na `arcengine` (BFS dla gier klawiaturowych, beam + segmentacja
4‑spójna dla klikanych), snapshoty przez `copy.deepcopy`, deduplikacja stanów po
`blake2b(frame)+levels_completed`.

**Dwa przebiegi, scalone po najlepszym wyniku na grę: 7/25 gier, 12 poziomów.**

| parametr | płytki | głęboki |
|---|---|---|
| cap węzłów / grę | 3 000 | 12 000 |
| limit czasu / grę | 200 s | 300 s |
| max poziomów | 4 | 6 |
| szerokość beam / kandydatów click | 60 / 20 | 120 / 28 |
| **gry z ≥1 poziomem** | **6/25** | **7/25** |
| **poziomy razem** | **9** | **12** |
| **wartość LB** | **1.67 pkt** | **2.59 pkt** |

Scalony playbook (kolumna „poziomy" = z którego przebiegu):

| gra | tryb | poziomy | akcje vs baseline | score gry | z |
|---|---|---|---|---|---|
| **tu93** | bfs | **5** (L0–L4) | 18/19, 10/16, 19/34, 17/42, 29/123 | **33.33** | głęboki |
| **vc33** | beam | **2** (L0–L1) | 3/7, 11/18 | **10.71** | głęboki |
| cd82 | beam | 1 | 5/55 | 4.76 | płytki |
| m0r0 | beam | 1 | 15/30 | 4.76 | płytki |
| sp80 | beam | 1 | 28/39 | 4.76 | głęboki |
| ls20 | bfs | 1 | 13/22 | 3.57 | płytki |
| lp85 | beam | 1 | 5/17 | 2.78 | płytki |

Każde rozwiązanie **zweryfikowane replayem na świeżej instancji gry, 2× powtórzone** —
silnik jest deterministyczny, więc playbook da się odtworzyć w harnessie co do akcji.

Formułę score'u zweryfikowałem co do setnej na ich własnych danych z r019:
tn36 L=1 → mój rachunek daje **3.57** (opublikowane 3.57), ls20 L=1 → **3.27** (3.27).
Czyli te liczby są policzone tym samym wzorem, którym liczy Kaggle.

**Wartość playbooka dziś: 2.59 pkt LB** (średnia po 25 grach, bo 110 runów to cykliczne
repliki tych 25 gier). To **podłoga**, nie sufit: te poziomy są zaliczone zanim model wyda
pierwszy token, a LLM startuje potem z poziomu L5 (tu93) zamiast L0 i z całym budżetem.

Trzy wnioski z pomiaru — w tym jeden, który obala moje własne wcześniejsze założenie:

> **1. Głębokość jest wszystkim.** Jeden poziom w 7-poziomowej grze jest wart ~3.5 pkt, bo
> mianownik to ΣW **wszystkich** poziomów. tu93 z 5 poziomami to 33.33 pkt w jednej grze —
> 13× więcej niż gra z jednym poziomem. Cel na 9 dni to ~5 gier z ≥2 poziomami, nie 25 gier
> z jednym.

> **2. Większy budżet POMAGA (poprawka do mojej wcześniejszej tezy).** W przebiegu płytkim
> uznałem, że 4× więcej węzłów nic nie daje — głęboki przebieg to obalił: tu93 4→5 poziomów,
> vc33 1→2, sp80 0→1, czyli +3 poziomy i +2 gry. Uczciwe zastrzeżenie: zmieniało się pięć
> parametrów naraz (węzły, czas, głębokość, beam, kandydaci click), więc nie wiem, który
> zadziałał; i zwrot jest malejący — 4× koszt dał +0.92 pkt LB. Do rozdzielenia osobnym
> przebiegiem, ale kierunek jest jasny: **ciąć budżet było błędem**.

> **3. Gry click-owe są nadal czarne.** tn36, ka59, dc22, ar25, cn04, r11l, s5i5, sc25 = 0
> poziomów mimo 12 000 węzłów. Beam z heurystyką „liczba zmienionych pikseli" prowadzi w
> ślepe uliczki, a kandydatów kliknięcia jest 20–28 na ramkę. To jest właściwe miejsce na
> ich nieużywany port Rusta (`rust/src/grid.rs`, ~121×) do segmentacji obiektów.

**ft09 to osobny przypadek**: search kończy się po 56 węzłach w 0.7 s, bo
`available_actions` jest puste albo jednoelementowe — gra wymaga akcji, której nie wystawia
(`ACTION7`? przytrzymanie? klik w specyficzny piksel?). Do obejrzenia ręcznie: to 1/25
budżetu leżąca na ulicy.

Co z tego wynika na następne kroki searcha (w tej kolejności):
1. **Makro-akcje + iterative widening** dla gier klawiaturowych: baseline to 30–230 akcji,
   a BFS z branchingiem 5 sięga głębokości ~6. Sekwencje długości 2–3 jako jeden ruch
   + deduplikacja stanów powinny wejść na 20–30.
2. **Heurystyka celu dla click-gier** zamiast nowości ramki: postęp w wykrytym regionie
   (HUD/licznik/pasek) + segmentacja obiektów z ich portu Rusta.
3. **ft09** — zdiagnozować brak akcji.
4. **Równoległość**: 25 gier × 300 s na 2 rdzeniach to ~45 min. Na maszynie z 16 rdzeniami
   (albo w offline jobie na Kaggle CPU) ten sam budżet na grę można dać 8× więcej grom,
   albo 8× pogłębić każdą.

### Jak wpiąć playbook w harness

`results/playbook.json` ma dla każdej gry listę `{level, actions, seq[{a,x?,y?}], expected_level_score}`.
Replay to pętla `game.perform_action(ActionInput(id=GameAction.from_id(a), data={"x","y"}))`
zaczynająca od RESET-u — dokładnie to robi `tools/build_playbook.py::replay`, i to przeszło.

- w `duck-v7`: patch dodający odtwarzanie przed pierwszą turą analyzera (ten sam plik
  `framework/`, hook w pętli `play()` przed `self.analyzer.analyze(...)`) — jeśli gra i poziom
  są w playbooku, wykonaj sekwencję i nie wołaj modelu;
- w `duck-original` (kernel V8, bez patchy): cell 12 *„Customization hook"* ma `bm`, `bm.games`,
  `bm.solver`. Tu najprościej monkeypatchować `_HarnessGameSession` (istnieje też w czystym
  bundle, L168) — ale bez patcha da się podpiąć tylko `should_stop`, czyli połowę ABANDON,
  bez darmowego RESET-u. Pełny 0004 wymaga mechanizmu patchy z duck-v7.

---

## 6. Czego nie robić (aktualizacja listy z DIAGNOZY)

- Nie planować na krzywej 200k→41.8 / 300k→45.7 z FINDINGS 15.10 — ich własny pomiar daje
  ~175–219k/grę, czyli 26–27 LB. Teraz dodatkowo wiadomo, że `v7-abandon` (31–34 pkt) to no-op.
- Nie pushować `request.json`, dopóki wisi run (r065 jest `pending` od 14:02, `42bb78b`
  `in_progress` od 13:48).
- Nie sumować sufitów (playbook 1.67 pkt + odzyskane tokeny + MAXREQ↑ to trzy **różne**
  mechanizmy o niepewnej addytywności).
- Nie optymalizować liczby akcji poza playbookiem — różnica 29.0 (sufit z głębokości) vs
  27.21 (pomierzone) to 1.75 pkt za całą efektywność.
- Nie dodawać kosztu decyzyjnego (world model / nudge) — ich historia: v5 23.94 < v2 24.66.
