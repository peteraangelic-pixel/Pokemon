# v17 — co powstało na innych gałęziach, co z tego wybrać, i dlaczego

**Data:** 2026-10-30 · **Kod:** `local/v17_policy.py` + `local/test_v17.py` (17/17).
**Baza porównania:** v13.2 (`6b10853`), `duck-v13-3-arena` (Smak `5548d35`),
dwa **rozbieżne** `duck-v15`.

---

## 0. Najpierw sprostowanie: **v13.4 nie istnieje**

Szukałem czterema metodami, nie jedną:

| metoda | zakres | wynik |
|---|---|---|
| `gh api .../branches` | Pokemon (8 gałęzi), Gemma-konkurs (3), Smak-Domu-Konkurs (2) | brak |
| `git ls-tree` + grep ścieżek `13[.-]4\|v134` | 6 pobranych gałęzi Pokemon | brak |
| `git grep` **treści** `v13[.-]4` | wszystkie gałęzie Pokemon + Gemma | brak |
| `git log --all` + `search/commits` | oba repo | brak |

**Co istnieje zamiast tego: `duck-v13-3-arena`** (Smak, `5548d35`) — i to jest
ważniejsze niż v13.4, bo wprowadza **jedyną dźwignię, która ma zmierzony
rozmiar porównywalny z celem**.

Ślad po `5548d35`: nie jest osiągalny z żadnej gałęzi Pokemon ani Gemma.
Notebook jest jednak **w pakiecie Gemmy**: `ARC3/duck-v15/src/base-v13-3-arena.ipynb`
(721 KB). Wyciągnąłem z niego kod i tekst promptu — nie zgaduję, co robi.

---

## 1. Dwa `duck-v15`, które się nie znają

Oba mówią „v15", oba mówią „7 patchy", oba mają patch **0007**. **To nie są te same buildy.**

| | `Pokemon@a450b00f` `8d96c68` | `Gemma-konkurs@c4eeb067` `07bf05e` |
|---|---|---|
| baza | v14 (Gemma `b38b82e`) | **v13.3-arena** (`5548d35`) |
| patch 0007 | **eskalacja względna** → `tool_agent.py`, `solver.py`, `plan_commit.py` | **log zdarzeń win-path** → `arc3_winpath.py` |
| hint „batchuj" na openerze | **nie ma** | **ma** (`ARC3_OPENER_COMMIT_HINT=1`) |
| cap eskalacji na poziom | **2** (`ARC3_ESCALATE_MAX_PER_LEVEL`) | brak |
| `ESCALATE_ACTIONS` | 20 | 20 |
| sondy v14 | 2 (roster, budżet) | 2 (roster, budżet) + guard c45 |

**Pliki obu patchy 0007 są rozłączne** (sprawdzone `comm -12` → pusto). Czyli to
kolizja **nazw, nie kodu** — zestawy da się złożyć, tylko trzeba przenumerować.
Test: `test_patch_sets_compose`.

**Kluczowa różnica merytoryczna:** a450 ma **cap 2 na poziom**, Gemma go nie ma.
Ich własny README mówi, że w trybie submisji silnik zeruje baseline
(`base_actions_per_level is None`), więc eskalacja względna degraduje do 20 —
i wtedy **cap 2 jest jedyną częścią tego patcha, która cokolwiek robi**.
Gemma tego capa nie ma. To jest realny brak w ich v15.

---

## 2. Prawdziwa dźwignia: hint na openerze

Dokładny tekst, dopisany jako **ostatnia linia open-era** (tam, gdzie siedzi
prompt wznowienia):

> „When your evidence supports a choice, call `action(actions)` with the sequence
> it supports. Probe with a single action when you genuinely need to distinguish
> two possibilities; otherwise batch the route you have."

**Ich pomiar (upstream):** sekwencje po batchu ze wznowienia → **6,73 i 6,91**
akcji; po świeżym openerze → **5,43 i 3,91**. Opener nie zawierał **żadnej**
presji na działanie — cała presja w harnessie siedziała w ścieżce wznowienia.

