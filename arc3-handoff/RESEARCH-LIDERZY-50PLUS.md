# Jak liderzy robią 50–75 punktów — i co z tego jest dostępne dla nas

**Data:** 28.10.2026 ~23:40 UTC · **Pytanie usera:** „skoro dla ciebie problemem jest 50 pkt
(ilość notebooków nie ma nic do wyniku!), to jak lider uzyskał 75? dowiedz się tego!"

> **User ma rację i mój argument był wadliwy.** W `DIAGNOZA-23-89-I-PLAN.md` §5 napisałem, że 50+
> wymaga **+6.4 σ** od średniej bazy. To dowodzi, że **50 nie da się WYLOSOWAĆ na obecnej bazie**.
> **Nie dowodzi, że 50 jest nieosiągalne** — inny system ma inną średnią, a liczba wpisów
> (Turducken 212, Tufa 174) mówi tylko o tym, ile razy ktoś **losował**, nie o tym, jaką ma
> średnią. Poprawiam poniżej: rozdzielam to, co **opublikowane i odtwarzalne**, od tego, co
> **nieopublikowane**.

---

## 1. Najważniejsza pojedyncza liczba: opublikowana czołówka ma **22.53–27.89**

Źródło: `kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/744792` —
**Tong Hui Kang (26. miejsce), „Comparing the Milestone 2 winning solutions"**, 15 komentarzy,
szczegółowa tabela porównawcza trzech zwycięzców Milestone 2 z linkami do notebooków, repo,
writeupów i konkretnych linii kodu. **To jest najlepszy publiczny dokument techniczny o tym konkursie.**

Wszyscy trzej uruchamiają **Duck harness Tufa Labs na TAAF** i serwują **Qwen3.8-Flash-Next**:

| | **dfranzen** | **lordhansolo** | **sirikilohit (rellik13)** | **MY (c45/v11)** |
|---|---|---|---|---|
| **Public LB score** | **27.89** | **23.84** | **22.53** | **26.25 / 23.89** |
| Peak decode tok/s | **946** ← najwolniejszy | 1 135 | 1 159 ← najszybszy | ~603 (nasz pomiar) |
| KV dtype | fp8_e4m3 | fp8_e4m3 | fp8_e4m3 | fp8_e4m3 |
| KV pool (tokenów) | **1 011 264** | 1 417 100 | 1 004 288 | **1 011 264** ← identyczne |
| Context (server/harness) | **139 264 / 131 072** | 147 072 / 127 488 | **69 632 / 69 632** | (116+12+8)×1024 |
| Games streaming at once | **10** (all 110 live) | 14 (14 live) | 16 (28 live) | 10 smoke / 120→**10** rerun |
| GPU memory left free | 4.25 GB | 1.90 GB | 3.17 GB | — |
| Offloaded memory | 95.37 GB | 96.55 GB | 95.68 GB | — |
| Temperature | 0.7 | 0.6 | 0.6 | 0.7 |
| Server | SGLang Pennyroyal v2.5.3 | vLLM 0.29.1rc1 | SGLang Pennyroyal v2.5.0 | SGLang |
| Budget per game | slot do następnego trima (~59k nowego kontekstu), potem **re-queue wg priorytetu** | cap **3 918 s**/grę, 8 fal po 14 na 110 gier | **bez capu**: wspólna pula ~31k s, najpierw 2 400 s/grę, potem **UCB scheduler** | — |

