# Weryfikacja duck-v13.1 — co sprawdziłem i co z tego wynika

**Źródło:** `arc-agi-3/duck-v13-1/` na gałęzi `arena/a450b00f-pokemon`, commit `cbefdd4`
("korekty po 3 recenzjach"). Sprawdzone 2026-10-29 na moim sandboxie.

> Uwaga o metodzie: **nie mam GPU ani bundla Franzena**, więc nie mogłem odtworzyć
> 12/12 testów w oryginalnym środowisku ani zmierzyć żadnego biegu. Poniżej
> rozdzielam to, co **zweryfikowałem wykonaniem kodu**, od tego, co jest
> **wnioskiem z lektury** i od tego, czego **nie da się sprawdzić offline**.

---

## 1. Wynik krótko

**v13.1 jest technicznie sprawny. Ma jedną wadę projektową, która decyduje o tym,
czy da 28, czy 50: `commit(plan)` jest tylko *oferowane* modelowi, a nie wymuszane.**

Playbook jest wart **+2,3 pkt na naszych 10 grach** i **~+0,6 pkt na rosterze
110 gier**, jeśli te gry w nim są (a nie wiemy). To potwierdza własne „~2,9" z
README — i jednocześnie wyklucza 50 z samej tej dźwigni.

---

## 2. Co zweryfikowałem uruchomieniem kodu

| # | sprawdzenie | wynik |
|---|---|---|
| 1 | `tests/test_winpath.py` (7 testów) | **7/7 PASS** — po podstawieniu wiernego stubu `arcengine`; bez stubu 4 błędy to wyłącznie `ModuleNotFoundError`, nie błędy logiki |
| 2 | `tests/test_plan_commit.py` (12 testów) | **9/12 PASS** na module wyciągniętym z patcha 0005; 3 wymagają `inference.agent.python_tool_sandbox` z bundla — nie do odtworzenia offline |
| 3 | `playbook.json` — spójność | 9 gier, 14 poziomów, 184 akcje. **Każdy** wpis ma `init` + `hashes`, `len(actions)==len(hashes)`, brak powtórzonych `init` w obrębie gry |
| 4 | Klucze poziomów 0-based? | **Tak, spójne.** `_replay_once` używa `level = levels_completed`, playbook ma klucze `"0"`,`"1"`,… — zgadza się |
| 5 | `grid_key` w `build_playbook.py` vs `arc3_winpath.py` | **Identyczne**: `sha256(repr(tuple(tuple(int(c)…))).encode())[:16]`, oba biorą ostatnią klatkę stosu animacji. Playbook nie odpadnie po cichu z tego powodu |
| 6 | Scalanie playbooka do magazynu gry | **6/6 OK** dla identyfikatorów z rosteru (`cd82-2fe56bfb`, `ls20-9607627b`, …) — dopasowanie po bazowym kodzie działa |
| 7 | Przełączniki faktycznie włączone | `PLAN_COMMIT="1"`, `ARC3_WINPATH="1"`, `ARC3_DEAD_SKIP="1"`, `ARC3_LEVEL_TOKEN_CAP="0"` — i **`os.environ.update(_variant_env)` w komórce 13 naprawdę je eksportuje**. Komórka 2 drukuje `v13.1 profile=plan plan_commit=1` |
| 8 | Haki w `solver.py` (patch 0006) | Obecne: `begin_session`, `maybe_replay → continue`, `dead_skip → break`, `record_action` po każdej akcji |
| 9 | `previous_grid` istnieje w bazie? | **Tak** — `previous_grid = _grid_from_state(self.game.current_state)` w `_HarnessGameSession._execute_action`. Czyli **nie ma `NameError`** połykanego przez `try/except` |
| 10 | Krzyżowa kontrola ścieżek z moim niezależnym solverem | **cd82: identyczne** (5 akcji), **lp85: identyczne** (5 akcji). To dwa niezależne źródła tej samej ścieżki — dobra wiadomość |

### Dwie rozbieżności z moimi rozwiązaniami (nie błędy, ale warte uwagi)

