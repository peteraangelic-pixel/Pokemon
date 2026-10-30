# Pomiar `serve.log` + v13.3/v14/v15 — i DZIESIĄTA korekta: „3,6× luka silnika" NIE ISTNIEJE

**Data:** 30.10.2026 ~08:20 UTC · **Dwie rzeczy naraz:** (A) zbudowałem parser i **sparsowałem
prawdziwe logi** — hipoteza, którą sam postawiłem, jest **obalona moim własnym pomiarem**;
(B) w międzyczasie powstały **v13.3-arena (Smak `5548d35`)**, **duck-v14** i **duck-v15** (Gemma
`b38b82eb` 08:04, `07bf05e0` 08:12).

> **STRESZCZENIE. (1) Zbudowałem `tools/parse_serve_log.py` i uruchomiłem go na prawdziwych
> `serve.log` z r085 (986 600 B) i r093 (1 143 523 B). MOJA HIPOTEZA NASYCENIA PULI KV JEST
> OBALONA: obłożenie średnio 60 % / 53 %, próbek ≥0.91 tylko 3,5 % / 2,5 %, mediana kolejki
> **0.0 w każdym oknie**, a korelacja obłożenie↔przepustowość jest **DODATNIA** (+0,09 / +0,38) —
> przy wysokim obłożeniu throughput jest **wyższy** (752 vs 654 tok/s). (2) Przy okazji wyszło
> coś ważniejszego: **`r110` to run 27B/vLLM, nie 8B** — wiersz w tabeli `MEGA-CONFIG.md` jest
> **błędnie zaetykietowany**, więc **„3,6× luka silnika niepochodząca z modelu" NIE ISTNIEJE**.
> To jest **dziesiąta korekta mojego wniosku i najostrzejsza: zweryfikowałem ISTNIENIE artefaktu,
> nie jego TOŻSAMOŚĆ** — i na tej podstawie awansowałem parsowanie `serve.log` na dźwignię nr 1
> „wartą 20–40 punktów". **Awans wycofany.** (3) Gemma **zmierzyła** próg eskalacji na r085:
> `ESCALATE_ACTIONS=10` odpala **154×**, kosztuje **15,3 % puli tokenów gry** i każe modelowi
> przestać próbować na **31 z 32** poziomów, na których był na tempie — **19× za czuły**.
> Przy **20**: 60×, 6,0 %. (4) **v15 jest lepszy od v13.2 i nie zbuduję własnej wersji** —
> uzasadnienie w §6. (5) **v15 sam rozstrzyga spór o roster w trakcie biegu** (sonda z
> `bm.game_runs`) **i mierzy, czy batching działa** (alarm `actions_per_call < 1,5`).**

---

## 1. Parser zbudowany i uruchomiony — moja hipoteza OBALONA moim własnym pomiarem

**Narzędzie:** `arc3-handoff/tools/parse_serve_log.py` (commit w tym samym zestawie). Czysty
Python 3, biblioteka standardowa, 0 GPU, 0 slotów, 0 sieci. Wyciąga z linii SGLang
(`Decode batch: #running-req: N, #token: T, token usage: U, gen throughput (token/s): G, #queue-req: Q`)
szeregi czasowe i liczy percentyle, frakcje nasycenia, korelację oraz przepustowość przy niskim
i wysokim obłożeniu. Ma `--series` (okna) i `--csv`.

**Dane:** pobrałem przez `gh api` i sparsowałem **prawdziwe** logi:
`r085/output-pick/serve.log` (986 600 B, blob `65492e46`) i
`r093/output-pick/serve.log` (1 143 523 B, blob `85e7129b`).

| metryka | **r085** (c45, smoke) | **r093** (v11, smoke) |
|---|---|---|
| linii / próbek batch | 4 494 / 2 608 | 5 188 / 3 156 |
| decode / prefill | 1 574 / 1 034 | 2 054 / 1 102 |
| **pula KV (tokenów)** | **1 011 264** | **1 011 264** |
| **`token usage` średnio** | **0,6042** | **0,5258** |
| mediana / p90 / p95 / max | 0,66 / 0,81 / 0,87 / **1,00** | 0,53 / 0,82 / 0,88 / 0,97 |
| **frakcja próbek ≥ 0,91** | **3,53 %** | **2,53 %** |
| frakcja ≥ 0,80 | 12,46 % | 12,23 % |
| **`#queue-req` > 0** | **4,72 %** próbek | **3,33 %** |
| kolejka: średnia / max | 0,06 / 8 | 0,04 / 7 |
| `#running-req` średnio / max | **8,28** / 10 | **7,13** / 10 |
| **`gen throughput` średnio** | **663,0 tok/s** | **584,2 tok/s** |
| mediana / min | 712,3 / 33,4 | 597,7 / 22,1 |
| **korelacja `token usage` ↔ throughput** | **+0,0921** | **+0,3773** |
| throughput przy TU < 0,70 | 654,5 | 559,1 |
| **throughput przy TU ≥ 0,91** | **752,1** | **710,4** |
| „duszenie" (TU<0,70 ÷ TU≥0,91) | **0,87** | **0,787** |

