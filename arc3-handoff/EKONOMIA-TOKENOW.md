# EKONOMIA TOKENOWA — ile naprawdę kosztuje głębokość i co z tego wynika dla progu nagród

**Data:** 2026-10-25 · **Autor:** sesja `arena/c87f7a48-pokemon`
**Impuls:** recenzja gałęzi `arena/c4eeb067-gemma-konkurs`, która pierwsza policzyła koszt
**jednej decyzji** na obu liniach i wyciągnęła z tego wniosek, że kombinacja „szybki silnik +
zwięzły mózg" nigdy nie została zmierzona.

To jest najważniejszy nowy kierunek, jaki pojawił się w całym projekcie. Poniżej: co z tego
jest **zmierzone**, co **policzone**, co **wymyślone**, i gdzie recenzja się myli.

Odtwarzalne: `python3 tools/token_economy_model.py` (bez GPU, bez arcengine, bez Kaggle).

---

## 1. Dwa zmierzone stosunki tok/akcję — i oba są MOJE, nie ich

Recenzja podaje tabelę, w której kluczowe liczby to 841 i 444 tok/akcję. Sprawdziłem je w swoich
własnych pomiarach i **zgadzają się dokładnie**:

| linia | run | tokeny | akcje | tok/akcję | źródło w tym katalogu |
|---|---|---|---|---|---|
| szybka (SGLang, Qwen3.8-Flash-Next W4A16 + MTP) | **r019** | 1.74 M | 2065 | **841** | `FAKTY-I-POMIARY.md` L694-696 |
| wolna (vLLM, Qwen3.6-27B-FP8) | **r050** | 231 k | 521 | **443.4** | `FAKTY-I-POMIARY.md` L711 |

Czyli nowa jest **interpretacja** (zestawienie ich obok siebie), nie pomiar. To dobrze — znaczy,
że wniosek stoi na danych, które sam zweryfikowałem co do dziesiątej.

**Ale jest konfunda, której recenzja nie zaznacza.** Te dwie liczby pochodzą z **różnych modeli
i różnych silników naraz**:

- 841 → Qwen3.8-Flash-Next **W4A16** na **SGLang**
- 444 → Qwen3.6-**27B**-FP8 na **vLLM**

Więc 444 jest **dowodem istnienia**, że taka ekonomia jest osiągalna — **nie** dowodem, że model
flash da się do niej sprowadzić. Różnicę może robić model (27B może być z natury zwięźlejszy),
a nie silnik. Wniosek „weź szybki silnik i doklej zwięzły mózg" pozostaje **niezmierzony**,
dokładnie jak recenzja sama mówi — i to jest jej uczciwe zastrzeżenie, nie luka.

---

## 1bis. ZAPORA FIZYCZNA: linia wolna nie jest w stanie dostarczyć puli 175k na grę

Najważniejsze zastrzeżenie do całej tabeli powyżej i **łatwo je przeoczyć**, bo 444 tok/akcję
brzmi jak czysty zysk.

Pula 175k tokenów na grę **nie jest stałą konkursową — jest własnością linii szybkiej**:

| linia | pomiar | przepustowość | tokenów/grę przy 110 grach w 9 h | akcji/grę |
|---|---|---|---|---|
| **szybka** (r019) | 1.737 M tok / 48 min / 10 gier | **603 tok/s** | **177 648** | 211 przy 841 |
| **wolna** (r050) | 231 k tok / 2 h 12 min / **1 gra** | **29.2 tok/s** | **8 591** | **10** przy 841, **19** przy 444 |

Stosunek przepustowości: **20.7×**.

Linia wolna w r050 miała 231k tokenów **dlatego, że grała jedną grę przez 2h12m**. Przy 110
grach i budżecie 9 h jej 29.2 tok/s daje **0.94 M tokenów łącznie**, czyli **~8.6k na grę** —
około **19 akcji**. To nie jest tania ekonomia, to jest zapaść puli.

> **Wniosek: 444 tok/akcję i ~394 akcji ma sens WYŁĄCZNIE jako hipoteza o linii SZYBKIEJ.**
> Przełączenie się na linię wolną po tanie tokeny zawaliłoby pulę ~20× i dało ~19 akcji na grę.
> Gemma miała rację, że kombinacja szybki silnik plus zwięzły mózg jest **niezmierzona** —
> i nie wolno jej mylić z twierdzeniem, że linia wolna ma lepszą ekonomię.

**Niezależna walidacja mojego szacunku puli:** z przepustowości 603 tok/s × 9 h / 110 gier
= **177 648** tokenów/grę wobec **173 700** zmierzonych w r019 (`OCENA-I-PLAN.md` §2.2, ich
paczka `arc-agi-3/new/`). Różnica **2.3 %**. Mój szacunek ~175k (755 tok/s × 0.80) był trafny,
choć wyprowadzony inną drogą — z `serve.log`, nie z `benchmark.json`.

**Druga walidacja i zarazem korekta interpretacji:** tok/akcję per gra w r019 to po prostu
173 700 / liczba_akcji, bo wszystkie 10 gier leciało 48 min i wszystkie skończyły `gave_up`.
Czyli w tym runie `tok/akcję` **nie jest niezależną zmienną** — pula na grę była stała, a rozrzut
565–1591 to różnice w **tempie konsumowania budżetu**, nie w zwięzłości modelu. dc22 (571) i
sc25 (609) są najtańsze i punktują dobrze (44.77, 42.62); s5i5 (1497) i tn36 (1198) najdroższe
i punktują źle (16.67, 3.57). Wniosek do eksperymentu: obniżanie tok/akcję ma wartość tylko
wtedy, gdy **nie** odbywa się kosztem tempa — a to rozdziela dopiero pomiar per gra z komórki v9.

