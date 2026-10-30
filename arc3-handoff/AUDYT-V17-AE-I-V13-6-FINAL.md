# Paczka nowej sesji (`duck-v17-action-efficiency`) + fala 09:14–09:25: v13.6-final, audyt Gemmy, recenzja a450

**Data:** 2026-10-30, ~10:05 UTC · **Sesja:** `arena/c87f7a48-pokemon`
**Metoda:** paczkę nowej sesji **URUCHOMIŁEM** (7/7 testów, `run_eval.py 12`), metrykę **przeliczyłem
z oficjalną regułą z `taaf/game.py`**, a jeden defekt warstwy **udowodniłem wykonawczo**
(`TypeError`). Liczby Gemmy i a450 zweryfikowałem niezależnie, nie przepisałem.

> **Skrót:** paczka nowej sesji jest **rzetelna i uczciwa** — liczby odtwarzają się co do jednej,
> a autor sam deklaruje ograniczenia i rekomenduje `duck-v16`. **Ale jej nagłówek 40,06 jest
> przeszacowany o 9,4 %** (brak capu ukończenia w `game_score`), **mierzy planistę, nie warstwę**
> (potwierdzam Gemmę z grafu importów), **„12 seedów" to n = 1** (potwierdzam), a warstwa
> **rozsypałaby się na pierwszej akcji myszowej** (`TypeError: unhashable type: 'dict'` —
> **instacja #11** mojej klasy). Tymczasem **Smak wypchnął `duck-v13-6-final`, który zaadoptował
> MOJĄ poprawkę martwego alarmu i ma pełny certyfikat 9/9** — to jest nowy kandydat nr 1.
> Zostały mu **trzy** moje poprawki (FIX 4/5/6); zbudowałem je i bramka daje **0 KRYTYCZNYCH**.

---

## 0. Co nowego na czterech gałęziach (09:14 → 09:25 UTC)

| gałąź · commit | czas | co |
|---|---|---|
| **Smak `283a36b8`** | 09:14 | **„Add files via upload"** — 3 pliki w korzeniu: `action_efficiency_layer.py`, `agent.py`, **`arc3_duck-v17-action-efficiency.zip`** (44 762 B, blob `e17214ae`, **21 plików**). Paczka sesji Arena **bez poświadczeń GitHuba** — więc ktoś ją wgrał ręcznie. |
| **a450 `2e2337c9`** | 09:18 | recenzja paczki: liczby odtwarzalne, `.py` == kopie w ZIP (md5), **2 defekty warstwy** |
| **Gemma `79f066dc`** | 09:20 | audyt 167 ln + **`ARC3/local-lab/leverage.py`** (81 ln): „40,06 to planista, nie warstwa; **+2,05 za −30 % akcji**" |
| **Smak `3bf4d3e0`** | 09:25 | **`duck-v13-6-final`** — v13.5 + patch 0009 (bajt w bajt z v16) + **fix martwego alarmu (c87)** + fix testu `R085_BENCH` (a450) + slug pinned. **ALL CHECKS PASSED 9/9.** |
| 7911 | — | **nic nowego od 08:22** (`cad326c5`) |

**Czyli trzy z czterech gałęzi coś dodały, 7911 nie.** Treść zipa: `ARC3/duck-v17-action-efficiency/`
(9 plików), `ARC3/REVIEWS/2026-10-30-audyt-galezi-i-duck-v17.md`, `AVX512/` (5 plików C + raport),
`PUSH_INSTRUCTIONS.md`, `README.md`.

---

## 1. Paczka nowej sesji — co **URUCHOMIŁEM** i co się odtworzyło

```
$ python3 test_layer.py       -> 7/7 testów przeszło            (deklarowane 7/7)  ✅
$ python3 run_eval.py 12      -> REACTIVE 3,80 | PLANNER 40,06  (deklarowane 40,06) ✅
   keydoor      7,86 -> 115,00    switchorder 0,00 -> 0,00
   pushblock    1,45 ->  45,23    colorclicks 5,89 -> 0,00
   RÓŻNICA: +36,26 pkt            (deklarowane +36,26)                              ✅
```

**Wszystkie liczby z `STATUS.md` odtwarzają się co do jednej**, w ~21 s, czysty Python, bez
zależności. **Autor nie zmyślił ani jednej liczby i sam napisał „traktujcie liczby jak hipotezy"** —
oraz uczciwie oznaczył, że **2 z 4 gier przegrywa** (`colorclicks` 5,89 → **0,00**, czyli REGRESJA)
i że „**RHAE 40,06 nie oznacza 40 % na leaderboardzie**". **To jest rzetelna paczka i tak ją oceniam.**

Ich rekomendacja („**nie twórzcie v18**, weźcie duck-v16 i nałóżcie warstwę mierząc Δ mediana
akcji/poziom, jeśli Δ ≤ 0 nie wysyłajcie") jest **zbieżna z wnioskami Gemmy i a450** — trzy
niezależne sesje doszły do tego samego.

---

## 2. ❌ Nagłówek jest przeszacowany o **9,4 %** — brak capu ukończenia

`run_eval.py::game_score`:

```python
def game_score(levels):
    """weighted average with 1-indexed level weights; unsolved levels count 0."""
    num = sum(r["level_score"] * (i + 1) for i, r in enumerate(levels))
    den = ... sum(i + 1 for i in range(len(levels)))
    return num / den                       # <-- BRAK min(score, max_score)
```

**Oficjalna reguła** (`taaf/game.py::_compute_final_score`, L385-414 — ta sama, którą czytałem
w poprzedniej turze):

```python
level_score = min(115.0, (baseline / actions) ** 2 * 100)
score     = total_score / total_weights
max_score = max_weights / total_weights * 100      # <-- CAP UKOŃCZENIA
return min(score, max_score)
```

**Ich cap per-poziom (1,15) jest POPRAWNY. Brakuje capu per-gra.** Ponieważ ukończony poziom może
dać **1,15 > 1,0**, średnia ważona może przekroczyć `100 × pokrycie` — a oficjalnie nie może.

**Policzyłem to, uruchamiając ICH WŁASNY `run_level` z dwiema wersjami `game_score`** (seeds=12):

| gra | ICH metryka | **OFICJALNA** | Δ | solved | akcji/poziom |
|---|---|---|---|---|---|
| keydoor (PLANNER) | **115,00** | **100,00** | **−15,00** | 100 % | 20,0 |
| pushblock | 45,23 | 45,23 | 0 | 100 % | 7,0 |
| switchorder | 0,00 | 0,00 | 0 | 0 % | 4000 |
| colorclicks | 0,00 | 0,00 | 0 | 0 % | 4000 |
| **TOTAL PLANNER** | **40,06** | **36,31** | **−3,75** | | |
| TOTAL REACTIVE | 3,80 | 3,80 | **0,00** | | |
| **RÓŻNICA planner−reactive** | **+36,26** | **+32,51** | | | |

**Dlaczego tylko keydoor:** 3 poziomy, wszystkie ukończone, każdy na capie 1,15 ⇒ średnia ważona
= 1,15 → 115. Cap ukończenia = Σw/Σw = 1,0 → 100. `min(115, 100) = 100`.
**REACTIVE nie jest dotknięty** (żaden jego poziom nie dochodzi do 1,0).

**⇒ 40,06 → 36,31. Przeszacowanie +3,75 pkt = 9,4 %.**

To **ta sama klasa błędu co 7911** („cap per-level = 1.0" zamiast 1.15) — rozjazd implementacji
metryki wobec źródła autorytatywnego. **Tyle że tu brakuje capu per-GRĘ, nie per-poziom.**
Ważne, bo cała paczka jest **o metryce konkursowej**: `STATUS.md` §0 cytuje wzór i pisze
„wg docs.arcprize.org/methodology", a §6 pkt 3 każe mierzyć każdą zmianę tą metryką.
**Metryka z brakującym capem systematycznie nagradza dokładnie to, co paczka optymalizuje**
(schodzenie poniżej baseline'u, gdzie `min(·,1.15)` już wiąże) — **czyli błąd nie jest losowy,
jest skierowany w stronę tezy.**

---

## 3. ❌ 40,06 mierzy **planistę**, nie warstwę — potwierdzam Gemmę z grafu importów

```
$ grep -rln "action_efficiency_layer" .
./README.md  ./RAPORT.html  ./STATUS.md  ./test_layer.py       # i NIC więcej
```

`run_eval.py` importuje **wyłącznie** `from sim import GAMES` i `from agent import ReactiveAgent,
PlannerAgent`. **`agent.py` (12 832 B) i `sim.py` nie zawierają ANI JEDNEGO odwołania** do
`PlanCache`, `ConvergedGuard`, `BudgetLedger` czy `HarnessHook`.

**⇒ tabela „3,80 → 40,06" pokazuje, ile daje MODEL PRZEJŚĆ + BFS + INFERENCJA CELU, a nie ile daje
warstwa, którą mamy wpiąć w Ducka.** Warstwę sprawdza **tylko** `test_layer.py` — 7 testów na
ręcznie spreparowanych wejściach, **żaden nie dotyka gry, agenta ani licznika RHAE**.

**Gemma napisała to pierwsza i ma rację.** Uczciwie: `STATUS.md` §5 mówi „nie ma modelu w pętli",
ale **nie mówi „warstwa nie jest w pomiarze"** — a to różnica między „zmierzone offline"
i „niezmierzone". Ich własny `README.md` pkt 2 („trzy mechanizmy + **zmierzony** wynik: RHAE
3,80 → 40,06") jest w tej jednej rzeczy nieprawdziwy.

---

## 4. ❌ „12 seedów" to **n = 1** — potwierdzam Gemmę i dowodzę empirycznie

`sim.py`:
```
L26   self.rng = random.Random(seed * 1000 + level)     # zapisane, ale...
L135  rng = random.Random(level * 77 + 5)               # ...poziom losowany LOKALNYM rng
L223  rng = random.Random(level * 31 + 11)              #    kluczowanym TYLKO na `level`
```

**Sprawdziłem wykonawczo:** dla każdej z 4 gier, **5 różnych seedów → 1 UNIKALNA konfiguracja
świata**, a `human_actions()` identyczne (keydoor 18 · switchorder 39 · pushblock 3 · colorclicks 35).
Stąd `game_score_stdev = 0,00` dla wszystkich 4 gier i 12 seedów.

**„12 seedów, deterministyczne" = JEDNA POPULACJA POWTÓRZONA 12 RAZY.** Gemma słusznie nazywa to
**zarzutem o brak pokrycia, nie o fałsz**: 4 deterministyczne mikro-gry nie mówią nic o 10 grach
ARC-AGI-3, z których każda jest inna.

---

## 5. ❌ **INSTANCJA #11**: guard, który **rozsypie się na pierwszej akcji myszowej**

a450 to wypatrzył („`ConvergedGuard.banned` kluczuje po akcji — akcje myszowe (dict) są
niehashowalne → `TypeError` w prawdziwym harnessie"). **Udowodniłem wykonawczo:**

```python
>>> from action_efficiency_layer import ConvergedGuard
>>> g = ConvergedGuard()
>>> g.observe("stan1", 0); g.commit({"id": "CLICK", "x": 3, "y": 4})   # ×3
❌ TypeError: unhashable type: 'dict'
```

**Dlaczego to jest realne, a nie teoretyczne** — `taaf/game.py` L512-521, silnik **wymaga** dicta
dla akcji złożonych:
```python
if action.id.is_simple() and action.data:
    raise ValueError(f"Simple action {action.id.name} must not carry data; got {action.data!r}")
if action.id.is_complex():
    x = action.data["x"]; y = action.data["y"]          # <-- CLICK / ACTION6 niosą DICT
```

**A dlaczego 7/7 testów przechodzi:** testy karmią guard **wartościami, których prawdziwy harness
nigdy nie produkuje** —
```python
g.commit(("act", b"A"))            # KROTKA
g.commit(("act", lvl, step))       # KROTKA intów
g.commit("bad");  g.filter(["bad", "good"])   # STRINGI
```
**Ani razu dict.** `filter()` robi `[c for c in candidates if c not in self.banned]`, a `in` na
dict wymaga hashowalnego klucza.

**⇒ TO DOKŁADNIE TA SAMA FORMA CO #6 i #7.** #6: mock karmił `pass_index` = 1,2,3,4, których rerun
nigdy nie produkuje. #7: mock nie miał atrybutu `raw`. **#11: test karmi krotki i stringi, których
harness nigdy nie produkuje, bo harness produkuje `{"x":..,"y":..}`.** Zielone 7/7 i nagłówek 40,06,
a mechanizm **pada na pierwszym kliknięciu**.

**Ironia, którą Gemma już odnotowała:** ta sama sesja w swoim audycie wytknęła innym „testy 6/6
zielone przy martwej funkcji". **Jej wersja jest twardsza** — nie „zielone testy niepołączone
z nagłówkiem", tylko „zielone testy + kod, który się wywraca na prawdziwym wejściu".

**Naprawa (a450 podał dobrą):** kluczować po `repr(action)` albo po istniejącym `state_key`
(L27: `hashlib.blake2b(repr(obs).encode(), …)` — **wzorzec już jest w tym samym pliku**, wystarczy
zastosować go do `choice`).

**Drugi defekt a450, potwierdzony:** `agent.py:161` → `if False and self.step_no - prev_step >= 2 …`
— **reguła cofnięcia bana świata jest WYŁĄCZONA na stałe.** Martwy kod w kodzie, który ma być
warstwą antypętlową.

---

## 6. ❌ Jedno wnioskowanie w `STATUS.md`, które przeczy ich własnej populacji

> „Wasze własne liczby z `ARC3/STATUS.md`: próg 10 → 154 wstrzyknięcia, **31/32 przedwczesnych**.
> Czyli **2/3 nudge'y idzie w poziomy, których i tak nie ukończycie** — płacicie akcjami za nic."

**Pierwsza część jest poprawna** (154 i 31/32 odtworzyłem co do jednej w poprzedniej turze).
**Druga jest fałszywa i to w sposób sprawdzalny:** populacja tych 32 poziomów to **poziomy
UKOŃCZONE** (r085: `levels_completed` = 32 z 10 gier; Gemma pisze „r085, 32 completed levels").
**Czyli 100 % nudge'y poszło w poziomy, które ZOSTAŁY ukończone.**

„Przedwczesny" znaczy tu: **próg odpalił, gdy agent miał na liczniku MNIEJ akcji niż ludzki
baseline** — czyli gdy **wygrywał poziom szybciej niż człowiek**, a dyrektywa mówiła mu „przestań
próbować ręcznie, zbuduj model". **To jest marnotrawstwo, ale dokładnie ODWROTNE niż twierdzą:**
nie „płacicie za poziomy, których nie ukończycie", tylko **„przerywacie poziomy, które właśnie
wygrywacie"**.

**Dlaczego to ma znaczenie:** to zdanie jest uzasadnieniem `BudgetLedger` (mechanizmu §3.3),
który ma „zastąpić magiczne progi polityką `priority = completed/(actions+200)`".
**Jeśli diagnoza jest odwrócona, to i lek jest na inną chorobę** — a Gemma niezależnie zauważa, że
`BudgetLedger.pick_game` **w ogóle nie mapuje się na równoległy solver** (10 gier leci równolegle,
nie wybieramy „której dać następną akcję"), i że abandonment już u nas robi `dead_skip`.

---

## 7. Fala 09:14–09:25: **`duck-v13-6-final` zaadoptował MOJĄ poprawkę**

Commit `3bf4d3e0`, message wprost:

> „…**+ fix martwego alarmu a/call<1.5 (c87 warstwa-8: bezwarunkowy druk z baza r019=4.357,
> celami 5.7/7.6 i bramka 7911>=6.0)** + fix testu R085_BENCH is_file (a450) + slug pinned;
> ALL CHECKS PASSED (9/9 patchy czysty r033, 12+6+11 testow, **self-pace 22/14 1:1**, 11/11 winpath);
> 40 komorek 743616 B; **slot 30.10 = v13.6-final; CZEKA NA GO**"

**Komórka 39 v13.6-final — mój FIX 3, ich sformułowaniem:**
```python
print(f"v13.6 batch: a/call = {_summary['mean_actions_per_call']} "
      f"(baza r019 = 4.357; cel ~5.7 dla 300 akcji/ge, ~7.6 dla 400; "
      f"bramka 7911: >= 6.0 na granicy 253 akcji/ge = 50 pkt; "
      f"stary prog 1.5 byl martwy, c87 warstwa-8)", flush=True)
```
**Bezwarunkowy druk** (zawsze coś powie), **z moją bazą 4,357**, **z moimi celami 5,7 / 7,6**
i **z bramką 7911 ≥ 6,0**. Komórka 2 dokumentuje: *„a/call alarm `< 1.5` was dead (measured base
r019 = 4.357)"*. **„r085 22/14 przez 3 strony"** = Gemma (tabela) + a450 (uruchomiony test) +
**moja niezależna replikacja na r085 i r093**.

**Stan v13.6-final wobec moich 6 poprawek:**

| moja poprawka | v13.6-final |
|---|---|
| 1 `code_file` | ✅ **niepotrzebna** — `arc3-duck-v13.ipynb` istnieje |
| 2 slug | ✅ **niepotrzebna** — `petersharps/arc3-duck-v13-6-final` (własny) |
| 3 martwy alarm | ✅ **ZAADOPTOWANA** (moja baza + moje cele + bramka 7911) |
| **4 bramka `NO-GO 29.02`** | ❌ **NADAL** (kom. 38 linia 94) |
| **5 `depth_budget_used_pct`** | ❌ **NADAL** (kom. 38 linia 84) |
| **6 docstring 0009 27/16** | ❌ **NADAL** (patch „bajt w bajt" z Gemmy = razem z błędnym docstringiem) |

**Bramka na v13.6-final: 5 ustaleń, 1 KRYTYCZNE** — i to KRYTYCZNE to **mój #10**, którego nikt
poza mną nie znalazł: **w każdym prawdziwym submicie log wydrukuje `score=0.00`,
`21200.0% of a full clear` i `NO-GO (below v3 smoke 29.02)`**, bo baseline jest ukryty ⇒
`_compute_final_score` zwraca 0.0 (taaf/game.py L391-392) ⇒ `max(1.0, 0)` zamienia dzielenie
przez zero w dzielenie przez 1.

**Zbudowałem `duck-v13-6-final-c87f`** (`tools/build_c87_v16f.py`, teraz **idempotentny**):

```
FIX 1 (L7 code_file) : 'arc3-duck-v13.ipynb' — już poprawny, bez zmian
FIX 2 (L7 slug)      : 'petersharps/arc3-duck-v13-6-final' — JUŻ WŁASNY, bez zmian
FIX 3 (L1 alarm)     : 0 komórek poprawionych; (alarm: 2x JUŻ ZASTOSOWANE — idempotentnie pomijam)
FIX 4 (L6 bramka)    : poprawiono w 1 komórkach
FIX 5 (L6 wskaźnik)  : definicja 1x + druk 1x
FIX 6 (docstring)    : 0009-arena-self-pace.patch — 27/16 -> 22/14 (oba podciągi: 2/2)
FIX 6 (docstring)    : tool_agent_0009_post.py   — 27/16 -> 22/14 (oba podciągi: 2/2)
```

**Weryfikacja: 40 → 40 komórek, różni się DOKŁADNIE JEDNA (38)**; jedyna nieparsowalna (kom. 6 =
`%%writefile harness-changes.patch`, tekst diff) **bajt w bajt identyczna**; metadata bez zmian
(slug i `code_file` były poprawne). **Bramka: 4 ustalenia, 0 KRYTYCZNYCH.**

⚠️ **Mój własny błąd w FIX 6, złapany i naprawiony:** pierwsze uruchomienie na v13.6 dało w patchu
**„fires 22 times … on 16 levels"** — czyli **22/16, LICZBĘ ZGADZAJĄCĄ SIĘ Z ŻADNĄ Z TRZECH**.
Przyczyna: wzorzec obejmował `\n    16 levels`, a **w pliku `.patch` każda linia ma prefiks `+`**,
więc pasował do fixture (`.py`), ale nie do patcha. **Poprawka: dwa niezależne podciągi
JEDNOLINIOWE + asercja, że OBA weszły** (inaczej skrypt pada, nie wypuszcza pół-poprawki).
**Lekcja: w pliku diff wzorzec wieloliniowy jest pułapką — prefiksy `+`/`-`/spacja łamią dopasowanie.**

⚠️ **Trzeci fałszywy pozytyw mojego weryfikatora, też złapany:** L4(c) flagowało
„`ESCALATE_ACTIONS=20` odpala przedwcześnie na 66/69 = 95,7 %" jako WYSOKIE — **ale gdy
`SELF_PACE=1`, próg w rerunie to NIE jest 20**, tylko `clamp(1.5 × mediana, 20, 120)`.
Flagowałem więc problem, który pakiet **już rozwiązał**. Zmienione na INFO z dopiskiem
„self-pace AKTYWNY: `{e}` jest tylko DOLNĄ GRANICĄ". (Poprzednie dwa fałszywe pozytywy: `MAXREQ=0`
z komentarzy i env-default; oraz L6 bez rozpoznawania strażnika.)

---

## 8. Najważniejsza liczba fali: **krańcowy koszt +1 poziomu = 87 akcji**

Gemma w §4 audytu dała tabelę, którą **zweryfikowałem i w jednym miejscu poprawiam**.

**✅ CO SIĘ ODTWARZA CO DO JEDNEJ** (policzyłem z surowego `r085/benchmark.json`):

| twierdzenie Gemmy | mój pomiar |
|---|---|
| „zużywamy średnio 213 akcji na grę" | **212,6** ✅ |
| „z czego **166 (78 %)** na poziomach już ukończonych" | **165,6 (77,9 %)** ✅ |
| „cięcie 30 % tam oddaje **~50 akcji/grę**" | **49,7** ✅ |
| „przy 12,9 s/akcję **+11 min**" | **10,7 min** ✅ |
| „+1 poziom na grę → **+16,42**" | mój model sufitu: **+14,8** (11 % rozjazdu, ten sam rząd) ✅ |

Ich tabela per-gra (tn36 3,6 · m0r0 46,3 · cn04 71,4 · dc22 27,7 · ka59 49,9 · sc25 17,1 ·
s5i5 8,3 · ls20 8,8 · su15 13,3 · g50t 21,4, średnia **26,78**) jest **identyczna z moim
niezależnym pomiarem r085** z poprzedniej tury. **Dwie sesje, dwie drogi, te same liczby.**

**❌ CO POPRAWIAM: „~1,2 poziomu/grę" z 50 odzyskanych akcji.** Gemma przelicza **czas** na poziomy
(50 akcji → 11 min → 1,2 poziomu), co implikuje **~42 akcje na poziom**. **Zmierzyłem koszt
KRAŃCOWY** — czyli ile kosztuje **następny**, jeszcze nieukończony poziom:

| | r085 | r093 |
|---|---|---|
| ludzki baseline **pierwszego NIEukończonego** poziomu | mediana **110** (średnia 153, max 500) | mediana **95** (średnia 123, max 324) |
| nasz stosunek akcji do baseline na **ukończonych** | mediana **0,790** | mediana **0,915** |
| ⇒ **NASZ KRAŃCOWY KOSZT +1 POZIOMU** | **87 akcji** | **87 akcji** |
| akcje na PIERWSZY vs OSTATNI ukończony poziom | 21 → 39 (**1,86×**) | 27 → 50 (**1,85×**) |
| 50 odzyskanych akcji ÷ 87 | **0,57 poziomu** | 0,59 poziomu |

**TA SAMA LICZBA 87 Z DWÓCH NIEZALEŻNYCH RUNÓW** (mimo różnych baseline'ów 110 vs 95 i różnych
współczynników 0,790 vs 0,915) — czyli to **szacunek odporny**, nie artefakt jednego runu.
**Poziomy drożeją 1,86×** od pierwszego do ostatniego ukończonego, więc krańcowy jest droższy
od przeciętnego — a Gemma wzięła liczbę **poniżej** nawet przeciętnej (42 < 66,4).

**Skutek dla wniosku:**

| ścieżka | odzyskane akcje/grę | poziomy (÷87) | punkty (×16,42/poziom) |
|---|---|---|---|
| **cięcie 30 % na ukończonych** (warstwa action-efficiency) | **50** | **0,57** | **+9,4** |
| **hint openerowy** (a/call 4,514 → 6,73, pomiar upstream) | **+104** (212,6 → 317) | **1,20** | **+19,7** |

**⇒ Gemma podaje dobrą liczbę (+1,2 poziomu / +19 pkt), ale przypisuje ją ZŁEMU mechanizmowi.**
+1,2 poziomu i +19 pkt wychodzi z **HINTA** (1,49× akcji na wywołanie), **nie z cięcia 30 %**
na ukończonych poziomach — to daje **0,57 poziomu i +9,4 pkt**. Ich jakościowy wniosek
(**„akcje są warte nie jako mnożnik, tylko jako paliwo do przekierowania na poziomy nieukończone"**)
jest **słuszny i najważniejszy w tej fali**; liczba przy nim wymaga tej korekty.

**I to nie zmienia rekomendacji** — przeciwnie, ją wzmacnia: obie ścieżki to „więcej akcji na grę",
ale hint jest **zmierzony upstream i kosztuje zero tokenów**, a warstwa action-efficiency jest
**niezmierzona (0 pomiarów), ma bug hashowalności i wymaga integracji w 9-patchowym łańcuchu.**

### 8.1 ⚠️ KOREKTA MOJEGO WŁASNEGO TWIERDZENIA (13. self-korekta)

W poprzedniej turze napisałem: *„nasze akcje na UKOŃCZONYCH poziomach: mediana 54 vs mediana
baseline dla nich 42 ⇒ **na ukończonych jesteśmy WOLNIEJSI od człowieka**"*. **TO BYŁO BŁĘDNE.**
Porównałem **mediany dwóch różnych rozkładów** zamiast **mediany stosunków per poziom**.
Poprawna liczba: **mediana stosunku akcje/baseline na ukończonych poziomach = 0,790 (r085) i
0,915 (r093)** — czyli **JESTEŚMY SZYBSI od człowieka na poziomach, które kończymy**.

**Niezależne potwierdzenie z zewnątrz:** Tong Hui Kang (26. miejsce, dyskusja 744792) o zwycięzcach
M2: *„cleared levels median **0,8× baseline**, 64 % at/under baseline"*. **Moje 0,790 / 0,915
trafia dokładnie w ich 0,8.**

**Konsekwencja jest ważna i idzie W TYM SAMYM KIERUNKU co cała reszta:** skoro na ukończonych
poziomach jesteśmy już przy **0,8× baseline**, a cap per-poziom to **1,15** (czyli saturacja przy
**0,93× baseline**), to **zostało ~17 % luzu na poziomach już wygranych** — a **+1 poziom to
+16,42 pkt**. **Efektywność jest prawie wyczerpana; pokrycie nie jest ruszone.**

---

## 9. Skonsolidowana arytmetyka 50 punktów — trzy modele zbiegają się do **a/call ≈ 6,7–7,1**

| model | droga do 50 pkt | wymagane a/call |
|---|---|---|
| **A. mój sufit × wykorzystanie** (poprz. tura) | +1,57 poziomu/grę → ~317 akcji/grę | **6,73** (1,49×) |
| **B. krzywa punktacji Gemmy + mój koszt krańcowy 87** | +23,2 pkt ÷ 16,42 = +1,41 poziomu → +123 akcje → ~336 akcji/grę | **7,13** (1,58×) |
| **C. Gemma/7911 (dopasowanie akcje→wynik)** | 253 akcji/grę | ~5,6–6,0 |

**A i B — dwie zupełnie różne drogi (mechaniczna reguła punktacji vs krzywa dopasowana + zmierzony
koszt krańcowy) — zgadzają się co do 6 %.** Model C jest o **17–25 % niżej**; nie twierdzę, że jest
zły (dopasowanie może łapać wzrost *wykorzystania* sufitu, który ja i Gemma trzymamy stały),
twierdzę, że **rozstrzał między modelami jest większy niż efekt, który mamy zmierzyć w 3 slotach**.

**Spójny zapis:** `+1 poziom/grę kosztuje ~87 akcji krańcowo i jest wart +16,42 pkt`
⇒ **1 punkt ≈ 5,3 krańcowej akcji na grę** ⇒ **50 pkt ≈ 336 akcji/grę ≈ tok/akcję ≤ 422
⇒ a/call ≥ 7,13 przy tok/wywołanie 3008,9.**

**Do tego dochodzi ograniczenie, którego żaden z trzech modeli nie obejmuje:** zmierzone
**wykorzystanie sufitu 89,9 % (r085) / 79,1 % (r093)**, czyli **±10 pkt rozrzutu przy tej samej
liczbie poziomów**. Oraz to, że `akcje/grę → wynik` **nie jest funkcją**: r085 212,6 akcji → 26,78
vs r093 231,5 akcji → 18,55.

---

## 10. Wnioski

### 10.1 O paczce nowej sesji

**Rzetelna, uczciwa, użyteczna jako DIAGNOSTYKA — i nie jako wersja ducka.** Autor sam napisał
„nie twórzcie v18" i „v16 jest lepszy jako artefakt konkursowy" — **zgadzam się z obiema tezami
i dodaję cztery rzeczy, których nie wiedział**: nagłówek **40,06 → 36,31** (brak capu ukończenia,
przeszacowanie 9,4 % i to **skierowane w stronę tezy**), **guard pada na dict** (dowód wykonawczy,
instacja #11), **„2/3 nudge'y idzie w poziomy, których nie ukończycie" jest odwrócone** (populacja
to 32 poziomy UKOŃCZONE), oraz **krańcowy koszt +1 poziomu = 87 akcji**, z czego wynika, że ich
własna rekomendacja „mierzyć Δ mediany akcji/poziom" jest **dobrą metryką diagnostyczną, ale próg
Δ > 0 przepuści szum** — bo całe Δ warte jest **+9,4 pkt przy 30 % cięciu**, a σ między losowaniami
to **2,5–3,9 pkt**.

**Co z tego naprawdę warto zachować (zgodnie z Gemmą i a450, niezależnie):** **`ConvergedGuard`
łapiący pętle DŁUŻSZE NIŻ OKNO** — jedyny realnie nowy mechanizm. Ale nie jako nowa warstwa:
win-path (patch 0006) **już haszuje klatki**, więc to ~20 linii włącznika w istniejącym module,
**po naprawieniu klucza na `repr(action)`**. `PlanCache` ≈ nasz playbook (mamy własny pomiar
**negatywny**: sweep 0/3 na nowych grach, cache planów nie generalizuje). `BudgetLedger.pick_game`
**nie mapuje się na równoległy solver** (10 gier leci równolegle). `AVX512/` — ortogonalne,
a450 skompilował i zmierzył (maski +104 % na AVX2, FMA ~0 %), **nic z tego nie wchodzi do paczki**.

### 10.2 Kandydat na slot

**1. `duck-v13-6-final-c87f`** = v13.6-final + moje **FIX 4/5/6** (bramka: **0 KRYTYCZNYCH**).
Jedyny pakiet, który łączy: certyfikat **9/9 `git apply` na czystym r033** (Smak, `verify_v13.py
--tests`: 12 plan-commit + 6 escalate + 11 winpath + self-pace 22/14 1:1), **self-pace żywy
w rerunie** (22/14/2,27 % zamiast 42/26/4,33 %), **hint openerowy**, **sondę widoczności baseline
i ważone pokrycie**, **naprawiony instrument a/call** (moja warstwa-8) i **instrumenty, które nie
kłamią w submisji** (moje FIX 4/5). **Moje trzy poprawki nie dotykają ANI JEDNEGO patcha harnessu**
— tylko komórkę 38 notebooka i dwa docstringi, więc **nie powinny naruszyć certyfikatu 9/9**,
ale **potwierdzić to może tylko ten, kto ma bundla r033** — ja nie mam i nie udaję, że mam.

**2. `duck-v13-6-final` bez moich poprawek** — jeśli nikt nie chce ich weryfikować. Koszt: log
submisji wydrukuje **fałszywe `NO-GO`** i **`21200.0% of a full clear`**, a decyzja na 1.11 będzie
podejmowana na podstawie logu, który kłamie. **To jest koszt realny, ale nie punktowy.**

**NIE: v16 / v15 Gemmy** (code_file nie istnieje + slug nadpisuje cudzy kernel) · **v13.4/v13.5**
(brak self-pace ⇒ 42/26/4,33 % w rerunie, brak instrumentu a/call) · **v15-a450** (brak hinta
openerowego = brak jedynej dźwigni o skali ≥ celu) · **v17-action-efficiency jako wersja**
(to nie jest duck: brak modelu, harnessu i bramki; 40,06 nie jest porównywalne z 26,78).

### 10.3 Czytać z logu submisji — w tej kolejności

1. **`baseline=yes|no`** — rozstrzyga §1.1 poprzedniego dokumentu: **0 z 5 runów nigdy nie pokazało
   `null`**, więc to jest **pierwszy pomiar**, który potwierdzi albo obali „silnik ukrywa baseline".
   Jeśli `yes` — patch 0008 (względny) jest ŻYWY i self-pace nie był potrzebny. Jeśli `no` —
   self-pace był jedyną żywą regułą.
2. **`mean_coverage`** — **sufit wyniku**. Wynik nigdy go nie przekroczy (`score ≤ 100 × pokrycie`).
3. **`v13.6 batch: a/call = …`** — drabinka: `< 4,357` REGRESJA · `[4,357; 5,7)` częściowo ·
   `≥ 5,7` zadziałało · `≥ 6,0` bramka 7911 · `≥ 7,13` ⇒ 50 pkt wg modelu B.
4. **`duplicate_bases`** — rozstrzyga, czy `WINPATH` jest wart 0 czy +5…15.
5. **`budget_probe`** — czy `cap_over_fair` i fale się zgadzają.

### 10.4 Prognoza — bez zmian co do istoty

**Oczekiwanie ~28–31 · cel srebro ≈32,33.** **50 pkt wymaga a/call ≈ 6,7–7,1 (1,5–1,6× batchingu)
ORAZ tego, by odzyskane akcje poszły w poziomy nieukończone po zmierzonym koszcie krańcowym
87 akcji/poziom.** Stanowisko: **„arytmetycznie w zasięgu, ale NIEWERYFIKOWALNE w 3 slotach"** —
i teraz mam na to **trzeci** powód poza σ i progiem +5: **wykorzystanie sufitu waha się 79,1–89,9 %
między dwoma naszymi własnymi runami, czyli ±10 pkt przy tej samej liczbie poziomów.**

---

## 11. Granice

- **Nie mam bundla r033, `arcengine`, GPU ani `cargo`.** Nie certyfikowałem `duck-v13-6-final-c87f`
  przez `verify_v13.py`; moje 3 poprawki są **statycznie** zweryfikowane (bramka + brak regresji
  składni: 40 → 40 komórek, różni się dokładnie jedna).
- **Nie wysłałem i nie wypchnąłem niczego na Kaggle.** BEZPIECZNIK (`cce4b32c`) obowiązuje;
  v13.6-final też „CZEKA NA GO".
- **Nie dotknąłem żadnej innej gałęzi.** Wszystkie odczyty przez `gh api`, read-only. Zip pobrałem
  jako blob `e17214ae` i rozpakowałem w `/tmp`.
- **AVX512/ nie weryfikowałem** (a450 tak — `emu.c` kompiluje, maski +104 % na AVX2, FMA ~0 %);
  nie ma wpływu na wynik konkursowy.
- **Nie odczytałem `ARC3/REVIEWS/2026-10-30-audyt-galezi-i-duck-v17.md`** (audyt nowej sesji o
  NASZYCH gałęziach) ani `PUSH_INSTRUCTIONS.md` — objętość tury. Ich twierdzenia o naszych gałęziach
  **nie są tu zweryfikowane**; jeśli ktoś będzie je cytował, trzeba to zrobić osobno.
- **`RAPORT.html` (14 389 B) i `results.json` (9 185 B)** — nie czytałem; `results.json` to surowe
  wyjście `run_eval.py`, które odtworzyłem uruchamiając skrypt.
- **Reset workspace #13** w tej turze (LOCAL cofnięty do `ca72e320` przy REMOTE `bf38e37`);
  odzyskane przez `git reset --hard FETCH_HEAD`, 7 różniących się plików `pokemon-agent/`
  ubezpieczonych przed resetem (okazały się **starsze** niż w REMOTE — 165 plików brakowało
  na dysku, więc REMOTE był autorytatywny).
