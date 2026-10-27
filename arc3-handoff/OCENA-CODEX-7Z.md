# OCENA: osiągnięcia Codex w `arc-agi-3.7z` — i CZWARTA korekta mojego własnego błędu

**Data:** 27.10.2026 · **Źródło:** `arc-agi-3.7z` (2 283 440 B) na gałęzi
`peteraangelic-pixel/Smak-Domu-Konkurs` @ `arena/5ed750ef-smak-domu-konkurs`, blob
`3b35ee21cbef46ae2c3fed441b31b5c8f0cd6303`. Pobrane przez `gh api`, magia 7z zgodna
(`377abcaf271c`), rozmiar 1:1, rozpakowane `py7zr` 1.1.4 → **522 pliki, 46 MB, 130 `.md`**.

> **Ten dokument zawiera najważniejszą rzecz, jaką znalazłem w tym archiwum: surowy pomiar,
> który OBALA mój własny szacunek z `EKONOMIA-TOKENOW.md` §11.2.** Patrz §3. Mój patch 0004
> (level-token-cap 45k) został zmierzony i wynik jest **ujemny**.

---

## 1. Stan faktyczny na 27.10 — nic nie zostało wysłane

`kaggle/ops/results/r086-submissions/SUMMARY.md`, **STATUS=OK, UTC 2026-10-27 19:39:19**:

| ref | data | status | publicScore |
|---|---|---|---|
| 57629847 | 25.10 12:28 | COMPLETE | **0.00** ← c45 |
| 57607527 | 24.10 21:44 | ERROR | — |
| 57247568 | 16.10 00:02 | COMPLETE | **26.25** ← nadal najlepszy |
| 57201063 | 15.10 | COMPLETE | 23.94 |
| 57125322 | 13.10 | COMPLETE | 24.66 |

**Od 25.10 nie wysłano nic.** `s201-submit-after-midnight` i `s202-try-v7` to opsy z **16.10**,
nie nowe. BEZPIECZNIK (commit `cce4b32c`) działa — zero push/submit bez GO usera.

`s202` przy okazji dokumentuje twardy limit: **„Maximum weekly GPU quota of 30.00 hours
reached"** — czyli kwota GPU jest realnym ograniczeniem, nie tylko deklaracją.

---

## 2. Co Codex faktycznie osiągnął — zweryfikowane, nie przepisane

### 2.1 Uruchomił MÓJ `sweep2.py` na PC usera (27.10, 21:11–21:20)

`analysis/sweep2.py` to **mój plik** — rozpoznawalny po moim docstringu o kalibracji
(`ft09` 288 responsywnych współrzędnych, `sc25` 0 z 4096 klików, `tn36` mediana 1 piksel)
i po `--workers` z domyślną wartością **2**. Uruchomiony z **16 workerami i capem 90 s**:

| plik | gier | wyników |
|---|---|---|
| `sweep2_pc_16w_90s_2026-10-27.jsonl` | 24 | 1957.3 s łącznie (~33 min) |
| `sweep2_pc_lf52_bounded_2026-10-27.jsonl` | 1 (lf52) | 20.4 s |
| `sweep2_pc_full_2026-10-27.jsonl` | 1 (g50t) | 70.6 s |
| `sweep2_smoke_2026-10-27.jsonl` | 2 (ft09, ls20) | smoke |

**Porównanie z moim playbookiem (`results/playbook.json`, sandbox 2 CPU, cap 300 s):**

| | gry z ≥1 poziomem | poziomy |
|---|---|---|
| mój playbook | 11 | **16** |
| ich przebieg PC (16 w., 90 s) | 9 | **14** |
| **UNIA** | — | **17** |

* **Jedyna nowa wartość: `m0r0` — oni 2 poziomy, ja 1.** To jest realny zysk z ich przebiegu.
* **Cap 90 s kosztował więcej niż dał:** stracili `ar25` (1→0), `s5i5` (1→0) i `tu93` (5→4).
  Dokładnie ten mechanizm, który już zmierzyłem: `s5i5` pada przy **45 377 węzłach**, a nie przy
  12 012 — czyli wymaga dłuższego capu (`results/sweep3_bigcap.jsonl`). Przy 90 s nie dochodzi.
