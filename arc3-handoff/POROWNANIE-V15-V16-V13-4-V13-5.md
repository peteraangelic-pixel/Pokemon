# v15-a450 · v13.4-unified · v13.5-consensus · duck-v16 — porównanie, replikacja i MOJA NAJLEPSZA WERSJA

**Data:** 2026-10-30, ~09:40 UTC · **Sesja:** `arena/c87f7a48-pokemon`
**Metoda:** wszystko poniżej czytałem **w kodzie** (`taaf/game.py`, patche, komórki notebooków,
`kernel-metadata.json`, fixture testów), a liczby **policzyłem sam** z surowych `benchmark.json`.
Jeden test **uruchomiłem** (ich własny, bez GPU). Żadnej liczby nie przepisuję z cudzego README.

> **Skrót dla czytającego w pośpiechu:** powstało pięć pakietów. **Najlepszy kod ma duck-v16 Gemmy**
> (jedyny, którego reguła eskalacji jest żywa w punktowanym rerunie), ale **ma dwa defekty
> wdrożeniowe, przez które nie da się go wypchnąć** (`code_file` wskazuje plik, którego nie ma;
> slug należy do cudzego kernela). Zbudowałem **`c87-v16f` = v16 + 6 poprawek**, jako skrypt,
> i przepuściłem przez własną bramkę: **4 KRYTYCZNE → 0**. Po drodze potwierdziłem ze źródła
> pierwotnego fakt, który unieważnia całą linię „eskalacja względna", znalazłem **dwie nowe
> instancje klasy martwego kodu** (#9 wejście ukryte, #10 instrument głośno-mylący) i **policzyłem
> sufit wyniku mechanicznie** — z czego wynika, że „+1,1 poziomu na grę ⇒ 50" jest **sufitem 47,8,
> a wynikiem ~43**.

---

## 0. Co powstało na gałęziach od mojej ostatniej tury (08:45 → 09:40 UTC)

| pakiet / dokument | gałąź · commit | czas | co to jest |
|---|---|---|---|
| `duck-v15` (**drugi** v15) | Pokemon @ `a450b00f` · `8d96c68f` | 08:10 | v14 + **własny** patch 0007 (eskalacja względna + cap 2) |
| `V15-PLAN`, `V16-PLAN`, `V17-COMPARE` | Pokemon @ `7911f950` · `724189b2`/`c170f552`/`cad326c5` | 08:10–08:22 | analityka + `local/v15_policy.py`, `v17_policy.py`, `metric.py`, `token_budget.py` |
| **`duck-v13-4-unified`** | Smak @ `5ed750ef` · `f04c3e73` | 08:15 | v13.2 + v13.3-arena + patch 0008 (eskalacja względna) |
| `duck-v15` (Gemma) | Gemma @ `c4eeb067` · `07bf05e0` | 08:12 | v13.3-arena + 3 rzeczy env-only z v14 |
| **`duck-v13-5-consensus`** | Smak @ `5ed750ef` · `63ede621` | 08:27 | v13.4 + werdykt o widoczności baseline + ważone pokrycie w sondzie |
| **`duck-v16`** | Gemma @ `c4eeb067` · `0ef24651` | 08:38 | v13.4 + **patch 0009 self-pace** + sonda pokrycia |
| `ARC3/STATUS.md`, `REVIEWS/INDEX.md` | Gemma · `ec193e8b` | 08:44 | punkt wejścia dla innych gałęzi |
| `AUDYT-V13-4-...md` + addendum | Pokemon @ `a450b00f` · `839c1698`/`52b709ee` | 08:43/08:49 | niezależny audyt v13.4, v13.5, v16, v17 |

**Są DWA różne `duck-v15`** — oba mówią „v15", oba mówią „7 patchy", oba mają patch **0007**, ale
**o zupełnie innej treści** (a450: eskalacja względna → `tool_agent.py`+`solver.py`+`plan_commit.py`;
Gemma: log zdarzeń win-path → `arc3_winpath.py`). 7911 to złapał i miał rację.

**„v13.4 nie istnieje" (7911, `cad326c5` §0) — NIEAKTUALNE o 6 min 11 s.** Smak wypchnął
`f04c3e73` o **08:15:58**, 7911 commitował o **08:22:09**. To **dokładnie ten sam błąd**, który 7911
wypomniał sam sobie w preambule („v13.2 nie istnieje" było nieaktualne o 10 min). Szukali czterema
metodami — i wszystkie cztery były poprawne, tylko wykonane przed publikacją. **Wniosek nie jest
„7911 się myli", tylko: przy czterech sesjach piszących równolegle w oknie 30 minut, twierdzenie
„X nie istnieje" ma okres przydatności liczony w minutach.** Ich addendum z `52b709ee` już to prostuje.

---

## 1. FAKT CENTRALNY: w submisji silnik **UKRYWA** baseline

Gemma w patchu 0009 napisała zdanie, które unieważnia całą linię „eskalacja względna".
**Sprawdziłem je w źródle pierwotnym** — `taaf/game.py` z `r033-recon-bundle`
(688 linii, `Smak-Domu-Konkurs@5ed750ef`). Jest **w czterech miejscach**:

```
L254-255  docstring GameRun : "``base_actions_per_level`` is ``None`` when the engine hides
                               baselines (e.g. submission mode)."
L439-440  docstring Game    : "``base_actions_per_level`` is ``None`` when the engine hides
                               baselines (submission mode)."
L448      pole              : base_actions_per_level: list[int] | None = field(default=None, init=False)
L471-472  komentarz asercji : "# ``base_actions_per_level`` may legitimately be None (R11.02:
                               #  engine hides baselines in submission mode)."
L391-392  _compute_final_score: "if self.base_actions_per_level is None or ...: return 0.0"
```

**✅ POTWIERDZONE. Konsekwencja:** patch 0007 (a450) i 0008 (Smak/Gemma) liczą
`max(floor, rate × base_actions_per_level[level])`. W submisji ta lista jest `None`, więc
`if b > 0` **nie zachodzi** i funkcja zwraca **stały floor 20**. Cały pomiar
„8 wstrzyknięć, 0,8 % puli, **0/32 przedwczesnych**" — którym uzasadniano tę dźwignię — dotyczy
**SMOKE'A**, nie biegu punktowanego.

**To jest TA SAMA FORMA co instancja #6** (`dead_skip` bramkowany `pass_index`, a mock karmił
wartości, których rerun nigdy nie produkuje). **Tutaj smoke karmi wartości, których submisja nigdy
nie produkuje.** Reguła: *pomiar wykonany w trybie, w którym zmienna jest widoczna, nie dowodzi
niczego o trybie, w którym jest ukryta.*

### 1.1 Stan empiryczny: **nikt tego warunku nigdy nie zaobserwował**

Przejrzałem **wszystkie 5 dostępnych `benchmark.json`**:

| run | label | `n_passes` | gier | baseline **HIDDEN** | baseline **PRESENT** |
|---|---|---|---|---|---|
| r050 | — | — | — | (blob nie zdekodował się) | — |
| r085 | duck-harness-kaggle | 1 | 10 | **0** | **10** |
| r093 | duck-harness-kaggle | 1 | 10 | **0** | **10** |
| r108 | — | — | — | **ten sam blob `90173adb` co r093** | — |
| r110 | duck-harness-kaggle | 1 | 10 | **0** | **10** |
| r118 | duck-harness-kaggle | 1 | 10 | **0** | **10** |

**0 z 5 runów pokazuje `base_actions_per_level = null`** — bo wszystkie to **smoke'i**.
⇒ warunek „hidden" jest **UDOKUMENTOWANY W ŹRÓDLE, ALE NIE ZAOBSERWOWANY**. Cała argumentacja za
self-pace opiera się na dokumencie, nie na pomiarze.

**I to jest argument ZA sondą widoczności baseline, którą mają v13.5 (kom. 38) i v16 (kom. 39):**
pierwszy prawdziwy submit z tym pakietem **rozstrzygnie to empirycznie w biegu**. v13.4 i v15-a450
tej sondy **nie mają** — więc po submisji nie dowiedzielibyśmy się niczego.

### 1.2 Co jest ŻYWE w submisji (też `taaf/game.py`)

```
L569  execute_action : self.game_run.actions_per_level[level_before] += 1
L571-572             : levels_completed aktualizowane zaraz po tym
L258-259  docstring  : "Invariant: sum(actions_per_level) == len(history)"
```

**Licznik rośnie PO KAŻDEJ AKCJI, W TRAKCIE BIEGU** — nie na końcu. ⇒ **self-pace (patch 0009) ma
prawdziwe źródło danych.** Gemma twierdziła to w docstringu; **ja to potwierdziłem w kodzie silnika.**
To jest jedyna reguła eskalacji, która w rerunie robi coś innego niż stały floor.

---

## 2. Replikacja pomiaru eskalacji — **r085 (ich populacja) + r093 (mój niezależny run)**

Policzyłem z semantyki **wysłanego kodu**, na surowych `benchmark.json`.
Rzeczywista pula tokenów r085 = **1 417 188** `generated_tokens` / 10 gier = **141 719 na grę**;
dyrektywa = 146 tok (7911) ⇒ **1 wstrzyknięcie = 0,1030 % puli jednej gry**.

| reguła | r085 nudge / przedwczesne | **% puli** | r093 nudge / przedwczesne | **żywa w rerunie?** |
|---|---|---|---|---|
| próg 10 (v13.2, v13.3) | **154 / 31-32** | **15,87 %** | 157 / 26-27 | tak |
| próg 20 (v14) | **67 / 26** | 6,90 % | 72 / 23 | tak |
| próg 20 + cap 2 (**v13.4, v13.5, v15-a450 w rerunie**) | **42 / 26** | 4,33 % | 39 / 23 | tak |
| względna 1,2×baseline (patch 0007/0008) | **8 / 0** | 0,82 % | 10 / 0 | **NIE** — §1 |
| **self-pace 1,5×mediana (patch 0009, v16)** | **22 / 14** | **2,27 %** | **22 / 13** | **TAK** |

**CZTERY Z PIĘCIU LICZB GEMMY ODTWARZAJĄ SIĘ CO DO JEDNEJ** (154/31, 67/26, 42/26, 8/0).
**Ich arytmetyka tokenów też**: 154 × 146 / 141 719 = **15,87 %** vs ich **15,3 %** (0,6 pp);
8 × 146 / 141 719 = **0,82 %** vs ich **0,8 %**. **To jest solidna robota pomiarowa i tak ją oceniam.**

### 2.1 Tabela R085 w ich teście jest DOKŁADNA

`tests/test_self_pace.py` hardkoduje tabelę 10 gier (base + actions na ukończonych poziomach).
**Porównałem ją z `r085/output-pick/benchmark.json`: 10/10 gier, 32 poziomy, `base` i `actions`
— 0 ROZBIEŻNOŚCI.** Cytowana tabela nie jest tu artefaktem wtórnym; jest wierną kopią źródła.
(Zasada „ściągnij pierwotne i sprawdź tożsamość" tym razem daje wynik pozytywny — i mówię to wprost.)

### 2.2 Docstring patcha 0009 mówi **27/16** i NIE odtwarza się

| źródło w pakiecie Gemmy | nudge / przedwczesne |
|---|---|
| `patches/0009-arena-self-pace.patch`, docstring | **27 / 16** |
| `tests/fixtures/tool_agent_0009_post.py`, **ten sam docstring** | **27 / 16** |
| `ARC3/STATUS.md`, tabela | **22 / 14** |
| **uruchomiony przeze mnie `tests/test_self_pace.py`** | **`self-pace=22/14`** |
| **moja niezależna replikacja (r085)** | **22 / 14** |
| **moja replikacja na r093 (inny run)** | **22 / 13** |

**27/16 NIE JEST OSIĄGALNE.** Przeszukałem **192 kombinacje**: 2 populacje (32 ukończone / wszystkie
69 poziomów) × 3 rate (1,2 / 1,5 / 2,0) × 2 sufit (brak / 120) × 4 cap (0/1/2/3) × 2 kryteria
przedwczesności (`<` / `<=`) × 2 tryby. **Ani (22,14) z docstringu, ani (27,16) — żadna.**
Najbliżej: (23,12) przy rate 1,2 i cap 0; (20,13) na populacji 69 poziomów.
**Liczba przedwczesnych w całej siatce przyjmuje tylko wartości 12, 9 lub 6 — nigdy 14 ani 16.**

**a450b00f znalazł tę rozbieżność pierwszy** („docstring 0009 mowi 27/16, tabela i test 22/14") —
**potwierdzam niezależnie** i dodaję: nie jest to literówka, tylko liczba, której wysłany kod
nie produkuje przy żadnych parametrach.

### 2.3 Asercja, która **nie może rozstrzygnąć**

```python
assert rel[:2] == (8, 0), rel          # DOKŁADNA — dobra
assert floor[:2] == (42, 26), floor    # DOKŁADNA — dobra
assert pace[0] < floor[0] and pace[1] < floor[1], (pace, floor)   # ← NIERÓWNOŚĆ
```

**Trzecia asercja przechodzi dla 14/9, dla 22/14 i dla 27/16.** Przy cap 2 self-pace może dać
dowolną wartość od 0 do 41 i test będzie zielony. **To ta sama klasa co bramka `a/call ≥ 1,8`,
którą 7911 słusznie wypomniał Gemmie** — tylko że tamta jest w dokumencie GO/NO-GO, a ta jest
w teście jednostkowym, który ma dowodzić, że patch robi to, co mówi docstring.
**Naprawa: `assert pace[:2] == (22, 14)`.** Wtedy docstring 27/16 zostałby złapany natychmiast.

### 2.4 ⚠️ MÓJ WŁASNY BŁĄD tej tury (11. self-korekta)

Pierwszą replikację self-pace policzyłem jako **14/9** i ogłosiłem, że żadna z liczb Gemmy się nie
odtwarza. **Było to błędne.** Przyczyna: pominąłem ostatnią linię `_escalate_threshold`:

```python
paced = _escalate_self_pace(agent, floor)
return paced or floor          # <-- gdy brak historii, _escalate_self_pace daje 0, a `or floor` daje 20
```

Na **pierwszym poziomie każdej gry** nie ma jeszcze historii, więc `_median_int([])` = 0 ⇒
`_escalate_self_pace` = 0 ⇒ ale `_escalate_threshold` zwraca **floor 20**, nie 0. Ja zwracałem 0
(cisza). W r085 to **10 poziomów** różnicy — dokładnie tyle, ile brakowało do 22/14.

**Jak to znalazłem: URUCHOMIŁEM ICH TEST** (`python3 tests/test_self_pace.py`, bez GPU, bez bundla —
wydrukował `self-pace=22/14`). **Lekcja, którą dopisuję do swoich reguł: zanim ogłoszę, że cudza
liczba się nie odtwarza, uruchom ich kod, a nie tylko reimplementuj go.** Reimplementacja gubi
`or floor`. Kosztowało mnie to jedną fałszywą konkluzję, którą niniejszym wycofuję.

**Co ZOSTAJE prawdziwe po korekcie:** docstring **27/16 nadal się nie odtwarza** (192 kombinacje),
a asercja **nadal nie dyskryminuje**. Te dwa ustalenia nie zależały od mojego błędu.

---

## 3. DWIE NOWE INSTANCJE klasy „zielone testy, martwy kod"

### #9 — WEJŚCIE UKRYTE W SUBMISJI (dźwignia)

`ARC3_ESCALATE_RELATIVE=1` bez żywego zamiennika. W smoke'u działa i daje piękny pomiar
(8 wstrzyknięć, 0 przedwczesnych); **w submisji degraduje do flooru 20 + cap 2 = 42 / 26 / 4,33 %**.
Występuje w: **v13.4, v13.5, v15-a450** (u a450 reguła jest **zawsze włączona**, bez kill-switcha
env — czyta `self._arc3_base_actions` przez czystą funkcję `pc_escalate_at`). **v16 ma zamiennik.**

**Uczciwie o a450:** ich patch jest **None-safe** — `if base_actions:` + `getattr(self,
"_arc3_base_actions", None)`. **Nie crashuje w submisji.** To nie jest awaria, tylko cicha
degradacja — czyli dokładnie to, co najtrudniej zauważyć.

### #10 — INSTRUMENT GŁOŚNO-MYLĄCY (**nowa podklasa**)

Komórka „v11 metering" (v15-a450 kom. 35, v13.4 i v13.5 kom. 37, v16 kom. 38):

```python
need = sum(_v11_int(x) for x in (getattr(run, "base_actions_per_level", []) or []))   # = 0 w submisji
score = run._compute_final_score()      # = 0.0 w submisji (taaf/game.py L391-392)
"depth_budget_used_pct": round(100.0 * _mean("actions") / max(1.0, _mean("actions_need")), 1),
_gate = "NO-GO (below v3 smoke 29.02)" if _summary["mean_score"] <= 29.02 else "GO (above v3 smoke)"
```

W **każdym prawdziwym submicie** ta komórka wydrukuje:

```
MEAN game: score=0.00 weight=... actions=212/0 (21200.0% of a full clear) ...
v11 gate: NO-GO (below v3 smoke 29.02)
```

`max(1.0, ...)` zamienia dzielenie przez zero w dzielenie przez **1**, czyli w `100 × akcje`.

**Dlaczego to jest GROŹNIEJSZE niż martwy alarm #8:**

| | #8 cicho-martwy (`a/call < 1.5`) | **#10 głośno-mylący (`NO-GO`)** |
|---|---|---|
| gałąź | nigdy się nie wykonuje | **wykonuje się ZAWSZE** |
| log | **MILCZY** | **KRZYCZY pewnym siebie werdyktem** |
| skutek | nie dowiesz się, czy dźwignia zadziałała | **dowiesz się czegoś, co NIE JEST PRAWDĄ** |
| kolizja | — | `score=0.00` jest **nieodróżnialne od PRAWDZIWEJ porażki 0.00**, którą już raz mieliśmy (submisja **57629847**, c45: `concurrency=120` vs `MAXREQ=10`) |

Martwy alarm kosztuje utraconą informację. **Głośno-mylący instrument kosztuje błędną decyzję** —
a decyzja na 1.11 będzie podejmowana **na podstawie logu**.

**Naprawa (2 linie):** bramka świadoma baseline + `None` zamiast `max(1.0, …)`. W moim buildzie to
FIX 4 i FIX 5.

**Zestawienie: 10 instancji klasy.** 1 `SCOPE=run` · 2 `concurrency=120` vs `MAXREQ=10` ·
3 `EXPOSE_UNDO` unset · 4 `official_110()` · 5 `commit(plan)` · 6 `dead_skip`/`pass_index` ·
7 guard `GAME_OVER`/`raw` · 8 alarm `< 1.5` · **9 wejście ukryte w submisji** · **10 instrument
głośno-mylący**.

---

## 4. Defekty WDROŻENIOWE — zmierzone, nie wyczytane

| pakiet | `code_file` | plik w katalogu | `id` (slug) | werdykt |
|---|---|---|---|---|
| **v16 Gemma** `0ef24651` | `arc3-duck-v13.ipynb` | **`arc3-duck-v16.ipynb`** | `petersharps/arc3-duck-v13-4-unified` | ❌ **code_file NIE ISTNIEJE** + ❌ **slug = kernel v13.4 Smak** |
| **v15 Gemma** `07bf05e0` | `arc3-duck-v13.ipynb` | **`arc3-duck-v15.ipynb`** | `petersharps/arc3-duck-v13-3-arena` | ❌ **code_file NIE ISTNIEJE** + ❌ **slug = kernel v13.3-arena Smak** |
| v13.4 Smak `f04c3e73` | `arc3-duck-v13.ipynb` | `arc3-duck-v13.ipynb` ✅ | `…/arc3-duck-v13-4-unified` | ✅ |
| v13.5 Smak `63ede621` | `arc3-duck-v13.ipynb` | `arc3-duck-v13.ipynb` ✅ | `…/arc3-duck-v13-5-consensus` | ✅ |
| v15 a450 `8d96c68f` | `arc3-duck-v15.ipynb` | `arc3-duck-v15.ipynb` ✅ | `…/arc3-duck-v15` | ✅ |

**Kolizję sluga znalazł a450b00f** („push nadpisze tamten kernel") — **potwierdzam.**
**Brakującego `code_file` NIE znalazł nikt** — to nowe ustalenie tej tury.

**Kolejność zagrożenia jest odwrotna niż intuicja:**
- `code_file` ❌ → `kaggle kernels push` **pada głośno**. Blokuje submisję w ostatniej chwili, ale
  **nie niszczy niczego**.
- slug ❌ → push **przechodzi i NADPISUJE CUDZY KERNEL**. **Ciszej i groźniej.** A ponieważ
  „ostatnie 2 submisje są aktywne", nadpisanie kernela, z którego ktoś planuje submisję,
  może kosztować slot.

To jest **ta sama klasa błędu, za którą użytkownik zganił nas 2026-10-16**: *„wrzuciles ten sam plik
co w nocy!!!"* → używać **rozróżnialnych nazw bundli**. Zasada istnieje w naszych regułach od dwóch
tygodni i **dwa najnowsze pakiety ją łamią**.

---

## 5. Macierz porównawcza pięciu pakietów (wszystko sprawdzone w kodzie)

| cecha | v15-a450 `8d96c68f` | v13.4 `f04c3e73` | v13.5 `63ede621` | **v16 `0ef24651`** | **c87-v16f (mój)** |
|---|---|---|---|---|---|
| `ARC3_OPENER_COMMIT_HINT="1"` | ❌ **BRAK** | ✅ | ✅ | ✅ | ✅ |
| `ESCALATE_ACTIONS=20` | ✅ | ✅ | ✅ | ✅ | ✅ |
| cap 2 na poziom | ✅ (default **2** w patchu) | ✅ (default **0**, ustawione w env) | ✅ | ✅ | ✅ |
| reguła względna (0007/0008) | ✅ zawsze, **bez kill-switcha** | ✅ env | ✅ env | ✅ env | ✅ env |
| **self-pace (0009) — żywa w rerunie** | ❌ | ❌ | ❌ | ✅ | ✅ |
| sonda widoczności baseline | ❌ | ❌ | ✅ kom. 38 | ✅ kom. 39 | ✅ kom. 39 |
| ważone pokrycie (sufit wyniku) | ❌ | ❌ | ✅ kom. 38 | ✅ kom. 39 | ✅ kom. 39 |
| martwy alarm `< 1.5` | ❌ kom. 36 | ❌ kom. 38 | ❌ kom. 38 | ❌ kom. **39 i 40** | ✅ **4.357 + drabinka** |
| bramka `NO-GO 29.02` głośno-myląca | ❌ kom. 35 | ❌ kom. 37 | ❌ kom. 37 | ❌ kom. 38 | ✅ **świadoma baseline** |
| `depth_budget_used_pct` | ❌ | ❌ | ❌ | ❌ | ✅ **None** |
| `code_file` istnieje | ✅ | ✅ | ✅ | ❌ | ✅ |
| slug własny | ✅ | ✅ | ✅ | ❌ | ✅ `arc3-duck-v16-c87f` |
| docstring 0009 | — | — | — | ❌ 27/16 | ✅ **22/14** |
| **bramka `--strict`** | **3 KRYTYCZNE** | **3 KRYTYCZNE** | **3 KRYTYCZNE** | **4 KRYTYCZNE** | **✅ 0 KRYTYCZNYCH** |

**Zachowanie w RERUNIE (to jedyna kolumna, która naprawdę się liczy):**

| pakiet | reguła eskalacji w submisji | nudge / przedwczesne / % puli |
|---|---|---|
| v15-a450, v13.4, v13.5 | floor 20 + cap 2 (względna martwa) | **42 / 26 / 4,33 %** |
| **v16, c87-v16f** | **self-pace 1,5×mediana + cap 2** | **22 / 14 / 2,27 %** |

**⚠️ Pułapka, którą warto zapamiętać: smoke ĆWICZY INNĄ GAŁĄŹ niż rerun.** W smoke'u baseline jest
widoczny ⇒ `if b > 0` zachodzi ⇒ **wykonuje się reguła WZGLĘDNA**. W rerunie baseline jest ukryty ⇒
**wykonuje się self-pace**. Czyli smoke v16 **nie testuje ścieżki, która pójdzie do punktacji**.
To nie jest błąd Gemmy (tak działa silnik), ale **musi być zapisane**, żeby ktoś nie uznał
zielonego smoke'a za dowód, że self-pace działa.

---

## 6. Nowe pomiary przepustowości — i KOREKTA mojego własnego modelu

Policzyłem wprost z `history` / `actions_per_level` / `final_wallclock_seconds`:

| wielkość | **r085** (c45) | **r093** (v11) | r019 (stara linia) | 7911 (r013/15/18) |
|---|---|---|---|---|
| akcji / grę | 212,6 | 231,5 | 206 | — |
| wywołań / grę | 47,1 | 46,9 | 47,4 | — |
| tokenów / grę | **141 719** | **152 196** | — | 186 200 (budżet) |
| **a/call (ważone)** | **4,514** | **4,936** | **4,357** | **4,61** |
| **tok/akcję** | **666,6** | **657,4** | 841,2 | 853 |
| tok/wywołanie | 3008,9 | 3245,1 | 3664,6 | — |
| tok/s na grę | 50,4 | 61,0 | — | — |
| **ms/token na grę** | **19,83** | **16,41** | 17,2 | — |
| wall s / grę | 2810 | 2497 | 2945 | — |

**TRZY RZECZY Z TEGO WYNIKAJĄ:**

**(a) KONWERGENCJA CZTERECH SESJI NA a/call.** 4,357 (c87, r019) · 4,514 (r085) · 4,936 (r093) ·
**4,61 (7911, r013/r015/r018)**. Rozrzut **±6 %** wokół 4,6. **7911 w `1541d082` skorygował swoją
własną liczbę z 1,00 na 4,61** — czyli cztery niezależne sesje zmierzyły **tę samą wielkość**.
⇒ **próg alarmu 1,5 (notebook) i bramka 1,8 (dokument GO/NO-GO Smak §19) leżą 2,4–2,9× PONIŻEJ
najniższej kiedykolwiek zmierzonej wartości.** Martwy alarm #8 jest teraz potwierdzony na
**czterech runach**, nie na jednym.

**(b) KOREKTA MOJEGO MODELU (12. self-korekta).** W `V14-V15-I-WARSTWA-WERYFIKACJI.md` użyłem
`tok/akcję = 841,2` z r019. **r019 to STARA LINIA.** Obecna linia mierzy **666,6 (r085)** i
**657,4 (r093)** — czyli **mój model przeszacowywał tok/akcję o 27 %**. Podstawienie `ms/token`
17,2 i tok/akcję 841 dawało mi 203 akcje/grę; przy zmierzonych 666 i uczciwym udziale 2945 s
wychodzi **~259**, a r093 skalowany do 2945 s daje **273**. **Model jest wewnętrznie spójny**
(tożsamość `akcje = wall×1000/(ms/tok × tok/akcję)` odtwarza 212,6 i 231,5 **dokładnie**),
ale **wejścia wziąłem ze złego runu.**

**(c) SPÓJNOŚĆ Z serve.log.** 10 gier × 50,4–61,0 tok/s = **504–610 tok/s**, a mój
`parse_serve_log.py` na tych samych runach zmierzył **584,2 / 663,0 tok/s** po stronie serwera.
⇒ **concurrency 10 naprawdę biegło 10 grami równolegle.** Niezależne potwierdzenie, że poprawka
concurrency (0.00 → 23.89) działa tak, jak myśleliśmy.

---

## 7. SUFIT WYNIKU policzony mechanicznie — i dlaczego „+1,1 poziomu ⇒ 50" jest **sufitem**, nie wynikiem

Reguła punktacji (`taaf/game.py::_compute_final_score`, L385-414):
`score_gry = min( Σ s_k·w_k / Σ w_k , 100 × Σ w_k[ukończone i s_k>0] / Σ w_k )`, a wynik końcowy to
**średnia po grach**. Czyli **sufit = średnia per-gra pokryć ważonych**, gdzie
`pokrycie = c(c+1) / (n(n+1))` dla `c` ukończonych z `n` poziomów.

**⚠️ Mój pierwszy rachunek był zły:** zpoolowałem `Σ done_w / Σ w` po wszystkich grach (26,71 %) —
a wynik to **średnia wyników gier**, więc trzeba uśredniać **pokrycia per gra**. Po poprawce:

| | **r085** | **r093** |
|---|---|---|
| **SUFIT** (średnia pokryć per gra) | **29,79** | **23,45** |
| zmierzony wynik | 26,78 | 18,55 |
| **wykorzystanie sufitu** | **89,9 %** | **79,1 %** |
| poziomów / grę | 3,20 z 6,90 | 2,70 z 6,90 |
| akcji / grę | 212,6 | 231,5 |
| **akcji na zdobyty poziom** | **66,4** | **85,7** |

**`score ≤ sufit` zachodzi w obu runach** ✅ — i to jest **piąte niezależne potwierdzenie reguły
30/30** (po Gemmie, 7911, `_compute_final_score` i mojej lekturze L385-414).
**Wykorzystanie 89,9 % / 79,1 %** potwierdza zbieżność czterech sesji: „efektywność na ukończonych
poziomach 86–90 %".

### 7.1 Ile naprawdę trzeba, żeby **WYNIK** (nie sufit) wyniósł 50

| dodane poziomy/grę | sufit r085 | **oczekiwany wynik** (× 89,9 %) | sufit r093 | **wynik** (× 79,1 %) |
|---|---|---|---|---|
| +1,0 | 46,27 | **41,6** | 37,40 | 29,6 |
| **+1,1** | **47,82** | **43,0** | 39,01 | 30,9 |
| +1,5 | 54,34 | **48,9** | 45,82 | 36,2 |
| +2,0 | 63,25 | **56,9** | 55,19 | 43,7 |

**❗„+1,1 poziomu na grę to cała droga do 50" (7911 `724189b2`, Gemma `STATUS.md`) jest prawdziwe
dla SUFITU (47,82), ale NIE dla WYNIKU.** Przy zmierzonym wykorzystaniu 89,9 % daje **~43,0**.

**Żeby WYNIK = 50:**

| run | potrzebny sufit | **potrzebne poziomy/grę** | mnożnik głębokości | akcji/grę | **wymagany mnożnik batchingu** |
|---|---|---|---|---|---|
| **r085** (najlepszy z dwóch) | 55,6 | **+1,57** | **1,49×** | ~317 | **a/call 4,514 → 6,73 = 1,49×** |
| r093 | 63,2 | +2,70 | 2,00× | ~460 | a/call 4,936 → ~9,4 = 1,90× |

**Czyli: 50 pkt wymaga 1,49×–1,90× batchingu, a rozstrzał bierze się z DWÓCH niestabilnych ogniw.**

### 7.2 REFUTACJA: `akcje/grę → wynik` **nie jest funkcją**

| run | akcji/grę | poziomów/grę | **wynik** |
|---|---|---|---|
| r085 (c45) | **212,6** | 3,20 | **26,78** |
| r093 (v11) | **231,5** (+8,9 %) | 2,70 | **18,55** (−30,7 %) |

**WIĘCEJ AKCJI, MNIEJ PUNKTÓW.** Dwa nasze własne smoke'i, te same 10 gier.
Równie niestabilne jest drugie ogniwo: **akcji na zdobyty poziom 66,4 (r085) vs 85,7 (r093)
— rozrzut 29 %.**

**Wniosek, który musi wejść do każdego planu:** łańcuch
`batching → akcje/grę → poziomy/grę → pokrycie → wynik`
ma **DWA ogniwa o zmierzonej niestabilności 29 % i niemonotoniczności**. Każda projekcja typu
„X akcji/grę ⇒ Y punktów" niesie **co najmniej ±8 pkt błędu modelu** — **zanim** doliczymy szum
między losowaniami σ ≈ 2,5–3,9 i próg istotności +5 pkt.

**To jest arytmetyczna odpowiedź na „zbuduj coś, co da 50+":** nie chodzi o to, że się nie da.
Chodzi o to, że **przy tym błędzie modelu i 3 slotach nie odróżnimy „zadziałało" od „poszczęściło
się"** — a 7911 prognozuje z dopasowania `akcje→wynik` (253 akcji ⇒ 50), które mój łańcuch
mechaniczny (oparty na oficjalnej regule punktacji i odtwarzający zmierzony wynik) wycenia na
**~295–320 akcji/grę**. Różnica **17–25 %**. **Nie twierdzę, że 7911 się myli** — ich dopasowanie
może łapać efekt, którego mój łańcuch nie ma (więcej akcji może też podnosić *wykorzystanie*
sufitu, a ja je trzymam stałe). **Twierdzę, że rozstrzał między dwoma niezależnymi modelami jest
większy niż efekt, który chcemy zmierzyć.**

---

## 8. Ocena `V17-COMPARE` (7911) — zgoda, krytyka, i jedno potwierdzenie

**✅ ZGADZAM SIĘ I UZNAJĘ ZA NAJWAŻNIEJSZY WKŁAD TURY: stosunek 24 : 1.**
Cały spór o eskalację (10 → 20 → względna → self-pace) jest wart **2 akcje/grę = 0,92 % budżetu**;
hint na openerze jest wart **48–50 akcji**. **Moja replikacja to potwierdza z innej strony:**
różnica między najdroższą a najtańszą **żywą w rerunie** regułą eskalacji to 42 − 22 = 20 nudge'ów
= 2 920 tok = **2,06 % puli jednej gry**. Hint operuje na **akcjach na wywołanie**, czyli w
mianowniku `tok/akcję`, który decyduje o **wszystkich** akcjach. **7911 ma rację, że dwie gałęzie
spędziły dzień na optymalizacji rzeczy wartej 1 %.**

**✅ POTWIERDZAM ich krytykę bramki Gemmy/Smak `a/call ≥ 1,8`.** Zapisane runy: 4,57 / 5,20 / 5,38
(7911) oraz **4,357 / 4,514 / 4,936** (moje). **Najgorsza zmierzona wartość jest 2,4× powyżej
progu** ⇒ bramka przejdzie, nawet gdyby hint nie zrobił nic. To instancja #8 w dokumencie
GO/NO-GO, a nie tylko w notebooku (gdzie próg wynosi 1,5).

**❌ KRYTYKUJĘ ich własną bramkę `a/call ≥ 6,0`.** Jest **surowsza niż ich własny próg
wystarczalności**: w ich tabeli **5,62 akcji/generację (połowa efektu hinta) daje już 266 akcji/grę
≥ 253**, czyli wg ich modelu **wystarcza na 50** — a bramka 6,0 powiedziałaby **NO-GO**.
**Bramka binarna myli „zadziałało" z „wystarczyło".** Poprawna forma to **drabinka**, nie próg —
i taką wstawiłem w FIX 3:

```
a/call < 4,357        -> REGRESJA (hint nie zadziałał albo się cofnął)
4,357 <= a/call < 5,7 -> batching CZĘŚCIOWY; ~250-300 akcji/grę
a/call >= 5,7         -> batching ZADZIAŁAŁ; >= 300 akcji/grę
```

Drabinka **zawsze coś drukuje** (więc nie jest martwa) i **rozróżnia trzy stany** (więc nie jest
binarna). 7911 słusznie zauważył, że bramka musi **móc paść** — ale bramka, która **musi** paść
przy połowicznym sukcesie, wyrzuca informację wartą ~35 pkt.

**✅ POTWIERDZAM ich tabelę dwóch v15** — niezależnie sprawdziłem, że a450 **nie ustawia**
`ARC3_OPENER_COMMIT_HINT` (brak w dicie env komórki 1; zmienna pojawia się tylko w komórce 6, czyli
w źródle harnessu jako `_get_env_bool(..., False)`). **Więc v15-a450 nie ma największej dźwigni.**
a450 sam to przyznaje w addendum: *„Moje duck-v15 przescigniête przez oba (brak hinta openerowego)"*.

**⚠️ Rozbieżność mianownika:** 7911 liczy budżet **186 200 tok/grę**; zmierzona **wydana** pula to
**141 719 (r085)** / **152 196 (r093)**. Gemma używa ~146 000 (bo 154 × 146 / 0,153 = 146 300) —
**czyli Gemma i ja jesteśmy zgodni co do 3 %**, a 7911 ma mianownik o **24–31 % większy**.
To nie zmienia **rankingu** reguł (wszystkie liczone tym samym mianownikiem), ale zmienia
**procenty**: te same 154 nudge'ów to 15,87 % u mnie i u Gemmy, a 12,1 % u 7911.
**Nie rozstrzygam, czy 186 200 to budżet przydzielony, a 141 719 wydany** — jeśli tak, oba są
poprawne i trzeba to tylko nazwać. **Oznaczam jako rozbieżność, nie jako błąd.**

---

## 9. MOJA NAJLEPSZA WERSJA: **`c87-v16f`** = duck-v16 + 6 poprawek

### 9.1 Dlaczego bazą jest v16, a nie coś własnego

Trzy powody są **bez zmian** od poprzedniej tury i wszystkie twarde: nie mam bundla r033,
`arcengine`, GPU ani `cargo` (2 CPU / 3,9 GB); nie przetestuję przed spaleniem slotu, a zostały **3**;
v16 już dziedziczy certyfikację v13.3-arena. **Do tego doszedł czwarty, nowy:** v16 jest **jedynym**
pakietem, którego reguła eskalacji jest **żywa w rerunie** (§1.2, §5) — a to potwierdziłem
w kodzie silnika, nie w README.

### 9.2 Sześć poprawek (wszystkie weryfikowalne **statycznie** — bez bundla, bez GPU)

| # | warstwa | co | gdzie |
|---|---|---|---|
| 1 | **L7** | `code_file`: `arc3-duck-v13.ipynb` → `arc3-duck-v16.ipynb` | `kernel-metadata.json` |
| 2 | **L7** | slug: `petersharps/arc3-duck-v13-4-unified` → `petersharps/arc3-duck-v16-c87f` | `kernel-metadata.json` |
| 3 | **L1** | alarm `< 1.5` → **`< 4.357` + druk bezwarunkowy z drabinką celów** | komórki **39 i 40** |
| 4 | **L6** | bramka `NO-GO 29.02` → **świadoma baseline** (`N/A` gdy `actions_need == 0`) | komórka **38** |
| 5 | **L6** | `depth_budget_used_pct` → **`None`** zamiast `max(1.0, …)` + zabezpieczony druk | komórka **38** |
| 6 | — | docstring **27/16 → 22/14** | `patches/0009-*.patch` + `tests/fixtures/tool_agent_0009_post.py` |

**Build:** `arc3-handoff/tools/build_c87_v16f.py` (247 linii). **Każda poprawka jest ASERTOWANA** —
jeśli wzorzec nie pasuje, skrypt **pada**, nie produkuje cichego pół-pakietu:

```
FIX 1 (L7 code_file) : 'arc3-duck-v13.ipynb' -> 'arc3-duck-v16.ipynb'  [poprzedni NIE ISTNIAŁ]
FIX 2 (L7 slug)      : 'petersharps/arc3-duck-v13-4-unified' -> 'petersharps/arc3-duck-v16-c87f'
FIX 3 (L1 alarm)     : poprawiono w 2 komórkach (oczekiwane 2: sonda pokrycia + sonda rosteru)
FIX 4 (L6 bramka)    : poprawiono w 1 komórkach (oczekiwane 1)
FIX 5 (L6 wskaźnik)  : definicja 1x + druk 1x (oczekiwane 1 i 1)
FIX 6 (docstring)    : 0009-arena-self-pace.patch — 27/16 -> 22/14
FIX 6 (docstring)    : tool_agent_0009_post.py — 27/16 -> 22/14
```

### 9.3 Zweryfikowałem własny build trzema sposobami

**(a) Bramka.** `verify_config_liveness.py --package --strict`:

| pakiet | ustaleń | **KRYTYCZNYCH** |
|---|---|---|
| v16 (oryginał Gemmy) | 8 | **4** |
| **v16-c87f (mój)** | **4** | **✅ 0** |
| v13.5-consensus | 6 | 3 |
| v13.4-unified | 7 | 3 |
| v15-a450 | 7 | 3 |

**(b) Zero regresji składni.** 41 komórek przed i po; **różnią się dokładnie 3: 38, 39, 40** — te,
które chciałem. Jedyna komórka, która nie parsuje jako Python (kom. 6), to
`%%writefile /kaggle/harness-changes.patch` — **tekst diff, nie kod**, i jest **bajt w bajt
identyczna** przed i po.

**(c) Metadata.** `id = petersharps/arc3-duck-v16-c87f`, `code_file = arc3-duck-v16.ipynb`,
plik **istnieje**.

### 9.4 ⚠️ Dwa fałszywe pozytywy, które mój weryfikator dał **na moim własnym buildzie**

Po pierwszym przebiegu `c87-v16f` dostał **1 KRYTYCZNE** — na linii, którą **sam właśnie poprawiłem**.
Przyczyna: L6 dopasowywał `_gate … <= 29.02` **bez sprawdzania, czy komórka zawiera strażnika**
widoczności baseline. Poprawiłem: `GUARD_RX` rozpoznaje `actions_need == 0` /
`base_actions_per_level is None` / `baselines_hidden` / `baseline_available` i **degraduje do INFO**.
Analogicznie L6b: flaguję **tylko** konstrukcję `max(1.0, _mean("actions_need"))`, a nie każdą
wzmiankę o `depth_budget_used_pct` — dzięki czemu znika też duplikat (definicja + druk).

**Zasada, którą już raz sformułowałem i znowu się potwierdziła: narzędzie, które daje fałszywe
pozytywy, jest gorsze niż brak narzędzia, bo uczy ignorować raport.** Gdybym zostawił to
KRYTYCZNE, bramka `--strict` blokowałaby **poprawiony** pakiet — czyli dokładnie odwrotnie niż ma.

**Poprawiłem też własną sprzeczną rekomendację:** L4 radziło „próg WZGLĘDNY `max(20, 1.2×baseline)`",
czyli dźwignię, którą **L5 w tym samym przebiegu flaguje jako martwą w rerunie**. Teraz L4 odsyła
do self-pace i cytuje oba pomiary.

---

## 10. Co **wbudowałem** w weryfikator (7 kontroli zamiast 4)

`tools/verify_config_liveness.py`, **515 → 778 linii**, czysty Python 3, biblioteka standardowa.

| kontrola | co łapie | nowa? |
|---|---|---|
| **L1** ŻYWOTNOŚĆ INSTRUMENTU | próg poniżej zmierzonej bazy → gałąź nieosiągalna | #8 |
| **L2** DOMYŚLNA WARTOŚĆ ENV | default + walidator każdej zmiennej env | #1 #3 #4 |
| **L3** OSIĄGALNOŚĆ | warunki sięgające po zmienne stałe w rerunie | #6 |
| **L4** SPÓJNOŚĆ MIĘDZYWARSTWOWA | concurrency ≤ MAXREQ · cap vs uczciwy udział · `ESCALATE` vs **zmierzony** rozkład | #2 #5 |
| **L5** WEJŚCIE UKRYTE W SUBMISJI | zależność od `base_actions_per_level` **bez żywego zamiennika** + brak sondy widoczności | **✅ #9** |
| **L6** INSTRUMENT GŁOŚNO-MYLĄCY | bramka/wskaźnik, którego wejście jest **zerem z konstrukcji** w submisji; **rozpoznaje strażnika** | **✅ #10** |
| **L7** WDROŻENIOWOŚĆ PAKIETU | `code_file` istnieje? slug należy do **tego** pakietu? (`--package DIR`) | **✅ nowa** |

**L5 celowo szuka WZORCA, nie nazwy zmiennej:** a450 nie używa `ARC3_ESCALATE_RELATIVE` w ogóle
(reguła zawsze włączona, `pc_escalate_at` + `self._arc3_base_actions`), więc kluczowanie po nazwie
env **przegapiało** ich pakiet. Pierwsza wersja tak robiła i dała v15-a450 tylko **2** KRYTYCZNE
zamiast 3 — **poprawione**.

**L7 celowo odnosi się do nazwy NOTEBOOKA, nie katalogu:** katalog bywa scratchem audytora
(zbudowałem `/tmp/pkg/duck-v15-a450`), a regex `v\d+(?:[\.-]\d+)?(?:[\.-][a-z]+)?` wyciągnął z tego
`v15-a` i oflagował **poprawny** slug `arc3-duck-v15` jako kolizję. **Fałszywy pozytyw z mojej
własnej konwencji nazewniczej** — naprawione przez porównanie z `code_file`/rzeczywistym `.ipynb`.

**Dodatkowo:** deduplikacja ustaleń po `(kontrola, komórka, problem)` — ta sama wada zgłaszana
z definicji i z druku to **jedno** ustalenie, nie dwa.

---

## 11. Rekomendacja

### 11.1 Na slot 31.10

**`c87-v16f`** = duck-v16 Gemmy + 6 poprawek (§9.2), pod warunkiem że **ktoś z bundlem r033**
przepuści go przez `verify_v13.py` (9/9 patchy `git apply` + kompilacja drzewa + testy na
spatchowanym drzewie). **Ja tego zrobić nie mogę** i nie udaję, że zrobiłem — a450b00f zrobił to
dla v16 (`52b709ee`: *„9/9 patchy git apply na czystym r033, drzewo sie kompiluje, testy self-pace
przechodza"*), a **moje 6 poprawek nie dotyka ani jednego patcha harnessu** — tylko
`kernel-metadata.json`, trzy komórki notebooka i dwa docstringi. **Ryzyko utraty certyfikacji jest
więc bliskie zeru, ale „bliskie zeru" to nie „zweryfikowane".**

Konfiguracja bez zmian: `PLAN_COMMIT=1` · `ESCALATE_ACTIONS=20` · `RELATIVE=1` · `RATE=1.2` ·
`MAX_PER_LEVEL=2` · **`SELF_PACE=1` · `SELF_RATE=1.5` · `SELF_MAX=120`** ·
`OPENER_COMMIT_HINT=1` · `WINPATH=1` · `DEAD_SKIP=1` · `LEVEL_TOKEN_CAP=0` · concurrency 10 ·
obie sondy ON.

**Jeśli a450b00f albo Smak mają bundla: wystarczy `build_c87_v16f.py` + `verify_v13.py`.**
Jeśli nie — **v13.5-consensus jest najlepszym pakietem, który da się wypchnąć bez poprawek**
(własny slug ✅, `code_file` ✅, sonda widoczności baseline ✅, ważone pokrycie ✅), kosztem
**42 / 26 / 4,33 %** zamiast **22 / 14 / 2,27 %** w rerunie — czyli **2,06 pp puli jednej gry**.
**To jest cena braku self-pace i jest ona MAŁA.** Nie warto dla niej ryzykować nieskładanego pakietu.

### 11.2 Czego NIE brać

- **v15-a450** — **brak hinta openerowego**, czyli brak jedynej dźwigni o skali ≥ celu (24:1).
  a450 sam to przyznaje.
- **v13.4** — brak sondy widoczności baseline i brak pokrycia, czyli po submisji **nie dowiemy się**,
  czy reguła względna była martwa. v13.5 to naprawia bez żadnego kosztu.
- **v16 i v15 Gemmy bez poprawek 1 i 2** — `kaggle kernels push` albo padnie (`code_file`),
  albo **nadpisze cudzy kernel** (slug).

### 11.3 Ranking działań

1. **Wypchnąć `c87-v16f`** (albo v13.5, jeśli nikt nie zweryfikuje) na slot **31.10** — **po GO użytkownika**, BEZPIECZNIK obowiązuje.
2. **Bramka przed każdym pushem:** `verify_config_liveness.py <nb> --package <dir> --strict` → **0 KRYTYCZNYCH** (~10 s).
3. **Naprawić asercję** w `test_self_pace.py`: `pace[:2] == (22, 14)` zamiast `<`.
4. **Przeczytać z logu submisji** (w tej kolejności): `baseline=yes|no` (rozstrzyga §1.1) →
   `mean_coverage` (sufit) → **`mean_a_per_call` z drabinką** (rozstrzyga batching) →
   `duplicate_bases` (rozstrzyga wartość `WINPATH`) → `budget_probe`.
5. **1.11** — rozgałęzienie wg pkt 4. **2.11** — select best.

### 11.4 Prognoza (bez zmian co do istoty, z lepszymi liczbami)

**Oczekiwanie ~28–31** · **cel srebro ≈ 32,33** · **50 pkt wymaga +1,57 poziomu na grę
(1,49× głębokości, ~317 akcji/grę, 1,49× batchingu) przy wykorzystaniu sufitu 89,9 % —
albo +2,70 poziomu (2,00×) przy wykorzystaniu 79,1 %.**

**Stanowisko bez zmian:** *„arytmetycznie w zasięgu, ale NIEWERYFIKOWALNE w 3 slotach; obstawianie
tego to hazard, nie plan"* — **i §7.2 właśnie dodał do tego twardy powód**: dwa ogniwa łańcucha
`batching → wynik` mają **zmierzoną** niestabilność 29 % i **zmierzoną** niemonotoniczność, więc
błąd modelu (±8 pkt) jest **większy** niż efekt, który chcemy przypisać (+5 pkt próg istotności).

---

## 12. Granice tego dokumentu

- **Nie mam bundla r033, `arcengine`, GPU ani `cargo`.** Niczego nie certyfikowałem `git apply`
  ani nie uruchomiłem na silniku. **Wyjątek:** uruchomiłem `tests/test_self_pace.py` Gemmy — jest
  **offline** (fixture + hardkodowana tabela r085), więc działa w moim sandboxie.
- **Nie wysłałem i nie wypchnąłem niczego na Kaggle.** BEZPIECZNIK (`cce4b32c`) obowiązuje;
  `c87-v16f` istnieje jako **skrypt budujący + przepis**, nie jako submisja.
- **Nie dotknąłem `a450b00f`, `Gemma-konkurs`, `Smak-Domu-Konkurs`, `7911f950`.** Wszystkie odczyty
  przez `gh api`, read-only.
- **`r050` nie zdekodował się** (blob → `base64: invalid input`), więc w §1.1 jest 5 runów, nie 6.
- **`a/call` po włączeniu hinta openerowego NIE ZOSTAŁ ZMIERZONY przez nikogo** — Gemma pisze to
  wprost w `STATUS.md`, a 7911 cytuje pomiar **upstream** (3,91–5,43 → 6,73–6,91), nie nasz.
  **Największa dźwignia ma niepolski, niepobraną-przez-nas liczbę.** FIX 3 istnieje właśnie po to,
  żeby pierwszy submit z hintem **zmierzył** ją u nas.
- **Mój błąd z §2.4** (14/9 zamiast 22/14) jest **wycofany i opisany**, a nie usunięty — żeby reguła
  „uruchom ich kod, nie reimplementuj" miała udokumentowany powód.
- **Rozbieżność mianownika budżetu** (186 200 u 7911 vs 141 719 / 152 196 zmierzone) jest
  **oznaczona, nie rozstrzygnięta** (§8).