Szereg czasowy (`--series --window 300`) — **mediana kolejki 0,0 w KAŻDYM oknie**, obu runów:

```
r085: okna 0..8  TU mediana 0,16 → 0,48 → 0,76 → 0,78 → 0,71 → 0,73 → 0,68 → 0,60 → 0,61
                  p95         0,31   0,64   0,95   0,99   0,85   0,82   0,82   0,77   0,77
r093: okna 0..10 TU mediana 0,17 → 0,48 → 0,71 → 0,87 → 0,69 → 0,70 → 0,46 → 0,47 → 0,43 → 0,45 → 0,47
```

> ❌ **HIPOTEZA OBALONA — i obaliłem ją SAM, co jest jedynym powodem, dla którego ją postawiłem.**
> W `AUDYT-4-GALEZI-30-10.md` §3 postawiłem: pula 1 011 264, kontekst 131 072, 10 gier ⇒
> `10 × 131 072 = 1 310 720 > 1 011 264` ⇒ nasyca się przy średnim kontekście > 101 126,
> a trim odpala dopiero przy 118 000 ⇒ „nasycenie jest oczekiwane".
>
> **Pomiar mówi co innego:** średnie obłożenie **60 %** i **53 %**, a nie ~100 %; próbek ≥0,91 jest
> **3,5 %** i **2,5 %**, a nie „91-97 % full"; **kolejka jest zerowa w każdym oknie czasu**;
> a throughput przy **wysokim** obłożeniu jest **wyższy** (752 vs 654), czyli korelacja jest
> **dodatnia**, nie ujemna.
>
> **Dlaczego moja arytmetyka była zwodnicza:** liczyłem `10 × MAKSYMALNY kontekst`. Kontekst jest
> przycinany (trim przy 118k → ~59k), więc **średnie** obłożenie na grę to ~60–100k, nie 131k.
> **Pomnożyłem limit przez liczbę strumieni i nazwałem to nasyceniem.** To jest **dokładnie ten sam
> błąd co przy capie 45k** (`OCENA-CODEX-7Z.md` §3.3): *poprawna arytmetyka na źle dobranej
> populacji* — tutaj: na populacji „chwil maksymalnego kontekstu" zamiast „całego rozkładu".
>
> **Mechanizm rellik13 jest prawdziwy, ale nie dotyczy naszej konfiguracji.** On miał **16 strumieni**
> i kontekst **69 632**; my mamy **10 strumieni** i **131 072** przy tej samej puli. U niego pula
> była wąska; u nas jest ~40 % zapasu. **Nie wolno przenosić mechanizmu między konfiguracjami
> bez przeliczenia — to ta sama reguła co „nie przenosić werdyktu między wersjami bez diffu".**
>
> ✅ **Użyteczny produkt uboczny:** moje `EKONOMIA-TOKENOW.md` §1bis używało „linia szybka
> 603 tok/s". Zmierzone: **663 (r085)** i **584 (r093)** — czyli **603 leży dokładnie między nimi**.
> **Model przepustowości potwierdzony pomiarem, co do 10 %.**

---

## 2. ❗Przy okazji: `r110` to run **27B/vLLM**, nie 8B — więc „3,6× luka silnika" NIE ISTNIEJE

Cała teza o „największej dźwigni" (`AUDYT-4-GALEZI-30-10.md` §2) stała na wierszu tabeli
Gemma `MEGA-CONFIG.md` §1: *„r110 | **8B, v13 cap 45k** | 62,6 ms/token | 572 tok/akcję | 82 akcje"*.

**Sprawdziłem tożsamość artefaktu `r110-kernel_output_pick/output-pick`:**