* **Wniosek: moc PC nie była ograniczeniem — był nim cap.** 16 workerów na 5950X przerobiło
  24 gry w 33 minuty, czyli ~82 s/grę. Podniesienie capu do 300–600 s przy tej samej maszynie
  powinno odtworzyć moje 16 poziomów **plus** `m0r0` = 17. To jest najtańszy dostępny zysk
  i **nie zjada GPU ani slota**.

### 2.2 Zbudował i przetestował crate Rust na PC

`duck-v12-plan/README.md`: **„32/32 testy crate'a przeszły na Ryzen 9 5950X"**, benchmark
segmentacji 5624 / 363 klatek/s. Ocenione osobno w `OCENA-RUST-BENCH.md`: pomiar czysty,
ale **1 : 34 142 poniżej wiążącego ograniczenia**, więc nie wpływa na wynik konkursu.

Warto odnotować: **ich własny `MY-WORK-STATUS.md` z 13.10** (gałąź `arena/7911f950-pokemon`)
zawiera sekcję „Co jest błędne (usunięte) → **rust-simulator ❌**", a w niej zdanie:
*„Benchmark mierzył szukanie spójnych obszarów na losowych klatkach — **nie jest to wąskie
gardło**"*. To **niezależne, o 14 dni wcześniejsze potwierdzenie** mojego §5 w
`OCENA-RUST-BENCH.md`. Ten sam dokument prostuje też RHAE: *„Limit 1.15 był nałożony na sumę
całej gry zamiast na pojedynczy poziom. Prawdziwy wzór: osobno dla każdego poziomu,
min(115, 100·(base/agent)²), z wagą k"* — **identycznie z moim twierdzeniem o capie**.

### 2.3 Zapakował `duck-v12-plan` — i uczciwie go oznaczył

`duck-v12-plan/README.md` = baza `v11-ex-c45` + **jeden przełącznik `PLAN_COMMIT="1"`**.
Zawiera: łańcuch patchy c45, **concurrency 10 w prawdziwej submisji** (dopasowane do limitu
serwera), limit wyjścia 12k, limit budżetu poziomu, `commit(plan)` z weryfikacją po każdym
kroku, eskalację po 60 akcjach.

**Status dowodów jest uczciwy i to trzeba im policzyć na plus** — piszą wprost:
*„`PLAN_COMMIT="1"` nie ma jeszcze wyniku Kaggle. To świadomy wybór bardziej ambitnego
wariantu, a nie potwierdzenie poprawy wyniku"* oraz *„To nie jest pełna symulacja gry ani
wynik Kaggle"*. Kontrola na Windows 27.10: 5/5 patchy się aplikuje (po pominięciu różnic
białych znaków Git), drzewo się kompiluje, **9 testów `commit(plan)` przechodzi, 3 testy
sandboxu nie startują** z powodu windowsowego procesu sandboxowego.

⚠️ **To jest rozbieżność z moją rekomendacją.** W `POROWNANIE-V11.md` rekomendowałem
`PROFILE="c45"`, **nie** `plan` — bo nigdy nie było czystego pomiaru szybkiej linii i nowa
warstwa potrafi kosztować (ich własne v6 23.94 < v2 24.66). v12 = c45 + `PLAN_COMMIT=1`,
czyli wariant, który odradzałem. Ich `DECYZJA.md` §5 proponuje kolejność **A (fix concurrency,
`PLAN_COMMIT=0`) potem B (`PLAN_COMMIT=1`)** — **to jest zgodne z moją rekomendacją** i daje
czystą atrybucję. v12-plan idzie od razu na B. **Rozstrzygnięcie należy do usera**, ale
argument jest po stronie A-then-B: przy jednym slocie wysłanie B nie powie, czy zapunktował
fix concurrency, czy `commit()`.

### 2.4 Zretraktował własne błędne twierdzenia — zbieżnie z moją oceną

`kaggle/duck-v9/DECYZJA-SLOTU-26-10.md`, **RETRAKCJA 27.10 ~19:55**: wycofują
(1) „v9 w obecnej formie NIE WCHODZI / martwy przed serwerem" i (2) rekomendację kandydata
v10/v11-Smak. **To jest dokładnie to, co wykazałem w `OCENA-V10.md`** — niezależna konwergencja.

`duck-v11-c45/DECYZJA.md` §2 zamyka spór o „martwy patch" **na moją korzyść** i to z
replikacją: *„Zreplikowałem test c87: pełny potok IPythona (`run_cell`) dopisuje `\n` przy
`%%writefile` — plik z notebooka aplikuje się czysto."*

