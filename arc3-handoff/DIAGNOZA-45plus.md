# ARC-AGI-3 — dlaczego nie ma 45+ i co realnie da wygraną

**Autor:** sesja `arena/c87f7a48-pokemon` (audyt zewnętrzny gałęzi `arena/5ed750ef-smak-domu-konkurs`)
**Data:** 2026-10-24, ~14:20 UTC
**Źródła:** wszystko poniżej jest policzone z plików Waszej gałęzi (`r019-kernel-output/output/benchmark.json`, `serve.log`, `duck-v7/arc3-duck.ipynb`, `r033-recon-bundle`, `games/environment_files/*/metadata.json`) albo zmierzone przeze mnie lokalnie na CPU. Nie ma tu szacunków bez źródła — gdzie jest ekstrapolacja, jest to napisane wprost.

---

> ## ⚠ REKALIBRACJA CELU — 24.10 wieczorem, po pobraniu live danych ze strony Kaggle
>
> Tytuł tego dokumentu („dlaczego nie ma 45+”) opierał się na przekonaniu, że **45+ daje nagrodę**.
> **Nie daje.** Zweryfikowane dziś na oficjalnej stronie:
>
> - Nagrody pieniężne są **tylko za top-5** ($75k = 40k/15k/10k/5k/5k). Live leaderboard:
>   1. Tufa **68.91**, 2. Chen **68.21**, 3. Turducken 56.02, 4. mtg 50.37,
>   **5. the last dance 49.85** ← ostatnie płatne miejsce.
> - Czyli **„45+” to dziś miejsca 8–11 = zero pieniędzy**. Cel musi być **~50**.
> - Moja arytmetyka „+1 poziom na grę → 44.8” **jest poprawna, ale niewystarczająca**;
>   „+2 poziomy → 64.5” daje miejsca 2–3. Potrzeba realnie **+1.2 poziomu na grę**.
> - **Daniel Franzen, autor Ducka, ma 38.85 przy 104 submisjach = 15. miejsce, bez nagrody.**
>   Stockowy Duck ma sufit ~39. To jest najmocniejszy argument, że tuning env w Duku
>   nie prowadzi do top-5 — poniżej ta diagnoza dotyczy właśnie tego tuningu.
> - **Deadline to 2 XI (9 dni), nie 26 X (2 dni).** 26 X to *Entry Deadline* + *Team Merger
>   Deadline*; licznik na stronie Kaggle pokazuje dziś „9 days to go”. Entry mamy spełnione
>   (6 punktowanych submisji).
> - Publiczny LB liczy **~50 % danych testowych**, końcowy wynik z drugich 50 % — kolejność
>   może się przestawić.
>
> Szczegóły i źródła: `README.md` (blok „STAN ZWERYFIKOWANY NA ŻYWO”) oraz
> `WERYFIKACJA-INNYCH-GALEZI.md` §7bis.


## 0. TL;DR

1. **Wynik jest wypukłą funkcją GŁĘBOKOŚCI (liczby ukończonych poziomów), nie efektywności.** Na Waszym własnym przebiegu 10 gier: sufit z samej głębokości = 29.0, zmierzone 27.21 → **strata na „nieoptymalnych ruchach" to tylko 1.75 pkt (6%)**. Niemal każdy ukończony poziom już teraz dostaje 115 (cap), bo agent jest szybszy niż baseline.
2. **+1 poziom w każdej grze = średnia 44.8** (policzone na tych samych 10 grach). Całe pytanie „dlaczego nie 45+" sprowadza się do: **jak ukończyć jeden poziom więcej na grę**.
3. **35% wszystkich tokenów i 35% wszystkich akcji idzie w poziom, który nigdy nie zostaje ukończony** (tn36: 86%, ls20: 91%). To jest główny wyciek i on sam wystarczy na ~+1 poziom.
4. **Nie brakuje Wam GPU.** Pula ~175–220k tokenów/grę przy ~841 tokenów/akcję daje ~210–260 akcji, a 4–5 poziomów kosztuje ~200–300 akcji **jeśli nic nie jest marnowane**. Budżet starcza — jest wyrzucany.
5. **Największa niezagrana dźwignia: akcje bez tokenów.** Silnik zwraca `levels_completed` i `available_actions` po każdej akcji, więc deterministyczne wyszukiwanie kosztuje **0 tokenów LLM**. Dowód: rozwiązałem poziom 0 gry `ls20` czystym BFS-em w **13 akcjach** (baseline 22 → poziom warty 115 pkt) w 48 s na 2 rdzeniach sandboxa, **zero wywołań modelu**. Kod: `arc3-handoff/arc3_search.py`.

---

## 1. Jak naprawdę liczony jest wynik

`taaf/game.py:381-413` (`_compute_final_score`, lustrzane wobec `arc_agi.scorecard.EnvironmentScoreCalculator` v0.9.8):

```
poziom k (0-indeksowany), waga = k+1
ukończony i actions>0 : level_score = min(115, (baseline/actions)² · 100)
nieukończony          : level_score = 0
wynik gry = Σ(level_score·waga) / Σ(waga),  capped at  Σ(wagi ukończonych)/Σ(wagi) · 100
wynik LB  = średnia po 110 runach
```

**Sufit z samej głębokości** (nawet przy idealnej efektywności):

| N poziomów | L=1 | L=2 | L=3 | L=4 | L=5 | L=6 | L=7 |
|---|---|---|---|---|---|---|---|
| 6 | 4.8 | 14.3 | 28.6 | **47.6** | 71.4 | 100 | — |
| 7 | 3.6 | 10.7 | 21.4 | **35.7** | **53.6** | 75.0 | 100 |
| 8 | 2.8 | 8.3 | 16.7 | 27.8 | **41.7** | 58.3 | 77.8 |
| 9 | 2.2 | 6.7 | 13.3 | 22.2 | 33.3 | **46.7** | 62.2 |

Policzone na Waszych 10 grach z r019 (każda ma swoje własne N):

| scenariusz | średnia |
|---|---|
| teraz (L zmierzone) | **27.21** |
| sufit przy tym samym L (idealna efektywność) | 29.0 |
| **+1 poziom w każdej grze** | **44.8** |
| +2 poziomy | 64.5 |
| +3 poziomy | 75.8 |

