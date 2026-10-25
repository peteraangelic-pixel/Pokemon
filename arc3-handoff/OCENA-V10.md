# Ocena pakietu `arc-v10` (sesja `e499c604-b61e-4a81-b5ea-33f729bccc1f`)

**Data:** 2026-10-25 · **Autor:** sesja `arena/c87f7a48-pokemon`
**Co przeczytane (read-only przez `gh api`):** `arc-agi-3/e499c604-…/arc-v10/README.md`,
`DECYZJE-I-RYZYKA.md`, lista 17 plików pakietu, `ops/results/r075`–`r080`, oraz
**empiryczny test zachowania `%%writefile`** na IPython 9.17.1.

Werdykt w jednym zdaniu: **główne znalezisko v10 („v9 i v7 w ogóle by nie ruszyły") jest
OBALONE przez dowód produkcyjny i przez mechanizm, który zmierzyłem — ale `commit(plan)`
z weryfikacją każdego kroku jest najlepszą rzeczą, jaka powstała w tym projekcie, i jest
dokładnie odpowiedzią na ryzyko, które wczoraj zgłosiłem przy profilu `deep`.**

---

## 1. Twierdzenie v10 nr 1: „v9 (i v7) w ogóle by nie ruszyły" — OBALONE

### Co twierdzi v10 (`DECYZJE-I-RYZYKA.md` §1, „najważniejsze znalezisko")

```
duck-v9/arc3-duck-v9.ipynb  →  komórka 5, źródło: 498 799 znaków
duck-v7/arc3-duck.ipynb     →  komórka 4, źródło: 498 799 znaków  (ta sama wartość)
```
> „To środek hunka. `git apply --check` na tak wyekstrahowanym pliku:
> `error: corrupt patch at line 10086`. Komórka 10 robi `subprocess.run([... "git apply" ...],
> check=True)` — czyli `CalledProcessError` **przed** startem serwera i przed pierwszą grą."

oraz (`README.md`): „Każdy slot na v9 spaliłby się w ~2 minuty, **bez żadnego logu z gry**."

### Dowód produkcyjny, że jest odwrotnie

**r075-auto-submit** (25.10 12:28:04 UTC):
```
status[0] rc=0  petersharps/arc3-duck-c45  has status "KernelWorkerStatus.COMPLETE"
Submission ref: 57629847 -> PENDING
```

**r076-kernel-output** (25.10 12:36:38 UTC), `kernels output petersharps/arc3-duck-c45`, `rc=0`:
```
Downloading .per_game_cards.pkl                       (583 337 B)
Downloading cn04-2fe56bfb_p0_events.jsonl
Downloading dc22-fdcac232_p0_events.jsonl
Downloading g50t-5849a774_p0_events.jsonl
Downloading ka59-38d34dbb_p0_events.jsonl
Downloading ls20-9607627b_p0_events.jsonl
Downloading m0r0-492f87ba_p0_events.jsonl
Downloading s5i5-18d95033_p0_events.jsonl
Downloading sc25-635fd71a_p0_events.jsonl
Downloading su15-1944f8ab_p0_events.jsonl
Downloading tn36-ef4dde99_p0_events.jsonl   (+ _p0_viewer_data.json dla każdej)
```

**10 gier z logami zdarzeń.** Dokładnie te same 10 co w r019. Kernel `arc3-duck-c45` —
którego notebook **nie był zmieniany od 24.10 21:55** (historia: jeden commit `9c05c701`),
więc r075 uruchomił dokładnie tę wersję z „zepsutym" patchem — **zagrał i zostawił artefakty**.
Dodatkowo istnieją `_p0_viewer_data.json`, czyli warstwa `viewer` działa.

`c45` jest bazą v9 (`src/base-c45.ipynb`, 648 078 B — bajt w bajt z
`duck-c45/arc3-duck-c45.ipynb`), a komórka patcha ma w obu **identyczne 498 799 znaków**.
Skąd więc `COMPLETE`?

### Mechanizm — zmierzyłem go, a nie zgadłem

Komórka 4 w c45 to `%%writefile /kaggle/harness-changes.patch`, a jej `source` w JSON-ie
**faktycznie nie kończy się nową linią** (ostatni znak to `,`; 498 799 znaków — pomiar v10
jest dokładny). Kluczowe jest jednak, co z tym robi Jupyter:

```python
# IPython 9.17.1, pełny potok (run_cell z magic) — tak to wykonuje Jupyter
wejście: 3 znaki, kończy się \n: False
plik:    4 znaki, kończy się \n: True
=> PEŁNY POTOK IPYTHON DOPISAŁ NOWĄ LINIĘ: True
```

Dla porównania — to samo wywołane przez `run_cell_magic` (czyli **z pominięciem** transformatora
wejścia) nowelii **nie** dopisuje. To jest cała różnica:

| sposób wyekstrahowania patcha | końcowa nowa linia | `git apply --check` |
|---|---|---|
| odczyt `source` z JSON-a i zapis do pliku (**tak zrobił v10**) | **BRAK** | ✗ `corrupt patch at line 10086` |
| `%%writefile` w wykonującym się notebooku (**tak robi Kaggle**) | **JEST** | ✓ przechodzi |

Sprawdziłem też sam próg na syntetycznym patchu: bez końcowego `\n` → `error: corrupt patch at
line 8`; z `\n` → `Checking patch … OK`. Czyli **cały błąd to jedna brakująca nowa linia**,
a nie urwany hunk.

**To jest dokładnie ta pułapka, którą sam wcześniej zdiagnozowałem** i zapisałem w
`FAKTY-I-POMIARY.md`: „brak końcowej nowej linii ⇒ `corrupt patch at line 10086`; diagnozuj po
ROZMIARZE (498 779 vs 498 780 B)". Ten sam komunikat, ta sama przyczyna. v10 zobaczył ten sam
objaw i wyciągnął z niego wniosek o urwanym hunku oraz o tym, że notebooki nigdy nie ruszą.

### Druga część twierdzenia: „brakuje 8 plików, m.in. całych zmian `viewer/*`"

Policzyłem zawartość komórki 4:

```
plików w patchu c45: 16
pod ARC3-Inference/  : 16
poza ARC3-Inference/ : 0
plików z viewer/     : BRAK
```

A cell 9 aplikuje tak:
```python
subprocess.run(["git","apply","--include=ARC3-Inference/*","-v","/kaggle/harness-changes.patch"],
               cwd=f"{BUNDLE_DIR}/src", check=True)
```

**`--include=ARC3-Inference/*` odfiltrowuje wszystko spoza `ARC3-Inference/`.** Więc nawet gdyby
pełny diff Franzena (660 020 B / 24 pliki) zawierał zmiany w `viewer/*`, **zostałyby odrzucone
przy aplikacji tak czy inaczej**. Ich brak w patchu notebooka jest **bez znaczenia przez
konstrukcję**, nie przez szczęście.

`segmentation.py` w patchu **jest** (`ARC3-Inference/inference/utils/segmentation.py`, ostatni
plik), a jego końcowy hunk jest kompletny: deklaruje `-189,11 +233,16` i faktycznie zawiera
11 linii starych i 16 nowych.

**Uczciwe zastrzeżenie:** nie mam drzewa Franzena (`da-fr/arc-agi-3-solution`), więc nie mogę
wykluczyć, że względem pełnego diffu brakuje jakichś hunków *wewnątrz* `ARC3-Inference/`.
Ale dwa fakty mówią, że to nie jest problem blokujący: `git apply` przeszedł (kernel zagrał),
a harness wyprodukował komplet artefaktów dla 10 gier.

### Co mimo wszystko WARTO z tego wziąć

Remedium v10 — **podział patcha na kawałki < 400 000 znaków, sklejanie w runtime i drukowanie
sha256** — jest **dobrą inżynierią niezależnie od tego, czy diagnoza była trafna**. Usuwa całą
klasę ryzyka (długość komórki, ciche obcinanie, brak kontroli spójności). Koszt: zero.
Warto wziąć **mechanizm**, nie **uzasadnienie**.

---

## 2. `commit(plan)` — najlepszy pomysł w tym projekcie i odpowiedź na moje zastrzeżenie

Wczoraj (`OCENA-DEEPSEEK-V9.md` §3) napisałem, że w danych jest **odwrotna** korelacja
`a/call` ↔ score (ls20: 13.89 a/call → 3.27 pkt, 1/7 poziomów; su15: 1.85 → 56.42, 7/9) i że
`a/call` może być **objawem** utknięcia, więc wymuszenie dyrektywą 8–15 akcji/wywołanie
„nie stworzy zrozumienia, tylko przyspieszy mielenie". Zaleciłem, by bramką dla profilu `deep`
była **liczba poziomów**, nie `a/call`.

**`commit(plan)` jest dokładnie odpowiedzią na to ryzyko** — zamienia batchowanie ślepe na
batchowanie weryfikowane:

```python
commit([
    "LEFT",
    {"action": "UP",    "expect": {"level": 2}},
    {"action": "RIGHT", "expect": {"cells": {"12,30": "R"}}},
])
```

Każdy krok leci osobno, oczekiwanie jest porównywane z klatką, która **realnie** wróciła, a plan
**staje na pierwszym rozjeździe** i zwraca `mismatch` z nazwą pola. Obsługiwane oczekiwania:
`level`, `board_changed`, `step`, `digest` (z `frame_digest()`), `cells`. Stop także na:
ukończeniu poziomu, game over, końcu runu, `max_actions` (domyślnie 40).

Dlaczego to jest ważne punktowo, a nie tylko estetycznie: oficjalna metodologia mówi wprost, że
„**tool calls, reasoning steps, retries** … are **not counted** as actions". Weryfikacja kroku
w kodzie jest więc **darmowa punktowo**, a jej koszt to tylko czas. Zmierzone offline:
**4 ms** przy pustej historii, **146 ms** przy 200 zarejestrowanych przejściach, plan 20 akcji
≈ **3 s** — mieści się w 30-sekundowym timeoutcie narzędzia. To jest realny pomiar, nie szacunek.

Do tego `ARC3_ESCALATE_ACTIONS=60`: po 60 akcjach na poziomie bez ukończenia kolejny turn
**wymusza** procedurę retrodykcja z logu → `model_state`/`model_step` → `check_model()` →
`plan()` → `commit()`. To jest **runtime'owy odpowiednik mojego `RESET_LEVEL`**, ale z warstwą
modelu świata — czyli mocniejszy. Mój `RESET_LEVEL` tylko czyści klatkę; ten każe modelowi
najpierw napisać symulator i sprawdzić go na zarejestrowanych przejściach.

**Weryfikacja offline:** 12/12 testów `commit()` na spatchowanym drzewie, w tym integracyjny
przez prawdziwy bootstrap sandboxa; 5 profili rozwiązuje się do oczekiwanego env; każda ścieżka
`/kaggle/input/...` z notebooka zadeklarowana w metadanych. Kill-switch: `ARC3_PLAN_COMMIT`
nieustawione = zachowanie **identyczne** z c45. To jest poprawnie zaprojektowany eksperyment.

---

## 3. Zbieżność z moimi ustaleniami — dwie sesje, ten sam wniosek, inne dowody

| ustalenie | v10 (`DECYZJE-I-RYZYKA.md`) | moje |
|---|---|---|
| **roster może nie być 25 publicznymi grami** | §6: „Prywatny zestaw może nie być 25 publicznymi grami — **wtedy cała wiedza o konkretnych grach (playbook, triage budżetu) jest warta zero**" | `OCENA-DEEPSEEK-V9.md` §4: docstring `competition_arcade.py` („no repeated game IDs", „hidden baselines") + `clone_game_ids` („needs cloned IDs **on the simulator side**") + oficjalne 110 gier nieznanych |
| **a/call już jest wysokie** | §3: „Nie zwiększa liczby akcji na wywołanie — **to już jest 4,4–5,2** i sufit z tego tytułu jest blisko" | §3: 474 wywołań → 4.36 ważone / 5.2 średnia; tok/wywołanie 3664.6 = Gemmy 3665 |
| **cap ruchów jest wyczerpany** | (§4, przez 38.85 Franzena jako sufit linii) | twierdzenie o capie + oficjalna metodologia RHAE, warunek `a ≤ 0.9325·b` |
| **planowanie w kodzie jest darmowe** | §3: „przeniesienie planowania z modelu do kodu; dokładnie to robi czołówka" | §5: „tool calls, reasoning steps, retries are NOT counted as actions" |
| **jakość symulatora = jedyna niewiadoma** | §4: „jakość symulatora zależy od modelu i to jest jedyna nieusunięta niewiadoma" | §6: GPT-5.4 daje 24.67 < duck 27.21, bo odkrywał poziomy za drogo |