**I dodają coś, czego ja nie znalazłem — należy im się kredyt:**
*„`verify_offline.py` (pakiet v9) dawał fałszywy pass, bo przy ekstrakcji sam dopisywał `\n`.
Weryfikatory mają odtwarzać runtime 1:1 albo oznaczać normalizację."* To jest uogólnienie
mojego ustalenia w regułę i **trafniejsze niż moja wersja**: ja pokazałem, że mechanizm
działa; oni pokazali, **dlaczego ich weryfikator kłamał**. Reguła „weryfikator ma odtwarzać
runtime 1:1" jest warta przyjęcia do `FAKTY-I-POMIARY.md`.

---

## 3. ❌ CZWARTA KOREKTA MOJEGO WŁASNEGO BŁĘDU: kap 45k jest ZMIERZONY UJEMNIE

W `EKONOMIA-TOKENOW.md` §11.2 oszacowałem, że `ARC3_LEVEL_TOKEN_CAP=45000` jest wart
**+4.93 pkt** (26.25 → 31.18), i wpisałem to do tabeli „Najważniejsze liczby" w `README.md`.
**To jest obalone przez surowy pomiar, który leżał w archiwum.**

### 3.1 Surowe źródło, nie ich interpretacja

`kaggle/ops/results/r085-kernel_output_pick/output-pick/benchmark.json` (524 615 B) —
smoke c45, `start 2026-10-25T11:34:10`, `end 12:22:16`, `n_passes=1`, **10 `game_runs`**.
Przeliczyłem sam, z pól `final_score` / `levels_completed` / `number_of_levels`:

| gra | `final_score` | poziomy | akcje (z `roster_probe.jsonl`) |
|---|---|---|---|
| cn04 | **71.43** | 5/6 | 188 |
| ka59 | **49.87** | 5/7 | 253 |
| m0r0 | **46.26** | 4/6 | 252 |
| dc22 | 27.68 | 3/6 | 238 |
| g50t | 21.43 | 3/7 | 192 |
| sc25 | 17.12 | 3/6 | 205 |
| su15 | **13.33** | 3/9 | 102 |
| ls20 | 8.79 | 3/7 | 427 |
| s5i5 | 8.33 | 2/8 | 82 |
| tn36 | 3.57 | 1/7 | 187 |

> **MEAN `final_score` = 26.78** · **SUMA `levels_completed` = 32**

Obie liczby zgadzają się **co do setnej** z ich `DECYZJA-SLOTU-26-10.md` (26.78 / 32 poziomy).
Ich wartości per gra (cn04 71.4, ka59 49.9, m0r0 46.3, ls20 8.8, su15 13.3, sc25 17.1,
dc22 27.7) też — **to jest rzetelnie policzone, nie przepisane**.

### 3.2 Porównanie trzech smoke'ów na tych samych 10 grach

| smoke | config | MEAN |
|---|---|---|
| **v3** | bez capa | **29.02** |
| **v6 / r019** | bez capa | **27.21** |
| **c45** | **Z moim capem 45k** | **26.78** |

**c45 jest NAJNIŻSZY z trzech.** Mój kap kosztuje **−0.43** wobec r019 i **−2.24** wobec v3.

Mechanizm widać w ich tabeli zysków/strat, którą potwierdzam surowymi liczbami:

| gra | c45 (cap 45k) | r019 (bez capa) | Δ |
|---|---|---|---|
| ka59 | 49.87 | 17.9 | **+32.0** |
| cn04 | 71.43 | 47.6 | **+23.8** |
| m0r0 | 46.26 | 28.6 | **+17.7** |
| ls20 | 8.79 | 3.3 | **+5.5** |
| dc22 | 27.68 | 44.8 | **−17.1** |
| sc25 | 17.12 | 42.6 | **−25.5** |
| su15 | 13.33 | 56.4 | **−43.1** |

Suma siedmiu znanych Δ = **+79.0 − 85.7 = −6.7**, czyli −0.67 na grę przy 10 grach.
Pozostałe trzy (g50t, s5i5, tn36) dokładają +0.24 → razem −0.43. **Zgadza się z pomiarem.**

### 3.3 Dlaczego mój model się pomylił — i to jest cenniejsze niż sama korekta

Mój model brał `w` = „frakcja puli wydana na poziom, który **nigdy nie został ukończony**"
(zmierzone: agregat 35 %, tn36 86 %, ls20 91 %) i zakładał, że kap odzyskuje te tokeny.

