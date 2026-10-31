# Audyt pakietu 31.10 (kontroler symboliczny) i wynik 13.28 — co to zmienia

**Materiał.** `START-HERE-REVIEW-20261031.md` (upload; bajt w bajt = `arc-agi-3/analysis/START-HERE-REVIEW-20261031.md`
na gałęzi `Smak-Domu-Konkurs@codex/arc-local-lab-v18-20261030`, 4683 B) + cztery dokumenty, kod,
testy i surowe JSON-y z tej gałęzi (komity `f730639`, `aec6c3e`, `91f1ce9`, tip `3926007e`).
Obrazek dołączony do zlecenia — patrz §7, **nie jest leaderboardem ARC-AGI-3 i nie został użyty
jako dowód czegokolwiek**.

**Metoda.** Wszystko, co dało się uruchomić na CPU bez arcengine, **uruchomiłem**: ich 35 testów,
moduł na prawdziwej pierwszej klatce ft09, **własne plansze-wabiki** (fałszywe rozpoznania,
sprzeczne mapowania, oscylacja), hash notebooka, arytmetykę RHAE z ich JSON-ów. Czego nie
mogłem uruchomić (Rust, Duck z arcengine, Qwen, rerun Kaggle) — oznaczone jako nieodtworzone.

---

## 0. ❗ Najpierw fakt, który przestawia całą kampanię: **v13.7-final dostał 13.28 w rerunie**

`V13-7-SCORE-STATUS-20261031.md`: **zgłoszenie 57811453, COMPLETE, publicScore 13.28**
(źródło: Actions + own-submissions.csv). Porównanie zapisanych zgłoszeń:

| zgłoszenie | konfiguracja | publicScore |
|---|---|---:|
| 57247568 | **duck v3** | **26.25** ← zmierzony mistrz |
| 57201063 | — | 23.94 |
| 57125322 | — | 24.66 |
| 57737623 | v11 | 23.89 |
| **57811453** | **v13.7-final** | **13.28** |
| 57629847 | c45 | 0.00 |
| — | 27B slot B | 1.18 |

