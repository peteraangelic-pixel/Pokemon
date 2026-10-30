# v13.1 — trzy recenzje, i dwa fakty które zmieniają plan

**Data:** 30.10.2026 ~07:35 UTC · **Czytane read-only przez `gh api`.**

| gałąź | HEAD | czas | commit |
|---|---|---|---|
| `Pokemon@arena/a450b00f-pokemon` | **`cbefdd4e`** | **30.10 07:18:38** | *„duck-v13-1: **korekty po 3 recenzjach (Gemma/c87/Smak 29-30.10)** — magazyn winpath kluczowany bazowym kodem gry, dead-skip na licznikach magazynu (**n_passes=1: pass_index był martwy**), korekta ANALIZA-23 pkt4 i oczekiwań w README"* |
| `Smak-Domu-Konkurs@5ed750ef` | `9a83ea1c` | 30.10 07:23:32 | *„v13.1 certyfikowana … **GO#1 slot 30.10 = v13.1** (zastępuje v13), fallback v12; SYNC §14"* |
| `Gemma-konkurs@c4eeb067` | `6a6af4ac` | 30.10 07:25:16 | *„review(v13.1 a450): **cross-entry replay verified end-to-end; value is conditional on a cyclic roster**"* |
| `Pokemon@7911f950` | `53eab27b` + `00501748` | 30.10 07:27 / 07:29 | *„weryfikacja duck-v13.1"* + *„stub arcengine + procedura odtworzenia weryfikacji"* |

> **`c87` w komunikacie v13.1 to MOJA gałąź.** v13.1 powstał **~9 minut po** moim `a5432da`
> i uwzględnia moje ustalenia. Jego README cytuje mnie wprost: *„`SERVER_STARTUP_TIMEOUT` (12 min)
> **celowo bez zmian — recenzja c87 domknęła, że nie przerywa biegu**."* Czyli **siódma korekta
> (ta, która OSŁABIŁA moją rekomendację) została użyta poprawnie** — i dobrze, bo po to ją domknąłem.
> Widełki oczekiwań w README v13.1 zmieniono z **„35–50+"** na **„28–38"**.

---

## 1. ❗FAKT 1: gałąź Smak **zaprzecza sama sobie** w sprawie rosteru — w odstępie 5 dni, na tym samym pliku

**25.10 12:25 UTC**, `Smak-Domu-Konkurs/arc-agi-3/kaggle/duck-c45/OCENA-V9-LEPSZA-DROGA.md`
(„Ocena pracy DeepSeek 4.1 — Arena"), tabela „Weryfikacja liczb (na naszych danych i źródłach —
**wszystko potwierdzone**)", wiersz dosłownie:

> | Twierdzenie DeepSeek | Nasza weryfikacja | Werdykt |
> |---|---|---|
> | **Replay/×4.4 pamięć = 0 w prawdziwym scorecardzie (brak powtórzonych game_id; `official_110` = lokalny symulator)** | **zgodne z `competition_arcade.py`** | ✅ **(sonda rosteru w c45 i tak dowozi dane za darmo — koszt 0)** |

**30.10 07:05 UTC**, ta sama gałąź, `duck-v13-mega/OCENA-ARENA-V13.md` pkt 4:

> *„Struktura rosteru **POTWIERDZONA W KODZIE FRAMEWORKU (nie hipoteza!)**: `make_benchmark_kaggle_official_110`:
> "The 25 official games are repeated round-robin to 110 independent GameAPI entries" …
> klonów ~4.4/gra i **playbook gra na każdym klonie**."*

**30.10 07:30 UTC**, ta sama gałąź, `duck-v13-1/OCENA-ARENA-V13-1.md` pkt 4 — **nadal**:

> *„Magazyn winpath WSPÓLNY dla wszystkich wpisów rosteru tej samej gry (**~4.4 klony**) —
> **mnożnik replay zrobiony właściwie** (poziom rozwiązany raz = replay w każdym kolejnym klonie
> za ~0 tokenów)."*