**Błąd: zastosowałem statystykę o poziomach SKAZANYCH do wszystkich poziomów.**
Kap strzela do każdego poziomu, który przekroczy 45k — także do takiego, który **właśnie
miał zostać ukończony**. `su15` stracił 43.1 pkt, bo kap zabił długi poziom, który r019
dokończył. `sc25` i `dc22` tak samo.

Czyli `w` opisuje populację, **na którą kap nie działa** (poziom już przegrany — tam odzysk
jest prawdziwy), a szkoda dzieje się w populacji, **której `w` nie opisuje**. Model miał
poprawną arytmetykę i złą populację. To jest **trzecia** odmiana tego samego błędu w tej
sesji, po `concurrency=120` i kalibracji ×0.718:

> **Poprawna arytmetyka na źle dobranej populacji daje pewny siebie, fałszywy wynik.**
> Zanim policzę efekt dźwigni, muszę zapytać: **na których obiektach ta dźwignia faktycznie
> się uruchamia**, a nie na których chciałbym, żeby się uruchamiała.

### 3.4 Konsekwencja: `ARC3_LEVEL_TOKEN_CAP=0` wyłącza CAŁY mój patch 0004

Ich reguła decyzyjna brzmi: *„LB c45 < 29 → v9 profil c45 z `ARC3_LEVEL_TOKEN_CAP=0`
(usuwa podejrzanego regresu su15/sc25)"*. Sprawdziłem semantykę zera w moim kodzie, bo
„0" mogło znaczyć „zero tokenów dozwolone" — to była dokładnie ta klasa pułapki, która
spowodowała 0.00:

```python
# arc3-handoff/arc3_level_budget.py
@property
def enabled(self) -> bool:
    return self.cap > 0                      # L95-97

def peek(self, generated_tokens, levels_completed) -> str:
    if not self.enabled:
        return KEEP_GOING                    # L110-111
```
oraz `patches/0004-level-token-cap.patch:42`: `ARC3_LEVEL_TOKEN_CAP  tokens one level may
consume before acting (0 = off)`, i `from_env` ma default **0**.

> ✅ **ALL-CLEAR: `=0` znaczy WYŁĄCZONE, nie „zero tokenów".** Ich plan jest bezpieczny.
>
> ⚠️ **Ale konsekwencja jest większa, niż zapisali:** ponieważ `enabled = cap > 0`, a `peek()`
> przy `not enabled` natychmiast zwraca `KEEP_GOING`, wyłączenie capa **wyłącza cały mechanizm
> — także `RESET_LEVEL` i `ABANDON`**. Mój patch 0004 staje się **no-opem**. Nie da się
> wyłączyć capa a zostawić darmowego `RESET_LEVEL`: oba wiszą na tym samym warunku.
>
> **Uczciwy werdykt o patchu 0004: zmierzony, wynik ujemny, należy go wyłączyć.**
> `RESET_LEVEL` (darmowy, 0 tokenów LLM) pozostaje **niezmierzony osobno** — żeby go
> zmierzyć, trzeba by rozdzielić wyzwalacz (np. cap wysoki, ale reset niezależny od niego),
> a to jest zmiana kodu, nie env.

---

## 4. Poprawione oczekiwanie wyniku c45 po naprawie `concurrency`

`EKONOMIA-TOKENOW.md` §11.3 dawał **26–31, główny szacunek 31.18**. To było oparte na
oszacowanym +4.93 z capa. **Pomiar daje inną kotwicę i jest lepszy niż model:**

| kotwica | wartość | status |
|---|---|---|
| **c45 smoke — ta sama konfiguracja, która idzie do submisji** | **26.78** | ✅ **zmierzone** (r085) |
| v6/r019 smoke, bez capa | 27.21 | ✅ zmierzone |
| v3 smoke, bez capa | 29.02 | ✅ zmierzone |
| ich najlepszy LB | 26.25 | ✅ zmierzone |
| ~~mój model z kapem~~ | ~~31.18~~ | ❌ **obalone** |

> **POPRAWIONE OCZEKIWANIE: 24–29, punktowo ~26.8** dla c45 **z capem**, czyli
> **praktycznie tyle samo co ich obecny najlepszy wynik 26.25.**
>
> **Z `ARC3_LEVEL_TOKEN_CAP=0`: ~27.2–29.0**, czyli **+0.4 do +2.2** względem wariantu z capem.
>
> Dwa przeciwstawne efekty smoke→rerun, oba niezmierzone: rerun daje **2.2 h na grę** zamiast
> 48 min (więcej głębokości, w górę), a kalibracja Gemmy mówi **smoke→LB −2.8 do −5.9 pp**
> (w dół). Dlatego przedział, nie punkt.