> **WNIOSK, KTÓRY ZMIENIA OBRAZ: jesteśmy W PAŚMIE ZWYCIĘZCÓW MILESTONE 2.**
> Nasz najlepszy wynik **26.25** i obecny **23.89** mieszczą się między **22.53** a **27.89**.
> Nasz KV pool (**1 011 264**) jest **identyczny** z dfranzenem, czyli z najlepszym opublikowanym
> notebookiem. Nasza linia c45 **to jest** dfranzen (opis ref 57629847: „fast-line … Franzen-lineage").
>
> **Nie jesteśmy „słabi". Jesteśmy na poziomie opublikowanej czołówki.** Luka do 75.56 nie jest
> luką w dostrajaniu harnessa — bo dostrajanie harnessa rozstrzyga między **22.53 a 27.89**,
> czyli o ~5 punktów, nie o ~50.

---

## 2. Co zrobiła Chen — i dlaczego nie możemy tego powtórzyć

### 2.1 Trajektoria (posty `@arcprize` na X + `arc.markbarney.net/arc-leaderboards`)

| data | wynik Chen | źródło |
|---|---|---|
| 28.09 | **28.34** (nowe 1. miejsce) | post `@arcprize` |
| 09.10 | **59.17** (wyprzedziła Tufa Labs) | post `@arcprize` |
| 20.10 | 67.49 | tracker |
| 25.10 | 68.21 → **71.48** | post `@arcprize` 26.10: „jumped from 67% > 71% and has reclaimed 1st place" |
| 27.10 | **75.56** | `r101-lb` (28.10 23:01 UTC) |

**Kluczowy jest skok 28.34 → 59.17 w 11 dni (+30.8).** Dla porównania: **cała** opublikowana
rozpiętość między zwycięzcami Milestone 2 to 22.53–27.89, czyli **5.4 pkt**. Skok Chen jest
**5.7× większy niż wszystko, co opublikowano**, i nastąpił **w 11 dni**.

Komentarz obserwatora z 28.09 (na X): *„The top two are pulling away. Both over 27% and the next
three are bunched around 21. **Any hint yet on what Yi-Chia Chen changed?**"* — czyli już wtedy
nikt nie wiedział.

### 2.2 Chen **świadomie odmówiła** open-sourcingu

Z jej własnego posta w dyskusji ARC-AGI-3 (21 dni temu), dosłownie:

> *„I haven't decided yet whether I'll open-source my solution for the second milestone, but I'll
> let everyone know my final decision here by September 29… **Update: Given the complexity of the
> process, I've decided not to open-source my solution for the second milestone.**"*

Potwierdzenie z `mayankraj4728/ARC-AGI-3-2026` §7.2b (deep research 26.10):

> *„**Top ARC-AGI-3 teams (Tufa, Yi-Chia Chen, Turducken, NVARC3, …) have published nothing**;
> they release after the deadline."*

§7.3: *„**Teams far above us** (Tufa Labs 68.9, Yi-Chia Chen 67.5, Turducken 52.8, mtg 50.4, …)
have **not published** their current methods."*

**Kim jest Chen:** `kaggle.com/threerabbits` — National Taiwan University & Waseda University,
**Fields Model Initiative**, Taipei, 41 postów dyskusyjnych, **1. miejsce**. Jej pozostałe posty
dotyczą innej rywalizacji (dowody matematyczne IMO): system ról **Prover / Verifier / Refiner /
Selector** wytrenowany tak, że *„the model was already quite strong on easier problems, but the
difference became much more visible on medium and hard IMO-style problems"*, z *„compressed 32B
student"*. Czyli to osoba, która **trenuje i dystyluje modele**, a nie tylko stroi harness.

> **Odpowiedź na pytanie usera: NIE WIEMY, co zrobiła Chen — bo ona i cała czołówka nie
> opublikowali nic i opublikują dopiero po deadline.** To nie jest moja niechęć do sprawdzenia;
> sprawdziłem dyskusję, posty `@arcprize`, trackery, 4 publiczne repo i research log zespołu,
> który zrobił 4 rundy researchu po ~100 notebooków.
>
> **Co DA się ustalić: warstwy.** Rozdzielam to, co zmierzone, od tego, co domniemane (§3–§4).

---

## 3. Warstwa opublikowana: oś rywalizacji to **inżynieria inferencji**, ale NIE szybkość

Cztery cytaty od ludzi z czołówki, z tej samej dyskusji:

* **Son Pham (3. miejsce):** *„So many token wizardry :D. A bit unfortunate that we only figured
  out how important these are **late in the game**."*
* **xz (4. miejsce):** *„Congrats to the winners! **Very good inference engineering** :)"*
* **Nhan Duc Nguyen (20.):** *„Since all the public one have quite the same inference improvement,
  maybe **next phase will focus more on harness** (or we have new OSS model release 😂)"*
