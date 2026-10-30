# OCENA: `duck-v13-mega` (gałąź `arena/a450b00f-pokemon`) — i jedna decydująca niezgodność

**Data:** 30.10.2026 · **Źródło:** `peteraangelic-pixel/Pokemon` @ `arena/a450b00f-pokemon`,
commit **`3782f8c3`** (2026-10-28 **23:08:29 UTC**), katalog `arc-agi-3/duck-v13-mega/` (19 wpisów),
pobrane przez `gh api` **read-only**. Nie pushuję na tę gałąź.

Pliki: `README.md`, `ANALIZA-23.md`, `arc3-duck-v13.ipynb` (712 874 B, 35 komórek),
`kernel-metadata.json`, `playbook.json`, `patches/0006-winpath-replay.patch`,
`src/arc3_winpath.py` (14 624 B), `src/base-v11.ipynb`, `tests/test_plan_commit.py`,
`tests/test_winpath.py`, `tools/{build_playbook,build_v13,make_patch_0006,verify_v13}.py`.

> **WERDYKT W TRZECH ZDANIACH.** Inżynieria v13 jest **dobra i w dwóch miejscach lepsza od mojej**
> (`EXPOSE_UNDO='on'` znalezione **niezależnie i 30 minut wcześniej** niż ja to opublikowałem;
> weryfikacja testami **na spatchowanym drzewie**). `ARC3_LEVEL_TOKEN_CAP="0"` to **dokładnie**
> moja rekomendacja z `DIAGNOZA-23-89-I-PLAN.md` §8, z tym samym uzasadnieniem pomiarowym.
> **Ale główna dźwignia v13 (patch 0006, replay między passami) jest STRUKTURALNIE MARTWA
> w punktowanym rerunie, bo `n_passes = 1`** — a `ANALIZA-23.md` §4 opiera się na założeniu
> „każdy z **20 passów**", które dla rerunu jest **fałszywe**.

---

## 1. Co v13 zmienia względem v11 — pięć dźwigni naraz

Z ich `README.md`, tabela „Co zmienia v13 względem v11 (slot A, który dał ~23)":

| # | zmiana | mechanizm wg ich README | moja ocena |
|---|---|---|---|
| 1 | `PLAN_COMMIT = "1"` | commit(plan) z patcha 0005, eskalacja co 60 akcji | ⚠️ **niezmierzone na Kaggle** |
| 2 | `ARC3_LEVEL_TOKEN_CAP = "0"` | wyłącza cap 45k **(a z nim darmowy RESET/ABANDON z 0004)** | ✅ **ZGODNE Z MOJĄ REKOMENDACJĄ I POMIAREM** |
| 3 | **patch 0006: pamięć zwycięskich ścieżek + replay** | *„każdy ukończony poziom jest zapamiętywany; **w kolejnych passach / po resecie** poziom jest odtwarzany deterministycznie … z `generated_tokens=0`"* | ❌ **MARTWE w rerunie — §2** |
| 4 | **playbook offline** | *„14 poziomów / 9 gier rozwiązanych BFS-em na PC usera, każda sekwencja ponownie zwalidowana na prawdziwym kodzie gry (14/14 OK, 184 akcje)"* | ⚠️ **oparte na niezweryfikowanej hipotezie o rosterze — §3** |
| 5 | `ARC3_DEAD_SKIP = 1` | *„passy ≥4 gier, które po ≥3 passach mają 0 poziomów, kończą się od razu"* | ❌ **MARTWE — wymaga passa ≥4, §2** |
| — | fix concurrency = 10 | bez zmian względem v11 | ✅ konieczne |

---

## 2. ❌ DECYDUJĄCE: `n_passes = 1` w `TRUE_SUBMISSION` — replay między passami nie istnieje

### 2.1 Dowód z ich własnego notebooka

`arc3-duck-v13.ipynb`, **komórka 25** (wytłuszczenia i komentarze moje):

```python
bm.solver.concurrency = 10
bm.n_passes = 4                                        # ← ustawione POZA blokiem
demo_excluded_games = [] if TRUE_SUBMISSION else []
if TRUE_SUBMISSION:                                    # overrides for contest run
    bm.n_passes = 1                                    # ← NADPISANE NA 1
    bm.solver.concurrency = int(os.environ.get("ARC3_TRUE_CONCURRENCY", "10"))  # v11 fix
    bm.n_passes = 1                                    # ← ustawione DRUGI RAZ (nadmiarowo)
bm.solver.concurrency = max(1, len(_smoke["games"]))   # ← ścieżka smoke
```