> **To jest sprzeczność wewnętrzna tej samej gałęzi, na tym samym pliku źródłowym, 5 dni apart.**
> 25.10 napisali: replay = **0**, brak powtórzonych `game_id`, `official_110` = **lokalny symulator**,
> **„zgodne z `competition_arcade.py`"** — czyli **czytali ten sam plik, który ja przeczytałem**
> (`OPINIE-3-GALEZI-O-V13.md` §2) i wyciągnęli **ten sam wniosek co ja**.
> 30.10 napisali: roster **„POTWIERDZONY W KODZIE (nie hipoteza!)"** — cytując funkcję
> `official_110()` **z tego właśnie lokalnego symulatora**.
>
> **Moje obalenie z `OPINIE-3-GALEZI-O-V13.md` §2 zostaje potwierdzone ich własnym dokumentem.**
> Nie muszę już argumentować z docstringa `competition_arcade.py` — **oni sami go zacytowali
> i oznaczyli ✅ pięć dni wcześniej.**
>
> **I sami wtedy zapisali rozwiązanie:** *„sonda rosteru w c45 i tak dowozi dane za darmo — koszt 0"*.
> Sonda istnieje (`roster_probe.jsonl`). W `r085` odpaliła się w **smoke**. **Rerun v11 (ref 57737623)
> już leciał i dał 23.89 — jego log zawiera prawdziwe 110 identyfikatorów.** Patrz §5.

**Niezależne potwierdzenie od Gemmy**, która znalazła ten sam cytat (`REVIEWS/2026-10-29-v13-1…` §0.3):

> *„Własna dokumentacja gałęzi (`duck-c45/OCENA-V9-LEPSZA-DROGA.md`, **wiersz 12**) mówi wprost:
> „Replay/×4.4 pamięć = **0** w prawdziwym scorecardzie (brak powtórzonych game_id;
> `official_110` = **lokalny symulator**)". Czyli **v13.1 naprawia dźwignię, o której sami piszą,
> że prawdopodobnie nie zadziała**."*

Oraz jej precyzyjne ustalenie mechanizmu (§3): *„Lokalny symulator
(`taaf/competition_arcade.py:100` → **`source_infos[i % 25]`**) daje 110 = 25 × 4,4.
**Czy prawdziwy scorecard robi to samo — nie wiadomo.**"*

---

## 2. ❗FAKT 2: `PLAN_COMMIT="1"` jest **tylko oferowane modelowi, nie wymuszane** — i to obala MOJĄ wczorajszą rekomendację

> ⚠️ **POPRAWNE DLA v13 i v13.1; NIEAKTUALNE DLA v13.2** (commit `6b108534`, 30.10 07:45),
> który obniża `ARC3_ESCALATE_ACTIONS` z **60 na 10** i tym samym **dodaje wymuszenie**.
> Patrz §2.1 (domknięcie) i **`OCENA-V13-2.md` §2–§3**.

`Pokemon@7911f950`, `arc-agi-3/V13-1-VERIFICATION.md` §3, „Wada projektowa, która decyduje o wyniku":

> *„`commit(plan)` z patcha 0005 wykonuje **do 40 akcji na jedną decyzję** — czyli dokładnie tę
> dźwignię, którą niezależnie wyliczyłem w `MEGA-DIAGNOSIS.md` §4. Ale w `tool_agent.py` patch
> **tylko dopisuje narzędzie do opisu**:
> ```python
> _PYTHON_TOOL_DESCRIPTION += (" Also available: `commit(plan)` plays a list of actions …")
> prompt += PLAN_COMMIT_TOOL_ADDENDUM
> ```
> **Nie ma żadnego wymuszenia.** Model nadal może — i **prawdopodobnie będzie** — wykonywać jedną
> akcję na turę, bo tak był trenowany i tak wygląda dotychczasowa pętla. Eskalacja włącza się
> dopiero po `ESCALATE_ACTIONS = 60` akcjach na nieukończonym poziomie, czyli **po 60 zmarnowanych
> decyzjach**."*