**Wniosek 1:** efektywność ruchów jest już niemal darmowa (29.0 − 27.21 = 1.75 pkt do odzyskania w całej grze). Wszystkie siły w „ukończ jeden poziom więcej".

**Wniosek 2 — SPROSTOWANY 24.10 wieczorem:** liczby 40.97 (próg) i 62.96 (lider) to snapshot z **10–11.10** i są **przedawnione**: lider to dziś **68.91** (Tufa, ich CHAT-LOG 14.10), Chen 67.49. Nagrody są **za MIEJSCA** ($75k/40k/15k/10k/5k/5k), nie za próg punktowy, więc 40.97 nigdy nie było stałą barierą — to było 5. miejsce w tamtym dniu, a cel przesuwa się z tabelą. **Arytmetyka „+1 poziom na grę" pozostaje ważna**, bo jest liczona z ich własnego r019 (27.21 → 44.8), a nie z pozycji w tabeli. **LIVE 24.10: 45+ to miejsca 8–11, a płatne jest dopiero top-5 = 49.85** (Tufa 68.91, Chen 68.21, 5. the last dance 49.85; 8. NVARC3 45.90, 10. Majkel1337 45.03). **Ten wniosek jest więc częściowo nieaktualny — patrz rekalibracja na górze dokumentu i §7bis w `WERYFIKACJA-INNYCH-GALEZI.md`.** Szczegóły: `WERYFIKACJA-INNYCH-GALEZI.md` §7.

---

## 2. Arytmetyka budżetu — dlaczego dziś fizycznie nie starcza

**Ile akcji potrzeba na grę** (suma `baseline_actions` z `metadata.json` wszystkich 25 oficjalnych gier):

- średnio **685 akcji**, mediana 638, min 171 (cd82), max 1843 (wa30)
- średnio **7.3 poziomu** na grę

**Ile akcji możemy kupić** (pomiary, nie szacunki):

| wielkość | wartość | źródło |
|---|---|---|
| przepustowość serwera (dekoding, agregat) | **755 tok/s** (mediana), 792 przy batch 10, max 930 | `r019/output/serve.log`, 1872 linii decode |
| okno gry w prawdziwym zgłoszeniu | 532 min (`bm.solver.max_runtime_s_per_game = 532*60`) | `duck-v7.ipynb` cell 21 |
| gier w scorecardzie | 110 | `taaf/competition_arcade.py:OFFICIAL_110_RUN_COUNT` |
| pula na grę (teoretycznie) | 755 · 31920 / 110 = **219k tokenów** | j.w. |
| sprawność realna (smoke: 217k teorii → 174k pomierzone) | **×0.80** | `r019/output/benchmark.json` |
| pula na grę (realnie) | **~175k tokenów** | j.w. |
| koszt akcji | **841 tokenów/akcję** (2065 akcji, 1.74M tokenów) | `r019/output/benchmark.json` |
| **budżet akcji na grę** | **~208 akcji** (max 260 przy pełnej sprawności) | 175k / 841 |

**208 akcji wobec 685 potrzebnych = 30% budżetu człowieka.** Stąd 3.2 ukończonego poziomu z 7.3 i wynik 27.

Ale uwaga — to nie znaczy, że brakuje 3×. Zmierzone na Waszych własnych przebiegach: gdy agent **rozumie** mechanikę, kończy poziomy w 0.3–0.9× baseline (cn04: 145 akcji na 4 poziomy vs 468 baseline = 0.31×; su15: 139 na 7 poziomów vs 280 = 0.50×). Przy średniej 0.7×:

- 4 poziomy ls20 (baseline 22+123+73+84 = 302) ≈ **211 akcji** ← dokładnie nasz budżet
- 4 poziomy tn36 (32+72+26+40 = 170) ≈ **119 akcji** ← połowa budżetu

**Czyli budżet starcza na 4–5 poziomów, jeśli nie jest marnowany.** Średnia dziś: 3.2. Różnica to wyciek z punktu 3.

---

## 3. Gdzie dokładnie giną punkty (pomiar, `r019/output/benchmark.json`)

10 gier × 48 min, wszystkie `gave_up` (wyczerpany czas, nie przegrana), 0 crashy:

| gra | N | L | akcje | tokeny | tok/akcję | **zmarnowane na poziomie nigdy nie ukończonym** | wynik |
|---|---|---|---|---|---|---|---|
| su15 | 9 | 7 | 157 | 184 664 | 1176 | 18 (11%) | **56.42** |
| cn04 | 6 | 4 | 166 | 182 616 | 1100 | 23 102 (13%) | 47.62 |
| dc22 | 6 | 4 | 304 | 171 666 | 565 | 565 (0%) | 44.77 |
| sc25 | 6 | 4 | 285 | 166 390 | 584 | 53 712 (32%) | 42.62 |
| m0r0 | 6 | 3 | 215 | 170 262 | 792 | 15 838 (9%) | 28.57 |
| ka59 | 7 | 3 | 259 | 168 852 | 652 | 76 929 (46%) | 17.85 |
| s5i5 | 8 | 3 | 116 | 184 608 | 1591 | 28 646 (16%) | 16.67 |
| g50t | 7 | 2 | 168 | 168 970 | 1006 | 83 479 (49%) | 10.71 |
| tn36 | 7 | 1 | 145 | 173 865 | 1199 | **148 685 (86%)** | 3.57 |
| ls20 | 7 | 1 | 250 | 165 362 | 661 | **150 149 (91%)** | 3.27 |
| **razem** | | **3.2 śr.** | **2065** | **1.74M** | **841** | **0.60M = 35%** | **27.21** |

Trzy fakty, które z tego wynikają:

1. **su15 (56.4) i tn36 (3.6) wydały tyle samo tokenów i tyle samo akcji.** Różnica nie jest w budżecie — jest w tym, że su15 trafił z mechaniką na każdym poziomie, a tn36 wywalił 124 akcje (86% budżetu) w poziom 1, którego nigdy nie skończył.
2. **35% puli = 0.60M tokenów = ~72 akcje na grę w czarnej dziurze.** Przy koszcie ~35k tokenów za ukończony poziom (1.14M/32 poziomy), odzyskanie tego to **~1.7 poziomu na grę**.
3. Każda gra leci na pełnym czasie → ogranicza nas czas/tokeny, nie „brak pomysłów" i nie pętle (pętle: 0 przypadków w Waszej własnej klasyfikacji 110 przebiegów).

---