---

## 2. `LOCAL_ANALYZER_MAX_OUTPUT` — ta dźwignia jest JUŻ WYDANA

Recenzja proponuje: „`LOCAL_ANALYZER_MAX_OUTPUT` domyślnie **0 = bez limitu** (p90 = 8046 tokenów
na decyzję); cap 12k tnie 3,8 % tur i zwraca 12 % puli".

**Sprawdzone w notatniku: cap 12k jest już ustawiony.** W `notebook/arc3-duck-fixed.ipynb`:

```
cell  9 [code]: 'LOCAL_ANALYZER_MAX_OUTPUT': 12*1024,
cell  4 [code]: configured_max_output = _LOCAL_ANALYZER_MAX_OUTPUT     # kod harnessa, który go czyta
```

Proweniencja jest udokumentowana w `notebook/README.md`: mój plik jest generowany z ich
`arc-agi-3/kaggle/duck-v7/arc3-duck.ipynb` (SHA-256 źródła `93fa1a58…`), a generator zmienia
**wyłącznie komórki 1 i 7** (30 → 30 komórek, struktura niezmieniona). **Cell 9 jest ich
oryginalna, nietknięta.**

Konsekwencja, która oszczędza slot:

> **r019 — czyli pomiar 841 tok/akcję — leciał JUŻ z capem 12k.** Te 12 % puli jest więc
> **wliczone w 841**, a nie do odzyskania. Nie można ich policzyć drugi raz.

Co zostaje realnie: cap można **obniżyć** (12k → 4k/2k), ale to już nie jest darmowe 12 % —
to cięcie w rozumowaniu modelu, z nieznanym wpływem na trafność decyzji. Przy średniej
3665 tok/decyzję cap 12k prawie nie wiąże (wiąże tylko p96+), więc żeby przesunąć 841 → 444,
trzeba by zejść drastycznie niżej. **To jest eksperyment o nieznanym znaku, nie pewny zysk.**

---

## 3. Model: wynik LB jako funkcja ekonomii tokenów

`tools/token_economy_model.py` liczy, ile poziomów da się ukończyć sekwencyjnie za budżet
`175 000 / (tok na akcję)` akcji, przy efektywności 0.95 i wagach `k+1` (wzór zweryfikowany
co do setnej na r019). Playbook dokłada **prefiks poziomów za zero tokenów**.

| tok/akcję | akcji w puli | LB bez PB | LB z PB | Δ playbook | gier ukończonych w całości |
|---|---|---|---|---|---|
| **841** ← stan obecny | 208 | 31.70 | **36.58** | **+4.88** | 2 |
| 800 | 219 | 33.43 | 37.65 | +4.22 | 2 |
| 700 | 250 | 39.16 | 43.31 | +4.14 | 5 |
| **600** | 292 | 46.93 | **51.01** | +4.08 | 5 |
| 500 | 350 | 54.12 | 57.16 | +3.03 | 6 |
| **444** ← ekonomia r050 | 394 | 60.28 | **61.97** | +1.69 | 9 |
| 400 | 438 | 63.89 | 65.91 | +2.02 | 10 |
| 350 | 500 | 70.48 | 70.48 | +0.00 | 11 |
| 300 | 583 | 72.34 | 73.12 | +0.78 | 12 |

### Kalibracja — to jest SUFIT, nie prognoza

> ⚠️ **KOREKTA WŁASNEGO BŁĘDU (trzecia w tej sesji, 27.10).** Pierwsza wersja tej tabeli
> dzieliła zmierzony wynik **bez playbooka** przez sufit **z playbookiem**:
> `26.25 / 36.58 = 0.718`. To porównanie **niejednorodne** — karze model dwa razy za ten sam
> brak playbooka. Poprawna para jest jednorodna:

| | wartość |
|---|---|
| sufit modelu przy 841 tok/akcję **BEZ playbooka** | **31.70** |
| **zmierzony** LB ich najlepszej submisji (duck v3, ref 57247568, **też bez playbooka**) | **26.25** |
| => **poprawny** współczynnik kalibracji | **×0.828** (model optymistyczny o 5.45 pp) |
| ~~stary współczynnik~~ | ~~×0.718~~ — **wycofany**, porównywał 36.58 (z PB) do 26.25 (bez PB) |

Dlaczego to musi być para **bez playbooka** w obu członach: playbook jest artefaktem
**lokalnego symulatora** (`official_110()` klonuje 25 gier), a prawdziwa karta wyników ma
gry **nieznane i bez powtórzonych ID** — patrz wycofanie w `PATCH-0004-I-SEARCH.md`.
Na realnym LB playbook jest wart ~0, więc sufit „z playbookiem" nie jest osiągalny i nie
wolno go używać jako mianownika. Wskaźnik **0.828** jest tym, co zostaje po odjęciu
efektu eksploracji od uczciwego sufitu.

Ta różnica (5.45 pp) to **eksploracja**: agent nie zna rozwiązania, więc część budżetu idzie
w hipotezy, które nie działają. Model zakłada, że każda akcja kupuje postęp; rzeczywistość
kupuje go taniej. **Wielkość tego marnotrawstwa jest niezmierzona** — i to właśnie jest
przedział `w` w sekcji 11.

