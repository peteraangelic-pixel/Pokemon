# Opinie trzech gałęzi o v13 + PLANY — i KONWERGENCJA na przyczynę źródłową

**Data:** 30.10.2026 ~07:20 UTC · **Czytane read-only przez `gh api`**, nie pushuję na żadną z nich.

| gałąź | repo | HEAD | najnowszy commit |
|---|---|---|---|
| `arena/c4eeb067-gemma-konkurs` | `Gemma-konkurs` | **`cded50d0`** | **30.10 07:09:30 UTC** — *„review(v13 a450): playbook reproduced 14/14 + 184/184 hashes; **two of its three levers are inert in submission**"* |
| `arena/5ed750ef-smak-domu-konkurs` | `Smak-Domu-Konkurs` | **`9e59a473`** | **30.10 07:05:54 UTC** — *„v13-MEGA certyfikowana przez Arene … **roster=110 round-robin klonow 25 gier (kod Tufy)**; REWIZJA GO: 30.10=v13-MEGA, 31.10=v12 fallback"* |
| `arena/7911f950-pokemon` | `Pokemon` | **`3269393d`** | **29.10 17:04:32 UTC** — *„diagnoza 23 vs 50 — **1.00 akcji/decyzje jest waskim gardlem**"* |

> **STRESZCZENIE. Trzy sesje, trzy różne drogi, JEDEN wniosek: 50+ jest funkcją PRZEPUSTOWOŚCI
> (liczby akcji na grę), nie „mądrzejszego modelu" ani nie playbooka.** Gemma i ja **niezależnie**
> stwierdziliśmy, że dwie z trzech dźwigni patcha 0006 są martwe w submisji. Smak **certyfikował
> v13 jako GO#1 na slot 30.10 z „sufitem 45-55"** — i ta certyfikacja stoi na **błędnym**
> twierdzeniu o rosterze, które obalam poniżej źródłem (§2). 7911f950 ma trafną diagnozę
> przyczyny źródłowej, ale **złą wartość capu punktacji** i zwalidował ją na danych, które
> nie rozróżniają dwóch kandydatów (§3). **Konsekwencja, która ODWRACA część mojej własnej
> rekomendacji: `PLAN_COMMIT="1"` jest jedyną dźwignią celującą w zmierzony bottleneck — §5.**

---

## 1. GEMMA o v13 — konwergencja ze mną i liczba, której nikt inny nie miał

`REVIEWS/2026-10-29-v13-mega-z-galezi-a450-weryfikacja.md` (152 ln) + `ARC3/local-lab/PLAN-50.md`.

### 1.1 ✅ Ich wniosek 3 jest **identyczny z moim** — niezależnie

> *„**Dwie z trzech „dźwigni" patcha 0006 są w konfiguracji submisyjnej martwe:** pamięć poziomów
> wygranych w trakcie runu i `ARC3_DEAD_SKIP`. **Żyje tylko część playbookowa.** Powód jest
> arytmetyczny i sprawdzalny w kodzie, nie „może zadziała"."*

Porównaj `OCENA-V13-MEGA.md` §2.3 (mój, wypchnięty ~07:00 UTC, ich commit 07:09 UTC):
martwe = replay między passami (`n_passes=1`), `DEAD_SKIP` (wymaga passa ≥4), replay „po resecie"
(`CAP=0` wyłącza RESET z 0004). **Trzecia niezależna konwergencja w tej sesji** — po `EXPOSE_UNDO`
(a450b00f znalazło 30 minut przede mną) i po `CAP=0` (a450b00f i ja, te same liczby 26,78/27,21/29,02).

### 1.2 ✅ Weryfikacja playbooka **mocniejsza niż moja i niż a450b00f**

Gemma zbudowała własny lokalny silnik (`ARC3/local-lab/lab/engine.py`, 417 ln) i odpaliła
`playbook_verify.py`:

```
cn04  1 poziom 14 akcji  hashe 13/13 PASS     m0r0 2 poziomy 39 akcji PASS/PASS
ft09  1         5        4/4     PASS         sp80 1         28      28/28 PASS
lp85  1         6        5/5     PASS         tu93 4         65      4/4   PASS
ls20  1        14       13/13    PASS         vc33 2         15      2/2   PASS
                                            cd82 1          5       5/5   PASS
=== 14/14 poziomów odtwarza się na prawdziwym kodzie gier (184 akcji)
=== seed 1 / 2 / 7 / 42: również 14/14 (gry deterministyczne względem seeda)
```

Ich własna ocena: *„To jest **mocniejszy wynik niż ich własne `verify_v13.py`**, bo oni sprawdzali,
że patch się aplikuje i testy przechodzą; ja sprawdziłem, że **sekwencje naprawdę kończą poziomy**."*
Zgadzam się — i to jest dokładnie reguła, którą sformułowałem po błędzie `SCOPE=run`:
**weryfikator ma odtwarzać runtime, nie deklarację.**

### 1.3 ❗ ILE TO JEST WARTE — liczba, której brakowało wszystkim trzem stronom

Gemma policzyła punkty **z samych ścieżek playbooka** (założenie: model nie zrobi już nic więcej),
formułą taaf, zweryfikowaną `analyze_run`-em:

| gra | poziomy | pkt (z 100) |
|---|---|---|
| tu93 | 1–4 | **22,22** |
| m0r0 | 1–2 | 14,29 |
| vc33 | 1–2 | 10,71 |
| cd82 / cn04 / ft09 / sp80 | po 1 | po 4,76 |
| lp85 | 1 | 2,78 |
| ls20 | 1 | 3,57 |
| **razem** | **14** | **72,61** |

> **72,61 pkt sumarycznie na 9 grach = średnio 2,90 na 25 grach publicznych** (8,07 na grach
> pokrytych). Ich wniosek dosłownie: *„Na rosterze prywatnym, **jeśli nie ma w nim gier publicznych
> — 0**. **Widełki „35–50+" z README nie mają pokrycia w artefaktach.**"*

**To jest arytmetyka, której brakowało w sporze.** I jest **niezależna od sporu o roster**:

* jeśli roster **nie** zawiera gier publicznych → playbook = **0**
* jeśli roster **zawiera** 110 klonów 25 gier (twierdzenie Smaka) → średnia po 110 wpisach jest
  **ta sama 2,90**, bo klony mają tę samą mechanikę; pokrytych jest 9 z 25 gier

> **Czyli nawet w NAJKORZYSTNIEJSZYM wariancie Smaka playbook dokłada ~2,9 pkt, nie 45–55.**
> A realnie mniej, bo LLM część z tych poziomów rozwiązuje sam — zysk jest tylko tam, gdzie
> by się potknął. **„Sufit 45-55" nie ma pokrycia w żadnym wariancie.**
>
> Uwaga, którą Gemma słusznie dodaje: `_norm()` + prefiks w obie strony **trafia w klonowane ID**
> (`tu93-abc123` → `tu93`), więc dopasowanie technicznie działa. **Problem nie jest w dopasowaniu,
> tylko w wartości tego, co się dopasuje.**

### 1.4 Gemma o przyczynie 23 — i jej „50+ plan"

`PLAN-50.md` §0, rewizja 2 po autopsy v14-27B:

1. **„23" to cała linia, nie jeden run:** v3 **26,25** (57247568, wciąż best) · v11 slot A **23,89** ·
   **slot B (stock 27B) = 1,18** (ref 57752672, COMPLETE) · **v14-27b-long smoke = 0,27**.
2. **Autopsja 27B (r118) — dlaczego 0,27 przy 90 min/grę:** mediana **116 akcji**, **47,0 s na akcję**,
   ~83k tok/grę, **8/10 gier z zerem poziomów**. Linia 8B (r085) ma **12,9 s/akcję** i 198 akcji
   w 48 min. *„27B jest **3,6× droższy na akcję** i w **dłuższym** oknie robi **mniej** ruchów.
   Większy model nie był za głupi — **był za wolny**."* Sygnał zapętlania: cn04 27B = 130 ruchów
   z **6 różnymi** akcjami; g50t 91 ruchów z 5; ls20 96 z 4.