**Spadek względem v11: −10.61 pkt; względem mistrza: −12.97 pkt.** Smoke v13.7 = **22.59**,
czyli luka smoke→rerun **−9.31** (dla v11 była **+5.34** — smoke nie predykuje nawet **kierunku**).
Przy σ≈3.9 (drawy Franzena) różnica 10.61 to **≈2.7σ** ⇒ **to regresja konfiguracji, nie losowość**.
Dokument dyscyplinowanie nie przypisuje przyczyny („bez dowodów") — i ja też nie przypiszę;
kandydaci do ablacji to winpath-replay, self-pace, opener hint i sondy, jako **hipotezy**.

**Konsekwencja dla mnie — self-korekta nr 19.** Wczoraj napisałem: *„slot 30.10 =
`duck-v13-7-final` rev2 — ZGODA bezwarunkowa"*. **To było epistemicznie błędne i zostało
sfalsyfikowane pomiarem.** Moje audyty dowiodły rzeczy prawdziwych, ale **o czym innym**:
że 0010 jest dormant (≡ v13.6), że certyfikat i bramka są czyste, że slug i `code_file` są własne.
**Nie dowiodły — i nie mogły — że linia v13.x dobrze punktuje, bo linia v13.x nie miała wtedy
ANI JEDNEGO pomiaru rerun.** Słowo „bezwarunkowa" było błędem: poprawna formuła brzmiała
„najlepiej certyfikowany kandydat, **o niezmierzonym rerunie**, przy luce smoke→rerun ±10".
Teraz rerun jest zmierzony: **13.28**. **Wycofuję poparcie dla linii v13.x jako kandydata slotu.**

**Konsekwencja dla instrumentów — self-korekta nr 20.** Dokument pisze: *„Wzrost actions/call
do 5.3 oraz arbitralny próg 6.0 NIE są prognozą 50 pkt ani wystarczającym kryterium GO"* —
**przyjmuję**. Moja „bramka 7911 ≥ 6.0" była zapożyczoną od 7911 **implikacją wystarczalności**
(253 akcje/grę ⇒ 50 pkt), nie zwalidowanym predyktorem wyniku. **Degraduję a/call z „bramki"
do „diagnostyki"**: przydatna do czytania, czy hint openerowy działa, **bezużyteczna jako GO/NO-GO**.
(Uwaga: 5.3 w smoke v13.7 jest *poniżej* 6.0, więc nawet jako diagnostyka wskazywała kłopot —
ale to zbieżność, nie walidacja.)

**Konsekwencja operacyjna.** Zostały sloty 31.10 / 1.11 / 2.11 i **final submission 2 XI**;
w semantyce Kaggle liczy się zgłoszenie finalne. **Jedynymi konfiguracjami z DOBRYM pomiarem
rerun są v3 (26.25) i v11 (23.89).** Każda niezmierzona zmiana (linia v13.x, hybryda template)
jest przy tym stanie wiedzy zakładem o ujemnej wartości oczekiwanej. **Patrz §6.**

---

## 1. Co pakiet TWIERDZI i co z tego odtworzyłem

| # | twierdzenie | werdykt |
|---|---|---|
| 1 | notebook `duck-lab-candidates/template/agent.ipynb` ma SHA256 `550eb185…d5fa` | ✅ **POTWIERDZONE co do znaku** (pobrałem, `sha256sum` zgodny) |
| 2 | 3 poziomy ft09 w 4+7+14 = 25 akcjach, ~4.77 s, 0 wywołań LLM, 0 tokenów | ✅ **SPÓJNE**: `game-run.json` ma dokładnie 25 rekordów `ACTION6` z `generated_tokens: 0`; pierwsza akcja `{x:39,y:39}` |
| 3 | moduł wyprowadza regułę z obserwacji i **pierwsza zanotowana akcja** wynika z pierwszej klatki | ✅ **ODTWORZONE**: `infer_copy_action(initial_grid)` → `(6, x=39, y=39, expected_color=8)`, model `{2:9, 0:8}`, 4 panele — **dokładnie pierwsza akcja z tracku** |
| 4 | ich testy przechodzą (dokument: 42; plik `tests/test_template_transfer.py`) | ✅ **35 passed** — po dociągnięciu fixture `causal-agent-20261031/ft09-initial-grid.json`. **Moje pierwsze 33 porażki były MOIM brakującym plikiem**, nie ich błędem |
| 5 | hybryda 3 poziomy vs kontrola 0 przy 8192 tokenach obu ramion | ✅ **SPÓJNE** wewnętrznie: 47 vs 56 wywołań API, 0 błędów, limit czasu niewiążący; kontrola 2 akcje |
| 6 | fallback do Qwena: 56 wywołań, **0 dalszych akcji, 0 ukończeń** | ⚠️ **SPÓJNE z logiem, ale to POMIAR SŁABOŚCI Qwena, nie siły kontrolera** — patrz §3 |
| 7 | 75/75 identycznych śladów backendów NumPy vs Rust na 25 grach | ⚠️ **PRZYJMUJĘ**: `public25-final-comparison.json` deklaruje 75/75; **nie mam arcengine ani ich evala, więc nie odtwarzam**. Kod `rectangles.rs` przeczytany; **zgodność wiarygodna, niezmierzona przeze mnie** |
| 8 | Rust+Rayon16 ≈ **33.4×** dla kernela prostokątów (z narzutem ctypes) | ⚠️ **NIEODTWORZALNE U MNIE** (brak `rustc`/`cargo` w sandboxie). `structural-verification.json`: NumPy 0.29244 s, Rust serial 0.01548 s, Rayon16 0.00875 s. **Kwalifikacja uczciwa**: „Rectangle feature kernel only; excludes planning, game engine and LLM" |
| 9 | moduł **abstynuje na 24 z 25 publicznych gier** | ✅ **TO NAJSILNIEJSZE OGRANICZENIE I SAMI JE PODAJĄ**: pokrycie = `[["ft09", 3, 25]]` |
| 10 | „to nie ślepy test, nie prognoza Kaggle, nie potwierdzenie 50+" | ✅ **UCZCIWE I ZGODNE Z MOIM POMIAREM** (§4) |
| 11 | nazwa gałęzi `…-v18-…` jest historyczna, notebook **nie jest** testowaną wcześniej v18 | ✅ **ZGODNE z moim drzewem linii wersji** — v18 nigdy nie istniała jako zmierzony pakiet; nazwa to pułapka, dobrze oznaczona |
| 12 | „nie zgłaszaj notebooka bez osobnej zgody użytkownika" | ✅ **PRZYJMUIĘ JAKO WIĄŻĄCE** — zbieżne z BEZPIECZNIKIEM |

---

## 2. Audyt kodu: obserwacje, izolacja, fallback

**Dozwolone obserwacje — CZYSTO.** `template_hook.install`monkey-patchuje `ToolAgent.analyze`
i przekazuje kontrolerowi wyłącznie `frame.grid` (piksele), `valid_actions` (legalne sterowanie)
i `frame.level` (publiczny numer poziomu). **Nie ma ID gry, baseline'ów, stanu silnika, funkcji
punktacji, plików rozwiązań.** Akcja idzie przez **istniejące narzędzie Python Ducka**
(`self._run_python_tool(state_path, {'code': 'print(action([...]))'})`) ⇒ przez prawdziwy sandbox
i prawdziwy harness, nie przez boczną ścieżkę. ✓

**Fallback — POPRAWNY.** `if action is None:` → w trybie hybrydowym `return original(self, *args,
**kwargs)` (oryginalny analizator LLM); w `ARC3_TEMPLATE_ONLY=1` → callback stopu albo jawny
`ControllerAbstained`. ✓ Rozgraniczenie „abstynencja ≠ crash" jest zrobzone dobrze (poprawili
wcześniejszy adapter, który rzucał wyjątkiem).