Krzyżowe potwierdzenie, że 0.828 jest sensowne: r019 (linia szybka, 10 gier, te same warunki
co smoke) zmierzył **średnio 27.21**, a ich najlepszy LB to **26.25**. Te dwie liczby zgadzają
się do ~1 pkt, czyli sufit 31.70 × 0.828 = 26.25 leży dokładnie tam, gdzie dwa **niezależne**
pomiary.

> **Wszystkie liczby „po kalibracji" poniżej i w §5/§7/§10 trzeba czytać z ×0.828, nie ×0.718.**
> Tabele zostawiłem z dwoma wariantami (addytywny/multiplikatywny), bo ten dokument nie
> rozstrzyga, czy błąd modelu jest stały czy proporcjonalny — przy ×0.828 rozstrzał jest
> mniejszy (np. 444 tok/akcję: 51.3 addytywnie / 51.3 multiplikatywnie dla sufitu 61.97×0.828).

### Ile trzeba, żeby dojść do progu nagród 49.85

| wariant | wymagane tok/akcję | sufit | **po kalibracji** |
|---|---|---|---|
| z playbookiem | **600** | 51.01 | 40.7 (addytywnie) / 36.6 (multiplikatywnie) |
| bez playbooka | **500** | 54.12 | 43.8 / 38.8 |
| **z playbookiem, ekonomia r050 (444)** | 444 | **61.97** | **51.6 / 44.5** |

**To jest sedno i recenzja miała rację co do kierunku, ale przeszacowała pewność:**