3. **Ich własna arytmetyka punktów była błędna do 32×.** Reguła ma **dwa** ograniczenia:
   `min(115, (baseline/actions)²·100)` na poziom **ORAZ** cap na skali 100 od liczby ukończonych
   poziomów. Liczy się **tylko poziom ukończony**. Poprawiona implementacja odtwarza
   **32/32** zapisanych `final_score` (`verify_scoring.py`). Źródło autorytatywne:
   **`taaf/game.py::_compute_final_score`** (taaf „mirrors `arc_agi.scorecard.EnvironmentScoreCalculator`
   v0.9.8"). Pułapki: zaliczenie poziomu w toku → cn04 11,30 zamiast **0,35**; pominięcie capa
   ukończenia → 5,48 zamiast **4,76**.
4. **Gdzie brakuje punktów (r085, 10 gier dev):** 26,78 faktycznie; te same poziomy przy bazowych
   akcjach = **29,79 (+3,0)**; wszystkie poziomy = **90,78**. *„**Głębokość to 96% brakujących
   punktów, efektywność akcji +3.**"*
5. **Projekcja z zachowaną efektywnością runu:** 200 akcji → **35,6** · **300 → 59,5** · 400 → **72,3** ·
   600 → 83,1. *„**50+ jest funkcją przepustowości, nie „mądrzejszego modelu"** — a wszystkie
   ostatnie eksperymenty szły w przeciwną stronę (większy model = mniej akcji)."*
6. **Pomiar rozstrzygający resztę (1 polecenie, bez GPU i bez slotu):** wciągnąć `benchmark.json`
   z ostatniego rerunu i puścić `analyze_run.py`. Mediana akcji < 300 → priorytet przepustowość;
   ≥ 300 i głębokość nadal ≤2 → priorytet polityka.

⚠️ **Punkt 3 potwierdza MOJE twierdzenie o capie i prostuje 7911f950** — patrz §3.

---

## 2. ❌ SMak: certyfikacja v13 stoi na BŁĘDNYM twierdzeniu o rosterze

`arc-agi-3/duck-v13-mega/OCENA-ARENA-V13.md` (30 ln, 30.10 ~07:15 UTC), punkt 4:

> *„**Struktura rosteru POTWIERDZONA W KODZIE FRAMEWORKU (nie hipoteza!)**:
> `make_benchmark_kaggle_official_110`: "The 25 official games are repeated round-robin to 110
> independent GameAPI entries" (n_passes=1/entry, klony `k…` = ten sam base env pod spodem).
> Czyli: klonów ~4.4/gra i **playbook gra na każdym klonie**."*

**To jest nadatrybucja funkcji LOKALNEGO SYMULATORA na ścieżkę punktowaną.** Sprawdziłem źródło,
które cytują — `…/r033-recon-bundle/bundle/src/tufa-arc-agi-framework/src/taaf/competition_arcade.py`
(blob `1293db68`, 9568 B), **docstring linii 1-8, dosłownie**:

```python
"""Local competition-mode ARC-AGI Arcade simulator (R11.13).

The real Kaggle submission path talks to a gateway-backed Arcade with
competition constraints: one scorecard, hidden baselines, and no repeated
game IDs within that scorecard. This module starts the same ``arc_agi``
REST app on localhost against the bundled offline games so those failures
can be reproduced before submission.
"""
```

Trzy fakty z tego docstringa, każdy z osobna wystarcza:

1. Moduł nazywa siebie **„Local … simulator"**.
2. **„The real Kaggle submission path talks to a gateway-backed Arcade"** — czyli `official_110()`
   **nie jest** ścieżką punktowaną; jest jej **lokalną imitacją**.
3. Cel modułu: *„so those failures can be reproduced **before submission**"* — **przed** submisją.

Oraz sama funkcja (`ca.py` L58-79, L144-155):

```python
L67-68  # Repeating a 25-game list to 110 entries therefore needs cloned IDs on
        # the SIMULATOR SIDE. The cloned IDs are stable, compact, and hyphen-free
L79     return [f"{clone_prefix}{i:03d}" for i in range(total_runs)]   # k000..k109
L151    """Expose 110 cloned official games for the submission-shaped benchmark."""
```

> **`official_110()` klonuje 25 gier PO TO, żeby lokalny symulator miał KSZTAŁT prawdziwej karty
> wyników (110 rozróżnialnych wpisów).** „submission-shaped" = **kształtem** przypomina submisję,
> nie **jest** submisją. Klony `k000…k109` istnieją „on the simulator side", bo prawdziwa karta
> wymaga **„no repeated game IDs"** — symulator musi je **podrobić**.
>
> Nazwa `make_benchmark_kaggle_official_110` jest myląca (słowa „kaggle" i „official") i to jest
> prawdopodobnie przyczyna pomyłki. **To jest dokładnie ta sama klasa błędu, którą dokumentuję
> od trzech dni: czytanie NAZWY zamiast docstringu/walidatora.** `SCOPE=run` (nazwa sugerowała
> zakres, walidator go nie miał), `concurrency=120` (liczba przepisana bez porównania warstw),
> `official_110` (nazwa sugeruje roster submisji, docstring mówi „local simulator").

**Dodatkowe dowody przeciwko twierdzeniu Smaka, wszystkie niezależne od tego pliku:**

| dowód | treść | źródło |
|---|---|---|
| docstring `competition_arcade.py` | *„hidden baselines"* — prawdziwa karta ma **ukryte** baseline'y, więc to nie są znane baseline'y 25 publicznych gier | `ca.py` L3-4 |
| zmierzony wynik | offline source-introspection BFS → **0.20**, *„Game sources don't exist in the rerun"* | `mayankraj4728` ref 57272788 |
| held-out | **0/113 poziomów** na 15 grach held-out vs **7/70** na 10 dostrajanych; *„The public-25 score over-predicts the leaderboard"* | `rasagyavatsal/arc-prize-2026-arc-agi-3` |
| opis rerunu | *„The rerun plays the **110 hidden games** through a **gateway:8001 sidecar**; the gateway computes the score file"* | j.w. |
| strona konkursu | *„Tasks take place in **hidden, interactive environments** … designed so systems **can't just memorize solutions**"* | `kaggle.com/…/overview` |

⚠️ **Uczciwe zastrzeżenie — czego NIE dowodzę.** Docstring mówi *„no repeated game IDs **within
that scorecard**"*, a nie wprost „110 gier mechanicznie różnych od 25 publicznych". Formalnie
zostaje więc szczelina: gateway mógłby serwować te same mechaniki pod różnymi ID. **Nie mogę tego
wykluczyć z samego docstringa.** Ale: (a) „hidden baselines" wskazuje na inne gry, (b) trzy
niezależne pomiary (0.20, 0/113, „110 hidden games") mówią, że dostrajanie na publicznych
**nie przenosi się**, (c) **ciężar dowodu spoczywa na tym, kto twierdzi „POTWIERDZONA W KODZIE
(nie hipoteza!)"** — a przytoczony kod jest jawnie lokalnym symulatorem.

> **Werdykt: twierdzenie Smaka jest co najmniej PRZESADZONE („nie hipoteza!" → jest hipotezą),
> a najprawdopodobniej FAŁSZYWE.** Gemma **nie** popełniła tego błędu — pisze *„Na rosterze
> prywatnym, jeśli nie ma w nim gier publicznych — 0"*, czyli traktuje roster jako **otwarty**.

### 2.1 Konsekwencja dla ich GO#1 — i jak ją rozstrzygnąć ZA DARMO

Ich `SYNC §13` i `REWIZJA GO`: *„**slot 30.10 = v13-MEGA (sufit 45-55**; kill-switche), fallback
31.10 = v12 (c45+fix). PC sweep 600 s przed submitem."*

**„Sufit 45-55" nie ma pokrycia w żadnym wariancie** (§1.3): nawet przy rosterze złożonym z klonów
playbook dokłada **~2,9 pkt**. Czyli GO#1 jest wydany na podstawie liczby, którą ich własny
recenzent (Gemma, w tym samym oknie czasowym) policzył jako ~2,9.

> **ROZSTRZYGNIĘCIE JEST DARMOWE I JUŻ JEST ZBUDOWANE: `roster_probe.jsonl`.**
> Probe istnieje w c45/v11/v13 i w `r085` zapisał 10 gier — ale **odpalił się w SMOKE na bundlu
> offline** (`OCENA-CODEX-7Z.md` §5). **Jeśli probe zapisze `game_id` w RERUNIE, jeden rzut oka
> na 110 identyfikatorów kończy spór**: `cn04…`/`tu93…`/`k037` → Smak ma rację i playbook żyje;
> cokolwiek innego → playbook jest wart 0 i v13 redukuje się do `CAP=0` + `PLAN_COMMIT`.
>
> **Problem: log rerunu jest dostępny TYLKO w przeglądarce właściciela konta** (ich `DECYZJA.md`:
> *„log reruna — dostępny wyłącznie w przeglądarce usera"*). **To jest konkretna rzecz do
> zrobienia przez usera: Kaggle → Submissions → ref 57737623 (v11) → Output → pobrać log i szukać
> linii `roster_probe` / `[finished] <game_id>`.** v11 **już leciał** na rerunie i dał 23.89 —
> jego log zawiera prawdziwe identyfikatory 110 gier. **Zero kosztu, zero slotu.**

### 2.2 Co w ich certyfikacji jest TRAFNE — kredyt

* **Punkty 1-3 i 5 są rzetelne**: 6/6 patchy na czystym bundlu r033 (`git archive` z HEAD, ekstrakcja
  ich własnym ekstraktorem), spatchowane drzewo się kompiluje, `standalone src/arc3_winpath.py`
  **byte-identical** ze spatchowanym, testy **12/12 + 6/6** (i uczciwie odnotowali, że wcześniejsze
  błędy to **braki piaskownicy**: PIL, arcengine na `sys.path`).
* **Złapali mój błąd i mieli rację:** *„„20 passów" w ANALIZA-23 ≠ kod frameworka (110 wpisów,
  round-robin; ~4.4/gra). **Mnożnik replay jest więc ~4.4×, nie 20×**."* — poprawne jako krytyka
  `ANALIZA-23.md` §4 (który mówił o 20 passach). **Ale nie ratuje to dźwigni**: przy `n_passes=1`
  na wpis i ~4.4 wpisu na grę, pamięć między **wpisami** działa tylko wtedy, gdy `WinPathStore`
  przetrwa między wpisami **i** dopasuje ID — czyli znowu wszystko sprowadza się do rosteru (§1.3, §2).
* **Uczciwie odnotowali moje zastrzeżenie:** *„Multi-zmiana na jeden slot (commit ON + cap OFF +
  winpath + dead-skip) = **atrybucja rozmyta**; kill-switche to łagodzą, a przy 4 slotach i progu
  49.85 **SUFIT jest ważniejszy niż czystość atrybucji**."* → **To jest świadomy trade-off, nie
  przeoczenie, i trzeba go zakwestionować merytorycznie, nie proceduralnie:** „sufit 45-55" jest
  właśnie tym, czego **nie ma** (§1.3), więc przesłanka trade-offu odpada. Zostaje sam koszt —
  rozmyta atrybucja przy 4 slotach i σ≈2,5–3,9.
* **Kalibracja smoke→LB zebrana rzetelnie:** *„v11 18.55→23.89 (**+5.3**); slotB brak smoke→1.18;
  v3 29.02→26.25 (**−2.8**). **Rozrzut duży — smoke>=26 jako bramka.**"* Czyli smoke **bywa**
  +5.3 i **bywa** −2.8 → **smoke jest wykrywaczem katastrof, nie estymatorem**. Zgadzam się i to
  jest spójne z moim `EKONOMIA-TOKENOW.md` (kalibracja ×0.828 jako przybliżenie) oraz z wnioskiem,
  że **23.89 nie dowodzi regresji v11**.

---

## 3. 7911f950 — trafna diagnoza, **zła wartość capu**, i walidacja, która nie rozróżnia

`arc-agi-3/MEGA-DIAGNOSIS.md` (270 ln, 29.10 17:04), z surowych `benchmark.json` trzech realnych
runów Kaggle (`r013-push`, `r015-push`, `r018-push`, gałąź `arena/98ddb59f-pokemon`).

### 3.1 ✅ Trafne i zbieżne z moim

* **„23 to nie regresja."** *„Między runami mamy **sd = 2,47 pkt**, a pojedyncza gra skacze średnio
  o **11,7 pkt**. 26,25 → 23 to **−1,3 sd**. Ten submit po prostu wylosował dolną część własnego
  rozkładu."* → **Niezależne potwierdzenie mojego §2.1** (σ=3.93 z 8 drawów publicznych Franzena,
  próg istotności +5). Dwa różne zestawy danych, ta sama konkluzja: **23.89 to draw, nie sygnał.**
* **Pokrycie, nie efektywność.** *„Nasza efektywność na poziomach, które kończymy, to **86–90%** —
  jesteśmy blisko sufitu. **Pokrycie to 29%** i to jest cały problem: kończymy ~3 z 7 poziomów."*
  *„Przy naszym budżecie akcji **sufit wynosi 18,7–31,9 pkt**. Jesteśmy na **79–100%** tego sufitu.
  **Dalsze strojenie strategii przy tym samym budżecie nie da 50 — nie ma z czego.**"*
  → **Zbieżne z Gemmą** („głębokość to 96% brakujących punktów, efektywność +3") **i z moim
  twierdzeniem o capie** („cała praca nad efektywnością ruchów jest warta 1.75 pkt łącznie").
  **Trzy niezależne rachunki, ten sam wniosek.**
* **Wagi są wypukłe:** dla gry 7-poziomowej poziom 7 = **25,0%** gry, poziom 1 = **3,6%**;
  *„Ostatnie dwa poziomy są warte więcej niż pierwsze trzy razem"*. → Zgodne z Gemmą („poziom k
  płaci k jednostek") i z oficjalną metodologią RHAE.

### 3.2 ❌ Cap punktacji: twierdzą **1.0**, źródła mówią **1.15** — i ich walidacja tego NIE rozstrzyga

Ich tekst: *„Nasza własna implementacja w `rust/src/score.rs` używała cap **1,15** (z arcagibook).
**Strona konkursu mówi 1,0.** Poprawione: `OFFICIAL_CAP = 1.0` … Cap 1,15 zawyżał każdy poziom,
na którym biliśmy człowieka, o do 32%. **Konsekwencja: nie ma sensu być szybszym niż człowiek.**"*

**Trzy źródła przeciwko ich „poprawce":**

| źródło | cap | status |
|---|---|---|
| `docs.arcprize.org/methodology` (pobrałem i zapisałem w `FAKTY-I-POMIARY.md`) | *„per-level cap **1.15×**"* | **oficjalna metodologia** |
| `taaf/game.py::_compute_final_score` (blob z bundla r033) — Gemma | `min(**115**, (baseline/actions)²·100)` | **kod, który faktycznie liczy wynik**, mirror `arc_agi.scorecard.EnvironmentScoreCalculator` v0.9.8 |
| Gemma `verify_scoring.py` | odtwarza **32/32** zapisanych `final_score` | **regresja na prawdziwych wynikach** |

**A ich własna tabela walidacyjna nie rozróżnia 1.0 od 1.15 — i to jest błąd metodologiczny.**
Sprawdziłem każdy z czterech wierszy:

| gra | poziomy | Σw ukończonych | Σw wszystkich | **cap ukończenia** | ich wynik | harness |
|---|---|---|---|---|---|---|
| su15 | 3/9 | 1+2+3 = 6 | 45 | 100·6/45 = **13,33** | 13,33 | 13,33 |
| ka59 | 3/7 | 6 | 28 | **21,43** | 21,43 | 21,43 |
| g50t | 2/7 | 1+2 = 3 | 28 | **10,71** | 10,71 | 10,71 |
| s5i5 | 3/8 | 6 | 36 | **16,67** | 15,67 | **16,67** |

**We wszystkich czterech przypadkach `score = min(raw, cap_uKOŃCZENIA)` i to CAP UKOŃCZENIA wiąże** —
więc wartość capu per-poziom (100 czy 115) **nie wpływa na wynik**. Wiersz s5i5 jest tego dowodem
wprost: ich formuła dała 15,67 (×94% efektywności), harness dał **16,67** = dokładnie cap ukończenia.
**Czyli zwalidowali formułę na danych, które nie rozróżniają dwóch kandydatów, i na tej podstawie
„poprawili" 1.15 → 1.0.**

Potwierdzenie na moich własnych danych z tej sesji (`r093` v11, `cn04`): `actions_per_level[0]=14`
przy `base_actions_per_level[0]=29` → `(29/14)²·100 = 429` → cap per-poziom wiąże **przy obu
wartościach**; `levels_completed=1`, `number_of_levels=6` → cap ukończenia `100·1/21 = 4,76`
= zmierzony `final_score` **4,76**. **100 i 115 dają tu ten sam wynik.**

> **Werdykt: cap per-poziom to 1.15 (115), nie 1.0.** Ich **wniosek** („nie ma sensu być szybszym
> niż człowiek") jest **prawdziwy**, ale **z innego powodu, niż podają**: nie dlatego, że cap wynosi
> 1.0, tylko dlatego, że **cap UKOŃCZENIA** (`100·Σw_uKOŃCZONYCH/Σw_WSZYSTKICH`) wiąże niemal zawsze,
> gdy agent jest szybszy od baseline. To jest dokładnie moje twierdzenie o capie
> (`FAKTY-I-POMIARY.md` L512-524, warunek `a ≤ 0.9325·b`) — i Gemma potwierdza je regresją 32/32.
>
> **Rozróżnienie ma znaczenie praktyczne:** przy capie 1.15 istnieje wąska klasa gier, w których
> bycie szybszym od człowieka **jednak** płaci (gdy cap ukończenia nie wiąże, np. gra ukończona
> w całości). Przy capie 1.0 nie płaci nigdy. **Gemma mierzy tę klasę jako +3,0 pkt** (r085:
> 26,78 faktycznie → 29,79 przy bazowych akcjach). Czyli **nie zero, jak wynikałoby z ich
> „poprawki"** — ale też tylko 3 pkt wobec ~64 pkt brakującej głębokości.

### 3.3 ✅ Ich przyczyna źródłowa — i dlaczego jest najważniejszym zdaniem tego dokumentu

> *„**Przyczyna źródłowa: 6034 akcje / 6034 decyzje = dokładnie 1,00 akcji na decyzję LLM.**
> Każdy pojedynczy ruch kosztuje pełny round-trip modelu (~14,4 s, ~700–1100 tokenów).
> **Podwojenie akcji na decyzję podnosi sufit do 51,3.**"*

⚠️ **Uczciwe zastrzeżenie: te 1,00 akcji/decyzję pochodzi z `r013/r015/r018`, czyli ze STARSZEJ
linii** (gałąź `arena/98ddb59f-pokemon`, era v2/v3), **nie z naszej szybkiej linii**. Mój pomiar
z `r019` (ta sama jednostka, trzy sesje domknięte co do jedności): **474 wywołań modelu / 2065 akcji
= 4,357 akcji na wywołanie (ważone) i 5,204 (średnia z gier)**, przy **3664,6 tok/wywołanie**
i **841,2 tok/akcję**.

**Czyli nasza linia już batchuje ~4,4–5,2 akcji na wywołanie, nie 1,00.** Ale **kierunek jest ten
sam i wniosek się utrzymuje po podstawieniu właściwej liczby:**

| linia | akcji/wywołanie | tok/akcję | akcji/grę | sufit/ projekcja |
|---|---|---|---|---|
| r013/r015/r018 (stara) | **1,00** | ~700–1100 | — | 18,7–31,9; podwojenie → **51,3** |
| **r019 / nasza szybka** | **4,357** (ważone) | **841,2** | **212,6** (r085) | mój model: **31,70**; Gemma: 200 akcji → **35,6** |
| cel 50+ | ~**8–9** | ~**400–500** | **~300** | Gemma: 300 akcji → **59,5**; mój model: 500 tok/akcję → **54,12** |

> **TRZY NIEZALEŻNE MODELE DAJĄ TEN SAM PRÓG: ~300 akcji na grę (z obecnych ~213), czyli ~1,4–1,5×.**
> * 7911f950: „podwojenie akcji na decyzję → sufit **51,3**"
> * Gemma: „**300 akcji → 59,5**"; „50+ jest funkcją **przepustowości**"
> * mój `tools/token_economy_model.py`: **500 tok/akcję → 350 akcji → sufit 54,12**; 444 → 394 akcji → 60,28
>
> **I wszystkie trzy mówią, że NIE chodzi o lepszy model:** Gemma zmierzyła, że 27B dał **0,27**
> przy 47,0 s/akcję (8B: 12,9 s/akcję) — *„większy model nie był za głupi, był za wolny"*.
> Zewnętrzne potwierdzenie z tabeli Tong Hui Kanga: **najszybszy serwer (1159 tok/s) ma najgorszy
> wynik (22.53), najwolniejszy (946) najlepszy (27.89)** — ale to dotyczy **serwingu**, nie
> **liczby akcji na decyzję**, więc nie jest sprzeczne: liczy się ile akcji agent wykona, a nie
> jak szybko serwer dekoduje.

---

## 4. Co z tego wynika: spór o v13 rozstrzygnięty

| twierdzenie | kto | werdykt |
|---|---|---|
| „dwie z trzech dźwigni 0006 są martwe w submisji" | **Gemma + ja, niezależnie** | ✅ **PRAWDA** (Gemma: arytmetyka w kodzie; ja: `n_passes=1` z komórki 25 + `benchmark.json` r085/r093) |
| „playbook 14/14, 184/184 hashy, na silniku, seed 1/2/7/42" | Gemma (reprodukcja a450b00f) | ✅ **PRAWDA** — sekwencje są prawdziwe |
| „playbook jest wart ~2,9 pkt średnio na 25 grach, 0 jeśli roster prywatny" | **Gemma** | ✅ **PRAWDA i to jest liczba, która kończy spór** |
| „widełki 35–50+ z README" | a450b00f | ❌ **„nie mają pokrycia w artefaktach"** (Gemma); ~2,9 w najlepszym wariancie (§1.3) |
| „roster = 110 round-robin klonów 25 gier, POTWIERDZONE W KODZIE (nie hipoteza!)" | **Smak** | ❌ **NADATRYBUCJA lokalnego symulatora na ścieżkę punktową** (§2). Docstring: *„Local … simulator"*, *„real Kaggle submission path talks to a **gateway**-backed Arcade"*, *„before submission"* |
| „GO#1: v13-MEGA na slot 30.10, sufit 45-55" | **Smak** | ❌ **przesłanka („sufit 45-55") nie istnieje**; zostaje rozmyta atrybucja przy 5 zmianach i 4 slotach |
| „23 to nie regresja, −1,3 sd" | 7911f950 | ✅ **PRAWDA**, zbieżne z moim σ=3.93 |
| „cap per-poziom = 1.0, nie 1.15" | 7911f950 | ❌ **1.15** (oficjalna metodologia + `taaf/game.py` + regresja 32/32); ich walidacja nie rozróżnia (§3.2) |
| „1,00 akcji/decyzję to bottleneck" | 7911f950 | ⚠️ **prawda dla STAREJ linii** (r013/r015/r018); nasza szybka linia ma **4,357**. Kierunek i wniosek zostają (§3.3) |
| „głębokość = 96% brakujących punktów, efektywność +3" | **Gemma** | ✅ **PRAWDA**, zbieżne z moim twierdzeniem o capie (1.75 pkt) i z 7911f950 (86–90% efektywności, pokrycie 29%) |
| „50+ jest funkcją przepustowości, nie mądrzejszego modelu" | **Gemma** | ✅ **PRAWDA**, trzy niezależne modele dają próg ~300 akcji/grę (§3.3) |

---

## 5. ⚠️ TO ODWRACA CZĘŚĆ MOJEJ WŁASNEK REKOMENDACJI: `PLAN_COMMIT="1"` jest główną dźwignią

W `OCENA-V13-MEGA.md` §7 rekomendowałem `PLAN_COMMIT="0"` na slot najbliższy (*„niezmierzone;
v11 pokazał, że 0005 nie jest obojętne nawet przy `"0"`"*) i test osobno dopiero po 31.10.
**Trzy pomiary z §3.3 zmieniają tę kolejność**, i zapisuję to jako korektę własnej rekomendacji:

**Skoro bottleneck to liczba akcji na grę (~213 → ~300 potrzebne), a akcje na grę ogranicza
liczba akcji na decyzję LLM, to `commit(plan)` jest JEDYNĄ istniejącą dźwignią, która celuje
dokładnie w to.** Z `POROWNANIE-V11.md`: `commit(plan)` wykonuje plan krok po kroku z kontrolą
oczekiwanego stanu po każdym kroku (`level`/`board_changed`/`step`/`digest`/`cells`), stop przy
pierwszej rozbieżności, `max_actions=40`, **4 ms → 146 ms**, plan 20-akcyjny ≈ **3 s**,
**12/12 testów**. Plan 20 akcji w 3 s wobec ~14,4 s na pojedynczy ruch to jest **~5× tańsza akcja**.

**Dlaczego zmieniłem zdanie, uczciwie:**
* **za:** trzy niezależne rachunki wskazują ten sam bottleneck; `commit(plan)` jest zaimplementowany
  i przetestowany (12/12 na spatchowanym drzewie, niezależnie potwierdzone przez Gemmę i Smaka);
  to jedyna dźwignia v13, która **nie jest** martwa (`n_passes=1`) ani zależna od rosteru;
  Gemma i 7911f950 zgodnie mówią, że dalsze strojenie **przy tym samym budżecie akcji** nie da 50
* **przeciw:** nigdy nie zmierzone na Kaggle; ich własne v6 **23.94** < v2 **24.66** pokazuje, że
  nowa warstwa potrafi kosztować; przy σ≈2,5–3,9 **jeden** slot nie rozstrzygnie, czy +8 to efekt
  czy draw
* **rozstrzygnięcie:** dlatego **dwa sloty na tę samą konfigurację**, nie jeden (§6). To jest
  dokładnie metoda, którą Gemma zastosowała świadomie (control run 1 i control run 2 → pomiar
  szumu 39.84 vs 38.12) i którą mayankraj4728 zaleca jako „the best tool left: submit the safe
  release several times"

**Ale NIE w pakiecie z winpathem i dead-skipem** — bo wtedy wynik będzie nieinterpretowalny,
a to jest błąd, który już kosztował nas diagnostykę v11.

---

## 6. Plan na 4 sloty (30.10, 31.10, 1.11, 2.11) — poprawiony

Sloty zużyte: 28.10 = v11 A (**23.89**), 29.10 = slot B stock 27B (**1.18**). Zostały **4**.

| slot | konfiguracja | hipoteza (JEDNA) | dlaczego |
|---|---|---|---|
| **30.10** | c45 − 0005-martwe-warstwy: **`PLAN_COMMIT="1"`** + **`CAP=0`** + `WINPATH="0"` + `DEAD_SKIP="0"` + `EXPOSE_UNDO="on"` + concurrency 10 | **batching akcji na decyzję podnosi liczbę akcji/grę** | jedyna dźwignia celująca w zmierzony bottleneck (§3.3, §5). `CAP=0` to **usunięcie** zmierzonego −0.43/−2.24, nie nowa hipoteza. `WINPATH`/`DEAD_SKIP` wyłączone, bo **martwe** (§1.1) |
| **31.10** | **TA SAMA konfiguracja ponownie** | „wynik z 30.10 to draw, nie pomiar" | przy σ≈2,5–3,9 **dwa drawy** tego samego configu to minimum, żeby cokolwiek wiedzieć. Metoda Gemmy (control 1 vs control 2 → 39.84/38.12) |
| **1.11** | lepsza z dwóch; jeśli obie < 26 → **kontrola: `PLAN_COMMIT="0"`** z resztą bez zmian | atrybucja: czy `commit()` pomógł, czy zaszkodził | dopiero trzeci punkt pozwala oddzielić efekt od szumu |
| **2.11** | **select best** z dwóch dozwolonych finalnych | zabezpieczenie najlepszego drawa | Kaggle pozwala wybrać 2 submisje do punktacji prywatnej |

**Trzy rzeczy darmowe, do zrobienia PRZED slotem 30.10:**

1. **User: pobrać log rerunu ref 57737623** (Kaggle → Submissions → Output) i wyciągnąć
   identyfikatory gier + `roster_probe`. **To kończy spór o roster zerem kosztu** (§2.1) —
   i rozstrzyga, czy kiedykolwiek warto włączać `ARC3_WINPATH="1"`.
2. **Gemma: `analyze_run.py` na `benchmark.json` z ostatniego rerunu** — ich własny punkt 6:
   *„1 polecenie, bez GPU i bez slotu"*. Mediana akcji **< 300** → priorytet przepustowość
   (czyli `PLAN_COMMIT`); **≥ 300** i głębokość nadal ≤2 → priorytet polityka (czyli `PLAN_COMMIT`
   **nie** jest odpowiedzią i trzeba innego planu). **To jest bramka decyzyjna dla slotu 30.10.**
3. **PC sweep 600 s (`pc-sweep-pack`, 5950X)** — Smak i a450b00f oba to proponują. **Warto zrobić,
   ale tylko jeśli §2.1 rozstrzygnie roster NA TAK.** Jeśli roster jest prywatny, większy playbook
   jest wart **0** (§1.3) i te 600 s × 25 gier lepiej wydać na test logiki `commit(plan)` na CPU.

**Czego NIE robić** (zmierzone jako ujemne lub martwe):
* ❌ **27B / większy model** — zmierzone **1,18** (slot B) i **0,27** (v14 smoke); 47,0 s/akcję
  wobec 12,9 s/akcję dla 8B. *„Większy model nie był za głupi — był za wolny."*
* ❌ **jakakolwiek zmiana parametrów serwingu** (strumienie, MEMFRAC, kontekst, speculative steps,
  temperatura) — **−7 do −8** na zbiorze ukrytym; błąd śmiertelny #13
* ❌ **`ARC3_WINPATH="1"`** przed rozstrzygnięciem rosteru — martwe przy `n_passes=1`, a playbook
  wart ~2,9 pkt nawet w najlepszym wariancie
* ❌ **pamięć rozwiązanych poziomów** — LB średnia ≈25,2 vs 27,9 bez
* ❌ **search offline / playbook jako źródło punktów** — 0.20, 0/113 na held-out
* ❌ **stackowanie pięciu zmian** — błąd śmiertelny #8, już kosztował nas diagnostykę v11

**Cel pozostaje: średnia ~29–30, srebro ≈32.33.** `PLAN_COMMIT="1"` jest **jedyną** dźwignią
z realną szansą na więcej (~35+ przy projekcji Gemmy 300 akcji → 59,5 jako **górnym** ograniczeniu),
ale **50+ wymaga ~300 akcji/grę trwałe**, a to jest zmiana przepustowości całego stosu, nie jeden
przełącznik — i nikt tego nie zmierzył w 4 dni.

---

## 7. Co ten dokument zmienia w moich poprzednich

| dokument | korekta |
|---|---|
| `OCENA-V13-MEGA.md` §7 | **ODWRÓCONE**: rekomendowałem `PLAN_COMMIT="0"` na najbliższy slot. Trzy niezależne pomiary bottlenecku (§3.3) sprawiają, że `commit(plan)` jest **główną** dźwignią, nie odłożoną. Nowy plan: §6 |
| `OCENA-V13-MEGA.md` §3.2 | moje zastrzeżenie „0.20 dotyczy `find_game_source`, nie v13" **pozostaje**, ale Gemma daje brakującą liczbę: playbook = **2,90 pkt średnio**, niezależnie od mechanizmu dopasowania |
| `OCENA-CODEX-7Z.md` §5 | roster **nadal otwarty** — i teraz wiadomo, **jak go zamknąć za darmo**: log rerunu ref 57737623 (§2.1) |
| `FAKTY-I-POMIARY.md` §2 | twierdzenie o capie **potwierdzone trzeci raz, niezależnie**: Gemma `min(115,…)` z `taaf/game.py` + regresja **32/32** na prawdziwych `final_score`. Plus **nowa reguła**: cap **UKOŃCZENIA** (`100·Σw_uK/Σw_all`) wiąże niemal zawsze i to on, a nie cap per-poziom, zeruje wartość efektywności |
| `EKONOMIA-TOKENOW.md` §11 | próg **~300 akcji/grę** dla 50+ potwierdzony **trzema niezależnymi modelami** (mój 500 tok/akcję → 350; Gemma 300 → 59,5; 7911f950 podwojenie → 51,3) |
| `RESEARCH-LIDERZY-50PLUS.md` §3.1 | „szybkość serwera nie różnicuje" **pozostaje prawdziwe**, ale wymaga rozróżnienia: **tok/s serwera** ≠ **akcje na decyzję agenta**. Pierwsze nie różnicuje (946 → 27.89 vs 1159 → 22.53), **drugie jest bottleneckiem** (§3.3) |
| `README.md` | dodać: próg ~300 akcji/grę, playbook ~2,9 pkt, `official_110()` = **lokalny symulator** (nie roster), cap ukończenia jako właściwy powód zerowej wartości efektywności |