| dowód | wartość |
|---|---|
| nazwa logu harnessa | **`arc3-duck-v13-27b.log`** (173 096 B) |
| nazwa logu serwera | **`vllm-openai-server.log`** (175 134 B) — **vLLM, nie SGLang** (u 8B jest `serve.log`) |
| grep po treści logu | **742 × „vllm"**, 30 × „VLLM", **17 × „27b"**, 5 × „27B", **0 × „sglang"/„flash-next"** |
| `summary.txt` | mean score **0,73**, 926 akcji, 448 782 tokenów, **155,46 gen tok/s**, 48m 6s, start **28.10 23:17:39** |
| tokeny per gra | 45 247 · 45 775 · 45 411 · 44 850 · 45 276 · 44 582 · 42 317 · 44 385 · 45 769 · 45 170 — **każda ~45k** |

> ❌ **WIERSZ JEST BŁĘDNIE ZAETYKIETOWANY.** `r110` to **27B na vLLM**, nie „8B".
>
> **Konsekwencja — i to jest sedno:** tabela Gemmy ma `r085 = 17,2`, `r110 = 62,6`, `r118 = 63,1`.
> **`r110` i `r118` to OBA runy 27B i OBA mają ~63 ms/token — czyli są ze sobą zgodne.**
> Różnica 17,2 → 62,6 to **8B vs 27B**, czyli **dokładnie różnica modelu**, o której Gemma
> napisała, że *„nie pochodzi z modelu ani z promptu"*.
>
> **„3,6× luka silnika" NIE ISTNIEJE.** Nie ma żadnej tajemniczej regresji do odzyskania.
> Linia 8B **już jest** w swoim dobrym stanie: 663 tok/s agregatowo, 17,2 ms/token, 60 % obłożenia
> puli, zerowe kolejki (§1).

### 2.1 ❗DZIESIĄTA korekta — i najostrzejsza, bo dotyczy mojej własnej metody

W `AUDYT-4-GALEZI-30-10.md` §2.3 napisałem: *„**Sprawdziłem, że r110 istnieje** (nie jest zmyślony):
`ops/results/r110-kernel_output_pick/output-pick`. Zawartości w tej turze nie czytałem — **oznaczam
jako niezweryfikowaną wprost**, ale artefakt jest."*

**Zweryfikowałem ISTNIENIE, nie TOŻSAMOŚĆ.** A potem na tej podstawie:
* awansowałem parsowanie `serve.log` na **dźwignię nr 1**, „wartą 20–40 punktów",
* uczyniłem je **warunkiem koniecznym** dla decyzji o slocie (`OCENA-V13-2.md` §7.2 pkt 1),
* i napisałem zdanie: *„Wysyłanie v13.2 przed zmierzeniem silnika to powtórzenie błędu v11"*.

> **To jest najostrzejsza z dziesięciu korekt, bo złamałem własną regułę w momencie, w którym ją
> cytowałem.** Przez całą sesję pisałem, że liczby trzeba weryfikować u źródła, że `concurrency=120`
> wzięło się z przepisania liczby bez porównania warstw, że `official_110` wzięło się z czytania
> nazwy zamiast docstringa. **A tutaj przepisaliśmy z Gemmy wiersz tabeli — z etykietą, której
> nie sprawdziłem, mimo że miałem identyfikator bloba i mogłem to zrobić jednym poleceniem.**
>
> **Reguła, która z tego wynika i którą wpisuję do `FAKTY`:**
> **CYTOWANA TABELA JEST ARTEFAKTEM WTÓRNYM. Przed zbudowaniem na niej priorytetu trzeba pobrać
> artefakt PIERWOTNY i sprawdzić jego TOŻSAMOŚĆ (nazwa pliku, serwer, model, znacznik czasu),
> nie tylko ISTNIENIE.** „Artefakt istnieje" ≠ „artefakt jest tym, za co go uważa tabela".
>
> Koszt błędu: **straciłem jedną turę** na promowanie dźwigni, która nie istnieje. Nie kosztowało
> to slotu — i to jest jedyna okoliczność łagodząca.

### 2.2 Co z tego zostaje prawdziwe

* ✅ **Parser jest użyteczny** — ale jako **strażnik regresji** dla przyszłych runów i jako narzędzie,
  które **obaliło hipotezę**, nie jako dźwignia punktowa. Został zacommitowany i działa.
* ✅ **Arytmetyka `akcje/grę = 2945 × 1000 / (ms/token × tok/akcję)` pozostaje poprawna** — zmienił
  się tylko wniosek o tym, **który czynnik jest do ruszenia**.