**Czyli: `n_passes = 4` obowiązuje tylko poza rerunem; w punktowanym biegu jest `1`.**

### 2.2 Niezależne potwierdzenie z surowych artefaktów produkcyjnych

Przeliczyłem to sam w tej sesji z dwóch **niezależnych** plików, zanim przeczytałem v13:

| artefakt | pole | wartość |
|---|---|---|
| `r085-kernel_output_pick/output-pick/benchmark.json` (smoke **c45**, 25.10) | `n_passes` | **1** |
| `r093-kernel_output_pick/output-pick/benchmark.json` (smoke **v11**, 28.10) | `n_passes` | **1** |

Oraz z `FAKTY-I-POMIARY.md`: config duck-v7 dla `TRUE_SUBMISSION` = **`n_passes=1`**,
`concurrency=120`, `532*60 s`.

### 2.3 Konsekwencja — trzy z pięciu dźwigni v13 nie mają czego robić

| dźwignia v13 | czego wymaga | stan w rerunie |
|---|---|---|
| replay **„w kolejnych passach"** | passów 2…N | ❌ **`n_passes=1` → nie ma passów 2…** |
| *„każdy poziom rozwiązany przez LLM **w passie 1 działa jak playbook dla passów 2–20**"* (README) | passów 2–20 | ❌ **nie istnieją** |
| `ARC3_DEAD_SKIP=1`: *„passy ≥4 gier, które po ≥3 passach mają 0 poziomów"* | passa ≥4 i ≥3 passów historii | ❌ **nie istnieją** |
| replay **„po resecie"** | mechanizmu RESET | ❌ **`CAP=0` wyłącza RESET z patcha 0004** — ich własny README: *„wyłącza cap 45k na poziom **(a z nim darmowy RESET/ABANDON z 0004)**"* |

> **Błąd w `ANALIZA-23.md` §4, który trzeba poprawić.** Punkt 4 brzmi:
> *„**Każdy z 20 passów** zaczyna grę od zera: poziomy rozwiązane w passie 1 są odkrywane na nowo
> **w passach 2–20** — pełna eksploracja, pełne tokeny, pełna kara kwadratowa za akcje.
> To adresuje patch 0006 w v13."*
>
> **To jest nieprawda dla punktowanego biegu.** `n_passes=1`. Nie ma passów 2–20, nie ma
> ponownego odkrywania poziomów, i **nie ma problemu, który patch 0006 adresuje**.
> Cały punkt 4 diagnozy — i uzasadnienie głównej dźwigni v13 — stoi na liczbie passów,
> której w rerunie nie ma.
>
> **Jedna uczciwa niewiadoma, której nie domknąłem:** czy **silnik** sam restartuje poziom po
> śmierci (auto-RESET) niezależnie od patcha 0004. Mój patch wspomina *„the auto-RESET makes that
> span…"* i *„on the turn after a game over"*, więc taki mechanizm istnieje. **Ale to nie ratuje
> dźwigni:** `WinPathStore` zapisuje ścieżki poziomów **UKOŃCZONYCH**, a poziomu ukończonego
> w tym samym passie się nie powtarza — po ukończeniu agent idzie do następnego. Żeby replay
> miał co odtwarzać w passie 1, musi istnieć **uprzednio zapisana** ścieżka, czyli **playbook
> offline**. Czyli wszystko sprowadza się do §3.

### 2.4 Co z patcha 0006 zostaje żywe w rerunie

**Wyłącznie playbook offline**, dopasowany po `game_id`. Z `src/arc3_winpath.py`:

```python
L75-76  def enabled():        return os.environ.get("ARC3_WINPATH", "0") == "1"
L79-80  def replay_enabled(): return enabled() and os.environ.get("ARC3_WINPATH_REPLAY","1") != "0"
L107-108 def _norm(game_id):  return re.sub(r"[^a-z0-9]", "", str(game_id).lower())
L154-168 def _merge_playbook(self): mine = _norm(self.game_id); ... if match: for lvl, entry in ...
```
oraz docstring L32-33: *„Game-id matching is tolerant (exact, else **alphanumeric prefix match**),
because gateway ids may carry [suffixes]"*.

---

## 3. ⚠️ Playbook: ograniczona strata, bliski zeru zysk

### 3.1 Co jest DOBRE w implementacji — i dlaczego **nie** jest to ryzyko 0.00