## 4. Serwer: twarde liczby z `serve.log` (po co ten rozdział: żeby nie szukać tu głównej dźwigni)

Start (2026-10-13 11:05–11:13):

```
wagi        : Qwen4ExpForConditionalGeneration, auto-round bits=4 → 69.85 GB
draft (MTP) : 3.79 GB
mamba cache : 60 slotów, conv 0.13 GB + ssm 3.22 GB
KV cache    : fp8_e4m3, 1 011 264 tokeny, K 5.79 GB + V 5.79 GB
wolne na koniec: 4.25 GB      max_running_requests=10   context_len=139264
```

Decode (1872 próbek):

| #running-req | median tok/s | tok/s/strumień | ms/krok |
|---|---|---|---|
| 1 | 179 | 179.0 | 16 |
| 5 | 496 | 99.2 | 27 |
| 7 | 673 | 96.1 | 28 |
| 9 | 753 | 83.6 | 32 |
| 10 | 792 | 79.2 | 33 |

- `full token usage`: mediana **0.71**, max **0.99** → pula KV (1.01M tokenów) jest limitem dla 10 strumieni (~80k tokenów kontekstu na strumień). Wasze ustalenie „wąskim gardłem jest pamięć KV" — **potwierdzone pomiarem**.
- `mamba usage`: mediana 0.60 (36/60 slotów) → nie jest limitem, jest zapas na ~16 strumieni.
- `accept len` 2.65 z 4, `accept rate` 0.55 → spekulacja działa, ale nie jest darmowa.
- prefix cache: **61.7M tokenów z cache vs 4.54M nowych = 93.2% trafień** → prefill nie jest problemem, walutą są **tokeny generowane**.

**Ekstrapolacja (nie pomiar!):** ms/krok rośnie 27→33 przy batch 5→10, więc dalsze podnoszenie `MAXREQ` daje mniej niż liniowo: batch 20 ≈ 1150 tok/s (+45%), batch 30 ≈ 1370 tok/s (+73%). Warunek: mniejsze okno kontekstu (`LOCAL_ANALYZER_CONTEXT_WINDOW` 128k→~52k, `ARC3_CONTEXT_DRAIN_TOKENS` 58k→~24k), żeby 20 strumieni zmieściło się w 1.01M tokenów KV, plus `MAMBA_CACHE` 60→~80 (0.7 GB, wolne są 4.25 GB) i `CUDAGRAPH_MAXBS ≥ MAXREQ` (jest assert w launcherze).

**Zysk: +45% puli = 208 → ~300 akcji na grę. Warto, ale to dźwignia numer 3, nie numer 1** — bo wymaga krótszej pamięci agenta (ryzyko −pkt) i jednego pełnego smoke'a (2.5 h GPU) na zweryfikowanie.

---

## 5. ⚠️ Krzywa „200k→41.8, 300k→45.7" nie zgadza się z Waszym własnym pomiarem

W `FINDINGS-2026-10-13.md` (15.10) jest krzywa duck: 100k→24.7, ~175k→27.2, 200k→41.8, 300k→45.7, i na niej oparto plan v7 (expected 31–34).

Sprzeczność z twardymi danymi:
- smoke v6: **175–188k tokenów/grę → 27.21** ✓ (zgadza się z krzywą)
- LB duck v3: smoke 29.02 → **LB 26.25** ✓
- ale prawdziwe zgłoszenie ma **~219k teorii / ~175k realnie na grę** (punkt 2) — czyli **nigdy nie schodzi z rejonu 175–220k**, a krzywa obiecuje tam 41.8.
- Nasz pomiar przy 175–188k daje 27. **Punkt 200k→41.8 musi pochodzić z przebiegu o innej liczbie gier równoległych (mniej gier = więcej tokenów każda) i nie przenosi się na run 110 gier.**

**Rekomendacja: nie planować na tej krzywej.** Ona jest przyczyną, dla której od 9 dni goniony jest „budżet tokenów", a dane z r019 mówią, że problem leży w rozdziale budżetu (35% w czarnej dziurze), nie w jego wielkości.

---

## 6. Główna dźwignia: akcje, które nie kosztują tokenów

### 6.1 Dlaczego to w ogóle możliwe

`arcengine.perform_action()` zwraca `FrameData` z polami (sprawdzone lokalnie):

```
game_id, frame (1,64,64), state, levels_completed, win_levels, action_input, available_actions
```

Czyli **sygnał sukcesu (`levels_completed`), legalne akcje (`available_actions`) i pełna plansza są dostępne bez żadnego wywołania LLM**. Wyszukiwanie po drzewie akcji kosztuje tylko CPU.

Ważne ograniczenie: sandbox `python` udostępniany modelowi (`inference/agent/python_tool_sandbox.py`) daje wyłącznie `current_frame` (`.ascii/.step/.level/.shape/.segmentation`) i `history` — **model nie może sam stepować silnika**. Więc search musi siedzieć w harnessie (patch), nie w promptcie. To jest dokładnie to, czego nie macie, a co widać w technikach czołówki: `arc-prize-2026-sovereign-agent.ipynb` i `cprs-...-v22/v23` mają w opisie **bfs, beam, replay, cache, precompute, offline**.

### 6.2 Pomiar (mój, dzisiaj, CPU sandboxa, 2 rdzenie — odtworzony dwukrotnie)

```
gra=ls20  win_levels=7  dostępne_akcje=[1,2,3,4]  plansza=(64,64)
BFS z deduplikacją stanów (blake2b z ramki + levels_completed), snapshoty deepcopy:
  *** POZIOM UKOŃCZONY: 13 akcji, 1777 węzłów, 57.2 s
  odrębnych stanów: 538     31 węzłów/s     0 tokenów LLM
  sekwencja: ACTION3 ×3, ACTION1 ×4, ACTION4 ×3, ACTION1 ×3
```

- baseline poziomu 0 ls20 = **22 akcje** → 13 akcji daje `min(115,(22/13)²·100)` = **115 (cap)**.
- koszt w tokenach LLM: **0**. Koszt CPU: 57 s na 2 rdzeniach, naiwnym BFS-em.
- **Przestrzeń stanów jest mała**: 538 odrębnych stanów na głębokości 12 → deduplikacja tnie drzewo skutecznie, więc A* z heurystyką (segmentacja → odległość do obiektów docelowych) powinien znaleźć to w ~100–300 węzłach.
- kod: `arc3-handoff/arc3_search.py` — działa, ma tryb `bfs` i `beam`, sam generuje kandydatów kliknięć dla gier `click`.