* ✅ **Skoro silnik 8B jest już w dobrym stanie (17,2 ms/token), to jedynym czynnikiem do ruszenia
  jest `tok/akcję` = 647.** Cel Gemmy: *„400+ akcji/gę wymaga ~370 tok/akcję przy r085-owym
  silniku"*. **Czyli batching jest właściwą dźwignią — i v13.2/v13.3/v15 celują dokładnie w nią.**
  **To przywraca moją ocenę z `OPINIE-3-GALEZI-O-V13.md` §5, którą potem osłabiłem w
  `OCENA-V13-1` §2, a potem przywróciłem w `OCENA-V13-2` §3, a potem znów osłabiłem w §6.
  Stan ostateczny: batching JEST dźwignią, silnik NIE JEST.**
* ⚠️ **Ale `r110` potwierdza coś innego:** każda gra dostała **~45k tokenów** — czyli w tym runie
  cap 45k **był aktywny** i **wiązał** w każdej grze, przy wyniku **0,73**. To dodatkowy,
  niezależny dowód przeciwko mojemu patchowi 0004 (obok `OCENA-CODEX-7Z.md` §3).

---

## 3. Gemma ZMIERZYŁA próg eskalacji — i `10` jest **19× za czułe**

`REVIEWS/2026-10-29-v13-2-z-galezi-a450-weryfikacja.md` (commit `bfada7e7`, 07:55:46),
narzędzie `ARC3/local-lab/escalation_audit.py`, dane z **r085 (32 ukończone poziomy)**:

| próg | wstrzyknięć | tokenów dyrektyw | **% puli gry** | odpala **PRZED** ludzkim baseline'em |
|---|---|---|---|---|
| **10** (v13.2 / v13.3) | **154** | 22 330 | **15,3 %** | **31 / 32 poziomów** |
| **20** (v14 / v15) | **60** | 8 760 | **6,0 %** | ~25 / 32 |
| 60 (v13.1) | 12 | 1 740 | 1,2 % | 7 / 32 |
| `max(20, 1,2 × baseline[poziom])` | **8** | 1 160 | **0,8 %** | **0 / 32** |

Konkretne przykłady z v13.2: **`cn04/4` dostaje „przestań próbować" po 41 akcjach, gdy człowiek
potrzebuje 300**; `cn04/5` po 52 przy 208; `m0r0/3` po 94 przy 203.

**Dwa powody, dla których to nie jest kosmetyka (ich argumentacja):**
1. *„**kosztowna jest posłuszność, nie tekst.** Każda ze 154 zachęt prosi o turę modelarską
   (tysiące tokenów). Jeśli model posłucha co czwartej — ~12 tys. tokenów (**8 % puli**) plus akcje
   na weryfikację modelu."*
2. *„**możliwy efekt drugiego rzędu:** w scaffoldzie działa priority gate z referencją tempa
   w tokenach na poziom (`priority_pace_reference.json`, poziom 1 = 27 tys. tokenów, fallback
   45,9 tys.). **Gra, która napompuje tokeny, wpada do gorszej bandy kolejki.** Hipoteza
   (nie zmierzona): **eskalacja @10 sama wypycha grę z kolejki.**"*

> **To jest ważne i częściowo KORYGUJE moją ocenę v13.2.** W `OCENA-V13-2.md` §2 napisałem, że
> v13.2 „dodaje wymuszenie" i że to pierwsza dźwignia spełniająca wszystkie trzy warunki reguły
> `SCOPE=run`. **Gemma precyzuje: dyrektywa jest PRZYPOMNIENIEM, nie wymuszeniem** — *„To
> przypomnienie, nie wymuszenie — `commit()` zostaje opcją modelu"*.
>
> Czyli **stan dźwigni to „presja", nie „wymuszenie"** — czwarty stan, którego nie miałem w swojej
> taksonomii (niezmierzona / niewymuszona / wymuszona). **Uzupełniam: „zareklamowana" → „presja
> okresowa" → „wymuszona".** v13.2/v13.3/v15 są na środkowym.
>
> **I ich punkt 2 jest groźniejszy niż wygląda:** jeśli eskalacja pompuje tokeny, a priority gate
> szereguje gry **wg tokenów na poziom**, to dźwignia mająca przyspieszyć grę **wypycha ją z
> kolejki**. To byłaby **ujemna** pętla sprzężenia — i **sonda budżetu w v14/v15 to zmierzy**.

