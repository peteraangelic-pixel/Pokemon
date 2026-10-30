# Audyt czterech gałęzi (30.10 ~07:45 UTC) — RETRAKCJA Smaka, i 3,6× luka silnika

**Czytane read-only przez `gh api`.** Stan mojej gałęzi przed rozpoczęciem: HEAD == remote == `f3c5726`, 0 zmian.

| gałąź | HEAD | czas |
|---|---|---|
| `Gemma-konkurs@c4eeb067` | `6a6af4ac` | 30.10 07:25 |
| `Gemma-konkurs@6d081d52` | `678da952` | **25.10 10:20** (nieaktualizowana od 5 dni) |
| `Smak-Domu-Konkurs@5ed750ef` | **`b09f5037`** | **30.10 07:42** |
| `Pokemon@7911f950` | **`a84173ce`** | **30.10 07:38** |

> **STRESZCZENIE. (1) Smak wydał RETRAKCJĘ nr 3 i wycofał „roster = 110 klonów" oraz „sufit
> 45-55" — sprawdził docstring osobiście i cytuje moją lekcję po imieniu. (2) Wszystkie cztery
> sesje zbiegły na tę samą listę ustaleń. (3) Ale pojawiła się liczba, która jest warta więcej
> niż wszystkie dźwignie konfiguracyjne razem: `MEGA-CONFIG.md` Gemmy pokazuje, że TEN SAM model
> 8B miał 17,2 ms/token w r085 i 62,6 ms/token w r110 — **3,6× różnicy, która nie pochodzi ani
> z modelu, ani z promptu**. To jest 228 vs 82 akcji na grę. (4) Mam hipotezę mechanizmu,
> z arytmetyką, i jest sprawdzalna za darmo w `serve.log`. (5) `6d081d52` zawiera audyt MOJEJ
> gałęzi z 25.10 — w większości potwierdzenia, plus jedną flagę zgodności dotyczącą mojego kodu.**

---

## 1. ✅ RETRAKCJA Smaka — pełna konwergencja

`CROSS-SESSION-SYNC-2026-10-25.md` §15 (commit `43c8d9ff`, 07:35:41), dosłownie:

> **RETRAKCJA (3. w projekcie, po v11-Smak i v9-dead): „roster = 110 klonów 25 gier POTWIERDZONY
> W KODZIE" — FAŁSZYWE**
> * Weryfikacja osobiście w repo: `competition_arcade.py` L1-8: *„**Local** competition-mode
>   ARC-AGI Arcade simulator (R11.13). The **real Kaggle submission path talks to a gateway-backed
>   Arcade** … **hidden baselines**, and **no repeated game IDs within that scorecard**."*
> * Czyli `official_110()` = **KSZTAŁT** submisji na symulatorze LOKALNYM (przed-submisyjne repro
>   failów), **NIE roster punktowany**.
> * Wnioski: (a) **playbook EV ≈ 0** na ukrytym rosterze … — **„sufit 45-55" RETRAKTOWANY**;
>   (b) **replay między wpisami / dead-skip między wpisami = martwe** (brak powtórzeń w scorecardzie);
>   (c) **lekcja c87, trzeci raz: czytać DOCSTRING, nie nazwę funkcji.**
> * Zostaje formalna szczelina („no repeated IDs" ≠ wprost „gry mechanicznie różne"), ale 3 niezależne
>   pomiary zewnętrzne (source-introspection 0.20; held-out 0/113 vs 7/70; „110 hidden games").
>   **ROZSTRZYGNIĘCIE ZA DARMO**: probe z outputu dzisiejszego runa albo log reruna #57737623.

**To jest dokładnie ta retrakcja, o którą wnioskowałem** — włącznie z zachowaniem „formalnej
szczeliny", którą sam oznaczyłem jako uczciwe zastrzeżenie (`OPINIE-3-GALEZI-O-V13.md` §2).
I przyznają wprost w §16: *„Ujawniła NASZĄ wewnętrzną sprzeczność … **Przyznaję wprost: moja sesja
to poprawnie ustaliła 25.10 i sama sobie zaprzeczyła 30.10.** Retrakcja §15 stoi."*

### 1.1 Ich lista konwergencji (cytuję, bo to jest wspólny stan wiedzy czterech sesji)

| ustalenie | kto | status |
|---|---|---|
| „Dwie z trzech dźwigni 0006 martwe w submisji" | **Gemma + c87 niezależnie** | ✅ (`n_passes=1` + brak powtórzeń; dead-skip wymagał passa ≥4) |
| „23.89 = draw, nie regresja" | **7911 (sd=2.47; −1.3 sd) + c87 (σ=3.93)** | ✅ → **metoda: TA SAMA konfiguracja 2× z rzędu** |
| „Głębokość/pokrycie = ~96% brakujących punktów; efektywność 86-90%; sufit przy tym budżecie 18.7-31.9" | **Gemma + 7911 + c87** | ✅ |
| „50+ = PRZEPUSTOWOŚĆ (~300 akcji/grę z ~213), nie mądrzejszy model (27B: 0.27 przy 47 s/akcję)" | **3 niezależne modele** | ✅ |
| „Cap per-poziom = **1.15**, nie 1.0" | **c87** | ✅ (metodologia arcprize + `taaf/game.py` `min(115,…)` + regresja 32/32 Gemmy); i tak prawie zawsze wiąże **cap UKOŃCZENIA** |
| „Playbook 14/14" | **3 niezależne reprodukcje** | ✅ (Arena na silniku; Gemma 184/184 hashy + seedy 1/2/7/42; 7911 krzyżowo 2 ścieżki) |

### 1.2 Korekty, które przyjęli od 7911f950

* **`commit(plan)` tylko OFEROWANY** ⇒ *„bez wymuszenia v13.1 gra jak v11+playbook (~28-30)"*.
  Tanie naprawy: **`ESCALATE_ACTIONS` 60→8-10**; wymuszenie batcha na **1. turze poziomu**;
  odrzucanie 1-akcyjnych tur bez uzasadnienia (**kandydat na 1.11**).
* **cicha awaria replay** (`try/except pass`, init-mismatch → `broken` **bez logu**) ⇒
  **wymagać linii logu o replay**. To rozszerza znalezisko Gemmy (§4 jej recenzji) — ona sprawdziła,
  że `fails` **nie** rośnie i nie ma zatruwania ścieżek; 7911 dodaje, że **awaria jest niewidoczna**,
  więc nie dałoby się jej zdiagnozować z logu rerunu. **Oba prawdziwe, i drugie jest groźniejsze
  operacyjnie.**

### 1.3 Ich zrewidowany plan slotu (SYNC §16, `b09f5037` 07:42)

> **REWIZJA slotu 30.10: v13.1 as-shipped (`WINPATH=1`/`DEAD_SKIP=1` wracają — darmowa opcja przy
> cyklicznym rosterze) + probe ON**

Plus ich własna kontrola, którą warto odnotować jako **dobrą praktykę**: *„serving-parity
v13.1 == c45 potwierdzona — kom.21 == kom.17, MAXREQ=10/cuda-graph/chunked identycznie →
pakiet GO#1 **bez cichej regresji silnika**"*. **To jest dokładnie ten rodzaj sprawdzenia
spójności międzywarstwowej, którego zabrakło przy `concurrency=120`.**

⚠️ **Moja uwaga do tej rewizji, jedna:** po retrakcji §15 replay między wpisami jest **martwy**
(„brak powtórzeń w scorecardzie"), więc `WINPATH=1` nie jest „darmową opcją przy cyklicznym
rosterze" — jest **opcją przy rosterze, którego istnienie właśnie wycofali**. Wartość oczekiwana
≈ 0, a 7911 znalazł w tym kodzie **cichą awarię bez logu**. **Nie jest to ryzyko wyniku, jest to
ryzyko diagnostyki.** Ich decyzja, ale rozróżnienie jest warte zapisania: *„darmowa opcja"*
zakłada niezerowe prawdopodobieństwo wypłaty, a §15 właśnie to prawdopodobieństwo wycofał.

---

## 2. ❗NAJWAŻNIEJSZA LICZBA TEGO AUDYTU: 3,6× luka silnika, nie pochodząca z modelu ani z promptu

`Gemma-konkurs@6d081d52`… nie — **`Gemma-konkurs@c4eeb067`, `ARC3/local-lab/MEGA-CONFIG.md` §1.**

### 2.1 Najpierw ich własna korekta (i moja też)

> *„Pierwotna wersja tego punktu twierdziła, że dźwignią jest podniesienie `max_runtime_s_per_game`
> z 48 min. **To było błędne** i wynikało z **czytania dev-smoke'a jako submitu**."*

**To jest dokładnie ten sam błąd, który ja zrobiłem** w `DIAGNOZA-23-89-I-PLAN.md` §2.3 (wziąłem
smoke'owe „10 gier × 2880 s" za konfigurację rerunu) i który wycofałem w `OPINIE-3-GALEZI-O-V13.md`.
**Dwie sesje, ten sam błąd, ta sama korekta.** Reguła warta wpisania do `FAKTY-I-POMIARY.md`:
**komórka konfiguracyjna ma DWA bloki — smoke i `TRUE_SUBMISSION`. Czytanie pierwszego jako
drugiego daje fałszywy model budżetu.**

### 2.2 Arytmetyka prawdziwego submitu

```python
if TRUE_SUBMISSION:                       # KAGGLE_IS_COMPETITION_RERUN
    bm.solver.save_request_logs = False
    bm.n_passes = 1
    if USE_PRIORITY_SCHEDULING:           # = True
        bm.solver.concurrency = int(os.environ.get("ARC3_TRUE_CONCURRENCY", "10"))
        bm.solver.max_runtime_s_per_game = 532 * 60      # 31 920 s = 8,87 h
```

| element | wartość |
|---|---|
| budżet notatnika | **32 400 s (9 h)**, asercja w kodzie |
| roster | **110 gier** |
| concurrency (backend MAXREQ) | **10** |
| fal | 110 / 10 = **11** |
| **efektywny czas na grę** | 32 400 / 11 = **2 945 s ≈ 49 min** |

> **Cap 532 min NIGDY NIE WIĄŻE — wiąże liczba fal.** Podnoszenie go nic nie daje.
> `USE_PRIORITY_SCHEDULING = True` **potwierdza ostatecznie** moją korektę §2.3 z
> `OPINIE-3-GALEZI-O-V13.md` (scheduler priorytetowy jest włączony w rerunie; „równy przydział"
> dotyczył tylko smoke).

I wzór, który zastępuje wszystkie dotychczasowe modele budżetu:

```
akcje/grę = 2 945 s / (sekundy na akcję)
```

### 2.3 Tabela, która zmienia priorytety

`s/akcja` jest w każdym runie **liniowe w tokenach na akcję (r = 0,99–1,00 na 10 grach)**:

| run | silnik | **ms na token** | mediana tok/akcję | s/akcję | **akcje/gę (49 min)** |
|---|---|---|---|---|---|
| **r085** | 8B, bez capa | **17,2** | 647 | **12,9** | **228** |
| **r110** | 8B, v13 cap 45k | **62,6** | 572 | **36,0** | **82** |
| **r118** | 27B | 63,1 | 686 | 47,0 | 63 |

> **TEN SAM MODEL 8B: 17,2 vs 62,6 ms/token = 3,6×. Gemma wprost: *„3,6× różnicy nie pochodzi
> z modelu ani z promptu".***
>
> Zauważ też: **r110 ma MNIEJ tokenów na akcję (572) niż r085 (647), a mimo to 2,8× mniej akcji
> na grę.** Czyli „mózg treściwszy" (dźwignia 1) **nie pomógł** — zjadła go dźwignia 2 (silnik).
> **To obala intuicję, że oszczędzanie tokenów na akcję jest główną drogą.**

**Cele z `MEGA-CONFIG.md`:** *„400+ akcji/gę wymaga ~370 tok/akcję przy r085-owym silniku;
600 akcji wymaga ~230."* I ich §2.3/§4: dwie dźwignie — **mniej tokenów na akcję** oraz
**lepszy silnik**.

**Sprawdziłem, że r110 istnieje** (nie jest zmyślony): `Smak-Domu-Konkurs/arc-agi-3/kaggle/ops/
results/r110-kernel_output_pick/output-pick`. Zawartości w tej turze nie czytałem — **oznaczam
jako niezweryfikowaną przeze mnie wprost**, ale artefakt jest.

### 2.4 Dlaczego to jest warte więcej niż wszystkie dźwignie konfiguracyjne

Z projekcji Gemmy (`PLAN-50.md` §0 pkt 5, z zachowaną efektywnością runu):

| akcje/grę | projekcja wyniku |
|---|---|
| 200 | 35,6 |
| **300** | **59,5** |
| 400 | 72,3 |
| 600 | 83,1 |

* **r110 = 82 akcje/grę** → sufit 7911f950 dla 110 gier: **18,7**
* **r085 = 228 akcji/grę** → projekcja **~35,6**
* **odzyskanie 3,6× = przejście 82 → 228 akcji** bez zmiany modelu, promptu, playbooka, schedulera
  ani żadnej dźwigni, o której dyskutowaliśmy przez trzy dni

> **To jest jedyna zidentyfikowana droga do 40+, która NIE wymaga ani nowego modelu, ani
> nieopublikowanej techniki.** I jest **~10× większa** niż wszystko, o co spieraliśmy się
> w sprawie v13 (playbook 0–2,9 · `CAP=0` +0,4…2,2 · `EXPOSE_UNDO` niezmierzone ·
> `PLAN_COMMIT` bez wymuszenia ~0).

---

## 3. Moja hipoteza mechanizmu 3,6× — z arytmetyką, sprawdzalna za darmo

**Nie twierdzę, że to prawda. Twierdzę, że to jest hipoteza z liczbami i że da się ją rozstrzygnąć
bez GPU i bez slotu.**

### 3.1 Arytmetyka puli KV

Z tabeli Tong Hui Kanga (`discussion/744792`), potwierdzonej w moich `FAKTY-I-POMIARY.md`:

| parametr | wartość |
|---|---|
| **KV pool** | **1 011 264 tokenów** |
| kontekst (server / harness) | **139 264 / 131 072** |
| trim | przy **118k**, zrzuca do **~59k** |
| gry współbieżne | **10** |

```
10 gier × 131 072 tok = 1 310 720  >  1 011 264  (pula)
⇒ przy PEŁNYM kontekście mieści się 1 011 264 / 131 072 = 7,7 gry, nie 10
⇒ pula nasyca się, gdy ŚREDNI kontekst na grę przekracza 1 011 264 / 10 = 101 126 tok
⇒ a trim odpala DOPIERO PRZY 118 000 — czyli gry spędzają istotny czas POWYŻEJ progu nasycenia
```

**Nasycenie jest więc oczekiwane, nie wyjątkowe.** A kiedy pula jest nasycona, żądania **kolejkują
po miejsce w cache** — i to jest dokładnie mechanizm, który **rellik13 (25. miejsce, sirikilohit)**
opisał jako swój własny błąd:

> *„the **kv pool sat somewhere between 91-97% full and requests queued for cache space**, so the
> **memory was the actual limit**"*

Kolejkowanie po miejsce w cache wydłuża czas na token — czyli **podnosi ms/token bez zmiany modelu
i promptu**. Zgadza się z obserwacją Gemmy.

### 3.2 Dlaczego smoke (r085) mógł mieć 17,2 a rerun-opodobny (r110) 62,6

**Hipoteza: prefix-cache.** Moje `FAKTY-I-POMIARY.md` mają zmierzone **93,2% prefix-cache** dla
konfiguracji c45. Smoke gra **10 tych samych gier** przez cały bieg — współdzielony prefiks systemowy
i podobne stany dają wysoką trafialność. Rerun widzi **110 różnych gier**, więc trafialność spada,
a każda chybiona wymaga pełnego prefillu z kolejki po KV.

⚠️ **Uczciwie, czego ta hipoteza NIE wyjaśnia:** r110 w opisie Gemmy to *„8B, v13 cap 45k"*, czyli
też **smoke-like** run, nie pełny rerun 110 gier. Jeśli r110 też grał 10 gier, to prefix-cache
**nie** tłumaczy różnicy i trzeba innego mechanizmu (np. inny stan `cuda-graph`, inna fragmentacja
puli po zmianie capa, albo inna kolejność gier). **Nie domknę tego bez przeczytania r110.**

### 3.3 Jak rozstrzygnąć — 0 GPU, 0 slotów, na PC usera

Metryki, których **nikt nie sparsował**, a leżą w artefaktach:

| plik | rozmiar | co w nim jest |
|---|---|---|
| `r093/output-pick/serve.log` (v11) | **1 143 523 B** | log SGLang: obłożenie puli KV, kolejki, trafialność cache |
| `r085/output-pick/serve.log` (c45) | **986 600 B** | to samo dla runu z **17,2 ms/token** |
| `r110-kernel_output_pick/output-pick` | ? | run z **62,6 ms/token** |

**Policzyć dla każdego z trzech runów i porównać:**
1. **% obłożenia puli KV** w czasie (szereg, nie średnia) — czy r110 siedzi 91-97% jak u rellik13
2. **liczbę i czas kolejek po miejsce w cache** (`waiting for cache` / `queue` w logu SGLang)
3. **trafialność prefix-cache** (r085 ma zmierzone 93,2% — ile mają r110 i r093?)
4. **ms/token per gra**, nie per run — żeby zobaczyć, czy to globalne, czy dotyczy części gier

To jest **dokładnie** to zadanie, na którym 16 rdzeni i 64 GB usera realnie pomagają, a mój
sandbox (2 CPU / 3,9 GB) nie daje rady. **I to jest jedyna rzecz z całej listy, która może być
warta 20–40 punktów.**

---

## 4. `6d081d52` — audyt MOJEJ gałęzi z 25.10, którego nie znałem

`notes/ARC-AGI-3-cross-branch-update-2026-10-25.md` (commit `678da952`). Gałąź **nieaktualizowana
od 5 dni**, więc nie ma opinii o v13/v13.1 — ale zawiera audyt **mojej** pracy na tipie `6c53d13`.

### 4.1 Potwierdzenia moich ustaleń (niezależne, sprzed 5 dni)

* **Formuła punktacji „zgodna co do setnej z danymi r019"**: `min(115, (baseline/actions)²·100)`,
  wagi `w_k = k+1`, dodatkowy cap od ukończonych poziomów. Test na `tn36` (1/7 → 3,57) i `ls20`
  (1/7 → 3,27) odtwarza r019. **To czwarte niezależne potwierdzenie capu 115** (po arcprize,
  `taaf/game.py`, regresji Gemmy 32/32) — i kolejne przeciwko „1.0" z 7911f950.
* **Moje 1,75 pkt potwierdzone ich rachunkiem**: *„Sufit z samej głębokości smoke'u to 29,0 pkt
  wobec zmierzonych 27,21, czyli cała strata przypisana dalszej poprawie efektywności ruchów wynosi
  około **1,75 pkt**"*. Wniosek: *„wcześniejsza rada, by przede wszystkim „zmniejszać liczbę ruchów",
  **nie jest właściwym celem**"*, a *„**cel techniczny to ukończenie więcej ważonych poziomów**"*.
* **Moja kalibracja kliknięć uznana za najbardziej transferowalny wynik metodyczny**:
  *„kalibracja kliknięć **po zaobserwowanym efekcie**, zamiast wyznaczania klików z centroidów
  blobów"* — `ft09` przeszła z pustego searcha do ukończenia poziomu 1 w 4 akcjach.
* **Moja retrakcja +7–17 pkt odnotowana**: *„Nie sumować hipotetycznych zysków. Najnowszy commit
  c87 (`6c53d13`) wycofuje prognozę +7–17 pkt z level-cap/ABANDON: poziomy są sekwencyjne, a
  `ABANDON` kończy grę, nie przenosi budżetu."*
* **`RESET_LEVEL` jako jedyny kandydat per-gra, darmowy w tokenach, niezmierzony** — zgodnie z moim
  `PATCH-0004-I-SEARCH.md`.
* **`game_weights` NIE realokuje budżetu gry** — wpływa na diagnostykę/agregację. Oraz:
  **„`n_passes` jest nadpisywane do 1 w komórce 14 notebooka"** ⇒ **niezależne potwierdzenie
  `n_passes=1` już 25.10**, pięć dni przed moim ustaleniem z komórki 25 v13. Ich numeracja komórki
  inna (14 vs 25), bo inna wersja notebooka — mechanizm ten sam.
* **Korekta „brak pamięci"**: kompakcja pamięci **istnieje**, jest wyłączana przez
  `ARC3_MEMORY_SECTIONS=off`, a efektywny `ARC3_HISTORY_ASSISTANT_TURNS` = **150**, nie domyślne 30.
  Zgodne z moim `WERYFIKACJA-INNYCH-GALEZI.md`.
* **Mój budżet ~208 akcji/grę oznaczony jako szacunek z r019**, mieszczą się tylko `cd82` i `ft09`,
  najbliżej `sb26` i `r11l`; *„+1 poziom w każdej" to sufit arytmetyczny, nie plan wykonawczy.*
  Zgodne z moim `results/budget_triage.tsv`.

### 4.2 ⚠️ Flaga zgodności dotycząca MOJEGO kodu — przyjmuję

> *„Wewnętrzne `_get_valid_actions()`/`_score`/`_win_score` zostały w audycie oznaczone jako
> **niedozwolone w submissionie**; używać publicznego API i kalibracji po skutku."*

To dotyczy `arc3-handoff/arc3_search.py`. **Przyjmuję i to jest istotne**: gdyby ktokolwiek chciał
przenieść mój search do notebooka submisyjnego, te trzy funkcje **muszą być zastąpione** publicznym
API (`perform_action` + obserwacja skutku) i kalibracją po efekcie. **Dotąd miałem to zapisane
jako „search musi żyć w harnessie, bo sandbox wystawia tylko `current_frame` + `history`" — ale
nie jako zakaz zgodności.** To jest silniejsze sformułowanie i powinno trafić do
`PATCH-0004-I-SEARCH.md` jako ostrzeżenie.

Praktyczny skutek: **żaden** — search offline jest już wycofany jako źródło punktów
(0.20 / 0/113 / brak źródeł gier w rerunie). Ale flaga jest ważna dla **narzędzi lokalnych**,
żeby nie przeniosły zakazanego wzorca do submisji.

### 4.3 Ich ostrzeżenie o kolizji numeracji patchy — już je miałem

*„patch c87 o numerze `0004` i replay patch a450 `0004-solved-level-replay.patch` są **różnymi
zmianami**; nie składać ich w jeden łańcuch z tym samym numerem"* oraz *„c87 raportuje, że jego
standalone level-cap ma **zastąpić** stary patch 0003, a nie być dokładany po 0003b"*.
Zgodne z moim `PATCH-0004-I-SEARCH.md` §3 (ostrzeżenie o kolizji). **v13.1 używa numeru `0006`
dla winpath — czyli kolizja została uniknięta.**

---

## 5. 7911f950 `EVAL-BUDGET-MODEL.md` — dobry dowód pośredni, z jednym napięciem

### 5.1 Ich dowód na ~110 gier w rosterze (nie 25)

| obserwacja | wynik |
|---|---|
| smoke na 10 grach, 48 min/gra | 27,21 – 29,02 |
| **prawdziwy leaderboard** | **26,25** |

*„Te dwie liczby są **praktycznie identyczne**. A to znaczy, że w prawdziwym biegu graliśmy z takim
samym budżetem czasowym na grę jak w smoke (≈49 min), nie 4× dłużej."* Gdyby roster miał 25 gier,
efektywny czas na grę wyniósłby 32 400 × 10 / 25 = **216 min** (4,5× więcej) i wynik musiałby być
znacznie wyższy.

**To jest dobry argument i niezależny od docstringa.** Ale wymaga dwóch rozróżnień:

* **Odpowiada na pytanie (a) „ile gier?" → ~110.** ✅
* **Nie odpowiada na pytanie (b) „czy to klony 25 publicznych?"** — a **tylko (b) decyduje o wartości
  playbooka**. Smak to rozróżnia poprawnie po retrakcji; **warto go pilnować**, bo łatwo je zlać
  (ich „~4.4 klona" brało się właśnie z (a) przeskakującego na (b)).

### 5.2 ⚠️ Napięcie wewnętrzne w ich własnej tabeli — zaznaczam, nie rozstrzygam

Ich tabela sufitów (tempo 14,4 s/akcję z r013, `local/scheduler.py`, na kosztach ludzkich z r018):

| gier w rosterze | min/grę | akcji/grę | **sufit @ eff=90%** |
|---|---|---|---|
| 10 | 540 | 2 250 | 100,0 |
| 25 | 216 | 900 | 87,3 |
| 50 | 108 | 450 | 59,1 |
| **110** | **49** | **205** | **18,7** |

**Problem: ich sufit dla 110 gier wynosi 18,7, a zmierzony LB to 26,25 — czyli WYNIK JEST POWYŻEJ
ich własnego sufitu.** Jedno z trzech musi być nie tak:

1. tempo **14,4 s/akcję** pochodzi z **r013 (stara linia)**; nasza szybka linia ma **12,9 s/akcję**
   (Gemma, r085) — przy 12,9 zamiast 14,4 liczba akcji rośnie z 205 do **228** (+11%), co podnosi
   sufit, ale nie z 18,7 do 26,25;
2. albo `eff=90%` i koszty ludzkie z **r018** nie są reprezentatywne dla 110 ukrytych gier;
3. albo roster **nie ma** 110 gier.

**Nie rozstrzygnę tego bez `scheduler.py` i r018.** Zaznaczam, bo **ich §3 (dowód na ~110) i ich
własna tabela sufitów są w napięciu** — a obie liczby są cytowane w SYNC §16 Smaka jako ustalenia.
**To jest dokładnie ten rodzaj niespójności między dwiema liczbami w tym samym dokumencie, który
u mnie spowodował `concurrency=120`.** Reguła: **porównywać liczby osiem linijek od siebie.**

---

## 6. Stan wspólny i plan — po audycie czterech gałęzi

### 6.1 Co jest ustalone ponad wszelką wątpliwość (4 sesje, niezależne drogi)

1. **`n_passes = 1` w rerunie** — potwierdzone 4×: komórka 25 v13 (c87), `benchmark.json` r085/r093
   (c87), komórka 14 v11 (6d081d52, już 25.10), `EVAL-BUDGET-MODEL` (7911)
2. **Roster punktowany ≠ `official_110()`** — retrakcja Smaka §15, docstring, Gemma, trzy pomiary
   zewnętrzne. **Playbook EV ≈ 0–2,9, nie 45–55.**
3. **23.89 to draw, nie regresja** — sd 2,47 (7911) i σ 3,93 (c87), próg istotności +5
4. **Cap per-poziom = 1.15**, ale wiąże **cap ukończenia**; efektywność ruchów ≈ **1,75–3,0 pkt**
5. **Głębokość = ~96% brakujących punktów**; pokrycie **29%**; efektywność na ukończonych **86–90%**
6. **50+ = przepustowość**: ~**300 akcji/grę** z obecnych ~213; 27B **skreślone** (1,18 i 0,27)
7. **`commit(plan)` jest tylko oferowane** — bez wymuszenia `PLAN_COMMIT="1"` daje ~0, czasem ujemne
8. **Budżet: 11 fal × 2 945 s ≈ 49 min/grę**; cap 532 min **nigdy nie wiąże**

### 6.2 Kolejność działań po przeliczeniu wartości — zmieniona przez §2

| # | działanie | koszt | wartość |
|---|---|---|---|
| **1** | ❗**Sparsować `serve.log` z r085 (17,2 ms/tok), r110 (62,6) i r093** pod kątem obłożenia puli KV, kolejek i trafialności prefix-cache (§3.3) | **0 GPU, 0 slotów**, PC usera, ~godzina | **potencjalnie 82 → 228 akcji/grę = ~18,7 → ~35,6.** Największa znana dźwignia |
| **2** | **Pobrać log rerunu ref 57737623** i wyciągnąć 110 `game_id` (§1.5 Smaka: „rozstrzygnięcie za darmo") | **0**, przeglądarka usera | kończy spór o roster; decyduje czy `WINPATH` kiedykolwiek włączać |
| **3** | **Sprawdzić, czy `ARC3_ESCALATE_ACTIONS` jest env** i przygotować 60 → 8–10 | 0 GPU, kilkanaście minut CPU | wymusza batching = jedyna dźwignia celująca w akcje/decyzję |
| **4** | Slot **30.10**: v13.1 + **`probe ON`** + `CAP=0` + `EXPOSE_UNDO="on"` + `PLAN_COMMIT="0"` | 1 slot | ~27–29 **i rozstrzyga roster** |
| **5** | Slot **31.10**: rozgałęzienie pomiarem — jeśli §1 da odzyskanie silnika → konfiguracja z nim; jeśli roster prywatny → `ESCALATE_ACTIONS` 8–10 jako **jedyna** zmiana | 1 slot | ~29–35 |
| **6** | Sloty **1.11 / 2.11**: drugi draw najlepszego configu, potem select best | 2 sloty | zabezpieczenie przed szumem |

**Zmiana względem mojego planu z `OCENA-V13-1-TRZY-RECENZJE.md` §5:** pkt 1 jest **NOWY i jest
pierwszy**. Przez trzy dni spieraliśmy się o dźwignie warte **0–2,9 pkt**, podczas gdy w artefaktach
leży różnica **3,6× w ms/token** warta **82 → 228 akcji/grę**. **Nikt jej nie zbadał, bo nikt nie
sparsował `serve.log`.** To jest ta sama lekcja co `concurrency=120` i `EXPOSE_UNDO`:
**liczby leżą obok siebie w artefaktach i czekają, aż ktoś je porówna.**

### 6.3 Czego nie robić (bez zmian, plus dwa nowe)

❌ 27B (1,18 / 0,27) · parametry serwingu bez pomiaru KV (−7…−8) · `n_passes>1` · search offline
(0.20 / 0/113) · stackowanie zmian · `PLAN_COMMIT="1"` bez wymuszenia · podnoszenie
`max_runtime_s_per_game` (**cap nigdy nie wiąże** — §2.2) · **oszczędzanie tokenów na akcję jako
GŁÓWNA dźwignia** (r110 miał 572 tok/akcję wobec 647 w r085 i **2,8× mniej akcji** — §2.3)
· przenoszenie `_get_valid_actions()`/`_score`/`_win_score` do submisji (§4.2)

**Oczekiwanie: ~28–30** (cztery sesje: Gemma 26–31 · c87 ~27–29 · Smak ~28–30 · ich README 28–38).
**Cel: srebro ≈32.33.** **Ścieżka do 40+ jest jedna: odzyskać 17,2 ms/token (§3).**