**Izolacja pamięci między grami — POPRAWNA.** Instancja kontrolera jest kluczowana na
`self._template_runtime = str(state_path.resolve())`; nowa ścieżka runtime ⇒ **nowa instancja**
i zero `_template_actions`. Wewnątrz instancji `learned` przenosi się **między poziomami**
(to zamierzony transfer) i jest kasowane przy sprzeczności (`self.learned = None`). ✓

**Samounieważniająca się predykcja — NAJLEPSZY ELEMENT.** Każda akcja zostawia `prediction`
z `expected_color`; na następnej klatce niezgodność ⇒ `rejected = True`, `learned = None`,
moduł **wychodzi z poziomu po jednej błędnej akcji**. To zamienia „fałszywe rozpoznanie"
z katastrofy w koszt jednej akcji. ✓

---

## 3. Ryzyko fałszywego rozpoznania — **mój własny pomiar: 0/60**

Zbudowałem plansze-wabiki o **tej samej geometrii** co ft09 (64×64, kafle 6, 4 panele, model
`{2:9, 0:8}`) i mierzyłem, czy kontroler klika:

| wabik | konstrukcja | wynik | oczekiwanie |
|---|---|---|---|
| sanity | prawdziwa pierwsza klatka ft09 | **klik (6,39,39)** | klik ✓ |
| B | wszystkie niezgodności naprawione wg reguły | **None** | abstynencja ✓ |
| A | sprzeczne mapowanie symboli w panelu referencyjnym | **None** | abstynencja ✓ |
| C | **60 plansz z losowym przemalowaniem 10 % pikseli** | **0/60 kliknięć** | abstynencja ✓ |