### 3.1 Guard GAME_OVER — potwierdzony, plus lekcja metodologiczna

Gemma przetestowała na prawdziwym silniku, ich modułem, na trzech wpisach rosteru:

```
v13.1: maybe_replay na martwej klatce -> False; broken=[0]   <-- poziom spalony do końca wpisu
v13.2: maybe_replay na martwej klatce -> False; broken=[]    <-- nic nie spalone
       wpis 3: replay=True -> levels=1  (ścieżka nietknięta)
```

> ⚠️ **Ich uwaga metodyczna jest siódmą instancją klasy błędu z `OCENA-V13-2.md` §5:**
> *„guard czyta `game_state.raw.state`, a **mój pierwszy symulator nie miał atrybutu `raw`** —
> guard **MILCZAŁBY** i test certyfikowałby ścieżkę, której nie ma. Poprawiłem symulator
> (`FakeState(raw=Raw(state=...))`), dopiero wtedy test ma sens. **To dokładnie ten rodzaj błędu,
> który daje fałszywe „ALL CHECKS PASSED".**"*
>
> **To jest instancja #7: MOCK NIE MA ATRYBUTU, KTÓRY CZYTA KOD PRODUKCYJNY ⇒ guard milczy ⇒
> test przechodzi.** Uzupełniam taksonomię: obok „mock karmi wartości, których rerun nie produkuje"
> (`pass_index`) jest „mock **nie ma pola**, które czyta guard". **Oba dają zielony test przy
> martwym kodzie.** Reguła: **mock musi być walidowany przeciwko KONTRAKTOWI, nie tylko przeciwko
> temu, co test chce zobaczyć** — np. asercja, że `hasattr(state, "raw")`.

---

## 4. v13.3-arena (Smak `5548d35`) — dwie rzeczy, których brakowało

Nie znalazłem tego commitu na `a450b00f` ani na `c4eeb067` (`gh api` → *No commit found for SHA*),
więc jest na innej gałęzi Smaka; **Gemma ma artefakt** w `ARC3/duck-v15/src/base-v13-3-arena.ipynb`
i opisuje go w `README.md` v15. Z ich tabeli porównawczej:

| | v13.2 | **v13.3-arena** | v14 | **v15** |
|---|---|---|---|---|
| **batch na openerze (`ARC3_OPENER_COMMIT_HINT=1`)** | – | **+** | – | **+** |
| **log zdarzeń win-path (patch 0007)** | – | **+** | – | **+** |
| `ESCALATE_ACTIONS` | 10 | 10 | **20** | **20** |
| sonda rosteru | – | – | **+** | **+** |
| sonda budżetu | – | – | **+** | **+** |
| guard hooka c45 (wyjątek nie zabija notebooka) | – | – | **+** | **+** |
| łańcuch patchy | 6 | **7** | 6 | **7** |

**Obie nowości v13.3 to dokładnie to, czego brakowało w mojej analizie:**

1. **`ARC3_OPENER_COMMIT_HINT=1` — batch na openerze.** To jest **„wymuszenie batcha na 1. turze
   poziomu"**, które Smak zapisał w SYNC §15 jako tanią naprawę obok `ESCALATE_ACTIONS 60→8-10`.
   **Atakuje `tok/akcję` od pierwszej tury**, zamiast czekać na próg eskalacji.
2. **Patch 0007 = log zdarzeń win-path.** To jest odpowiedź na znalezisko 7911f950
   (*„cicha awaria replay: `try/except pass`, init-mismatch → `broken` **bez logu** ⇒ wymagać linii
   logu o replay"*). **Bez tego nie dałoby się zdiagnozować replayu z logu rerunu.**

---

## 5. v14 i v15 (Gemma) — i dlaczego v15 jest najlepszym kandydatem

**v14** (`b38b82eb`, 08:04) = *„v13.2 with a measured escalation threshold and two probes that
cannot crash"*. Cztery zmiany, każda uzasadniona pomiarem albo usuwająca ryzyko wywalenia notebooka:

| # | zmiana | dlaczego |
|---|---|---|
| 1 | `ESCALATE_ACTIONS` **10 → 20** | pomiar z §3 |
| 2 | **hook sondy rosteru z c45 owinięty w `try/except`** | *„`_orig_play = _S._HarnessGameSession.play` stało **POZA** jakimkolwiek try w komórce, która ustawia `bm.solver.*`. **Brak atrybutu w innym revision bundla = wyjątek = martwy notebook przed startem**"* |
| 3 | **nowa sonda rosteru** (po biegu, z `bm.game_runs`) | *„odpowiada na jedyne pytanie, od którego zależy, czy pamięć win-path jest warta 0 czy +5…15"* |
| 4 | **nowa sonda budżetu** (przed biegiem) | *„cap na grę jest **11×** powyżej uczciwego udziału (532 min vs ~48 min przy 110 grach); **nikt tego nigdzie nie loguje**"* |

**Punkt 2 jest ważniejszy niż wygląda** — to jest **ósma instancja klasy „awaria na ścieżce
submisji, niewidoczna dla smoke"**: hook napisany poza `try`, który w smoke działa (bo bundl jest
ten sam), a w rerunie może wywalić notebook **przed startem**. To jest dokładnie mechanizm, który
dał nam 0.00 przy `concurrency=120`. **Gemma znalazła go czytając kod, nie mierząc.**