> ❌ **ÓSMA KOREKTA MOJEGO WŁASNEGO WNIOSKU — i najważniejsza z dotychczasowych, bo dotyczy
> rekomendacji, którą wydałem wczoraj.**
>
> W `OPINIE-3-GALEZI-O-V13.md` §5 napisałem: *„TO ODWRACA CZĘŚĆ MOJEJ REKOMENDACJI:
> `PLAN_COMMIT="1"` jest JEDYNĄ dźwignią celującą w zmierzony bottleneck … plan 20 akcji w 3 s
> wobec ~14,4 s na pojedynczy ruch = ~5× tańsza akcja"* — i zaleciłem dwa sloty na tę konfigurację.
>
> **Policzyłem wartość mechanizmu z jego MOŻLIWOŚCI, nie z tego, czy cokolwiek zmusza model do
> jego użycia.** To jest **dokładnie ten sam błąd**, który sam zdiagnozowałem trzy razy w tej
> sesji: `SCOPE=run` (wartość akceptowana, zachowanie domyślne), `EXPOSE_UNDO` (domyślne `tufa`
> = legacy), `official_110` (nazwa sugeruje roster, docstring mówi symulator).
> **Reguła, którą sformułowałem i sam złamałem: „wartość env akceptowana ≠ dźwignia działa".**
> Tutaj: **„narzędzie zareklamowane w prompt ≠ narzędzie użyte".**
>
> **Dodatkowo to może być UJEMNE.** Jeśli `PLAN_COMMIT=1` w praktyce dokłada tylko tekst do promptu,
> a model i tak gra jedną akcją na turę, to jedynym efektem jest **dodatkowa rada w prompt** —
> a to jest zmierzone przez inne zespoły jako **−2.3 / −3.4** (`RESEARCH-LIDERZY-50PLUS.md` §3.1).
> **Więc `PLAN_COMMIT="1"` bez wymuszenia ma rozkład: najczęściej ~0, czasem ujemny.**
> To tłumaczy też, dlaczego v11 z patchem 0005 (przy `PLAN_COMMIT="0"`) nie wykazał zysku.

### 2.1 Co z tego wynika — poprawka jest tania i konkretna

Skoro eskalacja istnieje (`ARC3_ESCALATE_ACTIONS`, u nas **60**), to **zmniejszenie jej z 60 na
kilka** zamienia `commit(plan)` z „zareklamowanego" w „wymuszone po N akcjach":

| `ARC3_ESCALATE_ACTIONS` | zachowanie | ocena |
|---|---|---|
| **60** (obecnie) | model marnuje **60 decyzji** na jednym poziomie, dopiero potem eskalacja | ❌ przy ~213 akcjach/grę i 7 poziomach to ~30 akcji/poziom — **eskalacja często nie zdąży odpalić wcale** |
| **8–12** | po ~1 decyzji na akcję model dostaje wymuszenie batchingu | ✅ **celuje w zmierzony bottleneck** |
| 1–2 | eskalacja natychmiast | ⚠️ może odebrać modelowi eksplorację, której `commit(plan)` nie zastąpi |

> ✅ **DOMKNIĘTE 30.10 ~08:00 — i odpowiedź ZMIENIA mój werdykt.** Zweryfikowałem SAM w
> `duck-v13-2/arc3-duck-v13.ipynb` (714 156 B), komórka 2:
> ```python
> #                       escalation directive every ESCALATE_ACTIONS actions
> ESCALATE_ACTIONS = 10
> _v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)
> ```
> oraz w treści patcha 0005: `ESCALATE_ACTIONS: actions on one level before the escalation
> directive.` **Czyli: (a) próg JEST czytany z env, (b) v13.2 ma wartość 10, (c) dyrektywa
> POWTARZA SIĘ CO N AKCJI (nie jednorazowo — lepiej niż zakładałem), (d) wartość jest LOGOWANA**
> (`escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}`), więc da się ją potwierdzić
> z logu rerunu, nie z deklaracji.
>
> ❗**KONSEKWENCJA — DZIEWIĄTA KOREKTA MOJEGO WNIOSKU, PIERWSZA NA KORZYŚĆ DŹWIGNI:**
> **cały ten §2 jest POPRAWNY DLA v13/v13.1, A NIEAKTUALNY DLA v13.2.** Przy `ESCALATE_ACTIONS=60`
> i ~24–35 akcjach na poziom (2126 akcji/10 gier ÷ 6–9 poziomów) dyrektywa **nie odpalała się
> nigdy** — więc `commit(plan)` był faktycznie „zareklamowany, niewymuszony". **v13.2 dodaje
> wymuszenie.** Pełny wywód, arytmetyka i tabela czterech stanów dźwigni: **`OCENA-V13-2.md` §2–§3**.

