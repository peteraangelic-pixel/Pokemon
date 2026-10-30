# Audyt `duck-v13-7-final` i czterech opinii o nim — 2026-10-30, fala 13:40–14:19 UTC

**Zakres.** (1) `duck-v13-7-final` z gałęzi `Smak-Domu-Konkurs@arena/5ed750ef`, rev1 `402b3475`
i rev2 `72761737`. (2) Opinia `a450b00f-pokemon` (7 komitów 13:42–14:14). (3) Opinia z gałęzi
`Gemma-konkurs@arena/6d081d52` zacytowana przez usera (komit `568420c` lokalny; **wypchnięta
w trakcie tej tury** jako `8799b6c4` 14:04 i `9f2b4e63` 14:06). (4) Audyt
`Gemma-konkurs@arena/c4eeb067` `4ac0a5c9` 13:55.

**Metoda.** Wszystko, co dało się uruchomić, **uruchomiłem**: pełny certyfikat `verify_v13.py
--bundle r033 --tests` (bundel jest w repo — patrz §2), 16 testów patcha 0010, symulator Gemmy
`sim_dyn_budget.py`, własny symulator per-akcja, rekonstrukcja modułu z **mojego** patcha 0004.
Nie wziąłem na słowo ani jednego hashu, ani jednej tabeli.

**Uczciwość co do pierwszeństwa.** Kolano ABANDON przy ≤20k znalazły **a450 (`c4dc99c9` 14:14:14Z)**
i **Smak (`3945d727` 14:18:57Z)** — zanim skończyłem. Mój pomiar jest **niezależną replikacją**,
nie odkryciem. To, co jest moje, jest oznaczone wprost w §8, §10, §11, §12 i §14.

---

## 0. Fala w kolejności