**v15** (`07bf05e0`, 08:12) = *„the opener hint is the right lever, so take it and keep 20"*:

> **Lineage: v13.2 (`6b10853`) → v13.3-arena (Smak `5548d35`) → v15.**
> **v15 = v13.3-arena + trzy rzeczy z v14, które są env-only albo read-only. Nie ma tu ani jednego
> nowego patcha**, więc certyfikacja v13.3 (**7/7 na czystym r033, 11/11 winpath, standalone ==
> patched, playbook 14/14 na silniku**) **przenosi się bez zmian**.
>
> **Diff v15 vs v13.3 to DOKŁADNIE komórki: 1 (nazwa wariantu), 2 (`ESCALATE_ACTIONS = 20`
> + komentarz), 26 (guard sondy c45), 30 (sonda budżetu), nowa 37 (sonda rosteru). Nic więcej.**

**Kluczowa interakcja, którą Gemma wyłapała (§1 v15) — i to jest argument za 20, nie za 10:**

> *„To ma znaczenie **SZCZEGÓLNIE TERAZ**, bo v13.3 dokłada hint „batchuj". **DWA NACISKI NARAZ:**
> „wykonuj więcej akcji na turę" i „przestań działać, zbuduj model" — **przy progu 10 drugi wygrywa
> na pierwszych ~10 akcjach każdego poziomu**. Przy 20 hint ma czas zadziałać."*

**Czyli `ESCALATE_ACTIONS=10` z v13.2 nie tylko kosztuje 15,3 % puli — ono KONTROWAŁO opener hint,
który jest właściwą dźwignią.** Dwie zmiany, które osobno wyglądają sensownie, razem się znoszą.
**To jest ta sama lekcja co „nie stackować zmian" (błąd śmiertelny #8), ale w wersji subtelniejszej:
zmiany mogą się znosić, nawet gdy każda jest uzasadniona.**

**Sonda rosteru w v15 (komórka 37) rozstrzyga spór, o który proszę od dwóch tur:**

> *„czyta `bm.game_runs`, pisze `roster_probe.jsonl` i drukuje werdykt o powtarzalności bazowych
> kodów gier — czyli czy pamięć win-path jest warta **0** czy **+5…15**. Dodatkowo **alarm:
> `actions_per_call < 1,5` → batch pressure nie działa**."*

**To jest lepsze niż mój pomysł „pobierz log rerunu z przeglądarki"**, bo:
* działa **w każdym** runie, nie tylko w tym, którego log user ręcznie pobierze,
* daje **werdykt**, nie surowe ID,
* i **mierzy przy okazji, czy batching zadziałał** (`actions_per_call`) — czyli bramkę GO/NO-GO
  dla jedynej dźwigni, w którą celujemy. **Moja baza porównawcza: 4,357 akcji/wywołanie z r019.**

---

## 6. ⚠️ Jeden spór faktualny, który v14/v15 rozstrzygnie — i w którym mam dane przeciwne

v14/v15 README §2, podstawa sondy budżetu:

> *„we **wszystkich trzech** zapisanych runach **każda gra kończy się dokładnie na capie**
> (`max(final_wallclock_seconds) == min(...) == 48 / 48 / 90 min`). **Gra nie zatrzymuje się sama**,
> więc cap jest przydziałem akcji."*

**To jest sprzeczne z moim pomiarem dwóch runów, które sam przeliczyłem z surowych `benchmark.json`:**