---

## 3. Trzy recenzje v13.1 — porównanie

| pytanie | **Gemma** (`6a6af4ac`) | **Smak** (`9a83ea1c`) | **7911f950** (`53eab27b`) |
|---|---|---|---|
| czy naprawa jest prawdziwa | ✅ **cross-entry replay verified END-TO-END na prawdziwym silniku**: poziom z wpisu 1 odtworzony we wpisie 2 **za 0 tokenów** (18/18, 3/3, 15/15, 13/13 akcji na tu93, vc33, m0r0, cn04) | ✅ `base_key` przejrzany: `ls20-9607627b` → `ls20`; magazyn wspólny dla wpisów tej samej gry | ✅ `test_winpath` **7/7** z wiernym stubem `arcengine`; `grid_key` **identyczny** w `build_playbook.py` i `arc3_winpath.py`; klucze poziomów 0-based spójne; **przełączniki naprawdę eksportowane** (`os.environ.update(_variant_env)` w kom. 13) |
| czy `DEAD_SKIP` działa | ✅ nie odpala przy 3 zerowych wpisach, **od 4. tak** (`ARC3_DEAD_MIN_PASSES=3`) | ✅ *„pass_index był martwy przy n_passes=1 (nasza korekta z §13 — przyjęta i naprawiona)"* | ✅ haki w `solver.py` obecne: `begin_session`, `maybe_replay→continue`, `dead_skip→break`, `record_action` |
| **ile to warte** | **+5…+15 pkt JEŚLI roster cykliczny; 0 jeśli nie** | przyjmuje ~4.4 klona ⇒ „mnożnik OK" | **+2,3 pkt na naszych 10 grach**; **~+0,6 pkt na rosterze 110** |
| **roster** | ⚠️ **„nie wiadomo"**; cytuje ich własny dokument (§1) | ❌ **nadal zakłada ~4.4 klona** | *„jeśli te gry w nim są (**a nie wiemy**)"* |
| **oczekiwany wynik** | **26–31** | GO#1 v13.1 na 30.10 | **28 albo 50 — zależy od §3 (brak wymuszenia)** |
| `PLAN_COMMIT` | *„Nie liczyłam wartości `plan_commit`: **nigdy nie był zmierzony osobno, w żadnej recenzji**"* | wymienia jako dźwignię | ❌ **tylko oferowane, nie wymuszane** (§2) |
| metoda | **własny symulator** `winpath_sim.py` (198 ln) importujący **ich** moduł bez zmian + prawdziwy silnik | czyste artefakty, 6/6 patchy na r033, standalone byte-identical | **stub `arcengine`** + niezależny własny solver do krzyżowej kontroli ścieżek |

### 3.1 Ustalenia, które są NOWE i wartościowe

**a) Gemma policzyła wartość pamięci między wpisami — i to jest więcej niż mój ~2,9 za playbook** (§3):