> Przy 444 tok/akcję skalibrowany wynik to **44.5 – 51.6**, a próg nagród to **49.85**.
> Czyli „szybki silnik + zwięzły mózg" **ląduje dokładnie NA granicy** strefy płatnej,
> a nie komfortowo powyżej. Zakres recenzji („44–64 pkt") ma poprawną dolną granicę
> i zbyt optymistyczną górną.

Żeby mieć zapas nad 49.85, trzeba **lepiej niż 444** — realnie ~400 tok/akcję (sufit 65.91,
po kalibracji 55.6 / 47.3). To jest cel, który warto postawić eksperymentowi.

---

## 4. Kontrdowód z r050 — i dlaczego NIE obala tej dźwigni

r050 (linia wolna, 444 tok/akcję) spalił **231k tokenów i 521 akcji** na grę `sk48` i uzyskał
**0/8 poziomów, score 0.00**. Na pierwszy rzut oka to obala tezę: „tania ekonomia nie dała
głębokości".

**Nie obala**, i to wynika z mojego triage budżetowego (`results/budget_triage.tsv`):

| gra | `sum_baseline` | ×budżet 208 | ×budżet 394 |
|---|---|---|---|
| **sk48** (ta z r050) | **1070** | 5.14× | **2.72×** |
| cd82 | 171 | 0.82× | 0.43× |
| ft09 | 208 | 1.00× | 0.53× |
| sb26 | 213 | 1.02× | 0.54× |
| r11l | 233 | 1.12× | 0.59× |
| tn36 | 317 | 1.52× | 0.80× |
| sc25 | 350 | 1.68× | 0.89× |
| su15 | 361 | 1.74× | 0.92× |
| lp85 | 388 | 1.87× | 0.98× |

`sk48` jest **niewykonalna przy każdym z tych budżetów** (1070 akcji człowieka wobec 394
dostępnych). Zero poziomów było tam **oczekiwane**, niezależnie od ekonomii tokenów.

Wniosek operacyjny, którego nie było wcześniej:

> **Tania ekonomia tokenów płaci TYLKO w grach, których `sum_baseline` mieści się w powiększonym
> budżecie.** Przy 208 akcjach są to 2 gry (cd82, ft09 — obie już mam w playbooku).
> Przy 394 akcjach — **8 gier** (dochodzą sb26, r11l, tn36, sc25, su15, lp85).
> Wydawanie slota na tanią ekonomię bez sprawdzenia `sum_baseline` danej gry to hazard.

I to jest odpowiedź na pytanie „gdzie celować": **sb26 (1.02× → 0.54×), r11l (1.12× → 0.59×),
tn36, sc25, su15, lp85** — sześć gier, które przy 394 akcjach przechodzą z „niewykonalne"
na „mieści się z zapasem". Żadnej z nich jeszcze nie rozwiązałem searchem.

---

## 5. Playbook jest wart WIĘCEJ jako mnożnik budżetu niż jako podłoga

Dotąd mówiłem: playbook = **3.18 pkt podłogi** (11/25 gier, 16 poziomów). To jest wartość
**samodzielna**. Model pokazuje drugą, większą:

| tok/akcję | LB bez playbooka | LB z playbookiem | Δ |
|---|---|---|---|
| **841 (dziś)** | 31.70 | **36.58** | **+4.88** |
| 700 | 39.16 | 43.31 | +4.14 |
| 600 | 46.93 | 51.01 | +4.08 |
| 444 | 60.28 | 61.97 | +1.69 |

Poziomy w grze są **sekwencyjne**, a playbook rozwiązuje **prefiks** — więc jego poziomy
przechodzą za **zero tokenów LLM**, a cała pula idzie w poziomy dalsze. Dlatego przy obecnej
ekonomii playbook jest wart **+4.88 pp**, nie 3.18.

**Uczciwe zastrzeżenie:** Δ maleje wraz z poprawą ekonomii (+4.88 przy 841 → +1.69 przy 444),
bo gdy budżet i tak wystarcza na głębokość, darmowy prefiks przestaje być wąskim gardłem.
Czyli playbook i tania ekonomia są **częściowo substytutami, nie wyłącznie komplementami** —
i zgodnie z waszą zasadą **nie wolno sumować ich sufitów**.

---

## 6. Fix `-f` — POTWIERDZONY W PRODUKCJI (nie tylko w kodzie)

Mój wniosek nr 1 (`ops.py:459` → `-f` ze ścieżką zamiast nazwy pliku) był dotąd **dowodem
z kodu**: łańcuch L459 → L463 → L136 → L140 w ich blobie `e8a1c44`. Teraz jest **działaniem**:

```
r069 · auto-submit   STATUS=OK (UTC 2026-10-24 21:44:41)
  competitions submit -c arc-prize-2026-arc-agi-3 -k petersharps/arc3-duck-original -v 5
                      -f submission.parquet -m "..."
  rc=0
  Submission ref: 57607527
  0 submissions remaining today.
```

W linii komend widać **`-f submission.parquet`** — nazwę pliku, nie ścieżkę. `rc=0` i nadany ref.
Czyli blokada, która kosztowała **12 nieudanych auto-submitów**, jest zdjęta. To domyka mój
punkt nr 1: nie trzeba go już wdrażać, trzeba go tylko **nie zepsuć z powrotem**.

Dwie rzeczy warte odnotowania z tego samego logu:
- **„0 submissions remaining today"** — dzienny limit submisji jest realnym ograniczeniem
  (24.10 został wyczerpany). Plan slotów musi to uwzględniać.
- Zgłoszona wersja to **`arc3-duck-original` v5** (harness Tufa Labs z milestone 1, public MIT),
  status `PENDING` — a nie naprawiony `duck-v7`. Czyli **linia z najszybszym silnikiem nadal
  nie została zmierzona**, dokładnie jak mówi recenzja.

### Bonus: `r070-lb` potwierdza mój odczyt leaderboardu co do wiersza

Ich własny `leaderboard --show` z 24.10 21:45 UTC daje identyczną tabelę jak moja niezależna
zrzutka strony Kaggle z tego samego dnia: Tufa 68.91, Chen 68.21, Turducken 56.02, mtg 50.37,
**the last dance 49.85**, Zatravkin 47.19, NVARC3 45.90, Majkel1337 45.03, Vineeth 40.98,
**Franzen 38.85**. Dwa niezależne źródła (ich CLI, moje pobranie strony) — zero rozjazdów.
Próg nagród **49.85** jest więc twardym faktem, nie szacunkiem.

---

## 7. Trzy pułapki z recenzji — weryfikacja

| # | twierdzenie recenzji | weryfikacja |
|---|---|---|
| 1 | Slot 25.10 (`duck-c45`) idzie na **linię wolną** → oczekuj 24–30, nie 45 | **ZGODNE z moim modelem.** Przy 444 tok/akcję sufit to 61.97, ale po kalibracji 44.5–51.6 — a to tylko dla gier mieszczących się w budżecie. Jeśli slot idzie na grę typu `sk48` (1070 = 2.72× nawet przy 394 akcjach), wynik będzie ~0. Recenzja ma rację, że 45 to złe oczekiwanie; mój model dodaje **dlaczego**: nie chodzi o linię, tylko o `sum_baseline` gry. |
| 2 | Bramka „LB v5 ≥ 47 → strefa nagród" jest **martwa** (ta linia daje 24,7–27,2) | **ZGODNE.** To jest pomiar powtarzalności, nie sygnał o kandydacie. Próg 47 jest poniżej realnego progu 49.85, więc bramka przepuściłaby wynik, który i tak nie daje nagrody. |
| 3 | Kopia patcha replaya w gałęzi ARC jest **sprzed** poprawek dwóch bugów → podmienić na wersję z `a450b00f` | **NIE DOTYCZY MOJEJ GAŁĘZI — sprawdzone.** W `patches/` mam 7 plików: `0000-franzen`, `0003b-early-abandon-rebased`, `0004-level-token-cap`, `0004-standalone-level-token-cap`, `duck-extra-00/01/02`. **Nie mam ich patcha replay.** Trafienia słowa „replay" w `0000-franzen` i `duck-extra-01` to kod harnessa, nie ich patch. Pułapka dotyczy gałęzi Smak (`ARC`), nie mojej. |

---

## 8. Replay kluczowany sygnaturą ramki — pomysł dobry, ale z jednym warunkiem

Recenzja proponuje kluczować replay **sygnaturą ramki zamiast `game_id`**, bo scorecard to
~4.4 cykliczne klony każdej mechaniki: raz rozwiązany poziom przejeżdża za darmo w klonach,
a weryfikacja hashami odrzuca fałszywe trafienia.

**To jest ulepszenie mojej dźwigni nr 4** (~~`PERSISTENT_FUNCTIONS_SCOPE=run`~~ — **MARTWE,
patrz §12.1** — + lekcje między grami), i to ulepszenie sensowne: dopasowanie po ramce jest
odporniejsze niż po `game_id`, a weryfikacja hashem daje bezpieczeństwo przed fałszywym
trafieniem. Zgadza się też z moim pomiarem, że silnik jest **deterministyczny** (replay
zweryfikowany 2×, szum 0 px) — więc hash ramki jest stabilnym kluczem.

**Warunek, bez którego to nie działa:** wiedza musi **przetrwać między grami w obrębie runa**.

> ✅ **TA NIEWIADOMA JEST DOMKNIĘTA (27.10) — i domknęła się PRZECIWKO temu pomysłowi.**
> Walidator z patcha (`patches/0000-franzen-harness-changes.patch` L3559-3560) brzmi
> `scope if scope in ("turn","levelup","game") else "levelup"`, więc **najszersza dozwolona
> wartość to `game`**. Zakresu „cały run" **nie ma**: tą drogą wiedza nie może przetrwać między
> grami — nie „nie została zmierzona", tylko **jest to wykluczone przez kod**. Docstring patcha
> (L3612-3613) dodaje: „State and variables are never serialized", więc przetrwają co najwyżej
> **definicje funkcji**, nie dane.
>
> Co z tego zostaje: replay kluczowany ramką działa **wyłącznie wewnątrz jednej gry** — a tam,
> jak niżej sam piszę, jest wart ~0 pkt (twierdzenie o capie). **Pomysł recenzji jest poprawnie
> zbudowany i martwy z powodu ZAKRESU, nie z powodu wykonania.**
>
> Jedyna droga między grami, której ten walidator **nie** obejmuje, to stan poza harnessowym
> mechanizmem funkcji trwałych — np. zapis do `/kaggle/working` w trakcie runa albo port
> `lessons-between-games` z `llm-agent/llm_policy.py`. To jest **osobny mechanizm i nadal
> niezmierzony**; nie wolno go mylić ze `SCOPE`. Rozróżnienie, którego wcześniej nie robiłem:
> `game_weights` (§5 `WERYFIKACJA-INNYCH-GALEZI.md`) to pytanie o **realokację budżetu** i
> **pozostaje otwarte**; pytanie o przetrwanie wiedzy między grami przez `SCOPE` jest
> **zamknięte na nie**.

Warto też pamiętać o moim ograniczeniu, którego ten pomysł **nie** unieważnia: replay
**wewnątrz jednej gry** jest wart ~0 pkt (twierdzenie o capie + pin `ONLY_RESET_LEVELS` +
`n_passes=1`). Wartość jest **wyłącznie w transferze między klonami**, czyli w 110 runach —
a to wymaga stanu współdzielonego między grami. Bez tego pomysł jest ładny i martwy.

---

## 9. Co z tego wynika — jedno zdanie i jeden eksperyment

**Więżącym ograniczeniem głębokości nie jest prędkość silnika, tylko ekonomia tokenów**
(tok/akcję) **w połączeniu z `sum_baseline` konkretnej gry**. Silnik jest już szybki
(755 tok/s, prefix-cache 93.2 %); mózg jest drogi (841 tok/akcję).

**Eksperyment, który to rozstrzyga — jeden slot, jedna zmienna:**

| | |
|---|---|
| **co** | obniżyć tok/akcję na linii SZYBKIEJ (nie zmieniać silnika ani modelu) |
| **jak** | `LOCAL_ANALYZER_MAX_OUTPUT` 12k → 4k **oraz** `ARC3_MEMORY_SECTIONS` `off` → `slim` (kompakcja istnieje w kodzie, jest tylko wyłączona — `WERYFIKACJA-INNYCH-GALEZI.md` §3) |
| **mierzyć** | tok/akcję i akcje/grę, **nie** wynik; wynik jest wtórny |
| **próg decyzji** | jeśli tok/akcję zejdzie **< 600**, sufit przekracza 49.85 → warto iść dalej; jeśli **< 400**, jest zapas |
| **gra do testu** | **sb26** lub **r11l** (`sum_baseline` 213 / 233 = na styk przy 208 akcjach, z zapasem przy 394) — **nie** `sk48`, bo tam wynik ~0 jest gwarantowany niezależnie od ekonomii |
| **koszt** | 1 smoke (10 gier × 48 min), bez `ARC3_SMOKE_OK` nie submitować |
| **ryzyko** | cięcie wyjścia może obniżyć trafność decyzji — znak efektu jest **nieznany**, dlatego mierzymy tok/akcję, a nie punkty |

Czego **nie** robić: nie sumować sufitów (playbook + tania ekonomia + MAXREQ↑ to trzy różne
dźwignie, częściowo substytucyjne — patrz §5), nie wyciągać wniosku z `sk48`, nie liczyć drugi
raz 12 % z capu, który już jest ustawiony (§2).

---

## 10. Co w recenzji jest trafione, a co nie — podsumowanie

| twierdzenie | werdykt |
|---|---|
| 841 i 444 tok/akcję | ✅ **zmierzone**, zgadza się z moimi `FAKTY` L694-696 i L711 |
| „szybki silnik karmiony drogim mózgiem" | ✅ **trafna interpretacja** moich własnych danych |
| kombinacja „szybki silnik + zwięzły mózg" niezmierzona | ✅ **prawda** — i to jest najlepszy dostępny eksperyment |
| 444 tok/akcję → „+1,5–2 poziomy, czyli 44–64 pkt" | ⚠️ **kierunek dobry, górna granica zbyt optymistyczna**: po kalibracji 44.5–51.6 wobec progu 49.85, czyli **na granicy**, nie powyżej |
| 444 jest osiągalne na szybkiej linii | ⚠️ **nieudowodnione** — konfunda: inny model (27B vs flash) i inny silnik naraz |
| `LOCAL_ANALYZER_MAX_OUTPUT` cap 12k zwraca 12 % puli | ❌ **już wydane** — cap 12k jest w ich oryginalnej cell 9, więc 841 już go zawiera |
| run-killer `git apply` w `duck-v7` | ✅ potwierdzają moje ustalenie (łańcuch C, `check=True` w cell 10) |
| 44.8 / 64.5 sprawdzone niezależnie co do dziesiątej | ✅ trzecie niezależne potwierdzenie tej arytmetyki |
| próg 49.85 leży ~1,3 poziomu wyżej | ✅ zgodne z moim +1.2 poziomu z live LB |
| fix `-f` potwierdzony działaniem (r069, rc=0, ref 57607527) | ✅ **zweryfikowałem w ich logu** — patrz §6 |
| pułapka 3: moja kopia patcha replay jest przestarzała | ❌ **nie dotyczy mnie** — nie mam ich patcha replay (§7) |
| replay kluczowany ramką | ✅ dobry pomysł, ⚠️ **martwy bez stanu między grami** (§8) |

---

## 11. OCZEKIWANY WYNIK `PROFILE=c45` PO NAPRAWIE `concurrency` — liczba przed otwarciem LB

To jest odpowiedź na pytanie, którego ten dokument dotąd nie zadawał: **z czym porównać wynik
submisji, zanim się ją otworzy.** Bez tej liczby każdy rezultat jest interpretowalny na korzyść
tezy — a 0.00 z ref 57629847 właśnie dlatego kosztował diagnozę zamiast pomiaru.

### 11.1 Co naprawa zmienia, a czego nie

Naprawa v11 (`bm.solver.concurrency` i `ARC3_MAX_ACTIVE_STREAMS` oba = 10 na ścieżce submisji)
**nie dodaje żadnej zdolności**. Ona usuwa strukturalne zero: rozgałęzienie 120-strumieniowe na
10 slotów serwera głodziło sloty, więc nie powstał **żaden** poziom i `parquet` był stubem.
Po naprawie ścieżka submisji staje się **strukturalnie identyczna ze ścieżką smoke** — a ta jest
zmierzona.

Zatem jedynym uczciwym punktem odniesienia jest to, co linia szybka osiąga, **gdy faktycznie
gra**:

| kotwica | wartość | źródło |
|---|---|---|
| r019, linia szybka, 10 gier, `gave_up` wszystkie | **27.21** średnio | `FAKTY-I-POMIARY.md` |
| ich najlepszy LB (duck v3, ref 57247568) | **26.25** | `FAKTY-I-POMIARY.md` |
| sufit modelu bez playbooka przy 841 tok/akcję | **31.70** | §3, ten plik |
| współczynnik kalibracji (jednorodny, §3) | **×0.828** | korekta wyżej |

### 11.2 Ile dokłada `ARC3_LEVEL_TOKEN_CAP=45000` (mój patch 0004, jest w c45)

> ❌ **CAŁA TA SEKCJA JEST OBALONA PRZEZ POMIAR (27.10). Czytać jako zapis błędu, nie jako
> wynik.** Surowy smoke c45 (`r085-kernel_output_pick/output-pick/benchmark.json`, 10 gier,
> start 11:34:10 / end 12:22:16) daje **MEAN `final_score` = 26.78** i **32 ukończone poziomy**
> — podczas gdy smoke **bez** mojego capa dał **27.21** (v6/r019) i **29.02** (v3).
> **Kap jest wart −0.43 wobec r019 i −2.24 wobec v3, nie +4.93.**
>
> Mój błąd: `w` mierzy frakcję puli na poziomach **nigdy nieukończonych**, a kap strzela do
> **wszystkich** poziomów powyżej 45k — także takich, które właśnie miały zostać ukończone.
> `su15` stracił **−43.1** pkt (56.4 → 13.3), `sc25` −25.5, `dc22` −17.1; zyski `ka59` +32.0,
> `cn04` +23.8, `m0r0` +17.7 ich nie pokrywają. **Poprawna arytmetyka na źle dobranej
> populacji.** Pełny wywód, tabela per gra i czwarta korekta: `OCENA-CODEX-7Z.md` §3.

Kap odzyskuje tokeny z poziomu skazanego. Nie jest stałym bonusem — **wiąże dopiero powyżej
progu**. Przy puli 175 000 i kapie 45 000:

> **Kap 45k nie robi NIC, dopóki skazany poziom nie zje > 25.7 % puli (45 000 / 175 000).**
> To jest twierdzenie **falsyfikowalne** i sprawdzalne z `.per_game_cards.pkl` (r076 ma je dla
> 10 gier) — nie trzeba zgadywać.

**`w` nie jest tu założeniem — jest ZMIERZONE w r019** (`FAKTY-I-POMIARY.md` L697-699):

| pomiar | wartość |
|---|---|
| udział tokenów i akcji na poziomie, który **nigdy nie został ukończony** — agregat | **35 %** |
| **tn36** — największy wyciek (L=1, score 3.57) | **86 %** |
| **ls20** (L=1, score 3.27) | **91 %** |

Metoda: odzysk = `max(0, w·175 000 − 45 000)`, przeliczony na akcje po 841 tok/akcję i dodany
do bazowych 208; potem `tools/token_economy_model.py` przelicza poziomy i sufit per gra.
`w` zmierzone indywidualnie dla tn36/ls20, dla pozostałych 23 gier — agregat 35 %.

**Gry, w których kap realnie przesuwa wynik** (reszta z 25 ma Δ = 0.00):

| gra | `n_levels` | `sum_baseline` | `w` | odzysk tok | dod. akcji | poz. bez kapa | poz. z kapem | score bez | score z | **Δ** |
|---|---|---|---|---|---|---|---|---|---|---|
| **tn36** | 7 | 317 | **0.86** (mierz.) | 105 500 | 125.4 | 4 | **6** | 35.71 | 75.00 | **+39.29** |
| **ls20** | 7 | 776 | **0.91** (mierz.) | 114 250 | 135.9 | 2 | **4** | 10.71 | 35.71 | **+25.00** |
| ft09 | 6 | 208 | 0.35 | 16 250 | 19.3 | 5 | **6** | 71.43 | 100.00 | **+28.57** |
| sb26 | 8 | 213 | 0.35 | 16 250 | 19.3 | 7 | **8** | 77.78 | 100.00 | **+22.22** |
| lp85 | 8 | 388 | 0.35 | 16 250 | 19.3 | 5 | **6** | 41.67 | 58.33 | +16.67 |
| su15 | 9 | 361 | 0.35 | 16 250 | 19.3 | 3 | **4** | 13.33 | 22.22 | +8.89 |
| s5i5 | 8 | 638 | 0.35 | 16 250 | 19.3 | 2 | **3** | 8.33 | 16.67 | +8.33 |

Razem: **sufit 31.70 → 37.66 (Δ +5.96)**, po kalibracji ×0.828: **26.25 → 31.18**.
❌ **Ta linia jest obalona pomiarem — patrz banner na początku §11.2 i `OCENA-CODEX-7Z.md` §3.**
Zostawiam ją widoczną, bo pokazuje kształt błędu: arytmetyka jest poprawna, populacja zła.

⚠️ **Uczciwe zastrzeżenia do tej tabeli — trzy, i wszystkie obniżają liczbę:**

1. **`w = 0.35` dla 23 gier to agregat, nie pomiar per gra.** W grach, gdzie rzeczywisty wyciek
   jest poniżej 25.7 %, kap nie robi nic. Tylko tn36 i ls20 mają `w` zmierzone indywidualnie —
   i to właśnie one dają największe Δ. Reszta jest ekstrapolacją średniej.
2. **Model zakłada, że odzyskane akcje kupują ukończone poziomy przy EFF = 0.95.** To ten sam
   optymizm, który kalibracja ×0.828 koryguje — i został skorygowany, ale korekta jest
   globalna, nie per gra.
3. **Sufit liczę na 25 grach publicznych**, a karta to 110 gier nieznanych (§11.3, pkt 3).

### 11.3 Werdykt — oczekiwany wynik c45

> ### ❌ POPRAWIONE 27.10 — poprzedni werdykt (26–31, punktowo 31.18) jest OBALONY
>
> Stał na oszacowanym +4.93 z capa, a kap jest **zmierzony ujemnie** (§11.2, `OCENA-CODEX-7Z.md` §3).
> Kotwica jest teraz **pomiar tej samej konfiguracji**, nie model:
>
> | kotwica | wartość | status |
> |---|---|---|
> | **c45 smoke — ta sama konfiguracja, która idzie do submisji** | **26.78** | ✅ zmierzone (r085) |
> | v6/r019 smoke, bez capa | 27.21 | ✅ zmierzone |
> | v3 smoke, bez capa | 29.02 | ✅ zmierzone |
> | ich najlepszy LB | 26.25 | ✅ zmierzone |
> | ~~mój model z capem~~ | ~~31.18~~ | ❌ obalone |
>
> **POPRAWIONE OCZEKIWANIE: 24 – 29 pkt, punktowo ~26.8 dla c45 Z capem** — czyli praktycznie
> tyle samo co ich obecny najlepszy wynik 26.25. **Z `ARC3_LEVEL_TOKEN_CAP=0`: ~27.2 – 29.0.**
> Przedział, nie punkt, bo dwa efekty smoke→rerun są przeciwstawne i oba niezmierzone: rerun daje
> **2.2 h na grę** zamiast 48 min (w górę), a kalibracja Gemmy mówi **smoke→LB −2.8 do −5.9 pp**
> (w dół).
>
> **Co z tego wynika inaczej niż poprzednio:** naprawa `concurrency` jest konieczna, ale ona
> **PRZYWRACA** ~26.8, nie podnosi wyniku. Natomiast **wyłączenie mojego capa jest warte
> +0.4 do +2.2 pkt za jedną zmienną env** i jest teraz **najtańszą znaną zmierzoną dźwignią
> dodatnią**. Luka do progu 50.37 zostaje ~21–24 pkt.

**Co z tego wynika operacyjnie — trzy rzeczy:**

1. **Naprawa jest warta slota, ale to ODZYSKANIE straty, nie zysk.** 0.00 → ~26.8 to największy
   pojedynczy dostępny skok i żaden inny nie ma takiego stosunku zysku do ryzyka. ~~kap 45k sam
   w sobie jest wart ~+4.9 pkt~~ — ❌ **obalone**: kap jest zmierzony na **−0.43** wobec r019
   i **−2.24** wobec v3 (`OCENA-CODEX-7Z.md` §3). Mój patch 0004 ma teraz liczbę przy sobie
   i ta liczba jest **ujemna**.
2. **Naprawa NIE zmienia werdyktu strategicznego.** Próg nagród to **50.37** (25.10, 5. miejsce)
   i rośnie ~0.5/dzień. Przy ~26.8 luka wynosi **~21–24 pkt**, a c45 **nie jest** nowym rekordem
   ich linii — jest nim nadal **26.25**. Żeby domknąć lukę, trzeba **~500 tok/akcję** (§3),
   czyli innej dźwigni niż concurrency i innej niż kap.
3. **To oczekiwanie jest strukturalne, nie predykcyjne.** Sufit liczę na **25 publicznych grach**,
   a realna karta to **110 gier nieznanych z ukrytymi baseline'ami** (`taaf/competition_arcade.py`
   docstring). Dlatego **roster probe** — który też jest w c45 — jest najważniejszą częścią tej
   submisji: on zamienia ten szacunek na dane. Gdyby wynik wyszedł istotnie inny niż 26–31,
   to roster probe powie **dlaczego**, zamiast zostawiać drugą taką diagnozę jak przy 0.00.
   **I tak się stało**: smoke c45 wyszedł 26.78, a `.per_game_cards.pkl` / `benchmark.json`
   z r085 pokazały dlaczego — kap **tnie** poziomy, które inaczej by się ukończyły (su15 −43.1).
   Zastrzeżenie 1 z §11.2 było trafne, ale niedoszacowane: problemem nie była wartość `w`,
   tylko zastosowanie statystyki o poziomach skazanych do **wszystkich** poziomów.