| run | gry kończące się WCZEŚNIEJ niż cap | dowód |
|---|---|---|
| **r093** (v11) | **3 z 10**: `g50t` **1499 s**, `cn04` **1609 s**, `tn36` **1692 s** (pozostałe 7: 2871–2893 s) | `r093/output-pick/benchmark.json`, pole `final_wallclock_seconds` |
| **r085** (c45) | **1 z 10**: `tn36` **2166 s** (pozostałe 9: 2880–2885 s) | `r085/output-pick/benchmark.json`, j.w. |

> **Czyli „każda gra kończy się dokładnie na capie" NIE JEST prawdziwe ani dla r085, ani dla r093.**
> Nie wiem, które trzy runy Gemma miała na myśli (prawdopodobnie r085/r110/r118 — i nawet wtedy
> r085 ma `tn36` przy 2166 s). **Oznaczam to jako rozbieżność, nie jako obalenie**, bo nie znam
> ich zestawu.
>
> **Dlaczego to ma znaczenie:** z „gra nie zatrzymuje się sama" Gemma wnioskuje, że **cap jest
> przydziałem akcji** (`akcje = cap / sekundy_na_akcję`). Ale mój `r093` pokazuje **trzy gry, które
> zatrzymały się same**, z `state=gave_up` i logiem `level budget exhausted (… min_done=0)` —
> czyli **przez `ABANDON` z mojego patcha 0004** (`OCENA-CODEX-7Z.md` §2.2, §3.3). **Jeśli gry
> mogą kończyć się wcześnie, to cap NIE jest jedynym przydziałem, a mój bug `min_done=0` jest realny
> i mierzalny** (3 gry × 1188–1381 s = 3840 s i ~243 600 tokenów oddanych).
>
> **Rozstrzygnięcie jest już zbudowane: sonda budżetu v15** loguje liczbę gier, `n_passes`,
> concurrency, budżet notebooka, uczciwy udział, cap i iloraz — **a `bm.game_runs` ma
> `final_wallclock_seconds` per gra**, więc jeden przebieg pokaże, czy rozrzut jest zerowy.
> **To jest dobrze zaprojektowane i nie muszę tego rozstrzygać przed slotem.**

---

## 7. Czy mam plan na coś lepszego niż v13.2? — odpowiedź uczciwa

### 7.1 ❌ Nie zbuduję własnej wersji notebooka. Trzy powody, wszystkie twarde.

1. **Nie mogę jej zweryfikować.** Warunkiem certyfikacji jest `verify_v13.py --bundle <r033> --tests`
   na **czystym bundlu Franzena** (6/6 lub 7/7 patchy, kompilacja drzewa, testy **na spatchowanym
   drzewie**). **Nie mam bundla r033, nie mam `arcengine`, nie mam GPU, nie mam `cargo`**
   (2 CPU / 3,9 GB RAM). Mój sandbox nie odtworzy nawet `test_plan_commit.py` (3 z 12 testów
   wymagają `inference.agent.python_tool_sandbox` z bundla — potwierdził to 7911f950 niezależnie).
2. **Nie mogę jej przetestować przed spaleniem slotu.** Zostały **3 sloty** (31.10, 1.11, 2.11 —
   30.10 jest dziś i Smak planuje go zużyć). Przy σ≈2,5–3,9 i progu istotności +5 pkt
   **niezweryfikowany pakiet mojego autorstwa byłby najmniej pewną rzeczą w kolejce.**
3. **v15 już jest lepszy i jest zweryfikowany.** Diff v15 vs v13.3 = **5 komórek**, dziedziczy
   certyfikację 7/7 patchy, i zawiera **obie** rzeczy, które sam bym dodał (sonda rosteru, sonda
   budżetu) plus **dwie, na które bym nie wpadł** (guard hooka c45 poza `try`; interakcja
   opener-hint ↔ eskalacja).

> **Uczciwa odpowiedź na „a może sam zrobisz lepszą wersję": NIE, bo zbudowałbym rzecz
> niezweryfikowalną i zużyłbym na nią slot, którego nie ma.** Wartość, którą mogę dodać, jest
> **inna**: pomiar, który obala wspólne założenia (§1, §2), i ranking (§7.3).

### 7.2 ❌ „Dogonić liderów" = 50+ — podtrzymuję, że to nieosiągalne, i teraz mam jeden dowód więcej