**To zgadza się z moimi liczbami trzema niezależnymi pomiarami:**

| źródło | akcje/generację |
|---|---|
| mój `r0{13,15,18}` (30 gier) | **4,61** (mediana 4,62; średnie runów 5,38 / 4,57 / 5,20) |
| c87 (`r019`, 474 calle / 2065 akcji) | **4,357** |
| Gemma, opener | **3,91–5,43** |

Wszyscy mierzyliśmy **tę samą liczbę** i nikt nie wiedział, dlaczego jest taka
niska. Odpowiedź: mierzyliśmy głównie generacje po openerze.

### 2.1 Ile to jest warte — arytmetyka

Budżet: 186 200 tok/gę ÷ tok/akcję = akcje/gę. Myślę, że 50 pkt wymaga **253**.

| akcji/generację | tok/akcję | akcji/grę | |
|---|---|---|---|
| 4,61 (dziś) | 853 | **218** | za mało |
| 5,07 (+10% efektu) | 776 | 240 | za mało |
| **5,62 (połowa efektu)** | **700** | **266** | **≥253** |
| 6,73 (poziom wznowienia) | 584 | 319 | dużo zapasu |

**Połowiczne zadziałanie hinta wystarcza na 50.** To dokładnie ten „+22% budżetu",
którego szukałem w `V16-PLAN.md` §0 — i nie trzeba za niego płacić ani jednym
tokenem. To zmiana **w promptcie**.

---

## 3. Gdzie obie gałęzie tracą czas: spór o eskalację jest zaokrągleniem

Dyrektywa eskalacji to **540 znaków ≈ 146 tokenów**. Na `r018` (32 ukończone
poziomy, 10 gier):

| próg | wstrzyknięć | /grę | tok/grę | % budżetu | akcji/grę |
|---|---|---|---|---|---|
| 10 (v13.2, v13.3) | 121 | 12,1 | 1 767 | **0,95%** | 2,1 |
| 20 (oba v15) | 52 | 5,2 | 759 | 0,41% | 0,9 |
| cap 2 przy 20 | 39 | 3,9 | 569 | 0,31% | 0,7 |
| względny | 4 | 0,4 | 58 | 0,03% | 0,1 |

**Cały spór 10 → 20 → względny jest wart 2 akcje na grę (0,92% budżetu).**
Hint jest wart **48–50 akcji**.

> **Stosunek 24 : 1.**

Nawet gdybym założył, że dyrektywa kosztuje **10×** więcej niż jej długość
(całą generację na budowanie modelu zamiast działania), zostaje **20 akcji vs 50**
— hint nadal wygrywa 2,5×. Test: `test_escalation_is_rounding_error`.

**Wniosek, który zmienia priorytety:** obie gałęzie spędziły ten dzień na
optymalizacji rzeczy wartej 1% budżetu, podczas gdy dźwignia warta 22% leżała
w jednym zdaniu promptu.

---

## 4. Bramka Gemmy nie może paść — czyli nie jest testem

Ich GO/NO-GO: **`actions_per_call ≥ 1,8`**.

| run | zmierzone | bramka 1,8 |
|---|---|---|
| r013 | 5,38 | przechodzi |
| r015 | 4,57 | przechodzi |
| r018 | 5,20 | przechodzi |

**Najgorszy zmierzony run to 4,57 — 2,5× powyżej progu.** Bramka przejdzie
nawet gdyby hint **nie robił nic**. To dokładnie lekcja, którą c87 zacytował
ode mnie: *„testy 6/6 zielone przy martwej funkcji"* — tym razem w cudzym
pakiecie, w krytycznej bramce decydującej o slocie.

**Moja bramka: `actions_per_call ≥ 6,0`.**

- **pada na wszystkich trzech zapisanych runach** (4,57 / 5,20 / 5,38) — czyli
  jest testem, nie pieczątką;
- leży **dokładnie na granicy celu**: 6,0 → 284 akcji/grę ≥ 253;
- powyżej niej wynik jest interpretowalny: „hint zadziałał i wystarczył".