**Wąskie gardło i droga przyspieszenia** (pomiar): `deepcopy` stanu = 16.9 ms, `perform_action` = 4.36 ms → ~21 ms/węzeł (mierzone 32 ms z hashowaniem). Zamiast deepcopy: `level_reset()` kosztuje **1.82 ms** + odtworzenie sekwencji od początku poziomu, albo iteracyjne pogłębianie DFS na jednej instancji. Do tego `multiprocessing` po 16 rdzeniach 5950X. Realny cel: **300–1000 węzłów/s**, czyli poziom w kilka sekund.

**Pułapka implementacyjna (znaleziona):** `FrameData.frame` nie zawsze ma kształt `(1,64,64)` — przy animacjach silnik zwraca kilka klatek, np. `(6,64,64)`. Trzeba brać **ostatnią** ramkę (`while a.ndim>2: a=a[-1]`), inaczej hash stanu się rozsypuje. To jest dokładnie ten rodzaj cichego błędu, który u Was zabił parser 14.10 — warto mieć na to test.

Koszty silnika zmierzone lokalnie:

| operacja | czas |
|---|---|
| `perform_action` | 4.36 ms |
| `copy.deepcopy(game)` (przywracanie stanu) | 16.9 ms |
| `level_reset()` | 1.82 ms |
| instantiate + RESET | 17.2 ms |

Mój BFS jest naiwny (odtwarza całą sekwencję od zera dla każdego węzła, O(głębokość²)) → 37 węzłów/s. Z `deepcopy` jako snapshotem i A* z heurystyką (segmentacja → odległość do obiektów docelowych) realne jest **100–1000 węzłów/s**, a na Waszym 5950X (16 rdzeni, `multiprocessing`) ~10–16× więcej. Budżet: 110 gier × 3 poziomy × 10 s = 55 min CPU rozłożone na 9 h runa, **zero GPU**.

### 6.3 Gry „click" — uczciwie o ograniczeniu

`tn36` (tag `click`): `available_actions = [6]`, czyli wyłącznie MOUSE z `data={'x','y'}` (0..63) → przestrzeń 4096 kliknięć. Czysty BFS odpada. Rozwiązanie: kandydaci z segmentacji (harness już ma `inference/utils/segmentation.py`: `nodes` z `id/color/hash/pixels/boundary/children` — to gotowa lista ~10–40 sensownych punktów na ramkę) + beam search z heurystyką nowości. Wasz port Rust segmentacji (`rust/src/grid.rs`, ~121× na realistycznej klatce) jest dokładnie tym, czego tu trzeba i **nigdy nie został do niczego podpięty**.

Rozkład 25 gier: 4× `keyboard` (czysty BFS działa od ręki), 13× `keyboard_click`, 7× `click`, 1 bez tagu. Czyli ~40% zestawu to gry, w których search jest prosty, a reszta wymaga kandydatów z segmentacji.

### 6.4 Co to daje punktowo

Search bankuje tanie poziomy **za darmo**: 1–2 poziomy na grę × 110 gier. Z tabeli z punktu 1: +1 poziom = 27.2 → **44.8**. Dodatkowo search zwalnia tokeny na poziomy, gdzie potrzebny jest wgląd modelu (czyli dokładnie to, czego nie umie zrobić).

Wariant minimalny (najtańszy, bez szukania rozwiązania): **search jako zwiadowca** — harness robi 30–80 tanich akcji na początku poziomu i podaje modelowi gotową tabelę „akcja → co się zmieniło w segmentacji" (które obiekty reagują, które są HUD-em). To adresuje Waszą własną diagnozę klasy (a) „nowa mechanika niezrozumiana: 6/10" i kosztuje ~0 tokenów, a oszczędza 4 wywołania LLM na poziom (Wasz szacunek z v6.1: 150–250k tokenów na 10 poziomów).

---

## 7. Bug w `v7-abandon`: zabezpiecza dokładnie te gry, które najbardziej przeciekają

`patches/0003-early-abandon.patch`, `arc3_abandon.should_abandon()`:

```python
def should_abandon(generated_tokens: int, levels_completed: int) -> bool:
    cap = abandon_budget()
    if cap <= 0: return False
    if levels_completed > min_levels(): return False   # min_levels default 0
    return int(generated_tokens) >= cap
```

Przy `ARC3_ABANDON_MIN_LEVELS=0` warunek `levels_completed > 0` **nigdy nie porzuca gry, która ukończyła choć jeden poziom**. A z pomiaru (punkt 3) najwięksi wyciekający to:

- tn36: **L=1**, 86% tokenów w poziomie 1
- ls20: **L=1**, 91% tokenów w poziomie 1
- g50t: L=2, 49%
- ka59: L=3, 46%

Czyli v7 łapie tylko gry z L=0 — w smoke'u r019 **nie było ani jednej takiej gry**. v7-abandon w tej postaci nie zmienia nic. (To może wyjaśniać, dlaczego expected 31–34 nigdy się nie potwierdziło — poza tym, że nigdy nie zostało zmierzone.)

**Fix (2 linie logiki, testowalne offline jednostkami, tak jak reszta patcha):** próg na **tempo marginalne**, nie na stan bezwzględny:

```python
# zamiast levels_completed > min_levels()
tokens_since_last_level = generated_tokens - tokens_at_last_level_completion
if tokens_since_last_level < cap: return False          # postęp był niedawno -> gramy dalej
if levels_completed >= min_levels_total: return False   # i tak już dużo -> nie porzucamy
return True                                             # brak postępu od cap tokenów -> oddaj slot
```

plus **cap per poziom** (nie per gra): po `ARC3_LEVEL_TOKEN_CAP` (np. 40k) bez ukończenia poziomu → `level_reset()` + eskalacja klasy hipotezy w audycie, a dopiero po drugim takim capie → obniż priorytet gry w schedulerze (nie twardy abandon — twardy abandon trwale zeruje grę, a `RESET` daje drugą szansę).

Uwaga na prawdziwym runie: przy 110 grach i 10 slotach (`ARC3_MAX_ACTIVE_STREAMS=10`) oddanie slotu **realnie przenosi przepustowość** na inną grę — to jedyny mechanizm, który w ogóle może dać „więcej tokenów na grę" bez dotykania serwera.