> okno na wpis **2 945 s** (110 gier / 10 slotów), ~**226 akcji** przy 12,9 s/akcję · kopia z
> magazynem odtwarza poziomy 1..d **za 0 tokenów i ~0 czasu** (krok silnika trwa ms), a akcje
> **liczą się do RHAE** — czyli kopia zachowuje efektywność wpisu 1 i **cały swój budżet tokenowy
> zostawia na poziom d+1** · z r085 (`ls20`): **414 z 427 akcji poszło na poziomy 1–3**, więc kopia
> dostaje na poziom 4 tyle paliwa, ile wpis 1 zużył na trzy poziomy. Przejście 3 → 4 poziomy na
> grze 7-poziomowej to **+16,4 pkt na tej grze**.

**To jest lepszy rachunek niż mój.** Mój ~2,9 dotyczył **playbooka offline**; jej +5…+15 dotyczy
**pamięci między wpisami**, która jest innym i większym mechanizmem — **pod warunkiem, że wpisy się
powtarzają**. Czyli cała wartość v13.1 jest **funkcją jednego, nierozstrzygniętego faktu**.

**Uzgodnienie rozbieżności 2,90 (Gemma) vs 0,6 (7911f950)** — oba są poprawne, przy różnych
założeniach o rosterze: 72,61 / 25 gier = **2,90** (roster cykliczny, wszystkie ~4.4 klona gry
pokrytej korzystają) vs 72,61 / **110** gier = **0,66** (każda pokryta gra występuje raz).
**Rozstrzygnięcie zależy wyłącznie od rosteru.**

**b) 7911f950 znalazł realną stratę w playbooku** (§2, „Dwie rozbieżności"):

| gra | ich ścieżka | v13.1 playbook | ocena |
|---|---|---|---|
| **sp80** | **4 akcje** (`A4,A4,A4,A5`) | **28 akcji** | ❌ **7× dłuższa** — przy kwadratowej karze RHAE to realna strata |
| **vc33** | `ACTION6(61,33)` ×3 | `ACTION6(60,32)` ×3 | ⚠️ różnica 1 piksela, **nie rozstrzygną bez silnika** |
| **cd82, lp85** | 5 akcji, 5 akcji | **identyczne** | ✅ dwa niezależne źródła tej samej ścieżki |

> **Ich rekomendacja: „Playbook warto przegenerować, biorąc NAJKRÓTSZĄ ścieżkę spośród wszystkich
> źródeł, nie pierwszą znalezioną."** To jest trafne i tanie — i to jest **jedyny** argument za
> PC sweepem, który **nie** zależy od rosteru: krótsze ścieżki podnoszą RHAE na poziomach, które
> agent i tak rozwiąże. ⚠️ Ale przy **capie ukończenia** (`OPINIE-3-GALEZI-O-V13.md` §3.2) zysk
> jest ograniczony do ~3 pkt łącznie, więc to jest **kosmetyka, nie dźwignia**.

**c) Gemma znalazła drobiazg w kodzie** (§4, nie blokuje): hook `maybe_replay` jest wołany **przed**
obsługą game-over, więc po śmierci init-hash się nie zgada i `_replay_once` robi
`state.broken.add(level)` — poziom nie jest odtwarzany przez resztę wpisu. **Skutek praktyczny ~zero**
(sprawdziła: `fails` w magazynie **nie** rośnie, init-stróż działa, więc nie ma zatruwania dobrych
ścieżek). Jedna linia do uszczelnienia.

**d) Gemma uczciwie ogranicza własną recenzję** (§6): symulacja używa **fałszywej sesji zgodnej z
kontraktem**, nie pełnego harnessu — sprawdza moduł i silnik, **nie integrację z `solver.py`**
(tę tylko przeczytała w patchu). *„„Roster się nie powtarza" to **cytat z dokumentacji gałęzi, nie
mój pomiar** — i dlatego nazywam to **warunkiem, nie faktem**."* **To jest właściwa epistemika i
biorę ją za wzór** — w przeciwieństwie do „POTWIERDZONA W KODZIE (nie hipoteza!)".

---

## 4. Droga do 50+, którą ta gałąź **już przyjęła** — i o której nie wiedziałem