Miałem gotowy zarzut z `mayankraj4728` §G: *„Replaying a winning path: the gateway **refuses to
open a game twice**, and it can leave the scorecard open, **risking 0.00**"*. **Sprawdziłem i ten
zarzut NIE DOTYCZY v13** — i to trzeba im policzyć na plus:

* `WinPathStore(game_id)` pisze do `winpath_dir()/game_id.json` i odtwarza **wewnątrz gry, którą
  harness już otworzył**. **Nie otwiera gier ponownie.** Więc mechanizm „gateway odmawia
  drugiego otwarcia" **nie zachodzi**.
* Docstring L20-26: *„replay is verified against the recorded **grid-hash chain** (initial grid +
  grid after every action). **The first mismatch**, an unavailable [action] … whose replay fails
  **3 times is never replayed again**."* Czyli złe dopasowanie **degraduje do normalnej gry LLM**,
  a nie do crashu.
* `ARC3_WINPATH` **domyślnie `0` = stock behaviour**, env-gated (komórka 11: *„with `ARC3_WINPATH`
  unset the patched code is inert"*). **To jest lepsza dyscyplina niż `EXPOSE_UNDO` i
  `ARC3_PERSISTENT_FUNCTIONS_SCOPE`**, których legacy domyślne po cichu zmieniały zachowanie
  (`RESEARCH-LIDERZY-50PLUS.md` §4.1, §6).
* Cztery **niezależne kill-switche**, każdy jedną wartością: `PLAN_COMMIT`, `ARC3_WINPATH`,
  `ARC3_DEAD_SKIP`, `ARC3_LEVEL_TOKEN_CAP`.

### 3.2 Co jest ZŁE: hipoteza o rosterze ma trzy niezależne pomiary przeciwko sobie

Cały zysk z playbooka wymaga, żeby **110 prywatnych gier** miało identyfikatory dopasowujące się
do 9 publicznych (`cn04`, `m0r0`, `ft09`, `ls20`, `cd82`, `lp85`, `sp80`, `vc33`, `s5i5`).

| dowód | treść | źródło |
|---|---|---|
| docstring `taaf/competition_arcade.py` | *„one scorecard, **hidden baselines**, and **no repeated game IDs**"* | `FAKTY-I-POMIARY.md`, `OCENA-DEEPSEEK-V9.md` |
| zmierzony wynik offline source-introspection | **0.20**, *„❌ Game sources don't exist in the rerun"* | `mayankraj4728`, ref 57272788 (16.10), błąd śmiertelny #1 |
| held-out evaluation | **0/113 poziomów** na 15 grach held-out vs **7/70** na 10 dostrajanych | `rasagyavatsal/arc-prize-2026-arc-agi-3` |
| mój własny `roster_probe.jsonl` (r085) | 10 `game_id` = **gry PUBLICZNE** — ale probe odpalił się **w smoke na bundlu offline**, nie na gatewayu | `OCENA-CODEX-7Z.md` §5 |

⚠️ **Uczciwe zastrzeżenie do mojego własnego dowodu #2:** `0.20` dotyczy mechanizmu
`find_game_source` (**czytanie kodu źródłowego gry w rerunie**), a v13 kodu źródłowego w rerunie
**nie czyta** — dopasowuje po `game_id` i odtwarza zapisaną sekwencję akcji. **To nie jest ten sam
mechanizm**, więc `0.20` nie jest pomiarem v13. Bezpośrednio relevantne są dowody #1 i #3:
brak powtórzonych ID i brak transferu z gier dostrajanych na held-out.

> **Werdykt o playbooku: OGRANICZONA STRATA, BLISKI ZERA ZYSK.**
> Nie trafi w żadną grę (dowody #1, #3), a jeśli trafi błędnie przez **tolerancyjne**
> dopasowanie prefixem, to łańcuch hashy + fallback do LLM + reguła 3 strike'ów ograniczają stratę
> do kilku zmarnowanych akcji (ich README przyznaje: *„odtworzone akcje przechodzą przez normalną
> ścieżkę wykonania i **są liczone**"* — czyli **RHAE `(baseline/akcje)²` replay NIE poprawia**,
> oszczędność jest tylko w tokenach, a przy `n_passes=1` i `CAP=0` nie ma re-eksploracji,
> którą mógłby oszczędzić).
>
> **Ich własny README uczciwie to hedguje**: *„Jeśli roster jest w pełni prywatny, playbook nie
> trafi w żadną grę (0 poziomów) i zostaje commit + cap-off + pamięć w obrębie runu — raczej
> ~28–38."* Zgadzam się z hedgem, ale **gałąź ~28–38 jest zawyżona**, bo „pamięć w obrębie runu"
> przy `n_passes=1` i `CAP=0` nie ma czego odtwarzać (§2.3). Realny wkład v13 ponad v11 to
> **`CAP=0` + `EXPOSE_UNDO='on'`**, czyli według moich pomiarów **+0.4 do +2.2** i być może
> dodatkowy mały plus z UNDO — **nie ~5 do ~15**, które implikuje widełkowanie ~35–50+.

---

## 4. ❌ Pięć zmian naraz = błąd śmiertelny #8, i to dokładnie ten, który zniszczył diagnostykę v11

`mayankraj4728` §11, punkt **8**: *„**Never stack several unscored changes in one submission.**
With ±4 noise you can't tell which one hurt."*

v13 stackuje: `PLAN_COMMIT=1` **+** `CAP=0` **+** patch 0006 (winpath) **+** playbook **+**
`DEAD_SKIP=1`. Przy σ≈3.93 i progu istotności +5 pkt **wynik v13 nie będzie interpretowalny**:

* wyjdzie ~29 → nie wiemy, czy to `CAP=0`, czy `PLAN_COMMIT`, czy szum
* wyjdzie ~22 → nie wiemy, czy playbook zaszkodził, czy `PLAN_COMMIT`, czy szum

**To jest dokładnie ta sama pułapka, przez którą v11 (23.89) jest do dziś niezdiagnozowane** —
`DIAGNOZA-23-89-I-PLAN.md` §7 pkt 1: *„NIE ROZDZIELILEM wplywu 0005 od szumu"*. v13 **powtarza**
ten błąd z większą liczbą zmiennych.

> **Na szczęście naprawa jest darmowa — kill-switche już są.** Ustawienie
> `ARC3_WINPATH="0"`, `ARC3_DEAD_SKIP="0"`, `PLAN_COMMIT="0"` i zostawienie **tylko**
> `CAP=0` + `EXPOSE_UNDO="on"` + concurrency 10 daje **konfigurację mierzalną**:
> delta wobec v11 = `CAP=0` (+0.4…+2.2 zmierzone) + `EXPOSE_UNDO` (poparte cudzym pomiarem,
> zerowe ryzyko po stronie serwingu). To jest **jedyny** wariant, po którym cokolwiek będziemy wiedzieć.

---

## 5. ✅ Co v13 ma LEPSZE ode mnie — kredyt, nie krytyka

**1. `EXPOSE_UNDO: 'on'` — znalezione NIEZALEZNIE i WCZEŚNIEJ niż ja to opublikowałem.**
Komórka 13 notebooka zawiera `'EXPOSE_UNDO': 'on'`. Commit v13 = **28.10 23:08:29 UTC**;
mój `RESEARCH-LIDERZY-50PLUS.md` §4.1 (gdzie to opisałem jako własne znalezisko z rellik13)
został wypchnięty **~30 minut później**. **Czyli to nie jest przejęcie ode mnie — to niezależna
konwergencja**, i to jest najsilniejsze możliwe potwierdzenie, że dźwignia jest prawdziwa:
dwie sesje, różne drogi, ten sam wniosek. **Moja rekomendacja „dodaj `EXPOSE_UNDO=on`" jest
w v13 już spełniona — nie ma czego dodawać.**

**2. Dyscyplina weryfikacji jest lepsza niż to, co proponowałem.** Z ich README:
*`tools/verify_v13.py --bundle <r033> --tests` → **ALL CHECKS PASSED**: notebook 35 komórek,
wszystkie komórki kodu się kompilują, **6/6 patchy aplikuje się w kolejności notebooka na czystym
drzewie**, drzewo się kompiluje, **12/12 testów plan-commit i 6/6 testów winpath NA SPATCHOWANYM
DRZEWIE**. **Przełącznik przetestowany w obie strony („1" włącza, „0" czyści env — poprawka
względem v11)**.*
Testowanie **na spatchowanym drzewie** i **w obie strony** to jest dokładnie reguła, którą
wyprowadziłem z błędu `SCOPE=run` („wartość env akceptowana ≠ dźwignia działa") — tylko że oni
ją **zastosowali**, a ja ją **sformułowałem**.

**3. `CAP=0` z poprawnym uzasadnieniem pomiarowym.** Ich tabela: *„smoke na tych samych 10 grach:
z capem 26,78 < bez 27,21 < 29,02"* — **identyczne liczby, które sam przeliczyłem** z surowego
`r085/output-pick/benchmark.json` (`OCENA-CODEX-7Z.md` §3.1). Niezależna konwergencja po raz drugi.

**4. `ANALIZA-23.md` pkt 1 i 5 są trafne.** *„Smoke 26,78 **nie jest** estymatorem wyniku LB na
pełnym rosterze — to pomiar innej, łatwiejszej populacji przy innym budżecie"* (rozcieńczenie
tokenów przez 110 gier przy 10 slotach) oraz *„±2–3 pkt między identycznymi runami to norma,
nie sygnał"* — to jest zgodne z moim §2.1 (σ=3.93, próg +5) i z `EKONOMIA-TOKENOW.md` §1bis.

---

## 6. ⚠️ NOWA LUKA, którą znalazłem w v13: `SERVER_STARTUP_TIMEOUT = 12 min` przy ładowaniach 25–30 min

Komórka 13:

```python
# Kaggle might cancel the run in no action is done in some timeframe.
# To prevent this, harness will start up even if backend is not yet ready,
# and the first started game will perform a single reset action.
NOTEBOOK_START_TIME = time.time()
SERVER_STARTUP_TIMEOUT = 12 * 60                       # ← 720 s
os.environ['ARC3_WARMUP_ACTION_GAMES'] = '1'           # ← keepalive
os.environ['ARC3_HTTP_RETRY_INITIAL_SECONDS'] = '900'  # ← 15 min retry
```

**Dobra wiadomość: baza dfranzen MA już odpowiednik keepalive.** `ARC3_WARMUP_ACTION_GAMES='1'`
+ „the first started game will perform a single reset action" to jest dokładnie mechanizm, który
`mayankraj4728` opisuje jako własny „safety fix 2: startup keepalive". Plus
`ARC3_HTTP_RETRY_INITIAL_SECONDS='900'` = 15 min. Czyli **„gateway kończy bieg po 15 minutach bez
akcji" jest zaadresowane** — i mój postulat z `DIAGNOZA-23-89-I-PLAN.md` §8 (dodaj keepalive)
był **częściowo nadmiarowy**. Koryguję to.

**Zła wiadomość: 720 s < obserwowane czasy ładowania modelu.** `mayankraj4728` §D i §6.2:
*„Kaggle's model disk is sometimes very slow: we have seen loads of **257 s, 599 s, 25 min and
over 30 min**"*, i *„Without this, a slow load means 0.00. **It held through a 25-minute load** in
our smoke test"*. Ich safety fix 4 to *„waits up to **30 min** for the gateway instead of 10.
Another team lost a ~33.7 run (it scored 8.61) to a gateway outage longer than 10 min."*

> **`SERVER_STARTUP_TIMEOUT = 12 * 60` = 720 s jest krótszy niż zaobserwowane ładowania
> 25 min (1500 s) i 30+ min (1800+ s).** Jeśli dysk modelu będzie wolny, harness może
> przerwać start **zanim** serwer wstanie.
>
> **Rekomendacja: `SERVER_STARTUP_TIMEOUT = 30 * 60`.** Jedna liczba, zero wpływu na granie,
> poparte cudzym pomiarem (25-minutowe ładowanie przetrwane) i cudzą stratą (~33.7 → 8.61).
> **To jest najtańsza dostępna ochrona przed 0.00 i nie koliduje z żadną dźwignią.**
>
> ⚠️ Nie domknąłem: czy `SERVER_STARTUP_TIMEOUT` faktycznie przerywa bieg, czy tylko przechodzi
> do kolejnego etapu. To trzeba przeczytać w komórce, która go używa — **nie zgaduję**.

---

## 7. Rekomendacja

**Nie wysyłać v13 „jak leci".** Nie dlatego, że jest zły inżynieryjnie (nie jest — §5), tylko
dlatego, że **trzy z pięciu dźwigni nie wykonują się w rerunie** (§2), czwarta opiera się na
hipotezie z trzema pomiarami przeciwko (§3), a piąta jest niezmierzona (§1) — i wszystkie pięć
naraz daje wynik **nieinterpretowalny** (§4).

**Konfiguracja do wysłania, ułożona z tego, co v13 już ma (kill-switche):**

| parametr | wartość | podstawa |
|---|---|---|
| `ARC3_LEVEL_TOKEN_CAP` | **`"0"`** | ✅ zmierzone: cap kosztuje −0.43 vs r019 i −2.24 vs v3 (`OCENA-CODEX-7Z.md` §3) |
| `EXPOSE_UNDO` | **`"on"`** | ✅ już w v13; rellik13 „not mislead the agent" (`RESEARCH-LIDERZY-50PLUS.md` §4.1) |
| `bm.solver.concurrency` | **10** | ✅ v11 fix, potwierdzone w produkcji (0.00 → 23.89) |
| `ARC3_WINPATH` | **`"0"`** | ❌ martwe przy `n_passes=1`; playbook nie trafi w roster (§2, §3) |
| `ARC3_DEAD_SKIP` | **`"0"`** | ❌ wymaga passa ≥4 (§2.3) |
| `PLAN_COMMIT` | **`"0"`** | ⚠️ niezmierzone; v11 pokazał, że 0005 nie jest obojętne nawet przy `"0"` |
| `SERVER_STARTUP_TIMEOUT` | **`30 * 60`** (z 12) | ⚠️ §6 — ładowania 25–30 min |
| parametry serwingu | **BEZ ZMIAN** | ❌ −7 do −8 na zbiorze ukrytym (`RESEARCH-LIDERZY-50PLUS.md` §3.3) |

**Delta wobec v11 = dokładnie dwie zmiany: `CAP` 45000→0 i `SERVER_STARTUP_TIMEOUT` 12→30 min**
(`EXPOSE_UNDO` i concurrency v11 już miał). **To jest mierzalne.** Oczekiwanie: **~27–29**,
czyli odzyskanie `CAP=0` (+0.4…+2.2) bez ryzyka nowych warstw.

**Jeśli zostaną sloty po 31.10** — wtedy, i tylko wtedy, warto przetestować `PLAN_COMMIT="1"`
**osobno**, bo to jedyna dźwignia v13, która nie jest martwa ani oparta na rosterze.
`ARC3_WINPATH="1"` **nie** — dopóki `n_passes=1`, nie ma czego odtwarzać.

**Jedna rzecz, która mogłaby zmienić ten werdykt, i jest tania:** gdyby ktoś ustawił
`bm.n_passes = 4` **w bloku `TRUE_SUBMISSION`** (a nie tylko poza nim), wtedy patch 0006
i `DEAD_SKIP` **ożyją** — replay między passami zacznie mieć co robić. **Ale to jest osobna
hipoteza i osobny slot**, a nie dodatek do v13: przy 9 h i 110 grach cztery passy oznaczają
**4× mniej czasu na grę**, a `ANALIZA-23.md` pkt 1 słusznie ostrzega, że RHAE jest **wypukłe
w głębokości**, więc cięcie budżetu na grę kosztuje więcej niż połowę wyniku. **Cztery passy
po płytko mogą być gorsze niż jeden głęboki** — i to jest pytanie, którego nikt nie zmierzył.

---

## 8. Co ten dokument zmienia w poprzednich

| dokument | korekta |
|---|---|
| `DIAGNOZA-23-89-I-PLAN.md` §8 | postulat „dodaj startup keepalive" był **częściowo nadmiarowy** — baza dfranzen ma `ARC3_WARMUP_ACTION_GAMES='1'` + `ARC3_HTTP_RETRY_INITIAL_SECONDS='900'` (§6). Zostaje realna luka: `SERVER_STARTUP_TIMEOUT` 12 min < 25–30 min |
| `RESEARCH-LIDERZY-50PLUS.md` §4.1 | `EXPOSE_UNDO='on'` znalezione **niezależnie** przez gałąź a450b00f o **23:08:29 UTC**, ~30 min przed moją publikacją. Konwergencja, nie przejęcie |
| `RESEARCH-LIDERZY-50PLUS.md` §7 pkt 1 | test logiki `action_names.py` **jest już zrobiony** w v13: `tests/` + weryfikacja przełącznika **w obie strony** na spatchowanym drzewie |
| `OCENA-CODEX-7Z.md` §5 | `roster_probe.jsonl` potwierdza: probe widział **gry publiczne**, bo odpalił się w smoke na bundlu offline. Pytanie o roster **nadal otwarte** i v13 na nim polega |
| `PATCH-0004-I-SEARCH.md` | **`CAP=0` zostało przyjęte przez drugą gałąź** z tym samym uzasadnieniem pomiarowym. Mój patch 0004 jest oficjalnie wycofany z użycia przez obie strony |
