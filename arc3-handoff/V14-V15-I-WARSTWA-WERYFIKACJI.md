# v14 / v15 / v13.3-arena + ZBUDOWANA warstwa weryfikacji — i odpowiedź na „czy masz coś lepszego"

**Data:** 30.10.2026 ~08:45 UTC · **Czytane read-only przez `gh api`.**

| artefakt | gdzie | stan |
|---|---|---|
| `ARC3/duck-v14/` | `Gemma-konkurs@c4eeb067`, `b38b82eb` 08:04 | 36 komórek, `test_v14_package.py`, `build_v14.py`, `PROPOZYCJA-0007.md` |
| `ARC3/duck-v15/` | j.w., `07bf05e0` 08:12 | **37 komórek**, 7 patchy |
| `arc-agi-3/duck-v13-3-arena/` | **`Smak-Domu-Konkurs@5ed750ef`** | `0007-arena-replay-log.patch`, `build_v133_arena.py`, `OCENA-ARENA-V13-3-ARENA.md` |

> **STRESZCZENIE. (1) Sprawdziłem v14 i v15 w KODZIE, nie w README — i znalazłem rzecz, której nikt
> nie znalazł: ALARM `mean_actions_per_call < 1.5` w v14 (kom. 35) i v15 (kom. 36) NIE MOŻE NIGDY
> ODPALIĆ, bo zmierzona baza to 4,357. To jest ÓSMA instancja klasy „martwy kod przy zielonych
> testach" — i najgroźniejsza, bo to nie dźwignia, tylko INSTRUMENT, który miał powiedzieć, czy
> dźwignia zadziałała. (2) Niezależnie ZREPLIKOWAŁEM pomiar Gemmy na innym runie (r093): próg 10 →
> przedwczesna eskalacja na 96,3 % poziomów vs ich 96,9 %; wstrzyknięcia 211/96/21 vs ich 154/60/12
> — stosunki zgodne. (3) ZBUDOWAŁEM `tools/verify_config_liveness.py` (515 linii) — brakującą
> warstwę weryfikacji; odpalona na v13.2/v14/v15 daje 1–4 ustaleń i poprawnie rozróżnia próg 10
> (KRYTYCZNY) od 20 (akceptowalny). (4) Odpowiedź na „czy zbudujesz coś lepszego": **własnego
> notebooka NIE**, ale **mam dwie konkretne poprawki do v15 i bramkę weryfikacyjną** — i to jest
> uczciwy zakres. (5) ❗ARYTMETYKA SIĘ ZMIENIŁA: 50+ NIE JEST już wykluczone — jest
> **niezweryfikowalne w 3 slotach**. To jest słabsze twierdzenie niż „nieosiągalne" i je koryguję.**

---

## 1. ❗Znalazłem w v14 i v15 martwy instrument — i nikt go nie znalazł

Sprawdziłem **kod**, nie README. `ARC3/duck-v15/arc3-duck-v15.ipynb` (729 138 B, 37 komórek),
**komórka 36** (sonda rosteru):

```python
_acpc = [_r["actions_per_call"] for _r in _v14_recs if _r["calls"]]
"mean_actions_per_call": round(sum(_acpc) / len(_acpc), 2) if _acpc else 0.0,
...
if _acpc and _summary["mean_actions_per_call"] < 1.5:
    print(f"v15 roster: a/call = {_summary['mean_actions_per_call']} < 1.5 -> commit(plan) ...")
```

**To samo w v14, komórka 35** (sprawdzone: `arc3-duck-v14.ipynb`, 722 437 B, 36 komórek).