| czas (UTC) | gałąź · komit | co |
|---|---|---|
| 13:40:50 | Smak `999f9194` | upload `arc-arena-handoff-30-10.zip` (handoff „sesji strategii") |
| 13:42:16 | a450 `f7a08aa8` | v13.6-final zweryfikowana (ALL CHECKS PASSED odtwarzalne) |
| 13:44:50 | a450 `7ce86077` | weryfikacja handoffu v16-naj + korekta atrybucji 40,06 |
| 13:49:38 | **Smak `402b3475`** | **`duck-v13-7-final` rev1** (25 plików) |
| 13:50:04 | Smak `de57e4d8` | SYNC §22 + CHAT-LOG |
| 13:51:42 | a450 `278f5964` | v13.7 zweryfikowana (10/10 patchy, 0010 dormant) |
| 13:55:15 | Smak `94f48547` | `naj.txt` (16 ln) |
| 13:55:37 | Gemma c4eeb067 `4ac0a5c9` | audyt v13.7 + `local-lab/sim_dyn_budget.py` |
| 13:57:50 | a450 `7ef2fe09` | adjudykacja opinii 6d081d52, uzbrojenie 20k przyjęte |
| **13:59:58** | **Smak `72761737`** | **v13.7 rev2: arming 20000 (nie 60000)** + SPROSTOWANIE |
| 14:02:12 | a450 `90934193` | v17-arena-dyn niezweryfikowalne bez pusha |
| 14:04:42 | Gemma 6d081d52 `8799b6c4` | **PUSH** audytów 13.x–17 + v17-arena / v17-arena-dyn |
| 14:06:09 | a450 `30ef58b5` | v17-arena-dyn 11/11 zweryfikowane + v13.7 rev2 |
| 14:06:46 | Gemma 6d081d52 `9f2b4e63` | audyt eskalacji + fixtures benchmarków |
| 14:11:19 | Smak `d0bec95f` | SYNC §24: v17-arena-dyn zweryfikowany u nich w całości |
| **14:14:14** | **a450 `c4dc99c9`** | **sweep capa 10k–20k na prawdziwym module — kolano** |
| **14:18:57** | **Smak `3945d727`** | **SYNC §25: replikacja sweepu cyfrą w cyfrę + krytyka poolingu + ocena fixów c87** |

**Cztery sesje zeszły się w 39 minut** na tym samym wniosku operacyjnym. To rzadkie i warto to
odnotować: spór nie dotyczy już faktów, tylko wagi nieumierzalnego zysku.

---

## 1. Tożsamość łańcucha — udowodniona z **mojego** patcha, nie z ich drzewa

Patch `0010-dyn-level-budget` (12 275 B) nie jest nowy: to upgrade modułu
`framework/arc3_level_budget.py`, który **tworzy mój `0004-level-token-cap.patch`**. Zrobiłem
rekonstrukcję od drugiej strony niż ktokolwiek:

```
mój 0004 (--include framework/arc3_level_budget.py)  -> 142 linii
  + git apply 0010-dyn-level-budget.patch            -> check OK, APPLIED
  cmp z ich src/arc3_level_budget_v13_2.py           -> BAJT W BAJT (md5 9c184195 oba)
  git apply -R --check 0010 na ich pliku             -> PRZESZEDŁ (odwracalny)
```

**Hash patcha 0010 potwierdzony obiema funkcjami, czyli obie gałęzie miały rację:**
md5 `7194ab32` (a450) **i** sha256 `736b09cf64ec` (6d081d52). `0009-arena-self-pace.patch`
w v13.7 == ten sam plik w Gemmy v16: md5 `9cdc3c74`, sha256 `94619210820c` — **proweniencja
bajtowa, którą Smak chroni, jest prawdziwa** (§13).

**Korekta atrybucji z mojej strony:** w notatkach miałem `tools/arc3_level_budget.py` jako moje
narzędzie. **Nie istnieje** — mam 11 `.py` + 2 `.sh`, a moduł budżetu żyje wyłącznie jako
`framework/arc3_level_budget.py` tworzony przez mój patch 0004. Poprawione.

---

## 2. Bundel r033 **JEST w repozytorium** — certyfikat da się uruchomić offline

Przez dwie tury pisałem, że zgodność moich poprawek z certyfikatem „potwierdzić może tylko ten,
kto ma bundla r033". **To było nieprawdziwe i sam to teraz obalam.** Bundel leży w repo Smak:

```
arc-agi-3/kaggle/ops/results/r033-recon-bundle/    74 pliki, 1,7 MB
  bundle/src/ARC3-Inference/inference/framework/solver.py     49 315 B
  bundle/src/ARC3-Inference/inference/agent/tool_agent.py     89 299 B
  bundle/src/tufa-arc-agi-framework/src/taaf/game.py          30 002 B
  bundle/benchmark_initial.pkl · deploy_target.pkl · setup_commands.json · preamble.txt
```

**Uruchomiłem pełny certyfikat.** Zależności: `requests`, `numpy`, `pillow`
(`pip install --break-system-packages`). Wynik na surowym v13.7 rev2:

```
51 OK / 1 FAIL     (skrypt ma 43 wywołania check(); rev1 miał 42)
FAIL = "11 winpath tests pass on patched tree"
       8 błędów = ModuleNotFoundError: No module named 'arcengine'
       1 asercja = test_playbook_prefix_match_and_replay: maybe_replay -> False
```

`arcengine` **wymaga Pythona ≥ 3.12**, sandbox ma 3.11.2 i tylko `python3.11`. To **jedyna**
kontrola nie do odtworzenia u mnie — limit środowiska, **nie wada pakietu**. Reszta przeszła,
w tym trzy najważniejsze:

```
OK  all ten patches extracted · applies: harness-changes + duck-extra-00..08
OK  patched tree compiles
OK  self-pace tests pass (22/14 on r085, 1:1 from shipped code)
OK  0010 reconstruction == patched tree bytes (cmp)
OK  16 dyn-budget tests pass (on shipped bytes)
```

**I uruchomiłem ich `tests/test_self_pace.py` wprost — drukuje:**

```
4. r085, 32 poziomy:  rel+baseline=8/0  floor20=42/26  self-pace=22/14   (nudge/przedwczesne)
```

**Wszystkie pięć moich liczb eskalacyjnych odtwarza się z ich wysyłkowego kodu**: 8/0, 42/26,
**22/14**. Trzecia niezależna reprodukcja po Gemmie i a450 — a450 pisze „mają już 3 niezależne
reprodukcje (Gemma, a450, Smak)"; z tą jest czwarta, **z mojej strony**.

---

## 3. rev2 to zmiana **komentarza**, nie konfiguracji

Diff komórek rev1 → rev2 (wyrównany, nie pozycyjny):

```
komorek rev1=41  rev2=41      ROZNIĄCE SIĘ: [2]      758 240 B -> 759 109 B
```

Komórka 2 dostała 10 linii komentarza („UZBROJENIE (korekta po opinii Gemmy 6d081d52…)").
**`ARC3_VARIANT` w komórce 1 jest nietknięty i nadal ma `"ARC3_LEVEL_TOKEN_CAP": "0"`.**

⇒ **Komunikat komitu „v13.7 rev2: arming 20000 (nie 60000)" opisuje rekomendację w komentarzu,
nie zmianę konfiguracji.** To **dobra** wiadomość dla slotu 30.10 (zero zmiany zachowania), ale
warto to wiedzieć: uzbrojenie nadal jest ręcznym flipem, którego w pakiecie nie ma.

**Nikt z trzech recenzentów nie oglądał rev2** — wszystkie ich hashe i rozmiary (41 komórek /
758 240 B / md5 `0be69523`) dotyczą rev1. Md5 rev1 potwierdzam: **`0be69523`** ✓.

---

## 4. Dormancja: z kodu **i** z pomiaru

```python
self.dyn_enabled = _env_bool("ARC3_DYN_CAP", True) and self.static_cap > 0
@property
def enabled(self): return self.static_cap > 0          # peek: if not self.enabled: return KEEP_GOING
```

`ARC3_LEVEL_TOKEN_CAP="0"` ⇒ `static_cap = 0` ⇒ `enabled` False ⇒ `peek` zwraca `KEEP_GOING`
**przed jakimkolwiek liczeniem**. Uruchomione narzędzie Gemmy potwierdza:

| cap | r085 | r093 |
|---|---|---|
| `0` (wysyłane) | `keep_going=2126`, **0 decyzji** | `keep_going=2315`, **0** |

**2126 akcji = dokładnie liczba Gemmy c4eeb067.** Ich „dormant naprawdę dormant" ✓, i teraz
mam to z dwóch stron: z kodu i z traktu. `ARC3_DYN_CAP=0` ⇒ `dyn_enabled` False ⇒ gałąź
statyczna, **bajtowo równoważna decyzjom 0004** — kill-switch A/B Smaka potwierdzony w kodzie.

---

## 5. Kolano przy ≤20k — replikacja i **moje systematyczne niedoszacowanie**

Mój symulator (per-akcja, `step()`, ten sam zrekonstruowany moduł, 40 gier r085/r093/r110/r118):

| cap | RESET (ja) | AB gier (ja) | utracone poz. (ja) | uwolnione tok (ja) | a450/Smak: RESET / AB / utracone / uwolnione |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 / 0 |
| **20000** | **45** | **18** | **9** | **517 067** | **48 / 20 / 15 / 667 937** |
| 30000 | 40 | **0** | 0 | 0 | 43 / 0 / 0 / 0 |
| 45000 | 30 | **0** | 0 | 0 | 32 / 0 / 0 / 0 |
| 60000 | 24 | **0** | 0 | 0 | 28 / 0 / 0 / 0 |

**Zgodność jakościowa całkowita: ABANDON = 0 przy 45k i 60k, przełącznik dopiero przy ≤20k.**
Per-run przy 20k (ja): r085 **2** gry, r093 **6**, r110 **0**, r118 **10/10** (9 przy 0 ukończeń).
Ich per-run: 3/7/0/10. Kierunek i kształt identyczne.

**Wielkości mam systematycznie o 7–22 % niższe.** a450 wyjaśnia to wprost i **nie opublikował
narzędzia** (komit `c4dc99c9` to 28 linii dokumentu), więc nie mogę tego domknąć:

> „Rozbieznosc z symulacja galezi 6d081d52 (18 gier, 3 utracone): ich symulacja jest poziomowa
> (decyzja na koncu poziomu; galaz progresu w step() uprzedza porzucenia srodpoziomowe) —
> niedoszacowuje. Solver wola step() co akcje, wiec powyższe jest blizsze prawdziwemu zachowaniu."

**Uwaga: liczby „18 gier, 3 utracone" to MOJE liczby**, i a450 ma rację co do „3" —
**było błędne, poprawiam na 9** (§14, korekta 14). Przyjmuję ich 48/20/15/667 937 jako lepsze
oszacowanie i **nie utrzymuję własnego**; różnica nie zmienia żadnego wniosku, bo obie strony
mają ABANDON = 0 powyżej 20k i niezerowy poniżej.

---

## 6. Arytmetyka progu ABANDON — dlaczego kolano jest tam, gdzie jest

Z kodu: ABANDON wymaga `resets_used >= max_resets` **oraz** `spent >= abandon_mult × _current_cap()`
**w jednej próbie**. Przy `ladder = 1.5`, `abandon_mult = 1.5`, `max_resets = 1` i braku historii:

```
próba 1: cap = V                      -> RESET przy spent >= V
próba 2: cap = V × 1.5                -> ABANDON przy spent >= 1.5 × 1.5 V = 2.25 V
łącznie: ~ V + 2.25 V = 3.25 V tokenów, zanim gra zostanie porzucona
```

| V | 3.25·V | vs pula tokenów | zmierzone |
|---|---|---|---|
| 20 000 | 65 000 | ≪ 141 718 (r085), ≪ 152 196 (r093), < 81 864 (r118) | **ABANDON żywy** ✓ |
| 45 000 | 146 250 | na krawędzi 152 196 | 0 ✓ |
| 47 000 | 152 750 | **powyżej** każdej puli | 0 ✓ |
| 60 000 | 195 000 | powyżej każdej puli | 0 ✓ |

Zmierzone mediany tokenów w chwili ABANDON: **67 397 (r118), 73 193 (r085), 89 663 (r093)** —
spójne z 3.25·V = 65 000 plus podłoga dynamiczna u gier z historią.

**⚠️ To jest OGRANICZENIE, nie prawo.** Przy V = 30 000 i 40 000 wzór przewiduje „osiągalne"
(97 500 i 130 000 ≤ 152 196), a pomiar daje **0**. Powód: podłoga dynamiczna
`mediana × 4` (mediana kosztu ukończonego poziomu = **27 613** ⇒ ×4 ≈ 110 000) podnosi cap
u gier z historią ponad próg. **Poprawny zapis: `3.25·V > pula` ⇒ ABANDON niemożliwy;
`3.25·V ≤ pula` ⇒ możliwy, ale nie przesądzony.** Granica praktyczna wypada przy **V ≈ 47 000**
(zmierzone: 47k → 26 RESET / 0 ABANDON; 50k → 26 / 0; 55k → 24 / 0).

---

## 7. `MIN_DONE=1` — pełna zbieżność ze Smakiem

Zmierzyłem niezależnie: przy cap 20 000 `MIN_DONE=1` zbija ABANDON z 18/40 na **6/40**, ale
**utracone zbankowane poziomy zostają te same** — bo tłumione są dokładnie te porzucenia, które
nic nie kosztują (gry przy 0 ukończeń), a zostają te, które kosztują.

Smak SYNC §25B formułuje to lepiej i dochodzi do tego samego:

> „MIN_DONE=1 NEUTRALIZOWAŁBY cel patcha (blokuje 13/20 „bezstratnych" ABANDONÓW, zostawia
> 7 kosztownych) — zostaje 0."

**Zgoda, bez zastrzeżeń.** Uwaga porządkująca: `ARC3_LEVEL_MIN_DONE` nie jest „metryką ochronną"
— ochronną metryką jest `completed/game` przed/po, co Smak pisze osobno i słusznie.

---

## 8. ❗ RESET **jest akcją** w sensie RHAE — wada mojego własnego patcha 0004

To jest moje i nikt z czterech sesji tego nie podnosi. Dowód end-to-end:

```python
# solver.py:663 (bundel r033)
def _execute_auto_reset(self) -> None:
    action = arcengine.ActionInput(id=arcengine.GameAction.RESET, data={})
    self._execute_action(action, batch_index=1, batch_size=1, generated_tokens=0)
# -> _execute_action -> self.game.execute_action(action, generated_tokens=0, ...)

# taaf/game.py:184   """Legal action ids, with RESET (0) always present."""
# taaf/game.py:497   def execute_action(...)  -- BRAK jakiegokolwiek wyjątku dla RESET
# taaf/game.py:571   self.game_run.actions_per_level[level_before] += 1
# taaf/game.py:582   assert sum(actions_per_level) == len(history)
```

**RESET kosztuje zero tokenów (`generated_tokens=0`) i dokładnie JEDNĄ akcję**, doliczoną do
`actions_per_level[level_before]` — a ponieważ `ONLY_RESET_LEVELS=true` zachowuje poziom
(`game_api.py:221`, potwierdzam w źródle razem z komentarzem wyjaśniającym, dlaczego flaga musi
być ustawiona **po** `arcade.make`), **licznik tego poziomu rośnie dalej: akcje próby 1 nie są
zwracane.**

Mój patch 0004 loguje `"%s: level budget exhausted (%s) - issuing a free RESET"` i mówi w
docstringu „It costs zero LLM tokens (no analyzer call)". **Zdanie o tokenach jest prawdziwe.
Słowo „free" jest fałszywe w sensie RHAE**, gdzie `poziom = min((baseline/akcje)², 1.15)`.

**Ale raz zmierzone, ten zarzut obraca się NA KORZYŚĆ uzbrojenia 20 000:**

| cap | RESET-ów | akcje już zbankowane na poziomie w chwili cięcia: mediana / suma / max | tokeny progu: mediana |
|---|---|---|---|
| **20 000** | 45 | **24 / 1 291 / 100** | 22 363 |
| 45 000 | 30 | 62 / 1 997 / 156 | 49 594 |
| 60 000 | 24 | 64 / 1 754 / 219 | 63 497 |

**Niższe uzbrojenie tnie WCZEŚNIEJ, więc każdy RESET osieroca mniej akcji w mianowniku RHAE** —
mediana 24 zamiast 64, suma 1 291 zamiast 1 754, mimo że resetów jest 45 zamiast 24. Sam koszt
RESET-ów jako akcji jest znikomy (45 akcji / 40 gier ≈ 0,5 % budżetu ~213 akcji/grę); istotne
jest to, ile akcji próby-1 zostaje w liczniku poziomu, i tu **20k jest tańsze niż 60k**.

**Wniosek, którego wcześniej nie było:** uzbrojenie 0010 zmienia **profil akcji**, nie tylko
profil tokenów. Dlatego log z 1.11 trzeba czytać także przez `actions/game`, nie tylko przez
`completed/game` — inaczej bieg, który wymienia akcje na tokeny, wygląda na wygraną.

---

## 9. Marnotrawstwo: pool 64,5 % odtworzony — ale to statystyka ZŁYCH runów

Policzyłem z surowych `benchmark.json` (segmentacja `sum(actions_per_level[:levels_completed])`):

| run | mediana | max | średnia | gry z 0 ukończeń | tok/grę | ukończone |
|---|---|---|---|---|---|---|
| r085 | **19,7 %** | 92,9 % | 27,3 % | 0/10 | 141 718 | 32 |
| r093 | **33,7 %** | 100 % | 44,9 % | 1/10 | 152 196 | 27 |
| r110 | **100 %** | 100 % | 80,6 % | **6/10** | 44 878 | 4 |
| r118 | **100 %** | 100 % | 91,0 % | **8/10** | 81 864 | 2 |
| **pool 40** | **64,5 %** | **100 %** | 61,0 % | 15/40 | — | 65 |

**Pool 64,5 % / max 100 % odtwarza się dokładnie** (6d081d52 i a450) ✓. Ale rozkład mówi, skąd
się bierze: **produkują go wyłącznie r110 i r118**, gdzie 14 z 20 gier nie ukończyło niczego.
Na dwóch runach, które dały zmierzone wyniki 26,78 i 18,55, mediana wynosi **19,7 % i 33,7 %**.

**Godzę trzy liczby krążące w tej fali — wszystkie są poprawne, to różne statystyki:**

| liczba | co to jest | kto |
|---|---|---|
| **25 %** | udział **ważony tokenami** na r085 (35 496 / 141 719) | Gemma c4eeb067 |
| **27,3 %** | **nieważona średnia** udziałów per gra na r085 | ja |
| **64,5 %** | **mediana per gra** po 4 runach (zdominowana przez r110/r118) | 6d081d52 / a450 |

Smak SYNC §25C potwierdza to moimi liczbami i domyka interpretację: **„0010 ma dwie motywacje
żyjące w różnych reżimach"** — przy 20k tnie głównie złe runy (0-ukończone), a w dobrych chroni
drogie poziomy przez `mediana × 4`. To porządkuje spór „25 % vs 64,5 %" lepiej niż którakolwiek
ze stron.

**Koszt ukończonych poziomów (65 sztuk z 4 runów):** `>45k: 14` ✓, `>60k: 13` ✓ — dokładnie
jak w cytacie. **max = 91 043** (= a450), **nie 88 114** (= cytat); a450 odnotował to jako
„drobna różnica segmentacji" i **potwierdzam: moja segmentacja daje 91 043, czyli zgadza się
z a450, a nie z cytatem**. Mediana kosztu ukończonego poziomu = **27 613**.

---

## 10. `cap = max(static, mediana×4)` — dowód z kodu, mocniejszy niż z danych

Cytat wyprowadza „reguła z konstrukcji tylko poluzowuje" z pomiaru (16/40 gier, 15 luźniej,
0 ciaśniej). **Z kodu wynika to bez pomiaru:**

```python
self.cap_min = max(1, _env_int("ARC3_DYN_CAP_MIN", self.static_cap or DEFAULT_CAP_MIN))
self.cap_max = max(self.cap_min, _env_int("ARC3_DYN_CAP_MAX", DEFAULT_CAP_MAX))
...
base = float(self.static_cap)
if len(self._level_costs) >= 2:
    base = max(base, median(self._level_costs) * self.cap_mult)
base = min(max(base, self.cap_min), self.cap_max)
return int(base * (self.ladder ** self.resets_used))
```

`cap_min = static_cap` (domyślnie!) i `cap_max = max(cap_min, 150k) ≥ cap_min`, więc
`base ∈ [static_cap, cap_max]`, a `ladder^resets ≥ 1`. **⇒ `_current_cap() ≥ static_cap`
ZAWSZE.** Reguła **nie może** ciąć ciaśniej niż wartość uzbrojenia — to tożsamość, nie obserwacja.

Dwie rzeczy, które z tego płyną i których w cytacie nie ma:

1. **`DEFAULT_CAP_MIN = 45_000` jest w praktyce MARTWE** — `_env_int(..., self.static_cap or
   DEFAULT_CAP_MIN)` podstawia `static_cap`, gdy ten jest niezerowy. Przy uzbrojeniu 20 000
   podłoga wynosi **20 000**, nie 45 000. Stała 45 000 obowiązuje tylko wtedy, gdy nikt nie
   uzbroi capa — a wtedy cały moduł jest uśpiony. **To wzorzec „dead constant" w mojej
   taksonomii, tylko że nieszkodliwy.**
2. **„Jedyna dźwignia tnąca w 0010 to sam arming"** — czyli gałka patcha **0004**, nie 0010.
   Dlatego właśnie wartość 20 000 (a nie 60 000) jest całą treścią tej zmiany i dlatego
   „wybór wartości nie ma dziś znaczenia" (Gemma c4eeb067, zmierzone na 0/45k/60k) **nie
   przenosi się na 20k** — przekracza granicę reżimu z §6.

**Potwierdzam obie uwagi o kodzie z cytatu:** docstring *„a cheap game is cut much sooner than a
flat 45k ever would"* jest **fałszywy przy 60 000** (podłoga = arming = 60 000) i prawdziwy przy
20 000 **tylko ścieżką statyczną** — a450 ujął to trafnie („przy 60k fałszywy, przy 20k
prawdziwy"). Oraz: **drabina RESET mnoży PO clampie** (`int(base * ladder**resets)` za
`min(..., cap_max)`), więc cap może wynieść **150 000 × 1.5 = 225 000 > cap_max** ✓ —
`describe()` drukuje wtedy `cap=225000, max=150000`, co wygląda na sprzeczność, a jest
dokumentowanym zachowaniem. Kosmetyka, nie błąd.

**@60000, policzone przeze mnie na 40 grach:** aktywny (≥2 ukończone) w **16/40** ✓,
**15 luźniej / 0 ciaśniej** ✓, mediana capa w tych 16 = **129 372** (cytat: **128 612**, 0,6 %
różnicy — ta sama rozbieżność segmentacji co przy max 91 043 vs 88 114). **Co do jednej liczby
jak u nich, z tym samym zastrzeżeniem co u a450.**

---

## 11. ❌ „v13.7 = mój duck-v16, zachowuje się dokładnie jak v16" — obalone

Gemma c4eeb067 `4ac0a5c9`: *„v13.7 = **moje duck-v16** + patch 0010, bajt w bajt na każdym
wspólnym artefakcie … więc na submisji v13.7 **zachowuje się dokładnie jak v16**"* oraz
*„Diff komórek v16 → v13.7 to **5 pozycji** … **Zero zmian w logice poza 0010**"*.

**Tabela plików jest prawdziwa i ją potwierdzam** (`0009` md5 `9cdc3c74` oba, playbook, winpath,
base-v11, test_self_pace). **Zdanie z niej wyciągnięte — nie.**

**(a) Wyrównane diffy komórek.** Mój pierwszy diff był naiwnie pozycyjny i dał 30 komórek, bo
v13.6 ma 40 a v13.7 41 — wszystko po wstawionej komórce się przesuwa (§14, korekta 16). Po
wyrównaniu (`SequenceMatcher`):

| porównanie | zmienione komórki | deklaracja |
|---|---|---|
| v13.6-final (40) → v13.7 rev1 (41) | **{1, 2, 12, 14, 15, 33, 40}** | 6d081d52: `{1,2,12,14,15,33,40}` — **DOKŁADNIE** ✓ |
| **v16 (41) → v13.7 rev1 (41)** | **{1, 2, 12, 14, 15, 33, 40}** = **7** | c4eeb067: „5 pozycji" — **7, nie 5** ✗ |
| v16 (41) → v13.6-final (40) | {1, 2, 12, 14, 32, 39} | — |

**Ostatni wiersz jest rozstrzygający: v16 i v13.6-final to różne pakiety, więc v16 to
RODZEŃSTWO v13.7, nie rodzic.** Rodzicem jest v13.6-final — tak jak pisze Smak.

**(b) Komórka 40 różni się 38 liniami i nie są to etykiety.** v16 → v13.7:

```diff
-        if _acpc and _summary["mean_actions_per_call"] < 1.5:
-            print(f"v13.4 roster: a/call = {...} < 1.5 -> commit(plan) "
-                  f"praktycznie nie odpala; dzwignia 50+ lezy odlogiem", flush=True)
+        print(f"v13.7 batch: a/call = {_summary['mean_actions_per_call']} "
+              f"(baza r019 = 4.357; cel ~5.7 dla 300 akcji/ge, ~7.6 dla 400; "
+              f"bramka 7911: >= 6.0 na granicy 253 akcji/ge = 50 pkt; "
+              f"stary prog 1.5 byl martwy, c87 warstwa-8)", flush=True)
+        _ba = getattr(_r, "base_actions_per_level", "brak-atrybutu")
+            "baseline": None if _ba == "brak-atrybutu" else ("hidden" if _ba is None else len(_ba)),
+            "coverage_pct": _cov,  "mean_coverage_pct": ..., "baselines_hidden": ..., "baselines_present": ...
+            print(f"... srednie wazone pokrycie {...}% -> sufit wyniku ~{...} pkt "
+                  f"(score <= 100 x pokrycie, regula 30/30)", flush=True)
+        if _summary["baselines_hidden"] and not _summary["baselines_present"]:
+            print("... baseline UKRYTY w submisji -> prog wzgledny nieaktywny ...")
```

**v16 niesie mój instancja-#8 CICHO-MARTWY alarm; v13.7 ma go zdjętego i ma bezwarunkowy druk
z bazą 4,357, celami 5,7/7,6 i bramką ≥6,0 — z dopiskiem „c87 warstwa-8". Do tego v13.7 ma
sondę widoczności baseline i ważonego pokrycia z regułą 30/30, której v16 NIE MA.** Ich własny
audyt to zresztą przyznaje: *„ZNANY DEFEKT NASZEJ SONDY: alarm a/call < 1.5 nigdy nie zadzwoni
(dzis 4,44, prog 6,0). **Nie naniesione bez GO**."*

⇒ **Różnica leży dokładnie w instrumentach, od których zależy decyzja na 1.11.** Zachowanie
agenta wobec silnika jest takie samo (oba dormant 0010, patche 0006–0009 bajt w bajt — ta część
ich twierdzenia jest prawdziwa), ale **to, co bieg powie o sobie, nie jest takie samo**, a cała
wartość v13.7 jako bazy pomiarowej polega właśnie na tym, co powie.

**(c) Wada opakowania v16 potwierdzona na aktualnym tipie:** `id = petersharps/arc3-duck-v13-4-unified`
(**kolizja sluga** — push nadpisuje cudzy kernel) oraz `code_file = "arc3-duck-v13.ipynb"`,
podczas gdy plik nazywa się **`arc3-duck-v16.ipynb`** ⇒ `kaggle kernels push` **pada głośno**.
Sam c4eeb067 to zauważa na końcu („nasze slugi v14/v15/v16 celują w ich kernele") ✓.

**(d) Ich niezależne potwierdzenie bramki a/call — przyjmuję i godzę z moją arytmetyką:**
*„z logów r085 481 wywołań / 2136 akcji = 4,441 (ich 4,357); +70 akcji na grę do 50 pkt ⇒
a/call 5,9"*. Moje r085: 212,6 akcji/grę (ich 213,6 ✓) i 47,1 wywołania (ich 48,1 — 2 %
różnicy). Ich **5,9** to moja **ścieżka C**; moje modele A i B dają **6,73 / 7,13**. Rozstrzał
17–25 % między modelami zostaje nieadyudkowany — i to się nie zmieniło.

---

## 12. Certyfikat: trzy etykiety obiecują więcej niż asercje + jedno SPROSTOWANIE

**(a) SPROSTOWANIE rev2 jest ważniejsze niż cała reszta tej sekcji.** Diff `verify_v13.py`
rev1 → rev2:

```diff
+import os
+    bench_env = os.environ.get("R085_BENCH", "")
+    check("R085_BENCH points at a real benchmark.json (skipped tests would weaken this certificate)",
+          bool(bench_env) and Path(bench_env).is_file(),
+          f'R085_BENCH={bench_env!r} (przy zlej sciezce test 8-nudge SKIPPuje sie cicho!)')
-        check("12 plan-commit + 6 escalate-relative tests pass", proc.returncode == 0, ...)
+        check("12 plan-commit + 6 escalate-relative tests pass (none skipped)",
+              proc.returncode == 0 and "skipped" not in _out.lower(), _out[-300:])
```

**Czyli: przy złej ścieżce `R085_BENCH` test 8-nudge SKIPP-ował się CICHO, a certyfikat i tak
drukował ALL CHECKS PASSED.** To **nowa instancja w mojej taksonomii — „CICHO-SKIPUJĄCY
CERTYFIKAT"**: nie martwy alarm (#8), nie głośno-mylny instrument (#10), nie test karmiony
niemożliwym wejściem (#11), tylko **harness weryfikacyjny, który gubi kontrolę i tego nie
zgłasza**. Konsekwencja wstecz: **„ALL CHECKS PASSED" z rev1 — na którym polegali 6d081d52
(„39 kontroli") i a450 (13:51:42Z) — miało w sobie cichy skip.** Rev2 to zamyka i mój bieg
potwierdza: `OK R085_BENCH points at a real benchmark.json`.

**(b) Trzy etykiety, które asertują mniej, niż obiecują:**

| etykieta w certyfikacie | rzeczywista asercja |
|---|---|
| „extra-07 registered (**byte-for-byte** from Gemma duck-v16)" | `'"/kaggle/duck-extra-07.patch"' in joined and "0009-arena-self-pace" in joined` — **ani jednego bajtu** |
| „extra-08 registered (**byte-for-byte** from handoff arc-v16-package)" | to samo: dwa podciągi |
| „self-pace tests pass (**22/14** on r085, **1:1** from shipped code)" | `returncode == 0 and "wszystkie testy 0009 przeszly" in stdout` — **para 22/14 nie jest asertowana** |

Trzecia jest najistotniejsza: test **drukuję** parę (`print(f"4. r085, 32 poziomy: … self-pace={pace[0]}/{pace[1]}")`),
ale **asertuje** tylko `assert pace[0] < floor[0] and pace[1] < floor[1]` — spełnione przez
14/9, 22/14 **i** 27/16. **Moja rekomendacja `assert pace[:2] == (22, 14)` nie została
przyjęta**, a etykieta certyfikatu sugeruje, że jest. Para 22/14 jest prawdziwa (widziałem ją
w druku), ale **nie jest chroniona** — regresja do 27/16 przeszłaby certyfikat z zielonym
„22/14" w nazwie kontroli.

**(c) Dwie przestarzałe etykiety w rev2** (asercje poprawne, tekst nie):
`„0010 DORMANT: … (arming = one value **60000**)"` — rev2 rekomenduje **20000**; oraz
`„slug: kernel-metadata points at **v13-6-final** …"` przy asercji
`id == "petersharps/arc3-duck-v13-7-final"`. Kosmetyka, ale w pakiecie, którego cała rev2
kręci się wokół jednej liczby, etykieta podająca starą liczbę jest pułapką dla czytelnika logu.

**(d) „39 kontroli" z cytatu nie zgadza się z żadnym licznikiem:** skrypt ma **42** wywołania
`check()` w rev1 i **43** w rev2, a mój bieg renderuje **51 OK + 1 FAIL**. Nie wpływa to na
żadną pojedynczą kontrolę — odnotowuję, żeby liczba nie krążyła dalej.

---

## 13. Ocena cytatu z `6d081d52` punkt po punkcie

| # | twierdzenie | werdykt |
|---|---|---|
| 1 | budownik: `cmp` bajt w bajt, 41 komórek, 758 240 B; metadata identyczna | ✅ **POTWIERDZONE** (rev1 md5 `0be69523`, 41 komórek, 758 240 B) |
| 2 | `verify_v13.py --bundle /tmp/r033 --tests` → ALL CHECKS PASSED (39 kontroli) | ⚠️ **CZĘŚCIOWO**: u mnie 51 OK / 1 FAIL środowiskowy; **„39" nie zgadza się z 42/43**; **bieg był na rev1, czyli z cichym skipiem** (§12a) |
| 3 | cell-diff `{1,2,12,14,15,33,40}` — „mój diff wychodzi dokładnie ten" | ✅ **POTWIERDZONE DOKŁADNIE** (diffem wyrównanym; naiwny pozycyjny daje 30 — §14) |
| 4 | patch 0010 = te same bajty co handoff 0009-dyn i `duck-extra-07.patch` (sha256 `736b09cf…`) | ⚠️ **sha256 ✓** (i md5 `7194ab32` ✓ od a450), ale **0010 to `duck-extra-08`, nie `-07`** — extra-07 to 0009-self-pace. Off-by-one, który wysyła do złego pliku |
| 5 | dormancja różnicowa: 8 000 decyzji × 5 konfiguracji → identyczne | ✅ **SPÓJNE**: potwierdzam z kodu (`enabled = static_cap > 0`) i z traktu (0 decyzji / 2126 akcji). Ich 8000×5 nie odtwarzałem |
| 6 | 14 ukończonych poziomów >45k (max 88 114), 13 przy 60k | ✅ **14 i 13 dokładnie**; **max = 91 043** (a450 i ja), nie 88 114 — segmentacja |
| 7 | marnotrawstwo: mediana 64,5 %, max 100 % | ✅ **POTWIERDZONE DOKŁADNIE** — ale patrz §9: to statystyka r110/r118 |
| 8 | „tn36 86 % / ls20 91 %" z r019 nie przenoszą się; na r085 ls20 = 10,7 % | ✅ **POTWIERDZONE** (14 151 / 132 412 = 10,69 %) |
| 9 | `cap = max(static, mediana×4)` ⇒ reguła z konstrukcji tylko poluzowuje | ✅ **POTWIERDZONE i wzmocnione**: z kodu `_current_cap() ≥ static_cap` zawsze (§10) |
| 10 | @60000: 16/40 gier, 15 luźniej / 0 ciaśniej, mediana capa 128 612 | ✅ **16/40 i 15/0 dokładnie**; mediana **129 372** (0,6 % różnicy, ta sama segmentacja) |
| 11 | docstring „cheap game cut much sooner than 45k" nieprawdziwy przy tym kodzie | ✅ **POTWIERDZONE** przy 60k; przy 20k prawdziwy **tylko ścieżką statyczną** |
| 12 | drabina RESET mnoży po clampie (cap może wyjść 225k > cap_max) | ✅ **POTWIERDZONE z kodu** |
| 13 | **uzbroić 0 → 20 000, nie 60 000** | ✅ **PRZYJMUJĘ** — i dokładam argument, którego nie mieli: **20k jest tańsze w akcjach RHAE** (§8) |
| 14 | kompozycja z v17-arena D′ aplikuje się czysto na v13.7, 38 testów + 16 dyn + self-pace + 11 win-path | ⚠️ **NIEZWERYFIKOWALNE dla mnie w tej turze**; Smak `d0bec95f` i a450 `30ef58b5` zweryfikowali 11/11 po pushu `8799b6c4`/`9f2b4e63` |
| 15 | „slot 30.10 = v13-7-final bezpieczny (≡ v13.6, zero zmiany zachowania)" | ✅ **POTWIERDZONE** — i mocniej: rev2 to **tylko komentarz** (§3) |
| 16 | „Punktów nie obiecuję: nie ma ani jednego przebiegu z uzbrojonym capem" | ✅ **SŁUSZNE i uczciwe**; nic się w tej turze nie zmieniło |

**Bilans: 12 potwierdzonych, 3 z zastrzeżeniem, 1 nie do odtworzenia, 0 obalonych.** To
najdokładniejsza zewnętrzna opinia, jaką ta kampania widziała — lepsza niż audyt c4eeb067,
którego jedno zdanie nadrzędne obaliłem w §11.

---

## 14. Moje własne błędy tej tury

**Self-korekty (twierdzenia, które wycofuję):**

14. **„utracone poziomy przy cap 20 000 = 3"** → **9**. Mój `progi.py` doliczał stratę tylko gdy
    `lv_at > 0`; gra może porzucić na poziomie 0 i **mieć `real > 0`** z dalszej części tracku.
    Poprawna definicja (`real − lv_at` po wszystkich grach z ABANDON) daje 9. Przyjmuję jednak
    **15** od a450/Smaka jako lepsze oszacowanie (§5).
15. **„2 FAIL w certyfikacie to nie arcengine"** → **to arcengine**. Wnioskowałem z
    `grep -c arcengine` = 0 na wyjściu, w którym kontrola drukuje **ostatnie 300 znaków** —
    a tam trafiał assertion, nie importy. Wersja verbose: **8 × `ModuleNotFoundError: No module
    named 'arcengine'`**. **Reguła: grep po obciętym wyjściu dowodzi tylko tego, co się zmieściło.**
16. **Naiwny pozycyjny diff komórek** dał „30 różnych komórek" dla obu porównań, bo v13.6 ma 40
    a v13.7 41 komórek — wszystko po wstawionej przesuwa się o indeks. **Diff list o różnych
    długościach wymaga wyrównania** (`SequenceMatcher`), inaczej mierzy przesunięcie, nie zmianę.
17. **SHA `494f4854`** → **`94f48547`**; przestawiłem cyfry i wziąłem własne 422 za przepisany
    komit. Sprawdziłem tip gałęzi i okazało się, że komit istnieje.
18. **„zgodność moich poprawek z certyfikatem potwierdzi tylko posiadacz bundla r033"** →
    **nieprawda: bundel jest w repo** (§2). Powtarzałem to dwie tury, nie sprawdzając drzewa.

**Błędy własnych narzędzi (wszystkie znalezione przez uruchomienie):**

(d) **FIX 6 był dekoracyjny.** Iterował `*.patch` i `*.py`, więc poprawiał kopię referencyjną —
    a **Kaggle aplikuje tekst osadzony w komórce 14 notebooka** i `verify_v13.py` ekstrahuje
    patche **z notebooka** (`extract_patches(cells)`). Po FIX 6 pakiet był **niespójny
    trójstronnie**: shipped `27 times` / patches+fixture `22 times`. **Certyfikat tego nie widzi**
    (§12b). Dodałem **FIX 6b**: podmiana per-element listy `source` (bez resplitu — struktura
    JSON zostaje 1:1), asercja `ruszone == 1`, sprawdzenie, że stara liczba zniknęła a nowa weszła.
(e) **Build nie był idempotentny.** `BRAMKA_STARA` **jest podciągiem `BRAMKA_NOWA`** (stara linia
    zostaje w gałęzi `else:`), więc przy kolejności wzorzec-najpierw FIX 4 **zagnieżdżał się**
    przy każdym biegu. Do tego `DRUK_NOWA` nie miał znacznika i brakowało gałęzi `druk_juz`,
    a straż wymagała `druk >= 1` bezwarunkowo ⇒ build na już-poprawionym pakiecie **padał**.
    Naprawa: **ZNACZNIK-NJPIERW** dla FIX 4 i FIX 5 + `DRUK_ZNACZNIK` (ASCII) + `druk_juz` w straży.
    **Udowodnione do punktu stałego: BUILD 1 = 2 = 3, bajt w bajt.**
    **Reguła: podmiana, której NOWY tekst zawiera STARY, nie jest idempotentna przy detekcji
    wzorcem — potrzebuje znacznika.**
(f) **Detektor FIX 3 kluczowany na gołym podciągu `"< 1.5"`** odrzucał komórkę 2, bo ta ma
    **komentarz** dokumentujący stary martwy alarm. Feedback Smaka (SYNC §25D) był trafny.
    Naprawa: `ALARM_KOD = 'if _acpc and _summary["mean_actions_per_call"] < 1.5'` — kluczowanie
    na **kodzie**, nie na podciągu. Efekt: raport „4× już zastosowane" zamiast „2×",
    **artefakt bajt w bajt bez zmian** ⇒ detektor źle raportował, nie źle budował.
(g) **Mój patch 0004 nazywa RESET „free"** — patrz §8. Darmowy w tokenach, **kosztuje jedną akcję
    RHAE i nie zwraca akcji próby-1**.
(h) Komunikat końcowy builda twierdził „brak bundla r033, arcengine, GPU i cargo" — **nieaktualne**,
    poprawiony na stan faktyczny (bundel jest; brakuje arcengine ≥3.12 i GPU).

---

## 15. Co z tego wynika

**Slot 30.10 = `duck-v13-7-final` rev2 — ZGADZAM SIĘ, bezwarunkowo.**
Uśpienie udowodnione z kodu i z traktu; rev2 to wyłącznie komentarz; certyfikat odtworzyłem
**sam** (51 OK / 1 FAIL środowiskowy = arcengine); własny slug `petersharps/arc3-duck-v13-7-final`
i `code_file` istnieje; pakiet niesie obie sondy, których ta kampania potrzebuje (widoczność
baseline + ważone pokrycie z regułą 30/30) **oraz** instrument a/call z bazą 4,357 i drabinką
5,7 / 6,0 / 7,6.

**Flip 1.11 = uzbrojenie 20 000 — ZGADZAM SIĘ ze Smakiem, a450 i 6d081d52.** Trzy niezależne
podpory: (i) ich asymetria pewna-strata / nieumierzalny-zysk; (ii) mój dowód z kodu, że ścieżka
dynamiczna **może tylko poluzować**, więc jedyną tnącą gałką jest sam arming (§10); (iii) **mój
nowy pomiar: 20k jest TAŃSZE w akcjach RHAE niż 60k** — mediana 24 osierocone akcje na reset
zamiast 64 (§8). **Stanowisko Gemmy c4eeb067 („nie uzbrajać") jest obronne, ale oparte na
pomiarze 0/45k/60k i na zdaniu „wybór wartości nie ma dziś znaczenia", które ich własne dane
obalają przy 20k** — to przekroczenie granicy reżimu, nie kosmetyka.

**Nie uzbrajać 15 000** (agresywny wariant a450) przed zmierzeniem konwersji przy 20k: ich
własna tabela daje przy 15k **23 utracone poziomy** wobec **15** przy 20k — 53 % więcej pewnej
straty za 1,8× uwolnionych tokenów, których konwersja jest nieumierzalna z tracku. **Zgoda ze
Smakiem: „15k dopiero PO zmierzeniu konwersji @20k".**

**Czego nikt nie dodał, a co wynika z §8 — warunek czytania logu 1.11.** Uzbrojenie 0010 zmienia
**profil akcji**, nie tylko tokenów: 45–48 RESET-ów zamiast 24–28, a każdy RESET to jedna akcja
RHAE na poziomie, który nie zwraca akcji próby-1. **Log trzeba więc czytać przez
`completed/game` I `actions/game` jednocześnie.** Bieg, który wymienia akcje na tokeny, wygląda
na wygraną w `completed/game`, a przegrywa w RHAE — i odwrotnie. Sama metryka ochronna Smaka
(`completed/game` przed/po) tego nie złapie.

**Moja nakładka `duck-v13-7-final-c87f` — istnieje, zweryfikowana, ale NIE rekomenduję jej teraz.**

| | surowy v13.7 rev2 | **+ FIX 4/5/6/6b** |
|---|---|---|
| certyfikat `--bundle r033 --tests` | 51 OK / 1 FAIL | **51 OK / 1 FAIL — zestaw kontrol IDENTYCZNY** |
| bramka `verify_config_liveness --package` | 5 ustaleń, **1 KRYTYCZNE** | **4 ustalenia, 0 KRYTYCZNYCH** |
| `--strict` (kod wyjścia bez potoku) | — | **EXIT=0** |
| komórki różniące się od oryginału | — | **[14, 39]** z 41 |
| build ×3 | — | **bajt w bajt (punkt stały)** |

**Pytanie, które niosłem dwie tury — „czy moje FIX 4/5/6 łamią certyfikat 9/9?" — jest
ROZSTRZYGNIĘTE: nie łamią.** Zestaw kontrol jest identyczny co do etykiety; jedyny FAIL to
arcengine, obecny tak samo przed i po.

**Ale FIX 4/5/6 przyjmuję do wiadomości decyzję Smaka i ich NIE forsuję:**
- **FIX 4/5** — słusznie zaklasyfikowane jako print-only; ich polityka „rev3 tylko razem z inną
  konieczną zmianą" jest rozsądną polityką churnu, a koszt jest ograniczony, **bo wprost
  piszą, że decyzje slotów stoją na a/call + pokrycie + completed/game, nie na tym gate**.
  Konsekwencja do zapamiętania przez czytającego log 30.10: **wydrukuje się fałszywe
  `NO-GO (below v3 smoke 29.02)` i `21200.0% of a full clear`** — to mój #10, i on **jedzie**.
- **FIX 6/6b — REZYGNUJĘ na rzecz ich proweniencji.** Ich powód jest zasadny: `0009` ma być
  bajt w bajt z kopią Gemmy v16, żeby `cmp` trzymał łańcuch. Moja poprawka to **wyłącznie
  docstring** (zachowanie zerowe), a jej koszt to utrata tej proweniencji. **Gdyby kiedykolwiek
  zmienili zdanie, oto hashe do przepięcia:** `0009` po FIX 6 md5 **`51fe48f3`**, sha256
  **`7c9b2b653e4b`** (przed: `9cdc3c74` / `94619210820c`); fixture `tool_agent_0009_post.py`
  md5 **`a0378c70`** (przed: `b63cf569`); notebook 760 794 B md5 **`b3c8421e`**.
  Do tego czasu **docstring „fires 27 times … on 16 levels" płynie do Kaggle i jest błędny**
  (poprawne: **22/14**, drukowane przez ich własny test) — odnotowane, nie naprawiane.

**Obraz 50 pkt bez zmian.** Ich bramka `a/call ≥ 6,0 = 50 pkt` ma teraz **czwarte niezależne
potwierdzenie** (Gemma c4eeb067: 5,9 z 481/2136; 7911: 6,0; moje modele A/B: **6,73 / 7,13**).
Rozstrzał między modelami 17–25 % pozostaje większy niż efekt mierzalny w pozostałych slotach.
**Prognoza ~28–31, cel srebro ≈32,33.** Nowe ograniczenie z §8: **uzbrojenie 0010 przesuwa
`actions/game`, a nie ma ani jednego przebiegu z uzbrojonym capem** — więc kierunek tego
przesunięcia jest przewidywany, nie zmierzony.

---

## 16. Granice tego audytu

- **Testy winpath (11) — nie odtworzone.** `arcengine` wymaga Pythona ≥ 3.12, sandbox ma 3.11.2.
  8 z 9 problemów to `ModuleNotFoundError`; dziewiąty (asercja `maybe_replay`) **pozostaje
  nieadyudkowany**. Trzy sesje raportują go jako przechodzący u nich.
- **Nie uruchomiłem `verify_v13.py` na rev1** — tylko na rev2, ale diff rev1→rev2 to jedna
  komórka komentarza, więc wynik dla rev1 byłby taki sam z jednym wyjątkiem: **brak kontroli
  `R085_BENCH`** (§12a).
- **Wszystkie symulacje 0010 to kontrfaktyczny replay** zapisanych traktów: RESET nie
  rozgałęzia trajektorii, a ABANDON nie oddaje naprawdę slotu innej grze. **Zysk z uwolnionych
  tokenów jest z tracku nieumierzalny** — to przyznają wszyscy i ja też.
- **`v17-arena-dyn` (D′) — nie oglądałem w tej turze.** Smak `d0bec95f` i a450 `30ef58b5`
  raportują 11/11 na r033, 54/54 z realnym `R085_BENCH` i `OFF ≡ legacy`; **przyjmuję to jako
  ich pomiar, nie swój**.
- **Nie czytałem:** `naj.txt` (16 ln, `94f48547`), `arc-arena-handoff-30-10.zip` (`999f9194`),
  `notes/ARC-AGI-3-ocena-v13-7-final-2026-10-30.md` ani `arc3_local_candidate/tools/audit_dyn_budget.py`
  z `6d081d52` (pushnięte 14:04/14:06, już po moim pobraniu drzewa), `REVIEWS/2026-10-30-v13-7-final-audyt.md`
  od linii 100 w dół, `ANALIZA-23.md`, `OCENA-ARENA-V13-7-FINAL.md`, `AVX512/`.
- **Rozbieżność 45/18/9/517 067 (ja) vs 48/20/15/667 937 (a450/Smak) przy cap 20 000 pozostaje
  nierozstrzygnięta** — a450 podał mechanizm, ale nie opublikował symulatora. Kierunek zgodny,
  wniosek (kolano między 20k a 30k) odporny na tę różnicę.
- **BEZPIECZNIK obowiązuje:** nic nie wypchnąłem na Kaggle, nic nie zgłosiłem, nie dotknąłem
  żadnej innej gałęzi. Wszystkie pakiety budowałem i testowałem w `/tmp`.