**Najważniejsza zbieżność to roster.** Dwie sesje doszły niezależnie do tego, że wiedza
o konkretnych grach (mój playbook, mój triage `sum_baseline`) może być warta zero — a v10 formułuje
to ostrzej i wprost wymienia **playbook i triage budżetu**, czyli dokładnie moje dwa artefakty.
To jest najsilniejsze dostępne potwierdzenie mojej korekty z `OCENA-DEEPSEEK-V9.md` §4.

Do tego dochodzi trzecie, niezależne źródło o planowaniu w kodzie: **Retrodict 99.86% RHAE
(7 703 akcji na 183 poziomy)** i **Tycho 100%** — oba na modelach frontier. v10 uczciwie
zaznacza: „Na Qwen 3.8 Flash Next **nikt tego nie zmierzył**".

---

## 4. Stan faktyczny operacji (r075–r080) i bezpiecznik użytkownika

| run | czas UTC | wynik |
|---|---|---|
| r075-auto-submit | 12:28:04 | `arc3-duck-c45` **COMPLETE**, submisja **57629847** PENDING |
| r076-kernel-output | 12:36:38 | `rc=0`, pobrane `.per_game_cards.pkl` + artefakty **10 gier** |
| **r077-push** | 12:40:28 | ❌ **FAILED** — guard ścieżki: „push dozwolony tylko pod `arc-agi-3/kaggle`; dostałem root repo" (`ops.py:157`) |
| **r078-push** | 12:41:43 | ⚠️ **ODMOWA** — `duck-v9` nie ma `kernel-metadata.json` |
| **r079-push** | 12:43:54 | ✅ `kernels push …/duck-v9` `rc=0` — „**Kernel version 1 successfully pushed**" → `petersharps/arc3-duck-v9` |
| r080-submissions | 12:50:18 | 57629847 nadal PENDING, bez `publicScore` |