**Wniosek operacyjny, mocniejszy niż poprzedni:**

1. **Naprawa `concurrency` jest konieczna, ale ona tylko PRZYWRACA wynik do ~26.8, nie podnosi go.**
   0.00 → ~26.8. To wciąż największy pojedynczy dostępny skok i wciąż warta slota — ale to jest
   **odzyskanie straty**, nie zysk.
2. **Wyłączenie mojego capa jest warte +0.4 do +2.2 pkt i kosztuje jedną zmienną env.**
   To jest teraz **najtańsza znana dźwignia dodatnia** — tańsza niż cokolwiek w
   `DIAGNOZA-45plus.md`, bo jest już zmierzona na tych samych 10 grach.
3. **Luka do progu 50.37 zostaje ~21–24 pkt.** Żadna z dotąd zmierzonych dźwigni jej nie domyka.

### 4.1 Dwie rzeczy, które pomiar POTWIERDZIŁ w moim modelu

Uczciwie — nie wszystko było złe:

* **Budżet akcji: mój model zakładał 208 akcji na grę.** Zmierzone z `roster_probe.jsonl`
  (zdarzenia `end`, pole `actions`): **2126 akcji / 10 gier = 212.6**. **Odchyłka 2.2 %.**
  Arytmetyka „175k tokenów / 841 tok/akcję ≈ 208 akcji" jest **potwierdzona**.
* **Concurrency 10 działa równolegle:** 10 gier × 2880 s, a wall clock `11:34:10 → 12:22:16`
  = **2886 s**. Czyli wszystkie 10 poszły naraz w 48 minut — **dokładnie ten mechanizm,
  którego zabrakło przy `concurrency=120`**. To niezależne potwierdzenie diagnozy 0.00.

⚠️ **Luka w danych:** `final_generated_tokens` i `final_uncached_input_tokens` są **0 dla
wszystkich 10 gier** w `benchmark.json`. Czyli tok/akcję **828** z ich `DECYZJA-SLOTU`
pochodzi z innego źródła (`serve.log`, 986 600 B), nie z tego pliku. Nie zweryfikowałem go
— oznaczam jako **niepotwierdzony z tego artefaktu**.

---

## 5. Roster probe NIE rozstrzygnął pytania o roster

W `POROWNANIE-V11.md` napisałem, że roster probe jest najważniejszą częścią c45, bo powie,
czy playbook i triage są cokolwiek warte. **Pliki są** (`roster_probe.jsonl`, 20 linii:
10 × `start` + 10 × `end`), ale:

* pola `start`: `game_id`, `index`, `frame0` (hash 16 hex), `actions_avail`, `win_levels=null`
* pola `end`: `game_id`, `index`, `actions`, `levels`, `frame_end`
* **`game_id` to 10 GIER PUBLICZNYCH** (`cn04-2fe56bfb`, `dc22-fdcac232`, `g50t-5849a774`,
  `ka59-38d34dbb`, `ls20-9607627b`, `m0r0-492f87ba`, `s5i5-18d95033`, `sc25-635fd71a`,
  `su15-1944f8ab`, `tn36-ef4dde99`)

