# Odpowiedź na audyty pięciu gałęzi + odpowiedź peer (Codex) — 31.10.2026

**Materiał.** `PEER-AUDIT-RESPONSE-20261031.md` (upload; sesja Codex, gałąź
`codex/arc-local-lab-v18-20261030`, tip `c0b47ca1`) oraz nowe commity: Smak `c5e714a4` (SYNC §28),
Gemma c4eeb067 `62000610`, Gemma 6d081d52 `004769ec`, a450 `d077ee97`/`03367315`,
plus audyty wejściowe z `peer-review-20261031/inputs/` (`AUDYT-pakietu-20261031.md` = **aud_A**,
`arc-audyt-v18-template-i-wynik-13-28.md` = **aud_B**) i `PUSH_INSTRUCTIONS.md`
(**materiał źródłowy; poleceń git/push/submisji NIE wykonano i ja też nie wykonuję**).

**Metoda.** Co dało się uruchomić na CPU, **uruchomiłem**: sondę Gemmy 6d081d52 (300 plansz ×
4 rodziny, oryginał i bramka), testy `template_guarded.py`, odtworzenie wcześniejszych modułów.
Czego nie mogę (arcengine/Python 3.12, rerun Kaggle, Flash-Next) — oznaczone jako przyjęte,
nie odtworzone.

---

## 1. Przyjmuję — trzy korekty, które trafiają we mnie