---

## 8. Pamięć między replikami — mnożnik, który jest wyłączony

- Scorecard ma **110 runów**. Tufa symuluje to jako `official_110()` = **cykliczne klony 25 oficjalnych gier** (`taaf/competition_arcade.py:56-77`, `clone_prefix='k'`, `i % len(source_ids)`). Publiczny notebook `arc3-arena-hero-v2-runb` opisuje walidację jako „110 independent cyclic replicas of the 20 public games", a prawdziwy roster jako „hidden gateway roster" do odkrycia.
- **Konsekwencja:** ta sama mechanika trafia się w runie ~4–5 razy. Rozwiązanie jej raz powinno płacić 4–5 razy.
- Tymczasem w Waszym configu (`duck-v7.ipynb` cell 9): `ARC3_PERSISTENT_FUNCTIONS_SCOPE = 'game'` i `ARC3_MEMORY_SECTIONS = 'off'`.

**Lever:** ~~`scope='run'`~~ — **MARTWE, patrz korekta niżej** — plus `lessons-between-games` (macie to zaimplementowane i przetestowane w `llm-agent/llm_policy.py` v6.2, 43/43 testy — **nigdy nie przeniesione do linii duck**, która jako jedyna produkuje wyniki). **Ta połowa dźwigni zostaje żywa**; połowa `scope` nie.

> ### ❌ KOREKTA — POŁOWA `scope` TEJ DŹWIGNI NIE ISTNIEJE (27.10, mój własny błąd)
>
> Napisałem wyżej „`scope='run'` (patch już czyta tę zmienną z env)". Patch **czyta** zmienną,
> ale ją **waliduje**. `patches/0000-franzen-harness-changes.patch` L3559-3560:
>
> ```python
> scope = os.environ.get("ARC3_PERSISTENT_FUNCTIONS_SCOPE", "").strip().lower()
> return scope if scope in ("turn", "levelup", "game") else "levelup"
> ```
>
> Dozwolone są **wyłącznie `turn | levelup | game`**, domyślne `levelup`. **`run` nie istnieje.**
>
> Najgorsze jest to, że degradacja jest **cicha**: nieznana wartość nie rzuca błędu, tylko wraca
> do `levelup`. Ustawienie `SCOPE=run` wyglądałoby w logu jak włączona zmiana, a harness
> zachowałby się **jak przy wartości domyślnej**. Slot spalony, a wniosek „dźwignia
> lessons-between-games nie działa" byłby **fałszywy** — bo testowano by ją w parze z martwą
> zmienną. To dokładnie ta sama klasa pułapki co `concurrency=120` (patrz `POROWNANIE-V11.md` §1):
> **konfiguracja, która przechodzi walidację składni, ale nie robi tego, co deklaruje**.
>
> Wniosek dla eksperymentu: `lessons-between-games` trzeba testować przy **`scope='game'`**
> (najszersza dozwolona wartość, i taka już jest w ich cell 9), nigdy przy `run`.
>
> Reguła, którą stąd wyciągam: **przed zaproponowaniem wartości zmiennej env należy wyciągnąć
> jej walidator z patcha.** Nazwa `SCOPE` sugeruje „cały run"; kod mówi co innego. Transkrypcja
> nazwy zmiennej do dokumentu to nie jest jej zrozumienie — ta sama lekcja co przy `MAXREQ`.