> **Probe odpalił się w SMOKE, który używa 10 gier publicznych z bundla — nie na gatewayu.**
> Zgodnie z docstringiem `taaf/competition_arcade.py`, prawdziwa ścieżka Kaggle mówi do
> Arcade z gatewayem („one scorecard, hidden baselines, **no repeated game IDs**"), a moduł
> lokalny startuje tę samą aplikację REST **na bundlowanych grach offline**.
>
> **Czyli pytanie o prywatny roster 110 gier POZOSTAJE OTWARTE.** Probe musiałby odpalić się
> w rerunie — a rerun zginął (0.00, brak artefaktów). Wartość playbooka i triage'u jest
> **nadal niezmierzona**, i moje wycofanie („na realnym LB prawdopodobnie 0") **stoi**.

To jest też lekcja o bramce `ARC3_SMOKE_OK`: **smoke nie testuje ścieżki submisji** — ani pod
względem `concurrency` (ustalenie wcześniejsze), **ani pod względem rostru** (ustalenie nowe).
Dwie niezależne klasy pytań, na które smoke strukturalnie nie odpowiada.

---

## 6. Jedna rozbieżność merytoryczna — dźwignia #4

Ich `DECYZJA.md` §4: *„`PERSISTENT_FUNCTIONS_SCOPE='game'` jest akceptowane — **dźwignia #4
żyje**."*

**Pierwsza połowa zdania jest prawdziwa, druga nie.** Walidator
(`patches/0000-franzen-harness-changes.patch` L3559-3560):
`return scope if scope in ("turn","levelup","game") else "levelup"`.

* `'game'` **jest** akceptowane ✅ — i ich notebook już to ma w cell 9.
* Ale **najszersza dozwolona wartość to `game`**, a dźwignia #4 (moja) obiecywała
  *„×4–5 na raz rozwiązanej mechanice (jeśli roster cykliczny)"* — czyli **przetrwanie wiedzy
  MIĘDZY grami w obrębie runa**. Zakresu `run` **nie ma**, więc ten mechanizm **nie istnieje**.
* Docstring patcha L3612-3613 dodaje: *„State and variables are never serialized"* — przetrwają
  co najwyżej **definicje funkcji**, nie dane.

> **„Wartość env jest akceptowana" ≠ „dźwignia działa".** Dźwignia #4 jest martwa w części
> `SCOPE`, a żywa w części `lessons-between-games` — pod warunkiem, że ta druga zostanie
> zaimplementowana **innym mechanizmem** niż `SCOPE` (np. port z `llm-agent/llm_policy.py`
> albo stan na dysku w `/kaggle/working`). Pełny wywód: `EKONOMIA-TOKENOW.md` §12.1 i §8.

---

## 7. Sprzęt usera — potwierdzony, i to zmienia moją rekomendację z §7 `OCENA-RUST-BENCH.md`

Z `STATUS.md` i `MY-WORK-STATUS.md`:

| | wartość |
|---|---|
| CPU | **AMD Ryzen 9 5950X, 16 rdzeni / 32 wątki** |
| RAM | **64 GB** |
| GPU | 8–16 GB VRAM → lokalnie tylko modele 7–8B; 27B wymaga Kaggle |
| mój sandbox dla porównania | **2 CPU / 3939 MB RAM** |

**64 GB RAM** rozstrzyga sprawę, którą w `OCENA-RUST-BENCH.md` §7 zostawiłem jako założenie
(„prawdopodobnie 32–64 GB"): mój zmierzony bloker `re86` = 0.190 MB/stan × 94 405 stanów =
**17.9 GB** mieści się w 64 GB **z 3.5× zapasem**. Czyli przeszukiwanie, które u mnie umarło
na pamięć, **na tej maszynie jest wykonalne**.

---

## 8. Co z tego wynika — trzy rzeczy w kolejności wartości

1. **Wyłączyć mój kap: `ARC3_LEVEL_TOKEN_CAP=0`.** Zmierzone **+0.4 do +2.2 pkt** na tych
   samych 10 grach, koszt = jedna zmienna env. To jest **jedyna znana zmierzona dźwignia
   dodatnia** i jest moja-własna-ale-ujemna, więc tym bardziej należy ją wyjąć.
   Uwaga: wyłącza cały patch 0004 (§3.4).
2. **Naprawić `concurrency` (10) — konieczne, ale to odzyskanie ~26.8, nie zysk.** Kolejność
   **A potem B** z ich `DECYZJA.md` §5, nie v12-plan od razu na `PLAN_COMMIT=1` (§2.3):
   przy ~2 slotach wysłanie B nie da atrybucji.
3. **Podnieść cap w `sweep2.py` na PC z 90 s do 300–600 s i powtórzyć przebieg.**
   Ich własny pomiar pokazuje, że **maszyna nie była ograniczeniem** (24 gry w 33 min),
   a cap 90 s kosztował `ar25`, `s5i5`, `tu93` — przy zysku tylko na `m0r0`. Przy 300 s
   unia powinna dać **17 poziomów**. **0 GPU, 0 tokenów, 0 slotów.** To jest najtańsza
   rzecz na tej liście i jedyna, która dokłada poziomy.

**Nie rekomenduję** dalszych pomiarów segmentacji (`OCENA-RUST-BENCH.md` §5: 1 : 34 142
poniżej wiążącego ograniczenia) ani wysyłania v12-plan jako pierwszego.