**Fałszywe rozpoznania na wabikach dopasowanych geometrycznie: 0/60.** Razem z mechanizmem
samounieważnienia daje to **niskie** ryzyko fałszywego rozpoznania — **przyznaję pakietowi
ten punkt w pełni**.

## 3b. ❗ Ale: **pętla stall jest NIEOGRANICZONA — mój zarzut wykonawczy**

Wabik D: komórka, która po kliknięciu przyjmuje oczekiwany kolor na jedną klatkę, a potem
**wraca** (oscylacja). Predykcja waliduje się co klatkę, więc `rejected` nigdy nie następuje,
a moduł wnioskuje na nowo i klika dalej:

```
WABIK D oscylująca komórka: akcji kontrolera w 60 klatkach = 60
```

**W `TemplateTransfer.act` ani w hooku NIE MA limitu akcji na poziom.** W semantyce RHAE akcje
są **mianownikiem** punktacji poziomu (`min((baseline/akcje)², 1.15)`), a w hybrydzie zjadają
wspólny budżet akcji i czasu. **Na ukrytej grze z oscylującym lub samopowracającym elementem
ten moduł może spalić cały poziom na klikach, które „walidują się" co klatkę.** W zapisanym
przebiegu to nie wystąpiło (25 akcji i oddanie sterowania), więc jest to **ryzyko, nie obserwacja**
— ale koszt naprawy jest jednej linii, a koszt wystąpienia to cały poziom.

**Rekomendacja techniczna (przed jakąkolwiek promocją):** licznik akcji na poziom w instancji
kontrolera; po K akcjach bez wzrostu `level` ⇒ `return None` (fallback) zamiast dalszych klików.
Druga, mniejsza: `install()` nie sprawdza podwójnego założenia (dwukrotne wywołanie = podwójny
wrap `analyze`) — warto strzec flagą.

## 3c. Słabość Qwena nie jest siłą kontrolera