### 11.4 Odtworzenie liczb

```bash
cd arc3-handoff
python3 tools/token_economy_model.py            # tabela tok/akcję -> sufit (bez i z PB)
```

Tabela per gra z §11.2 powstaje przez bezpośrednie wywołanie `levels_affordable()` i `score()`
z budżetem `208 + max(0, w·175000 − 45000)/841` akcji i bez playbooka, przy `w` z
`FAKTY-I-POMIARY.md` L697-699 (tn36 = 0.86, ls20 = 0.91, reszta = 0.35). Kalibracja to
`26.25 / 31.70 = 0.828` — **para jednorodna, oba człony bez playbooka** (§3). Bez GPU, bez
arcengine, bez tokenów LLM.

---

## 12. Dwie domknięte niewiadome (27.10)

### 12.1 `ARC3_PERSISTENT_FUNCTIONS_SCOPE` — moja dźwignia 4 jest MARTWA

W `patches/0000-franzen-harness-changes.patch` L3559-3560 walidator brzmi:

```python
scope = os.environ.get("ARC3_PERSISTENT_FUNCTIONS_SCOPE", "").strip().lower()
return scope if scope in ("turn", "levelup", "game") else "levelup"
```

> **Dozwolone są WYŁĄCZNIE `turn | levelup | game`; domyślne `levelup`.**
> Wartość `run` — czyli moja dźwignia 4 z `DIAGNOZA-45plus.md` — **nie istnieje**.