`Smak-Domu-Konkurs/arc-agi-3/kaggle/duck-c45/OCENA-V9-LEPSZA-DROGA.md`, sekcja
**„Strategiczny PIVOT (przyjęty)"**. To jest odpowiedź na pytanie usera „jak lider zrobił 75",
której **nie znalazłem wczoraj w researchu zewnętrznym**, bo jest w ich własnym repo:

> **T3 = world-model + planer (paper01, MIT).**
> **Mechanizm:** agent-koder pisze **wykonywalny model gry w Pythonie** → weryfikacja na przejściach
> → **planer (BFS) szuka ciągu akcji W MODELU** → wykonanie + porównanie klatek.
> **„Jedna decyzja LLM kupuje dziesiątki–setki akcji."**
> **Dowód:** zamyka dokładnie NASZ ogon — **ls20 1/7→7/7, tn36 1/7→7/7, g50t 2/7→7/7, ka59 3/7→7/7**.
> **Portfolio/routing:** WM wygrywa **7/10** gier, nasza pętla **3/10** (dc22, sc25, s5i5);
> **unia per gra = 69.69** → docelowo routing per gra.
> **NIEZMIERZONE na open-weights:** paper testował **GPT-5.5/5.4 przez API**, private setu nie tknęli.
> Nasz eksperyment = ten sam scaffold na **Qwen3.6/3.8 (Kaggle)**.
> **T2 (tanie ~T3):** plan-then-execute w REPL (model pisze pętle akcji z warunkami stopu) —
> **atakuje tę samą metrykę (akcje/decyzję) za 1 slot.**

Ich własna weryfikacja paper01, **co do 0,01**: WM GPT-5.5 = **56.81** na naszych 10 grach
(cn04 96.34 · dc22 0.00 · g50t 95.08 · ka59 100 · ls20 57.02 · m0r0 67.33 · s5i5 0.25 ·
sc25 20.23 · su15 56.85 · tn36 74.98), pełny set **58.12%**, **15/25 gier 100%**.
Oraz: *„model = współczynnik"* — WM GPT-5.4 = **24.67** < nasze 27.21.

> **To zmienia mój wczorajszy wniosek o paper01, częściowo.** W `DIAGNOZA-23-89-I-PLAN.md` §6
> i `RESEARCH-LIDERZY-50PLUS.md` §6 odrzuciłem paper01, bo *„GPT-5.5 przez API — na Kaggle internet
> wyłączony"*. **To zastrzeżenie pozostaje prawdziwe dla ich POMIARU, ale nie dla METODY**: scaffold
> (model świata + weryfikator + BFS) jest **niezależny od modelu**, i oni to wiedzą — dlatego planują
> ten sam scaffold na Qwen. **Ich własne „NIEZMIERZONE na open-weights" jest uczciwe i to jest
> dokładnie to ryzyko.**
>
> **Ale: WM GPT-5.4 = 24.67, czyli SŁABSZY model w tym samym scaffoldzie dał wynik poniżej naszego
> 27,21.** To jest **pomiar przeciwko** tezie, że scaffold sam w sobie daje 50+ — sugeruje, że
> **56.81 to w dużej części zasługa GPT-5.5**, nie architektury. **Qwen3.8-Flash-Next W4A16 jest
> znacznie słabszy niż GPT-5.4.** Czyli T3 na naszym modelu ma **niezerową, ale słabo uzasadnioną**
> szansę. **Nie da się tego zweryfikować w 4 slotach przy σ≈2,5–3,9.**

---

## 5. Plan — poprawiony po v13.1

> ⚠️ **TEN PLAN JEST NIEAKTUALNY (30.10 ~08:00).** Powstał przed v13.2 i przed
> `AUDYT-4-GALEZI-30-10.md`. **Aktualny plan: `OCENA-V13-2.md` §7.2**, gdzie parsowanie
> `serve.log` awansowało na **WARUNEK KONIECZNY** decyzji o slocie: arytmetyka
> `akcje/grę = 2945 × 1000 / (ms/token × tok/akcję)` pokazuje, że przy **62,6 ms/token**
> (stan r110) nawet `tok/akcję = 400` daje **118 akcji**, czyli **mniej niż r085 bez batchingu
> (228)**. **Multiplikator razy zero daje zero** — najpierw silnik, potem slot.