**BEZPIECZNIK (commit `cce4b32c`, 12:49:13):** „zero push/submit do Kaggle bez GO —
`request.json` → read-only `submissions` (r080); **zawieszona auto-decyzja 26.10**; CHAT-LOG
rejestr". Czyli od 12:49 **nic nie idzie na Kaggle automatycznie** — każda dalsza akcja wymaga
jawnego GO użytkownika. To jest ważniejsze niż którakolwiek liczba w tym dokumencie i wszystkie
plany slotów trzeba czytać przez ten filtr.

**Rozjazd planu v10 ze stanem faktycznym:** v10 pisze „Pierwszy slot: `c45`. Nie po to, żeby
wygrać, ale żeby mieć jedną zmierzoną liczbę dla tego stosunku na tym koncie." **Ten slot został
zużyty o 12:28** (r075 → ref 57629847). Czyli krok 1 planu v10 jest już wykonany, a wynik LB
powinien być widoczny ~21:30 UTC. Plan v10 tego nie odzwierciedla — był pisany równolegle.

**Kwota GPU (v10 §6, realne ograniczenie):** 30 h/tydzień. Dwa pełne runy po 9 h + smoke 2.5 h
= **20.5 h**. „Trzeci slot może nie wejść." Przy bezpieczniku i tej kwocie realnie dostępne są
**~2 sloty**, nie 3 — więc wybór między `plan` a `deep` jest wyborem **albo-albo**, nie sekwencją.