| gra | moje | v13.1 playbook |
|---|---|---|
| **vc33** | `ACTION6(61,33)` ×3 | `ACTION6(60,32)` ×3 |
| **sp80** | 4 akcje (`A4,A4,A4,A5`) | **28 akcji** |

vc33: różnica 1 piksela — obie ścieżki mogą działać lub tylko jedna; **nie rozstrzygnę
bez silnika**. sp80: moja ścieżka jest **7× krótsza**. Playbook nie jest
najkrótszy, a przy kwadratowej karze RHAE różnica 28 vs 4 akcje na jednym poziomie
to realna strata. **Playbook warto przegenerować, biorąc najkrótszą ścieżkę spośród
wszystkich źródeł, nie pierwszą znalezioną.**

---

## 3. Wada projektowa, która decyduje o wyniku

`commit(plan)` z patcha 0005 wykonuje **do 40 akcji na jedną decyzję** — czyli
dokładnie tę dźwignię, którą niezależnie wyliczyłem w `MEGA-DIAGNOSIS.md` §4
(dziś: 1,00 akcji na decyzję, sufit ~19–31 pkt; przy 2 akcjach/decyzję sufit 51,3).

Ale w `tool_agent.py` patch **tylko dopisuje narzędzie do opisu**:

```python
_PYTHON_TOOL_DESCRIPTION += (" Also available: `commit(plan)` plays a list of actions …")
prompt += PLAN_COMMIT_TOOL_ADDENDUM
```

**Nie ma żadnego wymuszenia.** Model nadal może — i prawdopodobnie będzie —
wykonywać jedną akcję na turę, bo tak był trenowany i tak wygląda dotychczasowa
pętla. Eskalacja włącza się dopiero po `ESCALATE_ACTIONS = 60` akcjach na
nieukończonym poziomie, czyli **po 60 zmarnowanych decyzjach**.

To tłumaczy, dlaczego warianty „plan" wcześniej nie dawały wyraźnego zysku: lewar
jest w kodzie, ale nie w zachowaniu modelu. Dopóki `commit()` jest opcjonalne,
v13.1 gra jak v11 z dodatkowym playbookiem — czyli ~28–30, nie 50.

**Co by to naprawiło** (najtańsza zmiana o największym efekcie):

1. **Wymusić batch przy pierwszej turze poziomu** — jeśli model zna ścieżkę, musi
   iść przez `commit()`, nie pojedynczymi akcjami.
2. **Zejść z `ESCALATE_ACTIONS` z 60 na ~8–10.** 60 akcji to przy naszej
   zmierzonej wydajności niemal cały budżet poziomu.
3. **Odrzucać turę, która wykonuje 1 akcję bez uzasadnienia** (np. gdy
   `model_step` już przewiduje wynik) — twarda bramka, nie sugestia w promptcie.

---

## 4. Ryzyko cichej awarii (do jednej linii logu)

Cała integracja jest w `try/except Exception: pass`. Jeśli `init` nie zgodzi się
z klatką startową, `_replay_once` robi `state.broken.add(level)` i **nigdy nie
zaloguje, że replay nie zadziałał**. Feature staje się no-opem bez śladu.

Dwa konkretne powody, dla których `init` może się nie zgodzić, a których **nie
dało się rozstrzygnąć offline**, bo `_grid_from_state` jest w `base-v11.ipynb`
ucięte przez nagłówek hunka:

- **repr numpy vs int.** Rekordy z biegu biorą `previous_grid` z bazy
  (`_grid_from_state`), a replay porównuje z `_grid_of` (koercja `int(c)`).
  Jeśli baza nie koercuje, `repr()` różni się (`np.uint8(3)` vs `3`) i **kanał
  uczenia się nowych poziomów jest martwy** — działałby tylko playbook offline.
- **która klatka stosu animacji.** Baza bierze `state.raw.frame` przez
  `normalize_frames`, replay bierze `state.frame.data` i peeluje do ostatniej.
  Przy animacjach może to być inna klatka.

**Zalecenie:** dopisać jedną linię w `record_action` i jedną w `_replay_once`:

```
print(f"v13 winpath: level={level} init={init} cur={cur} match={init==cur}", flush=True)
```