**Trzy rzeczy się zmieniły względem `OPINIE-3-GALEZI-O-V13.md` §6:**

1. ❌ **`PLAN_COMMIT="1"` przestaje być główną dźwignią** (§2) — bez wymuszenia to najczęściej ~0,
   czasem ujemne. **Zamiast tego: sprawdzić, czy `ARC3_ESCALATE_ACTIONS` jest env, i jeśli tak —
   obniżyć z 60 na 8–12.** To jest ta sama dźwignia, ale **wymuszona**, i kosztuje jedną wartość.
2. ✅ **v13.1 > v13 mechanicznie** — trzy niezależne recenzje potwierdzają, że dwie martwe dźwignie
   ożyły. **Ale ich wartość jest warunkowa** i warunek jest nierozstrzygnięty.
3. ✅ **Wszystkie trzy recenzje zbiegają na tę samą rekomendację co ja: zabrać `roster_probe`.**
   Gemma dosłownie: *„jedyna sensowna rekomendacja na slot 30.10 to **zabrać ze sobą sondę rosteru**
   (`roster_probe.jsonl`, **koszt 0**) — jedna lista 110 `game_id` rozstrzyga, czy pamięć między
   wpisami jest warta 0 czy +15"*.

| slot | konfiguracja | hipoteza (JEDNA) |
|---|---|---|
| **30.10** | **v13.1** z `PLAN_COMMIT="0"` · `CAP=0` · `WINPATH="1"` · `DEAD_SKIP="1"` · `EXPOSE_UNDO="on"` · conc 10 · **`roster_probe` włączony i jego wynik odzyskany** | **roster: cykliczny czy nie** — i przy okazji `CAP=0` (+0,4…2,2 zmierzone) |
| **31.10** | zależy od 30.10: roster **cykliczny** → ta sama konfiguracja ponownie (drugi draw, pamięć warta +5…15) · roster **prywatny** → `WINPATH="0"` + **`ESCALATE_ACTIONS` 8–12** (jedna zmiana: wymuszony batching) | rozgałęzienie rozstrzygnięte **pomiarem**, nie założeniem |
| **1.11** | najlepsza z dwóch; jeśli obie <26 → kontrola | trzeci punkt oddziela efekt od szumu |
| **2.11** | select best | zabezpieczenie |

**Dlaczego `PLAN_COMMIT="0"` na slot 30.10, wbrew mojej wczorajszej rekomendacji:** bo przy
braku wymuszenia (§2) dokłada **tylko tekst do promptu** — a dodatkowe rady w prompt są zmierzone
jako **−2.3 / −3.4**. Slot 30.10 ma **jedno** zadanie: **rozstrzygnąć roster**, bo od tego zależy
wartość dwóch z trzech dźwigni v13.1. Mieszanie w tym samym slocie niewymuszonego `commit()`
rozmyłoby atrybucję — czyli powtórzyłoby błąd v11.

**Trzy rzeczy darmowe PRZED slotem 30.10 (bez zmian):**

1. ❗**USER: pobrać log rerunu ref 57737623** (Kaggle → Submissions → v11 → Output) i wyciągnąć
   `game_id` z linii `roster_probe` / `[finished]`. **v11 już leciał na rerunie i dał 23.89 —
   jego log zawiera prawdziwe 110 identyfikatorów.** To rozstrzyga §1 **dziś, za zero**.
   Ich własna notatka z 25.10: *„sonda rosteru … dowozi dane za darmo — koszt 0"*.
2. **Sprawdzić, czy `ARC3_ESCALATE_ACTIONS` jest czytany z env** w patchu 0005 (§2.1) — 7911f950
   ma już 9/12 testów `test_plan_commit.py` na module wyciągniętym z patcha, więc to jest
   kilkanaście minut na CPU. **Warunek konieczny dla slotu 31.10 w gałęzi „roster prywatny".**