> ❌ **ALARM NIE MOŻE NIGDY ODPALIĆ.** Zmierzona baza: **4,357 akcji na wywołanie**
> (`FAKTY-I-POMIARY.md`, r019: **474 wywołania modelu / 2065 akcji**, trzy sesje domknięte co do
> jednostki). Warunek `< 1.5` jest **3× poniżej** wartości, którą już mamy.
>
> **Dlaczego to jest groźniejsze niż martwa dźwignia:** sonda rosteru v15 jest **jedynym**
> instrumentem, który w tym samym biegu odpowiada na dwa pytania — czy roster się powtarza
> (wartość `WINPATH`) i **czy batching zadziałał** (wartość `OPENER_COMMIT_HINT` + `ESCALATE=20`).
> **Pierwsza część działa** (druk werdyktu o powtarzalności bazowych kodów). **Druga jest martwa.**
> Czyli po submisji dowiemy się o rosterze, ale **NIE dowiemy się, czy jedyna dźwignia o właściwej
> skali zadziałała** — a to jest dokładnie ta informacja, od której zależy decyzja na 1.11.
>
> **Poprawka (jedna linia w komórce 36):**
> ```python
> if _acpc and _summary["mean_actions_per_call"] < 4.357:      # zmierzona baza r019
>     print(f"v15 roster: a/call = {_summary['mean_actions_per_call']} < 4.357 (baza r019) "
>           f"-> batching NIE poprawił akcji/wywołanie")
> ```
> Albo lepiej — **drukować wartość bezwarunkowo z odniesieniem**, bo celem nie jest alarm, tylko pomiar:
> ```python
> print(f"v15 batch: a/call = {_summary['mean_actions_per_call']} (baza r019 = 4.357; "
>       f"cel dla 400 akcji/grę ≈ 7.6)", flush=True)
> ```
> Próg **1.5** wygląda na wzięty z innej linii: `MEGA-DIAGNOSIS.md` 7911f950 mierzy **1,00 akcji
> na decyzję** dla **r013/r015/r018** (stara linia). Przy 1,00 próg 1,5 ma sens. **Przy naszej
> 4,357 nie ma.** To jest **przeniesienie progu z cudzej konfiguracji bez przeliczenia** — ta sama
> reguła, którą sformułowałem przy mechanizmie rellik13 (`POMIAR-SERVE-LOG-I-V15.md` §1).

### 1.1 To jest ÓSMA instancja klasy — i uzupełnia taksonomię

| # | instancja | co jest martwe | warstwa |
|---|---|---|---|
| 1 | `SCOPE=run` | wartość poza walidatorem degraduje cicho | walidator |
| 2 | `concurrency=120` vs `MAXREQ=10` | frontend 12× backend | spójność warstw |
| 3 | `EXPOSE_UNDO` nieustawione | default `tufa` = reklama akcji odrzucanej | default legacy |
| 4 | `official_110()` jako roster | nazwa vs docstring | nazwa vs docstring |
| 5 | `commit(plan)` | narzędzie zareklamowane, brak ścieżki wymuszenia | prompt vs zachowanie |
| 6 | `dead_skip` przy `pass_index` | `pass_index` zawsze 0 w rerunie | **mock vs konfiguracja submisji** |
| 7 | guard `GAME_OVER` | mock bez atrybutu `raw` ⇒ guard milczy | **mock vs kontrakt** |
| **8** | **alarm `actions_per_call < 1.5`** | **próg 3× poniżej zmierzonej bazy ⇒ gałąź nieosiągalna** | **PRÓG VS ZMIERZONA BAZA** |

> **Nowa warstwa w taksonomii: INSTRUMENT.** Dotąd wszystkie instancje dotyczyły **dźwigni**
> (kod, który ma coś zrobić). Ósma dotyczy **miernika** (kod, który ma powiedzieć, czy dźwignia
> zadziałała). **Martwy miernik jest groźniejszy niż martwa dźwignia**, bo martwa dźwignia daje
> wynik neutralny, a martwy miernik daje **fałszywe poczucie, że wiemy**.
>
> **Reguła: dla KAŻDEGO progu alarmowego w notebooku sprawdzić, czy przy zmierzonej bazie gałąź
> jest osiągalna.** To robi `verify_config_liveness.py` kontrolą L1 (§3).

---