---

## 5. Werdykt

| twierdzenie / element v10 | werdykt |
|---|---|
| „v9 i v7 w ogóle by nie ruszyły; każdy slot spaliłby się w ~2 min bez logu z gry" | ❌ **OBALONE** — c45 ma `COMPLETE` (r075) i **10 gier z logami** (r076). Mechanizm: `%%writefile` w pełnym potoku IPython **dopisuje** końcową nową linię; `git apply --check` na surowym `source` z JSON-a jej nie ma (§1) |
| „498 799 to sufit długości komórki, ogon nigdy nie trafił do notebooka" | ⚠️ pomiar długości **dokładny**, wniosek **niepotwierdzony**: patch jest dobrze uformowany, `git apply` przechodzi, ostatni hunk kompletny |
| „brakuje całych zmian `viewer/*`" | ⚠️ **bez znaczenia** — cell 9 aplikuje z `--include=ARC3-Inference/*`, a w patchu jest **0 plików spoza** `ARC3-Inference/`; artefakty `_p0_viewer_data.json` i tak powstają |
| podział patcha na kawałki < 400k + sha256 w runtime | ✅ **brać** — dobra inżynieria, usuwa klasę ryzyka, koszt zero (niezależnie od trafności diagnozy) |
| `commit(plan)` z `expect` per krok i stopem na pierwszym rozjeździe | ✅ **najcenniejszy element pakietu** — bezpośrednia odpowiedź na ryzyko odwrotnej korelacji `a/call`↔score (§2) |
| `ARC3_ESCALATE_ACTIONS` (retrodykcja → model → check → plan → commit) | ✅ **mocniejsze niż mój `RESET_LEVEL`** — runtime'owy odpowiednik z warstwą modelu świata |
| pomiar kosztu `commit()`: 4 ms / 146 ms / 3 s na plan 20 akcji | ✅ realny pomiar, mieści się w 30 s timeoutcie narzędzia |
| 12/12 testów + integracyjny przez bootstrap sandboxa | ✅ |
| kill-switch `ARC3_PLAN_COMMIT` nieustawione = identycznie z c45 | ✅ poprawna konstrukcja eksperymentu |
| ryzyko rosteru: „playbook i triage budżetu warte zero" | ✅ **niezależne potwierdzenie mojej korekty** (§3) |
| „45+ wymaga modelu, który realnie pisze symulatory; Retrodict/Tycho robią to na frontier, nie na 27–30B" | ✅ **zgadzam się**, i to jest uczciwe postawienie sprawy |
| plan slotów: 1. `c45`, 2. `plan`, 3. wygrany | ⚠️ **slot 1 już zużyty** o 12:28 (r075); przy kwocie 20.5 h/30 h realnie ~2 sloty i **bezpiecznik** wymagający jawnego GO (§4) |

**Co bym zrobił z tym pakietem:** wziąć `commit(plan)` + eskalację + chunkowanie patcha z sha256,
**nie** brać uzasadnienia „bo v9 by nie ruszyło" (jest fałszywe i prowadzi do złej kolejności
slotów). I zanim cokolwiek pójdzie na slot: poczekać na LB z ref **57629847** (~21:30 UTC), bo
to pierwszy pomiar szybkiej linii z moim `level-token-cap 45k` i `roster probe` — a `roster probe`
rozstrzygnie pytanie, czy wiedza o konkretnych grach jest cokolwiek warta.