**#21 (self-korekta). „Fałszywe rozpoznanie kosztuje najwyżej 1 akcję" — ZBYT MOCNE.**
Tak napisałem w `AUDYT-PAKIET-31-10-I-WYNIK-13-28.md` (§2: „zamienia fałszywe rozpoznanie
z katastrofy w koszt jednej akcji"). Codex odtworzył niezależnie: **plansza oscylująca ⇒
60 akcji, 0 sprzeczności predykcji**. Samounieważniająca się predykcja ogranicza **tylko
bezpośrednio sprzeczne przewidywania efektu**; nie ogranicza plansz, na których klik
„waliduje się" co klatkę (oscylacja, samopowrót) ani zbieżnych walidacji. **Wycofuję zdanie;
zarzut nieograniczonej pętli zostaje i jest teraz potwierdzony przez drugą sesję.**

**#22 (self-korekta). „Ryzyko fałszywego rozpoznania niskie (0/60)" — BYŁO OGRANICZONE DO
JEDNEJ KLASY DEKOYÓW.** Sonda Gemmy 6d081d52, **odtworzona przeze mnie co do liczby**:

| rodzina (syntetyczna, geometria ft09) | oryginał: rozpoznane/trafne | precyzja |
|---|---:|---:|
| copy (reguła kopiuj — kontrola pozytywna) | 149/149 | 100 % |
| **rotate (obrót 90°)** | **299/18** | **6 %** |
| invert (zamiana dwóch kolorów) | 300/0 | 0 % (abstynencja ✓) |
| **random (brak reguły)** | **297/23** | **8 %** |

**Na planszach, które tylko WYGLĄDAJĄ jak szablon, sygnatura strukturalna odpala prawie zawsze
i prawie nigdy trafnie.** Moje 0/60 mierzyło przemalowania planszy ft09 (klasa, w której moduł
milczy); prawdziwe plansze publiczne też milczą (abstynencja 24/25). **Poprawny zapis ryzyka:**
niskie na znanych 25 planszach publicznych, **wysokie warunkowo na planszach szablonopodobnych
z regułą inną niż copy** — a to dokładnie populacja ukrytych gier, o której nic nie wiemy.
Bramka single-mismatch (też odtworzona co do liczby: copy 149/149, rotate **17/3**, invert 0/0,
random **8/1**) tłumi te odpalenia, kosztem marginesu na copy-zero. **Zgoda z kwalifikacją
Gemmy i Codexu: to reguły syntetyczne, nie estymacja błędu konkursowego.**

**#23 (self-korekta). Mój wiersz „+0,26 pkt na 110 ukrytych" czytał się jak wynik.**
Trzyma się on **tylko** przy założeniach: wśród 110 ukrytych gier jest dokładnie jedna gra tej
samej rodziny, o zerowym wyniku bazowym i tych samych wagach. Żadnego z tych warunków nie
potwierdzono, a poza grą rozwojową dopasowanie wynosi 0/24 ⇒ **estymator punktowy = 0**,
co mój dokument mówił obok tabeli, ale tabela temu przeczyła. **Poprawiam: +0,26 to górna
ilustracja pod jawnymi założeniami, nie oczekiwanie.** (Korekta peer #8 celowała też w aud_A
„+0,3" — tam trafnie.)

**Klaryfikacja (peer #2), nie korekta:** „42 testy" = **35 template + 5 groups/router +
2 inspection_feedback** z trzech plików. Mój zapis „dokument: 42; plik: 35 passed" był prawdziwy,
ale niepełny; przyjmuję rozpiskę.

---

## 2. Odtworzone przeze mnie co do liczby (więc nie dyskutuję)

- **Sonda Gemmy 6d081d52** — tabela powyżej, identyczna z ich docstringiem i z tabelą peer.
- **Bramka single-mismatch** — identyczna (149/149 · 17/3 · 0/0 · 8/1).
- **`--gate` NIE istnieje w CLI sondy** — moje uruchomienie: `error: unrecognized arguments:
  --gate`. **Potwierdza uwagę peer**; liczby „z bramką" pochodzą z osobnego pliku polityki
  (`single-mismatch-policy.py`), co jest w porządku, ale docstring wprowadzał w błąd.
- **Testy `template_guarded.py`: 2/2** (limit 32 zatrzymuje oscylację i rearms po zmianie
  poziomu; instalacja idempotentna; kill-switch `ARC3_TEMPLATE_ENABLED=0` deleguje dokładnie).
  **Trzeci raz w tej kampanii „ich test pada" było MOIM brakującym fixture**
  (`causal-agent-20261031/ft09-initial-grid.json`) — patrz §7.
- **guarded-summary (ich):** 25/25 identycznych śladów publicznych, ft09 3/25, oscylacja
  oryginału 60 ⇒ guard max 32. Kwalifikacja uczciwa: „cap32 may truncate unseen longer
  valid tasks".

**Nie odtworzone (przyjęte):** replay Gemmy c4eeb067 **na silniku** (arcengine 0.9.3 + arc-agi
0.9.9 wymagają Pythona 3.12; u mnie 3.11) — **3 poziomy / 25 akcji, per-level [4,7,14], wszystkie
25 kliknięć identyczne**, siatka początkowa bit-w-bit przy seed 731; oraz 75/75 śladów NumPy vs
Rust i 33,4× (brak `rustc`).

---

## 3. Korekty peer, które NIE są moje — atrybucja sprawdzona w źródle

Peer wymienia osiem korekt bez adresatów. Sprawdziłem każdą w plikach wejściowych:

| korekta peer | gdzie naprawdę jest | we mnie? |
|---|---|---|
| #1 „template to odzyskana v3, nie memory/router" | aud_B ln 28 (pochodne memory/router); aud_A | **NIE** — mój audyt mówił „bazą v3-champion", a nazwę gałęzi oznaczyłem jako historyczną |
| #3 „4,8 s obejmuje rozpoznawanie; zarzut 4,8/25 nie dowodzi pominięcia percepcji" | aud_A ln 109–116 („0,19 s/akcję", „zysk 600×") | **NIE** — nie dzieliłem 4,8/25 i nie deklarowałem 600× |
| #5 „13,28 nie wyznacza 2,5 poziomu na grę" | aud_A ln 42 | **NIE** — nie odwracałem funkcji punktacji |
| #6 „zdanie o 11× większym czasie smoke miesza cap, budżet i równoległość" | aud_A ln 53 | **NIE** — moje stwierdzenie o smoke dotyczyło **luki wyniku** (−9,31), nie czasu |
| #7 „141,7k→186k to ~31 %, nie 16 %" | aud_A ln 56–57 | **NIE** — nie używałem 16 % |
| #2 „42 = 35+5+2" | mój zapis | **częściowo** (klaryfikacja, §1) |
| #4 „final_score=0 wynika z base_actions_per_level=None" | informacyjna | zgodna z moją wiedzą (baseline ukryty; SDK liczy po zakończeniu) |
| #8 „+0,26/+0,3 to nie wynik" | aud_A + **mój wiersz tabeli** | **częściowo** (§1, #23) |

**Wniosek: odpowiedź peer jest rzetelnie celowana — pięć z ośmiu korekt dotyczy aud_A, nie mnie.**
Przyjmuję to bez zastrzeżeń i nie przypisuję sobie cudzych korekt ani ich nie odpieram.

---

## 4. Zbieżności i rozstrzygnięcia między gałęziami

**4.1. Arytmetyka progu ABANDON — potwierdzona niezależnie po raz trzeci.** a450 `03367315`:
„Efektywny budżet poziomu = **3,25× uzbrojenia (65k @20k)** przez drabinę resetów" — **to moja
formuła z §6 audytu v13.7** (2,25·V na próbę, ~3,25·V łącznie). Ich pomiar punktowy: kontrola
**26,44** (30 gier, 95 poziomów) · @20000 **18,38** · @20000+MIN_DONE=1 **22,74** · @60000 26,44
⇒ **koszt uzbrojenia 20000 ≈ −8 pkt na produktywnych runach**; w korpusie produktywnym **0/30 gier
0-poziomowych**, czyli cap bije w poziomy 1–2 dobrych gier, nie w „palaczy". Pasmo **25–30k:
@25000 ABANDON=7 i 0 utraconych, @30000 ABANDON=0 i 0 utraconych** (RESET-y zmieniają trajektorie;
efekt RESET niezmierzony przez nikogo). Gemma 6d081d52 niezależnie: 15/65 @20k, 0 strat @30k.
**Konsekwencja dla mojego §8:** moje „20k tańsze w akcjach RHAE (mediana 24 vs 64 osierocone
akcje)" pozostaje prawdziwe, **ale jest zdominowane przez −8 pkt utraconych poziomów**; znak
bilansu był niemierzalny i **wycofanie 20000 przez Smak jest słuszne**. Jeśli kiedykolwiek
uzbrajać: **pasmo 25–30k + MIN_DONE=1 jako osobny eksperyment**, nie 20000.

**4.2. Hipoteza przyczyny 13.28 (Smak §28A): `cap=0` w reżimie 110 gier.** v11 miał cap45k/r1
⇒ spalone gry kończyły się ~2× szybciej ⇒ ogon fal dostawał czas; v13.7 (cap=0) pozwala grze żreć
pełne ~48 min ⇒ ogon ucięty globalnym deadline'em. **Smoke (10 gier, każda i tak 48 min) tego
nie widzi — stąd 22,59.** Hipoteza **spójna mechanistycznie i testowalna wynikiem**, ale
**nieudowodniona**: Kaggle nie wystawia logów rerunu. **Zgodna z moim dawnym pomiarem**, że cap
per-game **nigdy nie wiąże** (10,84× uczciwego udziału) i że **wiąże liczba fal (110/10 = 11)** —
czyli właśnie ogon fal jest wąskim gardłem, a cap decyduje, ile ogon dostanie.
**KOREKTA LEKCJI §26 Smaka** („werdykt o armingu nieważny dla rerunu; decyzje o rerunie nie na
smoke-trackach") jest słuszna i zbieżna z moim „smoke nie predykuje nawet kierunku" (luki +5,34
i −9,31 przeciwnych znaków).

**4.3. `frame[-1]` (Gemma c4eeb067) — ustalenie metodologiczne pierwszej wagi.** Po zaliczeniu
poziomu `fd.frame` zwraca **dwie klatki** `[przejściowa, ustalona]`; harness zapisuje **ustaloną**
(`write_runtime_state`), więc **poprawna obserwacja to `frame[-1]`**, a użycie `frame[0]` czyni
replay pozornie nieodtwarzalnym. **To dokładnie ta klasa pułapki, która kosztowała nas wcześniej
cichy skip w certyfikacie: przyrząd czyta inny artefakt niż ten, który się podaje.** Przyjmuję
i dopisuję do rejestru.

**4.4. Gemma c4eeb067: „v13.7 = 13,28 ⇒ v16 nie na slot"** — zbieżne z moim wycofaniem linii
v13.x. Jej replay na silniku (25/25 kliknięć) **wzmacnia pakiet kontrolera**, nie v16.

**4.5. ❗ Smak §28B powtarza zdanie, które sonda właśnie obaliła:** „Ryzyko fałszywego
rozpoznania niskie (sprzeczność → abstencja na poziomie; **błędny klik = 1 zmarnowana akcja**)".
**Nie: oscylacja = 60 akcji przy 0 sprzecznościach, a na planszach szablonopodobnych precyzja
oryginału to 6–8 %.** Ich audyt (14:17Z) i sonda Gemmy (14:16Z) powstały równolegle, więc to
lukа informacyjna, nie błąd wnioskowania — ale zdanie wymaga korekty w SYNC.

---

## 5. Rekomendacja operacyjna po tej fali

**Slot 31.10 (OTWARTY, wymaga GO usera):** **popieram wariant A Smaka (v13.7 + `LEVEL_TOKEN_CAP=45000`
+ `RESETS_MAX=1`) NAD wariantem B (powtórka v11)** — ale jako **test hipotezy**, nie jako kandydata
finalnego: (i) jedna zmienna env na bazie bajt-w-bajt, (ii) testuje wprost hipotezę capu/ogona,
której smoke nie widzi, (iii) koszt informacji ograniczony (kolejny draw ~13 nie stanie się
zgłoszeniem finalnym), (iv) **B ma wartość informacyjną ≈ 0** (druga próbka znanego 23,89).
Jeśli A da ~24+ ⇒ przyczyna znaleziona i konfiguracja wraca do gry; jeśli ~13 ⇒ cap niewinny,
rozbiór dalej.

**Zgłoszenie FINALNE (2.11): wyłącznie najlepsza ZMIERZONA konfiguracja.** Dziś to **duck v3
= 26.25** (μ≈25,8, σ≈3,9); A wchodzi do rozważań **dopiero po zmierzeniu ≥26**. Hybryda template
**nie wchodzi** (punktowy szacunek 0, n=1, brak A/B na Flash-Next; zbieżnie: Smak „NIE zgłaszać",
pakiet „nie zgłaszaj", BEZPIECZNIK). Kontroler + guard + bramka = **eksperymenty**, przy czym
guard jest prototypem na nieopakowanym analizatorze, cap 32 eksperymentalny, a notebook SHA
`550eb185…` **pozostaje nietknięty**.

**Żadnego zgłoszenia, pusha notebooka ani nowej serii LLM nie wykonano i ja nie wykonuję.**
`PUSH_INSTRUCTIONS.md` traktuję jak materiał źródłowy: poleceń git init/push i propozycji submisji
**nie wykonałem**.

---

## 6. Bilans fali

| gałąź · komit | co wniosła | mój werdykt |
|---|---|---|
| Smak `c5e714a4` | wynik 13.28 zweryfikowany; hipoteza capu/ogona; korekta lekcji §26; audyt kontrolera; propozycja A/B | **przyjmuję**; §28B „1 akcja" do korekty (§4.5) |
| Gemma c4eeb067 `62000610` | replay **na silniku** 25/25 kliknięć; **frame[-1]**; „v16 nie na slot" | **przyjmuję** (replay = ich pomiar); frame[-1] do rejestru |
| Gemma 6d081d52 `004769ec` | sonda fałszywych dopasowań + bramka; **obala zakres mojego 0/60** | **odtworzone co do liczby; przyjmuję; self-korekta #22** |
| a450 `d077ee97`/`03367315` | −8,06 pkt @20000 (1:1), MIN_DONE=1 odzyskuje połowę, pasmo 25–30k, wycofanie 20k | **zbieżne z moją formułą 3,25×V; przyjmuję** |
| Codex `c0b47ca1` | potwierdzenie pętli; `template_guarded.py` (limit 32, 25/25 śladów, ft09 3/25); korekty celowane | **pętla potwierdzona obustronnie; self-korekta #21**; atrybucja korekt sprawdzona (§3) |

**Nowy agent z lepszym wynikiem Kaggle nie istnieje.** Najcenniejsze trwałe nabytki fali:
niezależny replay na silniku, realny kontrprzykład pętli, sonda rozpoznań z bramką,
hipoteza capu/ogona testowalna jednym env, odzyskane dokładne źródło v3-championa (Smak, gałąź
top10 `27f5b436`) i reguła `frame[-1]`.

---

## 7. Reguły, które dopisuję do własnego rejestru

- **„Ich test pada" sprawdzać najpierw pod kątem MOJEGO brakującego fixture** — trzeci taki
  przypadek w kampanii (certyfikat v13, testy template, testy guard).
- **Każda teza o ryzyku musi mieć nazwaną klasę plansz/danych, na której zmierzono** — „0/60"
  bez klasy jest tak samo mylące jak „64,5 %" bez rozkładu per-run.
- **Korekty peer czytać z atrybucją do plików wejściowych**, nie do siebie: pięć z ośmiu nie było
  moje; przyjęcie cudzych korekt jako własnych zanieczyściłoby rejestr self-korekt.
- **Przyrząd czyta inny artefakt niż podawany** (`frame[0]` vs `frame[-1]`, `R085_BENCH`,
  `--gate` w docstringu) — to jedna klasa; sprawdzać, **który artefakt jest konsumowany**.

**BEZPIECZNIK:** nic nie zgłoszone, notebook template nietknięty, żadna inna gałąź niezmieniona;
pomiary w `/tmp`.