## 2. Niezależna replikacja pomiaru Gemmy — na innym runie i innym podzbiorze

Gemma mierzyła na **r085, 32 ukończone poziomy**. Ja policzyłem z **surowego
`r093/output-pick/benchmark.json`** (v11, 10 gier, blob `90173adb`) na **69 poziomach** i na
**27 ukończonych**.

### 2.1 Zmierzony rozkład `base_actions_per_level` (ludzki baseline) — n = 69

```
min 6 | p10 26 | p25 36 | MEDIANA 72 | p75 115 | p90 208 | max 578 | średnia 104,0
```

**To jest właściwe odniesienie dla `ESCALATE_ACTIONS`** — nie „akcje agenta na poziom", bo
dyrektywa mówi modelowi *„przestań próbować ręcznie, zbuduj model"*, a to jest przedwczesne
dokładnie wtedy, gdy agent jest jeszcze **w tempie człowieka**.

### 2.2 Przedwczesna eskalacja — porównanie z Gemmą

| próg | **Gemma** (r085, 32 ukończone) | **mój pomiar** (r093, 27 ukończonych) | mój (r093, wszystkie 69) |
|---|---|---|---|
| **10** | **31/32 = 96,9 %** | **26/27 = 96,3 %** | 67/69 = 97,1 % |
| 20 | ~25/32 = 78 % | 25/27 = 92,6 % | 66/69 = 95,7 % |
| 60 | 7/32 = 22 % | 10/27 = 37,0 % | 38/69 = 55,1 % |

> **Przy progu 10 zgodność jest niemal dokładna: 96,9 % vs 96,3 % — 0,6 pp.** Przy 20 i 60 się
> rozjeżdża (78 vs 92,6; 22 vs 37), bo to **inne runy**, inne podzbiory i Gemma dodatkowo
> warunkuje na „agent był na tempie lub lepszy od baseline'u", a ja liczę surowe `próg < baseline`.
> **Oznaczam to, nie uśredniam.** Wniosek kierunkowy jest ten sam i jest **niezależnie
> zreplikowany**: przy progu 10 eskalacja jest przedwczesna na ~96–97 % poziomów.

### 2.3 Liczba wstrzyknięć — wskaźnik OPERATYWNY (koszt to tokeny, nie sama przedwczesność)

`Σ floor(akcje_poziomu / próg)` po 69 poziomach r093. Suma akcji agenta **2315**, suma baseline **7175**.

| próg | **wstrzyknięć (r093)** | % sumy akcji | przedwczesnych (`a_k ≤ b_k`) | **Gemma (r085)** |
|---|---|---|---|---|
| 10 | **211** | **9,1 %** | 22 | **154** |
| 20 | **96** | **4,1 %** | 18 | **60** |
| 30 | 58 | 2,5 % | 10 | — |
| 60 | **21** | **0,9 %** | 7 | **12** |
| `max(20, 1,2×baseline)` | — | — | — | **8** (0,8 % puli, **0/32**) |

**Stosunki są zgodne:** Gemma 154/60 = **2,57** i 60/12 = **5,0**; moje 211/96 = **2,20** i
96/21 = **4,57**. Moje liczby są na **69** poziomach (vs 32) i są **dolnym ograniczeniem**, bo akcje
na poziomach nieukończonych są ucięte przez koniec biegu, nie przez ukończenie poziomu.

> **Wniosek, który waliduje wybór Gemmy i precyzuje mój:** próg **20** kosztuje **4,1 %** sumy akcji,
> próg **10** kosztuje **9,1 %** — czyli **2,2× więcej**. Przy progu 10 Gemma zmierzyła dodatkowo
> **15,3 % puli tokenów gry** na same dyrektywy. **20 jest rozsądnym kompromisem, ale optimum jest
> WZGLĘDNE**: `max(20, 1.2 × baseline[poziom])` → **8 wstrzyknięć, 0,8 % puli, 0 przedwczesnych**.
> To wymaga patcha scaffoldu (`PROPOZYCJA-0007.md` Gemmy), którego **nie mogę zweryfikować**
> (brak bundla r033) — więc **rekomenduję, nie buduję**.

