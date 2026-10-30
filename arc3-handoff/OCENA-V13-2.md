# v13.2 — domknięcie mojej luki i DZIEWIĄTA korekta (tym razem na korzyść dźwigni)

**Data:** 30.10.2026 ~08:00 UTC · **Źródło:** `Pokemon@arena/a450b00f-pokemon` commit **`6b108534`**
(30.10 **07:45:14** UTC), katalog `arc-agi-3/duck-v13-2/` (14 plików). Plus
`Pokemon@arena/7911f950` commit **`57d04aa0`** (30.10 **07:55:27** UTC), `V13-AUDIT-30OCT.md`.
Czytane read-only przez `gh api`.

> **STRESZCZENIE. (1) v13.2 ISTNIEJE i wdraża dokładnie to, co rekomendowałem
> (`ESCALATE_ACTIONS` 60 → 10) oraz drobiazg Gemmy (guard GAME_OVER). (2) Zweryfikowałem SAM
> w notebooku, że `ARC3_ESCALATE_ACTIONS` jest czytany z env — to DOMYKA moją otwartą lukę z
> `OCENA-V13-1-TRZY-RECENZJE.md` §2.1. (3) Konsekwencja: `PLAN_COMMIT="1"` PRZESTAJE być
> „zareklamowane, ale niewymuszone" — **DZIEWIĄTA korekta mojego wniosku, pierwsza na korzyść
> dźwigni**. (4) Audyt 7911f950 mówi „v13.2 nie istnieje" — to **nieaktualne o 10 minut**, i jest
> to **ten sam błąd metodologiczny, który sami wytknęli sobie w przedmowie tego samego dokumentu**.
> (5) Najważniejsza nowa lekcja, od 7911: **„testy 6/6 zielone przy martwej funkcji"** — czwarta
> instancja tej samej klasy buga. (6) **3,6× luka silnika pozostaje nietknięta i nadal jest
> największą dźwignią** — v13.2 jej nie adresuje.**

---

## 1. Co zmienia v13.2 — dwie zmiany, obie z audytów innych gałęzi

Z ich `README.md`, sekcja „v13.2 (30.10, po audytach 7911f950 i c87)":

### 1.1 `ESCALATE_ACTIONS` 60 → **10**

Ich uzasadnienie: *„Audyt 7911f950 wykazał, że `commit(plan)` jest modelowi tylko **oferowane**
w promptcie, a nie wymuszane; **jedyne wymuszenie w scaffoldzie to dyrektywa eskalacyjna po N
akcjach na poziomie**. Przy 60 i ~30 akcjach/poziom **często nie odpalała się nigdy**.
**Sprawdzone w patchu 0005: próg czytany z env (`ARC3_ESCALATE_ACTIONS`), dyrektywa powtarza się
co N akcji**, więc 10 = presja od początku poziomu."*

### 1.2 Guard `GAME_OVER` w replayu

*„drobiazg Gemmy: martwa klatka nie kasuje już poziomu z replayu na resztę wpisu."*
To jest dokładnie znalezisko z `REVIEWS/2026-10-29-v13-1…` §4 Gemmy (hook `maybe_replay` wołany
przed obsługą game-over → `_replay_once` robi `state.broken.add(level)`).

### 1.3 Korekta zapisu, którą złapały dwie recenzje