Test: `test_new_gate_rejects_every_recorded_run` — sprawdza, że **każdy**
zapisany run ją oblewa.

---

## 5. Moja najlepsza wersja: **v17** = Gemma + cap 2 + log pokrycia + bramka

Nie buduję czwartego pakietu od zera. Biorę to, co w obu jest najmocniejsze:

| element | źródło | dlaczego |
|---|---|---|
| **hint na openerze** | v13.3-arena (Smak) | jedyna dźwignia z rozmiarem ≥ celu (22%+) |
| 7 certyfikowanych patchy | v13.3-arena | certyfikacja przenosi się bez zmian |
| `ESCALATE_ACTIONS = 20` | v14 (Gemma) | zmierzone na 32 poziomach |
| **cap 2 eskalacji na poziom** | **a450 `8d96c68`** | jedyna część patcha 0007 żywa w rerunie |
| eskalacja względna | a450 `8d96c68` | pomaga w smoke/lokalnie, w rerunie degraduje do 20 |
| sondy rosteru + budżetu | v14 (Gemma) | rozstrzygają dwie otwarte niewiadome |
| **log pokrycia** | moje `local/metric.py` | `score ≤ 100 × coverage` — to jest wynik |
| **bramka 6,0** | moje `local/v17_policy.py` | bramka, która może paść |

**Łańcuch:** 7 patchy v13.3 przenosi się bez zmian (certyfikowane 7/7 na czystym
r033), a patch eskalacji względnej z a450 wchodzi jako **0008** — pliki rozłączne,
więc `git apply` nie ma się o co zderzyć. Razem **8 patchy**.

**Czego świadomie NIE biorę:** nic więcej. c87 §4: przy σ ≈ 3,93 każda
niezmierzona zmiana dokłada wariancję, której nie da się przypisać. Hint jest
zmierzony, cap 2 jest zmierzony, `ESCALATE=20` jest zmierzony. Reszta czeka.

---

## 6. Uczciwa prognoza i co ją może obalić

| scenariusz | akcji/grę | pokrycie | wynik |
|---|---|---|---|
| hint **nie działa** | 218 | 29% | **~29** (jak dziś) |
| hint +10% | 240 | 32% | ~32 |
| hint połowicznie | 266 | 35% | ~35 |
| hint pełny | 319 | 42% | ~42 |

**v17 to nie jest 50 z marszu.** To pierwszy build, w którym droga do 50 nie
wymaga nowego budżetu — wymaga, by jedno zdanie promptu zadziałało choć
w połowie tak, jak zmierzyli to na `r085`.

**Co by to obaliło:** `actions_per_call` poniżej 6,0 przy poprawnie wstrzykniętym
hikcie (wtedy teza o openerze jest fałszywa i wracamy do cięcia tokenów
z `V16-PLAN.md` §2.1). Bramka jest zaprojektowana tak, żeby to **wykryć
w jednym slocie**, a nie po trzech.

---

## 7. Co wysłać

**Gdyby był jeden slot:** `duck-v15` Gemmy (`07bf05e`) — ma hint, certyfikację
i sondy; brakuje mu tylko capa 2, wartego 0,2 akcji/grę, więc strata jest
znikoma, a ryzyko składania patchy zerowe.

**Gdyby były dwa:** drugi na **v17** z bramką 6,0 — ale wtedy pierwszy slot
zużywa się na to samo, więc sensowniej: **jeden slot na v17**, bo v17 ⊇ v15
Gemmy i bramka mówi, czy iść dalej.

**Czego nie zrobiłem:** nie tknąłem `a450b00f`, `Gemma-konkurs` ani
`Smak-Domu-Konkurs`; nie wysłałem submitu; **nie mam bundla r033**, więc
kompozycji 8 patchy nie zweryfikowałem `git apply`. Weryfikacja plików jest
statyczna (`comm -12` na nagłówkach `diff --git`), nie wykonawcza — i tak to
nazywam.