Bez tego nie wiemy po biegu, czy replay w ogóle się uruchomił. To jest dokładnie
ta klasa błędu, która dała 23: feature był w kodzie, ale nie zadziałał, i nikt
tego nie zobaczył.

---

## 5. Ile to realnie jest warte

Playbook sam, efektywność 100%, na znanych rosterach:

| roster | gier pokrytych | oczekiwany zysk |
|---|---|---|
| nasze 10 gier (r018) | 3 / 10 | **+2,26 pkt** |
| 25 gier publicznych | 9 / 25 | **+2,71 pkt** |
| **110 gier (ewaluacja)** | 9 / 110 | **+0,62 pkt** |
| 110 gier, jeśli tych 9 nie ma | 0 / 110 | **0,00 pkt** |

Na naszych 10 grach playbook daje: cn04 +4,8%, ls20 +3,6%, m0r0 +14,3% —
reszta gier bez zmian.

**⚠️ KOREKTA 30.10 — realna wartość to raczej 0, nie +0,62.** Te liczby zakładają,
że gry z playbooka **trafią** w roster ewaluacji. Niezależna recenzja c87
(`arena/c87f7a48-pokemon`, `arc3-handoff/OCENA-V13-MEGA.md` §3) przytacza docstring
`taaf/competition_arcade.py`: „one scorecard, hidden baselines, and **no repeated
game IDs**", oraz cudzy pomiar held-out: **0/113 poziomów** na grach odstawionych.
Jeśli to prawda, playbook nie trafi w żadną grę i jego wartość to **0,00**.
Nie zweryfikowałem tego samodzielnie (brak źródeł harnessu w repo) — oznaczam
jako dowód c87. Szczegóły: `V13-AUDIT-30OCT.md` §5.2.

**To jest podłoga, nie sufit** — dochodzi jeszcze dead-skip i replay poziomów
nauczonych przez LLM w trakcie biegu. Ale podłoga jest mała i **rozcieńcza się
razem z rosterem**: 9 gier na 110 to 8% populacji.

---

## 6. Werdykt

| pytanie | odpowiedź |
|---|---|
| Czy v13.1 jest zepsuty? | **Nie.** 7/7 testów winpath, 9/12 plan-commit offline, playbook spójny, hashe zgodne, przełączniki włączone i eksportowane |
| Czy da 50? | **Nie z tej dźwigni.** Playbook to +0,6…+2,7. Reszta zależy od `commit()`, które jest opcjonalne |
| Czy README kłamie? | **Nie.** Sam podaje 28–38 i mówi wprost, że 45–55 wymaga „wszystkiego naraz". To uczciwe |
| Największe ryzyko | Cicha awaria replayu — zero logów, zero sygnału |
| Największa szansa | Wymusić `commit()` i zejść z eskalacji 60 → ~8 |

**Rekomendacja:** nie wysyłać v13.1 w obecnej postaci jako „wersji na 50" — jest
warta mniej więcej tyle, ile poprzednia. Warto najpierw zrobić dwie rzeczy, obie
tanie: (a) wymusić batchowanie w `commit()`, (b) dodać logi do winpath. To zmienia
v13.1 z „+0,6 pkt" na wersję, która **mierzy** swoją główną dźwignię.

Jeśli mimo wszystko wysyłać teraz — to jako pomiar kontrolny, nie jako kandydata
na 50.

---

## 7. Uzupełnienie: co jest w `duck-v13-1/` a czego nie sprawdziłem wyżej

> Ta sekcja dopisana 30.10, po pytaniu „czy to wszystko jest zacommitowane".

### 7.1 `ANALIZA-23.md` — diagnoza z tamtej gałęzi

W katalogu `duck-v13-1/` leży `ANALIZA-23.md` (28.10) — niezależna diagnoza tego
samego wyniku 23, którego dotyczy mój `MEGA-DIAGNOSIS.md`. Jej tezy, w kolejności
prawdopodobieństwa wg autora:

| # | teza | zgodność z moją analizą |
|---|---|---|
| 1 | **Rozcieńczenie rosteru**: smoke 10 gier × 48 min nie jest estymatorem pełnego rosteru, bo budżet na grę jest dzielony przez wszystkie gry | **Rozszerzam to w `EVAL-BUDGET-MODEL.md` §3** — i dochodzę do odwrotnego wniosku: przy rosterze ~110 gier budżet na grę **wychodzi ~49 min, czyli tyle samo co smoke**. Dlatego realny LB ≈ smoke, i dlatego smoke jednak jest estymatorem |
| 2 | Wysłano wariant z `PLAN_COMMIT="0"` (kontrola c45fix z capem 45k), a nie „plan" | Zgodne z moim ustaleniem, że `commit()` i tak jest tylko oferowany — więc nawet `PLAN_COMMIT=1` grałby jak kontrola |
| 3 | Cap 45k sam w sobie kosztuje (26,78 < 27,21 < 29,02) | Nie weryfikowałem; pomiar między-buildowy, autor sam go nazywa słabym |
| 4 | Zero pamięci między wpisami (`n_passes=1`) — **korekta 30.10** | Potwierdzam w kodzie: komórka 25 ustawia `bm.n_passes = 1` pod `TRUE_SUBMISSION` |
| 5 | Wariancja ±2–3 pkt to norma | **Zgodne z moim pomiarem**: sd między runami 2,47; pojedyncza gra skacze o 11,7 pkt |

Punkt 5 zgadza się u nas niezależnie (ja liczyłem z `benchmark.json`, oni z historii
runów). Punkt 1 to jedyne miejsce, gdzie się różnimy — i mam na to dowód pośredni,
opisany w `EVAL-BUDGET-MODEL.md` §3.

### 7.2 v13 vs v13.1 — ✅ SPROSTOWANIE (30.10)

**Pierwotna wersja tej sekcji była nieprawdziwa.** Napisałem, że na gałęzi jest tylko
jeden commit i diffu nie da się odtworzyć. Przyczyna błędu: klon był single-branch,
a pierwszy `git fetch` nie pobrał historii. Po `git fetch --all` widzę **dwa** commity:

| commit | zawartość |
|---|---|
| `3782f8c` | **v13** → katalog `arc-agi-3/duck-v13-mega/` |
| `cbefdd4` | **v13.1** → katalog `arc-agi-3/duck-v13-1/` |

Diff jest dostępny, policzony i opisany w **`V13-AUDIT-30OCT.md` §2**. W skrócie:
w kodzie zmieniły się **dwie rzeczy** (`base_key()` zamiast `_sanitize()` przy ścieżce
magazynu; usunięta bramka `pass_index < 4` w `dead_skip()`), reszta to dokumentacja
i metadane. `playbook.json`, `base-v11.ipynb`, `test_plan_commit.py`,
`build_playbook.py` i `make_patch_0006.py` są **bajt w bajt identyczne**.

Obie zmiany naprawiają realne, **dowiedzione uruchomieniem** błędy v13 — patrz
`V13-AUDIT-30OCT.md` §3.

Z README v13.1 wynikało, że korekty dotyczyły trzech rzeczy (teraz **potwierdzone diffem**):

1. magazyn winpath kluczowany bazowym kodem gry (pamięć między wpisami rosteru),
2. dead-skip oparty o liczniki magazynu zamiast `pass_index` (bo przy `n_passes=1`
   `pass_index` był martwy),
3. korekta `ANALIZA-23.md` pkt 4 i oczekiwań w README.

Wszystkie trzy są w v13.1 **i wszystkie trzy potwierdziłem diffem jako nieobecne w v13**.
Punkt 1 i 2 są w kodzie (`base_key`, brak bramki `pass_index`); punkt 3 to
`ANALIZA-23.md` pkt 4. Nie muszę już zgadywać — mam oba drzewa.

### 7.3 Czego nadal nie wiem

- Czy `init`-hashe playbooka zgadzają się z klatkami prawdziwego silnika
  (wymaga uruchomienia gry — patrz §4).
- Czy vc33 wymaga `(61,33)` czy `(60,32)` — różnica 1 piksela, nierozstrzygnięta.
- Czy moja 4-akcyjna ścieżka dla sp80 kończy poziom (playbook ma 28).
- Czy `commit()` faktycznie podnosi akcje na decyzję w realnym biegu — **nikt tego
  nie zmierzył**, ani autorzy v13.1, ani ja.