* **Tong Hui Kang (26.):** *„I should have majored in inference engineering when I was in college"*

### 3.1 ❌ Szybkość NIE jest różnicująca — dowód z tabeli

| | peak decode tok/s | Public LB |
|---|---|---|
| dfranzen | **946** ← najwolniejszy | **27.89** ← najlepszy |
| lordhansolo | 1 135 | 23.84 |
| sirikilohit | **1 159** ← najszybszy | **22.53** ← najgorszy |

**Zależność jest ODWROTNA.** Najszybszy serwer ma najgorszy wynik. Czyli **„zróbmy to szybciej"
nie jest drogą** — i to jest **niezależne, zewnętrzne potwierdzenie** mojego wniosku z
`OCENA-RUST-BENCH.md` §6.1 i `DIAGNOZA-23-89-I-PLAN.md` §6.1, że Rust+rayon nie da punktów.
Teraz mam dowód z czołówki, nie tylko z rachunku 1 : 34 142.

### 3.2 ✅ Różnicujący jest stosunek **kontekst ↔ współbieżność** — i MY JESTEŚMY PO DOBREJ STRONIE

* **dfranzen:** największy kontekst (**139 264 / 131 072**), **najmniej** gier współbieżnych (10),
  wszystkie 110 żywe, **re-queue wg priorytetu** → **27.89**
* **sirikilohit:** kontekst **o połowę mniejszy** (69 632), 16 strumieni / 28 gier żywych → **22.53**

**rellik13 (= sirikilohit) sam to diagnozuje, i to jest najważniejszy cytat tego dokumentu:**

> *„Looks like I took a **wrong turn with the context vs concurrency tradeoff**. For the most part,
> I thought the **decode throughput was the bottleneck**, so I kept the **concurrency high**. The logs
> showed me that the **kv pool sat somewhere between 91-97% full and requests queued for cache
> space**, so the **memory was the actual limit** but I realized this a bit too late."*

> **To jest TA sama pułapka, w którą my wpadliśmy z `concurrency=120` przy `MAXREQ=10`**
> (`POROWNANIE-V11.md`, `FAKTY-I-POMIARY.md` L629/L636/L638). On myślał, że ogranicza throughput,
> a ograniczała pamięć KV; my mieliśmy frontend 12× większy niż backend. **Ta sama klasa błędu:
> optymalizacja zasobu, który nie jest wiążący.** Różnica: on miał 16 strumieni i przeżył (22.53),
> my mieliśmy 120 i dostaliśmy **0.00**.
>
> Reguła, którą z tego wyciągam i która powinna trafić do `FAKTY`:
> **najpierw zmierz, który zasób jest nasycony (KV pool %, kolejka, tok/s), dopiero potem go
> zmieniaj.** Nasz `serve.log` (1 143 523 B w `r093`) ma te dane i **nie został sparsowany**.

### 3.3 Zmierzona dźwignia +8 pkt — i dlaczego jest dla nas **już zamknięta**

> **rellik13:** *„the **fp8 kv was implemented yesterday** and i spent the free memory on history
> (the **trims moved from 37k→27k to 57k→45k**). I guess **this alone took the score from 14.5
> to 22.5**."*

**+8 punktów z jednej zmiany inferencyjnej** (fp8 KV → połowa pamięci vs bf16 → dłuższa historia
przed trimem). To jest największa pojedyncza zmierzona dźwignia, jaką znalazłem w całym researchu.

