# DIAGNOZA 23.89 i PLAN na 4 dni — oraz dlaczego „mega wersja na 50+" nie istnieje

**Data:** 28.10.2026, ~23:10 UTC · **Submisja:** ref **57737623**, `arc3-duck-v11` v1, slot A, 28.10 13:11:56
**Wynik:** COMPLETE, **publicScore 23.89** · **Deadline:** 2 XI 23:59 UTC · **1 submisja/dzień**

> **STRESZCZENIE UCZCIWE, zanim szczegóły:**
> 1. **23.89 nie jest anomaliią — to niskie losowanie.** Nasza baza (Franzen M2) ma udokumentowany
>    rozkład publiczny **średnia 25.77, SD 3.93**, z zaobserwowanymi drawami **21.01** i **35.35**. 23.89 mieści
>    się w ±1 SD. Nasz „najlepszy" wynik **26.25 też jest zwykłym drawem Franzena**, nie osiągnięciem.
> 2. **Mój patch 0004 (cap 45k) jest zmierzony ujemnie i musi być wyłączony.** W v11 trzy gry
>    skończyły się 20–23 minuty za wcześnie, porzucając **243 600 tokenów**.
> 3. **Jest JEDNA zmierzona dodatnia dźwignia na naszej dokładnie bazie: scheduler priorytetowy D′**
>    (średnia 25.77 → ~29.0). My gramy **równym przydziałem czasu**, co ich lista błędów śmiertelnych
>    wymienia jako **zakazane** (#6).
> 4. **50+ jest nieosiągalne do 2 XI.** Próg top-5 to **51.04**, baza ma średnią 25.77. To **+25.3 pkt
>    = +6.4 SD**. Zespół z 29 submisjami i 4 rundami researchu (~100 publicznych notebooków) konkluduje:
>    *„no public or published idea shows a measured gain on top of our agent"*.
> 5. **Realny cel: średnia ~29–30, drawy do ~35.** Linie medali z 27.10 (4904 zespoły):
>    złoto ≈ 38.2 · **srebro ≈ 32.33** · brąz ≈ 31.04. Czyli **srebro jest w zasięgu jednego
>    szczęśliwego drawa**, a 50+ nie jest w zasięgu żadnej liczby drawów.

---

## 1. Co dokładnie zostało wysłane i co się stało

Z `ops/results/r100-submissions/SUMMARY.md` (STATUS=OK, UTC 2026-10-28 22:59:23), opis submisji:

```
arc3-duck-v11 slot A 28.10: c45 config (PLAN_COMMIT=0, cap45k/r1, WM=0)
+ concurrency fix 120->10 w TRUE_SUBMISSION (przyczyna 0.00 c45, ref 57629847);
smoke ARC3_SMOKE_OK mean 18.54
```

**Naprawa `concurrency` ZADZIAŁAŁA.** Poprzedni rerun c45 dał **0.00** (ref 57629847); ten dał
**23.89** i status COMPLETE. Strukturalne zero jest usunięte — to jest potwierdzenie diagnozy
z `POROWNANIE-V11.md` w produkcji.

Ale wynik jest **niższy niż ich dotychczasowy najlepszy 26.25** i niższy niż smoke c45 (26.78).

### 1.1 Pełna historia submisji (r100)

| ref | data | config | publicScore |
|---|---|---|---|
| **57737623** | **28.10 13:11** | **v11 slot A: c45 + fix concurrency + 0005** | **23.89** |
| 57629847 | 25.10 12:28 | c45 (concurrency=120) | **0.00** |
| 57607527 | 24.10 21:44 | duck-original v5 | ERROR |
| 57247568 | 16.10 00:02 | duck v3 | **26.25** ← dotąd najlepszy |
| 57201063 | 15.10 | v5-world-model-stuck | 23.94 |
| 57125322 | 13.10 | v2-think-less | 24.66 |
| 57104951 / 57102988 | 12.10 | t4-v2 qwen2.5-7b | ERROR / ERROR |
| 57075036 | 11.10 | novelty-explorer baseline | 0.01 |

**Sześć submisji z rzędu w paśmie 23.89–26.25** (pomijając zera i ERROR-y). To nie jest sześć
niezależnych porażek — to **sześć drawów tej samej bazy**, z czego dwa zepsute przez błędy
konfiguracji (0.00, ERROR).

---

## 2. Dlaczego 23.89 — trzy przyczyny, w kolejności pewności

### 2.1 SZUM (pewność: wysoka, źródło zewnętrzne i zmierzone)

Najważniejsza rzecz, której **nie miałem w żadnym z moich 10 dokumentów**. Z publicznej analizy
zespołu na **identycznej bazie** (§3):

| kod | drawy na publicznym LB |
|---|---|
| **Franzen M2 bez zmian** | 27.89, 27.62, 27.83, 27.80, **21.01**, 31.47, 25.67, **35.35** → forum: **średnia 25.77, SD 3.93** |
| D′ scheduler | 31.54, 30.74, 29.05, **24.77** → średnia ≈ **29.0** |

* Model sampluje z **temperaturą 0.7**, a wynik gry jest **prawie bimodalny** (≈0 albo ≈100).
* **Ten sam kod** (ich v5) dał 29.05, potem **24.77** (−4.3), potem **30.01**.
* Dwa identyczne przebiegi treningowe: **39.84** i **38.12**, z rozstrzałem **~14 pkt na grę**,
  w tym **`cn04` poszło 71 → 4**.
* **Zmiana musi dać ~+5 pkt, żeby jeden draw cokolwiek mówił.**
* **Wyświetlany wynik notebooka to NAJSZCZĘŚLIWSZY draw, nie średnia.** Strona Franzena pokazuje
  34.30 — artefakt wyświetlania, realny draw to 25.67.

> **Konsekwencja dla nas, i to jest korekta mojego własnego rozumowania:**
> **23.89 mieści się w ±1 SD bazy (25.77 ± 3.93 → 21.84–29.70).** Franzen M2 ma udokumentowany
> draw **21.01**. Czyli 23.89 **nie dowodzi**, że v11 jest gorszy od c45 — dowodzi tylko, że
> to był niski draw.
>
> **I muszę wycofać część wczorajszej diagnozy.** W `OCENA-CODEX-7Z.md` przypisałem spadek smoke
> 26.78 → 18.55 patchowi `0005-plan-commit`, bo env był bajt-identyczny a patche różniły się o jeden.
> **Ten wniosek był zbyt mocny.** `cn04` 71.43 → 4.76 to **dokładnie ten sam swing, który inny zespół
> udokumentował na IDENTYCZNYM kodzie** (71 → 4). Przy rozstrzale ~14 pkt/grę jedno porównanie smoke
> **nie może** ustalić winnego. Zostawiam to, co jest strukturalne (§2.2), i wycofuję przypisanie
> całego −8.23 patchowi 0005.

### 2.2 Mój kap 45k + `min_done=0` porzuca gry wcześnie (pewność: wysoka, dowód strukturalny)

To jest **niezależne od szumu**, bo to nie są punkty — to są sekundy i tokeny.

Z `r093-kernel_output_pick/output-pick/benchmark.json` (v11, start 12:16:24, end 13:04:37)
i `arc3-duck-v11.log`:

| gra | v11 wall | v11 tokeny | v11 poziomy | c45 wall | c45 tokeny | c45 poziomy |
|---|---|---|---|---|---|---|
| **g50t** | **1499 s** | **91 902** | **0/7** | 2881 s | 151 576 | 3/7 |
| **cn04** | **1609 s** | **87 614** | 1/6 | 2880 s | 150 263 | 5/6 |
| **tn36** | **1692 s** | 101 886 | 1/7 | 2166 s | 95 753 | 1/7 |
| pozostałe 7 | ~2871–2893 s | 132–171 k | — | ~2880 s | — | — |

**Trzy gry zakończyły się o 1188–1381 s za wcześnie**, porzucając łącznie
**3840 s = 64 minuty** czasu i **~243 600 tokenów** z puli ~175 k/grę.

`g50t` jest najważniejszy: **0/7 poziomów, 91 902 tokeny, 1499 s.** Gra, która **nie zapunktowała
wcale**, sama się zatrzymała, mając 23 minuty i 83 k tokenów zapasu. To nie jest losowość —
to jest mechanizm.

Mechanizm w logu, **26 wystąpień** (c45: **18**):

```
g50t-5849a774: level budget exhausted (LevelBudget(cap=45000, resets=1/1, level=0, min_done=0))
cn04-2fe56bfb: level budget exhausted (LevelBudget(cap=45000, resets=1/1, level=1, min_done=0))
```

i w `arc3_level_budget.py`:

```python
if self.resets_used < self.max_resets: return RESET_LEVEL
if int(levels_completed) < self.min_done: return KEEP_GOING   # min_done=0 → NIGDY nie chroni
return ABANDON
```

> **BŁĄD PROJEKTOWY W MOIM PATCHU, teraz zmierzony w produkcji:**
> przy `min_done=0` warunek `levels_completed < 0` **nigdy** nie jest prawdziwy, więc `ABANDON`
> odpala **także na grze z zerem ukończonych poziomów**. A to jest dokładnie gra, która ma
> **najwięcej do zyskania** kontynuując. Mój kill-switch domyślnie wyłącza ochronę, która
> jest najbardziej potrzebna.
>
> Poprawna wartość to `ARC3_LEVEL_MIN_DONE` **> 0** (np. 1–2), albo `ARC3_LEVEL_TOKEN_CAP=0`
> (wyłącza cały mechanizm — `enabled = cap > 0`).

To jest **piąta** korekta mojego własnego błędu w tej sesji i **druga** w tym samym patchu:
wczoraj pomiar pokazał, że kap jest warty −0.43 wobec r019 (`OCENA-CODEX-7Z.md` §3); dziś log
pokazuje **dlaczego** — nie „kap tnie długie poziomy", tylko **`ABANDON` wyrzuca gry z budżetem**.

### 2.3 Gramy równym przydziałem czasu — a to jest błąd śmiertelny #6 (pewność: wysoka)

Ich lista „Fatal mistakes and anti-patterns (NEVER repeat)", punkt **6**:

> **„Never use uniform time allocation. Priority scheduling (D′) is essential."**

Nasza konfiguracja (c45 i v11) daje każdej grze **równy** czas: 10 gier × 2880 s. Zmierzone
konsekwencje u nich, na tej samej bazie:

* **cd82** scored 0 w obu kontrolach i ~100 w przebiegach zmienionych — bo agent nie zaliczył
  poziomu 1 w ~50 akcjach, scheduler zepchnął go na koniec kolejki i **nigdy nie dostał czasu modelu**.
* **lf52 i su15** czasami **w ogóle nie dostają tury** — scheduler celowo daje gry z wieloma
  poziomami (lf52 ma 10) na koniec, bo ich pierwszy poziom jest wart mniej punktów.

Czyli przy równym przydziale **część gier dostaje czas, w którym i tak nie zapunktuje**, a gry
z największym potencjałem czekają. To jest dokładnie ten sam mechanizm, który opisałem w
`DIAGNOZA-45plus.md` jako dźwignię `ABANDON` („oddaj slot grze, która robi postęp") — **ale oni
to zaimplementowali jako SCHEDULER, nie jako zabicie gry**, i **zmierzyli +2 do +3 pkt**.

> **Kluczowe rozróżnienie, którego ja nie zrobiłem:**
> * **Scheduler priorytetowy** = zmienia KOLEJNOŚĆ dostępu do czasu modelu. Gra pozostaje żywa.
>   Zmierzone: **25.77 → ~29.0**.
> * **Mój `ABANDON`** = TRWALE kończy grę i oddaje jej budżet. Zmierzone: **g50t 0/7 przy
>   23 minutach zapasu**.
>
> To jest ta sama intuicja („nie marnuj czasu na gry, które stoją") zrealizowana w sposób, który
> **niszczy wartość** zamiast ją przenosić. `ABANDON` jest nieodwracalny; priorytet nie.

---

## 3. Źródło zewnętrzne: zespół na IDENTYCZNEJ bazie, 29 submisji, 4 rundy researchu

`github.com/mayankraj4728/ARC-AGI-3-2026`, README 1217 linii, **aktualizowany 28.10** (dziś).
Pobrany przez `api.github.com`.

**Dlaczego to źródło jest warte więcej niż wszystkie moje modele razem:** ich baza to
**„Daniel Franzen's Milestone-2 solution + Tufa Labs Duck harness + Qwen3.8-Flash-Next (W4A16)
serwowany przez SGLang, 10 gier naraz"** — czyli **dokładnie nasza linia c45** (opis ref 57629847:
„fast-line (SGLang + Qwen3.8-Flash-Next W4A16 + drafter, Franzen-lineage)"). Ich Franzen M2
bez zmian = **25.67**; nasz duck v3 = **26.25**. **Te same liczby z tego samego rozkładu.**

### 3.1 Zmierzone i ODRZUCONE — czyli lista slotów, których nie musimy spalić

| pomysł | problem, który miał rozwiązać | wynik | werdykt |
|---|---|---|---|
| **ThinkingCap** (model myślący krócej) | myślenie zjada czas i tokeny | 10 gier × 60 min: **62.24 vs 74.47**, 57 vs 62 z 72 poziomów, 4242 vs 2500 akcji | ❌ mniej poziomów, więcej zmarnowanych akcji |
| **Pamięć rozwiązanych poziomów** | agent zapomina po przycięciu historii | LB średnia **≈25.2** (5 przebiegów) vs **27.9** bez | ❌ nigdy nie pobiła wersji bez pamięci |
| **Helper-retention fix** | timeout wyrzucał wszystkie helpery (119 w jednym przebiegu) | **41.80** vs 39.84 kontrola, **+2.8 ± 5.7** | ❌ działa, ale zysk mniejszy niż szum |
| **No-op guard** | powtarzanie akcji, które nic nie zmieniają | trening **42.23**, **+3.3 ± 5.4** (remis); LB z nim: **23.57** | ❌ remis w treningu, niski LB |
| **Strategy-audit message** (Lord Han Solo, 2. miejsce M2) | agent zakleszcza się na złej regule | **40.84** ale **85 poziomów** (mniej niż obie kontrole), **+1.9 ± 6.3** | ❌ mniej poziomów, w szumie |
| **Więcej strumieni / więcej pamięci GPU / dłuższy kontekst / niższa temperatura** | — | **−7 do −8 na zbiorze ukrytym**; niższa temperatura → agent trzyma się pierwszego pomysłu | ❌ **błąd śmiertelny #13** |
| **Dodatkowe rady w prompt** | — | **−2.3 / −3.4** (zmierzone przez inne zespoły) | ❌ |
| **Replay wygranej ścieżki** | — | **gateway odmawia otwarcia gry dwa razy** i może zostawić otwartą kartę wyników → ryzyko 0.00 | ❌ |
| **Model jako Dataset** (szybsze ładowanie) | wolny dysk | re-upload ~185 GB + nowy smoke | ⏭️ za późno i ryzykowne; keepalive już to pokrywa |
| **Twierdzenia z papierów** (PRO-LONG, OpenAI compaction, NVIDIA AVO) | — | używają dużych modeli chmurowych albo nasz agent już robi to samo | ❌ |

> ⚠️ **To bezpośrednio potwierdza dwie moje wcześniejsze korekty i jedną zabija:**
> * **Potwierdza** wycofanie „lever #3: podnieść `MAXREQ` 10→16-20" (`FAKTY` L677-679) —
>   zmierzone **−7 do −8**. Miałem rację, że dźwignia była odwrotna.
> * **Potwierdza** wycofanie playbooka i replayu — gateway **odmawia** otwarcia gry dwa razy.
> * **Zabija całą moją linię searchu offline.** Patrz §4.

Ich konkluzja, dosłownie:

> *„Bottom line: no public or published idea shows a measured gain on top of our agent.
> Silver (≈32.33) is only 2.3 above our best (30.01), and that's within one run's luck
> (spread about ±4). The best tool left is to **submit the safe release several times**."*

### 3.2 Cztery poprawki bezpieczeństwa — i dlaczego to jest najwyższa wartość oczekiwana

My **już spaliliśmy** jedno 0.00 (concurrency) i jeden ERROR. Oni widzieli u siebie
**0.00, 0.00, 0.01** jednego dnia (25.10) na niezweryfikowanym kodzie.

| # | poprawka | mechanizm awarii, który blokuje |
|---|---|---|
| 1 | **gateway check** | jeśli Kaggle nie ustawi flagi „to jest bieg punktowany", notebook sprawdza, czy gateway odpowiada — inaczej bieg punktowany idzie ścieżką „practice" i daje **0.00** |
| 2 | **startup keepalive** | **gateway kończy bieg po 15 MINUTACH bez akcji.** Ładowanie modelu na Kaggle obserwowane: 257 s, 599 s, **25 min, ponad 30 min**. Bez keepalive wolny dysk = **0.00**. U nich przetrwało 25-minutowe ładowanie |
| 3 | **start retry** (z S16 ondrewsha) | jedna nieudana start gry zamyka **wspólną kartę wyników** → **0.00**. Odtworzone na CPU. Retry 4×, co 5 s |
| 4 | **dłuższe czekanie na gateway** | 30 min zamiast 10; dodatkowy czas odejmowany od czasu gier, więc bieg nie kończy się później. **Inny zespół stracił przebieg ~33.7 (wynik 8.61)** przez awarię gatewaya dłuższą niż 10 min |

> **To jest jedyna zmiana na tej liście, która nie jest w szumie.** Ochrona przed 0.00 nie podnosi
> średniej — ona **usuwa zero z rozkładu**. Przy naszej historii (0.00, ERROR, ERROR, 0.01) to jest
> **największa dostępna wartość oczekiwana**, większa niż jakakolwiek dźwignia merytoryczna.
>
> I to jest ta sama lekcja co `concurrency=120`: **nasze bramki walidują ścieżkę treningową,
> a awarie są na ścieżce submisji.** Ich keepalive i gateway check istnieją dokładnie dlatego,
> że smoke **nie** testuje tych awarii.

### 3.3 Ich „błędy śmiertelne", które MY obecnie popełniamy

| # | ich reguła | nasz stan |
|---|---|---|
| **1** | **Nigdy nie używaj źródeł gier offline (`find_game_source`). Ukryte gry istnieją tylko za gatewayem** | ❌ **cała moja linia searchu offline na tym stoi** — patrz §4 |
| **6** | **Nigdy nie używaj równego przydziału czasu. Scheduler priorytetowy (D′) jest niezbędny** | ❌ gramy równo: 10 × 2880 s |
| **8** | **Nigdy nie stackuj kilku niepunktowanych zmian w jednej submisji** (przy ±4 szumu nie wiesz, co zaszkodziło) | ❌ v11 = fix concurrency **+** 0005 **+** cap45k **+** WM=0 naraz |
| **9** | Nigdy nie licz na `n_passes > 1` ani replaye w rerunie. Jeden bieg na grę | ✅ `n_passes=1` |
| **11** | Nigdy nie usuwaj startup keepalive | ❌ **nie mamy go** |
| **13** | Nigdy nie zmieniaj parametrów serwingu (strumienie, MEMFRAC, kontekst, speculative steps) | ✅ nie zmieniamy (i dobrze — patrz §3.1) |

---

## 4. ❌ Moja linia searchu offline jest ZMIERZONA NA 0.20 — wycofuję ją

Ich pierwsza submisja w rodowodzie:

| ref | data | co to było | wynik |
|---|---|---|---|
| 57272788 | 16.10 | **v1/v2: offline source-introspection BFS (`find_game_source`)** | **0.20** |

z adnotacją: **„❌ Game sources don't exist in the rerun"**, i jako błąd śmiertelny #1:
**„Never use offline game sources (`find_game_source`). Hidden games exist only behind the gateway."**

Drugie, niezależne potwierdzenie z `github.com/rasagyavatsal/arc-prize-2026-arc-agi-3`:

> **Held-out evaluation: 0/113 poziomów rozwiązanych na 15 grach held-out vs 7/70 na 10 grach
> dostrojonych.** „The public-25 score over-predicts the leaderboard because its points come from
> games the agent was tuned on."

> **WYCOFUJĘ całą linię searchu offline jako źródło punktów.**
> Dotyczy to: `arc3_search.py`, `sweep.py`, `sweep2.py`, `build_playbook.py`, `results/playbook.json`
> (11 gier / 16 poziomów / 3.18 pkt), `results/budget_triage.tsv` i `calib_probe.py` jako źródła
> sekwencji. **Wszystko to czyta źródła 25 gier publicznych, których w rerunie NIE MA.**
>
> Wczoraj napisałem „na realnym LB prawdopodobnie 0" — dziś mam **pomiar: 0.20** oraz
> **0/113 poziomów na held-out**. To nie jest „prawdopodobnie", to jest zmierzone.
>
> **Co z tego zostaje użytecznego:** twierdzenie o capie i wzór RHAE (potwierdzone oficjalnie),
> arytmetyka budżetu (**212.6 akcji/grę zmierzone vs 208 w modelu = 2.2 %**, `OCENA-CODEX-7Z.md` §4.1),
> model ekonomii tokenowej **jako narzędzie do rozumowania o ograniczeniach** (nie jako prognoza),
> i `sweep2.py` **jako harness do testowania logiki agenta** — ale nie do produkowania sekwencji.
>
> **Konsekwencja dla pytania usera o Rust+rayon: patrz §6 — to nie jest droga do 50 punktów.**

---

## 5. Dlaczego „mega wersja na 50+" nie istnieje — arytmetyka, nie pesymizm

| wielkość | wartość | źródło |
|---|---|---|
| próg top-5 (5. miejsce) | **51.04** (yktori, 27.10 18:13) | `ops/results/r101-lb`, 28.10 23:01 UTC |
| top-5 obecnie | Chen **75.56** · Tufa **68.91** · Turducken **56.02** · last dance **51.51** · yktori **51.04** | j.w. |
| średnia naszej bazy (Franzen M2) | **25.77**, **SD 3.93** | §3.1, 8 drawów publicznych |
| najlepszy zmierzony draw bazy | 35.35 | j.w. |
| najlepsza zmierzona dźwignia (D′) | średnia **~29.0** | j.w. |
| nasza najlepsza submisja | **26.25** | r100 |
| **wymagany skok od średniej bazy** | **+25.3 pkt = +6.4 SD** | — |
| liczba drawów potrzebna na 51 przy SD 3.93 | **praktycznie nieskończona** (P(X≥51) ≈ 0 przy μ=25.77) | — |
| dostępnych slotów do 2 XI | **~4–5** (1/dzień) | `0 submissions remaining today` w r095 |
| wpisy zespołów na 50+ | Turducken **212**, Tufa **174**, Chen 43 | leaderboard |

Trzy rzeczy, które **wykluczają** 50+ niezależnie od siebie:

1. **Rozkład.** Baza ma μ=25.77, σ=3.93. Żeby trafić 51, trzeba **+6.4 σ**. To nie jest „szczęśliwy
   draw", to jest inna klasa systemu.
2. **Brak zmierzonej dźwigni.** Zespół z 29 submisjami, 4 rundami researchu i ~100 przeczytanymi
   publicznymi notebookami: *„no public or published idea shows a measured gain on top of our agent"*.
   Wszystko, co zmierzyli, było **w szumie albo ujemne** (§3.1).
3. **Budżet.** ~4–5 slotów × 1/dzień, przy szumie ±4 i progu +5 potrzebnym do stwierdzenia czegokolwiek.
   **Nie da się w 4 dni przetestować nawet JEDNEJ nowej hipotezy z ufnością**, nie mówiąc o zbudowaniu
   nowej architektury.

I argument z paper01, który wcześniej traktowałem jako nadzieję — **wszystkie cztery zastrzeżenia są
dyskwalifikujące**: world model + verifier + BFS planner dał **56.81** na tych samych 10 grach r019,
ale (a) **GPT-5.5 przez API** — na Kaggle **internet jest wyłączony**, (b) **1500 akcji na poziom** —
nasz budżet to ~212, (c) **bez limitu 48 min na grę**, (d) **tylko zbiór publiczny**, który
over-predyktuje (0/113 na held-out).

> **Uczciwa odpowiedź na „stworz mega wersje ktora da ponad 50 score": NIE STWORZĘ, bo taka wersja
> nie istnieje w 4 dni na tej bazie.** Obiecanie jej byłoby dokładnie tym rodzajem przeszacowania,
> które w tej sesji prostowałem pięć razy (`+14 do +37 pkt` z searchu, `45+ = miejsca 5–8`,
> kap `1.0724`, kalibracja `×0.718`, kap `+4.93`). Podaję zamiast tego cel osiągalny i ścieżkę.

### 5.1 Cel osiągalny i co on daje

| cel | wartość | prawdopodobieństwo |
|---|---|---|
| **Średnia ~29–30** (D′ + safety, bez capa) | zmierzone na identycznej bazie | **wysokie** |
| **Brąz ≈ 31.04** | jeden dobry draw powyżej średniej | **umiarkowane** |
| **Srebro ≈ 32.33** | draw w górnej części rozkładu (ich najlepsze: 35.35, 31.54, 31.47) | **realne, ~1 na 3–4 drawy** |
| Złoto ≈ 38.2 | draw powyżej najlepszego zaobserwowanego u nich | niskie |
| **Top-5 / 51.04** | +6.4 σ | **praktycznie zero** |

Linie medali z 27.10 przy **4904 zespołach**: złoto ≈ 38.2 (rank ~19), srebro ≈ 32.33 (rank ~228),
brąz ≈ 31.04 (rank ~455). Oni przy 30.01 byli **~rank 733**. Czyli **srebro = awans o ~500 miejsc**
i jest to osiągalne samym usunięciem zera z rozkładu + D′.

---

## 6. Rust + rayon i 64 GB RAM: co to MOŻE, a czego NIE

User ma **5950X 16C/32T + 64 GB RAM** (potwierdzone w `STATUS.md`) i pyta o lokalne środowisko
testowe w Rust. Odpowiedź rozdzielona na to, co da punkty, i to, co nie da.

### 6.1 Czego NIE da — i dlaczego

| pomysł | dlaczego nie |
|---|---|
| **Rust do segmentacji** | `OCENA-RUST-BENCH.md` §5: **1 : 34 142** poniżej wiążącego ograniczenia (0.178 ms vs 6077 ms na wywołanie modelu). Ich własny `MY-WORK-STATUS.md` z 13.10: *„nie jest to wąskie gardło"* |
| **Rust do szybkiego searchu offline po grach** | ❌ **źródła gier nie istnieją w rerunie** — zmierzone **0.20** (§4) i **0/113 na held-out**. Szybsze przeszukiwanie gier, których nie ma, daje zero |
| **Lokalny model na PC do testowania agenta** | GPU **8–16 GB VRAM** → tylko modele 7–8B. Nasza linia to **Qwen3.8-Flash-Next W4A16 na RTX 6000**. Lokalny wynik małym modelem **nie przenosi się** na wynik LB |
| **Rust symulator gier** | ich `MY-WORK-STATUS.md` już to wycofał: *„rust-simulator ❌ — to mock, nie uruchamia prawdziwych gier; warunek wygranej `agent_actions <= baseline * 2`, nie ma logiki gier; RHAE scoring był błędny"* |
| **Więcej równoległości = więcej punktów** | **błąd śmiertelny #13**: zmiany parametrów serwingu kosztują **−7 do −8**. Równoległość jest po stronie serwera, nie nasza |

### 6.2 Co DA — i to jest warte zrobienia na tym PC

Nie punkty bezpośrednio, ale **ochronę slotów**, a sloty są teraz najdroższym zasobem (~4 do końca):

1. **Lokalny weryfikator łańcucha patchy i env** — ich `submission_gate.py` robi dokładnie to:
   `prepare → push → check-smoke → submit`, i **odmawia** submisji, jeśli ten konkretny release
   (ID + hashe plików) nie przeszedł swojego smoke. Plus **47 lokalnych testów CPU**.
   **To jest mechanizm, którego nam brakuje** i który złapałby zarówno `concurrency=120`,
   jak i `SCOPE=run`, jak i nie-obojetny `0005` **przed** spaleniem slotu.
   → **Do zbudowania w Python, nie w Rust.** 16 rdzeni pomaga, bo można równolegle sprawdzać
   wszystkie kombinacje env; 64 GB nie jest tu potrzebne.
2. **Walidatory spójności międzywarstwowej** — reguła z §2.2 i `POROWNANIE-V11.md` §1:
   `assert concurrency <= MAX_ACTIVE_STREAMS`, `assert SCOPE in ("turn","levelup","game")`,
   `assert LEVEL_MIN_DONE > 0 or LEVEL_TOKEN_CAP == 0`. Trzy asercje, które łapią całą klasę
   bugów „konfiguracja przechodzi, ale nie robi tego, co deklaruje".
3. **Analiza logów po fakcie** (`serve.log` 1.14 MB, logi per gra po ~250–340 kB) — tu **16 rdzeni
   i 64 GB realnie pomagają**, i to jest praca, której nie da się zrobić w moim sandboxie
   (2 CPU / 3.9 GB). Konkret: wyciągnąć z `serve.log` prawdziwe tok/akcję dla v11, bo
   `final_generated_tokens` w `benchmark.json` jest **0 dla wszystkich gier** (§7.3).
4. **Nie** budować: nowego symulatora, portu silnika, Rust searcha po grach.

> **64 GB RAM odblokowuje jedną rzecz, którą wcześniej musiałem porzucić:** `re86` potrzebował
> **17.9 GB** frontier (0.190 MB/stan × 94 405 stanów) wobec moich 3.9 GB. Ale **to już nie ma
> wartości punktowej** — §4. Zostaje jako narzędzie badawcze, nie jako droga do wyniku.

---

## 7. Luki w danych, których NIE domknąłem — zaznaczone uczciwie

1. **Nie rozdzieliłem wpływu `0005-plan-commit` od szumu.** Env c45 i v11 jest **bajt-identyczne**
   (te same 10 kluczy i wartości: `ABANDON_MIN_LEVELS=0`, `ABANDON_TOKENS=0`, `EXPERIMENT_HINT=1`,
   `LEVEL_MIN_DONE=0`, `LEVEL_NOTES=1`, `LEVEL_RESETS_MAX=1`, `LEVEL_TOKEN_CAP=45000`,
   `STUCK_AUDIT_TOKENS=60000`, `WORLD_MODEL=0`, `WORLD_MODEL_NUDGE=0`), patche różnią się **o jeden**
   (c45: 0001/0002/**0004**; v11: 0001/0002/0004/**0005**). Ale przy rozstrzale ~14 pkt/grę
   **jedno porównanie smoke tego nie rozstrzyga.** Żeby rozstrzygnąć, trzeba dwóch przebiegów
   tego samego configu — czyli 4 GPU-godzin, których nie mamy.
2. **Nie zweryfikowałem tok/akcję = 828 dla v11.** `final_generated_tokens` i
   `final_uncached_input_tokens` są **0 dla wszystkich 10 gier** w `benchmark.json`. Liczba 828
   pochodzi z `serve.log` (1 143 523 B), którego nie parsowałem. **Oznaczone jako niepotwierdzone.**
3. **`ARC3_WORLD_MODEL=0` jest w obu configach**, więc patch `0002-executable-world-model` jest
   **aplikowany, ale wyłączony**. Nie wiem, czy włączenie go pomaga — ich v5
   („v5-world-model-stuck") dał **23.94**, czyli poniżej 26.25. **Jedno dane, w szumie.**
4. **Nie wiem, czy `WM=0` w v11 to zmiana wobec c45.** Oba logi pokazują `WORLD_MODEL=0`,
   więc **nie** — to nie jest delta. Delta to wyłącznie patch 0005.

---

## 8. PLAN na 4 dni — jedna hipoteza na slot, bez stackowania

Zasada z ich błędu śmiertelnego #8: **nigdy nie stackuj kilku niepunktowanych zmian w jednej
submisji.** Przy ±4 szumu nie wiesz, co zaszkodziło. My w v11 złamaliśmy tę zasadę
(4 zmiany naraz) i dlatego **nie wiemy**, co dało 23.89.

Priorytet jest odwrotny niż intuicja: **najpierw usuwamy zero z rozkładu, potem podnosimy średnią.**

| slot | data | konfiguracja | hipoteza (JEDNA) | oczekiwany efekt |
|---|---|---|---|---|
| **1** | 29.10 | **c45 minus 0005, `LEVEL_TOKEN_CAP=0`** + **4 safety fixes** | „usunięcie capa i dodanie keepalive/retry/gateway-check przywraca bazę i usuwa 0.00" | **~26–29**, i koniec z zerami |
| **2** | 30.10 | **ten sam config, ponownie** | „poprzedni wynik to draw, nie pomiar" | drugi draw tej samej średniej → **ustala μ z dwóch punktów** |
| **3** | 31.10 | **+ D′ slot-priority scheduler** (jedyna zmiana) | „priorytet zamiast równego przydziału daje +2 do +3" | **~29–31** |
| **4** | 1.11 | **najlepszy z 1–3, ponownie** | próbka drugiego drawa lepszego configu | szansa na draw ≥ **32.33** (srebro) |
| **5** | 2.11 | **select best** | Kaggle pozwala wybrać finalne submisje | zabezpieczenie najlepszego drawa |

**Uzasadnienie slotu 1 — dlaczego to jest ta konfiguracja:**

* **`LEVEL_TOKEN_CAP=0`** — mój kap jest zmierzony ujemnie (−0.43 vs r019, `OCENA-CODEX-7Z.md` §3)
  i `ABANDON` przy `min_done=0` wyrzuca gry z budżetem (§2.2). `enabled = cap > 0`, więc zero
  wyłącza cały mechanizm — **ALL-CLEAR sprawdzone w kodzie**, `=0` nie znaczy „zero tokenów".
  *Uwaga: to wyłącza też darmowy `RESET_LEVEL`. Nie da się ich rozdzielić bez zmiany kodu,
  a na zmianę kodu nie ma slotów.*
* **bez patcha 0005** — bo `PLAN_COMMIT=0` i tak nic nie włącza, a patch jest jedyną deltą wobec
  c45. Zewnętrzne potwierdzenie: forge (3. miejsce Milestone 1) — *„the top-scoring run of this
  notebook used a profile that **turns off** all of the extra machinery"* (`arcprize.org/blog/
  arc-prize-2026-milestone-1`). Oraz ich własne v6 **23.94** < v2 **24.66**.
* **4 safety fixes** — jedyna zmiana spoza szumu (§3.2). My mamy w historii 0.00, ERROR, ERROR, 0.01.

**Czego NIE robić w żadnym slocie** (wszystko zmierzone jako neutralne lub ujemne, §3.1):
pamięć rozwiązanych poziomów · no-op guard · strategy-audit · ThinkingCap · jakakolwiek zmiana
parametrów serwingu · dodatkowe rady w promptcie · replay · niższa temperatura.

**Bramka przed każdym slotem** — trzy asercje w notebooku, nie w dokumencie:

```python
# 1. spójność warstw (bug, który dał 0.00)
assert bm.solver.concurrency <= int(os.environ["ARC3_MAX_ACTIVE_STREAMS"]), "frontend > backend"
# 2. walidator env (bug, który byłby martwą dźwignią)
assert os.environ.get("ARC3_PERSISTENT_FUNCTIONS_SCOPE","game") in ("turn","levelup","game")
# 3. mój własny błąd: ABANDON nie może wyrzucać gry, która nic nie zapunktowała
_cap = int(os.environ.get("ARC3_LEVEL_TOKEN_CAP","0"))
_min = int(os.environ.get("ARC3_LEVEL_MIN_DONE","0"))
assert _cap == 0 or _min >= 1, "cap>0 z min_done=0 porzuca gry z 0 poziomów"
```

---

## 9. Co ten dokument zmienia w poprzednich

| dokument | co było | co jest teraz |
|---|---|---|
| `OCENA-CODEX-7Z.md` §3 | kap 45k warty −0.43 (pomiar) | **plus mechanizm**: `ABANDON` przy `min_done=0` wyrzuca gry z budżetem (§2.2) |
| `OCENA-CODEX-7Z.md` §2.3 | v12/0005 jako rozbieżność z moją rekomendacją | **wycofuję przypisanie** spadku smoke patchowi 0005 — to mógł być szum (§2.1) |
| `EKONOMIA-TOKENOW.md` §11 | oczekiwany c45 24–29, ~26.8 | **zmierzone: 23.89** — model był w przedziale, ale **szum jest większy niż cały efekt capa** |
| `PATCH-0004-I-SEARCH.md` | playbook „na realnym LB prawdopodobnie 0" | ❌ **zmierzone 0.20** (ich ref 57272788) + **0/113 na held-out**. Wycofane, nie „prawdopodobnie" |
| `DIAGNOZA-45plus.md` | dźwignia `ABANDON` jako „fleet-only, niezmierzona" | ❌ **zmierzona i ujemna**; właściwa forma to **scheduler priorytetowy** (D′), nie zabicie gry |
| `FAKTY-I-POMIARY.md` | brak modelu szumu | ⚠️ **NAJWIĘKSZA LUKA**: μ=25.77, σ=3.93, próg istotności +5 pkt, wyświetlany wynik = najlepszy draw |
| `README.md` | cel „~50" | ❌ **50+ = +6.4 σ, nieosiągalne**; cel realny **29–30**, srebro **32.33** |