Próg top-5 = **51,04** (yktori), Chen **75,56**. Nasza linia: średnia **25,77**, σ **3,93**,
najlepszy draw bazy **35,35**. **Wymagany skok +25,3 pkt = +6,4 σ.**

**Nowy dowód, który doszedł w tej turze i który jest silniejszy od poprzednich:** jedyną dźwignią
o właściwej skali jest `tok/akcję` (647 → ~370 dla 400 akcji). **Zmierzony koszt samej dyrektywy
eskalacyjnej przy progu 10 to 15,3 % puli tokenów gry** — czyli dźwignia, która ma **obniżyć**
zużycie tokenów, przy złym progu je **podnosi**. **To pokazuje skalę trudności: nawet poprawna
co do kierunku zmiana musi być skalibrowana pomiarem, a my mamy 3 sloty i σ≈3.**

Podtrzymuję też: **WM GPT-5.4 = 24.67 < nasze 27,21** (`OCENA-ARENA-V13.md` Smaka), więc scaffold
paper01 bez GPT-5.5 nie daje 56.81. A T3 (world-model + planer) jest **niezmierzony na open-weights**
i niezmierzalny w 3 slotach.

### 7.3 ✅ Co realnie rekomenduję — ranking po tej turze

| # | działanie | koszt | wartość |
|---|---|---|---|
| **1** | **Wysłać v15** (nie v13.2, nie v14) — ma zmierzony próg 20, opener hint, patch 0007 (log replay), guard hooka, **i obie sondy** | 1 slot | ~28–31 **+ rozstrzyga roster i mierzy `actions_per_call` w tym samym biegu** |
| **2** | **Przeczytać z logu tego runu: `roster_probe.jsonl` + `budget_probe.json` + `actions_per_call`** | 0 | rozgałęzienie na 1.11: roster cykliczny → zostawić `WINPATH=1`; `actions_per_call` < 1,5 → batching nie działa i trzeba innej dźwigni |
| **3** | **Test osiągalności** (`OCENA-V13-2.md` §5) + asercja kontraktu mocka (§3.1) | 0 GPU, CPU | łapie klasę bugów, która kosztowała 4 recenzje |
| **4** | **Parser `serve.log` jako strażnik regresji** — uruchamiać na **każdym** nowym runie | 0 | ~5 min; wykryje nasycenie KV, **gdyby** pojawiło się przy innej konfiguracji |
| **5** | 31.10 → **drugi draw v15** (nie inna konfiguracja) | 1 slot | σ≈2,5–3,9 ⇒ dwa drawy to minimum |
| **6** | 1.11 → rozgałęzienie z pkt 2; 2.11 → select best | 2 sloty | ochrona przed szumem |

**Czego NIE robić** — stan po tej turze (dwie pozycje WYCOFANE, trzy NOWE):
* ❌ ~~parsowanie `serve.log` jako dźwignia nr 1~~ — **WYCOFANE**, hipoteza obalona (§1)
* ❌ ~~„odzyskać 17,2 ms/token"~~ — **WYCOFANE**, nie ma czego odzyskiwać; 8B już tak działa (§2)
* ❌ `ESCALATE_ACTIONS = 10` — **zmierzone jako 19× za czułe**: 154 wstrzyknięcia, 15,3 % puli,
  31/32 poziomów „przestań próbować" przed baseline'em, i **kontrowanie opener hintu** (§3, §5)
* ❌ 27B (0,73 / 0,27 / 1,18) · parametry serwingu (−7…−8) · `n_passes>1` · search offline
  (0.20 / 0-113) · podnoszenie `max_runtime_s_per_game` (cap nigdy nie wiąże) · stackowanie zmian
* ➕ **NOWE:** ❌ budowanie priorytetu na **cytowanej tabeli** bez sprawdzenia tożsamości artefaktu (§2.1)
* ➕ **NOWE:** ❌ przenoszenie **mechanizmu** z cudzej konfiguracji (16 strumieni / 69k kontekstu)
  na naszą (10 / 131k) bez przeliczenia (§1)
* ➕ **NOWE:** ❌ hooki pisane **poza `try`** w komórce ustawiającej `bm.solver.*` — brak atrybutu
  w innym revision bundla = martwy notebook przed startem (§5, v14 pkt 2)

**Oczekiwanie pozostaje ~28–31. Cel: srebro ≈32.33. Do liderów (51,04 / 75,56) droga nie istnieje
w 3 slotach — i wolę to powiedzieć dziesiąty raz, niż obiecać jedenaście.**