### 2.4 Przy okazji: dwa nowe pomiary z r093

* **Nasze akcje na UKOŃCZONYCH poziomach: n = 27, mediana 54, średnia 63,8** — a mediana
  `base_actions_per_level` dla tych samych poziomów to **42**. Czyli na ukończonych poziomach
  jesteśmy **wolniejsi** od człowieka (stosunek mediana 0,532 licząc `nasze/baseline` per poziom).
* **Suma akcji agenta 2315 vs suma baseline 7175 = 32 %** — czyli **pokrycie, nie efektywność**,
  jest problemem. **Czwarte niezależne potwierdzenie** (po Gemmie „głębokość = 96 % brakujących
  punktów", 7911 „pokrycie 29 %", moim twierdzeniu o capie „efektywność ≈ 1,75 pkt").

---

## 3. ✅ ZBUDOWAŁEM brakującą warstwę weryfikacji: `tools/verify_config_liveness.py`

**515 linii, czysty Python 3, biblioteka standardowa. 0 GPU, 0 slotów, 0 bundla, 0 silnika.**
Działa na **tekście** notebooka i patchy — więc uruchamiam go w moim sandboxie (2 CPU / 3,9 GB)
na **prawdziwych** plikach pobranych przez `gh api`.

**Cztery kontrole — każda odpowiada na jedną z ośmiu instancji z §1.1:**

| kontrola | co robi | którą instancję łapie |
|---|---|---|
| **L1 ŻYWOTNOŚĆ INSTRUMENTU** | każdy próg porównujący **znaną metrykę** do liczby: czy gałąź może się wykonać przy zmierzonej bazie? | **#8** (alarm `< 1.5` przy bazie 4,357) |
| **L2 DOMYŚLNA WARTOŚĆ ENV** | każda zmienna env czytana w patchu/notebooku: jej **default i walidator**; flaguje legacy-default i nieustawione | **#1 #3 #4** (`SCOPE`, `EXPOSE_UNDO`, `official_110`) |
| **L3 OSIĄGALNOŚĆ** | warunki sięgające po zmienne **stałe w rerunie** (`pass_index=0`, `n_passes=1`) | **#6** (`dead_skip`) |
| **L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA** | concurrency ≤ MAXREQ · cap na grę vs uczciwy udział · `ESCALATE_ACTIONS` vs **zmierzony** rozkład baseline i **zmierzona** liczba wstrzyknięć | **#2 #5** + próg eskalacji |

**Wszystkie bazy są ZMIERZONE i mają źródło w komentarzu** (`actions_per_call=4.357` z r019,
`actions_per_game=212.6` z r085, `base_actions_per_level` — pełna lista 69 wartości z r093,
`ms_per_token=17.2`, `kv_token_usage_mean=0.6042` z mojego `parse_serve_log.py`,
`fair_share_s_per_game=2945` z komórki 25). **Da się je nadpisać przez `--baseline`, jeśli jest
świeższy pomiar — skrypt nigdy nie zgaduje, tylko porównuje.**

### 3.1 Wynik na prawdziwych notebookach

| pakiet | ustaleń | KRYTYCZNE | co złapał |
|---|---|---|---|
| **v13.2** (`ESCALATE=10`) | 4 | **1** | `ESCALATE_ACTIONS=10 → 211 wstrzyknięć = 9,1 % sumy akcji` · cap 10,84× powyżej uczciwego udziału |
| **v14** (`ESCALATE=20`) | 4 | **1** | **alarm `actions_per_call < 1.5` NIE MOŻE ODPALIĆ** (baza 4,357) |
| **v15** (`ESCALATE=20`) | 4 | **1** | **ten sam martwy alarm** (komórka 36) |

**To jest właściwe rozróżnienie i waliduje wybór Gemmy:** próg **10** jest flagowany jako
**KRYTYCZNY** (9,1 % ≥ próg 6 %), próg **20** przechodzi (4,1 % < 6 %) — a **oba** pakiety mają
martwy alarm. Czyli narzędzie **nie** krytykuje decyzji, którą Gemma podjęła na podstawie pomiaru,
i **łapie** to, czego Gemma nie złapała.

### 3.2 Uczciwie: dwa fałszywe pozytywy, które znalazłem i naprawiłem w swoim narzędziu

Pierwsze uruchomienie dało `concurrency=10, MAXREQ=0` jako **KRYTYCZNE**. Sprawdziłem przyczynę:

* `MAXREQ=10` występuje w notebookach **TYLKO W KOMENTARZACH** (`"SGLang slot (MAXREQ=10 concurrent
  generations)"`, `"# v11 fix: was 120 vs MAXREQ=10 server"`) — mój regex brał je za konfigurację;
* `ARC3_MAX_ACTIVE_STREAMS` złapałem jako **default** z `_get_env_int("ARC3_MAX_ACTIVE_STREAMS", 0)`,
  czyli `0`, a nie wartość ustawioną;
* plus duplikat L1 (ta sama linia raportowana z `if` i z `print` cytującego próg w tekście).

**Naprawione:** odrzucam linie-komentarze, biorę **tylko jawne ustawienia** (`os.environ[...] =`
albo wpis w dict wariantu), a gdy wartości backendu **nie da się** ustalić statycznie, raportuję
**INFO „nie da się zweryfikować"** z gotową asercją do preflightu — **zamiast zmyślać KRYTYCZNE**.
Dodatkowo L1 raportuje tylko warunek, nie `print`.

> **To jest ta sama dyscyplina, którą wymagam od innych, zastosowana do własnego kodu:**
> narzędzie, które daje fałszywe pozytywy, jest gorsze niż brak narzędzia, bo uczy ignorować
> raport. **Nie wypuszczam checkera, który kłamie.**
>
> ⚠️ **I uczciwie o granicach mojego narzędzia:** (a) mój wskaźnik „przedwczesności"
> (`próg < baseline`) jest **prostszy i grubszym sitem** niż kryterium Gemmy (która warunkuje
> dodatkowo na „agent był na tempie") — dlatego przy progach 20 i 60 moje liczby są wyższe;
> wskaźnikiem **operatywnym** jest liczba wstrzyknięć i to ona decyduje o ważności.
> (b) L2 ma **ręczną** listę `KNOWN_LEGACY_DEFAULTS` — łapie tylko te zmienne, o których wiem;
> nowa zmienna z legacy defaultem **przejdzie niezauważona**. (c) L3 sprawdza tylko dwie zmienne
> stałe (`pass_index`, `n_passes`). (d) **Nie zastępuje `verify_v13.py`** — uzupełnia je o warstwę,
> której tam brakuje.

---

## 4. v13.3-arena — zlokalizowany, i potwierdzam co dokłada

`Smak-Domu-Konkurs@5ed750ef`, katalog `arc-agi-3/duck-v13-3-arena/`:
`README.md`, `ANALIZA-23.md`, **`OCENA-ARENA-V13-3-ARENA.md`**, `arc3-duck-v13.ipynb`,
`kernel-metadata.json`, `patches/0006-winpath-replay.patch`, **`patches/0007-arena-replay-log.patch`**,
`playbook.json`, `src/arc3_winpath.py`, `src/base-v11.ipynb`, `tests/{test_plan_commit,test_winpath}.py`,
`tools/{build_playbook,build_v13,build_v133_arena}.py`.

Potwierdzone z komórki 2 i 6 notebooka v15 (który dziedziczy v13.3):
* **`ARC3_OPENER_COMMIT_HINT`** — `return _get_env_bool("ARC3_OPENER_COMMIT_HINT", False)`,
  a komentarz w komórce 2: *„v13.3-arena additions: `ARC3_OPENER_COMMIT_HINT=1` (batching pressure
  on …)"* oraz *„hint kill-switch: `"ARC3_OPENER_COMMIT_HINT": "0"` in variant"*.
  ⚠️ **Default `False`** — czyli **bez jawnego ustawienia hint jest WYŁĄCZONY**. To jest
  **dokładnie instancja #3** (default legacy) i **L2 mojego narzędzia to łapie**, gdy dopiszę tę
  zmienną do `KNOWN_LEGACY_DEFAULTS` (jest w liście).
* **komórka 6** zawiera też **egzekwowanie kompaktowości wyjścia narzędzi**: *„Never print or echo
  full board frames"*, `board_print_suppressed_rows`, *„existing 'never print full boards' policy
  **mechanically** for models that …"*. **To jest nowe i ważne**: policy jest egzekwowana
  **mechanicznie** (tłumienie wierszy), nie tylko proszona w promptcie — czyli atakuje `tok/akcję`
  od strony wyjścia narzędzi, a nie wyjścia modelu. **To jest trzecia dźwignia na `tok/akcję`,
  o której wcześniej nie wiedziałem.**

---

## 5. ❗Korekta mojego stanowiska o 50+ — z „nieosiągalne" na „nieweryfikowalne w 3 slotach"

Dotąd pisałem (`DIAGNOZA-23-89-I-PLAN.md` §5, `RESEARCH-LIDERZY-50PLUS.md`, `POMIAR-SERVE-LOG-I-V15.md`):
*„50+ wymaga +25,3 pkt = +6,4 σ, nieosiągalne"*. **To było poprawne jako stwierdzenie o LOSOWANIU
na obecnej bazie, ale zbyt mocne jako stwierdzenie o możliwej bazie.** Liczę dokładnie:

```
akcje/grę = 2945 × 1000 / (ms/token × tok/akcję)
tok/akcję = tok/wywołanie ÷ akcje/wywołanie = 3664,6 ÷ 4,357 = 841,2   (r019 — zgadza się z pomiarem)

STAN OBECNY : 17,2 ms/tok × 647 tok/akcję  → 228 akcji/grę  → projekcja Gemmy 35,6 | zmierzone 26,78
CEL 300 akcji: ms/tok × tok/akcję ≤ 9817   → tok/akcję ≤ 571 (przy 17,2 ms/tok)
CEL 400 akcji: ms/tok × tok/akcję ≤ 7362   → tok/akcję ≤ 428
CEL 600 akcji: ms/tok × tok/akcję ≤ 4908   → tok/akcję ≤ 285
```

Żeby zejść z 647 do **428** tok/akcję przy niezmienionym `tok/wywołanie` (3664,6), trzeba
**akcje/wywołanie 4,357 → 6,57** (1,51×). Żeby zejść do **370** (cel Gemmy na 400+ akcji) —
**4,357 → 9,90** (2,27×).

> **Czyli 50+ wymaga, żeby model batchował 1,5–2,3× więcej akcji na wywołanie.** To jest
> **konkretne, liczbowe i osiągalne mechanicznie**: `commit(plan)` ma `max_actions=40`, więc
> sufit jest daleko. **Pytanie nie brzmi „czy się da", tylko „czy model posłucha".**
>
> **I tu jest sedno: jedynym instrumentem, który miał to zmierzyć, jest alarm
> `actions_per_call < 1.5` — KTÓRY JEST MARTWY (§1).** Czyli **obecnie żaden pakiet nie powie nam,
> czy batching zadziałał.** Dlatego poprawka alarmu jest **najważniejszą pojedynczą rzeczą**, jaką
> mogę wnieść — nie dlatego, że podnosi wynik, tylko dlatego, że **bez niej nie dowiemy się, czy
> cokolwiek podnosi wynik**.

**Korekta stanowiska, uczciwie:**

| twierdzenie | stan |
|---|---|
| „50+ wymaga +6,4 σ od średniej bazy" | ✅ **prawdziwe** — i dlatego **nie da się tego wylosować** |
| „50+ jest nieosiągalne" | ❌ **ZBYT MOCNE, KORYGUJĘ** — arytmetycznie wystarczy batching 1,5–2,3× |
| „50+ jest osiągalne" | ❌ **też nie** — bo **nie da się tego zweryfikować w 3 slotach** przy σ≈2,5–3,9 i progu +5 pkt |
| **stan właściwy** | ⚠️ **„50+ jest ARYTMETYCZNIE W ZASIĘGU, ale NIEWERYFIKOWALNE w 3 slotach; obstawianie go to hazard, nie plan"** |

**Dlaczego to nie jest to samo, co „nieosiągalne":** jeśli batching zadziała (a/call 4,36 → 6,6),
to akcje/grę rosną 228 → 325, projekcja Gemmy ~59,5, a przy jej własnym przeszacowaniu ~25 %
(porównanie: przy 228 akcjach projekcja 35,6 vs zmierzone 26,78 = **8,8 pkt / 25 % przeszacowania**)
dostajemy **~45**. **Czyli ~45–50 jest w zasięgu JEDNEGO udanego wdrożenia batchingu.**
**Ale** — i to jest powód, dla którego tego nie obiecuję: (a) przeszacowanie 25 % jest **jednym
punktem danych**, nie prawem; (b) czy model posłucha hintu — **niezmierzone, a instrument martwy**;
(c) `ESCALATE` i hint **mogą się znosić** (Gemma: przy progu 10 drugi nacisk wygrywał);
(d) 3 sloty przy σ≈3 **nie zweryfikują** +20 pkt vs szum, jeśli efekt będzie mniejszy niż +5.

---

## 6. ❌ Czy zbuduję własny notebook? NIE. ✅ Czy mam coś lepszego? TAK — ale nie konfigurację

### 6.1 Dlaczego nie zbuduję konfiguracji (trzy powody, bez zmian i twarde)

1. **Nie mogę zweryfikować.** Certyfikacja wymaga `verify_v13.py --bundle <r033>` na czystym bundlu
   Franzena (7/7 patchy, kompilacja drzewa, testy **na spatchowanym drzewie**). **Nie mam bundla
   r033, `arcengine`, GPU ani `cargo`** (2 CPU / 3,9 GB). 3 z 12 testów `test_plan_commit.py`
   wymagają `inference.agent.python_tool_sandbox` **z bundla** (potwierdził 7911f950 niezależnie).
2. **Nie mogę przetestować przed spaleniem slotu.** Zostały **3** (31.10, 1.11, 2.11).
3. **v15 już dziedziczy certyfikację v13.3** (7/7 na czystym r033, 11/11 winpath, standalone ==
   patched, playbook 14/14 na silniku) i ma **diff 5 komórek**. Mój pakiet zaczynałby od zera.

### 6.2 Co **mam** lepszego — trzy rzeczy, wszystkie zweryfikowalne przeze mnie

| # | co | dlaczego to jest wkład, a nie duplikat |
|---|---|---|
| **1** | **Poprawka martwego alarmu** (§1) — jedna linia w komórce 36 v15 / 35 v14 | **Nikt tego nie znalazł** w czterech gałęziach. Bez tego **nie dowiemy się, czy batching zadziałał** — a to jest jedyna dźwignia o właściwej skali (§5) |
| **2** | **`tools/verify_config_liveness.py`** (§3) — bramka przed każdą submisją | Łapie **całą klasę** 8 instancji, w tym **instrumenty**. Gemma i Smak mają `verify_v13.py` (patche + testy modułu); **nikt nie ma warstwy osiągalności i żywotności** |
| **3** | **Zmierzone bazy** (§2): rozkład `base_actions_per_level` (n=69, mediana 72, min 6, max 578) i liczby wstrzyknięć (211/96/58/21) | **Niezależna replikacja** pomiaru Gemmy na innym runie — i **surowe liczby**, które pozwalają ustawić próg względny bez zgadywania |

**Oraz dwie rekomendacje, których NIE buduję, bo nie mogę ich zweryfikować:**
* **próg względny** `max(20, 1.2 × baseline[poziom])` → 8 wstrzyknięć, 0,8 % puli, 0 przedwczesnych
  (Gemma `PROPOZYCJA-0007.md`; wymaga patcha scaffoldu ⇒ wymaga bundla r033)
* **sprawdzenie `ARC3_OPENER_COMMIT_HINT`** — default `False`, więc **musi** być ustawione jawnie
  na `"1"` w wariancie; to jest instancja #3 i mój L2 to łapie

### 6.3 Konkretny pakiet, który rekomenduję na slot 31.10

**v15 + dwie poprawki jednowierszowe** (żadna nie wymaga bundla ani GPU):

```python
# 1. komórka 36 (v15) / 35 (v14) — naprawa martwego alarmu
if _acpc and _summary["mean_actions_per_call"] < 4.357:          # było: < 1.5
    print(f"v15 roster: a/call = {_summary['mean_actions_per_call']} < 4.357 (baza r019) "
          f"-> batching NIE poprawil akcji/wywolanie", flush=True)
print(f"v15 batch: a/call = {_summary['mean_actions_per_call']} "
      f"(baza r019 = 4.357; cel dla 300 akcji/ge ≈ 5.7, dla 400 ≈ 7.6)", flush=True)

# 2. komórka 1 — asercja, że hint jest JAWNIE włączony (default to False!)
assert ARC3_VARIANT["env"].get("ARC3_OPENER_COMMIT_HINT") == "1", \
    "ARC3_OPENER_COMMIT_HINT ma default False - bez jawnego '1' batching na openerze jest MARTWY"
```

**Reszta bez zmian**: `ESCALATE_ACTIONS=20` (zweryfikowane: 4,1 % akcji vs 9,1 % przy 10) ·
`CAP=0` · `WINPATH=1` (bezpieczne: fallback do LLM, init-stróż, brak zatruwania ścieżek; wartość
warunkowa, nie ujemna) · `DEAD_SKIP=1` (prawdopodobnie martwy, ale nieszkodliwy) ·
`EXPOSE_UNDO="on"` · concurrency 10 · **obie sondy ON**.

**Bramka przed pushem:** `python3 verify_config_liveness.py <notebook> --strict` → **0 KRYTYCZNYCH**.

---

## 7. Ranking po tej turze

| # | działanie | koszt | wartość |
|---|---|---|---|
| **1** | **Naprawić martwy alarm** w v15 (§1, jedna linia) | 0 | **bez tego submisja nie powie, czy batching zadziałał** — a to jedyna dźwignia o właściwej skali |
| **2** | **Wysłać v15 + 2 poprawki** (§6.3) na slot 31.10 | 1 slot | ~28–31 **+ werdykt o rosterze + pomiar `a/call`** |
| **3** | **Bramka `verify_config_liveness.py --strict`** przed każdym pushem | ~10 s | łapie klasę 8 instancji, która kosztowała nas 4 recenzje i jeden slot (0.00) |
| **4** | **Przeczytać z logu**: `roster_probe.jsonl`, `budget_probe.json`, **`mean_actions_per_call`** | 0 | rozgałęzienie na 1.11 |
| **5** | **`parse_serve_log.py` na `serve.log` każdego nowego runu** | ~5 min | strażnik regresji KV (hipoteza obalona dla r085/r093, ale konfiguracja może się zmienić) |
| **6** | 1.11 → rozgałęzienie z pkt 4; 2.11 → **select best** | 2 sloty | ochrona przed szumem |

**Oczekiwanie: ~28–31.** Cel: **srebro ≈32,33**. **~45–50 jest arytmetycznie w zasięgu JEDNEGO
udanego wdrożenia batchingu (§5) — ale nie obiecuję tego, bo instrument, który miał to potwierdzić,
jest martwy, a 3 sloty przy σ≈3 tego nie zweryfikują.**