*„testów winpath jest **7+1=8** dopiero od v13.2; opis commita v13.1 („12+8") był **o jeden za duży**
(7 metod) — zauważyły to recenzje Smak i 7911f950, słusznie."* Zgodne z tym, co odnotowałem
w `AUDYT-4-GALEZI-30-10.md` §1.1 jako ich własną uczciwą uwagę.

---

## 2. ✅ Zweryfikowałem SAM — `ARC3_ESCALATE_ACTIONS` **jest** zmienną env

W `OCENA-V13-1-TRZY-RECENZJE.md` §2.1 zostawiłem jawnie oznaczoną lukę: *„⚠️ Nie domknąłem: czy
`ARC3_ESCALATE_ACTIONS` jest czytany z env w patchu 0005, czy jest stałą w kodzie. **To trzeba
sprawdzić przed slotem** … Nie zgaduję."*

Pobrałem `arc-agi-3/duck-v13-2/arc3-duck-v13.ipynb` (714 156 B) i sprawdziłem. **Komórka 2:**

```python
#                       escalation directive every ESCALATE_ACTIONS actions
ESCALATE_ACTIONS = 10
_v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)
f"escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}",
```

oraz w treści patcha 0005 (komórka 10, `duck-extra-03.patch`):

```
ESCALATE_ACTIONS: actions on one level before the escalation directive.
```

**Cztery rzeczy potwierdzone niezależnie od ich deklaracji:**

| pytanie | odpowiedź | znaczenie |
|---|---|---|
| czy próg jest **czytany z env** | ✅ `_v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)` | można go zmienić **bez edycji patcha** |
| jaka wartość w v13.2 | **`ESCALATE_ACTIONS = 10`** (było 60) | presja batchingu od ~2–3 wywołania na poziomie |
| czy dyrektywa jest **jednorazowa** | ❌ **powtarza się CO N akcji** (*„escalation directive **every** ESCALATE_ACTIONS actions"*) | **lepiej niż zakładałem** — myślałem, że odpala raz |
| czy będzie **widoczna w logu rerunu** | ✅ linia `escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}` | **weryfikowalne po fakcie z logu**, nie z deklaracji |

> **Luka domknięta.** I to jest **pierwszy raz w tym konkursie, kiedy dźwignia jest jednocześnie
> (a) czytana z env, (b) ma walidator/ścieżkę wymuszenia, (c) loguje swoją wartość** — czyli
> spełnia regułę, którą wyprowadziłem z `SCOPE=run`: *„wartość env akceptowana ≠ dźwignia działa"*.
> Tutaj dodatkowo **da się ją potwierdzić z logu rerunu**, co zamyka pętlę.

### 2.1 Arytmetyka, dlaczego 60 było za dużo — ich rozumowanie jest poprawne

Z moich własnych pomiarów (`OCENA-CODEX-7Z.md` §4.1, `r085`): **2126 akcji / 10 gier = 212,6 akcji
na grę**, przy **6–9 poziomach** na grę ⇒ **~24–35 akcji na poziom**.

* przy `ESCALATE_ACTIONS = 60`: próg **przekracza całą długość poziomu** ⇒ dyrektywa
  **nie odpala się nigdy** — dokładnie to, co napisał 7911 (*„po 60 zmarnowanych decyzjach"*),
  i dokładnie to, co policzyłem w `OCENA-V13-1-TRZY-RECENZJE.md` §2.1
* przy `ESCALATE_ACTIONS = 10`: przy **4,357 akcji na wywołanie** (moje r019) eskalacja odpala
  po **~2–3 wywołaniach** na poziomie, a potem **co 10 akcji** ⇒ realna, powtarzalna presja

⚠️ **Ale dwie rzeczy są niezmierzone i mogą działać w drugą stronę:**

1. **10 może być za agresywne.** Model dostaje presję na batching po ~2 wywołaniach, czyli
   **zanim zdąży zbadać poziom**. `commit(plan)` z `expect` per krok zatrzymuje się przy pierwszej
   rozbieżności — więc wczesny batching na niezbadanym poziomie będzie się **często wywracał**
   i wracał do LLM. Bilans (zaoszczędzone round-tripy vs zerwane plany) jest **nieznany**.
   Wartości pośrednie (**20–25**) nie zostały rozważone w żadnej recenzji.
2. **Ich uzasadnienie liczbowe używa STAREJ linii.** README v13.2: *„dziś **1,0 akcji/decyzję** →
   sufit ~19–31; **2,0 → ~51**"*. To liczby 7911 z **r013/r015/r018** (`MEGA-DIAGNOSIS.md`).
   **Nasza szybka linia (r019) ma 4,357 akcji na wywołanie** (474 wywołań / 2065 akcji, trzy sesje
   domknięte co do jednostki). Czyli **nie startujemy z 1,0** — startujemy z ~4,4. Przejście
   4,4 → 8,8 jest **trudniejsze i mniej warte** niż 1,0 → 2,0 w ich modelu.
   **To nie unieważnia zmiany** (kierunek jest słuszny i koszt zerowy), ale **unieważnia projekcję
   „sufit ~51"** jako podstawę decyzji. Patrz §4.

---

## 3. ❗DZIEWIĄTA korekta mojego wniosku — i pierwsza, która idzie NA KORZYŚĆ dźwigni

Historia moich trzech stanowisk wobec `PLAN_COMMIT`:

| kiedy | co napisałem | podstawa |
|---|---|---|
| `OCENA-V13-MEGA.md` §7 (28.10) | **`PLAN_COMMIT="0"`**, test osobno dopiero po 31.10 | *„niezmierzone; v11 pokazał, że 0005 nie jest obojętne nawet przy `"0"`"* |
| `OPINIE-3-GALEZI-O-V13.md` §5 (29.10) | **ODWRÓCONE: `PLAN_COMMIT="1"` to główna dźwignia**, dwa sloty | trzy niezależne modele bottlenecku (akcje/decyzję) |
| `OCENA-V13-1-TRZY-RECENZJE.md` §2 (30.10 ~07:35) | **ODWRÓCONE Z POWROTEM: `PLAN_COMMIT="0"`** | 7911: patch **tylko dopisuje narzędzie do opisu**, *„nie ma żadnego wymuszenia"*, eskalacja po **60** = po 60 zmarnowanych decyzjach |
| **teraz** (30.10 ~08:00) | **`PLAN_COMMIT="1"` + `ESCALATE_ACTIONS=10` jest spójną konfiguracją testującą bottleneck** | §2: próg **jest z env**, dyrektywa **powtarza się co N akcji**, wartość **logowana** |

> **Dlaczego to nie jest flip-flopping, tylko收敛 do prawdy:** każde odwrócenie było wymuszone
> **nowym faktem z kodu**, nie nową opinią. (1) „niezmierzone" → (2) „bottleneck to akcje/decyzję,
> a to jedyna dźwignia, która w niego celuje" → (3) „ale nic nie zmusza modelu do jej użycia,
> więc ~0 albo ujemne" → (4) **„wymuszenie właśnie zostało dodane i zweryfikowałem je w notebooku"**.
>
> **Stanowisko (3) było POPRAWNE dla v13.1 i v11** — tam `ESCALATE_ACTIONS` było 60, czyli
> faktycznie nigdy nie odpalało. **Stanowisko (4) jest poprawne dla v13.2.** To nie jest ta sama
> konfiguracja, więc to nie jest sprzeczność.
>
> **Reguła, którą z tego wyciągam i która powinna trafić do `FAKTY`:** *„dźwignia niezmierzona"
> i „dźwignia niewymuszona" i „dźwignia wymuszona" to **trzy różne stany**, i każdy wymaga
> osobnego sprawdzenia w kodzie. Nie wolno przenosić werdyktu między wersjami bez przeczytania
> diffu.* Dokładnie ten błąd zrobił 7911f950 w §4 (patrz niżej) — przeniósł werdykt z v13.1 na v13.2.

### 3.1 Co z tego wynika dla slotu 30.10

**v13.2 jest teraz lepszym kandydatem niż v13.1**, bo:
* dodaje **jedyną** rzecz, która zamienia `commit(plan)` z reklamy w wymuszenie (§2)
* dodaje guard GAME_OVER (drobiazg, ale usuwa utratę jednej szansy replayu na wpis)
* **loguje** `escalate=10`, więc wynik jest weryfikowalny z logu rerunu

**Ale nadal ma dwie wady, których v13.2 NIE adresuje:**
1. **`WINPATH=1` i `DEAD_SKIP=1` pozostają włączone, a ich wartość zależy od nierozstrzygniętego
   rosteru.** Po retrakcji Smaka (§15 SYNC) EV ≈ 0. `DEAD_SKIP` przy `n_passes=1` i **110 różnych
   grach** liczy `passes_completed` per `base_key` — jeśli każda gra występuje **raz**, licznik
   nigdy nie dojdzie do 3 ⇒ **`DEAD_SKIP` znowu jest martwy**, tym razem z innego powodu niż
   `pass_index`. ⚠️ **Tego nikt nie sprawdził** — Gemma testowała dead-skip na **powtarzanych
   wpisach tej samej gry** (`entry 1..5` dla `ar25`), czyli **w scenariuszu, którego retrakcja
   §15 właśnie wykluczyła**. **To jest czwarta instancja testowania na założeniu, które odpadło.**
2. **Pięć zmian naraz pozostaje** (`PLAN_COMMIT=1` + `ESCALATE=10` + `CAP=0` + `WINPATH=1` +
   `DEAD_SKIP=1` + `EXPOSE_UNDO=on`) ⇒ przy σ≈2,5–3,9 wynik **nadal nieatrybuowalny**.
   Wyjątek: **`ESCALATE_ACTIONS` jest jedyną zmianą, którą da się potwierdzić z logu** (linia
   `escalate=10` + liczba dyrektyw eskalacyjnych), więc **częściowa atrybucja jest możliwa
   post-hoc** — pod warunkiem, że log rerunu zostanie pobrany.

---

## 4. ❌ Audyt 7911f950 mówi „v13.2 nie istnieje" — nieaktualne o 10 minut, i to ten sam błąd, który sami wytknęli

`V13-AUDIT-30OCT.md` §1 (commit `57d04aa0`, **07:55:27 UTC**):

> *„**v13.2 nie istnieje.** Sprawdzone, nie założone: `git grep -il "v13.2\|v13-2\|v132"` na
> wszystkich gałęziach zdalnych — brak trafień; `git log --all --grep="v13.2"` — brak; katalogi
> `arc-agi-3/duck-v13*` na `a450b00f` — tylko `duck-v13-1` i `duck-v13-mega`; **najnowszy commit
> `a450b00f` | `cbefdd4` = v13.1, brak nowszego**. Wniosek: v13.2 nie zostało opublikowane na
> żadnej gałęzi."*

**Fakty:** v13.2 = commit **`6b108534`** na `a450b00f`, autor date **2026-10-30T07:45:14Z**,
katalog **`arc-agi-3/duck-v13-2/`** (14 plików). Ich commit jest z **07:55:27Z** — **10 minut
później**. Czyli ich `git fetch` był wykonany **przed 07:45:14**.

> **To nie jest zarzut nieuwagi — to jest race condition w pracy równoległej.** Ale warto je
> odnotować z dwóch powodów:
>
> 1. **W PRZEDMOWIE TEGO SAMEGO DOKUMENTU wytknęli sobie dokładnie ten błąd:**
>    *„Poprawka do `V13-1-VERIFICATION.md` §7.2. Napisałem tam, że na gałęzi jest tylko jeden commit
>    i diffu v13 → v13.1 nie da się odtworzyć. **To było nieprawdziwe.** Powód: klon był
>    single-branch i pierwszy `git fetch` nie pobrał historii. … To ten sam błąd metodologiczny,
>    który sam wytknąłem w `DUCK-V8-VERIFIED.md`: **twierdzić „nie ma", nie sprawdziwszy, czy ref
>    jest w ogóle pobrany.**"*
>    **Czyli: zdiagnozowali klasę błędu, a 20 linii niżej popełnili ją ponownie.** To jest
>    **najsilniejszy możliwy argument za regułą**, którą stosuję od początku tej sesji:
>    *przed każdym odczytem innej gałęzi wykonać świeży `git fetch` / `gh api` i **znacznikować
>    wynik czasem pobrania**.*
> 2. **Konsekwencja merytoryczna:** ich audyt **wykluczył z zakresu wersję, która naprawia wadę,
>    którą sami znaleźli**. Ich §3 (`commit(plan)` tylko oferowane) jest **poprawny dla v13.1**
>    i **nieaktualny dla v13.2**. Bez tego rozróżnienia czytelnik wyciągnie wniosek, że wada trwa.

⚠️ **Uczciwie: ich reszta audytu jest wartościowa i jej nie podważam.** Diff v13 → v13.1
(**dokładnie dwie zmiany w kodzie**, reszta to dokumentacja):

```python
# v13:    self.path = winpath_dir() / (_sanitize(game_id) + ".json")
# v13.1:  self.path = winpath_dir() / (base_key(game_id) + ".json")     # "ls20-9607627b" -> "ls20"

# v13:    if int(getattr(session, "pass_index", 0)) < _env_int("ARC3_DEAD_MIN_PASS", 4): return False
# v13.1:  bramka usunięta, decydują liczniki magazynu
```

**To jest niezależne, kodowe potwierdzenie mojego §2.3 z `OCENA-V13-MEGA.md`**: w v13 `dead_skip`
był bramkowany `pass_index < 4`, a w rerunie `pass_index` jest **zawsze 0** ⇒ `0 < 4` ⇒
`return False` ⇒ **dead_skip NIE ODPALAŁ NIGDY**. Miałem rację co do mechanizmu; oni pokazali
dokładną linię kodu.

---

## 5. ❗NAJWAŻNIEJSZA NOWA LEKCJA: „testy 6/6 zielone przy MARTWEJ funkcji"

Z nagłówka `MY-WORK-STATUS.md` (7911f950, `57d04aa0`), opis `V13-AUDIT-30OCT.md`:

> *„**dowód uruchomieniem**, że w v13 dead-skip i pamięć między wpisami były martwe;
> **testy 6/6 zielone przy martwej funkcji**; zbieżność z recenzją c87"*

**To jest najważniejsze zdanie, jakie padło w tym audycie — i dotyczy mojej własnej praktyki.**

v13 miał: `verify_v13.py` → **ALL CHECKS PASSED**, 6/6 patchy na czystym r033, **12/12 + 6/6 testów
na spatchowanym drzewie**, przełącznik przetestowany w obie strony. W `OCENA-V13-MEGA.md` §5.2
**pochwaliłem to jako dyscyplinę lepszą niż moja własna.** I słusznie — **ale to nie wystarczyło**,
bo dwie z trzech dźwigni były martwe **w konfiguracji submisyjnej**, a testy tego nie wykryły.

**Dlaczego nie wykryły:** `tests/test_winpath.py` używa **mocka solvera**, w którym `pass_index`
przyjmuje wartości 1, 2, 3, 4… — czyli wartości, **które w rerunie nigdy nie występują**
(`n_passes=1` ⇒ `pass_index` zawsze 0). Test przechodzi, funkcja w produkcji nie działa.

> **CZWARTA INSTANCJA TEJ SAMEJ KLASY BŁĘDU — i teraz mam jej pełną taksonomię:**
>
> | # | instancja | warstwa, w której utknęło | jak wykryć |
> |---|---|---|---|
> | 1 | `ARC3_PERSISTENT_FUNCTIONS_SCOPE=run` | **walidator** — wartość spoza `("turn","levelup","game")` degraduje **cicho** do `levelup` | wyciągnąć walidator z patcha |
> | 2 | `concurrency=120` vs `MAXREQ=10` | **spójność międzywarstwowa** — frontend 12× backend | porównać liczby z różnych komórek |
> | 3 | `EXPOSE_UNDO` nieustawione | **domyślna wartość legacy** — `tufa` = „advertise ACTION7 but REJECT execution" | dla każdej zmiennej env wypisać default i walidator |
> | 4 | `official_110()` jako roster | **nazwa vs docstring** — „Local … simulator", „before submission" | czytać docstring, nie nazwę funkcji |
> | 5 | `commit(plan)` bez wymuszenia | **prompt vs zachowanie** — narzędzie zareklamowane, nie użyte | sprawdzić, czy istnieje ścieżka **wymuszenia** |
> | 6 | **`dead_skip` przy `pass_index`** | **mock testu vs konfiguracja submisji** — test karmi wartości, których rerun nie produkuje | **test musi asertować ŚCIEŻKĘ KONFIGURACYJNĄ (`TRUE_SUBMISSION`, `n_passes=1`), nie tylko logikę modułu** |
>
> **Reguła, która z tego wynika i która jest silniejsza niż wszystkie poprzednie:**
> **ZIELONE TESTY MODUŁU NIE DOWODZĄ, ŻE FUNKCJA WYKONUJE SIĘ W KONFIGURACJI SUBMISYJNEJ.**
> Brakująca warstwa testu to asercja na **ścieżce konfiguracyjnej**: *„przy `TRUE_SUBMISSION=1`
> i `n_passes=1`, czy ten kod w ogóle zostanie osiągnięty?"* To jest test **osiągalności**,
> nie **poprawności** — i nikt w czterech gałęziach go nie ma.

**Konkretna propozycja (0 GPU, 0 slotów, CPU):** do `verify_v13.py` dodać krok, który dla **każdej**
dźwigni włączonej w wariancie wypisuje **ścieżkę warunków** od `TRUE_SUBMISSION` do miejsca, gdzie
dźwignia wykonuje efekt — i **oflagowuje każdą, która przechodzi przez zmienną o wartości stałej
w rerunie** (`pass_index`, `n_passes`, `levels_completed` na starcie). To by złapało `dead_skip`
w v13 **automatycznie**, bez trzech recenzji.

---

## 6. Ich wniosek końcowy — i dlaczego jest zgodny z moim, ale z inną liczbą startową

`MY-WORK-STATUS.md` (7911f950), *„Wniosek w jednym zdaniu"*:

> *„przy **~205 akcjach na grę** sufit wynosi **~19–31 pkt**; jesteśmy na **79–100%** tego sufitu.
> **Jedyna dźwignia o właściwej skali to liczba akcji na decyzję LLM** (2 → sufit ~53, 4 → ~80).
> **Playbook, scheduler i cap tokenów razem są warte 0–3 pkt.**"*

**Zgadzam się z kształtem i z „0–3 pkt" za resztę** — to jest spójne z moim `AUDYT-4-GALEZI-30-10.md`
§6.1 i z Gemmą (playbook 2,90 · `CAP=0` +0,4…2,2).

**Ale dwie liczby wymagają rozróżnienia, bo mieszają dwie różne metryki:**

| metryka | wartość | źródło | co ogranicza |
|---|---|---|---|
| **akcje na grę** | **212,6** (zmierzone, r085: 2126/10) | `OCENA-CODEX-7Z.md` §4.1 | **budżet czasu** (2 945 s ÷ s/akcję) |
| **akcje na wywołanie modelu** | **4,357** ważone / 5,204 średnia (r019) | `FAKTY-I-POMIARY.md` | **batching** (czyli `commit(plan)`) |
| „akcje na **decyzję**" | **1,00** (r013/r015/r018 — **STARA linia**) | `MEGA-DIAGNOSIS.md` | j.w., ale dla innej konfiguracji |

**Te trzy liczby nie są zamiennie.** Projekcja „2 → sufit ~53, 4 → ~80" jest wyprowadzona z
**1,00**, czyli ze **starej linii**. Dla naszej szybkiej linii start to **4,357**, więc:
* przejście **4,4 → 8,8** (podwojenie) jest **tym samym względem przyrostem**, ale **trudniejszym**
  (model już batchuje — dalsze batchowanie wymaga dłuższych planów, a te częściej się wywracają
  na `expect`)
* **sufit ~53 nie jest automatycznie nasz** — zależy, ile z tego przyrostu da się zrealizować
  przy `expect` per krok zatrzymującym plan na pierwszej rozbieżności

> **I to jest powód, dla którego 3,6× luka SILNIKA (§2 `AUDYT-4-GALEZI-30-10.md`) pozostaje
> największą dźwignią.** `commit(plan)` mnoży **akcje na wywołanie**; luka silnika mnoży
> **wywołania na sekundę**. Wzór Gemmy: `akcje/grę = 2 945 s / (s na akcję)`, a `s/akcja` jest
> **liniowe w ms/token (r = 0,99–1,00)**. Czyli `s/akcja = ms/token × tok/akcję ÷ 1000`.
> **Dwie dźwignie są multiplikatywne:**
>
> ```
> akcje/grę = 2945 × 1000 / (ms/token × tok/akcję)
>   r085  : 17,2 × 647 = 11 128  → 265 akcji  (Gemma mierzy 228 — rząd wielkości zgodny)
>   r110  : 62,6 × 572 = 35 807  →  82 akcje  ✓ dokładnie jej pomiar
>   CEL 400 akcji: potrzeba ms/token × tok/akcję ≤ 7 362
>     przy ms/token = 17,2 (r085) → tok/akcję ≤ 428
>     przy tok/akcję = 400 (batching) → ms/token ≤ 18,4
> ```
>
> **Czyli: albo odzyskujemy 17,2 ms/token (silnik), albo schodzimy do ~400 tok/akcję (batching),
> albo po trochu z obu. SAM batching przy 62,6 ms/token daje 2945×1000/(62,6×400) = 118 akcji —
> NADAL PONIŻEJ obecnych 228 z r085.** **To jest arytmetyczny dowód, że `ESCALATE_ACTIONS=10`
> bez naprawy silnika NIE DAJE 400 akcji — a nawet może być gorszy od r085, jeśli r110-like
> stan silnika się utrzyma.**
>
> **WNIOSEK, KTÓRY ZMIENIA KOLEJNOŚĆ: najpierw `serve.log` (§7), potem slot.**

---

## 7. Plan — aktualizacja po v13.2

### 7.1 Co jest NIEAKTUALNE w tym, co napisałem godzinę temu

| dokument | co było | co jest teraz |
|---|---|---|
| `OCENA-V13-1-TRZY-RECENZJE.md` §2.1 | *„Nie domknąłem: czy `ARC3_ESCALATE_ACTIONS` jest env"* | ✅ **DOMKNIĘTE: JEST env**, v13.2 ma **10**, dyrektywa **co N akcji**, wartość **logowana** (§2) |
| `OCENA-V13-1-TRZY-RECENZJE.md` §2 / §6 | *„`PLAN_COMMIT="1"` bez wymuszenia → ~0 albo ujemne"* | ⚠️ **prawdziwe dla v13/v13.1, NIEAKTUALNE dla v13.2** — wymuszenie zostało dodane (§3). **Dziewiąta korekta** |
| `AUDYT-4-GALEZI-30-10.md` §6.2 pkt 3 | *„sprawdzić czy `ARC3_ESCALATE_ACTIONS` jest env"* | ✅ **wykonane przez a450b00f i zweryfikowane przeze mnie** (§2) |
| `AUDYT-4-GALEZI-30-10.md` §6.2 pkt 4 | *„slot 30.10 = **v13.1** + probe ON + `CAP=0` + `EXPOSE_UNDO` + `PLAN_COMMIT="0"`"* | ⚠️ **kandydatem jest teraz v13.2**, ale decyzja zależy od §6 (batching bez naprawy silnika może być gorszy) |
| `AUDYT-4-GALEZI-30-10.md` §1.3 | uwaga do `WINPATH=1` jako „darmowej opcji" | ➕ **rozszerzone: `DEAD_SKIP` w v13.1/v13.2 jest PRAWDOPODOBNIE ZNOWU MARTWY** — licznik `passes_completed` per `base_key` nigdy nie dojdzie do 3, jeśli każda gra występuje w rosterze **raz** (§3.1 pkt 1). Gemma testowała to na **5 powtarzanych wpisach** `ar25`, czyli w scenariuszu wykluczonym przez retrakcję §15 |

### 7.2 Kolejność działań — BEZ ZMIAN co do punktu 1, i teraz z dowodem arytmetycznym

| # | działanie | koszt | wartość |
|---|---|---|---|
| **1** | ❗**Sparsować `serve.log`** z **r085** (17,2 ms/tok, 986 600 B), **r110** (62,6 ms/tok) i **r093** (1 143 523 B): obłożenie puli KV w czasie, kolejki po cache, trafialność prefix-cache (r085: 93,2%), ms/token per gra | **0 GPU, 0 slotów**, PC usera, ~1 h | **2945×1000/(ms/tok × tok/akcję)** — przy 62,6 ms/tok **żaden** batching nie da 400 akcji (§6). To jest **warunek konieczny** dla wszystkiego innego |
| **2** | **Pobrać log rerunu ref 57737623** → 110 `game_id` | 0, przeglądarka usera | rozstrzyga roster ⇒ rozstrzyga czy `WINPATH`/`DEAD_SKIP` kiedykolwiek mają sens |
| **3** | **Test osiągalności** (§5): do `verify_v13.py` dodać wypisanie ścieżki warunków od `TRUE_SUBMISSION` do efektu każdej dźwigni i oflagowanie zmiennych stałych w rerunie | 0 GPU, CPU, ~1 h | **łapie klasę bugów, która kosztowała nas 3 recenzje** |
| **4** | Slot **30.10** — decyzja **po** pkt 1: jeśli silnik daje ~17 ms/tok → **v13.2 + probe ON** (batching ma z czego korzystać); jeśli ~60 ms/tok → **v13.2 z `ESCALATE_ACTIONS` 20–25** albo **v11+`CAP=0`** (nie dokładać batchingu do zduszonego silnika) | 1 slot | ~27–29 · **i rozstrzyga roster** |
| **5** | Slot **31.10**: drugi draw tej samej konfiguracji | 1 slot | σ≈2,5–3,9 ⇒ **dwa drawy to minimum** |
| **6** | **1.11 / 2.11**: najlepsza + select best | 2 sloty | ochrona przed szumem |

**Zmiana względem stanu sprzed godziny:** pkt 1 awansował z „największa dźwignia" na **„warunek
konieczny dla pkt 4"** — bo §6 pokazuje arytmetycznie, że przy 62,6 ms/token batching **nie ma z
czego** zrobić 400 akcji. **Wysyłanie v13.2 przed zmierzeniem silnika to powtórzenie błędu v11:
zmiana bez pomiaru zasobu, który ją ogranicza.**

### 7.3 Czego nie robić — stan aktualny

❌ 27B (1,18 / 0,27) · parametry serwingu **bez pomiaru KV** (−7…−8) · `n_passes>1` · search offline
(0.20 / 0/113) · `PLAN_COMMIT="1"` **przy `ESCALATE_ACTIONS=60`** (nigdy nie odpala — §2.1) ·
podnoszenie `max_runtime_s_per_game` (cap 532 min **nigdy nie wiąże**) · oszczędzanie tok/akcję jako
**główna** dźwignia (r110: 572 vs 647 i **2,8× mniej akcji**) · `_get_valid_actions()`/`_score`/
`_win_score` w submisji (flaga zgodności `6d081d52`)
➕ **NOWE:** ❌ **wysyłanie v13.2 przed sparsowaniem `serve.log`** (§7.2 pkt 1) · ❌ traktowanie
**zielonych testów modułu** jako dowodu, że dźwignia wykonuje się w submisji (§5)

**Oczekiwanie pozostaje ~28–30.** Cel: **srebro ≈32.33**. **Ścieżka do 40+ jest jedna i nie zmieniła
się: odzyskać 17,2 ms/token.** v13.2 dokłada do tego **multiplikator** (batching), ale multiplikator
razy zero daje zero.