**Ale: tabela pokazuje `KV dtype: fp8_e4m3` u WSZYSTKICH TRZECH zwycięzców — i u nas też.**
Nasz KV pool 1 011 264 jest identyczny z dfranzenem. **Ta dźwignia jest już przez nas zużyta.**

Pozostaje wariant, który zgłasza **xz (4. miejsce)**:

> *„I ablated it a while ago and found **very little NLL penalty to use nvfp4 kv** and had been
> using it since. On the other hand, I just ran a token matched level completions against the
> milestone solutions and found mine to be **less action-efficient for some reason**. I am wondering
> if this has to do with the **kv quant** or just the harness prompts."*

nvfp4 KV zwolniłoby **4×** zamiast 2× pamięci. **Ale**: (a) xz jest 4. i **sam nie wie**, czy jego
niższa efektywność akcji to wina kwantyzacji KV; (b) rellik13 odpowiada, że przy krótkich
kontekstach test NLL *„might not show what happens at 60k-100k tokens where we actually run"* i że
rozstrzygnąłby to *„token-matched run with only kv dtype changed"*; (c) to wymaga przebudowy
bundla 185 GB i nowego smoke; (d) przy ±4 szumu i 1 submisji/dzień **nie da się tego zweryfikować
w 4 dni**. **Oceniam: wysokie ryzyko, nie do zwalidowania przed 2 XI.**

---

## 4. ✅ ZNALAZŁEM JEDNĄ DARMOWĄ RZECZ: nasz harness **wprowadza agenta w błąd**

Druga część cytatu rellik13 — i to jest **najbardziej wykonalna rzecz w tym dokumencie**:

> *„Some harness changes that helped were simply to **not mislead the agent**. (For ex:
> **UNDO instead of ACTION7**, **"level restarted" instead of "game over"**, **removing lines that
> tell the agent to ignore the budget bar**, etc etc.)"*

Sprawdziłem wszystkie trzy w `patches/0000-franzen-harness-changes.patch` (498 780 B):

### 4.1 `EXPOSE_UNDO` — **mamy ustawienie legacy, które reklamuje akcję odrzucaną** ❗

W patchu istnieje funkcja (`action_names.py`, L24-51):

```python
def undo_exposure_mode() -> str:
    """Read at call time; unset/invalid values preserve the original wiring.

    tufa: advertise ACTION7 verbatim but reject execution (legacy behavior).
    off:  hide ACTION7/UNDO and reject execution.
    on:   advertise UNDO and accept either name for engine ACTION7.
    """
    mode = os.environ.get("EXPOSE_UNDO", "tufa").strip().lower()
    return mode if mode in {"tufa", "off", "on"} else "tufa"
```

oraz w `to_engine_action`:

```python
if raw in {"ACTION7", "UNDO"}:
    return "ACTION7" if undo_exposure_mode() == "on" else None
```

**Czyli przy wartości domyślnej `tufa`: agent widzi w kontekście `ACTION7`, próbuje go użyć,
a `to_engine_action` zwraca `None` — akcja jest ODRZUCANA.** To jest dokładnie „misleading the
agent": harness reklamuje działanie, którego nie wykona.

**Nasz dump env z obu logów (`arc3-duck-c45.log` i `arc3-duck-v11.log`) zawiera 10 zmiennych:**
`ARC3_ABANDON_MIN_LEVELS`, `ARC3_ABANDON_TOKENS`, `ARC3_EXPERIMENT_HINT`, `ARC3_LEVEL_MIN_DONE`,
`ARC3_LEVEL_NOTES`, `ARC3_LEVEL_RESETS_MAX`, `ARC3_LEVEL_TOKEN_CAP`, `ARC3_STUCK_AUDIT_TOKENS`,
`ARC3_WORLD_MODEL`, `ARC3_WORLD_MODEL_NUDGE`.