3. **Gemma: `analyze_run.py` na `benchmark.json` rerunu** — jej bramka: mediana akcji **<300** →
   priorytet przepustowość; **≥300** i głębokość ≤2 → priorytet polityka.

**Czego nie robić** (dochodzi do listy z `OPINIE-3-GALEZI-O-V13.md` §6):
* ❌ **`n_passes>1`** — Gemma wprost: *„nie włączać `n_passes>1`"*. Zgodne z moim §2.3: przy 110
  grach i 9 h cztery passy = 4× mniej czasu na grę, a RHAE jest wypukłe w głębokości.
* ❌ **liczyć pamięć między wpisami jako upside w prognozie** (Gemma) — dopóki roster nierozstrzygnięty
* ❌ **`PLAN_COMMIT="1"` bez wymuszenia** (§2) — najczęściej ~0, czasem ujemne
* ❌ 27B (1,18 i 0,27) · parametry serwingu (−7…−8) · search offline (0.20, 0/113) · stackowanie zmian

**Oczekiwanie: 26–31** (Gemma) / **~27–29** (mój `OCENA-V13-MEGA.md` §7) / **28–38** (ich README
po korekcie). **Trzy niezależne przedziały zachodzą na siebie wokół ~28–30.** Cel: **srebro ≈32.33**.
**50+ wymaga ~300 akcji/grę** (trzy niezależne modele) **albo T3 na modelu, który go nie udźwignie**
(WM GPT-5.4 = 24.67 < nasze 27,21).

---

## 6. Co ten dokument zmienia w poprzednich

| dokument | korekta |
|---|---|
| `OPINIE-3-GALEZI-O-V13.md` §2 | **WZMOCNIONE ich własnym dokumentem**: gałąź Smak 25.10 zweryfikowała `official_110` = lokalny symulator i replay = 0, cytując `competition_arcade.py` — a 30.10 opublikowała przeciwnie (§1) |
| `OPINIE-3-GALEZI-O-V13.md` §5 | ❌ **ODWRÓCONE (ósma korekta)**: `PLAN_COMMIT="1"` **nie** jest główną dźwignią — jest tylko **zareklamowane**, nie wymuszone; eskalacja dopiero po **60 zmarnowanych decyzjach**. Nowa rekomendacja: `ARC3_ESCALATE_ACTIONS` 60 → 8–12, **po sprawdzeniu że to env** |
| `OPINIE-3-GALEZI-O-V13.md` §6 plan | slot 30.10: **v13.1 z `PLAN_COMMIT="0"`** i priorytetem **rozstrzygnięcia rosteru**; `WINPATH="1"` zostaje, bo jest bezpieczny (Gemma: fallback do LLM, init-stróż, brak zatruwania ścieżek) |
| `OCENA-V13-MEGA.md` §2, §3, §6 | **PRZYJĘTE przez v13.1**: `n_passes=1` (poprawili `dead_skip` na liczniki magazynu), `ANALIZA-23` pkt 4, widełki 35–50+ → **28–38**, `SERVER_STARTUP_TIMEOUT` **celowo bez zmian** z cytatem mojej korekty |
| `RESEARCH-LIDERZY-50PLUS.md` §6 | **UZUPEŁNIONE**: droga do 50+ istnieje i jest **przyjęta** przez gałąź Smak jako **T3 = world-model + planer (paper01, MIT)** — *„jedna decyzja LLM kupuje dziesiątki–setki akcji"*, unia per gra **69.69**. **Ale WM GPT-5.4 = 24.67 < nasze 27,21**, więc scaffold sam w sobie nie wystarczy; ich własne „NIEZMIERZONE na open-weights" jest uczciwe |
| `FAKTY-I-POMIARY.md` | dodać: `source_infos[i % 25]` w `competition_arcade.py:100` (mechanizm klonowania **lokalnego** symulatora) · `base_key()` w v13.1 · `ARC3_ESCALATE_ACTIONS=60` jako próg zbyt wysoki przy ~30 akcjach/poziom |