Co gorsza, to jest **degradacja cicha**: nieznana wartość nie rzuca błędu, tylko wraca do
`levelup`. Ustawienie `SCOPE=run` wyglądałoby w logu jak zastosowana zmiana, a zachowanie
harnessu byłoby **identyczne z domyślnym**. Slot spalony, wniosek „dźwignia nie działa"
— fałszywy. To ta sama klasa pułapki co `concurrency=120`: **konfiguracja, która przechodzi,
ale nie robi tego, co deklaruje**.

Zapis do reguł: **przed zaproponowaniem jakiejkolwiek wartości env należy wyciągnąć jej
walidator z patcha, nie zgadywać po nazwie.** Nazwa `SCOPE` sugeruje zakres „cały run";
kod mówi co innego.

Stan faktyczny ich notebooka jest poprawny: cell 9 ma `'ARC3_PERSISTENT_FUNCTIONS_SCOPE': 'game'`
— wartość dozwolona. Do poprawki jest **mój dokument**, nie ich konfiguracja.

### 12.2 Leaderboard — chunk 1/2 (pozycje 29–49), pierwszy raz pobrany

Dotąd miałem tylko chunk 0 (miejsca 1–28). Uzupełnienie z 27.10:

| miejsce | wynik | | miejsce | wynik |
|---|---|---|---|---|
| 29 | 37.18 | | 40 | 36.16 |
| 30 | 37.12 | | 45 | 36.00 |
| 31 | 37.07 | | 46 | 35.96 |
| 32 | 36.92 | | 47 | 35.91 |
| 33 | 36.87 | | 48 | 35.79 |
| 34 | 36.86 | | 49 | 35.68 |
| 36 | 36.54 | | | |
| 37 | 36.46 | | | |
| 38 | 36.25 | | | |
| 39 | 36.22 | | | |