> ❗ **`EXPOSE_UNDO` NIE JEST USTAWIONE → działa `tufa` → agent jest wprowadzany w błąd.**
>
> **POPRAWKA: `EXPOSE_UNDO="on"`.** Koszt: **jedna zmienna env**. Ryzyko: zerowe po stronie
> serwingu (to nie jest parametr inferencji, więc nie dotyczy ostrzeżenia „−7 do −8").
> Wymaga **tylko** weryfikacji, że `on` faktycznie reklamuje `UNDO` i przyjmuje obie nazwy —
> czyli test logiki w `action_names.py`, wykonalny **na CPU, bez GPU**.
>
> **To jest ta sama klasa buga co `SCOPE=run` i `concurrency=120`**: zmienna, której **domyślna
> wartość po cichu zachowuje legacy zachowanie**, a dokumentacja tego nie mówi. Trzeci raz
> w tym konkursie. Reguła: **dla każdej zmiennej env wyciągnąć z patcha jej DOMYŚLNĄ wartość
> i walidator, zanim uznamy konfigurację za kompletną.**

### 4.2 „game over" → „level restarted" — **częściowo już naprawione** ⚠️

Wystąpień: **14**. Ale patch zawiera już tekst korygujący (L5653-5655):

```
"GAME OVER occurred during the previous sequence. This means the "
"already been automatically RESET: the current level restarted from "
```

Czyli dfranzen mówi „GAME OVER", a **natychmiast wyjaśnia**, że poziom został zresetowany.
Zostaje jednak surowy werdykt pokazywany agentowi (L4402, L8143):

```python
verdict = "GAME OVER (attempt ended immediately after this action)"
```

**Ocena: częściowo zaadresowane. Zmiana „GAME OVER" → „LEVEL RESTARTED" w werdykcie jest tania,
ale NIE jest to czysta jedna zmienna** — wymaga edycji patcha, a my patchy nie możemy dotykać
bez zgody (BEZPIECZNIK) i bez ponownego smoke. **Priorytet niższy niż §4.1.**

### 4.3 „ignore the budget bar" — **NIE MAMY tego, już czyste** ✅

`grep -ci "ignore the budget"` → **0 wystąpień**. Natomiast dfranzen robi **odwrotność**:
aktywnie uczy agenta czytać pasek budżetu (L5666: *„inspect the budget bar in the death frame.
BAR RULE: the bar …"*, L5028, L5056). Jedyna uwaga (L612) ostrzega, że komponenty `resized`
*„can include backgrounds and budget bars"* — czyli żeby pasek nie był brany za obiekt gry.

**Trzecia poprawka rellik13 jest u nas już spełniona. Nie ma czego robić.**

---

## 5. ⚠️ MUSZĘ SKORYGOWAĆ WŁASNE TWIERDZENIE o „równym przydziale czasu"

W `DIAGNOZA-23-89-I-PLAN.md` §2.3 napisałem: *„Nasza konfiguracja (c45 i v11) daje każdej grze
równy czas: 10 gier × 2880 s"*, powołując się na ich błąd śmiertelny #6 (*„Never use uniform time
allocation. Priority scheduling (D′) is essential"*).

**To było za mocne i prawdopodobnie błędne dla ścieżki rerun.** Sprawdziłem patch:

```
L261: diff --git a/ARC3-Inference/inference/agent/priority_scheduler.py
L346: +def priority_value(
L1391-1392: +from inference.agent.priority_scheduler import (
                ProgressPace, PrioritySnapshot, parse_total_levels, priority_value,
L3135: +# The maximum _game_priority is about 1,325.
L3192: +def _priority_refresh_enabled() -> bool:
```

> **Nasz harness MA `priority_scheduler.py`** — plik, funkcję `priority_value()`, import
> i `_priority_refresh_enabled()`. Tabela Tong Hui Kanga potwierdza, że u dfranzena gra
> *„keeps its slot until its next history trim (~59k tokens of new context), then is **re-queued
> by priority** (level, levels left, actions and tokens spent on the level, tail fade)"*.
>
> **Czyli „10 gier × 2880 s" to jest konfiguracja SMOKE, a nie rerun.** W rerunie 110 gier
> idzie przez scheduler priorytetowy, który już tam jest. **Wycofuję §2.3 w części dotyczącej
> rerunu.** To **szósta** korekta mojego własnego dokumentu w tej sesji.
>
> **Co zostaje otwarte i jest warte sprawdzenia:** czym jest „D′" u mayankraj4728, skoro dfranzen
> **już ma** scheduler priorytetowy? Ich zmierzone +2 do +3 (26 → 29) musi więc być **czymś innym**
> niż samo włączenie priorytetu — prawdopodobnie inną funkcją priorytetu albo innym przydziałem
> fal. **Nie wiem i nie zgaduję.** Do sprawdzenia: czy `_priority_refresh_enabled()` jest u nas
> włączony i jaka jest nasza funkcja `priority_value` vs ich D′.

**Uwaga, która zostaje ważna niezależnie od tego:** `ABANDON` z mojego patcha jest **nieodwracalny**
i wyrzuca grę z budżetem (§2.2 diagnozy), podczas gdy scheduler dfranzena grę **kolejkuje ponownie**.
To rozróżnienie jest prawdziwe i to jest powód, żeby kap wyłączyć.

---

## 6. Warstwa nieopublikowana: co prawdopodobnie daje 28 → 75

Domniemania, **oznaczone jako domniemania**, z tym co za nimi stoi:

| hipoteza | dowód pośredni | ocena wykonalności dla nas w 4 dni |
|---|---|---|
| **Lepszy/nowszy model open-weight** | parthenos (976.): *„everybody waiting for **qwen 4**"*; Nhan Duc Nguyen: *„or we have new OSS model release 😂"*; Tufa M1: *„The gains came from multimodality and **better base models**, not hand-built tools"* | ❌ wymaga bundle 185 GB, nowego smoke, i nie ma gwarancji że model istnieje publicznie |
| **Test-time training / RL na grze** | `medium.com/@ccro8990`: Tufa *„focus heavily on **Test-Time Training (TTT)** — forcing an AI model to learn 'how to learn' the logic rules of a grid after it sees the test puzzle"*; linia Tufa to **StochasticGoose = CNN + RL** (1. miejsce preview 12.58%), a Duck to jej następca | ❌ wymaga GPU-godzin na trening **w trakcie** biegu 9 h; nasza kwota 30 h/tydz. już raz się wyczerpała |
| **Fine-tuning / dystylacja pod rozkład gier** | Chen pracuje w **Fields Model Initiative**, jej posty opisują system ról Prover/Verifier/Refiner/Selector i *„compressed 32B student"* — czyli **trenuje modele**; jej „complexity of the process" jako powód braku open-source | ❌ to tygodnie pracy i dane, nie 4 dni |
| **Lepsza funkcja priorytetu / scheduler pasmowy** | sirikilohit ma **UCB scheduler** (*„gives extra slices to games clearing the most levels per token"*), lordhansolo cap 3 918 s i 8 fal, dfranzen re-queue wg priorytetu z tail-fade | ⚠️ **JEDYNA realna kategoria** — ale wymaga pomiaru, a przy ±4 szumu i 1 slocie/dzień nie da się zweryfikować |
| **Drobiazgi harnessa („nie myl agenta")** | rellik13 wprost; u nas `EXPOSE_UNDO` = legacy | ✅ **WYKONALNE — §4.1** |

> **Uczciwa konkluzja: luka 28 → 75 to inna klasa systemu, nie inne ustawienia.**
> Opóźnienie Chen (28.34 → 59.17 w 11 dni) jest **5.7× większe** niż cała opublikowana
> rozpiętość między zwycięzcami M2 (5.4 pkt). Zespoły na 50+ **nie opublikowały nic** i
> opublikują po deadline. Chen odmówiła wprost. **Nie ma źródła, z którego moglibyśmy to wziąć.**

---

## 7. Co z tego wynika — poprawiony plan

**Zmieniam rekomendację z `DIAGNOZA-23-89-I-PLAN.md` §8 w jednym punkcie i dodaję jeden.**

| slot | data | konfiguracja | hipoteza (JEDNA) |
|---|---|---|---|
| **1** | 29.10 | **c45 minus 0005** + **`ARC3_LEVEL_TOKEN_CAP=0`** + **`EXPOSE_UNDO="on"`** + **4 safety fixes** | usunięcie capa i przestanie mylić agenta przywraca/podnosi bazę; safety usuwa 0.00 |
| **2** | 30.10 | **ten sam config ponownie** | poprzedni wynik to draw → μ z dwóch punktów |
| **3** | 31.10 | **+ jedna zmiana schedulera** (tylko jeśli §5 domknie, czym D′ różni się od `priority_scheduler.py`) | priorytet ponad dfranzenowski |
| **4** | 1.11 | najlepszy z 1–3 ponownie | szansa na draw ≥ 32.33 |
| **5** | 2.11 | select best | zabezpieczenie |

**Zasada, którą narzuca §1–§3:** przy ±4 szumu i progu istotności +5 pkt **nie da się w 4 dni
zweryfikować więcej niż jednej hipotezy na slot**. Więc slot 1 pakuje **wyłącznie** zmiany,
które są (a) zerowego ryzyka po stronie serwingu, (b) poparte cudzym pomiarem albo naszym kodem,
(c) nie wymagają GPU do zweryfikowania logiki. `EXPOSE_UNDO=on` spełnia wszystkie trzy.
`CAP=0` spełnia (a) i (c) i ma nasz własny pomiar ujemny za sobą.

**Cel pozostaje: średnia 29–30, srebro ≈32.33.** Nie 50+.

**Trzy rzeczy do zrobienia na PC usera (0 GPU, 0 slotów), w kolejności:**
1. **Test logiki `action_names.py`** dla `EXPOSE_UNDO ∈ {tufa, off, on}` — czy `on` reklamuje
   `UNDO` i przyjmuje obie nazwy, a `to_engine_action("UNDO")` zwraca `"ACTION7"`. **To jest
   warunek konieczny przed slotem 1**, bo inaczej powtarzamy błąd `SCOPE=run` (zmienna
   akceptowana, ale martwa). Wykonalne w Python na CPU, kilka minut.
2. **Sparsować `serve.log` (1 143 523 B z `r093`)** pod kątem **nasycenia KV pool** — dokładnie
   tej metryki, której rellik13 nie sprawdził na czas (*„kv pool sat 91-97% full and requests
   queued for cache space"*). Tu **16 rdzeni i 64 GB realnie pomagają**; w moim sandboxie
   (2 CPU / 3.9 GB) tego nie zrobię. Jeśli nasz pool jest nasycony, to jest **przyczyna**
   i wtedy (i tylko wtedy) warto rozważyć nvfp4 KV.
3. **Lokalny weryfikator configu** (§6.2 `OCENA-RUST-BENCH.md`) z rozszerzoną regułą z §4.1:
   dla **każdej** zmiennej env użytej w notebooku wypisać jej **domyślną wartość i walidator
   z patcha**, i oflagować każdą, która jest nieustawiona a ma legacy default. `EXPOSE_UNDO`,
   `ARC3_PERSISTENT_FUNCTIONS_SCOPE` i `concurrency` to trzy instancje **tej samej** klasy buga.

**Nie robić:** Rust+rayon na cokolwiek (§3.1 — najszybszy serwer ma najgorszy wynik), nvfp4 KV
(nie do zwalidowania w 4 dni), zmian parametrów serwingu (−7 do −8), searchu offline (0.20).