⚠️ Uczciwie: nie wiemy, czy prywatny roster to te same gry (jest „hidden"). Ale (a) walidacja publiczna jest cykliczna, (b) gry są tagowane `official` i pochodzą z `re-arc-3` train+eval, (c) koszt zmiany to jedna zmienna env z kill-switchem. Warto sprawdzić w jednym smoke'u, czy w runie powtarzają się sygnatury plansz (hash segmentacji pierwszej ramki) — to da się zlogować w 5 liniach patcha i rozstrzygnąć pytanie przy okazji następnego przebiegu.

---

> ### ⚠ KOREKTA RANKINGU DŹWIGNI — 24.10 późny wieczór (po recenzji zewnętrznej DeepSeek 4.1)
>
> Recenzja słusznie wyłapała, że **wiersz 1 obiecywał liczby, których mechanizm nie dowiezie**.
> Poziomy w grze są **sekwencyjne**, a stan `ABANDON` w moim kodzie oznacza **„stop the game”**
> (`arc3_level_budget.py:31`). Ucięcie budżetu na poziomie 3 **nie przenosi go na poziom 4** —
> kończy grę. Więc cap nie „odzyskuje 0.5–1.7 poziomu w tej samej grze”. Wycofuję tamten szacunek
> **(+7 do +17 pkt)** jako niepoparty mechanizmem.
>
> Co z tego zostaje, uczciwie:
> - **`ABANDON` = efekt flotowy, nie per-gra.** Uwalnia slot SGLang (`MAXREQ=10`) grze, która jeszcze
>   robi postęp. Realny, ale **niezmierzony** — i to jest poprawna krytyka: zmierzyć, nie zakładać.
> - **`RESET_LEVEL` = jedyny per-gra kandydat na +poziom.** Jest darmowy (0 tokenów LLM) i przy
>   `ONLY_RESET_LEVELS=true` **zachowuje poziom**, więc model planuje od czystej klatki zamiast mielć
>   hipotezę, która nie działała od 45k tokenów. To jest ten sam mechanizm, który recenzja niezależnie
>   wskazała jako „kompakcję kontekstu" (841 tok/akcję i 35% wycieku to ta sama choroba). **Też
>   niezmierzony** — ale to inna dźwignia niż ta, którą recenzja skrytykowała, i jej nie opisano.
> - **Wiersz 2 też był przeszacowany**: obiecywał „+14 do +37 pkt", a zmierzony wynik playbooka to
>   **3.18 pkt**. Poprawione w tabeli poniżej.
>
> ### 🎯 Triage budżetowy: gdzie głębokość jest FIZYCZNIE możliwa (nowe, policzone 24.10)
>
> Recenzja zaproponowała „szukać głębokości tam, gdzie budżet 208 akcji wystarcza (cn04, su15),
> a nie w ogonie (ls20, tn36)". **Sprawdziłem to na własnych metadanych i wskazane gry są błędne.**
> `sum_baseline` (akcje człowieka na ukończenie WSZYSTKICH poziomów) wobec budżetu ~208 akcji
> (175k tokenów / 841 tok na akcję):
>
> | gra | sum_baseline | ×budżet | werdykt |
> |---|---|---|---|
> | **cd82** | 171 | **0.82×** | ✓ wystarcza na wszystkie 6 poziomów — **już w playbooku (4.76)** |
> | **ft09** | 208 | **1.00×** | ✓ wystarcza na wszystkie 6 — **już w playbooku (4.76)** |
> | sb26 | 213 | 1.02× | ~ na styk (8 poziomów) |
> | r11l | 233 | 1.12× | ~ blisko (6 poziomów) |
> | tn36 | 317 | 1.52× | ✗ (recenzja wskazała jako „ogon" — i tak lepsze niż cn04) |
> | **su15** | 361 | **1.74×** | ✗ **wskazana przez recenzję jako wykonalna — nie jest** |
> | vc33 | 447 | 2.15× | ✗ (a mam w playbooku 10.71) |
> | tu93 | 462 | 2.22× | ✗ (a mam w playbooku 33.33 — najwięcej) |
> | **ls20** | 776 | 3.73× | ✗ |
> | **cn04** | 789 | **3.79×** | ✗ **wskazana przez recenzję jako wykonalna — jest jedną z NAJGORSZYCH** |
> | sk48 | 1070 | 5.14× | ✗ |
> | dc22 | 1228 | 5.90× | ✗ |
> | re86 | 1255 | 6.03× | ✗ |
> | lf52 | 1339 | 6.44× | ✗ |
> | wa30 | 1843 | 8.86× | ✗ |
>
> **Wniosek, który zmienia targetowanie:** tylko **2 z 25 gier** (cd82, ft09) mają budżet
> wystarczający na ukończenie wszystkich poziomów — i **obie już rozwiązałem**. Dwie kolejne
> (sb26 1.02×, r11l 1.12×) są na styk i to są **najlepsze niezmierzone cele**. Cała reszta
> wymaga albo więcej tokenów na akcję (dźwignia 5), albo większej puli (dźwignia 3) — nie
> „skupienia głębokości", bo głębokości tam fizycznie nie ma za co kupić.
>
> **To też tłumaczy, dlaczego „+1 poziom w każdej grze" (44.8) jest sufitem, nie planem:**
> przy 21 z 25 gier poza budżetem, +1 poziom trzeba brać z gier o niskim `sum_baseline`,
> a nie równomiernie ze wszystkich.


## 9. Ranking dźwigni

| # | dźwignia | oczekiwany zysk | koszt | ryzyko | dowód |
|---|---|---|---|---|---|
| 1 | **cap per poziom: RESET_LEVEL** (darmowy reset poziomu, 0 tokenów LLM) | **NIEZMIERZONE** — kandydat na +poziom w tej samej grze, bo reset przy `ONLY_RESET_LEVELS=true` **zachowuje poziom** i pozwala modelowi planować od czystej klatki zamiast mielć hipotezę, która właśnie nie działała od 45k tokenów | ~30 linii patcha, 16 testów offline, **0 GPU na napisanie** | niskie (kill-switch env) | `arc3_level_budget.py:25-34`; założenie o re-planningu **nie było testowane na harnessie** |
| 2 | **token-free search / playbook offline** (punkt 6) | **ZMIERZONE: 3.18 pkt — W SYMULATORZE LOKALNYM, nie na LB** (11 z 25 gier, 16 poziomów, każda sekwencja zweryfikowana replayem). To jest **podłoga**, nie +14–37 pkt — tamten szacunek wycofuję. **Na realnym LB prawdopodobnie 0**: gry ewaluacyjne są nieznane i bez powtórzonych ID, więc dosłowne sekwencje nie odpalą — patrz `PATCH-0004-I-SEARCH.md`. Wartość, która PRZENOSI się na LB, to `arc3_search.py` jako search **runtime** | 1–3 dni CPU-lokalnie, **0 GPU, 0 slotów** | zerowe (wynik już zweryfikowany) | `results/playbook.json`, `results/game_metadata.json` |
| 3 | `MAXREQ` 10→16–20 + mniejsze okno kontekstu + `MAMBA_CACHE`↑ | **+45% puli** → ~300 akcji/grę | 1 smoke (2.5 h GPU) | średnie (krótsza pamięć agenta) | serve.log: full token usage 0.71/0.99, ms/krok 27→33 |
| 4 | ~~`PERSISTENT_FUNCTIONS_SCOPE=run`~~ **MARTWE** (walidator dopuszcza tylko `turn\|levelup\|game`, patrz korekta w §5) + **lessons-between-games** (ta połowa żywa, przy `scope='game'`) | ×4–5 na raz rozwiązanej mechanice (jeśli roster cykliczny) | ~~1 zmienna env~~ + port z llm-agent | niskie | `competition_arcade.official_110()` |
| 5 | cięcie tok/akcję (841 → ~600): `MAX_OUTPUT` 12k→4k, `MEMORY_SECTIONS=slim`, mniej Pythona eksploracyjnego po stronie modelu (bo search robi to za darmo) | +40% akcji | 1 smoke | **wysokie** — Wasza historia: v6 „dokładaliśmy koszt-decyzję na stałej puli → LB spadł" (23.94 vs 24.66) | FINDINGS 15.10 |

**Kolejność: 1 → 2 → 4 → 3 → 5.** Punkt 1 i 2 nie zużywają ani jednego slotu zgłoszenia ani godziny GPU na etap developmentu — a to jest dzisiaj Wasze prawdziwe ograniczenie (quota 30 h/tydz., 1 zgłoszenie/dzień).

---

## 10. Stan operacyjny na 24.10 ~14:20 UTC (co blokuje cokolwiek)

| rzecz | stan |
|---|---|
| najlepsze LB | **26.25** (duck v3, 16.10); wcześniej 24.66 (v2), 23.94 (v5), 0.01 (atrapa) |
| ostatnie zgłoszenie | 16.10 → **sloty 17–23.10 przepadły** (7 dni bez pomiaru) |
| run Actions w tej chwili | `ARC3 ops` **pending od 14:02 UTC** (commit `ad8b804`: V8 push → smoke ~2.5 h → auto-submit `-v 8` ~17:30 UTC) |
| v7 | padł po ~25 min; root cause wg `4abe48a`: setup Tufy asertuje `KAGGLE_GPU_TYPE=rtx-pro-6000` → crash na default env |
| API submit | `400 Bad Request` na `CreateCodeSubmission` przy `-v 5` i `-v 7` (r058/r060) → potrzebny klik „Submit to Competition" w UI |
| GPU quota | „Maximum weekly GPU quota of 30.00 hours reached" (16.10, `s202`) |
| deadline'y | entry **26 X** (zaakceptowane ✅, 6 zmierzonych zgłoszeń), **finałowa submisja 2 XI**, wyniki 4 XII |

**Zostało ~9 dni = ~8 slotów zgłoszeń** (1/dzień) i ~1 reset kwoty GPU. To jest budżet, którym trzeba rozporządzić — dlatego punkt 9 jest ułożony tak, żeby 1 i 2 nie potrzebowały ani slotu, ani GPU na development.

**Uwaga procesowa:** nie pchajcie dwóch torów naraz (Wasza własna lekcja z `EXECUTE-TODAY-2026-10-15.md`) i nie pushujcie `request.json`, dopóki run z 14:02 nie skończy — `concurrency: arc3-ops, cancel-in-progress: false`, ale Wasza lekcja z r057 mówi, że „kolejne pushy anuluja pending runy".

---

## 11. Plan na 9 dni (konkretnie)

**Dziś (24.10), bez GPU:**
1. Niech run V8 dojedzie (14:02 → ~17:30). Jeśli API znowu da 400 → klik w UI. To jest slot dzisiejszy.
2. ~~Równolegle, **offline**: napisać patch `0004-level-token-cap` (punkt 7) + testy jednostkowe na czystej logicy.~~
   **WYKONANE 24.10**: `patches/0004-standalone-level-token-cap.patch` + `arc3_level_budget.py`
   + 16 testów (16/16 OK, 2 skipped). Łańcuch zweryfikowany `git apply` na prawdziwym drzewie,
   a wpięcie do ich notebooka zautomatyzowane (`tools/make_notebook_patch.py`,
   dowód: `results/verification_notebook.txt`). Zero GPU, zero slotów — jak planowano.
3. Zalogować w patchu sygnatury pierwszej ramki (hash segmentacji) per run → przy następnym przebiegu rozstrzygnie się pytanie o cykliczność rosteru (punkt 8).

**25–27.10, lokalnie na CPU (Wasz 5950X, 16 rdzeni, zero kwoty Kaggle):**
4. ~~Rozwinąć `arc3_search.py`: `deepcopy`-snapshoty + A* z heurystyką z segmentacji + `multiprocessing`. Cel: ≥1 poziom w ≥8 z 25 gier bez tokena LLM.~~
   **WYKONANE i PRZEKROCZONE 24.10**: **11/25 gier, 16 poziomów, 3.18 pkt (symulator lokalny, nie LB)**, wszystko
   replay-verified. Ale dwie części tego planu okazały się błędne i warto to wiedzieć:
   * **„heurystyka z segmentacji" była ślepa** — to segmentacja blobów blokowała ft09 (28
     martwych ruchów, frontier wysechł po 56 węzłach). Zastąpienie jej **kalibracją po
     EFEKCIE** (hash ramki po kliku) dało +3 gry od razu: ar25, cn04, ft09.
   * **„dla gier `click` kandydaci z segmentacji" nie działa** — patrz FAKTY §1bis(e):
     `signal_quality` NIE przewiduje rozwiązywalności (cursor_only 3 rozwiązane/7 nie,
     ok 5/6). vc33 ma medianę zmiany **1 px** (czyli „sam szum") a dała 2 poziomy = 10.71 pkt;
     sb26 ma `ok` i rozgałęzienie 5 a jest czarna. **Nie triage'ować gier po tych polach.**
   * A* się nie przydał: nie ma admissable heurystyki z publicznego API (brak sygnału postępu
     wewnątrz poziomu), więc został BFS + beam. Predyktorem jest długość minimalnego
     rozwiązania, której z góry nie znamy.
5. Z tego zrobić dwie rzeczy: (a) **playbook** (statyczny asset w notebooku: per gra/per sygnatura ramki → sekwencja lub heurystyka), (b) **runtime search** w harnessie jako fallback przed eskalacją do LLM.

**28–30.10 (po resecie kwoty GPU):**
6. Jeden smoke: v8-mózg + `0004-level-token-cap` (dźwignia 1). Bramka: jeśli średnia ≥ 29.0 (sufit obecnej głębokości) i `wasted_tokens%` spadł z 35% do <20% → zgłoszenie.
7. Jeden smoke: to samo + search (dźwignia 2) na grach `keyboard`. Bramka: `levels_completed` +1 średnio.

**31.10–1.11:**
8. Zgłosić zwycięzcę; drugi slot na wariant z `MAXREQ=16` (dźwignia 3), jeśli 6/7 dały mniej niż 34.
9. **1 XI: zostawić jeden slot zapasowy** — nie zgłaszać niczego, co nie ma dymu z `ARC3_SMOKE_OK`.

---

## 12. Czego NIE robić (na podstawie Waszych własnych danych)

- **Nie planować na krzywej „200k→41.8 / 300k→45.7"** — sprzeczna z pomiarem (punkt 5).
- **Nie dokładać kosztu decyzyjnego** (world model, nudge, dłuższe audyty) na stałej puli: v4 23.11, v5 27.21, v6 23.94 wobec baseline 29.48 i v2 24.66. Linia world-model zamknięta danymi (283/813 przejść).
- **Nie sumować sufitów** („+7+3−4+1…"): Wasz własny werdykt z `COMPARISON-V7_0` mówi, że to arytmetyka addytywna na nakładających się mechanizmach.
- **Nie inwestować w ML/value-gate bez danych** (`load_mlp_weights` → „random initialization", split 80/20 po wierszach = wyciek; w Pokemonie ta sama klasa błędu obaliła „acc 0.913").
- **Nie ruszać efektywności ruchów** — jest warta 1.75 pkt z 27.21 (punkt 1).
- **Nie pushować `request.json`, dopóki wisi run** (r057: push anuluje pending).

---

## Załącznik: pliki

- `arc3-handoff/arc3_search.py` — działający prototyp BFS/beam bez tokenów LLM (uruchomiony: ls20 L0 w 13 akcjach). Wymaga `pip install --no-deps --ignore-requires-python arcengine numpy` (Python 3.11 działa mimo wymogu 3.12) i pliku gry z `arc-agi-3/games/environment_files/<g>/<g>/<g>.py`.
- `arc3-handoff/DIAGNOZA-45plus.md` — ten plik.

**Do przeniesienia do Waszej gałęzi:** punkty 1–3 (arytmetyka wyniku i wycieku) powinny trafić do `FINDINGS`/`STATUS`, bo zmieniają cel: nie „więcej tokenów na grę", tylko **„+1 poziom na grę"**. Punkt 7 (bug v7-abandon) jest do naprawienia od ręki. Punkt 6 to jedyna dźwignia, która nie konsumuje ani GPU, ani slotu.

---

## AKTUALIZACJA 24.10.2026 ~16:30 UTC

Ciąg dalszy w **`PATCH-0004-I-SEARCH.md`** (ten sam katalog). Trzy rzeczy zmieniają obraz
z tej diagnozy:

1. **Linia `duck-v7` nie może wystartować.** Ich patch 0003 (`duck-extra-02.patch`) był
   wygenerowany względem oryginalnego `solver.py` (nagłówek `index 0b69d62..`), a cell 9
   nakłada go **po** patchu Franzena z `check=True` → `patch does not apply` →
   `CalledProcessError` → notebook umiera przed załadowaniem wag. Zweryfikowane przez
   `git apply` na prawdziwym drzewie 42 plików z bundle r033. Kolejki, która wisi teraz (r065 →
   kernel `arc3-duck-original`), to **nie** dotyczy — tam nie ma żadnych patchy.
2. **`v7-abandon` jest no-opem z dwóch niezależnych powodów** (zły licznik tokenów:
   `token_baseline` to kursor per krok, nie per gra; oraz guard `levels_completed > 0`
   chroniący dokładnie gry, które marnują najwięcej). Oczekiwane 31–34 pkt z FINDINGS 15.10
   nie ma podstaw — to punkt 6 tej diagnozy, potwierdzony testami.
3. **Lever #2 (search) działa, ale jest wart 3.18 pkt, nie +14..37.** Zmierzone na trzech
   przebiegach (płytki 3 000 węzłów/grę, głęboki 12 000, i v2 z kalibracją ruchów po
   efekcie): scalony wynik **11/25 gier, 16 poziomów, wszystko zweryfikowane replayem na
   świeżej instancji = 3.18 pkt podłogi W SYMULATORZE LOKALNYM** (na realnym LB prawdopodobnie 0).
   Powód rozjazdu z szacunkiem: jeden poziom w 7-poziomowej grze jest wart ~3.5 pkt, bo
   mianownik to ΣW **wszystkich** poziomów — wartość robi dopiero głębokość (tu93: 5 poziomów
   = 33.33 pkt w jednej grze, vc33: 2 poziomy = 10.71).
   **Poprawka do mojej własnej tezy:** głębszy przebieg DOŁOŻYŁ +3 poziomy i +2 gry
   (tu93 4→5, vc33 1→2, sp80 0→1), więc „4× większy budżet nie pomaga" było błędem —
   pomaga, tylko ze zwrotem malejącym (4× koszt → +0.92 pkt).
   **Drugi przełom (większy niż budżet):** generator kandydatów kliknięcia oparty na
   segmentacji blobów był dla części gier ŚLEPY. Zmiana na kalibrację po **efekcie**
   (sonda siatki co 4 px przez `level_reset()`, grupowanie po hashu ramki, jeden
   reprezentant na różny efekt) dała **+3 gry od razu: ar25, cn04, ft09** (2.59 → 3.08 pkt),
   przy koszcie ~0.5 s kalibracji na grę. ft09: rozgałęzienie 8 zamiast 28 martwych ruchów,
   poziom 0 w 4 akcjach. Szczegóły i trzy patologie gier click-owych: FAKTY §1bis.
   **Trzeci krok (też tani, i on rozstrzyga spór o budżet):** przebieg z capem **60 000**
   węzłów (5×) i 600 s na grę, uruchomiony tylko na 8 grach uciętych wcześniej capem, dał
   **+1 grę: s5i5** (1 poziom, 21 akcji, replay OK) → 3.08 → **3.18 pkt (symulator lokalny)**. To dowód, że
   dla części gier blokerem był faktycznie budżet, a nie heurystyka — ale TYLKO dla części.
   Rozróżnienie jest w FAKTY §1bis(f)-(g): są **trzy** tryby porażki (`node_cap_cut` 2 gry,
   `time_cut` 6, `frontier_exhausted` 6) i **przypisanie trybu zależy od budżetu** — dc22 i
   sc25 przy capie 12 000 wyglądały na ucięte, a przy 60 000 okazały się wyczerpane.
   Podnoszenie budżetu ma sens wyłącznie dla `node_cap_cut` (ka59, re86) i dla `time_cut`
   z niskim kosztem węzła; wa30 robi 0.64 s/węzeł, więc przy 60 000 węzłów potrzebowałaby
   10.7 godziny — jej nie pomoże żaden budżet.
   Czarne pozostają: tn36, ka59, dc22, r11l, sc25, lf52, bp35, g50t, re86, sb26,
   sk48, su15, tr87, wa30 (14 gier).

Gotowe do wpięcia: `patches/0004-standalone-level-token-cap.patch`, `arc3_level_budget.py`,
16 testów jednostkowych, `results/playbook.json`.

**SPROSTOWANIE tej samej sekcji (pomiar z wieczora 24.10):** napisałem wyżej „+ `0003b` jeśli
chcą zachować 0003". To ZŁA RADA i została zmierzona jako błędna: łańcuch
`franzen → 0001 → 0002 → 0003b → 0004-standalone` **nie nakłada się**
(`error: patch failed: solver.py:46`) — oba patche wchodzą w ten sam rejon `solver.py`.
Poprawne wpięcie to **ZASTĄPIĆ** ich 0003 naszym 0004 w tym samym slocie
(`/kaggle/duck-extra-02.patch`), a nie dokładać czwarty plik. Łańcuch
`franzen → 0001 → 0002 → 0004-standalone` = 4/4 OK, `py_compile` 3/3 OK, testy 16/16 OK.
Robi to automatycznie `tools/make_notebook_patch.py`, a dowód jest w
`results/verification_notebook.txt`.