Hybryda „3 vs 0" składa się z dwóch faktów: kontroler ukończył 3 poziomy **i** Qwen27B-local
przy 8192 tokenach nie ukończył nic, nawet po przejęciu sterowania (56 wywołań, 0 akcji).
**Drugi fakt to pomiar słabości lokalnego, ściętego budżetem Qwena — znany z tej kampanii
(27B-local = 1.18 w rerunie).** Na docelowym Flash-Next/SGLang fallback może zachować się inaczej,
czego pakiet sam nie ukrywa („Nie wykonano pełnego A/B hybrydowego Duck z docelowym
Flash-Next"). **Wiwniosek „hybryda > baseline" nie przenosi się na konfigurację konkursową
bez tego A/B.**

---

## 4. Ile to jest warte w punktach — arytmetyka, nie obietnica

ft09 ma **6 poziomów**; ukończone 3 ⇒ waga `Σw(done)/Σw(all) = (1+2+3)/(1+…+6) = 6/21`
= **28.5714 %** — **dokładnie `score_delta` z `paired-comparison.json`** ✓ (arytmetyka zgodna
z oficjalnym RHAE: średnia ważona numerami poziomów, cap per-gra).

| horyzont | udział ft09 | przyrost średniej |
|---|---|---:|
| 25 gier publicznych | 1/25 | **+1.14 pkt** |
| 110 gier ukrytych | 1/110 | **+0.26 pkt** |

**I kluczowe: poza grą rozwojową dopasowanie wynosi 0/24 publicznych gier.** Estymator
punktowy liczby gier tej rodziny wśród 110 ukrytych = **0** (górna granica 95 % ≈ 13 gier
⇒ do +3.4 pkt, ale to granica, nie oczekiwanie). **⇒ Kontroler jest wynikiem BADAWCZYM
o wartości oczekiwanej bliskiej zera dla wyniku konkursowego — i dwa rzędy wielkości mniejszym
niż regresja −10.61, którą właśnie zmierzono na linii v13.x.** Pakiet sam to kwalifikuje
identycznie; **przyznaję im pełną uczciwość i nie dopisuję nic ponad to**.

---

## 5. Odtwarzalność — bilans

**Odtworzone przeze mnie:** hash notebooka · 35/35 testów (po dociągnięciu fixture) · pierwsza
akcja z pierwszej klatki · arytmetyka 28.5714 · struktura `game-run.json` (25 × `ACTION6`,
`generated_tokens: 0`, `base_actions_per_level: null`) · abstynencje na wabikach B/A/C ·
brak limitu akcji (wabik D).

**Nieodtworzone (oznaczone, nie uznane):** przebieg Duck/arcengine (brak arcengine: wymaga
Pythona ≥ 3.12, sandbox ma 3.11.2) · przebieg Qwena · kompilacja i pomiar Rust (**brak
`rustc`/`cargo`**) · 75/75 identycznych śladów (przyjęte z JSON) · 33.4× (przyjęte z JSON).

**Uwaga o przyrządach:** `valid_model_run=false` jest **poprawne** i udokumentowane (LLM nie
był uruchamiany); `controller_abstained=false` w trybie hybrydowym **nie liczy przekazań
sterowania** — też udokumentowane, ale to druga w tej kampanii etykieta pola, która znaczy co
innego niż sugeruje nazwa. Kosmetyka z higienicznego punktu widzenia; odnotowuję, bo dokładnie
ta klasa zjawiska kosztowała nas wcześniej cichy skip w certyfikacie.

---

## 6. Rekomendacja operacyjna (stan po 13.28)

**1. Zgłoszenie finalne (i slot 31.10, jeśli ma być drawem): ZMIERZONY MISTRZ — duck v3 (26.25).**
To jedyna konfiguracja z dobrym pomiarem rerun i rozkładem drawów μ≈25.8, σ≈3.9. Przy semantyce
„liczy się zgłoszenie finalne" ostatnie zgłoszenie musi być konfiguracją o **najwyższej wartości
oczekiwanej**, nie o najładniejszym certyfikacie.

**2. NIE linia v13.x** — zmierzona: **13.28**. Certyfikat, bramka i dormancja 0010 pozostają
prawdziwe i **nie mają już znaczenia decyzyjnego**: certyfikat mierzy aplikację patchy, nie wynik.

**3. NIE hybryda template jako zgłoszenie** — punktowy szacunek ≈ 0 pkt na ukrytych, n=1,
jedna gra rozwojowa, brak A/B na docelowym modelowym stosie. **Zgodnie z pakietem i z
BEZPIECZNIKIEM: notebook nie idzie na Kaggle bez osobnej zgody usera.**

**4. Kontroler = kierunek badawczy z jedną naprawą przed promocją:** limit akcji na poziom (§3b).
Jeśli kiedykolwiek wróci jako kandydat, wraca **wyłącznie** jako delta nad zmierzonym mistrzem
i wyłącznie po A/B na docelowym stosie, z metryką `completed/game` **i** `actions/game`
(akcje są mianownikiem RHAE — patrz mój audyt v13.7 §8).

**5. Smoke NIE jest predyktorem.** Luki: v11 **+5.34**, v13.7 **−9.31**. **Żadna decyzja slotu
nie stoi na smoke** — to trzecie już podejście do tej reguły w tej kampanii i tym razem ma
dwa pomiary przeciwnych znaków.

**6. a/call = diagnostyka, nie bramka** (self-korekta nr 20). Czytać z logu nadal warto,
ale GO/NO-GO stoi na **zmierzonym rerunie konfiguracji lub na braku takowego**.

---

## 7. Obrazek dołączony do zlecenia — NIE jest leaderboardem ARC-AGI-3

Zrzut pokazuje kolumny `# / Team / Members / Score / Agents / Last / Join` i wyniki
**1208.9, 1164.2, 1160.9, 1151.1, 1148.4, 1131.1, 1125.2, 1075.2, 1073.6, 1070.7** dla zespołów
**YumeNeko, バーベナヘレナでコンボ決めたい連合, Stephen Schott, やる気元気ミワハルキ 2nd ver.,
Kentaro Totsuka, Colton Martin, Zedan Soorya, Akmal Xodarev (Busya PRIME), JerryChen, pao**.

**To nie jest tabela, którą śledzę i nie może nią być:**
- **Skala 1000+ jest niekompatybilna** z wynikiem ARC-AGI-3 na Kaggle (mean of game scores,
  historyczne maksimum 75.56; nasze pasmo 23–26).
- **Żadne z nazwisk nie występuje** w moim odczycie leaderboarda Kaggle (Chen, Tufa, Turducken,
  the last dance, yktori, mtg, NVARC3, Zatravkin, 復活, artificialagencylab, Majkel1337) **ani**
  w liście 40 handle'i z `read_top10.py` na gałęzi `codex/arc-top10-research-20261030`
  (yktori, grigoriyzatravkin, darraghdog, cpmpml, …), która czyta **dokładnie ten konkurs**
  przez `kaggle competitions leaderboard -c arc-prize-2026-arc-agi-3`.
- Kolumny `Agents` (odtwarzanie przebiegów) i `Join` (dołączanie do zespołu) oraz ranking
  rzędu 1000–1200 pasują do **areny agent-vs-agent z punktacją typu Elo** (klasa Battlecode /
  Lux AI / Screeps, obecna w briefie `konkursy-ai-2026.md`), **nie** do ARC-AGI-3.

**Traktuję go więc jako materiał nierozpoznany i nie wyciągam z niego żadnych wniosków
o pozycji, progu nagród ani sile konkurencji.** Jeśli ma mieć znaczenie decyzyjne, potrzebuję
źródła (URL/PLATFORMA); progi nagród i deadline ARC-AGI-3 pozostają jak w moich wcześniejszych
audytach, zweryfikowane na stronie konkursu, **nie z tego zrzutu**.

---

## 8. Self-korekty i nowe „nie robić" tej tury

**19.** *„slot 30.10 = v13.7 rev2 — ZGODA bezwarunkowa"* → **wycofane**. Poparcie dotyczyło
konfiguracji **bez ani jednego pomiaru rerun**; pomiar przyszedł (13.28) i falsyfikuje linię
v13.x. Poprawna formuła: „najlepiej certyfikowany kandydat **o niezmierzonym rerunie**".
**20.** *„bramka 7911: a/call ≥ 6.0"* → **degradacja do diagnostyki**. Była implikacją
wystarczalności zapożyczoną od 7911, nie zwalidowanym predyktorem; pakiet ma rację.

**Moje błędy narzędziowe/analityczne tej tury:** 33 porażki testów pakiety były **moim**
brakującym fixture (`ft09-initial-grid.json`), nie ich błędem — **diagnoza przed oskarżeniem
zadziałała, ale kosztowała jeden cykl**; oraz pierwsza wersja mojego wabika D miała martwą
linię symulacji kliknięcia, którą poprawiłem przed policzeniem 60 akcji.

**NOWE „NIE ROBIĆ":** nie promować konfiguracji, której **rerun nie zmierzono**, niezależnie
od liczby zielonych certyfikatów · nie czytać „hybryda 3 vs 0" bez rozłożenia na „kontroler 3"
i „słaby fallback 0" · nie uznawać przyspieszenia **kernela** za przyspieszenie gry · nie
przyjmować zrzutu ekranu za leaderboard bez identyfikacji platformy · nie ufać etykiecie pola
(`controller_abstained`, `valid_model_run`) bez przeczytania semantyki.

**BEZPIECZNIK:** nic nie wypchnięte na Kaggle, nic nie zgłoszone, notebook template **nie
tknięty**; żadna inna gałąź niezmieniona. Wszystkie pomiary w `/tmp`.