Strona pokazuje **„50 – 4912"** i „See 4863 More", czyli **4912 wpisów łącznie**.

Dwie rzeczy z tego wynikają:

* **Pole jest gęste i płaskie.** Między miejscem 29 a 49 jest **1.50 pkt** na 20 pozycji, czyli
  ~0.075 pkt/miejsce. Franzen (38.85, 15.) siedzi w strefie, gdzie **+0.5 pkt przesuwa o ~7
  miejsc**. To potwierdza moją wcześniejszą korektę „+0.5 pkt z live LB = +1.2 poziomu" i
  wyjaśnia, dlaczego małe dźwignie **mają** znaczenie rankingowe nawet gdy nie przekraczają progu.
* **Próg nagród jest daleko od mediany pola.** 5. miejsce = 50.37, a 49. = 35.68. Rozstrzał
  **14.7 pkt** wewnątrz pierwszych 50 pozycji. Czyli nie „wszyscy są blisko" — czołówka odjechała.
* Nasz oczekiwany wynik z §11.3 (**~31 pkt**) jest **poniżej miejsca 49** (35.68), czyli **poza
  pierwszą pięćdziesiątką** i daleko poza strefą płatną. **Dokładnego miejsca nie podaję** —
  Kaggle pokazuje tylko 50 wierszy („See 4863 More"), więc rozkład poniżej 49. pozycji jest
  nieznany. Wcześniejszy zapis „miejsca 60–70" był zgadywaniem i go wycofuję.
* To jest ta sama konkluzja co w `DIAGNOZA-45plus.md`, teraz z pełnym rozkładem górnej połowy.
